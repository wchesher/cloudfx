# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_judge - judge orchestration with the fake backend: anonymity, fail-closed, scoring, unseen IDs, reports

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mefile.answers import Question, Response, load_answers, load_questions, load_responses
from mefile.judge import FakeJudgeBackend, judge_responses
from mefile.judge.__main__ import main as judge_main
from mefile.judge.eval_corpus import run_judge_selfcheck
from mefile.judge.features import parse_choice, typicality
from mefile.judge.report import write_reports
from mefile.judge.rubric import output_schema

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def build():
    return load_answers(EXAMPLES / "example_build_answers.json")


@pytest.fixture
def reference():
    return load_answers(EXAMPLES / "example_test_answers.json")


@pytest.fixture
def questions():
    return load_questions(EXAMPLES / "example_questions.json")


def verdict(reference_score=2, profile_score=3, insufficient=False, generic=False):
    return {
        "reference_resemblance": {"score": None if insufficient else reference_score, "insufficient_evidence": insufficient, "explanation": "ref", "evidence_ids": ["S02"]},
        "profile_consistency": {"score": profile_score, "insufficient_evidence": False, "explanation": "prof", "evidence_ids": ["S01", "B99"]},
        "generic_writing": {"is_generic": generic, "explanation": "gen"},
        "matches": ["m"],
        "mismatches": [],
        "language_note": "none",
    }


def test_run_id_and_source_never_reach_the_model(build, reference, questions):
    backend = FakeJudgeBackend()
    responses = [Response("SECRET_RUN_7", "S02", "B. A call is faster."), Response("WETHOS_TWIN_X", "W02", "Hey, next time warn me.")]
    judge_responses(build, questions, reference, responses, backend)
    assert len(backend.requests) == 2
    for request in backend.requests:
        blob = request.system + request.user + json.dumps(request.context)
        assert "SECRET_RUN_7" not in blob
        assert "WETHOS_TWIN_X" not in blob


def test_backend_exception_fails_closed(build, reference, questions):
    result = judge_responses(build, questions, reference, [Response("R1", "S02", "B. Call.")], FakeJudgeBackend("raise"))
    evaluation = result["evaluations"][0]
    assert evaluation["status"] == "judge_error"
    assert evaluation["reference_resemblance"]["score"] is None
    assert evaluation["profile_consistency"]["score"] is None
    assert "outage" in evaluation["error"]
    assert any("failed closed" in w for w in result["metadata"]["warnings"])


def test_invalid_json_fails_closed(build, reference, questions):
    result = judge_responses(build, questions, reference, [Response("R1", "W02", "Hi.")], FakeJudgeBackend("invalid"))
    evaluation = result["evaluations"][0]
    assert evaluation["status"] == "judge_error"
    assert evaluation["reference_resemblance"]["score"] is None


def test_out_of_range_score_fails_closed(build, reference, questions):
    # a scenario reason score above 2 is schema-invalid for scenarios
    backend = FakeJudgeBackend("fixed", fixed=verdict(reference_score=4))
    result = judge_responses(build, questions, reference, [Response("R1", "S02", "B. Call.")], backend)
    assert result["evaluations"][0]["status"] == "judge_error"


def test_missing_score_without_insufficient_flag_fails_closed(build, reference, questions):
    bad = verdict()
    bad["profile_consistency"]["score"] = None
    result = judge_responses(build, questions, reference, [Response("R1", "W02", "Hi.")], FakeJudgeBackend("fixed", fixed=bad))
    assert result["evaluations"][0]["status"] == "judge_error"


def test_scenario_score_is_choice_points_plus_reason(build, reference, questions):
    backend = FakeJudgeBackend("fixed", fixed=verdict(reference_score=1))
    responses = [Response("same", "S02", "B. A short call settles it."), Response("different", "S02", "A. Point by point.")]
    result = judge_responses(build, questions, reference, responses, backend)
    same, different = result["evaluations"]
    assert same["features"]["choice_match"] is True
    assert same["reference_resemblance"]["choice_points"] == 2
    assert same["reference_resemblance"]["score"] == 3
    assert different["features"]["choice_match"] is False
    assert different["reference_resemblance"]["score"] == 1


def test_writing_score_passes_through(build, reference, questions):
    result = judge_responses(build, questions, reference, [Response("R1", "W02", "Hey.")], FakeJudgeBackend("fixed", fixed=verdict(reference_score=4)))
    assert result["evaluations"][0]["reference_resemblance"]["score"] == 4


def test_unverified_evidence_ids_are_flagged(build, reference, questions):
    result = judge_responses(build, questions, reference, [Response("R1", "W02", "Hey.")], FakeJudgeBackend("fixed", fixed=verdict()))
    profile = result["evaluations"][0]["profile_consistency"]
    assert profile["unverified_evidence_ids"] == ["B99"]


def test_unseen_question_id_uses_question_file(build, reference):
    questions = {
        "S99": Question("S99", "scenario", "A brand new private scenario.", {"A": "x", "B": "y", "C": "z", "D": "w"}, 60, "prompt"),
    }
    backend = FakeJudgeBackend()
    result = judge_responses(build, questions, reference, [Response("R1", "S99", "B. Because.")], backend)
    evaluation = result["evaluations"][0]
    assert evaluation["status"] == "ok"
    assert "A brand new private scenario." in backend.requests[0].user
    # no recorded answer for S99 in the reference file
    assert evaluation["reference_resemblance"]["insufficient_evidence"] is True
    assert evaluation["reference_resemblance"]["score"] is None


def test_question_absent_everywhere_is_an_error_not_a_score(build, reference):
    result = judge_responses(build, {}, reference, [Response("R1", "Q42", "text")], FakeJudgeBackend())
    evaluation = result["evaluations"][0]
    assert evaluation["status"] == "judge_error"
    assert evaluation["reference_resemblance"]["score"] is None


def test_missing_reference_file_marks_insufficient(build, questions):
    backend = FakeJudgeBackend("fixed", fixed=verdict(reference_score=4))
    result = judge_responses(build, questions, None, [Response("R1", "W02", "Hey.")], backend)
    reference_dimension = result["evaluations"][0]["reference_resemblance"]
    assert reference_dimension["insufficient_evidence"] is True
    assert reference_dimension["score"] is None
    assert "No recorded answer" in backend.requests[0].user


def test_self_preference_warning(build, reference, questions):
    backend = FakeJudgeBackend(model="claude-opus-5-5")
    result = judge_responses(build, questions, reference, [Response("R1", "W02", "Hey.")], backend, ["claude-opus-5-5", "gpt-sol-6.1"])
    assert any("self-preference" in w for w in result["metadata"]["warnings"])


def test_parse_choice_variants():
    assert parse_choice("B. A call lets you understand") == "B"
    assert parse_choice("(C) do it together") == "C"
    assert parse_choice("Option D, with a clause") == "D"
    assert parse_choice("**A** - reply in the doc") == "A"
    assert parse_choice("I would message them directly") is None
    assert parse_choice("Choose A or B depending") is None
    assert parse_choice("A short call is better, so B.") is None or parse_choice("A short call is better, so B.") == "B"
    assert parse_choice("A short call settles it") is None
    assert parse_choice("B because it is faster") == "B"


def test_typicality_is_none_without_peers():
    assert typicality("anything", []) is None
    assert typicality("call them directly", ["call them directly"]) == 1.0


def test_schema_is_strict():
    schema = output_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])


def test_reports_written(tmp_path, build, reference, questions):
    responses = load_responses(EXAMPLES / "example_comparison_responses.json")
    result = judge_responses(build, questions, reference, responses, FakeJudgeBackend())
    json_path, md_path = write_reports(result, tmp_path)
    data = json.loads(json_path.read_text())
    assert [e["run_id"] for e in data["evaluations"]] == ["R01", "R02", "R03"]
    for evaluation in data["evaluations"]:
        assert evaluation["declared_scale"]
        assert evaluation["question_id"]
    markdown = md_path.read_text()
    assert "| R01 | S02 |" in markdown
    assert "Scale." in markdown


def test_cli_end_to_end(tmp_path, capsys):
    code = judge_main([
        "--build", str(EXAMPLES / "example_build_answers.json"),
        "--questions", str(EXAMPLES / "example_questions.json"),
        "--reference", str(EXAMPLES / "example_test_answers.json"),
        "--responses", str(EXAMPLES / "example_comparison_responses.json"),
        "--out", str(tmp_path), "--fake",
    ])
    assert code == 0
    assert (tmp_path / "evaluations.json").exists()
    assert "3/3 evaluated" in capsys.readouterr().out


def test_selfcheck_runs_with_fake_backend():
    report = run_judge_selfcheck(FakeJudgeBackend())
    assert report["total"] == 7
    assert all("name" in p and "passed" in p for p in report["probes"])


def test_selfcheck_reports_failures_when_judge_breaks():
    report = run_judge_selfcheck(FakeJudgeBackend("raise"))
    assert report["passed"] == 0
