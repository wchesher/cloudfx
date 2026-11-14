# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_scoring_and_runner - Common Kit section 6 scoring rules, and the runner's refusal to save a cut-off answer

from pathlib import Path
from types import SimpleNamespace

import pytest

from mefile import kit, runner, scoring
from mefile.answers import load_answers, parse_answers

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_demo01_domain_means_match_hand_calculation():
    scores = {ds.domain.key: ds for ds in scoring.score_domains(load_answers(EXAMPLES / "example_build_answers.json"))}
    assert scores["extraversion"].mean == 3.1
    assert scores["agreeableness"].mean == 3.5
    assert scores["conscientiousness"].mean == 3.11 and len(scores["conscientiousness"].answered) == 9  # B23 skipped
    assert scores["emotional_stability"].mean == 2.8
    assert scores["intellect"].mean == 3.0


def test_reverse_keying_is_six_minus_response():
    domain = next(d for d in kit.DOMAINS if d.key == "extraversion")
    assert scoring.keyed(domain, "B06", 4) == 2 and scoring.keyed(domain, "B01", 4) == 4


def test_three_skipped_items_mean_not_scored_and_never_midpoint_filled():
    domain = next(d for d in kit.DOMAINS if d.key == "extraversion")
    items = [{"id": i, "response": 5} for i in kit.ITEMS if i not in domain.items[:3]]
    ds = {d.domain.key: d for d in scoring.score_domains(parse_answers({"person_id": "X", "items": items}))}
    assert ds["extraversion"].mean is None and ds["extraversion"].band == "not scored"
    two_skipped = [{"id": i, "response": 5} for i in kit.ITEMS if i not in domain.items[:2]]
    ds = {d.domain.key: d for d in scoring.score_domains(parse_answers({"person_id": "X", "items": two_skipped}))}
    assert len(ds["extraversion"].answered) == 8 and ds["extraversion"].mean is not None


def _reply(text, stop):
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=text)], model="m")


def test_runner_refuses_a_capped_or_empty_reply():
    with pytest.raises(RuntimeError, match="token cap"):
        runner._text_of(_reply("B. Half an ans", "max_tokens"))
    with pytest.raises(RuntimeError, match="no text"):
        runner._text_of(_reply("  ", "end_turn"))
    assert runner._text_of(_reply(" B. A call settles it. ", "end_turn")) == "B. A call settles it."
