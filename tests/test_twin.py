# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_twin - the AI twin over HTTP: practice library, ask-your-own, kit IDs only with the workbench, rate limit (runner faked)

from __future__ import annotations

import json
import sys
import threading
import types
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from mefile import app, practice, runner

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture()
def calls(monkeypatch):
    """Fake the SDK and runner.ask: nothing goes over the wire; every question the twin was asked is recorded."""
    asked = []

    def fake_ask(client, profile, question, *args, **kwargs):
        asked.append({"profile": profile, "question": question})
        return {"text": f"answer to {question.id}", "model_served": "claude-fake-model"}

    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=lambda: object()))
    monkeypatch.setattr(runner, "ask", fake_ask)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-key")
    return asked


@pytest.fixture()
def base_url(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "LEDGER_DIR", tmp_path / "consent")
    monkeypatch.setattr(app, "_CONSENTS", {})
    monkeypatch.setattr(app, "_TWIN_CALLS", {})
    monkeypatch.setattr(app, "QUESTIONS_FILE", EXAMPLES / "example_questions.json")
    monkeypatch.delenv("LUMIN8R_WORKBENCH", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def call(base_url: str, method: str, path: str, body: dict | None = None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["X-Consent-Token"] = token
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def consent(base_url: str, purposes=("build_profile", "ai_processing"), person_id: str = "TWIN-01") -> str:
    status, payload = call(base_url, "POST", "/api/consent", {"person_id": person_id, "purposes": list(purposes)})
    assert status == 200
    return payload["consent_token"]


def kit_question_id() -> str:
    return json.loads((EXAMPLES / "example_questions.json").read_text(encoding="utf-8"))["questions"][0]["id"]


def test_questions_are_the_practice_library_in_product_mode(base_url, monkeypatch):
    status, payload = call(base_url, "GET", "/api/twin/questions")
    assert status == 200 and set(payload) == {"practice"}
    assert [item["id"] for item in payload["practice"]] == [f"P{n:02d}" for n in range(1, 21)]
    assert payload["practice"] == practice.library_json()
    monkeypatch.setenv("LUMIN8R_WORKBENCH", "1")
    status, payload = call(base_url, "GET", "/api/twin/questions")
    assert set(payload) == {"practice", "evaluation"}
    assert kit_question_id() in {item["id"] for item in payload["evaluation"]}


def test_practice_question(base_url, calls):
    token = consent(base_url)
    status, payload = call(base_url, "POST", "/api/twin", {"markdown": "# me.md", "question_id": "P01"}, token)
    assert status == 200
    assert payload["text"] == "answer to P01" and payload["model"] == "claude-fake-model"
    assert payload["question"] == {"id": "P01", "type": "scenario", "prompt": practice.prompt_for(practice.BY_ID["P01"]),
                                   "word_limit": practice.SCENARIO_LIMIT}
    assert calls[0]["profile"] == "# me.md"
    status, payload = call(base_url, "POST", "/api/twin", {"markdown": "# me.md", "question_id": "P13"}, token)
    assert status == 200 and payload["question"]["type"] == "writing" and payload["question"]["word_limit"] == practice.WRITING_LIMIT


def test_own_question_both_kinds(base_url, calls):
    token = consent(base_url)
    body = {"markdown": "# me.md", "own_question": "  My manager wants a status update every day.  "}
    status, payload = call(base_url, "POST", "/api/twin", body, token)
    assert status == 200
    assert payload["question"]["id"] == "OWN" and payload["question"]["type"] == "open"
    assert payload["question"]["prompt"].endswith("My manager wants a status update every day.")
    status, payload = call(base_url, "POST", "/api/twin", {**body, "kind": "message"}, token)
    assert status == 200 and payload["question"]["type"] == "writing"
    assert payload["question"]["word_limit"] == practice.WRITING_LIMIT
    assert [c["question"].id for c in calls] == ["OWN", "OWN"]


@pytest.mark.parametrize("body, fragment", [
    ({"own_question": "   "}, "write a situation first"),
    ({"own_question": "x" * (practice.OWN_QUESTION_MAX_CHARS + 1)}, "under"),
    ({"own_question": "A real situation.", "kind": "essay"}, "kind"),
    ({"own_question": ["not", "text"]}, "write a situation first"),
    ({"question_id": "P99"}, "practice situation"),
    ({}, "practice situation"),
])
def test_bad_input_is_400(base_url, calls, body, fragment):
    token = consent(base_url)
    status, payload = call(base_url, "POST", "/api/twin", {"markdown": "# me.md", **body}, token)
    assert status == 400 and fragment in payload["error"]
    assert calls == []


def test_kit_ids_only_with_the_workbench(base_url, calls, monkeypatch):
    token = consent(base_url)
    body = {"markdown": "# me.md", "question_id": kit_question_id()}
    status, payload = call(base_url, "POST", "/api/twin", body, token)
    assert status == 400 and calls == []
    monkeypatch.setenv("LUMIN8R_WORKBENCH", "1")
    status, payload = call(base_url, "POST", "/api/twin", body, token)
    assert status == 200 and payload["question"]["id"] == kit_question_id()


def test_consent_gate_unchanged(base_url, calls):
    body = {"markdown": "# me.md", "question_id": "P01"}
    assert call(base_url, "POST", "/api/twin", body)[1] == {"error": "consent required", "purpose": "ai_processing"}
    token = consent(base_url, purposes=("build_profile",))
    assert call(base_url, "POST", "/api/twin", body, token)[0] == 403
    assert calls == []


def test_rate_limit_per_consent_token(base_url, calls, monkeypatch):
    monkeypatch.setattr(app, "TWIN_RATE_LIMIT", 2)
    token = consent(base_url)
    body = {"markdown": "# me.md", "question_id": "P02"}
    assert call(base_url, "POST", "/api/twin", body, token)[0] == 200
    assert call(base_url, "POST", "/api/twin", {"markdown": "# me.md", "question_id": "nope"}, token)[0] == 400  # not counted
    assert call(base_url, "POST", "/api/twin", body, token)[0] == 200
    status, payload = call(base_url, "POST", "/api/twin", body, token)
    assert status == 429 and "error" in payload
    other = consent(base_url, person_id="TWIN-02")
    assert call(base_url, "POST", "/api/twin", body, other)[0] == 200
    assert len(calls) == 3
