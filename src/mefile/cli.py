# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# cli - command line: convert, final (the freeze-day pipeline), run (Claude API), serve (review app)

"""
mefile command line
===================

    python -m mefile convert BUILD.json [--out DIR] [--scope full|coaching] [--withhold DOMAIN ...]
    python -m mefile final   BUILD.json QUESTIONS.json --out DIR      # freeze-day: me.md + paste packets + templates
    python -m mefile run     QUESTIONS.json --out FILE [--profile me.md] --prefix A    # LLM A via the Claude API
    python -m mefile serve   [--port 8080]                                              # consent + review app

``final`` refuses to write a profile that fails the claims gate (fail-closed); fix the converter,
never the file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import kit
from .answers import load_answers, load_questions
from .converter import SHARE_SCOPES, convert


def _write_profile(build_path: str, out_dir: Path, scope: str, withhold: list[str], variant: str = "evidence_first") -> int:
    answers = load_answers(build_path)
    for problem in answers.problems:
        print(f"input note: {problem}")
    profile = convert(answers, scope=scope, excluded_domains=set(withhold), variant=variant)
    out_dir.mkdir(parents=True, exist_ok=True)
    gate_lines = [f"BLOCKING: {b}" for b in profile.gate.blocking] + [f"warning: {w}" for w in profile.gate.warnings]
    (out_dir / "gate.txt").write_text("\n".join(gate_lines) + "\n", encoding="utf-8")
    for line in gate_lines:
        print(line)
    if not profile.gate.passed:
        print("claims gate FAILED: me.md was not written. Fix the converter or the input, not the file.")
        return 2
    (out_dir / "me.md").write_text(profile.markdown, encoding="utf-8")
    (out_dir / "me.json").write_text(json.dumps(profile.sidecar, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out_dir / 'me.md'} ({len(profile.markdown.split())} words, {len(profile.claims)} claims) and me.json")
    return 0


def cmd_convert(args) -> int:
    return _write_profile(args.build, Path(args.out), args.scope, args.withhold or [], args.variant)


def cmd_final(args) -> int:
    out = Path(args.out)
    status = _write_profile(args.build, out, "full", [])
    if status:
        return status
    profile = (out / "me.md").read_text(encoding="utf-8")
    questions = load_questions(args.questions)
    packets = out / "paste_packets"
    packets.mkdir(exist_ok=True)
    steps = ["# Freeze-day run sheet", "",
             "For EVERY question and EVERY model: open a NEW conversation, memory and custom instructions OFF.",
             "Message 1: paste the whole of `me.md` (also saved as message_1_profile.txt). Message 2: paste the question file below.",
             "Record the model name shown. Paste the answer into responses_template.json.", ""]
    template = {"responses": []}
    for question_id, question in questions.items():
        (packets / f"{question_id}_message_2_question.txt").write_text(question.prompt, encoding="utf-8")
        for system in ("A", "B"):
            template["responses"].append({"run_id": f"{args.team}-{system}-{question_id}", "question_id": question_id, "text": ""})
        steps.append(f"- {question_id} ({question.type}, {question.word_limit} words max): LLM A and LLM B")
    (packets / "message_1_profile.txt").write_text(profile, encoding="utf-8")
    (out / "responses_template.json").write_text(json.dumps(template, indent=2), encoding="utf-8")
    steps += ["", "LLM A: Claude Opus 5.5 Medium. LLM B: GPT Sol 6.1 Medium.",
              "Then: python -m mefile.judge --build BUILD --questions QUESTIONS --reference TEST --responses responses.json comparisons.json --out judge/"]
    (out / "RUN_SHEET.md").write_text("\n".join(steps) + "\n", encoding="utf-8")
    print(f"wrote paste packets for {len(questions)} questions, responses_template.json and RUN_SHEET.md in {out}")
    return 0


def cmd_run(args) -> int:
    from .runner import run_all
    profile = Path(args.profile).read_text(encoding="utf-8") if args.profile else None
    run_all(profile, load_questions(args.questions), args.prefix, Path(args.out))
    return 0


def cmd_experiment(args) -> int:
    from .experiment import anthropic_answerer, fake_answerer, run_experiment
    answerer = fake_answerer if args.dry_run else (None if args.manual else anthropic_answerer())
    judge_backend = None
    if args.judge:
        from .judge.backend import FakeJudgeBackend
        if args.dry_run:
            judge_backend = FakeJudgeBackend()
        else:
            from .judge.anthropic_backend import AnthropicJudgeBackend
            judge_backend = AnthropicJudgeBackend()
    result = run_experiment(Path(args.people), load_questions(args.questions), args.variants, Path(args.out), answerer, judge_backend)
    for s in result["summary"]:
        accuracy = "-" if s["choice_accuracy"] is None else f"{s['choice_accuracy']:.0%}"
        print(f"{s['model']} {s['condition']:<15} choices {s['choice_correct']}/{s['choice_scored']} ({accuracy})  lift {s['lift_over_no_profile']}")
    print(f"wrote {Path(args.out) / 'results.md'}")
    if args.manual:
        print(f"paste sheets: {Path(args.out)}/<PERSON>/PASTE_SHEET_LLM_A.md and PASTE_SHEET_LLM_B.md; re-run with --manual after pasting to rescore")
    return 0


def cmd_serve(args) -> int:
    from .app import serve
    serve(args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mefile", description="Common Kit answers in, me.md out.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("convert", help="build answers -> me.md + me.json")
    p.add_argument("build")
    p.add_argument("--out", default="out")
    p.add_argument("--scope", choices=sorted(SHARE_SCOPES), default="full")
    p.add_argument("--variant", default="evidence_first")
    p.add_argument("--withhold", nargs="*", choices=[d.key for d in kit.DOMAINS])
    p.set_defaults(func=cmd_convert)

    p = sub.add_parser("final", help="freeze-day pipeline: me.md, paste packets, response template, run sheet")
    p.add_argument("build")
    p.add_argument("questions")
    p.add_argument("--out", default="final")
    p.add_argument("--team", default="TEAM")
    p.set_defaults(func=cmd_final)

    p = sub.add_parser("run", help="answer questions on LLM A through the Claude API (two-turn loading protocol)")
    p.add_argument("questions")
    p.add_argument("--profile", help="me.md to load first; omit for the no-profile condition")
    p.add_argument("--prefix", default="A")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("experiment", help="profile vs no-profile, per me.md variant, scored against held-out answers")
    p.add_argument("--people", default="private/people", help="one folder per person with build.json and test.json")
    p.add_argument("--questions", default="examples/example_questions.json", help="the held-out questions (S02, S04, S06, W02, W04)")
    p.add_argument("--variants", nargs="+", default=["evidence_first", "trait_first", "short"])
    p.add_argument("--out", default="private/experiment")
    p.add_argument("--judge", action="store_true", help="also run the AI judge on every response")
    p.add_argument("--dry-run", action="store_true", help="fake answerer and fake judge: checks the plumbing, no API calls")
    p.add_argument("--manual", action="store_true", help="no API for LLM A: write paste sheets for A and B, score whatever has been pasted")
    p.set_defaults(func=cmd_experiment)

    p = sub.add_parser("serve", help="consent, review and export app")
    p.add_argument("--port", type=int, default=8080)
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
