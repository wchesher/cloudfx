# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# features - deterministic, model-free features of a response: choice, length, style markers, typicality

"""
Deterministic features
======================

Everything here is computed without a model, so it is reproducible and cannot be talked into a
score. The choice match decides half of a scenario's reference score; the rest are context the
judge model sees and evidence a human reviewer can check.

``typicality`` is a genericness PROXY, not a score: the mean token overlap of a response with the
other responses to the same question. A response that looks like everyone else's answer is more
likely to be generic model writing; a high value is a reason to look, not a verdict.
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence

CHOICE_PATTERN = re.compile(r"^\s*[\(\[\"'*]*\s*(?:option\s+|choice\s+|answer\s*:?\s*)?([ABCD])\b(?P<terminator>[\.\):,\-\*\]]|\s+(?P<next>\S)|$)", re.IGNORECASE)
CHOICE_FALLBACK_PATTERN = re.compile(r"\b(?:option|choice|choose|pick|go with)\s+([ABCD])\b(?:\s*(?:or|and|/)\s*([ABCD])\b)?", re.IGNORECASE)
WORD_PATTERN = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?")
CONTRACTION_PATTERN = re.compile(r"\b[A-Za-z]+['’](?:s|t|re|ve|ll|d|m)\b", re.IGNORECASE)
SENTENCE_SPLIT_PATTERN = re.compile(r"[.!?]+(?:\s+|$)")
GREETING_WORDS = ("hi", "hey", "hello", "dear", "morning", "afternoon", "evening", "team", "all", "folks", "everyone")

STOPWORDS = frozenset(
    """
    a an the and or but if so of to in on at by for with from as is are was were be been being it its
    this that these those i you he she we they me him her us them my your our their mine yours ours
    do does did doing have has had having will would can could should may might must shall not no
    just than then there here what which who whom when where why how all any each both few more most
    other some such only own same too very s t don about into over after before up down out off again
    further once
    """.split()
)


def parse_choice(text: str) -> str | None:
    """The scenario choice the response opens with (A-D), or None when it names no single option."""
    match = CHOICE_PATTERN.match(text or "")
    # "A short call..." opens with the article, not option A: a bare letter followed by a
    # space and a lowercase word is prose, not a choice.
    is_article = (
        match is not None
        and match.group(1) in ("A", "a")
        and match.group("next") is not None
        and match.group("next").islower()
    )
    if match and not is_article and match.group(1).isupper():
        return match.group(1).upper()
    fallback = {letter.upper() for pair in CHOICE_FALLBACK_PATTERN.findall(text or "") for letter in pair if letter}
    if len(fallback) == 1:
        return fallback.pop()
    return None


def words(text: str) -> list[str]:
    return WORD_PATTERN.findall(text or "")


def word_count(text: str) -> int:
    return len(words(text))


def content_tokens(text: str) -> set[str]:
    return {w.lower() for w in words(text) if w.lower() not in STOPWORDS and len(w) > 1}


def jaccard(first: set[str], second: set[str]) -> float:
    if not first and not second:
        return 0.0
    return len(first & second) / len(first | second)


def style_features(text: str) -> dict:
    text = text or ""
    tokens = words(text)
    sentences = [s for s in SENTENCE_SPLIT_PATTERN.split(text.strip()) if s.strip()]
    first_word = tokens[0].lower() if tokens else ""
    return {
        "words": len(tokens),
        "sentences": len(sentences),
        "mean_sentence_words": round(len(tokens) / len(sentences), 1) if sentences else 0.0,
        "contractions": len(CONTRACTION_PATTERN.findall(text)),
        "opens_with_greeting": first_word in GREETING_WORDS,
        "exclamations": text.count("!"),
        "questions": text.count("?"),
        "line_breaks": text.count("\n"),
    }


def typicality(text: str, others: Iterable[str]) -> float | None:
    """Mean Jaccard overlap of content words with the other responses to the same question."""
    mine = content_tokens(text)
    scores = [jaccard(mine, content_tokens(other)) for other in others]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 3)


def response_features(
    text: str,
    question_type: str,
    word_limit: int,
    reference_choice: str | None,
    peer_texts: Sequence[str],
) -> dict:
    count = word_count(text)
    features: dict = {
        "word_count": count,
        "word_limit": word_limit,
        "over_word_limit": count > word_limit,
        "style": style_features(text),
        "typicality": typicality(text, peer_texts),
        "peer_count": len(peer_texts),
    }
    if question_type == "scenario":
        choice = parse_choice(text)
        features["choice"] = choice
        features["reference_choice"] = reference_choice
        features["choice_match"] = (
            None if choice is None or reference_choice is None else choice == reference_choice
        )
    return features
