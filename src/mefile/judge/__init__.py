# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# judge - the AI judge: scores model responses against what the person actually said and the build evidence

"""
The AI judge (Common Kit Section 8)
===================================

Pure orchestration over one injected port (``JudgeBackend``), plus deterministic features computed
without any model. The pattern is teenyverse3 ``partner/classifier.py``: the judge is a SEAM so its
model is a spec field, the prompt is GENERATED from data (``rubric.py``), and the gate fails CLOSED:
a backend exception or an unparseable verdict becomes ``status = "judge_error"`` with null scores,
never a fabricated number.
"""

from .backend import FakeJudgeBackend, JudgeBackend, JudgeBackendError
from .judge import judge_responses
from .rubric import DECLARED_SCALE

__all__ = [
    "DECLARED_SCALE",
    "FakeJudgeBackend",
    "JudgeBackend",
    "JudgeBackendError",
    "judge_responses",
]
