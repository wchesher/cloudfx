# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_converter_fixes - three misreadings found in a real profile, pinned with fictional answers

from __future__ import annotations

import json
from pathlib import Path

from mefile import style
from mefile.answers import parse_answers
from mefile.converter import convert

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "example_build_answers.json"


def _answers(**changes):
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    for scenario in data["scenarios"]:
        if scenario["id"] in changes:
            scenario["choice"], scenario["explanation"] = changes[scenario["id"]]
    for message in data["writing"]:
        if message["id"] == "W01":
            message["text"] = "Guys,\nThanks for the work on this. The project is stopping and we will reuse what you built."
    return parse_answers(data)


def test_guys_is_a_greeting():
    assert style.measure("Guys,\nThanks for everything.").greets is True


def test_indirect_plus_let_it_pass_is_not_called_through_someone_else():
    md = convert(_answers(S01=("D", "Asking a question keeps it calm."),
                          S05=("C", "The idea matters more than credit. It usually comes out anyway.")), scope="full").markdown
    assert "Tends not to push back openly, raising disagreement indirectly or letting it pass" in md
    assert "Tends to raise disagreement indirectly or through someone else" not in md
    assert "Opens with a greeting in some messages (W01)" in md or "Opens with a greeting" in md
    assert "in up to 2 sentences" in md  # the S05 reason has two sentences
