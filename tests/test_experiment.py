# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_experiment - the experiment harness runs end to end with fake backends and never leaks held-out answers

import json
import shutil
from pathlib import Path

from mefile.answers import load_questions
from mefile.experiment import fake_answerer, run_experiment
from mefile.judge.backend import FakeJudgeBackend

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _person(tmp_path: Path) -> Path:
    person = tmp_path / "people" / "DEMO01"
    person.mkdir(parents=True)
    shutil.copy(EXAMPLES / "example_build_answers.json", person / "build.json")
    shutil.copy(EXAMPLES / "example_test_answers.json", person / "test.json")
    return tmp_path / "people"


def test_runs_end_to_end_and_scores_choices(tmp_path):
    seen_profiles = []

    def answerer(profile, question):
        seen_profiles.append(profile or "")
        return fake_answerer(profile, question)

    result = run_experiment(_person(tmp_path), load_questions(EXAMPLES / "example_questions.json"),
                            ["evidence_first", "short"], tmp_path / "out", answerer, FakeJudgeBackend())
    summary = {(s["model"], s["condition"]): s for s in result["summary"]}
    # the fake picks A without a profile and B with one; DEMO01's held-out choices are B, D, C
    assert summary[("A", "none")]["choice_correct"] == 0
    assert summary[("A", "evidence_first")]["choice_correct"] == 1
    assert summary[("A", "evidence_first")]["lift_over_no_profile"] > 0
    assert (tmp_path / "out" / "results.md").exists()
    assert (tmp_path / "out" / "DEMO01" / "llm_b_template.json").exists()
    held_out = json.loads((EXAMPLES / "example_test_answers.json").read_text())
    for scenario in held_out["scenarios"]:
        assert all(scenario["explanation"] not in p for p in seen_profiles)
    for message in held_out["writing"]:
        assert all(message["text"] not in p for p in seen_profiles)


def test_reads_pasted_llm_b_responses(tmp_path):
    people = _person(tmp_path)
    (people / "DEMO01" / "llm_b.json").write_text(json.dumps({"responses": [
        {"run_id": "DEMO01-B-none-S04", "question_id": "S04", "text": "D. Walk-away clause limits the risk."}]}))
    result = run_experiment(people, load_questions(EXAMPLES / "example_questions.json"), ["evidence_first"],
                            tmp_path / "out", None)
    rows = [r for r in result["rows"] if r["model"] == "B"]
    assert rows and rows[0]["choice_match"] is True


def test_manual_mode_pastes_model_a_from_text_file(tmp_path):
    people = _person(tmp_path)
    questions = load_questions(EXAMPLES / "example_questions.json")
    first = run_experiment(people, questions, ["evidence_first"], tmp_path / "out", None)
    assert first["rows"] == []
    out = tmp_path / "out" / "DEMO01"
    assert (out / "PASTE_SHEET_LLM_A.md").exists() and (out / "llm_a_answers_template.txt").exists()
    (people / "DEMO01" / "llm_a.txt").write_text(
        "=== DEMO01-A-none-S02\nA. A point-by-point reply keeps a record.\n\n"
        "=== DEMO01-A-evidence_first-S02\nB. A short call settles it faster.\nSecond line kept.\n"
        "=== DEMO01-A-evidence_first-S04\n\n")
    second = run_experiment(people, questions, ["evidence_first"], tmp_path / "out", None)
    rows = {r["run_id"]: r for r in second["rows"]}
    assert set(rows) == {"DEMO01-A-none-S02", "DEMO01-A-evidence_first-S02"}
    assert rows["DEMO01-A-evidence_first-S02"]["choice_match"] is True
    assert rows["DEMO01-A-evidence_first-S02"]["text"].endswith("Second line kept.")
    assert rows["DEMO01-A-none-S02"]["choice_match"] is False
