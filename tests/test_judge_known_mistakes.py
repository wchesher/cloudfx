# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_judge_known_mistakes - pins known judge mistakes as documented behaviour (docs/judge-mistake-example.md)

"""
These tests assert the CURRENT, WRONG output of the deterministic style layer. They document a known
limitation; they are not a specification. When the contraction counter is fixed to ignore possessive
"'s", both tests fail on purpose: update docs/judge-mistake-example.md and turn them into tests of the
correct behaviour.
"""

from __future__ import annotations

from mefile.judge.features import PersonCorpus, style_features, style_fidelity

# Fictional person: formal, never contracts, but writes possessives (supplier's, Monday's, committee's, team's).
FORMAL_PERSON = PersonCorpus(
    writing={
        "W01": "Good morning. The supplier's invoice arrived today. I will review it and I will reply by Friday.",
        "W03": "I am unable to attend Monday's meeting. Please send me the committee's notes.",
    },
    explanations={"S01": "I do not change a plan unless the team's data supports it."},
)
# A response in the person's own register: formal, no contractions.
FORMAL_RESPONSE = "I am sorry, but I cannot attend. I will read the notes and reply on Friday."


def test_known_limitation_possessive_counted_as_contraction_flags_formal_writer():
    # KNOWN LIMITATION (false positive): CONTRACTION_PATTERN counts possessive "'s" as a contraction, so a
    # person who never contracts is treated as someone who does, and a faithful formal response is flagged
    # P3 "lost signature marker". This asserts the wrong output on purpose.
    assert [style_features(text)["contractions"] for text in FORMAL_PERSON.writing.values()] == [1, 2]
    result = style_fidelity(FORMAL_RESPONSE, "writing", None, FORMAL_PERSON)
    assert result["categories"] == ["P3"]
    assert [flag["quote"] for flag in result["flags"]] == ["I am", "I will"]
    assert all("the person contracts (3 contractions in their own text)" in flag["detail"] for flag in result["flags"])


def test_known_limitation_same_person_without_possessives_is_not_flagged():
    # Control for the case above: the same sentences rephrased without "'s" raise no flag at all,
    # which isolates the possessive as the cause.
    rephrased = PersonCorpus(
        writing={
            "W01": "Good morning. The invoice from the supplier arrived today. I will review it and I will reply by Friday.",
            "W03": "I am unable to attend the meeting on Monday. Please send me the notes of the committee.",
        },
        explanations={"S01": "I do not change a plan unless the data of the team supports it."},
    )
    assert style_fidelity(FORMAL_RESPONSE, "writing", None, rephrased)["flags"] == []


def test_known_limitation_possessive_in_response_hides_lost_contractions():
    # KNOWN LIMITATION (mirror false negative): a person who does contract, and a response that never does
    # but mentions "Sam's", raises no P3 flag, because the possessive counts as the response's contraction.
    contracting_person = PersonCorpus(writing={"W01": "I'm out Friday, don't wait on me.", "W03": "Can't make it, we'll talk Monday."})
    result = style_fidelity("I am at Sam's place. I do not mind waiting.", "writing", None, contracting_person)
    assert "P3" not in result["categories"]
