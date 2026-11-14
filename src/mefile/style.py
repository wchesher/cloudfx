# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# style - zero-LLM writing-style measurement: length, openers, contractions, punctuation, warmth and hedging markers

"""
Writing style, measured not judged
==================================

Pure functions over the person's own text. Nothing here rates quality, grammar or polish: a
profile must not reward formal English (problem statement, ethical requirements), so the features
are descriptive counts the model can imitate, not scores.

The same functions run in the judge, so "matches the person's style" is checked with the exact
measure the profile was built from.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

WORD = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?")
SENTENCE_END = re.compile(r"[.!?]+(?=\s|$)")
CONTRACTION = re.compile(r"\b[A-Za-z]+['’](?:s|re|ve|ll|d|m|t)\b", re.IGNORECASE)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")

GREETINGS = ("hi", "hey", "hello", "dear", "morning", "good morning", "hiya", "team", "all", "folks", "everyone")
WARMTH = ("thanks", "thank", "love", "great", "appreciate", "excellent", "glad", "happy", "awesome", "amazing", "brilliant", "nice")
HEDGES = ("maybe", "perhaps", "might", "i think", "i guess", "kind of", "sort of", "probably", "possibly", "could we", "would it")
APOLOGY = ("sorry", "apologize", "apologies", "unfortunately")
FIRST_PERSON = ("i", "i'm", "i've", "i'd", "i'll", "me", "my")
INCLUSIVE = ("we", "we're", "we've", "let's", "us", "our")


def words(text: str) -> list[str]:
    return WORD.findall(text)


def word_count(text: str) -> int:
    return len(words(text))


def _count_phrases(lower: str, phrases: tuple[str, ...]) -> int:
    return sum(len(re.findall(r"\b" + re.escape(p) + r"\b", lower)) for p in phrases)


@dataclass(frozen=True)
class StyleFeatures:
    words: int
    sentences: int
    words_per_sentence: float
    contractions: int
    opener: str  # first two words, as written
    greets: bool
    exclamations: int
    questions: int
    line_breaks: int
    emoji: int
    warmth_markers: int
    hedges: int
    apologies: int
    first_person: int
    inclusive_we: int
    ends_with_question: bool

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def measure(text: str) -> StyleFeatures:
    tokens = words(text)
    lower = text.lower().replace("’", "'")
    sentences = max(1, len(SENTENCE_END.findall(text))) if text.strip() else 0
    first_words = [t.lower() for t in tokens[:2]]
    opener = " ".join(tokens[:2])
    greets = bool(first_words) and (first_words[0] in GREETINGS or " ".join(first_words) in GREETINGS)
    return StyleFeatures(
        words=len(tokens),
        sentences=sentences,
        words_per_sentence=round(len(tokens) / sentences, 1) if sentences else 0.0,
        contractions=len(CONTRACTION.findall(text)),
        opener=opener,
        greets=greets,
        exclamations=text.count("!"),
        questions=text.count("?"),
        line_breaks=text.count("\n"),
        emoji=len(EMOJI.findall(text)),
        warmth_markers=_count_phrases(lower, WARMTH),
        hedges=_count_phrases(lower, HEDGES),
        apologies=_count_phrases(lower, APOLOGY),
        first_person=sum(1 for t in tokens if t.lower().replace("’", "'") in FIRST_PERSON),
        inclusive_we=sum(1 for t in tokens if t.lower().replace("’", "'") in INCLUSIVE),
        ends_with_question=text.rstrip().endswith("?"),
    )


def word_range(texts: list[str]) -> tuple[int, int]:
    counts = [word_count(t) for t in texts if t.strip()]
    return (min(counts), max(counts)) if counts else (0, 0)
