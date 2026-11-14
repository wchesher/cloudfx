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

Endpoints
  GET  /                      the single-page app
  GET  /api/example           the fictional DEMO01 build file
  POST /api/consent           record consent  {person_id, purposes[], ai_services[], share_with[]}
  POST /api/withdraw          record withdrawal {person_id}
  POST /api/convert           {answers, scope, withhold[]} -> {markdown, sidecar, claims, gate, problems}
  POST /api/voice/session     ElevenLabs signed URL for the voice interview (only when configured)
  GET  /api/voice/transcript  ?conversation_id=... -> transcript, employee turns only
"""

from __future__ import annotations

import datetime as dt
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .answers import parse_answers
from .converter import SHARE_SCOPES, convert

STATIC = Path(__file__).parent / "static"
EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
LEDGER_DIR = Path(os.environ.get("MEFILE_CONSENT_DIR", "consent"))
MAX_BODY = 512_000


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
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/example":
            return self._send(200, (EXAMPLES / "example_build_answers.json").read_bytes(), "application/json")
        if path == "/api/config":
            from . import voice
            return self._json(200, {"scopes": SHARE_SCOPES, "voice_enabled": voice.configured()})
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
        if path == "/api/consent":
            if not body.get("person_id") or not body.get("purposes"):
                return self._json(400, {"error": "person_id and at least one purpose are required"})
            entry = _ledger_append({"event": "consent", "person_id": body["person_id"], "purposes": body.get("purposes", []),
                                    "ai_services": body.get("ai_services", []), "share_with": body.get("share_with", [])})
            return self._json(200, {"receipt": entry})
        if path == "/api/withdraw":
            entry = _ledger_append({"event": "withdrawal", "person_id": body.get("person_id", "")})
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
        if path == "/api/voice/session":
            from . import voice
            try:
                return self._json(200, voice.start_session())
            except Exception as error:
                return self._json(502, {"error": str(error)})
        return self._json(404, {"error": "not found"})


def serve(port: int = 8080) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"mefile app on http://localhost:{port}  (consent ledger: {LEDGER_DIR.resolve()})")
    server.serve_forever()
