# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# readings - "other ways to read this": fixed, hedged, non-personality explanations for each claim, as data

"""
Other ways to read this (ethics review: cultural and contextual interpretation)
===============================================================================

Every claim in a profile reads the person's answers one way: as a tendency of the person. The same
answer often has a better explanation that is not personality at all: what the role asks for, how
the team works, norms about directness and self-promotion that differ between workplaces and
language communities, a heavy stretch of work, or simply how the question was read. This module
gives each claim two or three such readings, in plain words, so the person and anyone they share
with see the alternatives next to the claim.

Rules for the wording (the tests hold them):
  - Deterministic: fixed tables keyed by trait domain and direction, by scenario and choice, and
    by evidence type. No model call, no randomness; the same claim always gets the same readings.
  - Hedged: every reading says "may", "might", "can" or "could". None is a finding.
  - Kind and non-stereotyping: no reading names a culture, nationality, region, religion, gender
    or age group. Differences are attributed to settings (teams, roles, workplaces, language
    communities), never to a kind of person.
  - Not personality: each reading points at the situation, the role, the norms or the question.

Limit claims get no readings: they already state what the evidence cannot show.

The readings go into the JSON sidecar only. The me.md text is never changed by this module.
"""

from __future__ import annotations

from . import kit, scoring
from .claims import Claim

# One reading every self-rating claim carries: the statements are short and can be read more than one way.
QUESTION_READING = ("Short self-rating statements can be read in more than one way, for example about work or about "
                    "life as a whole, now or usually, so the same answer may mean different things to different people.")
SINGLE_ITEM_READING = ("This is one answer to one statement; it may reflect a particular recent experience more than "
                       "a general pattern.")
MIDDLE_READINGS = (
    "A middle score can mean the person acts differently in different settings, not that they have no preference.",
    "It may also come from answering some statements with work in mind and others with life outside work in mind.",
)
MIXED_READINGS = (
    "Answers that point both ways within one area may mean behaviour changes with the setting or the people involved.",
)

# (domain key, direction) -> two readings. Direction is "higher" or "lower" after reverse-keying.
TRAIT_READINGS: dict[tuple[str, str], tuple[str, str]] = {
    ("extraversion", "higher"): (
        "Roles such as teaching, sales, support or leading a team ask people to speak up in groups; the ratings may "
        "describe what the job has practised more than a preference.",
        "Norms about describing oneself differ: in some settings rating one's own sociability highly is expected, "
        "in others it can sound like boasting, which may move answers either way.",
    ),
    ("extraversion", "lower"): (
        "Working mostly remotely, being new to a team, or speaking in a language that is not the person's strongest "
        "can make anyone quieter in groups for reasons that have nothing to do with temperament.",
        "Teams and language communities differ in how much one is expected to talk in a group, especially with "
        "senior people present; being quieter may be a form of respect in the settings the person knows.",
    ),
    ("agreeableness", "higher"): (
        "Some teams and roles reward smoothing things over; the ratings may reflect what has worked in that setting.",
        "Many people learn that putting others first is simply polite, so describing oneself this way may follow a "
        "norm about modesty more than a preference.",
    ),
    ("agreeableness", "lower"): (
        "Roles that require holding a firm line, such as reviewing, negotiating, auditing or safety work, can make "
        "focusing on the task over feelings part of the job.",
        "Teams, families and language communities differ in how openly care is shown; the ratings may track how "
        "care is expressed rather than how much the person cares.",
    ),
    ("conscientiousness", "higher"): (
        "Roles with deadlines, audits or safety rules make structure part of the job; the ratings may describe the "
        "role's demands more than a preference.",
        "Statements about order and preparation may have been read as being about work only, where routines are "
        "often set by the team.",
    ),
    ("conscientiousness", "lower"): (
        "A heavy or unpredictable workload can make anyone less organized for a while; these ratings may describe a "
        "busy stretch more than a lasting habit.",
        "Fast-moving teams often reward flexibility over planning; the ratings may reflect what the work asks for.",
    ),
    ("emotional_stability", "higher"): (
        "Some workplaces discourage showing worry or frustration, which can make calm the expected answer.",
        "A steady period at work or outside it can make anyone rate themselves calmer for now.",
    ),
    ("emotional_stability", "lower"): (
        "Current workload or circumstances, at work or outside it, can raise ratings like these for a while; they "
        "may describe a demanding period rather than the person.",
        "Settings differ in how acceptable it is to admit worry or irritation; these ratings may reflect how "
        "comfortable the person felt saying so, which can be a sign of candour.",
    ),
    ("intellect", "higher"): (
        "Roles in research, design or planning reward abstract thinking; the ratings may describe what the work "
        "exercises more than a preference.",
        "Norms about describing oneself differ: in some settings calling oneself full of ideas is expected, in "
        "others it can sound immodest, which may move answers either way.",
    ),
    ("intellect", "lower"): (
        "Several statements here ask about vocabulary and abstract ideas; answering in a language that is not the "
        "person's strongest, or schooling, can lower these ratings without saying anything about curiosity.",
        "Practical, hands-on roles can make concrete thinking the useful habit at work, so the ratings may reflect "
        "the job's needs.",
    ),
}

# Scenario readings: two that fit any choice, then one per choice letter. Build scenarios only (S01, S03, S05).
SCENARIO_READINGS: dict[str, tuple[str, str]] = {
    "S01": (
        "Whether it feels safe or worthwhile to question a manager in front of others depends a lot on the team and "
        "the manager; the choice may describe that setting more than the person.",
        "Current workload may shape how a deadline like this is weighed: someone already stretched may see it "
        "differently from someone with spare time.",
    ),
    "S03": (
        "Teams differ in how much authority they give people to undo work without sign-off; the choice may follow "
        "the team's incident rules or past practice.",
        "The person may have pictured a particular system or customer while reading the question, which can change "
        "what the safe choice looks like.",
    ),
    "S05": (
        "Norms about claiming credit differ between teams, workplaces and language communities; in some it is "
        "expected, in others it can read as self-promotion.",
        "The relationship with the colleague, and whether credit has been overlooked before, can change what seems "
        "worth raising.",
    ),
}
CHOICE_READINGS: dict[tuple[str, str], str] = {
    ("S01", "A"): "Some roles, such as a lead or the specialist asked for estimates, may make speaking up in the meeting part of the job.",
    ("S01", "B"): ("In many workplaces and language communities, raising a concern privately with the decision-maker "
                   "may be the respectful way to disagree, not a way of avoiding it."),
    ("S01", "C"): ("Being new, on a short contract, or in a team where pushing back has gone badly before can make "
                   "going along the sensible choice."),
    ("S01", "D"): "Asking a question instead of stating disagreement may be the ordinary, polite way to raise a risk in many teams and languages.",
    ("S03", "A"): "Roles responsible for keeping a service running may be expected to roll back first and investigate later.",
    ("S03", "B"): "Some teams may expect people to attempt a fix within a set time before rolling back.",
    ("S03", "C"): ("A role that has been told not to act without the lead, or a recent incident that went badly, may "
                   "make waiting the expected step."),
    ("S03", "D"): "Some teams may ask for the impact to be measured before any change during an incident.",
    ("S05", "A"): "In teams where credit is tracked openly, saying so in the meeting may simply be how attribution is done.",
    ("S05", "B"): "Raising it privately may be seen as the considerate way to protect a working relationship.",
    ("S05", "C"): "Someone who is already well recognized, or has a heavy workload, may reasonably let it go.",
    ("S05", "D"): "In some workplaces the manager may be the expected route for questions of credit.",
}
PATTERN_READINGS = (
    "A pattern across two or three situations is still very few situations; a different team or manager could change it.",
    "Norms about how directly to disagree differ between teams, workplaces and language communities, so the same "
    "choice can be blunt in one setting and polite in another.",
    SCENARIO_READINGS["S01"][0],
)

# Observed style, by the kind of evidence the claim measures.
STYLE_READINGS: dict[str, tuple[str, str]] = {
    "W": (
        "The messages were written for practice prompts, not to real colleagues; real messages may change with the "
        "audience, the tool and the stakes.",
        "Contractions, greetings and length may follow a team's or a channel's habits, or writing in a language "
        "that is not the person's strongest, more than personal style.",
    ),
    "V": (
        "The spoken answers were given in an interview, which can make anyone more formal or more hesitant than usual.",
        "Speech-to-text can change words, and speaking in a language that is not the person's strongest may affect "
        "hedging and length.",
    ),
    "S": (
        "The length of a written reason may follow the size of the answer box and the time available more than a habit.",
        "Writing in a language that is not the person's strongest can make reasons shorter or longer without saying "
        "anything about how the person thinks.",
    ),
}


def _domain_of(item_id: str) -> kit.Domain | None:
    for domain in kit.DOMAINS:
        if item_id in domain.items:
            return domain
    return None


def _measured(claim: Claim, answers, scores: list[scoring.DomainScore]) -> list[str]:
    domain = _domain_of(claim.evidence[0]) if claim.evidence else None
    if domain is None:
        return [*MIDDLE_READINGS, QUESTION_READING]
    if len(claim.evidence) == 2:  # two items in one domain pointing in opposite directions
        return [*MIXED_READINGS, MIDDLE_READINGS[0], QUESTION_READING]
    if len(claim.evidence) == 1:  # one emphatic self-description (answered 1 or 5)
        item_id = claim.evidence[0]
        response = answers.items.get(item_id)
        if response is None:
            return [SINGLE_ITEM_READING, QUESTION_READING]
        direction = "higher" if scoring.keyed(domain, item_id, response) >= 4 else "lower"
        return [TRAIT_READINGS[(domain.key, direction)][0], SINGLE_ITEM_READING, QUESTION_READING]
    score = next((ds for ds in scores if ds.domain.key == domain.key), None)
    if score is None or score.mean is None or 2.5 < score.mean < 3.5:
        return [*MIDDLE_READINGS, QUESTION_READING]
    direction = "higher" if score.mean >= 3.5 else "lower"
    return [*TRAIT_READINGS[(domain.key, direction)], QUESTION_READING]


def _reported(claim: Claim, answers) -> list[str]:
    scenario_ids = [e for e in claim.evidence if e in SCENARIO_READINGS]
    if len(scenario_ids) != 1:
        return list(PATTERN_READINGS)
    scenario_id = scenario_ids[0]
    choice = answers.scenarios.get(scenario_id, {}).get("choice")
    readings = list(SCENARIO_READINGS[scenario_id])
    if (scenario_id, choice) in CHOICE_READINGS:
        readings.append(CHOICE_READINGS[(scenario_id, choice)])
    return readings


def other_readings(claim: Claim, answers, scores: list[scoring.DomainScore]) -> list[str]:
    """Two or three hedged, non-personality explanations for one claim; an empty list for a limit claim."""
    if claim.kind == "measured":
        return _measured(claim, answers, scores)
    if claim.kind == "reported":
        return _reported(claim, answers)
    if claim.kind == "observed_style":
        prefix = claim.evidence[0][:1] if claim.evidence else "W"
        return list(STYLE_READINGS.get(prefix, STYLE_READINGS["W"]))
    return []


def readings_for(claims: list[Claim], answers, scores: list[scoring.DomainScore]) -> dict[str, list[str]]:
    """Claim ID -> its other readings, for every claim in a profile."""
    return {claim.id: other_readings(claim, answers, scores) for claim in claims}
