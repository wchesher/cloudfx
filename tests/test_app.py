# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_app - server-side consent enforcement over HTTP, and the judge self-judge guard

from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from mefile import app, runner

EXAMPLE_BUILD = Path(__file__).resolve().parents[1] / "examples" / "example_build_answers.json"


@pytest.fixture()
def base_url(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "LEDGER_DIR", tmp_path / "consent")
    monkeypatch.setattr(app, "_CONSENTS", {})
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def post(base_url: str, path: str, body: dict, token: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["X-Consent-Token"] = token
    request = urllib.request.Request(base_url + path, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def consent(base_url: str, purposes: list[str], person_id: str = "TEST-01") -> str:
    status, payload = post(base_url, "/api/consent", {"person_id": person_id, "purposes": purposes})
    assert status == 200
    return payload["consent_token"]


def example_convert_body() -> dict:
    return {"answers": json.loads(EXAMPLE_BUILD.read_text(encoding="utf-8")), "scope": "coaching"}


def test_convert_without_token_is_refused(base_url):
    status, payload = post(base_url, "/api/convert", example_convert_body())
    assert status == 403
    assert payload == {"error": "consent required", "purpose": "build_profile"}


def test_convert_with_unknown_token_is_refused(base_url):
    status, _ = post(base_url, "/api/convert", example_convert_body(), token="not-a-real-token")
    assert status == 403


def test_consent_then_convert_with_token(base_url, tmp_path):
    token = consent(base_url, ["build_profile"])
    status, payload = post(base_url, "/api/convert", example_convert_body(), token=token)
    assert status == 200
    assert payload["markdown"]
    # the body field works as well as the header
    status, _ = post(base_url, "/api/convert", {**example_convert_body(), "consent_token": token})
    assert status == 200
    ledger = (tmp_path / "consent" / "ledger.jsonl").read_text(encoding="utf-8")
    assert token not in ledger
    assert app._token_hash(token) in ledger


def test_withdraw_revokes_token(base_url, tmp_path):
    token = consent(base_url, ["build_profile"])
    assert post(base_url, "/api/convert", example_convert_body(), token=token)[0] == 200
    status, payload = post(base_url, "/api/withdraw", {"person_id": "TEST-01"}, token=token)
    assert status == 200
    assert payload["receipt"]["revoked_token_sha256"] == [app._token_hash(token)]
    status, payload = post(base_url, "/api/convert", example_convert_body(), token=token)
    assert status == 403
    assert payload["purpose"] == "build_profile"


def test_twin_requires_ai_processing(base_url, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    body = {"markdown": "# me.md", "question_id": "Q1"}
    token = consent(base_url, ["build_profile"])
    status, payload = post(base_url, "/api/twin", body, token=token)
    assert status == 403
    assert payload == {"error": "consent required", "purpose": "ai_processing"}
    # with the purpose granted the gate opens and the next check (no API key) answers
    token = consent(base_url, ["build_profile", "ai_processing"], person_id="TEST-02")
    assert post(base_url, "/api/twin", body, token=token)[0] == 503


def test_voice_session_requires_voice_interview(base_url):
    token = consent(base_url, ["build_profile"])
    status, payload = post(base_url, "/api/voice/session", {}, token=token)
    assert status == 403
    assert payload == {"error": "consent required", "purpose": "voice_interview"}


def test_judge_refuses_llm_a_model_without_override(monkeypatch):
    from mefile.judge.anthropic_backend import AnthropicJudgeBackend, JudgeConfigError

    monkeypatch.setitem(sys.modules, "anthropic", None)  # any import of the SDK now fails: construction must stay lazy
    monkeypatch.delenv("MEFILE_ALLOW_SELF_JUDGE", raising=False)
    with pytest.raises(JudgeConfigError, match="MEFILE_JUDGE_MODEL"):
        AnthropicJudgeBackend(model=runner.DEFAULT_MODEL)
    monkeypatch.setenv("MEFILE_JUDGE_MODEL", runner.DEFAULT_MODEL)
    with pytest.raises(JudgeConfigError):
        AnthropicJudgeBackend()
    assert AnthropicJudgeBackend(model=runner.DEFAULT_MODEL + "-other").model != runner.DEFAULT_MODEL
    monkeypatch.setenv("MEFILE_ALLOW_SELF_JUDGE", "1")
    assert AnthropicJudgeBackend(model=runner.DEFAULT_MODEL).model == runner.DEFAULT_MODEL
