# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# features - deterministic, model-free features of a response: choice, length, style markers, typicality, style-fidelity flags

"""
Deterministic features
======================

Everything here is computed without a model, so it is reproducible and cannot be talked into a
score. The choice match decides half of a scenario's reference score; the rest are context the
judge model sees and evidence a human reviewer can check.

``typicality`` is a genericness PROXY, not a score: the mean token overlap of a response with the
other responses to the same question. A response that looks like everyone else's answer is more
likely to be generic model writing; a high value is a reason to look, not a verdict.

Style fidelity (``style_fidelity``) ports the teammates' DPM pipeline style rubric (P1-P4 plus the
memorization and baseline gates, ``contrib/dpm-pipeline/judge_prompt.txt``) into deterministic
checks. Every check is RELATIVE to the person: a phrase is flagged only when the person's own text
(build writing samples, build scenario explanations and their recorded answer) never uses it, and
politeness is flagged only as excess over the person's own rate. Every flag carries the exact span
of the response that triggered it; a check that cannot quote a span raises no flag.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

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
    reference_text: str | None = None,
    corpus: "PersonCorpus | None" = None,
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
    if corpus is not None:
        features["style_fidelity"] = style_fidelity(text, question_type, reference_text, corpus, peer_texts)
    if question_type == "scenario":
        choice = parse_choice(text)
        features["choice"] = choice
        features["reference_choice"] = reference_choice
        features["choice_match"] = (
            None if choice is None or reference_choice is None else choice == reference_choice
        )
    return features


# ---------------------------------------------------------------------------
# Style fidelity: P1-P4 and the memorization and baseline gates (relative to the person)
# ---------------------------------------------------------------------------

MEMORIZATION_MINIMUM_WORDS = 8
LENGTH_TOLERANCE = 0.4  # P4: more than 40% outside the person's own length range
BASELINE_MINIMUM_OVERLAP = 0.1  # below this the batch overlap is noise, not a pull toward the batch
POLITENESS_EXCESS_RATIO = 1.5  # P2: at least 50% above the person's own rate ...
POLITENESS_EXCESS_MINIMUM = 1.0  # ... and at least one whole marker more than that rate predicts
MAXIMUM_QUOTES_PER_CHECK = 3
STYLE_CODES = ("P1", "P2", "P3", "P4")
GATE_CODES = ("MEMORIZATION", "BASELINE")

FLAG_LABELS = {
    "P1": "assistant register",
    "P2": "politeness excess",
    "P3": "corporate lexicon or lost signature marker",
    "P4": "structural homogenization",
    "MEMORIZATION": "copied from the build answers",
    "BASELINE": "closer to the other responses than to the person",
}

# P1: service phrases a chat assistant writes and people rarely do (the teammates' list, extended).
ASSISTANT_REGISTER_PATTERNS: tuple[tuple[str, re.Pattern], ...] = tuple(
    (label, re.compile(pattern, re.IGNORECASE | re.MULTILINE))
    for label, pattern in (
        ("happy to help", r"\b(?:(?:I'd|I would) be |I'm |I am )?(?:happy|glad) to (?:help|assist)\b"),
        ("I hope this helps", r"\b(?:I )?hope (?:this|that) helps\b"),
        ("great question", r"\bgreat question\b"),
        ("let me know if you need anything else", r"\blet me know if (?:you (?:need|have|want|would like|'d like)|there(?:'s| is) anything)\b[^.!?\n]*"),
        ("feel free / don't hesitate", r"\b(?:feel free to|(?:do not|don't) hesitate to)\b[^.!?\n]*"),
        ("hope this finds you well", r"\bhope (?:this|the|my) (?:message |email |note )?finds you well\b"),
        ("unrequested offer", r"\b(?:if you(?:'d| would)? like|if (?:it|that) helps|if needed|if useful),? (?:I|we) (?:can|could|would be happy to)\b[^.!?\n]*"),
        ("standing offer", r"\b(?:I'm|I am) (?:here|available|around) (?:if|whenever|for|to help)\b[^.!?\n]*"),
        ("unrequested summary", r"\b(?:in summary|to summari[sz]e|to sum up|in conclusion|tl;?dr)\b[^.!?\n]*"),
        ("draft preamble", r"\bhere(?:'s| is) (?:a |the |my )?(?:draft|message|version|reply|response)\b[^.!?\n:]*"),
        ("eager opener", r"^\s*(?:certainly|absolutely|of course|sure thing)!"),
    )
)

# P3: corporate lexicon (the teammates' list, extended with inflections).
CORPORATE_PATTERNS: tuple[tuple[str, re.Pattern], ...] = tuple(
    (label, re.compile(pattern, re.IGNORECASE))
    for label, pattern in (
        ("leverage", r"\bleverag(?:e|es|ed|ing)\b"),
        ("align", r"\balign(?:s|ed|ing|ment)?\b"),
        ("circle back", r"\bcircl(?:e|es|ed|ing) back\b"),
        ("synergy", r"\bsynerg(?:y|ies|istic)\b"),
        ("bandwidth", r"\bbandwidth\b"),
        ("touch base", r"\btouch(?:ing|ed)? base\b"),
        ("deep dive", r"\bdeep[- ]dives?\b"),
        ("per my last", r"\bper my last\b"),
        ("moving forward", r"\b(?:moving|going) forward\b"),
        ("stakeholders", r"\bstakeholders?\b"),
        ("deliverable", r"\bdeliverables?\b"),
        ("action items", r"\baction items?\b"),
        ("low-hanging fruit", r"\blow[- ]hanging fruit\b"),
        ("take this offline", r"\btake (?:this|it) offline\b"),
    )
)

# P2: hedges, softeners, thanks and apologies. Longer alternatives first so "I just think" counts once.
POLITENESS_PATTERN = re.compile(
    r"\b(?:I (?:just )?(?:think|guess|feel like|was wondering|wonder(?:ed)?)"
    r"|would it be possible|if (?:possible|you don't mind|that's (?:ok|okay|alright))"
    r"|when you (?:get|have) a (?:chance|moment|minute)|no worries"
    r"|maybe|perhaps|possibly|probably|kind of|sort of|a bit|a little|just|please|kindly"
    r"|thank(?:s| you)|appreciat(?:e|ed|ion)|grateful|sorry|apologi[sz]e|apologies)\b",
    re.IGNORECASE,
)

# P3 lost signature marker: forms a person who contracts would usually contract.
EXPANDED_FORM_PATTERN = re.compile(
    r"\b(?:I am|I will|I would|do not|does not|did not|is not|are not|was not|were not|will not|would not|"
    r"should not|could not|have not|has not|had not|let us|we are|you are|they are|it is|that is)\b",
    re.IGNORECASE,
)
SIGN_OFF_PATTERN = re.compile(
    r"^\s*(?:thanks|thank you|many thanks|cheers|best|best regards|kind regards|warm regards|regards|sincerely|"
    r"talk soon|all the best|speak soon)\b[^\n]{0,30}$",
    re.IGNORECASE,
)
BULLET_LINE_PATTERN = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+\S.*$", re.MULTILINE)
HEADER_LINE_PATTERN = re.compile(r"^\s*(?:#{1,6}\s+\S.*|\*\*[^*\n]{1,60}\*\*:?\s*|[A-Z][^\n.!?]{0,40}:)\s*$", re.MULTILINE)
SENTENCE_SPAN_PATTERN = re.compile(r"[^.!?\n]+[.!?]*")


def _normalize(text: str) -> str:
    """Same length as the input (so match offsets index the original), curly apostrophes made straight."""
    return (text or "").replace("’", "'").replace("‘", "'")


def _flag(flags: list[dict], text: str, code: str, start: int, end: int, detail: str, **extra) -> None:
    """Append a flag only when it can quote a non-empty span of the response. No quote, no flag."""
    quote = (text or "")[start:end].strip()
    if not quote or quote not in text:
        return
    flags.append({"code": code, "quote": quote, "detail": detail, **extra})


@dataclass(frozen=True)
class PersonCorpus:
    """The person's own text from the build answers: writing samples and scenario explanations, by ID."""

    writing: Mapping[str, str] = field(default_factory=dict)
    explanations: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_answers(cls, build) -> "PersonCorpus":
        return cls(
            writing=dict(build.writing),
            explanations={sid: answer.get("explanation", "") for sid, answer in build.scenarios.items()},
        )

    def sources(self) -> dict[str, str]:
        """Everything a generating model was shown verbatim (the memorization gate's sources)."""
        return {**{k: v for k, v in self.explanations.items() if v}, **{k: v for k, v in self.writing.items() if v}}

    def samples(self, question_type: str, reference_text: str | None) -> list[str]:
        """The person's texts of the same kind as the item, recorded answer included when present."""
        own = list(self.writing.values()) if question_type == "writing" else list(self.explanations.values())
        if reference_text:
            own.append(reference_text)
        return [t for t in own if t and t.strip()]

    def all_text(self, reference_text: str | None) -> str:
        return _normalize("\n".join([*self.writing.values(), *self.explanations.values(), reference_text or ""]))


def assistant_register_flags(text: str, person_text: str) -> list[dict]:
    flags: list[dict] = []
    normalized = _normalize(text)
    for label, pattern in ASSISTANT_REGISTER_PATTERNS:
        if pattern.search(person_text):
            continue  # the person writes this way themselves: fidelity, not leakage
        for match in list(pattern.finditer(normalized))[:MAXIMUM_QUOTES_PER_CHECK]:
            _flag(flags, text, "P1", match.start(), match.end(), f"assistant-register phrase ({label}) the person's own text never uses")
    return flags


def politeness_markers(text: str) -> list[re.Match]:
    return list(POLITENESS_PATTERN.finditer(_normalize(text)))


def politeness_flags(text: str, person_samples: Sequence[str]) -> tuple[list[dict], dict]:
    """P2: hedges, softeners, thanks and apologies flagged only as EXCESS over the person's own rate."""
    markers = politeness_markers(text)
    response_words = word_count(text)
    person_words = sum(word_count(s) for s in person_samples)
    person_markers = sum(len(politeness_markers(s)) for s in person_samples)
    info: dict = {
        "response_markers": len(markers),
        "response_per_100_words": round(100 * len(markers) / response_words, 1) if response_words else 0.0,
        "person_per_100_words": round(100 * person_markers / person_words, 1) if person_words else None,
        "excess_markers": None,
    }
    if not person_words or not response_words:
        return [], info  # no basis for a relative judgment: never flag in absolute terms
    expected = person_markers * response_words / person_words
    excess = len(markers) - expected
    info["excess_markers"] = round(excess, 2)
    flags: list[dict] = []
    if excess >= POLITENESS_EXCESS_MINIMUM and len(markers) > POLITENESS_EXCESS_RATIO * expected:
        detail = (
            f"politeness {info['response_per_100_words']} per 100 words vs the person's own "
            f"{info['person_per_100_words']}; {len(markers)} markers where the person's rate predicts {expected:.1f}"
        )
        for match in markers[:MAXIMUM_QUOTES_PER_CHECK]:
            _flag(flags, text, "P2", match.start(), match.end(), detail)
    return flags, info


def corporate_flags(text: str, person_text: str) -> list[dict]:
    flags: list[dict] = []
    normalized = _normalize(text)
    for label, pattern in CORPORATE_PATTERNS:
        if pattern.search(person_text):
            continue
        for match in list(pattern.finditer(normalized))[:MAXIMUM_QUOTES_PER_CHECK]:
            _flag(flags, text, "P3", match.start(), match.end(), f"corporate lexicon ({label}) the person's own text never uses")
    return flags


def _opens_with_greeting(text: str) -> bool:
    tokens = words(text)
    return bool(tokens) and tokens[0].lower() in ("hi", "hey", "hello", "dear", "morning", "afternoon", "evening", "greetings")


def _closing(text: str) -> tuple[int, int] | None:
    """Span of the last line (or last sentence of a one-line text) when it is a sign-off."""
    stripped = (text or "").rstrip()
    lines = [m for m in re.finditer(r"[^\n]+", stripped) if m.group(0).strip()]
    if len(lines) > 1:
        candidates = [lines[-1]]
    else:
        candidates = list(SENTENCE_SPAN_PATTERN.finditer(stripped))[-1:]
    for match in candidates:
        if SIGN_OFF_PATTERN.match(match.group(0)):
            return match.start(), match.end()
    return None


def _edge_span(text: str, from_end: bool, count: int = 5) -> tuple[int, int]:
    spans = [m.span() for m in WORD_PATTERN.finditer(text or "")]
    if not spans:
        return 0, 0
    chosen = spans[-count:] if from_end else spans[:count]
    return chosen[0][0], chosen[-1][1]


def signature_flags(text: str, question_type: str, person_samples: Sequence[str]) -> list[dict]:
    """P3 lost signature markers: contractions, and greeting or sign-off habits the person always shows."""
    flags: list[dict] = []
    normalized = _normalize(text)
    person_contractions = sum(len(CONTRACTION_PATTERN.findall(_normalize(s))) for s in person_samples)
    if person_contractions and not CONTRACTION_PATTERN.search(normalized):
        for match in list(EXPANDED_FORM_PATTERN.finditer(normalized))[:MAXIMUM_QUOTES_PER_CHECK]:
            _flag(flags, text, "P3", match.start(), match.end(),
                  f"lost signature marker: the person contracts ({person_contractions} contractions in their own text); the response never does")
    if question_type != "writing" or len(person_samples) < 2:
        return flags
    if all(_opens_with_greeting(s) for s in person_samples) and not _opens_with_greeting(text):
        start, end = _edge_span(text, from_end=False)
        _flag(flags, text, "P3", start, end, f"lost signature marker: all {len(person_samples)} of the person's messages open with a greeting; this one does not")
    if all(_closing(s) for s in person_samples) and not _closing(text):
        start, end = _edge_span(text, from_end=True)
        _flag(flags, text, "P3", start, end, f"lost signature marker: all {len(person_samples)} of the person's messages end with a sign-off; this one does not")
    return flags


def _median(values: Sequence[int]) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    return float(ordered[middle]) if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def structure_flags(
    text: str,
    question_type: str,
    person_samples: Sequence[str],
    corpus_samples: Sequence[str],
    reference_text: str | None,
) -> tuple[list[dict], dict]:
    """P4 structural homogenization: bullets, headers, a greeting-body-closing template, length."""
    flags: list[dict] = []
    if not any(BULLET_LINE_PATTERN.search(s) for s in person_samples):
        for match in list(BULLET_LINE_PATTERN.finditer(text))[:MAXIMUM_QUOTES_PER_CHECK]:
            _flag(flags, text, "P4", match.start(), match.end(), "bullet list; the person's own messages never use bullets")
    if not any(HEADER_LINE_PATTERN.search(s) for s in person_samples):
        for match in list(HEADER_LINE_PATTERN.finditer(text))[:MAXIMUM_QUOTES_PER_CHECK]:
            _flag(flags, text, "P4", match.start(), match.end(), "header line; the person's own messages never use headers")
    if question_type == "writing" and len(person_samples) >= 2:
        greets = _opens_with_greeting(text)
        closing = _closing(text)
        if greets and closing and not any(_opens_with_greeting(s) and _closing(s) for s in person_samples):
            _flag(flags, text, "P4", closing[0], closing[1], "greeting-body-closing template; none of the person's messages uses it")
        elif greets and not any(_opens_with_greeting(s) for s in person_samples):
            first_line = re.match(r"[^\n,.!?]+[,.!?]?", text.lstrip())
            offset = len(text) - len(text.lstrip())
            if first_line:
                _flag(flags, text, "P4", offset + first_line.start(), offset + first_line.end(),
                      f"opens with a greeting; none of the person's {len(person_samples)} messages does")

    # Length against the person's own range: their answer to this question and the median of their samples.
    response_words = word_count(text)
    if question_type == "scenario" and parse_choice(text):
        response_words = max(0, response_words - 1)  # the leading choice letter is not part of the reason
    bounds = [word_count(reference_text)] if reference_text else []
    corpus_median = _median([word_count(s) for s in corpus_samples if s.strip()])
    if corpus_median:
        bounds.append(corpus_median)
    bounds = [b for b in bounds if b]
    info: dict = {"response_words": response_words, "person_range": [min(bounds), max(bounds)] if bounds else None}
    if bounds:
        low, high = min(bounds), max(bounds)
        spans = [m.span() for m in WORD_PATTERN.finditer(text)]
        if response_words > high * (1 + LENGTH_TOLERANCE) and spans:
            first_extra = min(len(spans) - 1, int(math.ceil(high)))
            last = min(len(spans) - 1, first_extra + 24)
            _flag(flags, text, "P4", spans[first_extra][0], spans[last][1],
                  f"length {response_words} words vs the person's {low:g}-{high:g}; quoted from the first word past the person's longest")
        elif response_words < low * (1 - LENGTH_TOLERANCE):
            _flag(flags, text, "P4", 0, len(text), f"length {response_words} words vs the person's {low:g}-{high:g}")
    return flags, info


def _word_spans(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0).lower(), m.start(), m.end()) for m in WORD_PATTERN.finditer(_normalize(text))]


def memorization_flags(text: str, sources: Mapping[str, str], minimum: int = MEMORIZATION_MINIMUM_WORDS) -> list[dict]:
    """Every maximal run of ``minimum``+ consecutive words the response shares with one source, quoted."""
    response = _word_spans(text)
    tokens = [w for w, _, _ in response]
    flags: list[dict] = []
    for source_id, source_text in sorted(sources.items()):
        source_tokens = [w for w, _, _ in _word_spans(source_text)]
        grams = {tuple(source_tokens[i : i + minimum]) for i in range(len(source_tokens) - minimum + 1)}
        if not grams:
            continue
        covered = [False] * len(tokens)
        for i in range(len(tokens) - minimum + 1):
            if tuple(tokens[i : i + minimum]) in grams:
                for j in range(i, i + minimum):
                    covered[j] = True
        i = 0
        while i < len(tokens):
            if not covered[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(tokens) and covered[j + 1]:
                j += 1
            _flag(flags, text, "MEMORIZATION", response[i][1], response[j][2],
                  f"{j - i + 1} consecutive words copied from build answer {source_id}", source_id=source_id)
            i = j + 1
    return flags


def centroid_overlap(text: str, peer_texts: Sequence[str]) -> float | None:
    """Weighted Jaccard of the response's content words with the batch centroid (each word weighted by
    the share of peers using it). With one peer it equals plain Jaccard, so it extends ``typicality``."""
    if not peer_texts:
        return None
    mine = content_tokens(text)
    weights: dict[str, float] = {}
    for other in peer_texts:
        for token in content_tokens(other):
            weights[token] = weights.get(token, 0.0) + 1 / len(peer_texts)
    numerator = sum(weights.get(t, 0.0) for t in mine)
    denominator = len(mine) + sum(w for t, w in weights.items() if t not in mine)
    return round(numerator / denominator, 3) if denominator else 0.0


def baseline_gate(text: str, reference_text: str | None, peer_texts: Sequence[str]) -> tuple[list[dict], dict]:
    """Flag a response that overlaps the batch centroid more than it overlaps the person's own answer."""
    batch = centroid_overlap(text, peer_texts)
    person = round(jaccard(content_tokens(text), content_tokens(reference_text)), 3) if reference_text else None
    info = {"centroid_overlap": batch, "reference_overlap": person}
    if batch is None or person is None or batch < BASELINE_MINIMUM_OVERLAP or batch <= person:
        return [], info
    batch_words = set().union(*(content_tokens(p) for p in peer_texts)) - content_tokens(reference_text)
    best: tuple[int, int, int] | None = None
    for match in SENTENCE_SPAN_PATTERN.finditer(text):
        shared = len(content_tokens(match.group(0)) & batch_words)
        if shared and (best is None or shared > best[0]):
            best = (shared, match.start(), match.end())
    flags: list[dict] = []
    if best:
        _flag(flags, text, "BASELINE", best[1], best[2],
              f"overlap with the other responses {batch} exceeds overlap with the person's answer {person}; quoted sentence shares the most batch words the person did not use")
    return flags, info


def style_fidelity(
    text: str,
    question_type: str,
    reference_text: str | None,
    corpus: PersonCorpus,
    peer_texts: Sequence[str] = (),
) -> dict:
    """All style-fidelity flags for one response, relative to the person, each with its quoted span."""
    person_text = corpus.all_text(reference_text)
    person_samples = corpus.samples(question_type, reference_text)
    corpus_samples = corpus.samples(question_type, None)
    politeness, politeness_info = politeness_flags(text, person_samples)
    structure, length_info = structure_flags(text, question_type, person_samples, corpus_samples, reference_text)
    memorized = memorization_flags(text, corpus.sources())
    baseline, baseline_info = baseline_gate(text, reference_text, peer_texts)
    flags = [
        *assistant_register_flags(text, person_text),
        *politeness,
        *corporate_flags(text, person_text),
        *signature_flags(text, question_type, person_samples),
        *structure,
        *memorized,
        *baseline,
    ]
    return {
        "flags": flags,
        "categories": sorted({f["code"] for f in flags if f["code"] in STYLE_CODES}),
        "gates": {"memorization": bool(memorized), "baseline": bool(baseline)},
        "politeness": politeness_info,
        "length": length_info,
        "baseline": baseline_info,
        "person_samples": len(person_samples),
    }
