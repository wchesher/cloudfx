# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_intake_comparison - the Section 11 arm: kit only vs kit plus interview, the leakage guard, unchanged kit-only output

import json
import shutil
from pathlib import Path

import pytest

from mefile import cli
from mefile.answers import load_questions
from mefile.experiment import TranscriptLeakage, fake_answerer, run_experiment
from mefile.judge.backend import FakeJudgeBackend

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
QUESTIONS = EXAMPLES / "example_questions.json"

# Fictional interview for the fictional DEMO01. Nothing here comes from DEMO01's held-out test answers.
TRANSCRIPT = {
    "person_id": "DEMO01", "conversation_id": "conv_fictional_01", "duration_seconds": 612, "source": "elevenlabs",
    "interviewer_turns": [
        {"index": 0, "text": "Tell me about a time you disagreed with a teammate or manager about how to do something. What did you do?"},
        {"index": 2, "text": "Tell me about something you tried that did not work. What did you do next?"},
    ],
    "employee_turns": [
        {"index": 1, "seconds": 30.0, "text": "My lead wanted to ship on Friday. I asked for one more day of testing and showed the bug list."},
        {"index": 3, "seconds": 75.0, "text": "A new filing system confused everyone, so I rolled it back and wrote a one-page guide first."},
    ],
}


def _people(tmp_path: Path, kit_minutes: float | None = None, transcript: dict | None = None) -> Path:
    person = tmp_path / "people" / "DEMO01"
    person.mkdir(parents=True)
    build = json.loads((EXAMPLES / "example_build_answers.json").read_text())
    if kit_minutes is not None:
        build["kit_minutes"] = kit_minutes
    (person / "build.json").write_text(json.dumps(build))
    shutil.copy(EXAMPLES / "example_test_answers.json", person / "test.json")
    if transcript is not None:
        (person / "voice_transcript.json").write_text(json.dumps(transcript))
    return tmp_path / "people"


def _run(people: Path, out: Path, answerer=fake_answerer, judge=None, **keywords):
    return run_experiment(people, load_questions(QUESTIONS), ["evidence_first", "short"], out, answerer, judge, **keywords)


def test_interview_arm_appears_only_with_a_transcript(tmp_path):
    plain = _run(_people(tmp_path / "a"), tmp_path / "a" / "out")
    assert not any(r["condition"].endswith("_plus_interview") for r in plain["rows"])
    assert "comparison" not in plain
    assert not (tmp_path / "a" / "out" / "comparison.json").exists()
    assert not (tmp_path / "a" / "out" / "DEMO01" / "leakage_guard.json").exists()

    seen = []

    def answerer(profile, question):
        seen.append(profile or "")
        return fake_answerer(profile, question)

    result = _run(_people(tmp_path / "b", kit_minutes=24.5, transcript=TRANSCRIPT), tmp_path / "b" / "out", answerer,
                  FakeJudgeBackend())
    conditions = {r["condition"] for r in result["rows"] if r["model"] == "A"}
    assert conditions == {"none", "evidence_first", "evidence_first_plus_interview", "short", "short_plus_interview"}
    # the interview arm's profile cites the transcript; the kit-only one does not
    out = tmp_path / "b" / "out" / "DEMO01"
    assert "V01" in (out / "me.evidence_first_plus_interview.md").read_text()
    assert "V01" not in (out / "me.evidence_first.md").read_text()
    assert any("V01" in p for p in seen)
    held_out = json.loads((EXAMPLES / "example_test_answers.json").read_text())
    for scenario in held_out["scenarios"]:
        assert all(scenario["explanation"] not in p for p in seen)

    person = result["comparison"]["people"][0]
    assert person["leakage_guard"]["passed"] is True
    assert person["effort"]["kit_minutes"] == 24.5
    assert person["effort"]["interview_minutes"] == 10.2
    assert "elevenlabs" in person["effort"]["interview_minutes_source"]
    arms = {(a["model"], a["variant"], a["arm"]): a for a in person["arms"]}
    kit_arm, interview_arm = arms[("A", "evidence_first", "kit_only")], arms[("A", "evidence_first", "kit_plus_interview")]
    assert kit_arm["choice_scored"] == interview_arm["choice_scored"] == 3
    assert interview_arm["me_md_words"] > kit_arm["me_md_words"]
    assert kit_arm["intake_minutes"] == 24.5 and interview_arm["intake_minutes"] == 34.7
    assert interview_arm["difference_vs_kit_only"] == 0
    assert interview_arm["judged"] > 0
    # model B arms are listed even before anything is pasted for B
    assert arms[("B", "short", "kit_plus_interview")]["responses"] == 0
    assert (tmp_path / "b" / "out" / "comparison.json").exists()
    markdown = (tmp_path / "b" / "out" / "comparison.md").read_text()
    assert "| A | evidence_first | kit_plus_interview | 1/3 |" in markdown and "Leakage guard: passed" in markdown
    assert "Alternative intake" in (tmp_path / "b" / "out" / "results.md").read_text()
    # paste sheets cover the new arm, and a pasted answer for it is scored
    assert "DEMO01-B-short_plus_interview-S04" in (out / "PASTE_SHEET_LLM_B.md").read_text()


def test_pasted_answers_for_the_interview_arm_are_scored(tmp_path):
    people = _people(tmp_path, transcript=TRANSCRIPT)
    (people / "DEMO01" / "llm_b.txt").write_text("=== DEMO01-B-evidence_first_plus_interview-S04\nD. Walk away early if it fails.\n")
    result = _run(people, tmp_path / "out", answerer=None)
    arms = {(a["model"], a["variant"], a["arm"]): a for a in result["comparison"]["people"][0]["arms"]}
    assert arms[("B", "evidence_first", "kit_plus_interview")]["choice_correct"] == 1
    assert result["comparison"]["people"][0]["effort"]["kit_minutes"] is None
    assert result["comparison"]["people"][0]["effort"]["kit_minutes_source"] == "not recorded"


def test_kit_only_output_unchanged_without_a_transcript(tmp_path, monkeypatch):
    questions = load_questions(QUESTIONS)
    baseline = run_experiment(_people(tmp_path / "a"), questions, ["evidence_first"], tmp_path / "a" / "out", fake_answerer)
    assert set(baseline) == {"summary", "rows"}
    saved = json.loads((tmp_path / "a" / "out" / "results.json").read_text())
    assert set(saved) == {"summary", "rows"}
    assert sorted(p.name for p in (tmp_path / "a" / "out").iterdir()) == ["DEMO01", "results.json", "results.md"]
    # an empty transcript (no employee answers) builds no arm and leaves the rows as they were
    again = run_experiment(_people(tmp_path / "b", transcript={"person_id": "DEMO01", "employee_turns": []}), questions,
                           ["evidence_first"], tmp_path / "b" / "out", fake_answerer)
    assert again["rows"] == baseline["rows"] and again["summary"] == baseline["summary"]
    assert again["comparison"]["people"][0]["arm_built"] is False


@pytest.mark.parametrize("leak", [
    "I think this is like S02 in the kit.",
    "Honestly a short call usually settles a disagreement faster than anything else.",  # 8 words of S02's explanation
    "I wrote: can you give me a heads-up next time if something slips?",  # W02
])
def test_leakage_guard_refuses_the_run(tmp_path, leak):
    transcript = json.loads(json.dumps(TRANSCRIPT))
    transcript["employee_turns"][1]["text"] = leak
    with pytest.raises(TranscriptLeakage) as refused:
        _run(_people(tmp_path, transcript=transcript), tmp_path / "out")
    guard = json.loads((tmp_path / "out" / "DEMO01" / "leakage_guard.json").read_text())
    assert guard["passed"] is False and refused.value.guard == guard
    assert all(hit["turn"] == "employee turn V02" for hit in guard["test_ids_found"] + guard["quotes_found"])
    assert leak not in json.dumps(guard)  # the report names where, never the matched words
    assert not (tmp_path / "out" / "results.json").exists()


def test_leakage_guard_checks_interviewer_turns_and_allows_seven_words(tmp_path):
    transcript = json.loads(json.dumps(TRANSCRIPT))
    transcript["interviewer_turns"][1]["text"] = "Now tell me how you answered w04."
    with pytest.raises(TranscriptLeakage):
        _run(_people(tmp_path / "a", transcript=transcript), tmp_path / "a" / "out")
    transcript = json.loads(json.dumps(TRANSCRIPT))
    transcript["employee_turns"][1]["text"] = "A short call usually settles a disagreement, I find."  # 7 words shared
    result = _run(_people(tmp_path / "b", transcript=transcript), tmp_path / "b" / "out")
    assert result["comparison"]["people"][0]["leakage_guard"]["passed"] is True


def test_transcript_for_another_person_is_refused(tmp_path):
    with pytest.raises(RuntimeError, match="names person DEMO99"):
        _run(_people(tmp_path, transcript={**TRANSCRIPT, "person_id": "DEMO99"}), tmp_path / "out")


def test_cli_experiment_dry_run_with_voice_flag_and_guard(tmp_path, capsys):
    people = _people(tmp_path, kit_minutes=20)
    transcript = tmp_path / "t.json"
    transcript.write_text(json.dumps(TRANSCRIPT))
    status = cli.main(["experiment", "--people", str(people), "--questions", str(QUESTIONS), "--variants", "evidence_first",
                       "--out", str(tmp_path / "out"), "--dry-run", "--judge", "--voice", str(transcript)])
    printed = capsys.readouterr().out
    assert status == 0 and "leakage guard passed" in printed and "kit_plus_interview" in printed
    assert (tmp_path / "out" / "comparison.md").exists()
    transcript.write_text(json.dumps({**TRANSCRIPT, "employee_turns": [{"index": 1, "text": "Same as my S04 answer."}]}))
    status = cli.main(["experiment", "--people", str(people), "--questions", str(QUESTIONS), "--variants", "evidence_first",
                       "--out", str(tmp_path / "out2"), "--dry-run", "--voice", str(transcript)])
    assert status == 2 and "leakage guard: REFUSED" in capsys.readouterr().out
