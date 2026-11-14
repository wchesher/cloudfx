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
from mefile.judge.features import (
    PersonCorpus,
    assistant_register_flags,
    baseline_gate,
    corporate_flags,
    memorization_flags,
    parse_choice,
    politeness_flags,
    signature_flags,
    structure_flags,
    style_fidelity,
    typicality,
)
from mefile.judge.report import write_reports
from mefile.judge.rubric import CARD_REASON_TABLE, build_system_prompt, output_schema

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
    assert report["total"] == 10
    assert all("name" in p and "passed" in p for p in report["probes"])


def test_selfcheck_reports_failures_when_judge_breaks():
    report = run_judge_selfcheck(FakeJudgeBackend("raise"))
    assert report["passed"] == 0


# ---------------------------------------------------------------------------
# Style fidelity (P1-P4, memorization and baseline gates) and decision cards
# ---------------------------------------------------------------------------

PLAIN_W02 = "Hey, I covered the client report since it hadn't come in. All good, but can you give me a heads-up next time something slips?"


@pytest.fixture
def corpus(build):
    return PersonCorpus.from_answers(build)


def card(choice="B", tradeoff="speed over thread", rationale=("a call is faster",), commitment="firm"):
    return {"choice": choice, "tradeoff": tradeoff, "rationale": list(rationale), "conditions": [], "commitment": commitment}


def v2_verdict(reference_score=3, cards=None, style_deduction=None, style_flags=(), fix_hints=()):
    raw = verdict(reference_score=reference_score)
    raw.update({"decision_cards": cards, "style_deduction": style_deduction, "style_flags": list(style_flags), "fix_hints": list(fix_hints)})
    return raw


def rule_following_backend(content_score=3):
    """A fake that follows rubric/2: confirms every computed style flag and deducts 1 per category, and
    writes decision cards for scenarios. It stands in for a judge model that obeys the rubric."""

    def respond(request):
        context = request.context
        flags = context["style_flags"]
        if context["question_type"] == "scenario":
            cards = {"person_card": card(), "response_card": card(), "tradeoff_direction": "same", "rationale_overlap": "most", "mismatches": []}
            raw = v2_verdict(reference_score=2, cards=cards, style_flags=[{"code": f["code"], "quote": f["quote"], "counted": False, "note": "scenario"} for f in flags])
        else:
            categories = {f["code"] for f in flags if f["code"] in ("P1", "P2", "P3", "P4")}
            raw = v2_verdict(
                reference_score=content_score,
                style_deduction=min(2, len(categories)),
                style_flags=[{"code": f["code"], "quote": f["quote"], "counted": f["code"] in categories, "note": "confirmed"} for f in flags],
                fix_hints=["Add: writes two short sentences with no sign-off (W03)."],
            )
        raw["generic_writing"]["is_generic"] = bool(flags)
        return json.dumps(raw)

    return FakeJudgeBackend(respond)


def assert_quotes_are_spans(flags, text):
    assert flags, "expected at least one flag"
    for flag in flags:
        assert flag["quote"], flag
        assert flag["quote"] in text, flag


def test_assistant_register_is_quoted_and_relative_to_the_person():
    text = PLAIN_W02 + " Happy to help! Let me know if you need anything else."
    flags = assistant_register_flags(text, "Hey, short note.")
    assert_quotes_are_spans(flags, text)
    assert {f["quote"] for f in flags} == {"Happy to help", "Let me know if you need anything else"}
    assert all(f["code"] == "P1" for f in flags)
    # a person who writes "happy to help" themselves is not flagged for it
    assert [f["quote"] for f in assistant_register_flags(text, "Always happy to help.")] == ["Let me know if you need anything else"]
    assert assistant_register_flags(PLAIN_W02, "") == []


def test_politeness_is_flagged_only_as_excess_over_the_persons_own_rate():
    response = "Thanks so much, sorry for the trouble, and thank you again, I appreciate it."
    reserved_person = ["Covered it. Next time tell me early.", "Moved the meeting to Friday."]
    warm_person = ["Thanks so much! Sorry again, I appreciate you.", "Thank you, sorry for the delay, thanks for waiting."]
    flags, info = politeness_flags(response, reserved_person)
    assert_quotes_are_spans(flags, response)
    assert all(f["code"] == "P2" for f in flags)
    assert info["excess_markers"] >= 1
    # the SAME response from a naturally warm person is fidelity, not boilerplate
    warm_flags, warm_info = politeness_flags(response, warm_person)
    assert warm_flags == []
    assert warm_info["person_per_100_words"] > info["person_per_100_words"]
    # no person text means no basis: never flag in absolute terms
    assert politeness_flags(response, [])[0] == []


def test_corporate_lexicon_is_quoted_and_relative():
    text = "Let's circle back and align, then leverage the bandwidth we have."
    flags = corporate_flags(text, "plain words only")
    assert_quotes_are_spans(flags, text)
    assert {f["quote"].lower() for f in flags} == {"circle back", "align", "leverage", "bandwidth"}
    assert {f["quote"] for f in corporate_flags(text, "we should align first")} == {"circle back", "leverage", "bandwidth"}


def test_lost_contractions_quote_the_expanded_form():
    text = "I am covering it, but do not let it slip again."
    flags = signature_flags(text, "writing", ["I'm on it.", "Don't worry, it's fine."])
    assert_quotes_are_spans(flags, text)
    assert {f["quote"] for f in flags} == {"I am", "do not"}
    # a person who never contracts loses nothing
    assert signature_flags(text, "writing", ["I am on it.", "Do not worry."]) == []


def test_structure_flags_bullets_and_length_against_the_persons_range():
    bullets = "Hi,\n- covered the report\n- please flag slips early"
    flags, _ = structure_flags(bullets, "writing", ["Short note.", "Another short note."], ["Short note."], "Covered it.")
    assert_quotes_are_spans([f for f in flags if "bullet" in f["detail"]], bullets)
    long_text = " ".join(["word"] * 40) + " overflow tail here."
    length_flags, info = structure_flags(long_text, "writing", ["ten words " * 5], ["ten words " * 5], "one two three four five six seven eight nine ten")
    length = [f for f in length_flags if "length" in f["detail"]]
    assert_quotes_are_spans(length, long_text)
    assert info["person_range"] == [10, 10]
    # inside the person's own range: no flag
    within, _ = structure_flags("one two three four five six seven eight nine ten eleven", "writing", [], [], "one two three four five six seven eight nine ten")
    assert not [f for f in within if "length" in f["detail"]]


def test_memorization_detects_and_quotes_the_copied_span(corpus):
    text = "Hey, I covered the client report. This is not about the quality of your work, which was excellent, but give me a heads-up."
    flags = memorization_flags(text, corpus.sources())
    assert len(flags) == 1
    assert flags[0]["quote"] == "This is not about the quality of your work, which was excellent"
    assert flags[0]["source_id"] == "W01"
    assert flags[0]["code"] == "MEMORIZATION"
    # seven words is under the threshold
    assert memorization_flags("This is not about the quality of yours.", corpus.sources()) == []
    # scenario explanations are sources too, and curly apostrophes still match
    copied = "Honestly I would rather flag the risk while the plan can still change."
    assert memorization_flags(copied, corpus.sources())[0]["source_id"] == "S01"
    assert memorization_flags("Let\u2019s meet tomorrow at 10 so I can answer questions today", corpus.sources())[0]["source_id"] == "W01"


def test_baseline_gate_flags_a_response_closer_to_the_batch_than_to_the_person():
    reference = "Could we try somewhere else this time? Happy with anything near the office."
    peers = ["Let us consider an alternative venue for our team lunch.", "An alternative venue for the team lunch would be welcome."]
    text = "I suggest an alternative venue for the team lunch."
    flags, info = baseline_gate(text, reference, peers)
    assert_quotes_are_spans(flags, text)
    assert flags[0]["code"] == "BASELINE"
    assert info["centroid_overlap"] > info["reference_overlap"]
    # a response closer to the person is not flagged
    assert baseline_gate("Could we try somewhere else near the office?", reference, peers)[0] == []
    # no peers, or no recorded answer: no basis, no flag
    assert baseline_gate(text, reference, [])[0] == []
    assert baseline_gate(text, None, peers)[0] == []


def test_every_flag_on_the_selfcheck_corpus_quotes_its_response(corpus, reference):
    from mefile.judge.eval_corpus import CORPUS

    for entry in CORPUS:
        kind = "scenario" if entry["question_id"].startswith("S") else "writing"
        reference_text = reference.scenarios.get(entry["question_id"], {}).get("explanation") if kind == "scenario" else reference.writing.get(entry["question_id"])
        peers = [c["text"] for c in CORPUS if c["question_id"] == entry["question_id"] and c is not entry]
        result = style_fidelity(entry["text"], kind, reference_text, corpus, peers)
        for flag in result["flags"]:
            assert flag["quote"] in entry["text"], (entry["run_id"], flag)


def test_schema_is_strict_at_every_level():
    def walk(node, path="$"):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False, path
                assert set(node["required"]) == set(node["properties"]), path
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    schema = output_schema()
    walk(schema)
    for field in ("reference_resemblance", "profile_consistency", "generic_writing", "matches", "mismatches", "language_note",
                  "decision_cards", "style_deduction", "style_flags", "fix_hints"):
        assert field in schema["required"]
    assert {"type": "null"} in schema["properties"]["decision_cards"]["anyOf"]
    assert {"type": "null"} in schema["properties"]["style_deduction"]["anyOf"]
    card_schema = schema["properties"]["decision_cards"]["anyOf"][0]["properties"]["person_card"]
    assert set(card_schema["required"]) == {"choice", "tradeoff", "rationale", "conditions", "commitment"}


def test_rubric_states_the_style_and_card_rules():
    prompt = build_system_prompt()
    assert "at most 2 in total" in prompt or "at most 2" in prompt
    assert "capped at 2" in prompt
    assert "EXCESS relative to this person" in prompt
    assert "Polished English" in prompt and "must NOT raise" in prompt
    assert "decision cards" in prompt
    for (direction, overlap), points in CARD_REASON_TABLE.items():
        assert 0 <= points <= 2


def test_style_flags_reach_the_model_but_run_ids_do_not(build, reference, questions):
    backend = FakeJudgeBackend()
    text = PLAIN_W02 + " Happy to help!"
    judge_responses(build, questions, reference, [Response("SECRET_RUN_9", "W02", text)], backend)
    user = backend.requests[0].user
    assert 'P1 "Happy to help"' in user
    assert "SECRET_RUN_9" not in user + json.dumps(backend.requests[0].context)


def test_scenario_reason_comes_from_decision_cards(build, reference, questions):
    cards = {"person_card": card(), "response_card": card(tradeoff="record over speed"), "tradeoff_direction": "reversed", "rationale_overlap": "some", "mismatches": ["tradeoff reversed"]}
    # the model says 2, but its own card labels say reversed: the score follows the cards
    backend = FakeJudgeBackend("fixed", fixed=v2_verdict(reference_score=2, cards=cards))
    evaluation = judge_responses(build, questions, reference, [Response("R1", "S02", "B. Keeps a record.")], backend)["evaluations"][0]
    dimension = evaluation["reference_resemblance"]
    assert evaluation["status"] == "ok"
    assert dimension["reason_basis"] == "decision_cards"
    assert dimension["model_reason_score"] == 2
    assert dimension["reason_score"] == 0
    assert dimension["score"] == 2  # choice B matches: 2 + 0
    assert evaluation["decision_cards"]["mismatches"] == ["tradeoff reversed"]


def test_decision_cards_fail_closed_when_malformed_or_missing(build, reference, questions):
    too_many = {"person_card": card(rationale=("a", "b", "c", "d")), "response_card": card(), "tradeoff_direction": "same", "rationale_overlap": "most", "mismatches": []}
    bad_enum = {"person_card": card(commitment="maybe"), "response_card": card(), "tradeoff_direction": "same", "rationale_overlap": "most", "mismatches": []}
    for cards in (too_many, bad_enum):
        result = judge_responses(build, questions, reference, [Response("R1", "S02", "B. Call.")], FakeJudgeBackend("fixed", fixed=v2_verdict(reference_score=1, cards=cards)))
        assert result["evaluations"][0]["status"] == "judge_error"
        assert result["evaluations"][0]["reference_resemblance"]["score"] is None
    # explicit null cards for a scenario with a recorded answer: the reason has no basis
    result = judge_responses(build, questions, reference, [Response("R1", "S02", "B. Call.")], FakeJudgeBackend("fixed", fixed=v2_verdict(reference_score=1, cards=None)))
    assert result["evaluations"][0]["status"] == "judge_error"
    # an older verdict shape without the field is scored on the model's reason and recorded as such
    legacy = judge_responses(build, questions, reference, [Response("R1", "S02", "B. Call.")], FakeJudgeBackend("fixed", fixed=verdict(reference_score=1)))["evaluations"][0]
    assert legacy["status"] == "ok"
    assert legacy["reference_resemblance"]["reason_basis"] == "judge"
    assert "decision_cards" in legacy["verdict_missing_fields"]


def test_writing_style_deduction_is_bounded_by_counted_categories(build, reference, questions):
    text = PLAIN_W02 + " Happy to help! Let's circle back."
    echo = [
        {"code": "P1", "quote": "Happy to help", "counted": True, "note": ""},
        {"code": "P3", "quote": "circle back", "counted": True, "note": ""},
        {"code": "P1", "quote": "Glad to assist", "counted": True, "note": "not in the response"},
    ]
    evaluation = judge_responses(build, questions, reference, [Response("R1", "W02", text)], FakeJudgeBackend("fixed", fixed=v2_verdict(reference_score=4, style_deduction=2, style_flags=echo)))["evaluations"][0]
    dimension = evaluation["reference_resemblance"]
    assert dimension["content_tone_score"] == 4
    assert dimension["style_deduction"] == 2
    assert dimension["score"] == 2
    assert [f["quote"] for f in evaluation["rejected_style_flags"]] == ["Glad to assist"]
    # a deduction with no counted, quoted flag behind it is not applied
    unbacked = judge_responses(build, questions, reference, [Response("R1", "W02", PLAIN_W02)], FakeJudgeBackend("fixed", fixed=v2_verdict(reference_score=4, style_deduction=2)))["evaluations"][0]
    assert unbacked["reference_resemblance"]["score"] == 4
    assert unbacked["reference_resemblance"]["style_deduction"] == 0
    # a deduction above 2 is schema-invalid: fail closed
    invalid = judge_responses(build, questions, reference, [Response("R1", "W02", text)], FakeJudgeBackend("fixed", fixed=v2_verdict(reference_score=4, style_deduction=3)))
    assert invalid["evaluations"][0]["status"] == "judge_error"
    # an explicit null deduction on a scored writing answer: fail closed
    null = judge_responses(build, questions, reference, [Response("R1", "W02", text)], FakeJudgeBackend("fixed", fixed=v2_verdict(reference_score=4, style_deduction=None)))
    assert null["evaluations"][0]["status"] == "judge_error"


def test_memorization_gate_caps_writing_at_two(build, reference, questions):
    text = "Hey, I covered the client report. This is not about the quality of your work, which was excellent, but give me a heads-up next time."
    evaluation = judge_responses(build, questions, reference, [Response("R1", "W02", text)], FakeJudgeBackend("fixed", fixed=v2_verdict(reference_score=4, style_deduction=0)))["evaluations"][0]
    assert evaluation["features"]["style_fidelity"]["gates"]["memorization"] is True
    assert evaluation["reference_resemblance"]["caps_applied"] == ["memorization"]
    assert evaluation["reference_resemblance"]["score"] == 2


def test_baseline_gate_caps_writing_at_two(build, reference, questions):
    responses = [
        Response("R1", "W04", "I suggest an alternative venue for the team lunch."),
        Response("R2", "W04", "Let us consider an alternative venue for our team lunch."),
        Response("R3", "W04", "An alternative venue for the team lunch would be welcome."),
    ]
    result = judge_responses(build, questions, reference, responses, FakeJudgeBackend("fixed", fixed=v2_verdict(reference_score=4, style_deduction=0)))
    first = result["evaluations"][0]
    assert first["features"]["style_fidelity"]["gates"]["baseline"] is True
    assert "baseline" in first["reference_resemblance"]["caps_applied"]
    assert first["reference_resemblance"]["score"] <= 2


def test_fix_hints_that_repeat_the_test_answer_are_withheld(build, reference, questions):
    hints = ["Add: says 'can you give me a heads-up next time' to colleagues.", "Add: keeps messages to two sentences (W03)."]
    evaluation = judge_responses(build, questions, reference, [Response("R1", "W02", PLAIN_W02)], FakeJudgeBackend("fixed", fixed=v2_verdict(reference_score=4, style_deduction=0, fix_hints=hints)))["evaluations"][0]
    assert evaluation["fix_hints"] == ["Add: keeps messages to two sentences (W03)."]
    assert evaluation["fix_hints_withheld"] == 1


def test_error_paths_carry_the_new_fields(build, reference, questions):
    evaluation = judge_responses(build, questions, reference, [Response("R1", "W02", "Hi.")], FakeJudgeBackend("raise"))["evaluations"][0]
    assert evaluation["decision_cards"] is None
    assert evaluation["style_flags"] == [] and evaluation["fix_hints"] == []


def test_report_renders_style_flags_and_card_mismatches(tmp_path, build, reference, questions):
    cards = {"person_card": card(tradeoff="speed over record"), "response_card": card(tradeoff="record over speed"), "tradeoff_direction": "reversed", "rationale_overlap": "none", "mismatches": ["prioritises the written record"]}

    def respond(request):
        if request.context["question_type"] == "scenario":
            return json.dumps(v2_verdict(reference_score=0, cards=cards))
        return json.dumps(v2_verdict(reference_score=4, style_deduction=1, style_flags=[{"code": "P1", "quote": "Happy to help", "counted": True, "note": ""}], fix_hints=["Add: no closing offers (W01, W03)."]))

    responses = [Response("RS", "S02", "A. Replying point by point keeps a clear record."), Response("RW", "W02", PLAIN_W02 + " Happy to help!")]
    result = judge_responses(build, questions, reference, responses, FakeJudgeBackend(respond))
    _, md_path = write_reports(result, tmp_path)
    markdown = md_path.read_text()
    assert "| Style flags |" in markdown
    assert "## Style flags and decision cards" in markdown
    assert 'P1 "Happy to help" (counted)' in markdown
    assert "Decision cards: tradeoff reversed" in markdown
    assert "prioritises the written record" in markdown
    assert "Fix hint: Add: no closing offers (W01, W03)." in markdown
    data = json.loads((tmp_path / "evaluations.json").read_text())
    assert data["evaluations"][1]["reference_resemblance"]["score"] == 3


def test_selfcheck_style_probes_pass_with_a_rule_following_judge():
    report = run_judge_selfcheck(rule_following_backend())
    outcomes = {p["name"]: p for p in report["probes"]}
    assert outcomes["assistant-register leakage scores lower than the plain reply (W02)"]["passed"], outcomes
    assert outcomes["memorization: 8+ words copied from W01 are flagged and capped (W02)"]["passed"]
    assert outcomes["corporate lexicon is flagged with quotes (W04)"]["passed"]
    assert "This is not about the quality of your work" in outcomes["memorization: 8+ words copied from W01 are flagged and capped (W02)"]["detail"]
