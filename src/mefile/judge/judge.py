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
     the reason (model); writing = 0-4 (model).
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
    return {
        "reference_resemblance": _validate_dimension(raw.get("reference_resemblance"), "reference_resemblance", reference_maximum),
        "profile_consistency": _validate_dimension(raw.get("profile_consistency"), "profile_consistency", rubric.SCALE_MAXIMUM),
        "generic_writing": {"is_generic": generic["is_generic"], "explanation": generic["explanation"].strip()},
        "matches": raw["matches"],
        "mismatches": raw["mismatches"],
        "language_note": language_note.strip(),
    }


def _null_dimension(explanation: str, insufficient: bool = False) -> dict:
    return {"score": None, "insufficient_evidence": insufficient, "explanation": explanation, "evidence_ids": []}


def _known_evidence_ids(build: Answers, question_id: str) -> set[str]:
    return build.answered_ids() | {question_id}


@dataclass
class _Prepared:
    response: Response
    question: Question | None
    reference: dict | None
    features: dict | None


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
        },
    )
    try:
        result = backend.judge(request)
        verdict = validate_verdict(result.raw_text, question.type)
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
        }

    reference_dimension = verdict["reference_resemblance"]
    if prepared.reference is None:
        reference_dimension = _null_dimension("No recorded answer from the person for this question.", insufficient=True)
    elif question.type == "scenario":
        reason_score = reference_dimension["score"]
        choice_match = features.get("choice_match")
        choice_points = rubric.SCENARIO_CHOICE_POINTS if choice_match else 0
        reference_dimension = dict(reference_dimension)
        reference_dimension["reason_score"] = reason_score
        reference_dimension["choice_points"] = choice_points
        reference_dimension["score"] = None if reason_score is None else choice_points + reason_score
        choice_text = (
            f"Choice {features.get('choice') or 'not detected'} vs recorded {features.get('reference_choice')}: "
            f"{choice_points} of {rubric.SCENARIO_CHOICE_POINTS} points (computed without a model). "
        )
        reference_dimension["explanation"] = choice_text + "Reason: " + reference_dimension["explanation"]

    known = _known_evidence_ids(build, question.id)
    for dimension in (reference_dimension, verdict["profile_consistency"]):
        dimension["unverified_evidence_ids"] = [i for i in dimension.get("evidence_ids", []) if i not in known]

    return {
        **base,
        "judge_model_served": result.served_model,
        "status": "ok",
        "reference_resemblance": reference_dimension,
        "profile_consistency": verdict["profile_consistency"],
        "generic_writing": verdict["generic_writing"],
        "matches": verdict["matches"],
        "mismatches": verdict["mismatches"],
        "language_note": verdict["language_note"],
    }


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
        features = feature_module.response_features(
            response.text,
            question.type,
            question.word_limit,
            reference_answer.get("choice") if reference_answer and question.type == "scenario" else None,
            peers,
        )
        prepared.append(_Prepared(response, question, reference_answer, features))

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
