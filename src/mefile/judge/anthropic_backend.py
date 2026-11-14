# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# anthropic_backend - the real Anthropic far side behind the JudgeBackend seam

"""
The Anthropic judge backend
===========================

The only module that imports ``anthropic``, and it does so lazily, so importing the judge package
(and running the whole test suite) never needs the SDK or a key.

- Model: ``MEFILE_JUDGE_MODEL`` (default ``claude-opus-5-5``). Effort ``high``. No temperature and
  no thinking parameter (both are fixed by the model family).
- Self-judge guard: if the judge model equals ``runner.DEFAULT_MODEL`` (the LLM A model under test),
  construction raises ``JudgeConfigError`` unless ``MEFILE_ALLOW_SELF_JUDGE=1``. A model grading its
  own answers is the self-preference risk the risk pack names; the default judge string equals the
  LLM A default, so a real run must set ``MEFILE_JUDGE_MODEL`` to a different model (or opt in).
- Structured output: ``output_config.format`` with the rubric's JSON schema.
- Server-side refusal fallback enabled (``fallbacks="default"``); the served model is recorded,
  so an evaluation always says which model actually judged it.
- Fail-closed: a refusal, an empty output or any SDK error RAISES; the orchestration turns that
  into ``judge_error`` with null scores. The key is never read, logged or interpolated here; the
  SDK client resolves it from the environment.
"""

from __future__ import annotations

import os

from .. import runner
from .backend import JudgeBackendError, JudgeRequest, JudgeResult

DEFAULT_JUDGE_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
ALLOW_SELF_JUDGE_ENV = "MEFILE_ALLOW_SELF_JUDGE"


class JudgeConfigError(RuntimeError):
    """The judge is configured in a way that would invalidate its verdicts (raised at construction)."""


class AnthropicJudgeBackend:
    def __init__(self, model: str | None = None, effort: str = "high", max_tokens: int = 16000, client=None):
        self.model = model or os.environ.get("MEFILE_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
        if self.model == runner.DEFAULT_MODEL and os.environ.get(ALLOW_SELF_JUDGE_ENV) != "1":
            raise JudgeConfigError(
                f"judge model {self.model!r} is the LLM A model under test (runner.DEFAULT_MODEL); a model must not "
                f"judge its own answers. Set MEFILE_JUDGE_MODEL to a different model, or set {ALLOW_SELF_JUDGE_ENV}=1 "
                "to accept self-judging knowingly (and report it)."
            )
        self.effort = effort
        self.max_tokens = max_tokens
        self._client = client

    def _get_client(self):
        if self._client is None:
            import anthropic  # lazy: the seam boundary

            self._client = anthropic.Anthropic()
        return self._client

    def judge(self, request: JudgeRequest) -> JudgeResult:
        client = self._get_client()
        response = client.beta.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            system=request.system,
            messages=[{"role": "user", "content": request.user}],
            output_config={
                "effort": self.effort,
                "format": {"type": "json_schema", "schema": request.schema},
            },
        )
        if response.stop_reason == "refusal":
            category = getattr(getattr(response, "stop_details", None), "category", None)
            raise JudgeBackendError(f"judge model refused (category: {category})")
        if response.stop_reason == "max_tokens":
            raise JudgeBackendError("judge output truncated at max_tokens")
        text = next((block.text for block in response.content if getattr(block, "type", None) == "text"), "")
        if not text.strip():
            raise JudgeBackendError("judge returned no text")
        return JudgeResult(raw_text=text, served_model=str(getattr(response, "model", self.model)))
