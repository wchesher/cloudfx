# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_practice - the practice library and "ask your own" questions stay separate from the kit and well formed

import pytest

from mefile import kit, practice


def test_library_has_twenty_situations_none_from_the_kit():
    assert len(practice.LIBRARY) == 20 and len(practice.BY_ID) == 20
    kit_text = {s["wording"] for s in kit.SCENARIOS.values()} | set(kit.WRITING_PROMPTS.values())
    for situation in practice.LIBRARY:
        assert situation.wording not in kit_text and not situation.id.startswith(("S", "W", "B"))
        if situation.type == "scenario":
            assert set(situation.options) == {"A", "B", "C", "D"}


def test_prompts_follow_the_kit_shape():
    scenario = practice.as_question(practice.BY_ID["P01"])
    assert scenario.prompt.startswith("Choose A, B, C or D") and "A. Agree" in scenario.prompt and scenario.word_limit == 60
    writing = practice.as_question(practice.BY_ID["P13"])
    assert writing.prompt.startswith("Write the actual message") and writing.word_limit == 80


def test_own_question_is_wrapped_and_bounded():
    question = practice.own_question("  My manager   moved my deadline up a week. ")
    assert question.id == "OWN" and "My manager moved my deadline up a week." in question.prompt
    assert practice.own_question("Ask for a day off", kind="message").type == "writing"
    with pytest.raises(ValueError):
        practice.own_question("   ")
    with pytest.raises(ValueError):
        practice.own_question("x" * 601)
