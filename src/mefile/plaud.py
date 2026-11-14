# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# plaud - read a Plaud transcript export (TXT or SRT) into speakers, then into the transcript JSON intake reads

"""
Plaud import (fallback for an in-person interview, Common Kit Section 11)
========================================================================

A Plaud recorder (or the Plaud CLI, ``plaud transcript <id> -o t.txt``) gives a speaker-labelled
transcript. This module reads it in two steps, statelessly:

  1. ``speakers(text)``: who spoke, how many turns each, and a short sample, so the employee can
     pick which speaker is them;
  2. ``to_transcript(text, speaker)``: the chosen speaker's turns become ``employee_turns`` and
     everyone else's become ``interviewer_turns`` (so ``intake`` can match guide questions), in the
     same JSON ``intake.parse_transcript`` reads, with ``source: "plaud"``.

Formats read (the first that matches wins, in this order):

  - SRT: numbered cues with ``00:00:01,000 --> 00:00:04,000`` timing, text with or without a
    ``Speaker N:`` / ``Name:`` prefix. A cue without a prefix continues the previous speaker; a file
    with no prefixes at all is one speaker, ``Unlabeled``.
  - TXT lines ``[mm:ss - mm:ss] Speaker N: text`` (hours allowed, renamed speakers allowed).
  - TXT blocks: a header line ``Speaker N [mm:ss]`` (or ``Sam (01:02)``, ``Speaker 2 00:01:02``),
    then the text lines.
  - TXT lines ``Sam: text`` with no timestamps.

Lines that match nothing continue the turn before them; lines before the first turn (a title, a
date) are ignored. Consecutive turns by the same speaker are merged into one. Text only: nothing
here reads audio, and nothing is stored or logged.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

MAX_TEXT_BYTES = 500 * 1024
SAMPLE_CHARACTERS = 120
UNLABELED = "Unlabeled"

FORMAT_HELP = ("expected a Plaud TXT export (lines like '[00:12 - 00:18] Speaker 1: ...') "
               "or an SRT export (numbered cues with '00:00:12,000 --> 00:00:18,000' timing)")


class PlaudFormatError(ValueError):
    """The text is not a Plaud transcript this module can read; the message says why, for the person."""


@dataclass(frozen=True)
class Turn:
    speaker: str
    text: str
    start: float | None = None
    end: float | None = None


_TIME = r"(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?"
_LABEL = r"[A-Za-z][\w .'\-]{0,39}?"
_SRT_TIMING = re.compile(rf"^\s*({_TIME})\s*-->\s*({_TIME})\s*$")
_BRACKET_LINE = re.compile(rf"^\s*\[\s*({_TIME})\s*(?:-\s*({_TIME})\s*)?\]\s*({_LABEL})\s*:\s*(.*)$")
_BLOCK_HEADER = re.compile(rf"^\s*({_LABEL})\s*(?:\[\s*({_TIME})\s*\]|\(\s*({_TIME})\s*\)|({_TIME}))\s*$")
_NAME_LINE = re.compile(rf"^\s*({_LABEL})\s*:\s+(\S.*)$")
_PREFIX = re.compile(rf"^\s*({_LABEL})\s*:\s*(.*)$")


def seconds(stamp: str) -> float:
    """'mm:ss', 'h:mm:ss' or either with ',mmm' / '.mmm' -> seconds."""
    whole, _, fraction = stamp.replace(",", ".").partition(".")
    total = 0
    for part in whole.split(":"):
        total = total * 60 + int(part)
    return total + (float("0." + fraction) if fraction else 0.0)


def _label(raw: str) -> str:
    return " ".join(raw.split())


def _plausible_label(raw: str) -> bool:
    """A speaker label: at most four words, so an ordinary sentence with a colon is not mistaken for one."""
    return len(raw.split()) <= 4 and not re.search(r"https?$", raw.strip(), re.IGNORECASE)


def _check_text(text) -> str:
    if not isinstance(text, str):
        raise PlaudFormatError("send the transcript as text")
    if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
        raise PlaudFormatError("the transcript is over 500 KB; export a single recording")
    head = text.lstrip()[:8]
    if head.startswith("PK") or head.startswith("%PDF") or "\x00" in text[:2000]:
        raise PlaudFormatError("this looks like a DOCX or PDF export; export the transcript from Plaud as TXT or SRT")
    if not text.strip():
        raise PlaudFormatError("the transcript is empty")
    return text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")


def _parse_srt(lines: list[str]) -> list[Turn]:
    turns: list[Turn] = []
    current_speaker = UNLABELED
    position = 0
    while position < len(lines):
        timing = _SRT_TIMING.match(lines[position])
        if not timing:
            position += 1
            continue
        start, end = seconds(timing.group(1)), seconds(timing.group(2))
        position += 1
        body: list[str] = []
        while position < len(lines) and lines[position].strip():
            if _SRT_TIMING.match(lines[position]):
                break
            body.append(lines[position].strip())
            position += 1
        if body and body[-1].isdigit() and position < len(lines) and _SRT_TIMING.match(lines[position]):
            body.pop()  # a cue number that lost its blank line
        text = " ".join(body).strip()
        prefix = _PREFIX.match(text)
        if prefix and _plausible_label(prefix.group(1)):
            current_speaker, text = _label(prefix.group(1)), prefix.group(2).strip()
        if text:
            turns.append(Turn(current_speaker, text, start, end))
    return turns


def _parse_lines(lines: list[str], header) -> list[Turn]:
    """Shared loop for the TXT shapes: ``header(line)`` returns (speaker, start, end, text) for a turn start, or None."""
    turns: list[dict] = []
    for line in lines:
        found = header(line)
        if found:
            speaker, start, end, text = found
            turns.append({"speaker": speaker, "start": start, "end": end, "text": [text] if text else []})
        elif turns and line.strip():
            turns[-1]["text"].append(line.strip())
    return [Turn(t["speaker"], " ".join(t["text"]).strip(), t["start"], t["end"]) for t in turns if " ".join(t["text"]).strip()]


def _bracket_header(line: str):
    match = _BRACKET_LINE.match(line)
    if not match or not _plausible_label(match.group(3)):
        return None
    end = seconds(match.group(2)) if match.group(2) else None
    return _label(match.group(3)), seconds(match.group(1)), end, match.group(4).strip()


def _block_header(line: str):
    match = _BLOCK_HEADER.match(line)
    if not match or not _plausible_label(match.group(1)):
        return None
    stamp = match.group(2) or match.group(3) or match.group(4)
    return _label(match.group(1)), seconds(stamp), None, ""


def _name_header(line: str):
    match = _NAME_LINE.match(line)
    if not match or not _plausible_label(match.group(1)):
        return None
    return _label(match.group(1)), None, None, match.group(2).strip()


def _merge(turns: list[Turn]) -> list[Turn]:
    merged: list[Turn] = []
    for turn in turns:
        if merged and merged[-1].speaker == turn.speaker:
            last = merged[-1]
            merged[-1] = Turn(last.speaker, f"{last.text} {turn.text}", last.start,
                              turn.end if turn.end is not None else (turn.start if turn.start is not None else last.end))
        else:
            merged.append(turn)
    return merged


def _fill_block_ends(turns: list[Turn]) -> list[Turn]:
    """Block headers carry a start only: each turn ends where the next one starts."""
    filled = []
    for position, turn in enumerate(turns):
        end = turn.end
        if end is None and position + 1 < len(turns):
            end = turns[position + 1].start
        filled.append(Turn(turn.speaker, turn.text, turn.start, end))
    return filled


def parse(text) -> list[Turn]:
    """The turns of a Plaud export, consecutive same-speaker turns merged; PlaudFormatError when none can be read."""
    lines = _check_text(text).split("\n")
    if any(_SRT_TIMING.match(line) for line in lines):
        turns = _parse_srt(lines)
    elif any(_bracket_header(line) for line in lines):
        turns = _parse_lines(lines, _bracket_header)
    elif any(_block_header(line) for line in lines):
        turns = _fill_block_ends(_parse_lines(lines, _block_header))
    else:
        turns = _parse_lines(lines, _name_header)
    if not turns:
        raise PlaudFormatError("could not find any speaker turns: " + FORMAT_HELP)
    return _merge(turns)


def _sample(texts: list[str]) -> str:
    chosen = next((t for t in texts if len(t.split()) >= 4), texts[0])
    return chosen if len(chosen) <= SAMPLE_CHARACTERS else chosen[:SAMPLE_CHARACTERS].rsplit(" ", 1)[0] + "..."


def speakers(text) -> list[dict]:
    """[{label, turns, sample}] in order of first appearance."""
    by_speaker: dict[str, list[str]] = {}
    for turn in parse(text):
        by_speaker.setdefault(turn.speaker, []).append(turn.text)
    return [{"label": label, "turns": len(texts), "sample": _sample(texts)} for label, texts in by_speaker.items()]


def _resolve_speaker(turns: list[Turn], speaker: str) -> str:
    labels = list(dict.fromkeys(t.speaker for t in turns))
    wanted = _label(str(speaker or ""))
    if wanted in labels:
        return wanted
    folded = [label for label in labels if label.casefold() == wanted.casefold()]
    if len(folded) == 1:
        return folded[0]
    raise PlaudFormatError(f"speaker {wanted!r} is not in this transcript; choose one of: {', '.join(labels)}")


def to_transcript(text, speaker: str, person_id: str = "") -> dict:
    """The transcript JSON intake.parse_transcript reads: the chosen speaker as the employee, everyone else as interviewer."""
    turns = parse(text)
    employee_label = _resolve_speaker(turns, speaker)
    employee, interviewer = [], []
    for index, turn in enumerate(turns):
        if turn.speaker == employee_label:
            employee.append({"index": index, "seconds": turn.start, "text": turn.text})
        else:
            interviewer.append({"index": index, "text": turn.text})
    stamps = [value for turn in turns for value in (turn.start, turn.end) if value is not None]
    duration = round(max(stamps) - min(stamps), 3) if stamps else None
    digest = hashlib.sha256(_check_text(text).encode("utf-8")).hexdigest()
    return {
        "source": "plaud",
        "person_id": str(person_id or "").strip(),
        "conversation_id": f"plaud-{digest[:16]}",
        "duration_seconds": duration,
        "employee_turns": employee,
        "interviewer_turns": interviewer,
    }
