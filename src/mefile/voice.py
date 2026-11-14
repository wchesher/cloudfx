# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# voice - ElevenLabs Agents voice interview: signed session URL, transcript fetch (employee turns only), deletion

"""
Voice intake (optional extra credit, Common Kit Section 11)
===========================================================

A purpose-built ElevenLabs agent runs a ~10 minute behavioral interview. We keep the TRANSCRIPT of
the employee's own words and nothing else:

  - never tone of voice: inferring emotion from voice at work is prohibited under EU AI Act
    Article 5(1)(f); we analyze text only;
  - never a voice clone: the twin answers in text (or a stock synthetic voice), never the person's;
  - audio recording should be switched OFF on the agent (platform_settings.privacy.record_voice =
    false) and the conversation deleted from ElevenLabs once the transcript is saved.

The API key stays on the server; the browser only ever receives a short-lived signed URL.
Standard library only (urllib), the pattern of teenyverse3's stdlib ElevenLabs clients.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.elevenlabs.io"


def configured() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY") and os.environ.get("ELEVENLABS_AGENT_ID"))


def _call(method: str, path: str) -> dict:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("voice intake is not configured (ELEVENLABS_API_KEY missing)")
    request = urllib.request.Request(API + path, method=method, headers={"xi-api-key": key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"ElevenLabs returned {error.code} for {path.split('?')[0]}") from None


def start_session() -> dict:
    agent_id = os.environ.get("ELEVENLABS_AGENT_ID")
    if not agent_id:
        raise RuntimeError("voice intake is not configured (ELEVENLABS_AGENT_ID missing)")
    data = _call("GET", "/v1/convai/conversation/get-signed-url?" + urllib.parse.urlencode({"agent_id": agent_id}))
    return {"signed_url": data["signed_url"]}


def fetch_transcript(conversation_id: str) -> dict:
    if not conversation_id or not conversation_id.replace("_", "").replace("-", "").isalnum():
        raise RuntimeError("invalid conversation id")
    data = _call("GET", f"/v1/convai/conversations/{conversation_id}")
    turns = data.get("transcript") or []
    employee = [{"index": i, "seconds": t.get("time_in_call_secs"), "text": (t.get("message") or "").strip()}
                for i, t in enumerate(turns) if t.get("role") == "user" and (t.get("message") or "").strip()]
    interviewer = [{"index": i, "text": (t.get("message") or "").strip()}
                   for i, t in enumerate(turns) if t.get("role") == "agent"]
    return {
        "conversation_id": conversation_id,
        "status": data.get("status"),
        "duration_seconds": (data.get("metadata") or {}).get("call_duration_secs"),
        "employee_turns": employee,
        "interviewer_turns": interviewer,
    }


def delete_conversation(conversation_id: str) -> None:
    _call("DELETE", f"/v1/convai/conversations/{conversation_id}")


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

AGENT_SYSTEM_PROMPT = """You are a friendly, neutral workplace interviewer for a voluntary coaching profile. Before the
first question, say that you are an AI interviewer, that the conversation is transcribed (text only) to build a
profile the person controls, and that they can skip any question or stop at any time. Ask the questions below one at a
time, in order. After each answer ask at most one short follow-up: "What did you do?" or "What did you say?". Keep to
work situations only: never ask about health, family, religion, politics, age, ethnicity, or anything outside work. Do
not give advice, do not evaluate answers, do not comment on the person's personality. Finish after the last question by
thanking them. Questions:
""" + "\n".join(f"{i + 1}. {q}" for i, (_, q) in enumerate(INTERVIEW_GUIDE))
