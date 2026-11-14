# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# kit - the Digital Personality Modeling Common Kit as data: items, scoring key, scenarios, writing prompts

"""
The Common Kit as DATA
======================

One machine-readable module carries everything the organizers fixed: the 50 IPIP items and their
keying, the build and test split, the six scenarios and the four writing prompts. The converter,
the safeguard and the judge all read this module and nothing else, so a scoring key or an option
label cannot drift between them (the pattern of teenyverse3 ``partner/contract.py``: the prompt,
the classifier and the published contract are generated from one data module).

The one thing here the kit does not supply is ``OPTION_SIGNALS``: what each BUILD scenario option
says about how a person handles a situation. It is fixed per option, written once, and applied to
every person identically, so it is converter logic, not person-specific editing.
"""

from __future__ import annotations

from dataclasses import dataclass

KIT_VERSION = "dpm-common-kit/2026-11-14"

# ---------------------------------------------------------------------------
# Inventory (Section 3) and scoring key (Section 6)
# ---------------------------------------------------------------------------

RESPONSE_LABELS = {
    1: "very inaccurate",
    2: "moderately inaccurate",
    3: "neither accurate nor inaccurate",
    4: "moderately accurate",
    5: "very accurate",
}

ITEMS: dict[str, str] = {
    "B01": "Am the life of the party.",
    "B02": "Feel little concern for others.",
    "B03": "Am always prepared.",
    "B04": "Get stressed out easily.",
    "B05": "Have a rich vocabulary.",
    "B06": "Don't talk a lot.",
    "B07": "Am interested in people.",
    "B08": "Leave my belongings around.",
    "B09": "Am relaxed most of the time.",
    "B10": "Have difficulty understanding abstract ideas.",
    "B11": "Feel comfortable around people.",
    "B12": "Insult people.",
    "B13": "Pay attention to details.",
    "B14": "Worry about things.",
    "B15": "Have a vivid imagination.",
    "B16": "Keep in the background.",
    "B17": "Sympathize with others' feelings.",
    "B18": "Make a mess of things.",
    "B19": "Seldom feel blue.",
    "B20": "Am not interested in abstract ideas.",
    "B21": "Start conversations.",
    "B22": "Am not interested in other people's problems.",
    "B23": "Get chores done right away.",
    "B24": "Am easily disturbed.",
    "B25": "Have excellent ideas.",
    "B26": "Have little to say.",
    "B27": "Have a soft heart.",
    "B28": "Often forget to put things back in their proper place.",
    "B29": "Get upset easily.",
    "B30": "Do not have a good imagination.",
    "B31": "Talk to a lot of different people at parties.",
    "B32": "Am not really interested in others.",
    "B33": "Like order.",
    "B34": "Change my mood a lot.",
    "B35": "Am quick to understand things.",
    "B36": "Don't like to draw attention to myself.",
    "B37": "Take time out for others.",
    "B38": "Shirk my duties.",
    "B39": "Have frequent mood swings.",
    "B40": "Use difficult words.",
    "B41": "Don't mind being the center of attention.",
    "B42": "Feel others' emotions.",
    "B43": "Follow a schedule.",
    "B44": "Get irritated easily.",
    "B45": "Spend time reflecting on things.",
    "B46": "Am quiet around strangers.",
    "B47": "Make people feel at ease.",
    "B48": "Am exacting in my work.",
    "B49": "Often feel blue.",
    "B50": "Am full of ideas.",
}


@dataclass(frozen=True)
class Domain:
    key: str
    label: str
    positive: tuple[str, ...]
    reverse: tuple[str, ...]
    higher: str
    lower: str

    @property
    def items(self) -> tuple[str, ...]:
        return self.positive + self.reverse


DOMAINS: tuple[Domain, ...] = (
    Domain(
        "extraversion", "Extraversion",
        ("B01", "B11", "B21", "B31", "B41"),
        ("B06", "B16", "B26", "B36", "B46"),
        higher="more outgoing and talkative in groups",
        lower="more reserved and quieter in groups",
    ),
    Domain(
        "agreeableness", "Agreeableness",
        ("B07", "B17", "B27", "B37", "B42", "B47"),
        ("B02", "B12", "B22", "B32"),
        higher="more attentive to other people's feelings and needs",
        lower="less focused on other people's feelings and needs",
    ),
    Domain(
        "conscientiousness", "Conscientiousness",
        ("B03", "B13", "B23", "B33", "B43", "B48"),
        ("B08", "B18", "B28", "B38"),
        higher="more organized, prepared and structured",
        lower="more flexible and less structured",
    ),
    Domain(
        "emotional_stability", "Emotional Stability",
        ("B09", "B19"),
        ("B04", "B14", "B24", "B29", "B34", "B39", "B44", "B49"),
        higher="calmer and steadier under pressure",
        lower="more prone to stress, worry or irritation",
    ),
    Domain(
        "intellect", "Intellect/Imagination",
        ("B05", "B15", "B25", "B35", "B40", "B45", "B50"),
        ("B10", "B20", "B30"),
        higher="more drawn to ideas, imagination and reflection",
        lower="more practical and concrete",
    ),
)

# Items whose wording turns on vocabulary and word use (Section 6 interpretation caveat).
LANGUAGE_SENSITIVE_ITEMS = ("B05", "B40")

# ---------------------------------------------------------------------------
# Scenarios (Section 4) and writing prompts (Section 5)
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, dict] = {
    "S01": {
        "wording": "In a planning meeting your manager proposes a deadline you are fairly sure the team cannot hit. Everyone else nods.",
        "options": {
            "A": "Say so in the meeting and give your reasons.",
            "B": "Go along in the meeting and raise it with your manager privately afterwards.",
            "C": "Go along and plan to put in extra hours to try to hit it.",
            "D": "Ask a question in the meeting that points at the risk without saying you disagree.",
        },
    },
    "S02": {
        "wording": "A senior colleague from another team leaves a long comment on your work in a shared document. You think most of their points are wrong.",
        "options": {
            "A": "Reply in the document, point by point.",
            "B": "Message them directly and suggest a short call.",
            "C": "Make the changes they asked for to avoid friction.",
            "D": "Ask your manager to weigh in.",
        },
    },
    "S03": {
        "wording": "Late on a Friday, something you shipped starts failing for some customers. Undoing it removes a feature they asked for. A fix might take one hour or four. Your lead is unreachable.",
        "options": {
            "A": "Undo it now and fix it properly next week.",
            "B": "Try the fix, but undo it if it is not working within an hour.",
            "C": "Keep trying to reach your lead before doing anything.",
            "D": "Spend 20 minutes finding out how many customers are affected, then decide.",
        },
    },
    "S04": {
        "wording": "You must pick a supplier by end of day. Information is incomplete. One is cheaper and new to you; the other costs 30% more and you have used them before without trouble.",
        "options": {
            "A": "The familiar one.",
            "B": "The cheaper one.",
            "C": "Ask for a week's extension to gather more information.",
            "D": "The cheaper one, with a clause that lets you walk away early.",
        },
    },
    "S05": {
        "wording": "In a meeting a colleague presents an idea that was mostly yours. They do not mention you.",
        "options": {
            "A": "Say in the meeting that you had worked on this with them.",
            "B": "Talk to them privately afterwards.",
            "C": "Let it go. The idea moving forward is what matters.",
            "D": "Make sure your manager knows, without confronting the colleague.",
        },
    },
    "S06": {
        "wording": "You are asked to choose who takes on one interesting assignment: you, or a junior colleague who would learn a lot from it but would need your help.",
        "options": {
            "A": "Take it yourself.",
            "B": "Give it to the junior colleague.",
            "C": "Propose doing it together.",
            "D": "Ask your manager to decide.",
        },
    },
}

WRITING_PROMPTS: dict[str, str] = {
    "W01": "You have to tell your team that a project they worked hard on has been cancelled. Write the message you would post.",
    "W02": "A colleague missed something they promised, and you had to cover for them. Write the message you send them.",
    "W03": "Someone shares an idea in the team chat that you think is genuinely great. Reply.",
    "W04": "The team is picking a place for lunch and someone suggests somewhere you really do not like. Reply in the chat.",
}

SCENARIO_WORD_LIMIT = 60
WRITING_WORD_LIMIT = 80

BUILD_IDS = frozenset(ITEMS) | {"S01", "S03", "S05", "W01", "W03"}
DEVELOPMENT_TEST_IDS = frozenset({"S02", "S04", "S06", "W02", "W04"})

# ---------------------------------------------------------------------------
# What each BUILD scenario option signals (converter logic, identical for every person)
# ---------------------------------------------------------------------------
# Dimensions:
#   directness  how directly the person deals with a disagreement or grievance
#               3 = openly, in the group; 2 = directly, one-to-one with the person concerned;
#               1 = indirectly or through someone else; 0 = lets it pass or goes along
#   risk        how the person handles an uncertain decision (categorical)
#   autonomy    whether the person acts without the person in charge (categorical)
#   priority    what the person puts first when two goods conflict (categorical)

OPTION_SIGNALS: dict[str, dict[str, dict]] = {
    "S01": {
        "A": {"directness": 3, "summary": "raises a disagreement openly in the group, with reasons"},
        "B": {"directness": 2, "summary": "keeps the meeting smooth and raises the concern one-to-one with the decision-maker"},
        "C": {"directness": 0, "priority": "absorbs the cost personally (extra hours) rather than push back", "summary": "goes along and absorbs the cost personally"},
        "D": {"directness": 1, "summary": "signals the risk indirectly, without stating disagreement"},
    },
    "S03": {
        "A": {"risk": "takes the safe, reversible option first", "autonomy": "acts without waiting for the lead", "summary": "rolls back now and fixes later"},
        "B": {"risk": "takes a bounded, time-boxed risk with a fallback", "autonomy": "acts without waiting for the lead", "priority": "keeps what customers asked for if it can be done safely", "summary": "tries the fix with a one-hour limit before rolling back"},
        "C": {"autonomy": "waits for the person in charge before acting", "summary": "keeps trying to reach the lead first"},
        "D": {"risk": "gathers facts before deciding", "autonomy": "acts without waiting for the lead", "summary": "measures the impact first, then decides"},
    },
    "S05": {
        "A": {"directness": 3, "summary": "claims shared credit openly in the meeting"},
        "B": {"directness": 2, "summary": "raises it privately with the colleague"},
        "C": {"directness": 0, "priority": "puts the outcome ahead of personal credit", "summary": "lets it go because the idea moving forward matters more"},
        "D": {"directness": 1, "summary": "makes sure the manager knows, without confronting the colleague"},
    },
}

DIRECTNESS_LABELS = {
    3: "openly, in the group",
    2: "directly, one-to-one with the person concerned",
    1: "indirectly or through someone else",
    0: "lets it pass or goes along",
}
