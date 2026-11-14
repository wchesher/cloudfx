# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# runner - replay the official loading protocol on the Claude API: new conversation, me.md first, then the question

"""
The loading protocol, automated for development runs (Common Kit Section 9)
==========================================================================

"Start a new conversation for each question, with memory and custom instructions turned off. Paste
the full me.md as the first message, then paste the question exactly as given."

So each run is TWO user turns in a fresh conversation: turn 1 is the whole me.md (the model
replies, ideally "Ready."), turn 2 is the question's ``prompt`` verbatim. The no-profile condition
is the question alone. No system prompt, so nothing is added that a chat window would not have.

LLM A is "Claude Opus 5.5 Medium": model ``claude-opus-5-5`` at effort ``medium``. No fallback
model is configured here on purpose: a fallback would silently answer with a different model than
the one the protocol designates. The served model is recorded on every response.

LLM B (GPT Sol 6.1 Medium) runs through its own chat window using the paste packets that
``mefile final`` writes; its responses go into the same JSON format.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .answers import Question

DEFAULT_MODEL = os.environ.get("MEFILE_LLM_A_MODEL", "claude-opus-5-5")
DEFAULT_EFFORT = os.environ.get("MEFILE_LLM_A_EFFORT", "medium")


def _text_of(response) -> str:
    if response.stop_reason == "refusal":
        raise RuntimeError("the model declined this request (stop_reason refusal)")
    return "".join(block.text for block in response.content if block.type == "text").strip()


def ask(client, profile: str | None, question: Question, model: str = DEFAULT_MODEL, effort: str = DEFAULT_EFFORT) -> dict:
    messages: list[dict] = []
    first_reply = None
    if profile is not None:
        messages.append({"role": "user", "content": profile})
        first = client.messages.create(model=model, max_tokens=4000, output_config={"effort": effort}, messages=messages)
        first_reply = _text_of(first)
        messages.append({"role": "assistant", "content": first_reply or "Ready."})
    messages.append({"role": "user", "content": question.prompt})
    response = client.messages.create(model=model, max_tokens=4000, output_config={"effort": effort}, messages=messages)
    return {
        "text": _text_of(response),
        "first_reply": first_reply,
        "model_requested": model,
        "model_served": response.model,
        "effort": effort,
    }


def run_all(profile: str | None, questions: dict[str, Question], run_prefix: str, out_path: Path,
            model: str = DEFAULT_MODEL, effort: str = DEFAULT_EFFORT) -> list[dict]:
    import anthropic  # lazily: the rest of mefile never needs the SDK

    client = anthropic.Anthropic()
    records = []
    for question_id, question in questions.items():
        result = ask(client, profile, question, model, effort)
        records.append({"run_id": f"{run_prefix}-{question_id}", "question_id": question_id, **result,
                        "condition": "profile" if profile is not None else "no_profile",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})
        print(f"{run_prefix}-{question_id}: {result['text'][:90]}")
    out = {"responses": [{"run_id": r["run_id"], "question_id": r["question_id"], "text": r["text"]} for r in records],
           "provenance": records}
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return records
