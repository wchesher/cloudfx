# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# experiment - the human-context-lift experiment: people x me.md variants x models x {profile, no profile}

"""
The experiment (docs/strategy.md, move 1 and 2)
===============================================

For every consenting teammate in ``private/people/<PERSON>/`` (``build.json`` and ``test.json`` in the
organizer format), and for every me.md variant:

  - LLM A answers the held-out questions WITH the profile and WITHOUT it, through the official
    two-turn loading protocol (``runner.ask``);
  - or, in manual mode (no API key), LLM A is pasted by hand exactly like LLM B;
  - pasted responses are read from ``llm_a.txt`` / ``llm_b.txt`` (a ``=== RUN_ID`` line, then the
    answer) or the JSON comparison format; a paste sheet, the packets and empty templates are written;
  - scenario choices are scored against the person's held-out answers WITHOUT any model (exact
    letter match), and, when a judge backend is given, every response is also judged.

Held-out answers never reach a generating model: the profile is built from ``build.json`` only
(the claims gate refuses a build file that contains a test ID), and the answerer receives only the
profile and the question prompt. ``test.json`` is read solely by the scorer.

Output: ``results.json`` (every response with its scores) and ``results.md`` (the table for the
slides: accuracy and resemblance per model and condition, and the lift over no profile).

Alternative intake arm (Common Kit Section 11)
----------------------------------------------

When a person folder also holds ``voice_transcript.json`` (a reviewed behavioral interview, taken by
voice, recorded in person or typed; see ``intake.py``), every variant gets a second arm,
``kit_plus_interview``: the same build answers plus the transcript's cited V evidence, under the
condition ``<variant>_plus_interview``. Both arms answer the same held-out questions on the same models.
Before any profile is built, a leakage guard refuses the run if the transcript names a held-out test ID
or quotes 8 or more consecutive words from any held-out test answer (the compared answers stay out of
the alternative intake). The guard result is written to ``<PERSON>/leakage_guard.json``. The arm
comparison (accuracy, judge scores, me.md words, kit and interview minutes) goes to ``comparison.json``,
``comparison.md`` and a section of ``results.md``. With no transcript nothing of this runs, and the
output is exactly what it was before the arm existed.
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path
from typing import Any, Callable

from . import kit
from .answers import Answers, Question, Response, load_answers
from .converter import VARIANTS, convert
from .judge.features import parse_choice, word_count

Answerer = Callable[[str | None, Question], str]

TRANSCRIPT_FILE = "voice_transcript.json"
KIT_ONLY = "kit_only"
KIT_PLUS_INTERVIEW = "kit_plus_interview"
INTERVIEW_SUFFIX = "_plus_interview"  # condition name of the interview arm: <variant>_plus_interview
QUOTE_WORDS = 8  # this many consecutive words shared with a held-out test answer counts as leakage

_TEST_ID = re.compile(r"\b(" + "|".join(sorted(kit.DEVELOPMENT_TEST_IDS)) + r")\b", re.IGNORECASE)


class TranscriptLeakage(RuntimeError):
    """The alternative-intake transcript carries held-out test material; the experiment refuses to run."""

    def __init__(self, message: str, guard: dict):
        super().__init__(message)
        self.guard = guard


def _guard_words(text: str) -> list[str]:
    text = text.replace("\u2019", "'").replace("\u2018", "'").lower()
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)*", text)


def _runs(words: list[str], size: int) -> set[tuple[str, ...]]:
    return {tuple(words[i:i + size]) for i in range(len(words) - size + 1)}


def leakage_check(transcript: dict[str, Any], test: Answers) -> dict:
    """Does the transcript carry held-out test material? Checks every turn, the employee's and the interviewer's.

    Trips on a held-out test ID (S02, S04, S06, W02, W04, any case) or on QUOTE_WORDS+ consecutive words shared with a
    held-out answer (scenario explanations and writing messages in test.json). The result names where the match is and
    which test answer it matches, never the matched words, so the report does not spread the test answers.
    """
    turns: list[tuple[str, str]] = []
    for position, turn in enumerate(transcript.get("employee_turns") or []):
        turns.append((f"employee turn V{position + 1:02d}", str((turn or {}).get("text") or "")))
    for position, turn in enumerate(transcript.get("interviewer_turns") or []):
        index = (turn or {}).get("index")
        turns.append((f"interviewer turn {index if isinstance(index, int) else position}", str((turn or {}).get("text") or "")))
    answers = {sid: record.get("explanation", "") for sid, record in test.scenarios.items()}
    answers.update(test.writing)
    answer_runs = {test_id: _runs(_guard_words(text), QUOTE_WORDS) for test_id, text in sorted(answers.items())}

    test_ids, quotes = [], []
    for where, text in turns:
        for found in sorted({m.upper() for m in _TEST_ID.findall(text)}):
            test_ids.append({"turn": where, "test_id": found})
        runs = _runs(_guard_words(text), QUOTE_WORDS)
        for test_id, held_out in answer_runs.items():
            shared = len(runs & held_out)
            if shared:
                quotes.append({"turn": where, "test_answer": test_id, f"shared_{QUOTE_WORDS}_word_runs": shared})
    return {
        "passed": not test_ids and not quotes,
        "rule": (f"refuse if any transcript turn names a held-out test ID ({', '.join(sorted(kit.DEVELOPMENT_TEST_IDS))}) "
                 f"or shares {QUOTE_WORDS} or more consecutive words with a held-out test answer"),
        "turns_checked": len(turns),
        "test_answers_checked": sorted(answers),
        "test_ids_found": test_ids,
        "quotes_found": quotes,
    }


def _kit_minutes(person_dir: Path) -> tuple[float | None, str]:
    """kit_minutes as the assessment page records it in both answer files (build.json first)."""
    for name in ("build.json", "test.json"):
        try:
            value = json.loads((person_dir / name).read_text(encoding="utf-8")).get("kit_minutes")
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value), f"{name} kit_minutes (timed by the assessment page)"
    return None, "not recorded"


TRANSCRIPT_TURN_FIELDS = {"employee_turns": ("index", "seconds", "text"), "interviewer_turns": ("index", "text")}
TRANSCRIPT_FIELDS = ("person_id", "conversation_id", "duration_seconds", "source", "status")


def clean_transcript(raw: dict[str, Any]) -> dict[str, Any]:
    """Only the fields intake reads (text, positions, timing, source): anything else in an upload is dropped."""
    cleaned = {key: raw[key] for key in TRANSCRIPT_FIELDS if key in raw}
    for key, fields in TRANSCRIPT_TURN_FIELDS.items():
        cleaned[key] = [{f: turn[f] for f in fields if f in turn} for turn in raw.get(key) or [] if isinstance(turn, dict)]
    return cleaned


def guard_summary(guard: dict) -> str:
    """Where the guard tripped: turn and test ID only, never the matched words."""
    where = [f"{hit['turn']} names {hit['test_id']}" for hit in guard["test_ids_found"]]
    where += [f"{hit['turn']} quotes test answer {hit['test_answer']}" for hit in guard["quotes_found"]]
    return "; ".join(where)


def inspect_transcript(raw: Any, pid: str, test: Answers) -> dict:
    """Validate one interview transcript for one person and run the leakage guard. Never raises.

    Returns {evidence, transcript, leakage_guard, problem}: ``problem`` is None when the transcript can be used;
    ``evidence`` is None when there is a problem or no employee answers; ``leakage_guard`` is None only when the
    transcript was unusable before the guard could run.
    """
    from .intake import parse_transcript
    result: dict[str, Any] = {"evidence": None, "transcript": None, "leakage_guard": None, "problem": None}
    if not isinstance(raw, dict):
        result["problem"] = "the transcript is not a JSON object"
        return result
    named = str(raw.get("person_id") or "").strip()
    if named and named != pid:
        result["problem"] = f"the transcript names person {named}; it belongs in that person's folder"
        return result
    try:
        evidence = parse_transcript(raw)
    except (ValueError, TypeError, AttributeError) as error:  # e.g. an unknown source
        result["problem"] = f"the transcript is not usable: {error}"
        return result
    guard = leakage_check(raw, test)
    result["leakage_guard"] = guard
    if not guard["passed"]:
        result["problem"] = f"leakage guard refused the transcript ({guard_summary(guard)})"
        return result
    duration = getattr(evidence, "duration_seconds", None)
    source = getattr(evidence, "source", None) or raw.get("source")
    result["transcript"] = {
        "source": str(source) if source else "not recorded",
        "employee_answers": len(evidence),
        "evidence_ids": sorted(evidence.ids()),
        "duration_seconds": duration,
        "interview_minutes": round(duration / 60, 1) if duration is not None else None,
        "digest": evidence.digest(),
    }
    result["evidence"] = evidence if len(evidence) else None
    return result


def _load_interview(path: Path, pid: str, test: Answers, out: Path) -> tuple[Any, dict]:
    """(VoiceEvidence or None, transcript facts). Raises TranscriptLeakage or RuntimeError; the guard is written first."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError(f"{pid}: cannot read the interview transcript {path}: {error}") from error
    inspected = inspect_transcript(raw, pid, test)
    guard = inspected["leakage_guard"]
    if guard is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "leakage_guard.json").write_text(json.dumps(guard, indent=2), encoding="utf-8")
        if not guard["passed"]:
            raise TranscriptLeakage(f"{pid}: leakage guard refused the interview transcript ({guard_summary(guard)}). "
                                    "Keep the held-out test answers out of the alternative intake; remove those passages "
                                    f"in review and export the transcript again. Details: {out / 'leakage_guard.json'}", guard)
    if inspected["problem"]:
        raise RuntimeError(f"{pid}: interview transcript {path}: {inspected['problem']}")
    facts = {"path": str(path), **inspected["transcript"]}
    return inspected["evidence"], {"transcript": facts, "leakage_guard": guard}


def _people(people_dir: Path) -> list[Path]:
    return sorted(p for p in people_dir.iterdir() if p.is_dir() and (p / "build.json").exists() and (p / "test.json").exists())


def parse_pasted_text(text: str) -> dict[str, str]:
    """Plain-text answers file: a line '=== RUN_ID' then the pasted answer, until the next '===' line."""
    answers: dict[str, list[str]] = {}
    current = None
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith("==="):
            current = line.strip("= ").strip() or None
            if current:
                answers[current] = []
        elif current:
            answers[current].append(line)
    return {run_id: "\n".join(lines).strip() for run_id, lines in answers.items() if "\n".join(lines).strip()}


def pasted_responses(person_dir: Path, model: str) -> dict[str, str]:
    """Pasted answers for one model: llm_<model>.json (comparison format) and/or llm_<model>.txt (=== RUN_ID blocks)."""
    found: dict[str, str] = {}
    json_path = person_dir / f"llm_{model.lower()}.json"
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        found.update({r["run_id"]: r.get("text", "") for r in data.get("responses", []) if r.get("text", "").strip()})
    text_path = person_dir / f"llm_{model.lower()}.txt"
    if text_path.exists():
        found.update(parse_pasted_text(text_path.read_text(encoding="utf-8")))
    return found


def _write_paste_kit(person_dir: Path, out: Path, pid: str, profiles: dict[str, str], questions: dict[str, Question],
                     models: list[str]) -> None:
    packets = out / "paste_packets"
    packets.mkdir(parents=True, exist_ok=True)
    conditions = [("none", None), *profiles.items()]
    for condition, profile in conditions:
        if profile is not None:
            (packets / f"{condition}_message_1_profile.txt").write_text(profile, encoding="utf-8")
    for question_id, question in questions.items():
        (packets / f"{question_id}_message_2_question.txt").write_text(question.prompt, encoding="utf-8")
    for model in models:
        template = {"responses": []}
        blocks = []
        sheet = [f"# Paste sheet: {pid}, LLM {model}", "",
                 f"For EACH row: open a NEW chat on LLM {model} with memory and custom instructions OFF.",
                 "Message 1: paste the profile file (skip it when the condition is 'none'). Message 2: paste the question file.",
                 f"Paste the model's answer under its === line in {person_dir / ('llm_' + model.lower() + '.txt')}", "",
                 "| Run | Message 1 | Message 2 |", "|---|---|---|"]
        for condition, profile in conditions:
            for question_id in questions:
                run_id = f"{pid}-{model}-{condition}-{question_id}"
                template["responses"].append({"run_id": run_id, "question_id": question_id, "text": ""})
                blocks.append(f"=== {run_id}\n")
                first = f"paste_packets/{condition}_message_1_profile.txt" if profile is not None else "(none)"
                sheet.append(f"| {run_id} | {first} | paste_packets/{question_id}_message_2_question.txt |")
        (out / f"llm_{model.lower()}_template.json").write_text(json.dumps(template, indent=2), encoding="utf-8")
        (out / f"llm_{model.lower()}_answers_template.txt").write_text("\n".join(blocks), encoding="utf-8")
        (out / f"PASTE_SHEET_LLM_{model}.md").write_text("\n".join(sheet) + "\n", encoding="utf-8")


def run_experiment(people_dir: Path, questions: dict[str, Question], variants: list[str], out_dir: Path,
                   answerer: Answerer | None, judge_backend=None, transcripts: dict[str, Path] | None = None) -> dict:
    """answerer: calls LLM A through the API; None means LLM A is pasted by hand like LLM B.

    transcripts: optional {person_id: path} that overrides the person folder's voice_transcript.json.
    """
    rows: list[dict] = []
    interviews: dict[str, dict] = {}
    for person_dir in _people(people_dir):
        build = load_answers(person_dir / "build.json")
        test = load_answers(person_dir / "test.json")
        pid = build.person_id
        out = out_dir / pid
        out.mkdir(parents=True, exist_ok=True)
        transcript_path = (transcripts or {}).get(pid) or (person_dir / TRANSCRIPT_FILE)
        evidence = None
        if Path(transcript_path).exists():
            evidence, facts = _load_interview(Path(transcript_path), pid, test, out)
            kit_minutes, kit_source = _kit_minutes(person_dir)
            duration = facts["transcript"]["duration_seconds"]
            facts["effort"] = {
                "kit_minutes": kit_minutes, "kit_minutes_source": kit_source,
                "interview_minutes": round(duration / 60, 1) if duration is not None else None,
                "interview_minutes_source": ("transcript duration_seconds, taken by: " + facts["transcript"]["source"]
                                             if duration is not None else "not recorded"),
            }
            facts["arm_built"] = evidence is not None
            if evidence is None:
                facts["note"] = "the transcript has no employee answers, so no kit_plus_interview arm was built"
            facts["me_md_words"] = {}
            interviews[pid] = facts
        profiles: dict[str, str] = {}
        for variant in variants:
            profile = convert(build, variant=variant)
            if not profile.gate.passed:
                raise RuntimeError(f"{pid} {variant}: claims gate refused the profile: {profile.gate.blocking}")
            profiles[variant] = profile.markdown
            (out / f"me.{variant}.md").write_text(profile.markdown, encoding="utf-8")
            if pid in interviews:
                interviews[pid]["me_md_words"][variant] = len(profile.markdown.split())
            if evidence is not None:
                condition = variant + INTERVIEW_SUFFIX
                with_interview = convert(build, variant=variant, voice=evidence)
                if not with_interview.gate.passed:
                    raise RuntimeError(f"{pid} {condition}: claims gate refused the profile: {with_interview.gate.blocking}")
                profiles[condition] = with_interview.markdown
                (out / f"me.{condition}.md").write_text(with_interview.markdown, encoding="utf-8")
                interviews[pid]["me_md_words"][condition] = len(with_interview.markdown.split())
        _write_paste_kit(person_dir, out, pid, profiles, questions, ["B"] if answerer is not None else ["A", "B"])

        person_rows: list[dict] = []
        if answerer is not None:
            for condition, profile_text in [("none", None), *profiles.items()]:
                for question_id, question in questions.items():
                    text = answerer(profile_text, question)
                    person_rows.append({"person": pid, "model": "A", "condition": condition, "question_id": question_id,
                                        "run_id": f"{pid}-A-{condition}-{question_id}", "text": text})
        for model in (["B"] if answerer is not None else ["A", "B"]):
            for run_id, text in pasted_responses(person_dir, model).items():
                parts = run_id.split("-")
                if len(parts) >= 4 and parts[-3] == model and run_id.startswith(pid + "-"):
                    person_rows.append({"person": pid, "model": model, "condition": parts[-2], "question_id": parts[-1],
                                        "run_id": run_id, "text": text})

        for row in person_rows:
            question = questions.get(row["question_id"])
            row["type"] = question.type if question else "unknown"
            row["words"] = word_count(row["text"])
            row["over_limit"] = bool(question and row["words"] > question.word_limit)
            if row["type"] == "scenario":
                reference = test.scenarios.get(row["question_id"], {}).get("choice")
                row["choice"] = parse_choice(row["text"])
                row["reference_choice"] = reference
                row["choice_match"] = (row["choice"] == reference) if reference else None

        if judge_backend is not None and person_rows:
            from .judge.judge import judge_responses
            responses = [Response(r["run_id"], r["question_id"], r["text"]) for r in person_rows]
            verdicts = judge_responses(build, questions, test, responses, judge_backend)
            by_run = {e["run_id"]: e for e in verdicts["evaluations"]}
            for row in person_rows:
                evaluation = by_run.get(row["run_id"], {})
                row["judge_status"] = evaluation.get("status")
                row["resemblance"] = (evaluation.get("reference_resemblance") or {}).get("score")
                row["generic"] = (evaluation.get("generic_writing") or {}).get("is_generic")
        rows.extend(person_rows)

    summary = summarize(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"summary": summary, "rows": rows}
    markdown = render_markdown(summary, rows, variants)
    if interviews:
        comparison = compare_arms(rows, interviews, variants, ["A", "B"])
        comparison_md = render_comparison(comparison)
        result["comparison"] = comparison
        markdown += "\n" + comparison_md.replace("# Alternative intake", "## Alternative intake", 1)
        (out_dir / "comparison.json").write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")
        (out_dir / "comparison.md").write_text(comparison_md, encoding="utf-8")
    (out_dir / "results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "results.md").write_text(markdown, encoding="utf-8")
    return result


def _arm_of(condition: str) -> tuple[str, str]:
    """(variant, arm) for a condition name."""
    if condition.endswith(INTERVIEW_SUFFIX):
        return condition[: -len(INTERVIEW_SUFFIX)], KIT_PLUS_INTERVIEW
    return condition, KIT_ONLY


def compare_arms(rows: list[dict], interviews: dict[str, dict], variants: list[str], models: list[str]) -> dict:
    """Kit only vs kit plus interview, per person with a transcript, per model and variant."""
    people = []
    for pid, facts in sorted(interviews.items()):
        effort = facts["effort"]
        arms = []
        for model in models:
            for variant in variants:
                kit_accuracy = None
                for arm, condition in ((KIT_ONLY, variant), (KIT_PLUS_INTERVIEW, variant + INTERVIEW_SUFFIX)):
                    if arm == KIT_PLUS_INTERVIEW and not facts["arm_built"]:
                        continue
                    group = [r for r in rows if r["person"] == pid and r["model"] == model and r["condition"] == condition]
                    scored = [r for r in group if r.get("choice_match") is not None]
                    correct = sum(1 for r in scored if r["choice_match"])
                    scen = [r["resemblance"] for r in group if r.get("type") == "scenario" and isinstance(r.get("resemblance"), (int, float))]
                    writ = [r["resemblance"] for r in group if r.get("type") == "writing" and isinstance(r.get("resemblance"), (int, float))]
                    accuracy = round(correct / len(scored), 3) if scored else None
                    if arm == KIT_ONLY:
                        kit_accuracy = accuracy
                    minutes = effort["kit_minutes"]
                    if arm == KIT_PLUS_INTERVIEW:
                        minutes = (round(minutes + effort["interview_minutes"], 1)
                                   if minutes is not None and effort["interview_minutes"] is not None else None)
                    arms.append({
                        "model": model, "variant": variant, "arm": arm, "condition": condition,
                        "responses": len(group),
                        "choices": {r["question_id"]: {"chose": r.get("choice"), "person_chose": r.get("reference_choice"),
                                                       "match": r.get("choice_match")} for r in scored},
                        "choice_correct": correct, "choice_scored": len(scored), "choice_accuracy": accuracy,
                        "difference_vs_kit_only": (round(accuracy - kit_accuracy, 3)
                                                   if arm == KIT_PLUS_INTERVIEW and accuracy is not None and kit_accuracy is not None else None),
                        "scenario_resemblance_mean": round(statistics.mean(scen), 2) if scen else None,
                        "writing_resemblance_mean": round(statistics.mean(writ), 2) if writ else None,
                        "judged": len(scen) + len(writ),
                        "me_md_words": facts["me_md_words"].get(condition),
                        "intake_minutes": minutes,
                    })
        people.append({"person": pid, "transcript": facts["transcript"], "leakage_guard": facts["leakage_guard"],
                       "effort": effort, "arm_built": facts["arm_built"], **({"note": facts["note"]} if "note" in facts else {}),
                       "me_md_words": facts["me_md_words"], "arms": arms})
    return {
        "arms": [KIT_ONLY, KIT_PLUS_INTERVIEW],
        "method": ("Both arms answer the same held-out questions on the same models. Choice accuracy is an exact letter "
                   "match against the person's held-out answer, computed without any model. Judge resemblance is 0-4 "
                   "(null when no judge ran or evidence was insufficient). Intake minutes: kit minutes for kit only; "
                   "kit plus interview minutes for kit plus interview."),
        "people": people,
    }


def recompare(comparison: dict, rows: list[dict], variants: list[str], models: list[str] | None = None) -> dict:
    """The same comparison over updated rows (for example after the team hub judged them)."""
    return compare_arms(rows, {person["person"]: person for person in comparison["people"]}, variants, models or ["A", "B"])


def _minutes(value) -> str:
    return "not recorded" if value is None else f"{value:g}"


def render_comparison(comparison: dict) -> str:
    lines = ["# Alternative intake: kit only vs kit plus interview", "", comparison["method"], ""]
    for person in comparison["people"]:
        effort, guard, transcript = person["effort"], person["leakage_guard"], person["transcript"]
        lines += [
            f"### {person['person']}", "",
            f"- Leakage guard: {'passed' if guard['passed'] else 'REFUSED'} ({guard['turns_checked']} transcript turns checked "
            f"against {', '.join(guard['test_answers_checked']) or 'no test answers'}; {guard['rule']}).",
            f"- Interview: {transcript['employee_answers']} employee answers ({', '.join(transcript['evidence_ids']) or 'none'}), "
            f"taken by: {transcript['source']}.",
            f"- Kit minutes: {_minutes(effort['kit_minutes'])}. Source: {effort['kit_minutes_source']}.",
            f"- Interview minutes: {_minutes(effort['interview_minutes'])}. Source: {effort['interview_minutes_source']}.",
        ]
        if person.get("note"):
            lines.append(f"- Note: {person['note']}.")
        lines += ["", "| Model | Variant | Arm | Choices correct | Accuracy | Difference vs kit only | Scenario resemblance | "
                      "Writing resemblance | me.md words | Intake minutes |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for arm in person["arms"]:
            difference = arm["difference_vs_kit_only"]
            lines.append(
                f"| {arm['model']} | {arm['variant']} | {arm['arm']} | {arm['choice_correct']}/{arm['choice_scored']} | "
                f"{_fmt(arm['choice_accuracy'], True)} | {('+' if (difference or 0) > 0 else '') + _fmt(difference, True) if difference is not None else '-'} | "
                f"{_fmt(arm['scenario_resemblance_mean'])} | {_fmt(arm['writing_resemblance_mean'])} | {_fmt(arm['me_md_words'])} | "
                f"{_minutes(arm['intake_minutes'])} |")
        lines.append("")
    lines += ["One person, three scored scenarios per arm and model: a difference of one answer is 33 points and is noise. "
              "Report counts with every percentage. A null result is a result.", ""]
    return "\n".join(lines)


def summarize(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        groups.setdefault((row["model"], row["condition"]), []).append(row)
    summary = []
    for (model, condition), group in sorted(groups.items()):
        scored = [r for r in group if r.get("choice_match") is not None]
        correct = sum(1 for r in scored if r["choice_match"])
        scen = [r["resemblance"] for r in group if r.get("type") == "scenario" and isinstance(r.get("resemblance"), (int, float))]
        writ = [r["resemblance"] for r in group if r.get("type") == "writing" and isinstance(r.get("resemblance"), (int, float))]
        summary.append({
            "model": model, "condition": condition, "responses": len(group),
            "choice_correct": correct, "choice_scored": len(scored),
            "choice_accuracy": round(correct / len(scored), 3) if scored else None,
            "scenario_resemblance_mean": round(statistics.mean(scen), 2) if scen else None,
            "writing_resemblance_mean": round(statistics.mean(writ), 2) if writ else None,
            "over_limit": sum(1 for r in group if r.get("over_limit")),
            "flagged_generic": sum(1 for r in group if r.get("generic")),
        })
    baseline = {s["model"]: s["choice_accuracy"] for s in summary if s["condition"] == "none"}
    for s in summary:
        base = baseline.get(s["model"])
        s["lift_over_no_profile"] = (round(s["choice_accuracy"] - base, 3)
                                     if s["condition"] != "none" and s["choice_accuracy"] is not None and base is not None else None)
    return summary


def _fmt(value, pct: bool = False) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.0f}%" if pct else str(value)


def render_markdown(summary: list[dict], rows: list[dict], variants: list[str]) -> str:
    people = sorted({r["person"] for r in rows})
    lines = [
        "# Experiment results: human context lift",
        "",
        f"People: {len(people)}. Variants: {', '.join(variants)}. Conditions: no profile ('none') and each me.md variant. "
        "Choice accuracy is an exact letter match against the person's held-out answer, computed without any model. "
        "Resemblance is the AI judge's 0-4 score against the person's own answer (null = insufficient evidence or judge error).",
        "",
        "| Model | Condition | Scenario choices correct | Accuracy | Lift over no profile | Scenario resemblance | Writing resemblance | Over word limit | Flagged generic |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in summary:
        lines.append(f"| {s['model']} | {s['condition']} | {s['choice_correct']}/{s['choice_scored']} | {_fmt(s['choice_accuracy'], True)} | "
                     f"{('+' if (s['lift_over_no_profile'] or 0) > 0 else '') + _fmt(s['lift_over_no_profile'], True) if s['lift_over_no_profile'] is not None else '-'} | "
                     f"{_fmt(s['scenario_resemblance_mean'])} | {_fmt(s['writing_resemblance_mean'])} | {s['over_limit']} | {s['flagged_generic']} |")
    lines += ["", "## Every scenario response", "", "| Person | Model | Condition | Question | Chose | Person chose | Match |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        if r.get("type") == "scenario":
            lines.append(f"| {r['person']} | {r['model']} | {r['condition']} | {r['question_id']} | {r.get('choice') or '?'} | {r.get('reference_choice') or '?'} | "
                         f"{'yes' if r.get('choice_match') else 'no' if r.get('choice_match') is False else '-'} |")
    lines += ["", "Small samples: a few people times three scenarios. Report counts with every percentage, and treat differences of one or two answers as noise.", ""]
    return "\n".join(lines)


def anthropic_answerer(model: str | None = None, effort: str | None = None) -> Answerer:
    import anthropic
    from . import runner

    client = anthropic.Anthropic()
    model = model or runner.DEFAULT_MODEL
    effort = effort or runner.DEFAULT_EFFORT

    def answer(profile: str | None, question: Question) -> str:
        return runner.ask(client, profile, question, model, effort)["text"]

    return answer


def fake_answerer(profile: str | None, question: Question) -> str:
    """Plumbing check only: picks B with a profile, A without; writes a short message for writing tasks."""
    if question.type == "scenario":
        return ("B. " if profile else "A. ") + "Placeholder reason for a dry run."
    return "Placeholder message for a dry run."
