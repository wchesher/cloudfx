# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# __main__ - command line entry for the AI judge: evaluate responses, or run the self-check

"""
Usage:
  python -m mefile.judge --build BUILD.json --questions QUESTIONS.json --reference TEST.json \
      --responses OURS.json [COMPARISONS.json ...] --out DIR [--fake] \
      [--generation-model claude-opus-5-5 --generation-model gpt-sol-6.1]
  python -m mefile.judge selfcheck [--fake] [--out DIR]

The real backend reads its credentials from the environment (ANTHROPIC_API_KEY or an
``ant auth login`` profile) and its model from MEFILE_JUDGE_MODEL (default claude-opus-5-5).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..answers import load_answers, load_questions, load_responses
from .backend import FakeJudgeBackend
from .eval_corpus import format_selfcheck, run_judge_selfcheck
from .judge import judge_responses
from .report import write_reports


def _backend(fake: bool):
    if fake:
        return FakeJudgeBackend()
    from .anthropic_backend import AnthropicJudgeBackend

    return AnthropicJudgeBackend()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "selfcheck":
        parser = argparse.ArgumentParser(prog="python -m mefile.judge selfcheck")
        parser.add_argument("--fake", action="store_true", help="plumbing check with the deterministic fake backend")
        parser.add_argument("--out", help="directory to write selfcheck.json")
        args = parser.parse_args(argv[1:])
        report = run_judge_selfcheck(_backend(args.fake))
        print(format_selfcheck(report))
        if args.out:
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            (out / "selfcheck.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return 0

    parser = argparse.ArgumentParser(prog="python -m mefile.judge")
    parser.add_argument("--build", required=True, help="the person's build answer file")
    parser.add_argument("--questions", required=True, help="question file (id, type, wording, options, word_limit, prompt)")
    parser.add_argument("--reference", help="the person's own answers to the test questions")
    parser.add_argument("--responses", required=True, nargs="+", help="one or more response files (run_id, question_id, text)")
    parser.add_argument("--out", required=True, help="output directory for evaluations.json and evaluations.md")
    parser.add_argument("--generation-model", action="append", default=[], help="a model under test (warns if it equals the judge model)")
    parser.add_argument("--fake", action="store_true", help="use the deterministic fake backend (no network)")
    args = parser.parse_args(argv)

    build = load_answers(args.build)
    questions = load_questions(args.questions)
    reference = load_answers(args.reference) if args.reference else None
    responses = [r for path in args.responses for r in load_responses(path)]
    result = judge_responses(build, questions, reference, responses, _backend(args.fake), args.generation_model)
    json_path, md_path = write_reports(result, args.out)
    ok = sum(1 for e in result["evaluations"] if e["status"] == "ok")
    print(f"{ok}/{len(result['evaluations'])} evaluated; wrote {json_path} and {md_path}")
    for warning in result["metadata"]["warnings"]:
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
