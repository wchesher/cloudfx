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
  GET  /                      the single-page app
  GET  /api/example           the fictional DEMO01 build file
  POST /api/consent           record consent  {person_id, purposes[], ai_services[], share_with[]} -> {receipt, consent_token}
  POST /api/withdraw          record withdrawal {person_id, consent_token?}; revokes the person's tokens
  POST /api/convert           [build_profile] {answers, scope, withhold[]} -> {markdown, sidecar, claims, gate, problems}
  POST /api/twin              [ai_processing] {markdown, question_id} -> {text, model, question}
  POST /api/voice/session     [voice_interview] ElevenLabs signed URL for the voice interview (only when configured)
  GET  /api/voice/transcript  ?conversation_id=... -> transcript, employee turns only
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

from .answers import parse_answers
from .converter import SHARE_SCOPES, convert

STATIC = Path(__file__).parent / "static"
EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
LEDGER_DIR = Path(os.environ.get("MEFILE_CONSENT_DIR", "consent"))
PEOPLE_DIR = Path(os.environ.get("MEFILE_PEOPLE_DIR", "private/people"))
QUESTIONS_FILE = Path(os.environ.get("MEFILE_QUESTIONS", str(EXAMPLES / "example_questions.json")))
STATION_VARIANTS = os.environ.get("MEFILE_VARIANTS", "evidence_first,trait_first,short").split(",")


def _station_queue(model_filter: str | None) -> dict:
    """Every run the paste station needs: person x model x condition x question, with what to paste and what is saved."""
    from .answers import load_answers, load_questions
    from .experiment import pasted_responses
    questions = load_questions(QUESTIONS_FILE)
    people = sorted(p for p in PEOPLE_DIR.iterdir() if (p / "build.json").exists() and (p / "test.json").exists()) if PEOPLE_DIR.exists() else []
    runs, profiles = [], {}
    for person_dir in people:
        build = load_answers(person_dir / "build.json")
        pid = build.person_id
        for variant in STATION_VARIANTS:
            profile = convert(build, variant=variant)
            if profile.gate.passed:
                profiles[f"{pid}/{variant}"] = profile.markdown
        for model in ("A", "B"):
            if model_filter and model != model_filter:
                continue
            saved = pasted_responses(person_dir, model)
            for condition in ["none", *STATION_VARIANTS]:
                if condition != "none" and f"{pid}/{condition}" not in profiles:
                    continue
                for question_id, question in questions.items():
                    run_id = f"{pid}-{model}-{condition}-{question_id}"
                    runs.append({"run_id": run_id, "person": pid, "model": model, "condition": condition,
                                 "question_id": question_id, "type": question.type, "word_limit": question.word_limit,
                                 "profile_key": None if condition == "none" else f"{pid}/{condition}",
                                 "question": question.prompt, "answer": saved.get(run_id, "")})
    return {"runs": runs, "profiles": profiles, "people_dir": str(PEOPLE_DIR.resolve()), "variants": STATION_VARIANTS}


def _station_save(body: dict) -> dict:
    import re
    run_id, text = str(body.get("run_id", "")), str(body.get("text", ""))
    match = re.fullmatch(r"(.+)-([AB])-([a-z_]+)-([A-Za-z0-9]+)", run_id)
    if not match:
        raise ValueError("bad run id")
    pid, model, _, question_id = match.groups()
    person_dir = next((p for p in PEOPLE_DIR.iterdir() if (p / "build.json").exists()
                       and json.loads((p / "build.json").read_text(encoding="utf-8")).get("person_id") == pid), None)
    if person_dir is None:
        raise ValueError("unknown person")
    path = person_dir / f"llm_{model.lower()}.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"responses": []}
    data["responses"] = [r for r in data["responses"] if r.get("run_id") != run_id]
    if text.strip():
        data["responses"].append({"run_id": run_id, "question_id": question_id, "text": text.strip(),
                                  "pasted_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    from .answers import load_answers
    from .judge.features import parse_choice
    test = load_answers(person_dir / "test.json")
    chosen = parse_choice(text)
    reference = test.scenarios.get(question_id, {}).get("choice")
    return {"saved": bool(text.strip()), "choice": chosen, "match": (chosen == reference) if (chosen and reference) else None}


def _station_results() -> dict:
    from .answers import load_questions
    from .experiment import run_experiment
    out = PEOPLE_DIR.parent / "experiment"
    result = run_experiment(PEOPLE_DIR, load_questions(QUESTIONS_FILE), STATION_VARIANTS, out, None)
    return {"summary": result["summary"], "results_md": str((out / "results.md").resolve())}
MAX_BODY = 512_000

# Which consent purpose each gated endpoint needs. /api/station/* is deliberately absent: see do_GET/do_POST.
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

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
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
        if path in ("/", "/index.html"):
            return self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
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
        if path == "/paste":
            return self._send(200, (STATIC / "paste.html").read_bytes(), "text/html; charset=utf-8")
        # /api/station/* is team tooling over consenting teammates' data already on disk, not a person's own session: ungated.
        if path == "/api/station/queue":
            from urllib.parse import parse_qs, urlparse
            model = parse_qs(urlparse(self.path).query).get("model", [""])[0] or None
            try:
                return self._json(200, _station_queue(model if model in ("A", "B") else None))
            except Exception as error:
                return self._json(500, {"error": str(error)})
        if path == "/api/station/results":
            try:
                return self._json(200, _station_results())
            except Exception as error:
                return self._json(500, {"error": str(error)})
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
        if path == "/api/station/answer":  # team tooling over teammates' on-disk data, ungated (see do_GET)
            try:
                return self._json(200, _station_save(body))
            except Exception as error:
                return self._json(400, {"error": str(error)})
        if path == "/api/voice/session":
            from . import voice
            try:
                return self._json(200, voice.start_session())
            except Exception as error:
                return self._json(502, {"error": str(error)})
        return self._json(404, {"error": "not found"})


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
    print(f"paste station on http://localhost:{port}/paste  (people: {PEOPLE_DIR.resolve()})")
    server.serve_forever()
