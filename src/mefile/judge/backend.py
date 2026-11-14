# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# backend - the JudgeBackend seam, its request/result types, and a deterministic fake for tests

"""
The judge seam
==============

``JudgeBackend`` is the one port the orchestration calls. The real far side
(``anthropic_backend.AnthropicJudgeBackend``) is the only module allowed to import a vendor SDK,
so the judge can run a stronger or different model than the generators without touching the
orchestration, and the whole suite runs without network or keys.

A backend RAISES on any failure (transport, refusal, empty output). The orchestration turns a
raise into ``judge_error`` with null scores: a broken judge never fabricates a pass.

``FakeJudgeBackend`` is a plumbing stand-in, not a judge. Its heuristic mode scores word overlap
with the recorded answer so the self-check can exercise every path offline; its numbers mean
nothing about personality.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from . import features as feature_module


class JudgeBackendError(RuntimeError):
    """The backend could not produce a verdict (outage, refusal, empty output)."""


@dataclass(frozen=True)
class JudgeRequest:
    system: str
    user: str
    schema: dict[str, Any]
    # Non-prompt context for fakes and logging only. Never includes run_id or source.
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JudgeResult:
    raw_text: str
    served_model: str


class JudgeBackend(Protocol):
    model: str

    def judge(self, request: JudgeRequest) -> JudgeResult: ...


class FakeJudgeBackend:
    """Deterministic stand-in. mode: 'heuristic' | 'raise' | 'invalid' | 'fixed', or a callable."""

    def __init__(self, mode: str | Callable[[JudgeRequest], str] = "heuristic", fixed: dict | None = None, model: str = "fake-judge"):
        self.mode = mode
        self.fixed = fixed
        self.model = model
        self.requests: list[JudgeRequest] = []

    def judge(self, request: JudgeRequest) -> JudgeResult:
        self.requests.append(request)
        if callable(self.mode):
            return JudgeResult(self.mode(request), self.model)
        if self.mode == "raise":
            raise JudgeBackendError("fake backend outage")
        if self.mode == "invalid":
            return JudgeResult("this is not json {", self.model)
        if self.mode == "fixed":
            return JudgeResult(json.dumps(self.fixed), self.model)
        return JudgeResult(json.dumps(self._heuristic(request.context)), self.model)

    @staticmethod
    def _heuristic(context: dict[str, Any]) -> dict[str, Any]:
        response_tokens = feature_module.content_tokens(context.get("response_text", ""))
        reference_text = context.get("reference_text")
        is_scenario = context.get("question_type") == "scenario"
        maximum = 2 if is_scenario else 4
        typicality = context.get("typicality") or 0.0
        first_person = any(w.lower() in ("i", "i'm", "i'd", "i'll", "me", "my") for w in feature_module.words(context.get("response_text", "")))
        is_generic = typicality >= 0.35 or not first_person
        if reference_text is None:
            reference = {"score": None, "insufficient_evidence": True, "explanation": "No recorded answer.", "evidence_ids": []}
        else:
            overlap = feature_module.jaccard(response_tokens, feature_module.content_tokens(reference_text))
            score = min(maximum, round(overlap * maximum * 3))
            reference = {
                "score": score,
                "insufficient_evidence": False,
                "explanation": f"Heuristic stand-in: content-word overlap {overlap:.2f} with the recorded answer.",
                "evidence_ids": [context.get("question_id", "")],
            }
        return {
            "reference_resemblance": reference,
            "profile_consistency": {
                "score": None,
                "insufficient_evidence": True,
                "explanation": "Heuristic stand-in does not rate profile consistency.",
                "evidence_ids": [],
            },
            "generic_writing": {
                "is_generic": is_generic,
                "explanation": f"Heuristic stand-in: typicality {typicality}, first person {'present' if first_person else 'absent'}.",
            },
            "matches": [],
            "mismatches": [],
            "language_note": "Heuristic stand-in ignores language and style.",
        }
