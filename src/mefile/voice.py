# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# voice - ElevenLabs Agents voice interview: agent check and provisioning, signed session URL, transcript fetch, deletion

"""
Voice intake (optional extra credit, Common Kit Section 11)
===========================================================

A purpose-built ElevenLabs agent runs a ~10 minute behavioral interview. We keep the TRANSCRIPT of
the employee's own words and nothing else:

  - never tone of voice: inferring emotion from voice at work is prohibited under EU AI Act
    Article 5(1)(f); we analyze text only;
  - never a voice clone: your understudy answers in text (or a stock synthetic voice), never the person's;
  - audio recording is OFF on the agent (platform_settings.privacy.record_voice = false), and this is
    ENFORCED here: ``verify_agent`` reads the agent's live configuration and ``start_session`` refuses
    to open a session unless recording is off and authentication is on;
  - the conversation is deleted from ElevenLabs once the finished transcript has been fetched
    (app.py calls ``delete_conversation`` and reports ``deleted``).

``provision_agent`` (``python -m mefile voice-agent``) creates or updates the agent from the prompt and
the disclosure below, so the agent's settings live in code, not in a dashboard.

The API key stays on the server; the browser only ever receives a short-lived signed URL.
Standard library only (urllib), the pattern of teenyverse3's stdlib ElevenLabs clients.

API shapes: the endpoints and fields named in docs/voice-intake.md are marked "per docs/voice-intake.md";
anything else is marked UNVERIFIED and comes from the vendor API reference as remembered, not re-checked.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.elevenlabs.io"

AGENT_NAME = "lumin8r work-style interview"
MAX_DURATION_SECONDS = 660  # per docs/voice-intake.md: about 660
TURN_TIMEOUT_SECONDS = 15  # per docs/voice-intake.md: raised from the default 7 (the allowed range is UNVERIFIED)
VERIFY_CACHE_SECONDS = 600  # a passing verify_agent result is trusted for 10 minutes

_VERIFIED: dict[str, float] = {}  # agent_id -> time.monotonic() of the last passing check
_VERIFIED_LOCK = threading.Lock()


class AgentNotSafe(RuntimeError):
    """The agent's live configuration does not guarantee recording off and authentication on."""


def configured() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY") and os.environ.get("ELEVENLABS_AGENT_ID"))


def _call(method: str, path: str, body: dict | None = None) -> dict:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("voice intake is not configured (ELEVENLABS_API_KEY missing)")
    headers = {"xi-api-key": key, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(API + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:  # the status and the path only: never the key, never a body
        raise RuntimeError(f"ElevenLabs returned {error.code} for {method} {path.split('?')[0]}") from None
    except urllib.error.URLError as error:
        raise RuntimeError(f"ElevenLabs could not be reached ({type(error.reason).__name__})") from None


def _agent_id() -> str:
    agent_id = os.environ.get("ELEVENLABS_AGENT_ID")
    if not agent_id:
        raise RuntimeError("voice intake is not configured (ELEVENLABS_AGENT_ID missing)")
    return agent_id


def _valid_id(value: str) -> bool:
    return bool(value) and value.replace("_", "").replace("-", "").isalnum()


def agent_problems(agent: dict) -> list[str]:
    """What in an agent configuration (GET /v1/convai/agents/{id}) breaks the privacy rules; empty when it is safe.

    Fails closed: a missing field counts as a problem, since the vendor default for record_voice is on.
    """
    platform = agent.get("platform_settings") if isinstance(agent.get("platform_settings"), dict) else {}
    privacy = platform.get("privacy") if isinstance(platform.get("privacy"), dict) else {}
    auth = platform.get("auth") if isinstance(platform.get("auth"), dict) else {}
    problems = []
    if privacy.get("record_voice") is not False:
        problems.append("audio recording is not off (platform_settings.privacy.record_voice must be false)")
    if auth.get("enable_auth") is not True:
        problems.append("authentication is not on (platform_settings.auth.enable_auth must be true)")
    return problems


def verify_agent(agent_id: str | None = None, use_cache: bool = True) -> dict:
    """Read the agent's live configuration and confirm recording is off and auth is on; raise AgentNotSafe if not.

    A passing result is cached per agent for VERIFY_CACHE_SECONDS; a failing one is never cached.
    """
    agent_id = agent_id or _agent_id()
    if not _valid_id(agent_id):
        raise AgentNotSafe("the voice agent id is not valid")
    now = time.monotonic()
    if use_cache:
        with _VERIFIED_LOCK:
            checked_at = _VERIFIED.get(agent_id)
        if checked_at is not None and now - checked_at < VERIFY_CACHE_SECONDS:
            return {"agent_id": agent_id, "record_voice": False, "enable_auth": True, "cached": True}
    # UNVERIFIED: GET /v1/convai/agents/{agent_id} returning {platform_settings: {privacy: {record_voice}, auth:
    # {enable_auth}}}; docs/voice-intake.md names both fields but not this read endpoint.
    agent = _call("GET", f"/v1/convai/agents/{agent_id}")
    problems = agent_problems(agent)
    if problems:
        with _VERIFIED_LOCK:
            _VERIFIED.pop(agent_id, None)
        raise AgentNotSafe("voice interview refused: " + "; ".join(problems)
                           + ". Run python -m mefile voice-agent (update-lumin8r does) to fix the agent.")
    with _VERIFIED_LOCK:
        _VERIFIED[agent_id] = now
    return {"agent_id": agent_id, "record_voice": False, "enable_auth": True, "cached": False}


def start_session() -> dict:
    agent_id = _agent_id()
    verify_agent(agent_id)  # raises AgentNotSafe: no session on an agent that records audio or skips auth
    # per docs/voice-intake.md
    data = _call("GET", "/v1/convai/conversation/get-signed-url?" + urllib.parse.urlencode({"agent_id": agent_id}))
    return {"signed_url": data["signed_url"]}


def fetch_transcript(conversation_id: str) -> dict:
    if not _valid_id(conversation_id or ""):
        raise ValueError("invalid conversation id")
    # per docs/voice-intake.md: status, transcript[] with role (user|agent), message, time_in_call_secs.
    # UNVERIFIED: metadata.call_duration_secs.
    data = _call("GET", f"/v1/convai/conversations/{conversation_id}")
    turns = data.get("transcript") or []
    employee = [{"index": i, "seconds": t.get("time_in_call_secs"), "text": (t.get("message") or "").strip()}
                for i, t in enumerate(turns) if t.get("role") == "user" and (t.get("message") or "").strip()]
    interviewer = [{"index": i, "text": (t.get("message") or "").strip()}
                   for i, t in enumerate(turns) if t.get("role") == "agent"]
    return {
        "source": "elevenlabs",
        "conversation_id": conversation_id,
        "status": data.get("status"),
        "duration_seconds": (data.get("metadata") or {}).get("call_duration_secs"),
        "employee_turns": employee,
        "interviewer_turns": interviewer,
    }


def delete_conversation(conversation_id: str) -> None:
    if not _valid_id(conversation_id or ""):
        raise ValueError("invalid conversation id")
    _call("DELETE", f"/v1/convai/conversations/{conversation_id}")  # per docs/voice-intake.md


INTERVIEW_GUIDE = [
    ("V-disagree", "Tell me about a time you disagreed with a teammate or manager about how to do something. What did you do?"),
    ("V-words", "What exactly did you say first? Give me your words as closely as you can remember."),
    ("V-uncertain", "Describe a decision you had to make without enough information. What did you choose, and why?"),
    ("V-setback", "Tell me about something you tried that did not work. What did you do next?"),
    ("V-credit", "Tell me about a time credit for group work was not shared fairly. What happened, and what did you do?"),
    ("V-help", "Tell me about a time you helped a colleague when it cost you time."),
    ("V-decline", "Tell me about a time you said no to a request. How did you put it?"),
    ("V-message", "Think of a message you recently wrote to someone senior. How did you word it?"),
]

AGENT_SYSTEM_PROMPT = """You are a friendly, neutral workplace interviewer for a voluntary coaching profile. Your first
message has already said that you are an AI interviewer, that the conversation is transcribed (text only) to build a
profile the person controls, and that they can skip any question or stop at any time; do not repeat it. If the person
asks, say it again plainly. Ask the questions below one at a
time, in order. After each answer ask at most one short follow-up: "What did you do?" or "What did you say?". Keep to
work situations only: never ask about health, family, religion, politics, age, ethnicity, or anything outside work. Do
not give advice, do not evaluate answers, do not comment on the person's personality. Finish after the last question by
thanking them. Questions:
""" + "\n".join(f"{i + 1}. {q}" for i, (_, q) in enumerate(INTERVIEW_GUIDE))

# The disclosure the agent speaks first (ElevenLabs Agents terms 3.5, per docs/voice-intake.md): an AI, who processes
# the conversation, that it is transcribed, and that the person can stop.
FIRST_MESSAGE = ("Hi, I am an AI interviewer, not a person. ElevenLabs and its AI model providers process this "
                 "conversation, and it is transcribed to text. The audio is not kept, and the conversation is deleted "
                 "from ElevenLabs once your transcript is ready. You will read and edit the transcript before anything "
                 "uses it. You can skip any question or stop at any time. Shall we begin?")


def agent_config(name: str = AGENT_NAME) -> dict:
    """The agent body for create and update: prompt, disclosure, recording off, auth on, duration cap, turn timeout.

    Field paths per docs/voice-intake.md: conversation_config.agent.prompt.prompt, conversation.max_duration_seconds,
    turn.turn_timeout, platform_settings.auth.enable_auth, platform_settings.privacy.record_voice.
    UNVERIFIED: first_message nests under conversation_config.agent (docs/voice-intake.md names the field, not its parent).
    """
    return {
        "name": name,
        "conversation_config": {
            "agent": {"first_message": FIRST_MESSAGE, "language": "en", "prompt": {"prompt": AGENT_SYSTEM_PROMPT}},
            "conversation": {"max_duration_seconds": MAX_DURATION_SECONDS},
            "turn": {"turn_timeout": TURN_TIMEOUT_SECONDS},
        },
        "platform_settings": {"auth": {"enable_auth": True}, "privacy": {"record_voice": False}},
    }


def _find_agent_by_name(name: str) -> str | None:
    """The id of an existing agent with exactly this name, so a create that was never stored is not repeated."""
    # UNVERIFIED: GET /v1/convai/agents?search=... returning {agents: [{agent_id, name}]}.
    try:
        data = _call("GET", "/v1/convai/agents?" + urllib.parse.urlencode({"search": name, "page_size": 100}))
    except RuntimeError:
        return None
    for agent in data.get("agents") or []:
        if isinstance(agent, dict) and agent.get("name") == name and _valid_id(str(agent.get("agent_id") or "")):
            return str(agent["agent_id"])
    return None


def provision_agent(agent_id: str | None = None, name: str = AGENT_NAME) -> dict:
    """Create or update the interview agent idempotently, then verify it; returns {agent_id, action}.

    With an agent id: update it in place. Without one: update the agent with this exact name if one exists,
    else create it. Either way the live configuration is read back and must pass verify_agent.
    """
    body = agent_config(name)
    action = "updated"
    if agent_id and not _valid_id(agent_id):
        raise ValueError("invalid agent id")
    if not agent_id:
        agent_id = _find_agent_by_name(name)
    if agent_id:
        _call("PATCH", f"/v1/convai/agents/{agent_id}", body)  # UNVERIFIED: PATCH /v1/convai/agents/{agent_id}
    else:
        created = _call("POST", "/v1/convai/agents/create", body)  # per docs/voice-intake.md
        agent_id = str(created.get("agent_id") or "")  # UNVERIFIED: the response carries agent_id
        if not _valid_id(agent_id):
            raise RuntimeError("ElevenLabs created an agent but returned no agent id")
        action = "created"
    verify_agent(agent_id, use_cache=False)
    return {"agent_id": agent_id, "action": action}
