# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_voice_intake - Plaud import, consent on the voice routes, deletion after fetch, the agent check, /api/convert with voice

from __future__ import annotations

import io
import json
import threading
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from mefile import app, cli, intake, plaud, voice
from mefile.answers import load_answers
from mefile.converter import convert

BUILD = Path(__file__).resolve().parents[1] / "examples" / "example_build_answers.json"
GUIDE = dict(voice.INTERVIEW_GUIDE)
REAL_URLOPEN = urllib.request.urlopen  # the test client's own calls to the local server pass straight through
FAKE_KEY = "sk_test_fictional_key_never_printed"

# Fictional interviews only; nobody real said any of this.
PLAUD_TXT = f"""Team sync recording
2026-11-14

[00:00 - 00:06] Speaker 1: Thanks for doing this. {GUIDE['V-disagree']}
[00:07 - 00:30] Speaker 2: Last spring my lead wanted to skip the review step and I asked for one more pass.
I wrote it up in the channel first.
[00:31 - 00:33] Speaker 1: What did you say?
[00:34 - 00:50] Speaker 2: I said, I think we should wait a day, maybe two, or we will be fixing it all week.
[00:51 - 00:58] Speaker 1: {GUIDE['V-help']}
[01:00 - 01:20] Speaker 2: A new colleague was stuck on a spreadsheet so I stayed an hour to walk through it.
"""

PLAUD_SRT = f"""1
00:00:00,000 --> 00:00:05,000
Speaker 1: {GUIDE['V-decline']}

2
00:00:05,500 --> 00:00:12,000
Speaker 2: A vendor asked for a rush job and I told them Friday, not Wednesday.

3
00:00:12,000 --> 00:00:15,250
I offered a smaller piece by Wednesday instead.
"""

PLAUD_RENAMED = f"""Sam [00:01]
{GUIDE['V-setback']}

Riley [00:09]
We piloted a new intake form and nobody used it.
So we went back and asked people why.

Sam [00:31]
What did you do?

Riley [00:35]
I rewrote it with them in one afternoon.
"""


# ---------------------------------------------------------------------------------------------- plaud parsing


def test_plaud_txt_speakers_turns_and_samples():
    found = plaud.speakers(PLAUD_TXT)
    assert [s["label"] for s in found] == ["Speaker 1", "Speaker 2"]
    assert [s["turns"] for s in found] == [3, 3]
    assert found[1]["sample"].startswith("Last spring my lead")
    assert all(len(s["sample"]) <= plaud.SAMPLE_CHARACTERS + 3 for s in found)


def test_plaud_txt_transcript_shape():
    transcript = plaud.to_transcript(PLAUD_TXT, "Speaker 2", person_id="DEMO01")
    assert transcript["source"] == "plaud" and transcript["person_id"] == "DEMO01"
    assert transcript["conversation_id"].startswith("plaud-") and len(transcript["conversation_id"]) == 22
    assert transcript["duration_seconds"] == 80.0
    assert [t["index"] for t in transcript["employee_turns"]] == [1, 3, 5]
    assert transcript["employee_turns"][0]["text"].endswith("I wrote it up in the channel first.")  # continuation line joined
    assert transcript["employee_turns"][0]["seconds"] == 7.0
    assert [t["index"] for t in transcript["interviewer_turns"]] == [0, 2, 4]
    # the same text always gives the same conversation id; a different text a different one
    assert plaud.to_transcript(PLAUD_TXT, "speaker 2")["conversation_id"] == transcript["conversation_id"]
    assert plaud.to_transcript(PLAUD_SRT, "Speaker 2")["conversation_id"] != transcript["conversation_id"]


def test_plaud_srt_with_and_without_prefixes():
    found = plaud.speakers(PLAUD_SRT)
    assert [(s["label"], s["turns"]) for s in found] == [("Speaker 1", 1), ("Speaker 2", 1)]  # cue 3 continues Speaker 2
    transcript = plaud.to_transcript(PLAUD_SRT, "Speaker 2")
    assert transcript["employee_turns"][0]["text"].endswith("a smaller piece by Wednesday instead.")
    assert transcript["duration_seconds"] == 15.25
    unlabeled = "1\n00:00:01,000 --> 00:00:03,000\nWe shipped it on time.\n\n2\n00:00:03,000 --> 00:00:06,000\nThen we wrote it up.\n"
    assert plaud.speakers(unlabeled) == [{"label": "Unlabeled", "turns": 1, "sample": "We shipped it on time. Then we wrote it up."}]


def test_plaud_renamed_speaker_blocks_and_name_lines():
    found = plaud.speakers(PLAUD_RENAMED)
    assert [(s["label"], s["turns"]) for s in found] == [("Sam", 2), ("Riley", 2)]
    transcript = plaud.to_transcript(PLAUD_RENAMED, "Riley")
    assert [t["seconds"] for t in transcript["employee_turns"]] == [9.0, 35.0]
    named = f"Sam: {GUIDE['V-help']}\nAlex: I covered a shift for a teammate during exams week.\n"
    assert [s["label"] for s in plaud.speakers(named)] == ["Sam", "Alex"]
    bracketed = "[00:01 - 00:04] Jordan Lee: Hello there.\n[00:05 - 00:09] Sam: Hi, ready when you are.\n"
    assert [s["label"] for s in plaud.speakers(bracketed)] == ["Jordan Lee", "Sam"]


@pytest.mark.parametrize("text,fragment", [
    ("just some prose without any structure at all", "could not find any speaker turns"),
    ("   \n", "the transcript is empty"),
    ("PK\x03\x04 binary docx bytes", "DOCX or PDF"),
    ("x" * (plaud.MAX_TEXT_BYTES + 1), "over 500 KB"),
])
def test_plaud_malformed_is_a_clear_error(text, fragment):
    with pytest.raises(plaud.PlaudFormatError, match=fragment):
        plaud.speakers(text)


def test_plaud_unknown_speaker_names_the_choices():
    with pytest.raises(plaud.PlaudFormatError, match="choose one of: Speaker 1, Speaker 2"):
        plaud.to_transcript(PLAUD_TXT, "Speaker 9")


# ------------------------------------------------------------------------- plaud -> intake -> convert -> me.md


def test_plaud_transcript_cites_into_me_md():
    evidence = intake.parse_transcript(plaud.to_transcript(PLAUD_TXT, "Speaker 2", person_id="DEMO01"))
    assert [(i.id, i.question) for i in evidence] == [("V01", "V-disagree"), ("V02", "V-disagree"), ("V03", "V-help")]
    assert evidence.source == "plaud"
    profile = convert(load_answers(BUILD), voice=evidence)
    assert profile.gate.passed, profile.gate.blocking
    for voice_id in ("V01", "V02", "V03"):
        assert f"{voice_id}:" in profile.markdown
    assert "[V02]" in profile.markdown  # the hedging claim cites the turn it counts
    assert profile.sidecar["voice_evidence"]["source"] == "plaud"
    assert profile.sidecar["voice_evidence"]["conversation_id"].startswith("plaud-")


def test_intake_source_field():
    base = {"employee_turns": [{"index": 1, "text": "We shipped it."}], "interviewer_turns": []}
    for source in intake.SOURCES:
        assert intake.parse_transcript({**base, "source": source}).source == source
    assert intake.parse_transcript(base).source == ""
    # the source changes no evidence and not the digest
    assert intake.parse_transcript({**base, "source": "typed"}).digest() == intake.parse_transcript(base).digest()
    with pytest.raises(ValueError, match="unknown transcript source"):
        intake.parse_transcript({**base, "source": "zoom"})
    with pytest.raises(ValueError, match="must be a list of objects"):
        intake.parse_transcript({"employee_turns": "not a list"})


# ------------------------------------------------------------------------------------------ HTTP fixtures


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


def request(base_url: str, method: str, path: str, body: dict | None = None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["X-Consent-Token"] = token
    data = json.dumps(body).encode("utf-8") if body is not None else None
    call = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(call, timeout=20) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def consent(base_url: str, purposes: list[str], person_id: str = "DEMO01") -> str:
    status, payload = request(base_url, "POST", "/api/consent", {"person_id": person_id, "purposes": purposes})
    assert status == 200
    return payload["consent_token"]


class FakeResponse:
    def __init__(self, payload):
        self.raw = json.dumps(payload).encode("utf-8") if payload is not None else b""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.raw


class FakeElevenLabs:
    """Stands in for urllib.request.urlopen inside voice.py: routes keyed by (method, path without query)."""

    def __init__(self, routes: dict):
        self.routes = routes
        self.calls: list[tuple[str, str, dict | None]] = []

    def __call__(self, call, timeout=None):
        if not call.full_url.startswith(voice.API):
            return REAL_URLOPEN(call, timeout=timeout)
        path = call.full_url[len(voice.API):]
        self.calls.append((call.get_method(), path, json.loads(call.data) if call.data else None))
        assert call.get_header("Xi-api-key") == FAKE_KEY
        reply = self.routes.get((call.get_method(), path.split("?")[0]), 404)
        if isinstance(reply, int):
            raise urllib.error.HTTPError(call.full_url, reply, "fake", {}, io.BytesIO(b""))
        return FakeResponse(reply)

    def methods(self) -> list[tuple[str, str]]:
        return [(method, path.split("?")[0]) for method, path, _ in self.calls]


SAFE_AGENT = {"agent_id": "agent_fake1", "platform_settings": {"privacy": {"record_voice": False}, "auth": {"enable_auth": True}}}
DONE_CONVERSATION = {
    "status": "done",
    "metadata": {"call_duration_secs": 95},
    "transcript": [
        {"role": "agent", "message": voice.FIRST_MESSAGE, "time_in_call_secs": 0},
        {"role": "user", "message": "Yes, ready.", "time_in_call_secs": 8},
        {"role": "agent", "message": GUIDE["V-help"], "time_in_call_secs": 10},
        {"role": "user", "message": "I covered a shift for a teammate during exams week.", "time_in_call_secs": 18},
    ],
}


@pytest.fixture()
def eleven(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", FAKE_KEY)
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_fake1")
    monkeypatch.setattr(voice, "_VERIFIED", {})
    fake = FakeElevenLabs({})
    monkeypatch.setattr(voice.urllib.request, "urlopen", fake)
    return fake


# ------------------------------------------------------------------------------------------------ consent


@pytest.mark.parametrize("method,path,body", [
    ("GET", "/api/voice/transcript?conversation_id=conv_fake1", None),
    ("POST", "/api/voice/plaud", {"text": PLAUD_TXT}),
])
def test_voice_routes_require_voice_interview_consent(base_url, eleven, method, path, body):
    expected = {"error": "consent required", "purpose": "voice_interview"}
    assert request(base_url, method, path, body) == (403, expected)
    wrong = consent(base_url, ["build_profile"])
    assert request(base_url, method, path, body, token=wrong) == (403, expected)
    assert eleven.calls == []  # refused before ElevenLabs was ever called


# ------------------------------------------------------------------------------------- deletion after fetch


def test_transcript_fetch_then_delete(base_url, eleven):
    eleven.routes[("GET", "/v1/convai/conversations/conv_fake1")] = DONE_CONVERSATION
    eleven.routes[("DELETE", "/v1/convai/conversations/conv_fake1")] = None
    token = consent(base_url, ["voice_interview"])
    status, payload = request(base_url, "GET", "/api/voice/transcript?conversation_id=conv_fake1", token=token)
    assert status == 200
    assert payload["deleted"] is True and payload["source"] == "elevenlabs" and payload["status"] == "done"
    assert [t["text"] for t in payload["employee_turns"]] == ["Yes, ready.", "I covered a shift for a teammate during exams week."]
    assert eleven.methods() == [("GET", "/v1/convai/conversations/conv_fake1"), ("DELETE", "/v1/convai/conversations/conv_fake1")]
    assert [i.question for i in intake.parse_transcript(payload)] == ["other", "V-help"]


def test_transcript_not_done_is_not_deleted(base_url, eleven):
    eleven.routes[("GET", "/v1/convai/conversations/conv_fake1")] = {**DONE_CONVERSATION, "status": "processing"}
    token = consent(base_url, ["voice_interview"])
    status, payload = request(base_url, "GET", "/api/voice/transcript?conversation_id=conv_fake1", token=token)
    assert status == 200 and payload["deleted"] is False
    assert ("DELETE", "/v1/convai/conversations/conv_fake1") not in eleven.methods()


def test_transcript_delete_failure_is_reported(base_url, eleven):
    eleven.routes[("GET", "/v1/convai/conversations/conv_fake1")] = DONE_CONVERSATION
    eleven.routes[("DELETE", "/v1/convai/conversations/conv_fake1")] = 500
    token = consent(base_url, ["voice_interview"])
    status, payload = request(base_url, "GET", "/api/voice/transcript?conversation_id=conv_fake1", token=token)
    assert status == 200 and payload["deleted"] is False
    assert "500" in payload["delete_error"] and FAKE_KEY not in json.dumps(payload)


def test_transcript_bad_id_is_400(base_url, eleven):
    token = consent(base_url, ["voice_interview"])
    status, payload = request(base_url, "GET", "/api/voice/transcript?conversation_id=..%2Fagents", token=token)
    assert status == 400 and payload == {"error": "invalid conversation id"}
    assert eleven.calls == []


# --------------------------------------------------------------------------------------------- agent check


def test_verify_agent_refuses_recording_and_missing_auth(eleven):
    eleven.routes[("GET", "/v1/convai/agents/agent_fake1")] = {
        "platform_settings": {"privacy": {"record_voice": True}, "auth": {"enable_auth": False}}}
    with pytest.raises(voice.AgentNotSafe, match="audio recording is not off.*authentication is not on"):
        voice.start_session()
    assert ("GET", "/v1/convai/conversation/get-signed-url") not in eleven.methods()
    eleven.routes[("GET", "/v1/convai/agents/agent_fake1")] = {}  # fields missing: fail closed
    with pytest.raises(voice.AgentNotSafe):
        voice.verify_agent()


def test_session_route_refuses_unsafe_agent_with_503(base_url, eleven):
    eleven.routes[("GET", "/v1/convai/agents/agent_fake1")] = {"platform_settings": {"privacy": {"record_voice": True},
                                                                                     "auth": {"enable_auth": True}}}
    token = consent(base_url, ["voice_interview"])
    status, payload = request(base_url, "POST", "/api/voice/session", {}, token=token)
    assert status == 503 and payload["error"].startswith("voice interview refused: audio recording is not off")


def test_verify_agent_caches_a_pass_for_ten_minutes(eleven, monkeypatch):
    eleven.routes[("GET", "/v1/convai/agents/agent_fake1")] = SAFE_AGENT
    eleven.routes[("GET", "/v1/convai/conversation/get-signed-url")] = {"signed_url": "wss://example.invalid/signed"}
    clock = [1000.0]
    monkeypatch.setattr(voice.time, "monotonic", lambda: clock[0])
    assert voice.start_session() == {"signed_url": "wss://example.invalid/signed"}
    clock[0] += voice.VERIFY_CACHE_SECONDS - 1
    voice.start_session()
    assert eleven.methods().count(("GET", "/v1/convai/agents/agent_fake1")) == 1
    clock[0] += 2
    voice.start_session()
    assert eleven.methods().count(("GET", "/v1/convai/agents/agent_fake1")) == 2


# ----------------------------------------------------------------------------------------- provisioning


def run_cli(*argv) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        status = cli.main(list(argv))
    return status, out.getvalue(), err.getvalue()


def test_voice_agent_creates_when_no_id(eleven, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_AGENT_ID")
    eleven.routes[("GET", "/v1/convai/agents")] = {"agents": [{"agent_id": "agent_other", "name": "someone else's agent"}]}
    eleven.routes[("POST", "/v1/convai/agents/create")] = {"agent_id": "agent_new1"}
    eleven.routes[("GET", "/v1/convai/agents/agent_new1")] = SAFE_AGENT
    status, out, err = run_cli("voice-agent")
    assert status == 0 and out == "agent_new1\n"
    assert FAKE_KEY not in out + err
    body = next(b for m, p, b in eleven.calls if m == "POST")
    assert body["platform_settings"] == {"auth": {"enable_auth": True}, "privacy": {"record_voice": False}}
    assert body["conversation_config"]["agent"]["prompt"]["prompt"] == voice.AGENT_SYSTEM_PROMPT
    assert body["conversation_config"]["agent"]["first_message"] == voice.FIRST_MESSAGE
    assert body["conversation_config"]["conversation"]["max_duration_seconds"] == 660
    assert body["conversation_config"]["turn"]["turn_timeout"] > 7


def test_voice_agent_updates_in_place(eleven):
    eleven.routes[("PATCH", "/v1/convai/agents/agent_fake1")] = SAFE_AGENT
    eleven.routes[("GET", "/v1/convai/agents/agent_fake1")] = SAFE_AGENT
    status, out, _ = run_cli("voice-agent")
    assert status == 0 and out == "agent_fake1\n"
    assert ("POST", "/v1/convai/agents/create") not in eleven.methods()


def test_voice_agent_reuses_an_agent_with_the_same_name(eleven, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_AGENT_ID")
    eleven.routes[("GET", "/v1/convai/agents")] = {"agents": [{"agent_id": "agent_kept", "name": voice.AGENT_NAME}]}
    eleven.routes[("PATCH", "/v1/convai/agents/agent_kept")] = {}
    eleven.routes[("GET", "/v1/convai/agents/agent_kept")] = SAFE_AGENT
    status, out, _ = run_cli("voice-agent")
    assert status == 0 and out == "agent_kept\n"
    assert ("POST", "/v1/convai/agents/create") not in eleven.methods()


def test_voice_agent_fails_when_the_check_fails(eleven):
    eleven.routes[("PATCH", "/v1/convai/agents/agent_fake1")] = {}
    eleven.routes[("GET", "/v1/convai/agents/agent_fake1")] = {"platform_settings": {"privacy": {"record_voice": True}}}
    status, out, err = run_cli("voice-agent")
    assert status == 1 and out == "" and "audio recording is not off" in err and FAKE_KEY not in err


# ------------------------------------------------------------------------------------------ plaud route


def test_plaud_route_speakers_then_transcript(base_url):
    token = consent(base_url, ["voice_interview"])
    status, payload = request(base_url, "POST", "/api/voice/plaud", {"text": PLAUD_TXT}, token=token)
    assert status == 200 and [s["label"] for s in payload["speakers"]] == ["Speaker 1", "Speaker 2"]
    assert set(payload["speakers"][0]) == {"label", "turns", "sample"}
    status, payload = request(base_url, "POST", "/api/voice/plaud",
                              {"text": PLAUD_TXT, "speaker": "Speaker 2", "person_id": "DEMO01"}, token=token)
    assert status == 200 and payload["transcript"]["source"] == "plaud"
    assert len(intake.parse_transcript(payload["transcript"])) == 3


def test_plaud_route_malformed_is_400(base_url):
    token = consent(base_url, ["voice_interview"])
    status, payload = request(base_url, "POST", "/api/voice/plaud", {"text": "no speakers in this text at all"}, token=token)
    assert status == 400 and payload["error"].startswith("could not find any speaker turns")
    status, payload = request(base_url, "POST", "/api/voice/plaud", {"text": PLAUD_TXT, "speaker": "Nobody"}, token=token)
    assert status == 400 and "choose one of" in payload["error"]
    status, payload = request(base_url, "POST", "/api/voice/plaud", {"text": 42}, token=token)
    assert status == 400 and payload == {"error": "send the transcript as text"}


def test_plaud_route_caps_text_at_500_kb(base_url):
    token = consent(base_url, ["voice_interview"])
    status, payload = request(base_url, "POST", "/api/voice/plaud", {"text": "a" * (plaud.MAX_TEXT_BYTES + 1)}, token=token)
    assert status == 413 and "over 500 KB" in payload["error"]


# -------------------------------------------------------------------------- guide, config, convert with voice


def test_guide_and_config(base_url):
    status, guide = request(base_url, "GET", "/api/voice/guide")
    assert status == 200 and guide == [{"key": key, "question": question} for key, question in voice.INTERVIEW_GUIDE]
    status, config = request(base_url, "GET", "/api/config")
    assert status == 200 and config["plaud_enabled"] is True and "voice_enabled" in config


def test_convert_with_voice(base_url):
    token = consent(base_url, ["build_profile"])
    answers = json.loads(BUILD.read_text(encoding="utf-8"))
    transcript = plaud.to_transcript(PLAUD_TXT, "Speaker 2", person_id="DEMO01")
    status, payload = request(base_url, "POST", "/api/convert", {"answers": answers, "scope": "full", "voice": transcript}, token=token)
    assert status == 200 and payload["gate"]["passed"]
    assert "V02:" in payload["markdown"] and payload["sidecar"]["voice_evidence"]["source"] == "plaud"
    assert any(any(e.startswith("V") for e in c.get("evidence", [])) for c in payload["claims"])
    # without voice the response is what it was
    status, plain = request(base_url, "POST", "/api/convert", {"answers": answers, "scope": "full"}, token=token)
    assert status == 200 and "voice_evidence" not in plain["sidecar"]
    # a disputed claim still works next to voice
    claim_id = payload["claims"][0]["id"]
    status, disputed = request(base_url, "POST", "/api/convert",
                               {"answers": answers, "voice": transcript, "disputed": {claim_id: "not me"}}, token=token)
    assert status == 200 and next(c for c in disputed["claims"] if c["id"] == claim_id)["disputed"] is True


@pytest.mark.parametrize("bad,fragment", [
    ("a string", "voice must be a transcript object"),
    ({"employee_turns": "nope"}, "must be a list of objects"),
    ({"person_id": "DEMO02", "employee_turns": [{"index": 1, "text": "We shipped it."}]}, "the voice transcript is for"),
    ({"source": "zoom", "employee_turns": [{"index": 1, "text": "We shipped it."}]}, "unknown transcript source"),
])
def test_convert_with_bad_voice_is_400(base_url, bad, fragment):
    token = consent(base_url, ["build_profile"])
    answers = json.loads(BUILD.read_text(encoding="utf-8"))
    status, payload = request(base_url, "POST", "/api/convert", {"answers": answers, "voice": bad}, token=token)
    assert status == 400 and fragment in payload["error"]
