# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_admin - the operator's console over HTTP: the team gate, no secrets out, consent ledger, data, purges, traversal

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from mefile import admin, app, team

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
BUILD = json.loads((EXAMPLES / "example_build_answers.json").read_text(encoding="utf-8"))
TEST = json.loads((EXAMPLES / "example_test_answers.json").read_text(encoding="utf-8"))
CODE = "correct horse battery"
FAKE_ANTHROPIC = "sk-ant-FAKE-anthropic-key-0123456789"
FAKE_ELEVEN = "xi-FAKE-elevenlabs-key-9876543210"
FAKE_AGENT = "agent-FAKE-id-5555"
FAKE_OPENAI = "sk-proj-FAKE-openai-key-24680"


class Client:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.cookie = ""

    def call(self, method: str, path: str, body: dict | None = None):
        headers = {"Content-Type": "application/json"}
        if self.cookie:
            headers["Cookie"] = self.cookie
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
        if response_headers.get("Content-Type", "").startswith("application/json"):
            return status, json.loads(raw), response_headers, raw
        return status, raw, response_headers, raw

    def get(self, path: str):
        return self.call("GET", path)

    def post(self, path: str, body: dict):
        return self.call("POST", path, body)


@pytest.fixture()
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "LEDGER_DIR", tmp_path / "data" / "consent")  # inside data, as on the box
    monkeypatch.setattr(team, "_LOGIN_FAILURES", {})
    monkeypatch.setenv("LUMIN8R_DATA", str(tmp_path / "data"))
    monkeypatch.setenv("MEFILE_PEOPLE_DIR", str(tmp_path / "data" / "people"))
    monkeypatch.setenv("MEFILE_QUESTIONS", str(EXAMPLES / "example_questions.json"))
    monkeypatch.setenv("LUMIN8R_WORKBENCH", "1")  # these tests drive the workbench (team API, paste station)
    for name in ("LUMIN8R_TEAM_CODE", "LUMIN8R_REQUIRE_TEAM_CODE", "LUMIN8R_TEAM_NAME", "LUMIN8R_FINAL_VARIANT",
                 "MEFILE_VARIANTS", "ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_AGENT_ID", "MEFILE_JUDGE_MODEL",
                 "LUMIN8R_RELEASE", "LUMIN8R_HOST", "MEFILE_ALLOW_SELF_JUDGE", "OPENAI_API_KEY", "MEFILE_LLM_B_MODEL",
                 "MEFILE_LLM_B_EFFORT"):
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
    status, payload, _, _ = coded.post("/api/team/login", {"code": CODE})
    assert status == 200 and payload == {"ok": True}
    return coded


def upload_demo(client: Client) -> None:
    status, payload, _, _ = client.post("/api/team/people", {"code": "DEMO01", "build": BUILD, "test": TEST})
    assert status == 200, payload


def consent(client: Client, person_id: str) -> str:
    status, payload, _, _ = client.post("/api/consent", {"person_id": person_id, "purposes": ["build_profile", "ai_processing"],
                                                         "ai_services": ["anthropic"], "share_with": []})
    assert status == 200
    return payload["consent_token"]


ADMIN_GETS = ("/api/admin/overview", "/api/admin/consent", "/api/admin/consent/export", "/api/admin/people", "/api/admin/settings")


# ---------------------------------------------------------------------------
# Page and gate
# ---------------------------------------------------------------------------


def test_admin_page_serves_signed_out(server):
    status, body, headers, _ = Client(server).get("/admin")
    assert status == 200 and headers["Content-Type"].startswith("text/html")
    assert body == (app.STATIC / "admin.html").read_bytes()
    assert b"/api/team/login" in body


def test_gate_401_signed_out_200_with_cookie(coded):
    for path in ADMIN_GETS:
        assert coded.get(path)[0] == 401, path
    assert coded.post("/api/admin/purge", {"scope": "people", "confirm": "DELETE PEOPLE"})[0] == 401
    assert coded.post("/api/admin/people/delete", {"code": "DEMO01"})[0] == 401
    coded.post("/api/team/login", {"code": CODE})
    for path in ADMIN_GETS:
        assert coded.get(path)[0] == 200, path
    coded.cookie = "lumin8r_team=forged"
    assert coded.get("/api/admin/overview")[0] == 401


def test_gate_503_when_required_and_unset(server, monkeypatch):
    monkeypatch.setenv("LUMIN8R_REQUIRE_TEAM_CODE", "1")
    client = Client(server)
    status, payload, _, _ = client.get("/api/admin/overview")
    assert status == 503 and "update-lumin8r --set-key LUMIN8R_TEAM_CODE" in payload["error"]
    assert client.post("/api/admin/purge", {"scope": "final", "confirm": "DELETE FINAL"})[0] == 503


def test_unknown_admin_route_is_404(member):
    assert member.get("/api/admin/nothing")[0] == 404
    assert member.post("/api/admin/overview", {})[0] == 404


# ---------------------------------------------------------------------------
# Health: never a secret
# ---------------------------------------------------------------------------


def test_overview_reports_without_secrets(member, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_ANTHROPIC)
    monkeypatch.setenv("ELEVENLABS_API_KEY", FAKE_ELEVEN)
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", FAKE_AGENT)
    monkeypatch.setenv("MEFILE_JUDGE_MODEL", "claude-judge-test-model")
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_OPENAI)
    monkeypatch.setenv("MEFILE_LLM_B_MODEL", "gpt-test-model-id")
    monkeypatch.setenv("LUMIN8R_RELEASE", "abc1234")
    monkeypatch.setenv("LUMIN8R_HOST", "microverse.cloud")
    token = consent(member, "P01")
    upload_demo(member)
    status, payload, _, raw = member.get("/api/admin/overview")
    assert status == 200
    for secret in (CODE, FAKE_ANTHROPIC, FAKE_ELEVEN, FAKE_AGENT, FAKE_OPENAI, token, team._cookie_value(CODE)):
        assert secret.encode("utf-8") not in raw, secret
    assert b"token_sha256" not in raw
    assert payload["release"] == "abc1234" and payload["host"] == "microverse.cloud"
    assert payload["keys"] == {"ANTHROPIC_API_KEY": True, "OPENAI_API_KEY": True, "ELEVENLABS_API_KEY": True,
                               "ELEVENLABS_AGENT_ID": True, "LUMIN8R_TEAM_CODE": True}
    assert payload["llm_b_api"] == {"configured": True, "model": "gpt-test-model-id", "effort": "medium", "missing": []}
    assert payload["judge_model"] == "claude-judge-test-model" and payload["judge_ready"] is True
    assert payload["twin_ready"] is True and payload["voice_ready"] is True
    assert payload["uptime_seconds"] >= 0 and payload["started_at"]
    assert payload["counts"]["people"] == 1 and payload["counts"]["consents_active"] == 1
    assert payload["settings"]["require_team_code"] is False
    for path in ("/api/admin/settings", "/api/admin/consent", "/api/admin/people"):
        body = member.get(path)[3]
        for secret in (CODE, FAKE_ANTHROPIC, FAKE_ELEVEN, FAKE_AGENT, FAKE_OPENAI, token):
            assert secret.encode("utf-8") not in body, (path, secret)


def test_overview_judge_not_ready_when_it_would_judge_itself(member, monkeypatch):
    from mefile import runner
    status, payload, _, _ = member.get("/api/admin/overview")
    assert payload["release"] == "unknown" and payload["judge_ready"] is False and payload["judge_model"] is None
    assert payload["keys"]["ANTHROPIC_API_KEY"] is False and payload["twin_ready"] is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_ANTHROPIC)
    monkeypatch.setenv("MEFILE_JUDGE_MODEL", runner.DEFAULT_MODEL)
    payload = member.get("/api/admin/overview")[1]
    assert payload["twin_ready"] is True and payload["judge_ready"] is False and "LLM A" in payload["judge_note"]


def test_settings_list_commands(member, monkeypatch):
    monkeypatch.setenv("LUMIN8R_TEAM_NAME", "Night's Watch")
    monkeypatch.setenv("MEFILE_JUDGE_MODEL", "claude-judge-test-model")
    rows = {r["name"]: r for r in member.get("/api/admin/settings")[1]["settings"]}
    assert rows["ANTHROPIC_API_KEY"]["command"] == "sudo update-lumin8r --set-key ANTHROPIC_API_KEY"
    assert rows["LUMIN8R_TEAM_CODE"]["value"] is None and rows["LUMIN8R_TEAM_CODE"]["set"] is True
    assert rows["MEFILE_JUDGE_MODEL"]["value"] == "claude-judge-test-model"
    assert rows["LUMIN8R_HOST"]["command"] == ("echo 'LUMIN8R_HOST=microverse.cloud' | sudo tee -a /etc/lumin8r/update.env"
                                               " && sudo update-lumin8r")
    for name in ("LUMIN8R_PORT", "MEFILE_VARIANTS", "LUMIN8R_FINAL_VARIANT"):
        assert rows[name]["command"].startswith(f"echo '{name}=")
    # a value with a space and a quote survives two rounds of shell quoting: bash reads it back exactly
    import subprocess
    command = rows["LUMIN8R_TEAM_NAME"]["command"]
    echoed = subprocess.run(["bash", "-c", command.split(" | ")[0]], capture_output=True, text=True, check=True).stdout
    sourced = subprocess.run(["bash", "-c", echoed + '\nprintf %s "$LUMIN8R_TEAM_NAME"'], capture_output=True, text=True,
                             check=True).stdout
    assert sourced == "Night's Watch"
    assert rows["LUMIN8R_RELEASE"]["command"] is None


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------


def test_consent_aggregation_and_export(member, tmp_path):
    first = consent(member, "P01")
    consent(member, "P02")
    status, _, _, _ = member.post("/api/withdraw", {"person_id": "P01", "consent_token": first})
    assert status == 200
    status, payload, _, raw = member.get("/api/admin/consent")
    assert status == 200 and payload["entries_total"] == 3
    people = {p["person_id"]: p for p in payload["people"]}
    assert people["P01"]["state"] == "withdrawn" and people["P01"]["events"] == 2
    assert people["P02"]["state"] == "active" and people["P02"]["purposes"] == ["build_profile", "ai_processing"]
    assert people["P02"]["ai_services"] == ["anthropic"] and people["P02"]["first_at"] and people["P02"]["last_at"]
    assert b"token_sha256" not in raw and first.encode() not in raw
    ledger = (tmp_path / "data" / "consent" / "ledger.jsonl").read_text(encoding="utf-8")
    assert "token_sha256" in ledger  # the ledger itself keeps its hashes; only the console's views drop them
    status, body, headers, _ = member.get("/api/admin/consent/export")
    assert status == 200 and headers["Content-Type"].startswith("application/x-ndjson")
    assert "attachment" in headers["Content-Disposition"]
    lines = [json.loads(line) for line in body.decode("utf-8").splitlines()]
    assert [line["event"] for line in lines] == ["consent", "consent", "withdrawal"]
    assert all(not key.endswith("token_sha256") for line in lines for key in line)
    assert (tmp_path / "data" / "consent" / "ledger.jsonl").read_text(encoding="utf-8") == ledger  # never edited


def test_consent_empty_and_unreadable_lines(member, tmp_path):
    payload = member.get("/api/admin/consent")[1]
    assert payload["people"] == [] and payload["entries_total"] == 0
    assert member.get("/api/admin/consent/export")[1] == b""
    consent(member, "P03")
    with (tmp_path / "data" / "consent" / "ledger.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("not json at all\n")
    payload = member.get("/api/admin/consent")[1]
    assert payload["entries_total"] == 1 and payload["unreadable_lines"] == 1


# ---------------------------------------------------------------------------
# Data on the box
# ---------------------------------------------------------------------------


def test_people_listing_after_demo_upload(member, tmp_path):
    assert member.get("/api/admin/people")[1]["people"] == []
    upload_demo(member)
    member.post("/api/station/answer", {"run_id": "DEMO01-B-none-S02", "text": "B. A call.", "model_shown": "GPT Sol 6.1"})
    member.post("/api/station/answer", {"run_id": "DEMO01-A-none-S02", "text": "B."})
    (tmp_path / "data" / "people" / "DEMO01" / "voice_transcript.json").write_text("{}", encoding="utf-8")
    payload = member.get("/api/admin/people")[1]
    person = payload["people"][0]
    assert person["code"] == "DEMO01" and person["has_build"] and person["has_test"]
    assert person["kit_minutes"] is None  # the example build was not made by the kit page
    assert person["pasted"] == {"A": 1, "B": 1} and person["model_shown"] == {"A": [], "B": ["GPT Sol 6.1"]}
    assert person["voice_transcript"] is True and person["bytes"] > 0 and person["last_modified"]
    assert payload["total_bytes"] == person["bytes"]
    overview = member.get("/api/admin/overview")[1]
    assert overview["counts"]["pasted_runs_A"] == 1 and overview["counts"]["pasted_runs_B"] == 1


def test_people_listing_reads_kit_minutes(member, tmp_path):
    member.post("/api/team/people", {"code": "DEMO01", "build": {**BUILD, "kit_minutes": 23.5}})
    assert member.get("/api/admin/people")[1]["people"][0]["kit_minutes"] == 23.5


def test_delete_one_person_and_refuse_traversal(member, tmp_path):
    upload_demo(member)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")
    for bad in ("../outside", "..", "x", "a/b", "DEMO01/../../outside", "", None, 7):
        status, payload, _, _ = member.post("/api/admin/people/delete", {"code": bad})
        assert status == 400, (bad, payload)
    assert (outside / "keep.txt").exists()
    assert member.post("/api/admin/people/delete", {"code": "NOBODY"})[0] == 404
    status, payload, _, _ = member.post("/api/admin/people/delete", {"code": "DEMO01"})
    assert status == 200 and payload == {"deleted": True}
    assert not (tmp_path / "data" / "people" / "DEMO01").exists()


# ---------------------------------------------------------------------------
# Purges
# ---------------------------------------------------------------------------


def _seed(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    for relative in ("team/results.json", "team/results.md", "team/ratesheet.html", "team/keys/ratesheet_key.json",
                     "team/agreement.md", "team/selfcheck.json", "team/evaluations.json", "team/evaluations.md",
                     "experiment/results.md", "final/me.md", "final/responses.json"):
        path = data / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
    return data


def test_purge_requires_the_exact_phrase(member, tmp_path):
    upload_demo(member)
    for confirm in (None, "", "delete people", "DELETE PEOPLE ", "DELETE  PEOPLE", "DELETE OUTPUTS", "PEOPLE"):
        status, payload, _, _ = member.post("/api/admin/purge", {"scope": "people", "confirm": confirm})
        assert status == 400 and "DELETE PEOPLE" in payload["error"], confirm
    assert (tmp_path / "data" / "people" / "DEMO01" / "build.json").exists()
    for scope in ("everything", "../people", "", None, "PEOPLE"):
        assert member.post("/api/admin/purge", {"scope": scope, "confirm": f"DELETE {str(scope).upper()}"})[0] == 400


def test_purge_people_keeps_ledger_and_everything_else(member, tmp_path):
    consent(member, "P01")
    upload_demo(member)
    data = _seed(tmp_path)
    ledger = (data / "consent" / "ledger.jsonl").read_text(encoding="utf-8")
    status, payload, _, _ = member.post("/api/admin/purge", {"scope": "people", "confirm": "DELETE PEOPLE"})
    assert status == 200 and payload["deleted"] == ["people/DEMO01"] and payload["kept_consent_ledger"] is True
    assert (data / "people").is_dir() and not any((data / "people").iterdir())
    assert (data / "consent" / "ledger.jsonl").read_text(encoding="utf-8") == ledger
    assert (data / "team" / "results.json").exists() and (data / "final" / "me.md").exists()


def test_purge_outputs_then_final(member, tmp_path):
    consent(member, "P01")
    upload_demo(member)
    data = _seed(tmp_path)
    status, payload, _, _ = member.post("/api/admin/purge", {"scope": "outputs", "confirm": "DELETE OUTPUTS"})
    assert status == 200
    assert sorted(payload["deleted"]) == ["experiment/results.md", "team/agreement.md", "team/keys", "team/ratesheet.html",
                                          "team/results.json", "team/results.md", "team/selfcheck.json"]
    assert sorted(p.name for p in (data / "team").iterdir()) == ["evaluations.json", "evaluations.md"]
    assert (data / "final" / "me.md").exists() and (data / "people" / "DEMO01" / "build.json").exists()
    status, payload, _, _ = member.post("/api/admin/purge", {"scope": "final", "confirm": "DELETE FINAL"})
    assert status == 200
    assert sorted(payload["deleted"]) == ["final/me.md", "final/responses.json", "team/evaluations.json", "team/evaluations.md"]
    assert (data / "final").is_dir() and not any((data / "final").iterdir())
    assert (data / "people" / "DEMO01" / "build.json").exists() and (data / "consent" / "ledger.jsonl").exists()
    again = member.post("/api/admin/purge", {"scope": "final", "confirm": "DELETE FINAL"})[1]
    assert again["deleted"] == [] and again["kept_consent_ledger"] is True


def test_purge_never_follows_a_link_out_of_the_data(member, tmp_path):
    data = _seed(tmp_path)
    outside = tmp_path / "outside"
    (outside / "inner").mkdir(parents=True)
    (outside / "inner" / "precious.txt").write_text("keep", encoding="utf-8")
    (data / "people").mkdir(parents=True, exist_ok=True)
    os.symlink(outside, data / "people" / "LINKED")
    os.symlink(outside / "inner", data / "team" / "linked-dir")
    status, payload, _, _ = member.post("/api/admin/purge", {"scope": "people", "confirm": "DELETE PEOPLE"})
    assert status == 200 and payload["deleted"] == ["people/LINKED"]
    status, payload, _, _ = member.post("/api/admin/purge", {"scope": "outputs", "confirm": "DELETE OUTPUTS"})
    assert status == 200 and "team/linked-dir" in payload["deleted"]
    assert (outside / "inner" / "precious.txt").read_text(encoding="utf-8") == "keep"


def test_purge_keeps_a_ledger_that_shares_a_folder(member, tmp_path, monkeypatch):
    # a misconfigured box with the consent folder inside the people folder: the ledger still survives a people purge
    monkeypatch.setattr(app, "LEDGER_DIR", tmp_path / "data" / "people" / "consent")
    consent(member, "P01")
    upload_demo(member)
    payload = member.post("/api/admin/purge", {"scope": "people", "confirm": "DELETE PEOPLE"})[1]
    assert payload["deleted"] == ["people/DEMO01"]
    assert (tmp_path / "data" / "people" / "consent" / "ledger.jsonl").exists()


def test_purge_refuses_a_people_folder_that_holds_the_data(member, tmp_path, monkeypatch):
    monkeypatch.setenv("MEFILE_PEOPLE_DIR", str(tmp_path))
    data = _seed(tmp_path)
    status, payload, _, _ = member.post("/api/admin/purge", {"scope": "people", "confirm": "DELETE PEOPLE"})
    assert status == 409
    assert (data / "team" / "results.json").exists()


def test_admin_module_header():
    lines = Path(admin.__file__).read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# Copyright (c) 2026 William Chesher. MIT License, see LICENSE."
    assert lines[1].startswith("# admin - ")
