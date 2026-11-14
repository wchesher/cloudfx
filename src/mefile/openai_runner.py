# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# openai_runner - replay the official loading protocol for LLM B on the OpenAI Responses API (stdlib urllib, no SDK)

"""
LLM B through the OpenAI API (Common Kit Section 9, the same protocol as runner.py)
===================================================================================

"Load the file the same way in every test and in the final evaluation. Start a new conversation for
each question, with memory and custom instructions turned off. Paste the full me.md as the first
message, then paste the question exactly as given. For the no-profile comparison, do the same
without the file. Record the model name shown."

This mirrors ``runner.ask`` (LLM A on Claude) exactly: each run is a fresh conversation of TWO user
turns. Turn 1 is the whole me.md; the model's reply is kept and sent back as the assistant turn;
turn 2 is the question's ``prompt`` verbatim. The no-profile condition is the question alone. No
system prompt and no ``instructions``, so nothing is added that a chat window would not have. Each
call is stateless (the conversation is resent in ``input``; ``previous_response_id`` is never used),
which is what "a new conversation, memory off" means on an API.

Configuration (environment only, read per call):

- ``OPENAI_API_KEY``: the key. Never logged, never put in an error message.
- ``MEFILE_LLM_B_MODEL``: the model id exactly as OpenAI lists it. There is NO default: we do not
  know the API id behind the hackathon's "GPT Sol 6.1", and a guessed id would silently test a
  different model than the one the protocol designates.
- ``MEFILE_LLM_B_EFFORT``: the reasoning effort, default ``medium`` ("GPT Sol 6.1 Medium").

No fallback model. Refusal, an incomplete reply (token cap, content filter) or empty text is an
error, never a silent cut. The served model (the response's ``model``) is recorded on every run; the
response id is not stored.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from .answers import Question

API_URL = "https://api.openai.com/v1/responses"
KEY_ENVIRONMENT = "OPENAI_API_KEY"
MODEL_ENVIRONMENT = "MEFILE_LLM_B_MODEL"
EFFORT_ENVIRONMENT = "MEFILE_LLM_B_EFFORT"
DEFAULT_EFFORT = "medium"
MAX_OUTPUT_TOKENS = 32000  # reasoning tokens count against this cap too; a capped reply is an error, never a silent cut
TIMEOUT_SECONDS = 300
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
BACKOFF_SECONDS = 4.0
MAX_BACKOFF_SECONDS = 30.0
MODEL_MISSING_MESSAGE = f"set {MODEL_ENVIRONMENT} to the model id exactly as OpenAI lists it"
KEY_MISSING_MESSAGE = f"set {KEY_ENVIRONMENT} (on the box: sudo update-lumin8r --set-key {KEY_ENVIRONMENT})"

_KEY_SHAPE = re.compile(r"sk-[A-Za-z0-9_*.\-]{4,}")
urlopen = urllib.request.urlopen  # the one network call; tests replace this name


class OpenAIRunError(RuntimeError):
    """LLM B through the API could not produce an honest answer. The message never carries the key."""


class NotConfigured(OpenAIRunError):
    """A required setting (key or model id) is missing."""


def configured_model() -> str:
    return os.environ.get(MODEL_ENVIRONMENT, "").strip()


def configured_effort() -> str:
    return os.environ.get(EFFORT_ENVIRONMENT, "").strip() or DEFAULT_EFFORT


def configured() -> bool:
    """True when LLM B can run through the API: a key and an explicit model id are both set."""
    return bool(os.environ.get(KEY_ENVIRONMENT, "").strip()) and bool(configured_model())


def status() -> dict:
    """What a page or the console may show: configured or not, the model id and effort. Never the key."""
    missing = [name for name, value in ((KEY_ENVIRONMENT, os.environ.get(KEY_ENVIRONMENT, "").strip()),
                                        (MODEL_ENVIRONMENT, configured_model())) if not value]
    return {"configured": not missing, "model": configured_model() or None, "effort": configured_effort(),
            "missing": missing}


def _redact(text: str, key: str) -> str:
    """The text with the key, and anything shaped like an OpenAI key, removed (OpenAI echoes a masked key on 401)."""
    if key:
        text = text.replace(key, "[redacted]")
    return _KEY_SHAPE.sub("[redacted]", text)


def _http_error_message(error: urllib.error.HTTPError, key: str) -> str:
    detail = ""
    try:
        body = json.loads(error.read().decode("utf-8", "replace") or "{}")
        problem = body.get("error") if isinstance(body, dict) else None
        if isinstance(problem, dict):
            kind = problem.get("type") or problem.get("code") or ""
            detail = f"{kind}: {problem.get('message') or ''}".strip(": ")
    except (ValueError, OSError, AttributeError):
        detail = ""
    message = f"OpenAI API returned HTTP {error.code}" + (f" ({detail[:300]})" if detail else "")
    return _redact(message, key)


def _retry_wait(error: urllib.error.HTTPError) -> float:
    try:
        value = float((error.headers or {}).get("Retry-After", ""))
    except (TypeError, ValueError):
        value = BACKOFF_SECONDS
    return max(0.0, min(value, MAX_BACKOFF_SECONDS))


def _post(payload: dict, key: str) -> dict:
    """POST to the Responses API; one retry on 429 or 5xx after a backoff. Raises OpenAIRunError without the key."""
    data = json.dumps(payload).encode("utf-8")
    for attempt in (1, 2):
        request = urllib.request.Request(API_URL, data=data, method="POST", headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code in RETRY_STATUSES and attempt == 1:
                time.sleep(_retry_wait(error))
                continue
            raise OpenAIRunError(_http_error_message(error, key)) from None
        except urllib.error.URLError as error:
            raise OpenAIRunError(_redact(f"OpenAI API unreachable: {error.reason}", key)) from None
        except ValueError:
            raise OpenAIRunError("OpenAI API answered with something that is not JSON") from None
    raise OpenAIRunError("OpenAI API did not answer")  # not reached: the second attempt returns or raises


def _text_of(response: dict) -> str:
    """The reply text from the output items of type "message", content type "output_text". Loud on anything else."""
    state = response.get("status")
    if state == "incomplete":
        # UNVERIFIED: incomplete_details.reason ("max_output_tokens" or "content_filter" as documented)
        reason = (response.get("incomplete_details") or {}).get("reason") or "no reason given"
        if reason == "max_output_tokens":
            raise OpenAIRunError("the reply hit the output token cap before it finished (status incomplete, "
                                 "reason max_output_tokens); nothing was saved")
        raise OpenAIRunError(f"the reply is incomplete (status incomplete, reason {reason}); nothing was saved")
    if state not in (None, "completed"):
        problem = response.get("error") or {}
        detail = problem.get("message") if isinstance(problem, dict) else ""
        raise OpenAIRunError(f"the response did not complete (status {state}){': ' + str(detail)[:200] if detail else ''}")
    parts = []
    for item in response.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue  # reasoning items carry no answer text
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            if content.get("type") == "refusal":  # UNVERIFIED: refusal content part {"type": "refusal", "refusal": text}
                raise OpenAIRunError("the model declined this request (refusal content)")
            if content.get("type") == "output_text":
                parts.append(str(content.get("text") or ""))
    text = "".join(parts).strip()
    if not text:
        raise OpenAIRunError(f"the model returned no text (status {state or 'not given'})")
    return text


def require_settings(model: str | None, effort: str | None) -> tuple[str, str, str]:
    key = os.environ.get(KEY_ENVIRONMENT, "").strip()
    model = (model or configured_model()).strip()
    if not model:
        raise NotConfigured(MODEL_MISSING_MESSAGE)
    if not key:
        raise NotConfigured(KEY_MISSING_MESSAGE)
    return key, model, (effort or configured_effort()).strip()


def _request(messages: list[dict], model: str, effort: str) -> dict:
    return {
        "model": model,
        "input": messages,  # the whole conversation, resent every call: stateless, no previous_response_id
        "reasoning": {"effort": effort},
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        # store false: OpenAI does not keep this conversation for later retrieval through the API. It does NOT
        # change OpenAI's abuse-monitoring retention, which applies under OpenAI's own data policy either way.
        "store": False,
        # no "instructions" and no system or developer message: nothing a chat window would not have
    }


def ask(profile: str | None, question: Question, model: str | None = None, effort: str | None = None) -> dict:
    """One run of the loading protocol on LLM B. Returns the same record shape as runner.ask."""
    key, model, effort = require_settings(model, effort)
    # UNVERIFIED: an EasyInputMessage {"role", "content": string} is accepted for the assistant turn as well as user turns
    messages: list[dict] = []
    first_reply = None
    if profile is not None:
        messages.append({"role": "user", "content": profile})
        first_reply = _text_of(_post(_request(messages, model, effort), key))
        messages.append({"role": "assistant", "content": first_reply or "Ready."})
    messages.append({"role": "user", "content": question.prompt})
    response = _post(_request(messages, model, effort), key)
    return {
        "text": _text_of(response),
        "first_reply": first_reply,
        "model_requested": model,
        "model_served": str(response.get("model") or ""),
        "effort": effort,
    }


def run_all(profile: str | None, questions: dict[str, Question], run_prefix: str, out_path: Path,
            model: str | None = None, effort: str | None = None) -> list[dict]:
    """runner.run_all for LLM B: every question, the comparison format plus provenance, written to out_path."""
    require_settings(model, effort)  # fail before the first call, not halfway through
    records = []
    for question_id, question in questions.items():
        result = ask(profile, question, model, effort)
        records.append({"run_id": f"{run_prefix}-{question_id}", "question_id": question_id, **result,
                        "condition": "profile" if profile is not None else "no_profile",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})
        print(f"{run_prefix}-{question_id}: {result['text'][:90]}")
    out = {"responses": [{"run_id": r["run_id"], "question_id": r["question_id"], "text": r["text"]} for r in records],
           "provenance": records}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return records
