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
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Callable

from .answers import Answers, Question, Response, load_answers
from .converter import VARIANTS, convert
from .judge.features import parse_choice, word_count

Answerer = Callable[[str | None, Question], str]


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
                   answerer: Answerer | None, judge_backend=None) -> dict:
    """answerer: calls LLM A through the API; None means LLM A is pasted by hand like LLM B."""
    rows: list[dict] = []
    for person_dir in _people(people_dir):
        build = load_answers(person_dir / "build.json")
        test = load_answers(person_dir / "test.json")
        pid = build.person_id
        out = out_dir / pid
        out.mkdir(parents=True, exist_ok=True)
        profiles: dict[str, str] = {}
        for variant in variants:
            profile = convert(build, variant=variant)
            if not profile.gate.passed:
                raise RuntimeError(f"{pid} {variant}: claims gate refused the profile: {profile.gate.blocking}")
            profiles[variant] = profile.markdown
            (out / f"me.{variant}.md").write_text(profile.markdown, encoding="utf-8")
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
    (out_dir / "results.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "results.md").write_text(render_markdown(summary, rows, variants), encoding="utf-8")
    return {"summary": summary, "rows": rows}


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
