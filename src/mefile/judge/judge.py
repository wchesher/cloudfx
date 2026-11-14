# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# judge - orchestration: anonymize, compute features, call the backend, validate, combine, fail closed

"""
Judge orchestration
===================

For each response:
  1. Resolve the question (the question file first, the kit's own text second), so IDs the judge
     has never seen work as long as the question file carries them.
  2. Compute deterministic features, including the scenario choice match.
  3. Build an ANONYMOUS request: the model sees the question, the build evidence, the person's
     recorded answer and the response text. It never sees run_id or which system wrote it.
  4. Validate the verdict strictly. Any backend exception or schema-invalid verdict is
     ``judge_error`` with null scores; nothing is fabricated (fail-closed, teenyverse3
     ``partner/classifier.py``).
  5. Combine: scenario reference score = 2 points for the same choice (deterministic) + 0-2 for
     the reason, derived from the model's decision-card agreement labels; writing = the model's
     0-4 for content and tone, minus a style deduction of at most 2 (at most 1 per confirmed style
     category, and only for flags quoting a real span of the response), capped at 2 when the
     deterministic memorization or baseline gate fires.

The decision-card and style-fidelity methods are the teammates' DPM pipeline design
(``contrib/dpm-pipeline/judge_prompt.txt``), held here to lumin8r's declared 0-4 contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .. import kit
from ..answers import Answers, Question, Response
from . import features as feature_module
from . import rubric
from .backend import JudgeBackend, JudgeRequest


class InvalidVerdict(ValueError):
    pass


def resolve_question(question_id: str, questions: dict[str, Question]) -> Question | None:
    if question_id in questions:
        return questions[question_id]
    if question_id in kit.SCENARIOS:
        scenario = kit.SCENARIOS[question_id]
        return Question(question_id, "scenario", scenario["wording"], dict(scenario["options"]), kit.SCENARIO_WORD_LIMIT, "")
    if question_id in kit.WRITING_PROMPTS:
        return Question(question_id, "writing", kit.WRITING_PROMPTS[question_id], None, kit.WRITING_WORD_LIMIT, "")
    return None


def reference_for(question: Question, reference: Answers | None) -> dict | None:
    if reference is None:
        return None
    if question.type == "scenario" and question.id in reference.scenarios:
        return dict(reference.scenarios[question.id])
    if question.type == "writing" and question.id in reference.writing:
        return {"text": reference.writing[question.id]}
    return None


def _validate_dimension(raw: Any, name: str, maximum: int) -> dict:
    if not isinstance(raw, dict):
        raise InvalidVerdict(f"{name} is not an object")
    score = raw.get("score")
    insufficient = raw.get("insufficient_evidence")
    explanation = raw.get("explanation")
    evidence_ids = raw.get("evidence_ids")
    if not isinstance(insufficient, bool):
        raise InvalidVerdict(f"{name}.insufficient_evidence is not a boolean")
    if not isinstance(explanation, str):
        raise InvalidVerdict(f"{name}.explanation is not a string")
    if not isinstance(evidence_ids, list) or not all(isinstance(i, str) for i in evidence_ids):
        raise InvalidVerdict(f"{name}.evidence_ids is not a list of strings")
    if insufficient:
        score = None
    else:
        if isinstance(score, bool) or not isinstance(score, int):
            raise InvalidVerdict(f"{name}.score is missing while insufficient_evidence is false")
        if not rubric.SCALE_MINIMUM <= score <= maximum:
            raise InvalidVerdict(f"{name}.score {score} is outside 0-{maximum}")
    return {"score": score, "insufficient_evidence": insufficient, "explanation": explanation.strip(), "evidence_ids": evidence_ids}


V2_FIELDS = ("decision_cards", "style_deduction", "style_flags", "fix_hints")
HINT_LEAK_MINIMUM_WORDS = 5  # a fix hint sharing this many consecutive words with the recorded answer is withheld


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise InvalidVerdict(f"{name} is not a list of strings")
    return [v.strip() for v in value]


def _validate_card(raw: Any, name: str) -> dict:
    if not isinstance(raw, dict):
        raise InvalidVerdict(f"{name} is not an object")
    for key in ("choice", "tradeoff"):
        if not isinstance(raw.get(key), str):
            raise InvalidVerdict(f"{name}.{key} is not a string")
    rationale = _string_list(raw.get("rationale"), f"{name}.rationale")
    if len(rationale) > rubric.DECISION_CARD_RATIONALE_MAXIMUM:
        raise InvalidVerdict(f"{name}.rationale has {len(rationale)} reasons; at most {rubric.DECISION_CARD_RATIONALE_MAXIMUM}")
    if raw.get("commitment") not in rubric.COMMITMENT_VALUES:
        raise InvalidVerdict(f"{name}.commitment {raw.get('commitment')!r} is not one of {', '.join(rubric.COMMITMENT_VALUES)}")
    return {
        "choice": raw["choice"].strip(),
        "tradeoff": raw["tradeoff"].strip(),
        "rationale": rationale,
        "conditions": _string_list(raw.get("conditions"), f"{name}.conditions"),
        "commitment": raw["commitment"],
    }


def _validate_decision_cards(raw: Any) -> dict | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise InvalidVerdict("decision_cards is not an object or null")
    if raw.get("tradeoff_direction") not in rubric.TRADEOFF_DIRECTIONS:
        raise InvalidVerdict(f"decision_cards.tradeoff_direction {raw.get('tradeoff_direction')!r} is invalid")
    if raw.get("rationale_overlap") not in rubric.RATIONALE_OVERLAPS:
        raise InvalidVerdict(f"decision_cards.rationale_overlap {raw.get('rationale_overlap')!r} is invalid")
    return {
        "person_card": _validate_card(raw.get("person_card"), "decision_cards.person_card"),
        "response_card": _validate_card(raw.get("response_card"), "decision_cards.response_card"),
        "tradeoff_direction": raw["tradeoff_direction"],
        "rationale_overlap": raw["rationale_overlap"],
        "mismatches": _string_list(raw.get("mismatches"), "decision_cards.mismatches"),
    }


def _validate_style_flags(raw: Any) -> list[dict]:
    if not isinstance(raw, list):
        raise InvalidVerdict("style_flags is not a list")
    flags = []
    for index, flag in enumerate(raw):
        if not isinstance(flag, dict):
            raise InvalidVerdict(f"style_flags[{index}] is not an object")
        if flag.get("code") not in rubric.STYLE_FLAG_CODES:
            raise InvalidVerdict(f"style_flags[{index}].code {flag.get('code')!r} is invalid")
        if not isinstance(flag.get("quote"), str) or not isinstance(flag.get("note"), str) or not isinstance(flag.get("counted"), bool):
            raise InvalidVerdict(f"style_flags[{index}] is malformed")
        flags.append({"code": flag["code"], "quote": flag["quote"].strip(), "counted": flag["counted"], "note": flag["note"].strip()})
    return flags


def validate_verdict(raw_text: str, question_type: str) -> dict:
    try:
        raw = json.loads(raw_text)
    except (TypeError, json.JSONDecodeError) as error:
        raise InvalidVerdict(f"verdict is not JSON: {error}") from error
    if not isinstance(raw, dict):
        raise InvalidVerdict("verdict is not an object")
    reference_maximum = rubric.SCENARIO_REASON_MAXIMUM if question_type == "scenario" else rubric.SCALE_MAXIMUM
    generic = raw.get("generic_writing")
    if not isinstance(generic, dict) or not isinstance(generic.get("is_generic"), bool) or not isinstance(generic.get("explanation"), str):
        raise InvalidVerdict("generic_writing is malformed")
    for key in ("matches", "mismatches"):
        if not isinstance(raw.get(key), list) or not all(isinstance(v, str) for v in raw[key]):
            raise InvalidVerdict(f"{key} is not a list of strings")
    language_note = raw.get("language_note", "")
    if not isinstance(language_note, str):
        raise InvalidVerdict("language_note is not a string")
    # rubric/2 fields. A verdict that omits them entirely (an older backend or the heuristic fake) is
    # recorded as such and scored without them; a field that is present but malformed fails closed.
    missing = [key for key in V2_FIELDS if key not in raw]
    style_deduction = raw.get("style_deduction")
    if style_deduction is not None:
        if isinstance(style_deduction, bool) or not isinstance(style_deduction, int):
            raise InvalidVerdict("style_deduction is not an integer or null")
        if not 0 <= style_deduction <= rubric.STYLE_DEDUCTION_MAXIMUM:
            raise InvalidVerdict(f"style_deduction {style_deduction} is outside 0-{rubric.STYLE_DEDUCTION_MAXIMUM}")
    return {
        "missing_fields": missing,
        "decision_cards": _validate_decision_cards(raw.get("decision_cards")),
        "style_deduction": style_deduction,
        "style_flags": _validate_style_flags(raw.get("style_flags", [])),
        "fix_hints": _string_list(raw.get("fix_hints", []), "fix_hints"),
        "reference_resemblance": _validate_dimension(raw.get("reference_resemblance"), "reference_resemblance", reference_maximum),
        "profile_consistency": _validate_dimension(raw.get("profile_consistency"), "profile_consistency", rubric.SCALE_MAXIMUM),
        "generic_writing": {"is_generic": generic["is_generic"], "explanation": generic["explanation"].strip()},
        "matches": raw["matches"],
        "mismatches": raw["mismatches"],
        "language_note": language_note.strip(),
    }


def _null_dimension(explanation: str, insufficient: bool = False) -> dict:
    return {"score": None, "insufficient_evidence": insufficient, "explanation": explanation, "evidence_ids": []}


def _empty_v2_fields() -> dict:
    return {"decision_cards": None, "style_flags": [], "rejected_style_flags": [], "fix_hints": [], "fix_hints_withheld": 0}


def _known_evidence_ids(build: Answers, question_id: str) -> set[str]:
    return build.answered_ids() | {question_id}


@dataclass
class _Prepared:
    response: Response
    question: Question | None
    reference: dict | None
    features: dict | None
    corpus: feature_module.PersonCorpus | None = None


def _check_style_echo(echo: list[dict], response_text: str, deterministic: list[dict], person_text: str) -> tuple[list[dict], list[dict]]:
    """Keep echoed flags that quote the response verbatim. A flag the model ADDED (not among the
    deterministic ones) is also rejected when the person's own text uses the quoted phrase."""
    known = {(f["code"], f["quote"]) for f in deterministic}
    lowered_person = person_text.lower()
    kept, rejected = [], []
    for flag in echo:
        if not flag["quote"] or flag["quote"] not in response_text:
            rejected.append({**flag, "rejected_because": "the quote is not an exact span of the response"})
        elif (flag["code"], flag["quote"]) not in known and flag["code"] in ("P1", "P3") and flag["quote"].lower() in lowered_person:
            rejected.append({**flag, "rejected_because": "the person's own text uses this phrase"})
        elif (flag["code"], flag["quote"]) not in known and flag["code"] in feature_module.GATE_CODES:
            rejected.append({**flag, "rejected_because": "gates are deterministic; the model cannot raise one"})
        else:
            kept.append({**flag, "source": "computed" if (flag["code"], flag["quote"]) in known else "judge"})
    return kept, rejected


def _scenario_reference(dimension: dict, verdict: dict, features: dict, has_reference: bool) -> dict:
    reason_basis = "judge"
    model_reason = dimension["score"]
    reason_score = model_reason
    cards = verdict["decision_cards"]
    if not dimension["insufficient_evidence"] and has_reference:
        if cards is not None:
            reason_score = rubric.card_reason_score(cards["tradeoff_direction"], cards["rationale_overlap"])
            reason_basis = "decision_cards"
        elif "decision_cards" not in verdict["missing_fields"]:
            raise InvalidVerdict("decision_cards is null for a scenario with a recorded answer; the reason score has no basis")
    choice_match = features.get("choice_match")
    choice_points = rubric.SCENARIO_CHOICE_POINTS if choice_match else 0
    dimension = dict(dimension)
    dimension["reason_score"] = reason_score
    dimension["reason_basis"] = reason_basis
    dimension["model_reason_score"] = model_reason
    dimension["choice_points"] = choice_points
    dimension["score"] = None if reason_score is None else choice_points + reason_score
    card_text = ""
    if reason_basis == "decision_cards":
        card_text = f"Decision cards: tradeoff {cards['tradeoff_direction']}, rationale overlap {cards['rationale_overlap']} -> {reason_score} of {rubric.SCENARIO_REASON_MAXIMUM}. "
    choice_text = (
        f"Choice {features.get('choice') or 'not detected'} vs recorded {features.get('reference_choice')}: "
        f"{choice_points} of {rubric.SCENARIO_CHOICE_POINTS} points (computed without a model). "
    )
    dimension["explanation"] = choice_text + card_text + "Reason: " + dimension["explanation"]
    return dimension


def _writing_reference(dimension: dict, verdict: dict, style: dict | None, kept_flags: list[dict]) -> dict:
    content = dimension["score"]
    dimension = dict(dimension)
    dimension["content_tone_score"] = content
    if content is None:
        dimension.update({"style_deduction": None, "style_deduction_model": verdict["style_deduction"], "caps_applied": []})
        return dimension
    model_deduction = verdict["style_deduction"]
    if model_deduction is None and "style_deduction" not in verdict["missing_fields"]:
        raise InvalidVerdict("style_deduction is null for a writing answer with a content and tone score")
    counted_categories = sorted({f["code"] for f in kept_flags if f["counted"] and f["code"] in feature_module.STYLE_CODES})
    deduction = min(model_deduction or 0, len(counted_categories), rubric.STYLE_DEDUCTION_MAXIMUM)
    score = max(rubric.SCALE_MINIMUM, content - deduction)
    gates = (style or {}).get("gates", {})
    caps = [name for name in ("memorization", "baseline") if gates.get(name)]
    if caps:
        score = min(score, rubric.GATE_CAP)
    dimension.update(
        {
            "style_deduction": deduction,
            "style_deduction_model": model_deduction,
            "style_categories_counted": counted_categories,
            "caps_applied": caps,
            "score": score,
        }
    )
    parts = [f"Content and tone {content}"]
    if model_deduction is None:
        parts.append("no style deduction in the verdict")
    else:
        parts.append(f"minus style deduction {deduction}" + (f" ({', '.join(counted_categories)})" if counted_categories else ""))
    if caps:
        parts.append(f"capped at {rubric.GATE_CAP} by the {' and '.join(caps)} gate")
    dimension["explanation"] = "; ".join(parts) + f" = {score}. " + dimension["explanation"]
    return dimension


def _screen_fix_hints(hints: list[str], reference_text: str | None) -> tuple[list[str], int]:
    """Withhold a hint that repeats the recorded test answer: test answers must never reach a profile."""
    if not reference_text:
        return hints, 0
    kept = [h for h in hints if not feature_module.memorization_flags(h, {"reference": reference_text}, HINT_LEAK_MINIMUM_WORDS)]
    return kept, len(hints) - len(kept)


def judge_one(
    prepared: _Prepared,
    build: Answers,
    build_evidence: str,
    backend: JudgeBackend,
    system_prompt: str,
    schema: dict,
) -> dict:
    response = prepared.response
    base: dict[str, Any] = {
        "question_id": response.question_id,
        "run_id": response.run_id,
        "declared_scale": rubric.DECLARED_SCALE,
        "judge_model_requested": getattr(backend, "model", "unknown"),
        "judge_model_served": None,
        "features": prepared.features,
    }
    question = prepared.question
    if question is None:
        return {
            **base,
            "status": "judge_error",
            "error": f"question {response.question_id} is not in the question file or the kit",
            "reference_resemblance": _null_dimension("Question text unavailable.", insufficient=True),
            "profile_consistency": _null_dimension("Question text unavailable.", insufficient=True),
            "generic_writing": {"is_generic": None, "explanation": "Not evaluated."},
            "matches": [],
            "mismatches": [],
            "language_note": "",
            **_empty_v2_fields(),
        }

    features = prepared.features or {}
    user_prompt = rubric.build_user_prompt(build_evidence, question, prepared.reference, response.text, features)
    reference_text = None
    if prepared.reference is not None:
        reference_text = prepared.reference.get("explanation") if question.type == "scenario" else prepared.reference.get("text")
    request = JudgeRequest(
        system=system_prompt,
        user=user_prompt,
        schema=schema,
        context={
            "question_id": question.id,
            "question_type": question.type,
            "response_text": response.text,
            "reference_text": reference_text,
            "typicality": features.get("typicality"),
            "style_flags": [dict(f) for f in (features.get("style_fidelity") or {}).get("flags", [])],
            "style_gates": dict((features.get("style_fidelity") or {}).get("gates", {})),
        },
    )
    style = features.get("style_fidelity")
    corpus = prepared.corpus or feature_module.PersonCorpus()
    try:
        result = backend.judge(request)
        verdict = validate_verdict(result.raw_text, question.type)
        kept_flags, rejected_flags = _check_style_echo(
            verdict["style_flags"], response.text, (style or {}).get("flags", []), corpus.all_text(reference_text)
        )
        reference_dimension = verdict["reference_resemblance"]
        decision_cards = verdict["decision_cards"] if question.type == "scenario" else None
        if prepared.reference is None:
            reference_dimension = _null_dimension("No recorded answer from the person for this question.", insufficient=True)
        elif question.type == "scenario":
            reference_dimension = _scenario_reference(reference_dimension, verdict, features, True)
        else:
            reference_dimension = _writing_reference(reference_dimension, verdict, style, kept_flags)
    except Exception as error:  # fail-closed: no verdict means no score
        return {
            **base,
            "status": "judge_error",
            "error": f"{type(error).__name__}: {error}",
            "reference_resemblance": _null_dimension("Judge failed; no score was produced."),
            "profile_consistency": _null_dimension("Judge failed; no score was produced."),
            "generic_writing": {"is_generic": None, "explanation": "Judge failed."},
            "matches": [],
            "mismatches": [],
            "language_note": "",
            **_empty_v2_fields(),
        }

    known = _known_evidence_ids(build, question.id)
    for dimension in (reference_dimension, verdict["profile_consistency"]):
        dimension["unverified_evidence_ids"] = [i for i in dimension.get("evidence_ids", []) if i not in known]
    fix_hints, withheld = _screen_fix_hints(verdict["fix_hints"], reference_text)

    evaluation = {
        **base,
        "judge_model_served": result.served_model,
        "status": "ok",
        "reference_resemblance": reference_dimension,
        "profile_consistency": verdict["profile_consistency"],
        "generic_writing": verdict["generic_writing"],
        "matches": verdict["matches"],
        "mismatches": verdict["mismatches"],
        "language_note": verdict["language_note"],
        "decision_cards": decision_cards,
        "style_flags": kept_flags,
        "rejected_style_flags": rejected_flags,
        "fix_hints": fix_hints,
        "fix_hints_withheld": withheld,
    }
    if verdict["missing_fields"]:
        evaluation["verdict_missing_fields"] = verdict["missing_fields"]
    return evaluation


def judge_responses(
    build: Answers,
    questions: dict[str, Question],
    reference: Answers | None,
    responses: Sequence[Response],
    backend: JudgeBackend,
    generation_models: Iterable[str] = (),
) -> dict:
    """Evaluate every response. Returns {"metadata": {...}, "evaluations": [...]} in input order."""
    system_prompt = rubric.build_system_prompt()
    schema = rubric.output_schema()
    build_evidence = rubric.render_build_evidence(build)
    corpus = feature_module.PersonCorpus.from_answers(build)

    by_question: dict[str, list[Response]] = {}
    for response in responses:
        by_question.setdefault(response.question_id, []).append(response)

    prepared: list[_Prepared] = []
    for response in responses:
        question = resolve_question(response.question_id, questions)
        if question is None:
            prepared.append(_Prepared(response, None, None, None))
            continue
        reference_answer = reference_for(question, reference)
        peers = [other.text for other in by_question[response.question_id] if other is not response]
        reference_text = None
        if reference_answer is not None:
            reference_text = reference_answer.get("explanation") if question.type == "scenario" else reference_answer.get("text")
        features = feature_module.response_features(
            response.text,
            question.type,
            question.word_limit,
            reference_answer.get("choice") if reference_answer and question.type == "scenario" else None,
            peers,
            reference_text=reference_text,
            corpus=corpus,
        )
        prepared.append(_Prepared(response, question, reference_answer, features, corpus))

    evaluations = [judge_one(p, build, build_evidence, backend, system_prompt, schema) for p in prepared]

    requested = getattr(backend, "model", "unknown")
    generation_models = [m for m in generation_models if m]
    warnings = []
    if requested in generation_models:
        warnings.append(
            f"The judge model ({requested}) is also one of the generation models under test; "
            "self-preference bias is possible. Prefer a different judge model."
        )
    errors = sum(1 for e in evaluations if e["status"] != "ok")
    if errors:
        warnings.append(f"{errors} of {len(evaluations)} evaluations failed closed (judge_error, no score).")
    return {
        "metadata": {
            "rubric_version": rubric.RUBRIC_VERSION,
            "declared_scale": rubric.DECLARED_SCALE,
            "judge_model_requested": requested,
            "judge_models_served": sorted({e["judge_model_served"] for e in evaluations if e["judge_model_served"]}),
            "generation_models_under_test": generation_models,
            "person_id": build.person_id,
            "response_count": len(evaluations),
            "anonymized": True,
            "warnings": warnings,
        },
        "evaluations": evaluations,
    }
