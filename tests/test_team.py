# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_team - the team hub over HTTP: the team-code gate, people, traversal refusals, final, judge, bundle, docs

from __future__ import annotations

import io
import json
import threading
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from mefile import app, team
from mefile.judge.backend import FakeJudgeBackend

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
BUILD = json.loads((EXAMPLES / "example_build_answers.json").read_text(encoding="utf-8"))
TEST = json.loads((EXAMPLES / "example_test_answers.json").read_text(encoding="utf-8"))
QUESTIONS = json.loads((EXAMPLES / "example_questions.json").read_text(encoding="utf-8"))
CODE = "correct horse battery"


class Client:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.cookie = ""
        self.forwarded_for = ""

    def call(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict | bytes, dict]:
        headers = {"Content-Type": "application/json"}
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.forwarded_for:
            headers["X-Forwarded-For"] = self.forwarded_for
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                status, raw, response_headers = response.status, response.read(), dict(response.headers)
        except urllib.error.HTTPError as error:
            status, raw, response_headers = error.code, error.read(), dict(error.headers)
        set_cookie = response_headers.get("Set-Cookie", "")
        if set_cookie.startswith(team.COOKIE_NAME + "="):
            self.cookie = set_cookie.split(";")[0]
        if "json" in response_headers.get("Content-Type", ""):
            return status, json.loads(raw), response_headers
        return status, raw, response_headers

    def get(self, path: str):
        return self.call("GET", path)

    def post(self, path: str, body: dict):
        return self.call("POST", path, body)


@pytest.fixture()
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "LEDGER_DIR", tmp_path / "consent")
    monkeypatch.setattr(team, "_LOGIN_FAILURES", {})
    monkeypatch.setenv("LUMIN8R_DATA", str(tmp_path / "data"))
    monkeypatch.setenv("MEFILE_PEOPLE_DIR", str(tmp_path / "people"))
    monkeypatch.setenv("MEFILE_QUESTIONS", str(EXAMPLES / "example_questions.json"))
    for name in ("LUMIN8R_TEAM_CODE", "LUMIN8R_REQUIRE_TEAM_CODE", "LUMIN8R_TEAM_NAME", "LUMIN8R_FINAL_VARIANT",
                 "MEFILE_VARIANTS", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    http_server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{http_server.server_address[1]}"
    finally:
        http_server.shutdown()
        http_server.server_close()


@pytest.fixture()
def coded(server, monkeypatch):
    monkeypatch.setenv("LUMIN8R_TEAM_CODE", CODE)
    return Client(server)


@pytest.fixture()
def member(coded):
    status, payload, _ = coded.post("/api/team/login", {"code": CODE})
    assert status == 200 and payload == {"ok": True}
    return coded


def upload_demo(client: Client) -> None:
    status, payload, _ = client.post("/api/team/people", {"code": "DEMO01", "build": BUILD, "test": TEST})
    assert status == 200, payload
    assert payload["saved"] is True


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def test_pages_route(server):
    client = Client(server)
    status, body, headers = client.get("/")
    assert status == 200 and headers["Content-Type"].startswith("text/html")
    assert b"/app" in body and b"/team" in body  # both doors, from home.html or the fallback
    status, body, _ = client.get("/app")
    assert status == 200 and body == (app.STATIC / "index.html").read_bytes()
    assert client.get("/team")[0] == 200


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def test_login_wrong_right_and_rate_limit(coded):
    status, payload, _ = coded.post("/api/team/login", {"code": "nope"})
    assert status == 401 and payload["error"]
    status, payload, headers = coded.post("/api/team/login", {"code": CODE})
    assert status == 200 and payload == {"ok": True}
    cookie = headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie and "Path=/" in cookie and "Secure" not in cookie
    assert CODE not in cookie
    other = Client(coded.base_url)
    other.forwarded_for = "203.0.113.9"
    for _ in range(team.LOGIN_FAILURE_LIMIT):
        assert other.post("/api/team/login", {"code": "wrong"})[0] == 401
    assert other.post("/api/team/login", {"code": "wrong"})[0] == 429
    assert other.post("/api/team/login", {"code": CODE})[0] == 429  # locked out even with the right code
    neighbour = Client(coded.base_url)
    neighbour.forwarded_for = "198.51.100.4, 203.0.113.9"  # first hop decides
    assert neighbour.post("/api/team/login", {"code": CODE})[0] == 200


def test_secure_cookie_behind_https(coded):
    request = urllib.request.Request(coded.base_url + "/api/team/login", data=json.dumps({"code": CODE}).encode(),
                                     headers={"Content-Type": "application/json", "X-Forwarded-Proto": "https"}, method="POST")
    with urllib.request.urlopen(request, timeout=10) as response:
        assert "Secure" in response.headers["Set-Cookie"]


def test_gated_route_401_then_200_with_cookie_and_logout(coded):
    status, payload, _ = coded.get("/api/team/people")
    assert status == 401 and payload == {"error": "team sign-in required"}
    assert coded.get("/api/station/queue")[0] == 401
    assert coded.get("/paste")[0] == 401
    assert coded.get("/api/team/me")[1] == {"signed_in": False, "mode": "code"}
    coded.post("/api/team/login", {"code": CODE})
    assert coded.get("/api/team/people")[0] == 200
    assert coded.get("/paste")[0] == 200
    assert coded.get("/api/team/me")[1] == {"signed_in": True, "mode": "code"}
    status, _, headers = coded.post("/api/team/logout", {})
    assert status == 200 and "Max-Age=0" in headers["Set-Cookie"]
    coded.cookie = ""
    assert coded.get("/api/team/people")[0] == 401
    coded.cookie = team.COOKIE_NAME + "=forged"
    assert coded.get("/api/team/people")[0] == 401


def test_require_team_code_without_code_is_503(server, monkeypatch):
    monkeypatch.setenv("LUMIN8R_REQUIRE_TEAM_CODE", "1")
    client = Client(server)
    for method, path in (("GET", "/api/team/people"), ("GET", "/api/team/me"), ("GET", "/api/station/queue"),
                         ("POST", "/api/team/login")):
        status, payload, _ = client.call(method, path, {} if method == "POST" else None)
        assert status == 503
        assert payload == {"error": team.UNCONFIGURED_MESSAGE}


def test_local_mode_is_open(server):
    client = Client(server)
    assert client.get("/api/team/me")[1] == {"signed_in": True, "mode": "local"}
    assert client.get("/api/team/people")[0] == 200


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------


def test_upload_then_list_then_delete(member, tmp_path):
    upload_demo(member)
    assert (tmp_path / "people" / "DEMO01" / "build.json").exists()
    status, payload, _ = member.get("/api/team/people")
    assert status == 200
    person = next(p for p in payload["people"] if p["code"] == "DEMO01")
    assert person["has_build"] and person["has_test"]
    assert person["pasted"] == {"A": 0, "B": 0}
    assert person["total_runs"] == 2 * (1 + len(payload["variants"])) * len(payload["questions"])
    assert {"id": "S02", "type": "scenario"} in payload["questions"]
    status, payload, _ = member.post("/api/team/people/delete", {"code": "DEMO01"})
    assert status == 200 and payload == {"deleted": True}
    assert not (tmp_path / "people" / "DEMO01").exists()


def test_upload_refusals(member, tmp_path):
    leaked = json.loads(json.dumps(BUILD))
    leaked["scenarios"].append({"id": "S02", "choice": "B", "explanation": "leak"})
    status, payload, _ = member.post("/api/team/people", {"code": "DEMO01", "build": leaked})
    assert status == 400 and "S02" in payload["error"]
    test_with_build = json.loads(json.dumps(TEST))
    test_with_build["scenarios"].append({"id": "S01", "choice": "A", "explanation": "build id"})
    assert member.post("/api/team/people", {"code": "DEMO01", "build": BUILD, "test": test_with_build})[0] == 400
    assert member.post("/api/team/people", {"code": "OTHER1", "build": BUILD})[0] == 400  # code != person_id
    for bad in ("../evil", "x", "a/b", "..", "DEMO01/../../x"):
        status, _, _ = member.post("/api/team/people", {"code": bad, "build": {**BUILD, "person_id": bad}})
        assert status == 400
        assert member.post("/api/team/people/delete", {"code": bad})[0] == 400
    assert not (tmp_path / "people").exists() or not any((tmp_path / "people").iterdir())


# ---------------------------------------------------------------------------
# Traversal on files and docs
# ---------------------------------------------------------------------------


def test_traversal_refused_on_files_and_docs(member, tmp_path):
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "secret.txt").write_text("secret", encoding="utf-8")
    (tmp_path / "data" / "team" / "keys").mkdir(parents=True)
    (tmp_path / "data" / "team" / "keys" / "ratesheet_key.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "team" / "ok.txt").write_text("fine", encoding="utf-8")
    assert member.get("/api/team/files/ok.txt")[:2] == (200, b"fine")
    for path in ("/api/team/files/..", "/api/team/files/../secret.txt", "/api/team/files/..%2Fsecret.txt",
                 "/api/team/files/%2e%2e%2fsecret.txt", "/api/team/files/keys/ratesheet_key.json", "/api/team/files/.",
                 "/api/team/files/", "/api/team/docs/../CLAUDE", "/api/team/docs/..%2F..%2FCLAUDE",
                 "/api/team/docs/team-hub-contract", "/api/team/docs/strategy.md"):
        status, body, _ = member.get(path)
        assert status in (400, 404), path
        assert b"secret" not in (body if isinstance(body, bytes) else json.dumps(body).encode())


def test_docs_list_and_fetch(member):
    status, payload, _ = member.get("/api/team/docs")
    assert status == 200
    names = [d["name"] for d in payload["docs"]]
    assert "strategy" in names and "team-hub-contract" not in names
    assert all(d["title"] for d in payload["docs"])
    status, payload, _ = member.get("/api/team/docs/strategy")
    assert status == 200 and payload["name"] == "strategy" and payload["markdown"].startswith("#")


# ---------------------------------------------------------------------------
# Run (LLM A through the API, faked)
# ---------------------------------------------------------------------------


def test_run_answers_missing_llm_a_with_fake_answerer(member, monkeypatch, tmp_path):
    upload_demo(member)
    assert member.post("/api/team/run", {"model": "A", "use_api": True})[0] == 503  # no key
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-key")
    from mefile.experiment import fake_answerer
    monkeypatch.setattr(team, "api_answerer", lambda: fake_answerer)
    status, payload, _ = member.post("/api/team/run", {"model": "A", "use_api": True})
    assert status == 200 and payload["errors"] == [] and payload["answered"] > 0
    saved = json.loads((tmp_path / "people" / "DEMO01" / "llm_a.json").read_text(encoding="utf-8"))
    assert len(saved["responses"]) == payload["answered"]
    assert member.post("/api/team/run", {"model": "A"})[1] == {"answered": 0, "errors": []}
    assert member.post("/api/team/run", {"model": "B"})[0] == 400


def test_experiment_judge_503_without_key(member):
    upload_demo(member)
    status, payload, _ = member.post("/api/team/experiment", {"judge": True})
    assert status == 503 and "ANTHROPIC_API_KEY" in payload["error"]
    status, payload, _ = member.post("/api/team/experiment", {"judge": False})
    assert status == 200 and payload["results_md"].startswith("# Experiment results")
    assert member.get("/api/team/results")[1]["results_md"] == payload["results_md"]


# ---------------------------------------------------------------------------
# Final
# ---------------------------------------------------------------------------


def test_final_inputs_answer_judge_bundle(member, monkeypatch, tmp_path):
    status, payload, _ = member.post("/api/team/final/inputs", {"build": BUILD, "questions": QUESTIONS})
    assert status == 200, payload
    assert payload["gate"]["passed"] is True and payload["markdown"]
    run_ids = [r["run_id"] for r in payload["runs"]]
    assert "TEAM-A-S02" in run_ids and "TEAM-B-S02" in run_ids and len(run_ids) == 2 * len(QUESTIONS["questions"])
    assert {"id", "type", "prompt", "word_limit"} <= set(payload["questions"][0])

    leaked = json.loads(json.dumps(BUILD))
    leaked["writing"].append({"id": "W02", "text": "leak"})
    assert member.post("/api/team/final/inputs", {"build": leaked, "questions": QUESTIONS})[0] == 400

    status, payload, _ = member.post("/api/team/final/answer", {"run_id": "TEAM-A-S02", "text": "B. A short call settles it."})
    assert status == 200 and payload["saved"] is True
    assert member.post("/api/team/final/answer", {"run_id": "TEAM-A-../x", "text": "no"})[0] == 400
    saved = json.loads((tmp_path / "data" / "final" / "responses.json").read_text(encoding="utf-8"))
    assert saved["responses"] == [{"run_id": "TEAM-A-S02", "question_id": "S02", "text": "B. A short call settles it."}]
    state = member.get("/api/team/final")[1]
    assert state["markdown"] and state["evaluations_ready"] is False
    assert next(r for r in state["runs"] if r["run_id"] == "TEAM-A-S02")["answer"].startswith("B.")

    comparisons = {"responses": [{"run_id": "CMP-1-S02", "question_id": "S02", "text": "A. Point by point."},
                                 {"run_id": "CMP-1-W02", "question_id": "W02", "text": "Hi, I covered the report for you."}]}
    status, payload, _ = member.post("/api/team/final/judge", {"test": TEST, "comparisons": comparisons})
    assert status == 503  # no key: no judge
    monkeypatch.setattr(team, "judge_backend", lambda: FakeJudgeBackend())
    status, payload, _ = member.post("/api/team/final/judge", {"test": TEST, "comparisons": comparisons})
    assert status == 200, payload
    assert payload["counts"] == {"ok": 3, "judge_error": 0}
    assert payload["evaluations_md"].startswith("# AI judge evaluations")
    assert member.get("/api/team/final")[1]["evaluations_ready"] is True

    status, body, headers = member.get("/api/team/final/bundle")
    assert status == 200 and headers["Content-Type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        names = set(archive.namelist())
        assert {"me.md", "responses.json", "evaluations.json", "evaluations.md"} <= names
        assert archive.read("me.md").decode("utf-8") == state["markdown"]


def test_judge_config_error_is_503(member, monkeypatch):
    from mefile import runner
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-key")
    monkeypatch.setenv("MEFILE_JUDGE_MODEL", runner.DEFAULT_MODEL)
    monkeypatch.delenv("MEFILE_ALLOW_SELF_JUDGE", raising=False)
    upload_demo(member)
    status, payload, _ = member.post("/api/team/experiment", {"judge": True})
    assert status == 503 and "MEFILE_JUDGE_MODEL" in payload["error"]


def test_ratesheet_and_agreement(member, monkeypatch, tmp_path):
    upload_demo(member)
    assert member.post("/api/team/ratesheet", {})[0] == 409  # nothing pasted yet
    member.post("/api/station/answer", {"run_id": "DEMO01-B-none-S02", "text": "B. A call is faster."})
    member.post("/api/station/answer", {"run_id": "DEMO01-A-none-W02", "text": "Hey, I covered it; flag it next time?"})
    status, payload, _ = member.post("/api/team/ratesheet", {})
    assert status == 200 and payload == {"url": "/api/team/files/ratesheet.html"}
    status, body, _ = member.get(payload["url"])
    assert status == 200 and b"item-001" in body and b"DEMO01-B-none-S02" not in body
    monkeypatch.setattr(team, "judge_backend", lambda: FakeJudgeBackend())
    assert member.post("/api/team/experiment", {"judge": True})[0] == 200
    key = json.loads((tmp_path / "data" / "team" / "keys" / "ratesheet_key.json").read_text(encoding="utf-8"))
    ratings = {"rater": "Rater One", "ratings": [{"item_id": item_id, "score": 2, "note": ""} for item_id in key]}
    status, payload, _ = member.post("/api/team/agreement", {"ratings": [ratings]})
    assert status == 200, payload
    assert "Rater One" in payload["agreement_md"]
