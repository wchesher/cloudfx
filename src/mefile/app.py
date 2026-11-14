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
``build_profile``, /api/twin ``ai_processing``, /api/voice/session, /api/voice/transcript and
/api/voice/plaud ``voice_interview``; the token travels in the ``X-Consent-Token`` header or a
``consent_token`` body field (header only on GET), and anything else is
403 ``{"error": "consent required", "purpose": ...}``. /api/withdraw revokes the token and every
other token for that person code. A server restart forgets every token, so the page must consent
again: failing toward "ask again" is the safe direction.

Endpoints
  GET  /                      the public front door (static/home.html)
  GET  /app                   the employee bench, the single-page app (static/index.html)
  GET  /s/<id>                a shared profile (static/share.html); the page fetches /api/shares/<id> and decrypts with the #key
  GET  /privacy, /responsible-use   the public policy pages (static/privacy.html, static/responsible-use.html)
  POST /api/shares            [build_profile] {ciphertext, iv, version, purpose, recipient_label, expires_at} -> 201 {id, manage_token, url_path}
  GET  /api/shares/<id>       200 the stored ciphertext and its metadata while live; 410 revoked or expired; 404 unknown
  DELETE /api/shares/<id>     X-Manage-Token: revoke (ciphertext deleted, tombstone kept); 403 wrong token (shares.py)
  GET  /workbench             the hackathon workbench (static/team.html), only with LUMIN8R_WORKBENCH=1; /team redirects there
  GET  /kit                   take the Common Kit (static/kit.html, with the kit data from kit.py injected); out come build.json and test.json
  GET  /api/example           the fictional DEMO01 build file
  POST /api/consent           record consent  {person_id, purposes[], ai_services[], share_with[]} -> {receipt, consent_token}
  POST /api/withdraw          record withdrawal {person_id, consent_token?}; revokes the person's tokens
  POST /api/convert           [build_profile] {answers, scope, withhold[], disputed?: {claim_id: note}, voice?: transcript}
                              -> {markdown, sidecar, claims, gate, problems, answers}; voice is the transcript JSON of
                              any source (elevenlabs, plaud, typed), read by intake.parse_transcript and cited as V01...
                              claims: every claim (the owner's view, disputed ones included) with other_readings and disputed;
                              400 on an unknown or limit claim ID in disputed, or a note over converter.MAX_DISPUTE_NOTE characters
  GET  /api/twin/questions    {practice: [the practice library, practice.py]}; plus {evaluation: [kit questions]} with the workbench on
  POST /api/twin              [ai_processing] {markdown, question_id: "P01".."P20"} or {markdown, own_question, kind: "open"|"message"}
                              -> {text, model, question: {id, type, prompt, word_limit}}; kit question IDs only with the workbench on;
                              at most TWIN_RATE_LIMIT calls per consent token (or address) per hour, since each call spends API credit
  POST /api/voice/session     [voice_interview] {} -> {signed_url}; 503 when the agent records audio or skips auth
                              (voice.verify_agent), 502 when ElevenLabs fails or voice is not configured
  GET  /api/voice/transcript  [voice_interview, X-Consent-Token header] ?conversation_id=... -> the transcript plus
                              {deleted}: once status is "done" the conversation is deleted from ElevenLabs
  POST /api/voice/plaud       [voice_interview] {text, speaker?, person_id?}: no speaker -> {speakers: [{label, turns,
                              sample}]}; with speaker -> {transcript}. Stateless: nothing kept, nothing logged but the path
  GET  /api/voice/guide       [{key, question}]: the interview guide, so a typed interview asks the same questions
  GET  /interview             tell it in your own words: the optional interview, reviewed in the browser (static/interview.html)
  /paste, /api/station/*, /api/team/*   workbench tooling behind the team code (team.py, docs/team-hub-contract.md);
                              404 unless LUMIN8R_WORKBENCH=1, except /api/team/login, logout and me, which /admin uses
  GET  /admin                 the operator's console (static/admin.html); /api/admin/* behind the same team gate (admin.py)
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import secrets
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import admin, practice, shares, team
from .answers import parse_answers
from .converter import SHARE_SCOPES, convert

STATIC = Path(__file__).parent / "static"
EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
LEDGER_DIR = Path(os.environ.get("MEFILE_CONSENT_DIR", "consent"))
QUESTIONS_FILE = Path(os.environ.get("MEFILE_QUESTIONS", str(EXAMPLES / "example_questions.json")))
MAX_BODY = 512_000
PLAUD_PATH = "/api/voice/plaud"
PLAUD_MAX_BODY = 1_600_000  # 500 KB of transcript text (plaud.MAX_TEXT_BYTES) after JSON escaping, with room to spare

# Which consent purpose each gated endpoint needs. Team routes are absent: the team code gates them (team.py).
REQUIRED_PURPOSE = {"/api/convert": "build_profile", "/api/twin": "ai_processing", "/api/voice/session": "voice_interview",
                    "/api/voice/transcript": "voice_interview", PLAUD_PATH: "voice_interview",
                    "/api/shares": "build_profile"}
SHARE_API = "/api/shares/"
WORKBENCH_PAGES = ("/workbench", "/team")

TWIN_RATE_LIMIT = 30  # twin answers per consent token (or client address) per window
TWIN_RATE_WINDOW_SECONDS = 3600
_TWIN_CALLS: dict[str, deque] = {}
_TWIN_LOCK = threading.Lock()

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


def _token_person(token: str) -> str:
    with _CONSENTS_LOCK:
        record = _CONSENTS.get(_token_hash(token)) if token else None
    return record["person_id"] if record else ""


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
        if length > (PLAUD_MAX_BODY if self.path.split("?")[0] == PLAUD_PATH else MAX_BODY):
            raise ValueError("request too large")
        body = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(body, dict):
            raise ValueError("request body must be a JSON object")
        return body

    def _page(self, name: str, headers: dict[str, str] | None = None) -> None:
        target = STATIC / name
        body = target.read_bytes() if target.is_file() else _FALLBACK_PAGES.get(name, _FALLBACK_PAGES["home.html"])
        return self._send(200, body, "text/html; charset=utf-8", headers)

    def _client_address(self) -> str:
        forwarded = str(self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        return forwarded or self.client_address[0]

    def _team_request(self, path: str, body: dict) -> team.Request:
        from urllib.parse import urlparse
        return team.Request(
            method=self.command, path=path, query=urlparse(self.path).query, body=body,
            cookie_header=str(self.headers.get("Cookie") or ""), client_address=self._client_address(),
            https=str(self.headers.get("X-Forwarded-Proto") or "").lower() == "https")

    def _team(self, path: str, body: dict) -> None:
        return self._reply(team.handle(self._team_request(path, body)))

    def _admin(self, path: str, body: dict) -> None:
        return self._reply(admin.handle(self._team_request(path, body), LEDGER_DIR, ledger=_ledger_append))

    def _share_reply(self, call) -> None:
        try:
            status, payload = call()
        except shares.ShareError as error:
            return self._json(error.status, {"error": error.message})
        except Exception as error:  # the type only: never a body, a token or a ciphertext
            return self._json(500, {"error": f"share route failed: {type(error).__name__}"})
        return self._json(status, payload)

    def _share_id(self, path: str) -> str:
        return path[len(SHARE_API):]

    def _reply(self, reply: team.Reply) -> None:
        if reply.body is not None:
            return self._send(reply.status, reply.body, reply.content_type, reply.headers)
        return self._send(reply.status, json.dumps(reply.payload, ensure_ascii=False).encode("utf-8"), reply.content_type, reply.headers)

    def _consent_token(self, body: dict) -> str:
        return str(self.headers.get("X-Consent-Token") or body.get("consent_token") or "")

    def _twin(self, body: dict):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return self._json(503, {"error": "Your understudy needs an Anthropic API key on the server (ANTHROPIC_API_KEY)."})
        try:
            question = _twin_question(body)
        except ValueError as error:
            return self._json(400, {"error": str(error)})
        token = self._consent_token(body)
        if not _twin_rate_allows("token:" + _token_hash(token) if token else "address:" + self._client_address()):
            message = json.dumps({"error": "your understudy has rehearsed a lot this hour; try again later"}).encode("utf-8")
            return self._send(429, message, "application/json; charset=utf-8", {"Retry-After": str(TWIN_RATE_WINDOW_SECONDS)})
        try:
            return self._json(200, _twin_answer(str(body.get("markdown", ""))[:200_000], question))
        except ValueError as error:
            return self._json(400, {"error": str(error)})
        except Exception as error:  # report the reason, never the key
            return self._json(502, {"error": f"your understudy could not answer: {type(error).__name__}"})

    def _voice_transcript(self):
        """Fetch the transcript; once the conversation is done, delete it from ElevenLabs and say whether that worked."""
        from urllib.parse import parse_qs, urlparse
        from . import voice
        conversation_id = parse_qs(urlparse(self.path).query).get("conversation_id", [""])[0]
        try:
            transcript = voice.fetch_transcript(conversation_id)
        except ValueError as error:
            return self._json(400, {"error": str(error)})
        except Exception as error:  # surface the reason, never the key
            return self._json(502, {"error": str(error)})
        deleted = False
        if transcript.get("status") == "done":
            try:
                voice.delete_conversation(conversation_id)
                deleted = True
            except Exception as error:  # the transcript is still returned; the page says the deletion did not happen
                transcript["delete_error"] = str(error)
        transcript["deleted"] = deleted
        return self._json(200, transcript)

    def _plaud(self, body: dict):
        from . import plaud
        text, speaker = body.get("text"), body.get("speaker")
        try:
            if speaker in (None, ""):
                return self._json(200, {"speakers": plaud.speakers(text)})
            return self._json(200, {"transcript": plaud.to_transcript(text, str(speaker), str(body.get("person_id") or ""))})
        except plaud.PlaudFormatError as error:
            status = 413 if "over 500 KB" in str(error) else 400
            return self._json(status, {"error": str(error)})
        except Exception as error:  # the type only: never the transcript text
            return self._json(500, {"error": f"could not read the transcript: {type(error).__name__}"})

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            return self._page("home.html")
        if path in ("/app", "/index.html"):
            return self._page("index.html")
        if path in WORKBENCH_PAGES:
            if not team.workbench_enabled():
                return self._send(404, team.NOT_AVAILABLE_PAGE, "text/html; charset=utf-8")
            if path == "/team":
                return self._send(302, b"", "text/plain; charset=utf-8", {"Location": "/workbench"})
            return self._page("team.html")
        if path.startswith("/s/"):
            share_id = path[len("/s/"):].rstrip("/") if path.count("/") <= 3 else ""
            if not shares.valid_id(share_id):
                return self._send(404, _FALLBACK_PAGES["not_found"], "text/html; charset=utf-8")
            return self._page("share.html", {"X-Robots-Tag": "noindex, nofollow", "Referrer-Policy": "no-referrer"})
        if path == "/privacy":
            return self._page("privacy.html")
        if path == "/responsible-use":
            return self._page("responsible-use.html")
        if path.startswith(SHARE_API):
            return self._share_reply(lambda: (200, shares.read(self._share_id(path))))
        if path == "/admin":
            return self._page("admin.html")
        if admin.is_admin_path(path):
            return self._admin(path, {})
        if path == "/interview":  # optional: tell it in your own words (static/interview.html, behaviour in interview.js)
            return self._page("interview.html")
        if path in ("/assessment", "/kit"):  # /assessment is the product name; /kit stays as an alias for old links
            return self._send(200, _kit_page(), "text/html; charset=utf-8")
        if team.is_team_path(path):
            return self._team(path, {})
        if path.startswith("/static/") and path.count("/") == 2 and path.rsplit(".", 1)[-1] in ("css", "js", "svg"):
            target = STATIC / path.split("/")[-1]
            if target.is_file():
                kinds = {"css": "text/css", "js": "text/javascript", "svg": "image/svg+xml"}
                return self._send(200, target.read_bytes(), kinds[path.rsplit(".", 1)[-1]] + "; charset=utf-8")
            return self._json(404, {"error": "not found"})
        if path == "/api/twin/questions":
            payload = {"practice": practice.library_json()}
            if team.workbench_enabled():  # the kit's evaluation questions are team tooling, never the product's
                from .answers import load_questions
                payload["evaluation"] = [{"id": q.id, "type": q.type, "wording": q.wording, "prompt": q.prompt,
                                          "word_limit": q.word_limit} for q in load_questions(QUESTIONS_FILE).values()]
            return self._json(200, payload)
        if path == "/api/example":
            return self._send(200, (EXAMPLES / "example_build_answers.json").read_bytes(), "application/json")
        if path == "/api/config":
            from . import voice
            return self._json(200, {"scopes": SHARE_SCOPES, "voice_enabled": voice.configured(), "plaud_enabled": True,
                                    "twin_enabled": bool(os.environ.get("ANTHROPIC_API_KEY")),
                                    "workbench_enabled": team.workbench_enabled()})
        if path == "/api/voice/guide":
            from . import voice
            return self._json(200, [{"key": key, "question": question} for key, question in voice.INTERVIEW_GUIDE])
        if path == "/api/voice/transcript":
            if not _token_allows(str(self.headers.get("X-Consent-Token") or ""), REQUIRED_PURPOSE[path]):
                return self._json(403, {"error": "consent required", "purpose": REQUIRED_PURPOSE[path]})
            return self._voice_transcript()
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            body = self._body()
        except ValueError as error:
            return self._json(400, {"error": str(error)})
        if team.is_team_path(path):
            return self._team(path, body)
        if admin.is_admin_path(path):
            return self._admin(path, body)
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
            token = self._consent_token(body)
            # Only a holder of this person's own consent token can switch off their share links, so nobody can
            # revoke someone else's shares by guessing a person code.
            with _CONSENTS_LOCK:
                owns = bool(token) and _CONSENTS.get(_token_hash(token), {}).get("person_id") == person_id
            revoked = _revoke(person_id, token)
            shares_off = shares.revoke_person(person_id, _ledger_append) if owns else []
            entry = _ledger_append({"event": "withdrawal", "person_id": person_id, "revoked_token_sha256": revoked,
                                    "shares_revoked": len(shares_off)})
            return self._json(200, {"receipt": entry, "shares_revoked": len(shares_off)})
        if path == "/api/convert":
            answers = parse_answers(body.get("answers") or {})
            scope = body.get("scope", "full")
            try:
                voice = _voice_evidence(body.get("voice"))
                profile = convert(answers, scope=scope, excluded_domains=set(body.get("withhold") or []),
                                  disputed=body.get("disputed") or None, voice=voice)
            except ValueError as error:
                return self._json(400, {"error": str(error)})
            return self._json(200, {
                "markdown": profile.markdown,
                "sidecar": profile.sidecar,
                "claims": profile.claim_records(),
                "gate": {"passed": profile.gate.passed, "blocking": profile.gate.blocking, "warnings": profile.gate.warnings},
                "problems": answers.problems,
                "answers": answers.to_json(),
            })
        if path == "/api/shares":
            token = self._consent_token(body)
            return self._share_reply(lambda: (201, shares.create(body, _token_person(token), self._client_address(), _ledger_append)))
        if path == "/api/twin":
            return self._twin(body)
        if path == "/api/voice/session":
            from . import voice
            try:
                return self._json(200, voice.start_session())
            except voice.AgentNotSafe as error:
                return self._json(503, {"error": str(error)})
            except Exception as error:
                return self._json(502, {"error": str(error)})
        if path == PLAUD_PATH:
            return self._plaud(body)
        return self._json(404, {"error": "not found"})


    def do_DELETE(self):
        path = self.path.split("?")[0]
        if path.startswith(SHARE_API):
            manage_token = str(self.headers.get("X-Manage-Token") or "")
            return self._share_reply(lambda: (200, shares.revoke(self._share_id(path), manage_token, _ledger_append)))
        return self._json(404, {"error": "not found"})


def _fallback(title: str, text: str) -> bytes:
    return ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width, initial-scale=1'>"
            f"<title>{title}</title><main style='max-width:36rem;margin:4rem auto;padding:0 16px;font-family:system-ui'>"
            f"<h1>{title}</h1><p>{text}</p><p><a href=\"/\">Home</a></p></main>").encode("utf-8")


_FALLBACK_PAGES = {  # served only until the real page exists in static/
    "home.html": (b"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width, initial-scale=1'>"
                  b"<title>lumin8r</title><h1>lumin8r</h1><p><a href=\"/kit\">Take the assessment</a></p>"
                  b"<p><a href=\"/app\">Your file</a></p>"),
    "team.html": (b"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width, initial-scale=1'>"
                  b"<title>lumin8r team</title><h1>Team</h1><p>The team page is not built yet. <a href=\"/\">Home</a></p>"),
    "share.html": _fallback("Shared profile", "This page is being rebuilt. Open the link again in a few minutes."),
    "privacy.html": _fallback("Privacy", "This page is being rebuilt. Open it again in a few minutes."),
    "responsible-use.html": _fallback("Responsible use", "This page is being rebuilt. Open it again in a few minutes."),
    "not_found": _fallback("This link does not exist", "Check that you copied the whole link."),
}


KIT_DATA_TOKEN = "__KIT_DATA__"


def _voice_evidence(value):
    """The optional ``voice`` field of /api/convert: transcript JSON of any source -> VoiceEvidence, or None."""
    if value in (None, {}):
        return None
    if not isinstance(value, dict):
        raise ValueError("voice must be a transcript object")
    from .intake import parse_transcript
    return parse_transcript(value)


def _kit_page() -> bytes:
    """static/kit.html with the kit's own text injected at request time, so the page cannot drift from kit.py."""
    from . import kit
    data = {"version": kit.KIT_VERSION, "items": kit.ITEMS, "response_labels": kit.RESPONSE_LABELS,
            "scenarios": kit.SCENARIOS, "writing": kit.WRITING_PROMPTS, "scenario_word_limit": kit.SCENARIO_WORD_LIMIT,
            "writing_word_limit": kit.WRITING_WORD_LIMIT, "test_ids": sorted(kit.DEVELOPMENT_TEST_IDS)}
    embedded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")  # nothing in the data can close the script tag
    return (STATIC / "kit.html").read_text(encoding="utf-8").replace(KIT_DATA_TOKEN, embedded, 1).encode("utf-8")


def _twin_question(body: dict):
    """The question an understudy call answers: a practice situation, the person's own question, or (workbench only) a kit question."""
    own = body.get("own_question")
    if own is not None:
        kind = body.get("kind", "open")
        if kind not in ("open", "message"):
            raise ValueError('kind must be "open" or "message"')
        if not isinstance(own, str):
            raise ValueError("write a situation first")
        return practice.own_question(own, kind)
    question_id = str(body.get("question_id", ""))
    situation = practice.BY_ID.get(question_id)
    if situation is not None:
        return practice.as_question(situation)
    if question_id and team.workbench_enabled():
        from .answers import load_questions
        question = load_questions(QUESTIONS_FILE).get(question_id)
        if question is not None:
            return question
    raise ValueError("choose a practice situation (P01 to P20) or ask your own")


def _twin_rate_allows(key: str) -> bool:
    now = time.monotonic()
    with _TWIN_LOCK:
        calls = _TWIN_CALLS.setdefault(key, deque())
        while calls and now - calls[0] >= TWIN_RATE_WINDOW_SECONDS:
            calls.popleft()
        if len(calls) >= TWIN_RATE_LIMIT:
            return False
        calls.append(now)
        return True


def _twin_answer(markdown: str, question) -> dict:
    """Your understudy (Claude, an AI) answers ONE question as the person, through the official two-turn loading protocol."""
    from . import runner
    import anthropic
    result = runner.ask(anthropic.Anthropic(), markdown, question)
    return {"text": result["text"], "model": result["model_served"],
            "question": {"id": question.id, "type": question.type, "prompt": question.prompt, "word_limit": question.word_limit}}


def serve(port: int = 8080) -> None:
    # 127.0.0.1 by default; a container behind the shared docker edge sets LUMIN8R_BIND=0.0.0.0 (its port is published
    # only to the host's loopback and the edge network, never to the internet)
    server = ThreadingHTTPServer((os.environ.get("LUMIN8R_BIND", "127.0.0.1"), port), Handler)
    shares.start_sweeper()  # expired shares are deleted at startup and hourly (and on read)
    print(f"mefile app on http://localhost:{port}  (consent ledger: {LEDGER_DIR.resolve()}, shares: {shares.shares_dir().resolve()})")
    if team.workbench_enabled():
        print(f"workbench on http://localhost:{port}/workbench  (people: {team.people_dir().resolve()}, "
              f"data: {team.data_dir().resolve()}, team code: {team.gate_mode()})")
    else:
        print("workbench off (LUMIN8R_WORKBENCH=1 turns it on)")
    server.serve_forever()
