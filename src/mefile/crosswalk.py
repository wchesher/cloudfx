# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# crosswalk - Big Five and scenario evidence mapped onto the four Wethos Style scales, as labelled hypotheses only

"""
Wethos Style crosswalk (HYPOTHESES, not measurements)
=====================================================

Wethos Style measures behavior on four scales with its own instrument: Ideas (Practical to
Visionary), Relational (Factual to Interpersonal), Action (Methodical to Expedient) and Order
(Flexible to Structured). Nothing in the Common Kit measures those scales. This module states
where the kit evidence would place a person IF the conceptual overlap holds, cites the answers,
and says how strong the evidence is, so the result can seed a conversation inside Wethos, never
replace its assessment. Same honesty rule as Wethos's own Observed Twins: assumptions are
hypotheses.
"""

from __future__ import annotations

from . import scoring
from .answers import Answers

SCALES = {
    "ideas": ("Ideas", "Practical", "Visionary", "intellect"),
    "relational": ("Relational", "Factual", "Interpersonal", "agreeableness"),
    "order": ("Order", "Flexible", "Structured", "conscientiousness"),
}

ORDER_ITEMS = ("B33", "B43", "B08", "B28")  # like order, follow a schedule, (rev) leave belongings, (rev) forget to put back


def _lean(mean: float | None, low_pole: str, high_pole: str) -> str:
    if mean is None:
        return "no evidence"
    if mean >= 3.5:
        return f"leans {high_pole}"
    if mean <= 2.5:
        return f"leans {low_pole}"
    return "between the poles"


def wethos_style_hypotheses(answers: Answers, scores: list[scoring.DomainScore], excluded: set[str]) -> dict:
    by_key = {ds.domain.key: ds for ds in scores}
    out: dict[str, dict] = {}
    for key, (label, low, high, domain_key) in SCALES.items():
        ds = by_key[domain_key]
        if domain_key in excluded:
            out[key] = {"scale": label, "hypothesis": "withheld by the person", "evidence": [], "strength": "none"}
            continue
        evidence = list(ds.answered)
        mean = ds.mean
        if key == "order":
            order_scores = [ds.keyed_scores[i] for i in ORDER_ITEMS if i in ds.keyed_scores]
            if order_scores:
                mean = round(sum(order_scores) / len(order_scores), 2)
                evidence = [i for i in ORDER_ITEMS if i in ds.keyed_scores]
        out[key] = {
            "scale": f"{label} ({low} to {high})",
            "hypothesis": _lean(mean, low, high),
            "basis": f"{ds.domain.label} items, mean {mean}" if mean is not None else "not scored",
            "evidence": evidence,
            "strength": "weak: conceptual overlap only, different instrument",
        }
    s03 = answers.scenarios.get("S03", {}).get("choice")
    action = {
        "A": ("leans Expedient", "rolls back immediately to close the problem"),
        "B": ("leans Expedient", "acts quickly within a time box"),
        "C": ("leans Methodical", "waits for the lead before acting"),
        "D": ("leans Methodical", "measures impact before deciding"),
    }.get(s03)
    out["action"] = {
        "scale": "Action (Methodical to Expedient)",
        "hypothesis": action[0] if action else "no evidence",
        "basis": f"S03 choice {s03}: {action[1]}" if action else "S03 not answered",
        "evidence": ["S03"] if action else [],
        "strength": "very weak: a single scenario",
    }
    out["_notice"] = ("Hypotheses for discussion inside Wethos, not Wethos Style scores. Wethos Style measures behavior "
                      "with its own instrument; the Common Kit does not.")
    return out
