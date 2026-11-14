# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# intake - load a reviewed voice-interview transcript as cited evidence items (V01, V02, ...), text only

"""
Voice transcript as evidence (optional intake, Common Kit Section 11)
=====================================================================

The review app downloads the employee-reviewed transcript as ``voice_transcript.json``::

    {person_id, conversation_id, duration_seconds,
     employee_turns: [{index, seconds, text}], interviewer_turns: [{index, text}]}

``load_transcript`` turns it into evidence items the zero-LLM converter can quote and cite:

  - employee turns only, in file order; interviewer turns are used only to find the question;
  - IDs are positional, ``V01`` for the first employee turn, ``V02`` for the second, and so on,
    exactly as the review app numbered them while the person read and edited them. A turn the
    person emptied is dropped WITHOUT renumbering the rest, so a V ID always names the turn the
    person reviewed under that ID;
  - each item is tagged with the interview-guide question it answers: the nearest interviewer turn
    before it, matched to ``voice.INTERVIEW_GUIDE`` wording by shared content words. A short
    follow-up ("What did you do?") keeps the question it follows; anything else unmatched is
    ``other``.

Text only: nothing about tone, pace or emotion exists in this file, and nothing here infers it.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import voice

OTHER = "other"
MATCH_THRESHOLD = 0.5  # share of a guide question's content words the interviewer turn must contain

_STOPWORDS = frozenset(
    "a about an and are as at be can did do for give how i in is it me my of on or so that the this "
    "to was what when where which who why you your".split()
)
_FOLLOW_UP = re.compile(r"\bwhat (?:did you (?:do|say)|happened)\b")


def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOPWORDS}


_GUIDE_WORDS = [(key, _content_words(question)) for key, question in voice.INTERVIEW_GUIDE]
GUIDE_KEYS = tuple(key for key, _ in voice.INTERVIEW_GUIDE)
GUIDE_WORDING = dict(voice.INTERVIEW_GUIDE)


def match_guide_question(interviewer_text: str) -> str | None:
    """The guide key whose wording this interviewer turn carries, or None. Ties go to the earlier question."""
    said = _content_words(interviewer_text)
    best_key, best_score = None, 0.0
    for key, words in _GUIDE_WORDS:
        score = len(words & said) / len(words) if words else 0.0
        if score > best_score:
            best_key, best_score = key, score
    return best_key if best_score >= MATCH_THRESHOLD else None


@dataclass(frozen=True)
class VoiceItem:
    id: str  # V01, V02, ...
    question: str  # a voice.INTERVIEW_GUIDE key, or "other"
    text: str
    seconds: float | None = None


class VoiceEvidence(list):
    """A list of VoiceItem, carrying the transcript's metadata (person, conversation, duration)."""

    def __init__(self, items, person_id: str = "", conversation_id: str = "", duration_seconds: float | None = None):
        super().__init__(items)
        self.person_id = person_id
        self.conversation_id = conversation_id
        self.duration_seconds = duration_seconds

    def ids(self) -> frozenset[str]:
        return frozenset(item.id for item in self)

    def digest(self) -> str:
        canonical = json.dumps(
            {"person_id": self.person_id, "conversation_id": self.conversation_id,
             "items": [[i.id, i.question, i.text] for i in self]},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _index(record: dict[str, Any]) -> int | None:
    value = record.get("index")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def parse_transcript(data: dict[str, Any]) -> VoiceEvidence:
    interviewer = sorted(
        ((_index(t), str(t.get("text") or "")) for t in data.get("interviewer_turns") or [] if _index(t) is not None),
        key=lambda pair: pair[0],
    )
    items: list[VoiceItem] = []
    for position, turn in enumerate(data.get("employee_turns") or []):
        text = str(turn.get("text") or "").strip()
        if not text:
            continue  # emptied in review: dropped, and the IDs after it keep their numbers
        where = _index(turn)
        question = OTHER
        if where is not None:
            current = None  # the guide question in force at this point of the conversation
            for asked_at, asked in interviewer:
                if asked_at >= where:
                    break
                matched = match_guide_question(asked)
                if matched:
                    current = matched
                elif not (current and _FOLLOW_UP.search(asked.lower())):
                    current = None  # an unmatched turn that is not a follow-up starts something else
            question = current or OTHER
        seconds = turn.get("seconds")
        items.append(VoiceItem(
            id=f"V{position + 1:02d}",
            question=question,
            text=text,
            seconds=float(seconds) if isinstance(seconds, (int, float)) and not isinstance(seconds, bool) else None,
        ))
    duration = data.get("duration_seconds")
    return VoiceEvidence(
        items,
        person_id=str(data.get("person_id") or "").strip(),
        conversation_id=str(data.get("conversation_id") or "").strip(),
        duration_seconds=duration if isinstance(duration, (int, float)) and not isinstance(duration, bool) else None,
    )


def load_transcript(path: str | Path) -> VoiceEvidence:
    return parse_transcript(json.loads(Path(path).read_text(encoding="utf-8")))
