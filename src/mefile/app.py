# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# app - stdlib web app: consent first, then answers -> reviewed, corrected, scoped me.md download

"""
The employee's app (problem statement: review, question, correct, decide whether to share)
=========================================================================================

Stateless by design: the server keeps NO answers and NO profiles. The browser holds the person's
answers, sends them to /api/convert, and downloads the result itself. The only thing written to
disk is the consent ledger (what was agreed, when, for which purposes), because a consent is only
worth something if it can be shown later. Withdrawing appends a withdrawal entry; the ledger is
append-only so the history of agreement and withdrawal is never rewritten.

Consent is enforced HERE, not only on the page. /api/consent returns an opaque ``consent_token``;
the server keeps, in memory only, sha256(token) -> person code, purposes, time (the raw token is
never stored, and the ledger records only the hash). /api/convert needs a token carrying
``build_profile``, /api/twin ``ai_processing``, /api/voice/session ``voice_interview``; the token
travels in the ``X-Consent-Token`` header or a ``consent_token`` body field, and anything else is
403 ``{"error": "consent required", "purpose": ...}``. /api/withdraw revokes the token and every
other token for that person code. A server restart forgets every token, so the page must consent
again: failing toward "ask again" is the safe direction.

Endpoints
  GET  /                      the public front door (static/home.html)
  GET  /app                   the employee bench, the single-page app (static/index.html)
  GET  /team                  the team hub (static/team.html); its API and the paste station live in team.py
  GET  /api/example           the fictional DEMO01 build file
  POST /api/consent           record consent  {person_id, purposes[], ai_services[], share_with[]} -> {receipt, consent_token}
  POST /api/withdraw          record withdrawal {person_id, consent_token?}; revokes the person's tokens
  POST /api/convert           [build_profile] {answers, scope, withhold[]} -> {markdown, sidecar, claims, gate, problems}
  POST /api/twin              [ai_processing] {markdown, question_id} -> {text, model, question}
  POST /api/voice/session     [voice_interview] ElevenLabs signed URL for the voice interview (only when configured)
  GET  /api/voice/transcript  ?conversation_id=... -> transcript, employee turns only
  /paste, /api/station/*, /api/team/*   team tooling behind the team code (team.py, docs/team-hub-contract.md)
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import team
from .answers import parse_answers
from .converter import SHARE_SCOPES, convert

STATIC = Path(__file__).parent / "static"
EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
LEDGER_DIR = Path(os.environ.get("MEFILE_CONSENT_DIR", "consent"))
QUESTIONS_FILE = Path(os.environ.get("MEFILE_QUESTIONS", str(EXAMPLES / "example_questions.json")))
MAX_BODY = 512_000

# Which consent purpose each gated endpoint needs. Team routes are absent: the team code gates them (team.py).
REQUIRED_PURPOSE = {"/api/convert": "build_profile", "/api/twin": "ai_processing", "/api/voice/session": "voice_interview"}

_CONSENTS: dict[str, dict] = {}  # sha256(token) -> {person_id, purposes, at}; memory only, raw tokens never kept
_CONSENTS_LOCK = threading.Lock()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue_token(person_id: str, purposes: list[str], at: str) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    digest = _token_hash(token)
    with _CONSENTS_LOCK:
        _CONSENTS[digest] = {"person_id": person_id, "purposes": frozenset(purposes), "at": at}
    return token, digest


def _token_allows(token: str, purpose: str) -> bool:
    if not token:
        return False
    with _CONSENTS_LOCK:
        record = _CONSENTS.get(_token_hash(token))
    return record is not None and purpose in record["purposes"]


def _revoke(person_id: str, token: str) -> list[str]:
    """Revoke the presented token and every token issued to this person code; return the revoked hashes."""
    with _CONSENTS_LOCK:
        doomed = {digest for digest, record in _CONSENTS.items() if person_id and record["person_id"] == person_id}
        if token and _token_hash(token) in _CONSENTS:
            doomed.add(_token_hash(token))
        for digest in doomed:
            del _CONSENTS[digest]
    return sorted(doomed)


def _ledger_append(entry: dict) -> dict:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **entry}
    with (LEDGER_DIR / "ledger.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


class Handler(BaseHTTPRequestHandler):
    server_version = "mefile"

    def log_message(self, fmt, *args):  # never log request bodies; paths only
        print(f"{self.command} {self.path.split('?')[0]} -> {args[1] if len(args) > 1 else ''}")

    def _send(self, status: int, body: bytes, content_type: str, headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ValueError("request too large")
        body = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(body, dict):
            raise ValueError("request body must be a JSON object")
        return body

    def _page(self, name: str) -> None:
        target = STATIC / name
        body = target.read_bytes() if target.is_file() else _FALLBACK_PAGES.get(name, _FALLBACK_PAGES["home.html"])
        return self._send(200, body, "text/html; charset=utf-8")

    def _client_address(self) -> str:
        forwarded = str(self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        return forwarded or self.client_address[0]

    def _team(self, path: str, body: dict) -> None:
        from urllib.parse import urlparse
        reply = team.handle(team.Request(
            method=self.command, path=path, query=urlparse(self.path).query, body=body,
            cookie_header=str(self.headers.get("Cookie") or ""), client_address=self._client_address(),
            https=str(self.headers.get("X-Forwarded-Proto") or "").lower() == "https"))
        if reply.body is not None:
            return self._send(reply.status, reply.body, reply.content_type, reply.headers)
        return self._send(reply.status, json.dumps(reply.payload, ensure_ascii=False).encode("utf-8"), reply.content_type, reply.headers)

    def _consent_token(self, body: dict) -> str:
        return str(self.headers.get("X-Consent-Token") or body.get("consent_token") or "")

    def _twin(self, body: dict):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return self._json(503, {"error": "Try your twin needs an Anthropic API key on the server (ANTHROPIC_API_KEY)."})
        try:
            return self._json(200, _twin_answer(str(body.get("markdown", ""))[:200_000], str(body.get("question_id", ""))))
        except ValueError as error:
            return self._json(400, {"error": str(error)})
        except Exception as error:  # report the reason, never the key
            return self._json(502, {"error": f"player two could not answer: {type(error).__name__}"})

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            return self._page("home.html")
        if path in ("/app", "/index.html"):
            return self._page("index.html")
        if path == "/team":
            return self._page("team.html")
        if team.is_team_path(path):
            return self._team(path, {})
        if path.startswith("/static/") and path.count("/") == 2 and path.rsplit(".", 1)[-1] in ("css", "js", "svg"):
            target = STATIC / path.split("/")[-1]
            if target.is_file():
                kinds = {"css": "text/css", "js": "text/javascript", "svg": "image/svg+xml"}
                return self._send(200, target.read_bytes(), kinds[path.rsplit(".", 1)[-1]] + "; charset=utf-8")
            return self._json(404, {"error": "not found"})
        if path == "/api/twin/questions":
            from .answers import load_questions
            questions = load_questions(QUESTIONS_FILE)
            return self._json(200, {"questions": [{"id": q.id, "type": q.type, "wording": q.wording, "prompt": q.prompt,
                                                   "word_limit": q.word_limit} for q in questions.values()]})
        if path == "/api/example":
            return self._send(200, (EXAMPLES / "example_build_answers.json").read_bytes(), "application/json")
        if path == "/api/config":
            from . import voice
            return self._json(200, {"scopes": SHARE_SCOPES, "voice_enabled": voice.configured(),
                                    "twin_enabled": bool(os.environ.get("ANTHROPIC_API_KEY"))})
        if path == "/api/voice/transcript":
            from urllib.parse import parse_qs, urlparse
            from . import voice
            conversation_id = parse_qs(urlparse(self.path).query).get("conversation_id", [""])[0]
            try:
                return self._json(200, voice.fetch_transcript(conversation_id))
            except Exception as error:  # surface the reason, never the key
                return self._json(502, {"error": str(error)})
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            body = self._body()
        except ValueError as error:
            return self._json(400, {"error": str(error)})
        if team.is_team_path(path):
            return self._team(path, body)
        purpose = REQUIRED_PURPOSE.get(path)
        if purpose and not _token_allows(self._consent_token(body), purpose):
            return self._json(403, {"error": "consent required", "purpose": purpose})
        if path == "/api/consent":
            purposes = body.get("purposes")
            if not body.get("person_id") or not isinstance(purposes, list) or not purposes:
                return self._json(400, {"error": "person_id and at least one purpose are required"})
            person_id, purposes = str(body["person_id"]), [str(p) for p in purposes]
            at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            token, digest = _issue_token(person_id, purposes, at)
            entry = _ledger_append({"at": at, "event": "consent", "person_id": person_id, "purposes": purposes,
                                    "ai_services": body.get("ai_services", []), "share_with": body.get("share_with", []),
                                    "token_sha256": digest})
            return self._json(200, {"receipt": entry, "consent_token": token})
        if path == "/api/withdraw":
            person_id = str(body.get("person_id", ""))
            revoked = _revoke(person_id, self._consent_token(body))
            entry = _ledger_append({"event": "withdrawal", "person_id": person_id, "revoked_token_sha256": revoked})
            return self._json(200, {"receipt": entry})
        if path == "/api/convert":
            answers = parse_answers(body.get("answers") or {})
            scope = body.get("scope", "full")
            try:
                profile = convert(answers, scope=scope, excluded_domains=set(body.get("withhold") or []))
            except ValueError as error:
                return self._json(400, {"error": str(error)})
            return self._json(200, {
                "markdown": profile.markdown,
                "sidecar": profile.sidecar,
                "claims": [{"id": c.id, "kind": c.kind, "text": c.text, "evidence": list(c.evidence)} for c in profile.claims],
                "gate": {"passed": profile.gate.passed, "blocking": profile.gate.blocking, "warnings": profile.gate.warnings},
                "problems": answers.problems,
                "answers": answers.to_json(),
            })
        if path == "/api/twin":
            return self._twin(body)
        if path == "/api/voice/session":
            from . import voice
            try:
                return self._json(200, voice.start_session())
            except Exception as error:
                return self._json(502, {"error": str(error)})
        return self._json(404, {"error": "not found"})


_FALLBACK_PAGES = {  # served only until the real page exists in static/
    "home.html": (b"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width, initial-scale=1'>"
                  b"<title>lumin8r</title><h1>lumin8r</h1><p><a href=\"/app\">Build your file</a></p>"
                  b"<p><a href=\"/team\">Team</a></p>"),
    "team.html": (b"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width, initial-scale=1'>"
                  b"<title>lumin8r team</title><h1>Team</h1><p>The team page is not built yet. <a href=\"/\">Home</a></p>"),
}


def _twin_answer(markdown: str, question_id: str) -> dict:
    """Player two answers ONE question as the person, through the official two-turn loading protocol."""
    from .answers import load_questions
    from . import runner
    questions = load_questions(QUESTIONS_FILE)
    question = questions.get(question_id)
    if question is None:
        raise ValueError("unknown question")
    import anthropic
    result = runner.ask(anthropic.Anthropic(), markdown, question)
    return {"text": result["text"], "model": result["model_served"],
            "question": {"id": question.id, "type": question.type, "prompt": question.prompt, "word_limit": question.word_limit}}


def serve(port: int = 8080) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"mefile app on http://localhost:{port}  (consent ledger: {LEDGER_DIR.resolve()})")
    print(f"team hub on http://localhost:{port}/team  (people: {team.people_dir().resolve()}, data: {team.data_dir().resolve()}, "
          f"team code: {team.gate_mode()})")
    server.serve_forever()
