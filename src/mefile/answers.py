# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# answers - load and check the organizer file formats: answer files, question files, comparison response files

"""
The organizer file formats (Common Kit Section 7 and the 00-examples folder), read exactly as
shipped: field names are never renamed, and question IDs are kept unchanged.

Loading never silently repairs. Anything odd (an unknown ID, a response outside 1-5, a choice
outside A-D, an ID that is both answered and skipped) is returned as a ``problems`` list so the
app can show it to the person and the converter can refuse to cite a bad record.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import kit


@dataclass
class Answers:
    person_id: str
    items: dict[str, int] = field(default_factory=dict)
    scenarios: dict[str, dict[str, str]] = field(default_factory=dict)  # id -> {choice, explanation}
    writing: dict[str, str] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def answered_ids(self) -> set[str]:
        return set(self.items) | set(self.scenarios) | set(self.writing)

    def to_json(self) -> dict[str, Any]:
        """Back to the organizer format, so a corrected file can be saved and reloaded."""
        return {
            "person_id": self.person_id,
            "items": [{"id": k, "response": v} for k, v in sorted(self.items.items())],
            "scenarios": [
                {"id": k, "choice": v["choice"], "explanation": v["explanation"]}
                for k, v in sorted(self.scenarios.items())
            ],
            "writing": [{"id": k, "text": v} for k, v in sorted(self.writing.items())],
            "skipped": sorted(self.skipped),
        }


def parse_answers(data: dict[str, Any]) -> Answers:
    problems: list[str] = []
    person_id = str(data.get("person_id") or "").strip()
    if not person_id:
        problems.append("person_id is missing")
        person_id = "UNKNOWN"

    items: dict[str, int] = {}
    for rec in data.get("items") or []:
        item_id = str(rec.get("id", "")).strip()
        response = rec.get("response")
        if item_id not in kit.ITEMS:
            problems.append(f"{item_id or '?'}: not an inventory item ID; ignored")
            continue
        if not isinstance(response, int) or isinstance(response, bool) or not 1 <= response <= 5:
            problems.append(f"{item_id}: response {response!r} is not a whole number from 1 to 5; treated as skipped")
            continue
        if item_id in items:
            problems.append(f"{item_id}: answered twice; the first answer is kept")
            continue
        items[item_id] = response

    scenarios: dict[str, dict[str, str]] = {}
    for rec in data.get("scenarios") or []:
        sid = str(rec.get("id", "")).strip()
        choice = str(rec.get("choice", "")).strip().upper()
        explanation = str(rec.get("explanation") or "").strip()
        if not sid:
            problems.append("a scenario record has no id; ignored")
            continue
        if choice not in ("A", "B", "C", "D"):
            problems.append(f"{sid}: choice {choice!r} is not A, B, C or D; treated as skipped")
            continue
        scenarios[sid] = {"choice": choice, "explanation": explanation}

    writing: dict[str, str] = {}
    for rec in data.get("writing") or []:
        wid = str(rec.get("id", "")).strip()
        text = str(rec.get("text") or "")
        if not wid:
            problems.append("a writing record has no id; ignored")
            continue
        if not text.strip():
            problems.append(f"{wid}: empty message; treated as skipped")
            continue
        writing[wid] = text

    skipped = [str(s).strip() for s in data.get("skipped") or [] if str(s).strip()]
    answered = set(items) | set(scenarios) | set(writing)
    for sid in skipped:
        if sid in answered:
            problems.append(f"{sid}: listed as skipped but also answered; the answer is used")
    skipped = [s for s in skipped if s not in answered]

    return Answers(person_id, items, scenarios, writing, skipped, problems)


def load_answers(path: str | Path) -> Answers:
    return parse_answers(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(frozen=True)
class Question:
    id: str
    type: str  # "scenario" | "writing"
    wording: str
    options: dict[str, str] | None
    word_limit: int
    prompt: str


def parse_questions(data: dict[str, Any]) -> dict[str, Question]:
    out: dict[str, Question] = {}
    for rec in data.get("questions") or []:
        qtype = str(rec.get("type", "")).strip().lower()
        options = rec.get("options")
        word_limit = rec.get("word_limit")
        if not isinstance(word_limit, int):
            word_limit = kit.SCENARIO_WORD_LIMIT if qtype == "scenario" else kit.WRITING_WORD_LIMIT
        out[str(rec["id"])] = Question(
            id=str(rec["id"]),
            type=qtype,
            wording=str(rec.get("wording", "")),
            options=dict(options) if isinstance(options, dict) else None,
            word_limit=word_limit,
            prompt=str(rec.get("prompt", "")),
        )
    return out


def load_questions(path: str | Path) -> dict[str, Question]:
    return parse_questions(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(frozen=True)
class Response:
    run_id: str
    question_id: str
    text: str


def parse_responses(data: dict[str, Any]) -> list[Response]:
    return [
        Response(str(r["run_id"]), str(r["question_id"]), str(r.get("text", "")))
        for r in data.get("responses") or []
    ]


def load_responses(path: str | Path) -> list[Response]:
    return parse_responses(json.loads(Path(path).read_text(encoding="utf-8")))
