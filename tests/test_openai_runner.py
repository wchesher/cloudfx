# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_openai_runner - LLM B on the OpenAI Responses API: the two-turn protocol shape, loud errors, experiment and CLI wiring

from __future__ import annotations

import io
import json
import shutil
import urllib.error
from pathlib import Path

import pytest

from mefile import cli, openai_runner
from mefile.answers import load_questions
from mefile.experiment import openai_answerer, run_experiment

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
QUESTIONS = load_questions(EXAMPLES / "example_questions.json")
FAKE_KEY = "sk-proj-FAKE-openai-test-key-13579"
MODEL = "gpt-test-model-id"


def completed(text: str, model: str = "gpt-test-model-id-2026-11-01") -> dict:
    return {"id": "resp_test", "object": "response", "status": "completed", "model": model,
            "output": [{"type": "reasoning", "summary": []},
                       {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]}]}


class FakeOpenAI:
    """Stands in for urllib's urlopen: records every request, answers from a script (dicts or HTTPError codes)."""

    def __init__(self, replies=None, default=None):
        self.replies = list(replies or [])
        self.default = default
        self.requests: list[dict] = []

    def __call__(self, request, timeout=None):
        assert request.full_url == openai_runner.API_URL and request.get_method() == "POST"
        self.requests.append({"payload": json.loads(request.data.decode("utf-8")),
                              "authorization": request.get_header("Authorization")})
        reply = self.replies.pop(0) if self.replies else self.default
        if callable(reply):
            reply = reply(self.requests[-1]["payload"])
        if isinstance(reply, tuple):  # (status, error body)
            status, body = reply
            raise urllib.error.HTTPError(request.full_url, status, "error", {}, io.BytesIO(json.dumps(body).encode("utf-8")))
        return io.BytesIO(json.dumps(reply).encode("utf-8"))


@pytest.fixture()
def configured(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("MEFILE_LLM_B_MODEL", MODEL)
    monkeypatch.delenv("MEFILE_LLM_B_EFFORT", raising=False)
    monkeypatch.setattr(openai_runner.time, "sleep", lambda seconds: None)


def install(monkeypatch, fake: FakeOpenAI) -> FakeOpenAI:
    monkeypatch.setattr(openai_runner, "urlopen", fake)
    return fake


# ---------------------------------------------------------------------------
# The protocol shape
# ---------------------------------------------------------------------------


def test_two_turn_protocol_shape(configured, monkeypatch):
    fake = install(monkeypatch, FakeOpenAI([completed("Ready."), completed("B. A short call settles it.")]))
    question = QUESTIONS["S02"]
    record = openai_runner.ask("# me.md\nthe whole profile", question)
    assert record == {"text": "B. A short call settles it.", "first_reply": "Ready.", "model_requested": MODEL,
                      "model_served": "gpt-test-model-id-2026-11-01", "effort": "medium"}
    first, second = (r["payload"] for r in fake.requests)
    assert first["input"] == [{"role": "user", "content": "# me.md\nthe whole profile"}]
    assert second["input"] == [{"role": "user", "content": "# me.md\nthe whole profile"},
                               {"role": "assistant", "content": "Ready."},
                               {"role": "user", "content": question.prompt}]  # verbatim
    for payload in (first, second):
        assert payload["model"] == MODEL and payload["store"] is False
        assert payload["reasoning"] == {"effort": "medium"} and payload["max_output_tokens"] >= 16000
        assert "instructions" not in payload and "previous_response_id" not in payload
        assert all(message["role"] in ("user", "assistant") for message in payload["input"])  # no system or developer
    assert all(r["authorization"] == f"Bearer {FAKE_KEY}" for r in fake.requests)
    assert "id" not in record and "resp_test" not in json.dumps(record)  # the response id is not stored


def test_no_profile_is_the_question_alone(configured, monkeypatch):
    fake = install(monkeypatch, FakeOpenAI([completed("D. Walk-away clause.")]))
    monkeypatch.setenv("MEFILE_LLM_B_EFFORT", "high")
    record = openai_runner.ask(None, QUESTIONS["S04"])
    assert len(fake.requests) == 1
    assert fake.requests[0]["payload"]["input"] == [{"role": "user", "content": QUESTIONS["S04"].prompt}]
    assert fake.requests[0]["payload"]["reasoning"] == {"effort": "high"}
    assert record["first_reply"] is None and record["effort"] == "high"


# ---------------------------------------------------------------------------
# Loud failures, never the key
# ---------------------------------------------------------------------------


def test_missing_model_environment_is_a_clear_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)
    monkeypatch.delenv("MEFILE_LLM_B_MODEL", raising=False)
    with pytest.raises(openai_runner.NotConfigured) as caught:
        openai_runner.ask(None, QUESTIONS["S02"])
    assert str(caught.value) == "set MEFILE_LLM_B_MODEL to the model id exactly as OpenAI lists it"
    assert openai_runner.configured() is False
    assert openai_runner.status() == {"configured": False, "model": None, "effort": "medium", "missing": ["MEFILE_LLM_B_MODEL"]}


def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MEFILE_LLM_B_MODEL", MODEL)
    with pytest.raises(openai_runner.NotConfigured, match="OPENAI_API_KEY"):
        openai_runner.ask(None, QUESTIONS["S02"])


@pytest.mark.parametrize("response, words", [
    ({"status": "incomplete", "model": MODEL, "incomplete_details": {"reason": "max_output_tokens"}, "output": []},
     "max_output_tokens"),
    ({"status": "incomplete", "model": MODEL, "incomplete_details": {"reason": "content_filter"}, "output": []},
     "content_filter"),
    ({"status": "completed", "model": MODEL, "output": [{"type": "message", "role": "assistant",
                                                          "content": [{"type": "refusal", "refusal": "I can't help."}]}]},
     "declined"),
    ({"status": "completed", "model": MODEL, "output": [{"type": "message", "role": "assistant",
                                                          "content": [{"type": "output_text", "text": "   "}]}]},
     "no text"),
    ({"status": "completed", "model": MODEL, "output": [{"type": "reasoning", "summary": []}]}, "no text"),
    ({"status": "failed", "model": MODEL, "error": {"message": "server trouble"}, "output": []}, "status failed"),
])
def test_unusable_replies_raise(configured, monkeypatch, response, words):
    install(monkeypatch, FakeOpenAI([response]))
    with pytest.raises(openai_runner.OpenAIRunError, match=words):
        openai_runner.ask(None, QUESTIONS["S02"])


def test_http_error_never_carries_the_key(configured, monkeypatch):
    echoed = {"error": {"type": "invalid_request_error", "code": "invalid_api_key",
                        "message": f"Incorrect API key provided: {FAKE_KEY}. Also sk-proj-FAKE****1357."}}
    install(monkeypatch, FakeOpenAI([(401, echoed)]))
    with pytest.raises(openai_runner.OpenAIRunError) as caught:
        openai_runner.ask(None, QUESTIONS["S02"])
    message = str(caught.value)
    assert "HTTP 401" in message and "invalid_request_error" in message
    assert FAKE_KEY not in message and "sk-" not in message


def test_retries_once_on_429_and_5xx(configured, monkeypatch):
    fake = install(monkeypatch, FakeOpenAI([(429, {"error": {"message": "slow down"}}), completed("C. Fine.")]))
    assert openai_runner.ask(None, QUESTIONS["S06"])["text"] == "C. Fine."
    assert len(fake.requests) == 2
    fake = install(monkeypatch, FakeOpenAI([(503, {}), (503, {}), completed("never reached")]))
    with pytest.raises(openai_runner.OpenAIRunError, match="HTTP 503"):
        openai_runner.ask(None, QUESTIONS["S06"])
    assert len(fake.requests) == 2  # one retry, not more
    fake = install(monkeypatch, FakeOpenAI([(400, {"error": {"message": "bad"}}), completed("never reached")]))
    with pytest.raises(openai_runner.OpenAIRunError, match="HTTP 400"):
        openai_runner.ask(None, QUESTIONS["S06"])
    assert len(fake.requests) == 1  # a 4xx other than 429 is not retried


# ---------------------------------------------------------------------------
# The experiment and the command line
# ---------------------------------------------------------------------------


def _people(tmp_path: Path) -> Path:
    person = tmp_path / "people" / "DEMO01"
    person.mkdir(parents=True)
    shutil.copy(EXAMPLES / "example_build_answers.json", person / "build.json")
    shutil.copy(EXAMPLES / "example_test_answers.json", person / "test.json")
    return tmp_path / "people"


PROMPTS = {question.prompt for question in QUESTIONS.values()}


def _answer_by_turn(payload: dict) -> dict:
    """B. to a question turn (with or without a profile before it); Ready. to the profile turn."""
    return completed("B. A short call." if payload["input"][-1]["content"] in PROMPTS else "Ready.")


def test_experiment_uses_llm_b_api_when_given(configured, monkeypatch, tmp_path):
    people = _people(tmp_path)
    pasted = {"responses": [{"run_id": "DEMO01-B-none-S04", "question_id": "S04", "text": "D. pasted by a person"}]}
    (people / "DEMO01" / "llm_b.json").write_text(json.dumps(pasted))
    fake = install(monkeypatch, FakeOpenAI(default=_answer_by_turn))
    result = run_experiment(people, QUESTIONS, ["evidence_first"], tmp_path / "out", None, answerer_b=openai_answerer())
    rows = [r for r in result["rows"] if r["model"] == "B"]
    assert len(rows) == 2 * len(QUESTIONS)  # none + evidence_first, every question, all by API
    assert all(r["source"] == "api" and r["model_served"] == "gpt-test-model-id-2026-11-01" for r in rows)
    assert all(r["text"] == "B. A short call." for r in rows)
    assert not (tmp_path / "out" / "DEMO01" / "PASTE_SHEET_LLM_B.md").exists()
    assert (tmp_path / "out" / "DEMO01" / "PASTE_SHEET_LLM_A.md").exists()  # LLM A stays on paste here
    assert json.loads((people / "DEMO01" / "llm_b.json").read_text()) == pasted  # the person's paste is untouched
    assert len(fake.requests) == len(QUESTIONS) + 2 * len(QUESTIONS)  # no-profile: one call; profile: two calls


def test_experiment_pastes_llm_b_otherwise(tmp_path):
    people = _people(tmp_path)
    (people / "DEMO01" / "llm_b.json").write_text(json.dumps({"responses": [
        {"run_id": "DEMO01-B-none-S04", "question_id": "S04", "text": "D. Walk-away clause."}]}))
    result = run_experiment(people, QUESTIONS, ["evidence_first"], tmp_path / "out", None)
    rows = [r for r in result["rows"] if r["model"] == "B"]
    assert [r["text"] for r in rows] == ["D. Walk-away clause."] and "source" not in rows[0]
    assert (tmp_path / "out" / "DEMO01" / "PASTE_SHEET_LLM_B.md").exists()


def test_cli_experiment_picks_api_when_configured_and_says_so(configured, monkeypatch, tmp_path, capsys):
    people = _people(tmp_path)
    install(monkeypatch, FakeOpenAI(default=_answer_by_turn))
    code = cli.main(["experiment", "--manual", "--people", str(people), "--variants", "evidence_first",
                     "--out", str(tmp_path / "out")])
    out = capsys.readouterr().out
    assert code == 0 and f"LLM B: OpenAI API, model {MODEL}, effort medium" in out
    assert "PASTE_SHEET_LLM_A.md;" in out and "PASTE_SHEET_LLM_B.md" not in out
    rows = json.loads((tmp_path / "out" / "results.json").read_text())["rows"]
    assert {r["model"] for r in rows} == {"B"} and all(r["source"] == "api" for r in rows)


def test_cli_experiment_defaults_to_paste_without_settings(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MEFILE_LLM_B_MODEL", raising=False)
    monkeypatch.setattr(openai_runner, "urlopen", lambda *a, **k: pytest.fail("no API call in paste mode"))
    people = _people(tmp_path)
    assert cli.main(["experiment", "--manual", "--people", str(people), "--variants", "evidence_first",
                     "--out", str(tmp_path / "out")]) == 0
    assert "LLM B: paste by hand" in capsys.readouterr().out
    assert (tmp_path / "out" / "DEMO01" / "PASTE_SHEET_LLM_B.md").exists()
    # forcing api without a model id fails loudly before anything runs
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)
    assert cli.main(["experiment", "--manual", "--llm-b", "api", "--people", str(people), "--out", str(tmp_path / "o2")]) == 2
    assert "set MEFILE_LLM_B_MODEL to the model id exactly as OpenAI lists it" in capsys.readouterr().out


def test_cli_final_fills_llm_b_by_api(configured, monkeypatch, tmp_path, capsys):
    fake = install(monkeypatch, FakeOpenAI(default=_answer_by_turn))
    out = tmp_path / "final"
    code = cli.main(["final", str(EXAMPLES / "example_build_answers.json"), str(EXAMPLES / "example_questions.json"),
                     "--out", str(out), "--team", "TEAMX"])
    assert code == 0 and "LLM B: OpenAI API" in capsys.readouterr().out
    template = {r["run_id"]: r["text"] for r in json.loads((out / "responses_template.json").read_text())["responses"]}
    assert all(template[f"TEAMX-B-{q}"] == "B. A short call." for q in QUESTIONS)
    assert all(template[f"TEAMX-A-{q}"] == "" for q in QUESTIONS)  # LLM A is still pasted
    provenance = json.loads((out / "responses_llm_b.json").read_text())["provenance"]
    assert {p["model_served"] for p in provenance} == {"gpt-test-model-id-2026-11-01"}
    me = (out / "me.md").read_text(encoding="utf-8")
    assert all(r["payload"]["input"][0]["content"] == me for r in fake.requests)  # the full me.md is message 1


def test_cli_run_llm_b(configured, monkeypatch, tmp_path):
    install(monkeypatch, FakeOpenAI(default=_answer_by_turn))
    target = tmp_path / "B.json"
    assert cli.main(["run", str(EXAMPLES / "example_questions.json"), "--llm", "B", "--prefix", "B", "--out", str(target)]) == 0
    data = json.loads(target.read_text())
    assert [r["run_id"] for r in data["responses"]] == [f"B-{q}" for q in QUESTIONS]
    assert all(p["model_requested"] == MODEL and p["condition"] == "no_profile" for p in data["provenance"])
