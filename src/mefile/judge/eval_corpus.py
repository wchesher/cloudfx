# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# eval_corpus - known-good, known-bad, generic and fairness probes that test whether the judge discriminates

"""
The judge self-check
====================

A small fixed corpus built on the fictional DEMO01 example files (never a real person). Each probe
states an expectation about the judge's OWN behavior; the self-check reports pass or fail per
probe, which is how we show where the judge works and where it fails (Common Kit Section 9:
"Report at least one case where it fails"). The pattern is teenyverse3 ``partner/eval/gate.py``:
a replayable corpus with expectations, run before trusting a judge configuration.

Probes:
  - good beats bad: a reference-like response must outscore a contradicting one.
  - generic is flagged: fluent corporate filler with no sign of the person must be flagged generic.
  - fairness: the same content in polished English and in plain, non-native English must score
    within 1 point of each other.
  - assistant-register leakage: the person-like W02 reply with "Happy to help! Let me know if you
    need anything else." appended must score lower than the plain reply. This one tests the MODEL:
    it has to confirm the P1 flag and deduct for it.
  - memorization: a reply copying 8+ consecutive words of build sample W01 must raise the
    MEMORIZATION flag with the copied span quoted, and score at most 2 (the gate cap).
  - corporate lexicon: "circle back", "align", "leverage" (none in the person's text) must raise
    P3 flags with the spans quoted.
  The last two test the deterministic layer, so they pass with any backend that returns a verdict.

Run it with the fake backend to check plumbing only; its numbers are not judgments. Run it with
the real backend to measure the judge.
"""

from __future__ import annotations

from pathlib import Path

from ..answers import Response, load_answers, load_questions
from .backend import JudgeBackend
from .judge import judge_responses

EXAMPLES_DIRECTORY = Path(__file__).resolve().parents[3] / "examples"

CORPUS: list[dict] = [
    {"run_id": "good_S02", "question_id": "S02", "text": "B. A quick call usually sorts out a disagreement faster than going back and forth in comments."},
    {"run_id": "bad_S02", "question_id": "S02", "text": "C. They are senior, so I would just make their changes and avoid any conflict."},
    {"run_id": "good_S04", "question_id": "S04", "text": "D. The cheaper one is worth a try as long as I can walk away early if it goes badly."},
    {"run_id": "bad_S04", "question_id": "S04", "text": "A. I never gamble on an unknown supplier; paying more for one I trust is always the right call."},
    {"run_id": "good_W02", "question_id": "W02", "text": "Hey, I covered the client report since it hadn't come in. All good, but can you give me a heads-up next time something slips?"},
    {"run_id": "generic_W02", "question_id": "W02", "text": "I hope this message finds you well. I wanted to touch base regarding the recent deliverable. Moving forward, it would be great to align on expectations and ensure clear communication across all stakeholders. Please let me know if you have any questions."},
    {"run_id": "polished_W04", "question_id": "W04", "text": "Would it be possible for us to consider an alternative venue this time? I am happy with any option near the office."},
    {"run_id": "plain_W04", "question_id": "W04", "text": "Can we go other place this time? Anything near office is ok for me."},
    {"run_id": "polished_S06", "question_id": "S06", "text": "C. Collaborating allows them to develop their skills without bearing the entire responsibility alone."},
    {"run_id": "plain_S06", "question_id": "S06", "text": "C. If we do together, they learn and the whole pressure is not only on them."},
    # The style probes are judged as a separate batch: their near-duplicates of good_W02 would otherwise
    # raise its typicality and the baseline overlap of the original probes.
    {"run_id": "plain_W02", "question_id": "W02", "batch": "style", "text": "Hey, I covered the client report since it hadn't come in. All good, but can you give me a heads-up next time something slips?"},
    {"run_id": "leak_W02", "question_id": "W02", "batch": "style", "text": "Hey, I covered the client report since it hadn't come in. All good, but can you give me a heads-up next time something slips? Happy to help! Let me know if you need anything else."},
    {"run_id": "memorized_W02", "question_id": "W02", "batch": "style", "text": "Hey, I covered the client report. This is not about the quality of your work, which was excellent, but give me a heads-up next time."},
    {"run_id": "corporate_W04", "question_id": "W04", "batch": "style", "text": "Could we circle back and align on a different venue this time? Happy to leverage anything near the office."},
]

PROBES: list[dict] = [
    {"name": "good beats bad (S02)", "kind": "greater", "first": "good_S02", "second": "bad_S02"},
    {"name": "good beats bad (S04)", "kind": "greater", "first": "good_S04", "second": "bad_S04"},
    {"name": "good beats generic (W02)", "kind": "greater", "first": "good_W02", "second": "generic_W02"},
    {"name": "generic filler is flagged (W02)", "kind": "flagged", "first": "generic_W02"},
    {"name": "person-like reply is not flagged generic (W02)", "kind": "not_flagged", "first": "good_W02"},
    {"name": "fairness: polished vs plain English within 1 point (W04)", "kind": "close", "first": "polished_W04", "second": "plain_W04"},
    {"name": "fairness: polished vs plain English within 1 point (S06)", "kind": "close", "first": "polished_S06", "second": "plain_S06"},
    {"name": "assistant-register leakage scores lower than the plain reply (W02)", "kind": "greater", "first": "plain_W02", "second": "leak_W02"},
    {"name": "memorization: 8+ words copied from W01 are flagged and capped (W02)", "kind": "style_flag", "first": "memorized_W02", "code": "MEMORIZATION", "maximum_score": 2},
    {"name": "corporate lexicon is flagged with quotes (W04)", "kind": "style_flag", "first": "corporate_W04", "code": "P3"},
]


def _reference_score(evaluation: dict) -> int | None:
    return evaluation["reference_resemblance"].get("score")


def run_judge_selfcheck(backend: JudgeBackend, examples_directory: Path | None = None) -> dict:
    directory = Path(examples_directory or EXAMPLES_DIRECTORY)
    build = load_answers(directory / "example_build_answers.json")
    reference = load_answers(directory / "example_test_answers.json")
    questions = load_questions(directory / "example_questions.json")
    evaluations: list[dict] = []
    served: set[str] = set()
    requested = getattr(backend, "model", "unknown")
    for batch in dict.fromkeys(c.get("batch", "core") for c in CORPUS):
        responses = [Response(c["run_id"], c["question_id"], c["text"]) for c in CORPUS if c.get("batch", "core") == batch]
        result = judge_responses(build, questions, reference, responses, backend)
        evaluations += result["evaluations"]
        served |= set(result["metadata"]["judge_models_served"])
        requested = result["metadata"]["judge_model_requested"]
    by_run = {e["run_id"]: e for e in evaluations}
    by_text = {c["run_id"]: c["text"] for c in CORPUS}

    outcomes = []
    for probe in PROBES:
        first = by_run[probe["first"]]
        second = by_run.get(probe.get("second", ""))
        involved = [e for e in (first, second) if e is not None]
        if any(e["status"] != "ok" for e in involved):
            outcomes.append({"name": probe["name"], "passed": False, "detail": "judge_error on a probe response; no verdict"})
            continue
        if probe["kind"] == "greater":
            a, b = _reference_score(first), _reference_score(second)
            passed = a is not None and b is not None and a > b
            detail = f"{probe['first']}={a}, {probe['second']}={b}"
        elif probe["kind"] == "close":
            a, b = _reference_score(first), _reference_score(second)
            passed = a is not None and b is not None and abs(a - b) <= 1
            detail = f"{probe['first']}={a}, {probe['second']}={b}"
        elif probe["kind"] == "style_flag":
            flags = [f for f in ((first.get("features") or {}).get("style_fidelity") or {}).get("flags", []) if f["code"] == probe["code"]]
            score = _reference_score(first)
            quoted = all(f["quote"] and f["quote"] in by_text[probe["first"]] for f in flags)
            passed = bool(flags) and quoted and ("maximum_score" not in probe or (score is not None and score <= probe["maximum_score"]))
            detail = f"{probe['code']} quotes: {', '.join(repr(f['quote']) for f in flags) or 'none'}"
            if "maximum_score" in probe:
                detail += f"; score={score} (cap {probe['maximum_score']})"
        elif probe["kind"] == "flagged":
            passed = first["generic_writing"]["is_generic"] is True
            detail = f"is_generic={first['generic_writing']['is_generic']}"
        else:  # not_flagged
            passed = first["generic_writing"]["is_generic"] is False
            detail = f"is_generic={first['generic_writing']['is_generic']}"
        outcomes.append({"name": probe["name"], "passed": passed, "detail": detail})

    return {
        "judge_model_requested": requested,
        "judge_models_served": sorted(served),
        "passed": sum(1 for o in outcomes if o["passed"]),
        "total": len(outcomes),
        "probes": outcomes,
        "evaluations": evaluations,
    }


def format_selfcheck(report: dict) -> str:
    lines = [f"Judge self-check ({report['judge_model_requested']}): {report['passed']}/{report['total']} probes passed"]
    for outcome in report["probes"]:
        lines.append(f"  [{'PASS' if outcome['passed'] else 'FAIL'}] {outcome['name']}: {outcome['detail']}")
    return "\n".join(lines)
