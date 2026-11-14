# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# claims - the claim record and the export gate: every claim cites real build answers, no labels, no test leakage

"""
The claims gate (the safeguard we demonstrate)
==============================================

A profile is a list of CLAIMS, each carrying the answer IDs behind it. Before a me.md can be
exported, ``gate`` checks every claim and the rendered file, and REFUSES export (fail-closed, the
pattern of teenyverse3's publish redaction gate) when:

  1. a claim (other than a stated limit) cites no evidence;
  2. a claim cites an ID that was not answered in the build file (a skipped or unknown ID), or a
     voice ID (V01, V02, ...) that is not in the voice evidence passed in;
  3. the file or a claim cites or quotes a development-test ID (S02, S04, S06, W02, W04), which
     would leak held-out answers into generation;
  4. a claim uses a fixed personality label ("is an introvert", "personality type");
  5. the rendered file lacks text the converter declares required (``required_text``): the exact refusal of the
     "Rules for any AI reading this file" section, so a file cannot be exported without its use rules.

Warnings (shown, not blocking): absolute words outside quotations ("always", "never"), and claims
that lean on the vocabulary items B05/B40 without the language caveat.

Limits of the gate, stated plainly: it checks that a claim POINTS AT real answers; it cannot check
that the answers truly SUPPORT the wording. That second check is the employee's review, which is
why export also requires the review step in the app.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import kit
from .answers import Answers

KINDS = ("reported", "observed_style", "measured", "limit")

LABEL_PATTERNS = (
    re.compile(r"\b(?:is|are|an?)\s+(?:an?\s+)?(?:introvert|extrovert|extravert|ambivert|narcissist|people[- ]pleaser|type [a-z])\b", re.I),
    re.compile(r"\bpersonality type\b", re.I),
    re.compile(r"\b(?:INTJ|INFP|ENTJ|ENFP|ISTJ|ISFJ|ESTJ|ESFJ|INTP|INFJ|ENTP|ENFJ|ISTP|ISFP|ESTP|ESFP)\b"),
)
ABSOLUTE = re.compile(r"\b(always|never|completely|totally)\b", re.I)
QUOTED = re.compile(r"\"[^\"]*\"|'[^']*'|“[^”]*”")
TEST_ID = re.compile(r"\b(" + "|".join(sorted(kit.DEVELOPMENT_TEST_IDS)) + r")\b")


@dataclass(frozen=True)
class Claim:
    id: str
    kind: str
    text: str
    evidence: tuple[str, ...] = ()


@dataclass
class GateResult:
    blocking: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.blocking


def gate(claims: list[Claim], answers: Answers, rendered: str, voice_ids=None, required_text=()) -> GateResult:
    """``voice_ids``: the V IDs of the supplied voice evidence (``intake.VoiceEvidence.ids()``); None means no voice.
    ``required_text``: strings the rendered file must contain verbatim (the converter passes its refusal text)."""
    result = GateResult()
    answered = answers.answered_ids()
    voice_ids = frozenset(voice_ids or ())
    for claim in claims:
        if claim.kind not in KINDS:
            result.blocking.append(f"{claim.id}: unknown claim kind {claim.kind!r}")
        if claim.kind != "limit" and not claim.evidence:
            result.blocking.append(f"{claim.id}: no evidence cited")
        for evidence_id in claim.evidence:
            if evidence_id in kit.DEVELOPMENT_TEST_IDS:
                result.blocking.append(f"{claim.id}: cites held-out test answer {evidence_id}")
            elif evidence_id.startswith("V"):
                if evidence_id not in voice_ids:
                    result.blocking.append(f"{claim.id}: cites {evidence_id}, which is not in the supplied voice evidence")
            elif evidence_id not in answered:
                result.blocking.append(f"{claim.id}: cites {evidence_id}, which is not an answered build item")
        unquoted = QUOTED.sub("", claim.text)
        for pattern in LABEL_PATTERNS:
            if pattern.search(unquoted):
                result.blocking.append(f"{claim.id}: uses a fixed personality label")
                break
        if claim.kind != "limit" and ABSOLUTE.search(unquoted):
            result.warnings.append(f"{claim.id}: absolute wording ({ABSOLUTE.search(unquoted).group(0)!r}) outside a quotation")
        if set(claim.evidence) & set(kit.LANGUAGE_SENSITIVE_ITEMS) and "language" not in claim.text.lower():
            result.warnings.append(f"{claim.id}: relies on vocabulary items B05/B40; check the language caveat applies")
    for text in required_text:
        if text not in rendered:
            result.blocking.append(f"rendered profile is missing required text: {text[:60]!r}...")
    leaked = sorted(set(TEST_ID.findall(rendered)))
    if leaked:
        result.blocking.append(f"rendered profile mentions held-out test IDs: {', '.join(leaked)}")
    for test_id in kit.DEVELOPMENT_TEST_IDS & answers.answered_ids():
        result.blocking.append(f"input contains held-out test answer {test_id}; the converter must receive build answers only")
    return result
