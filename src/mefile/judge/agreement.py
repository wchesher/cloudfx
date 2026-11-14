# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# agreement - human-agreement kit: a blind rating sheet for people, and agreement statistics against the AI judge

"""
Checking the judge against people
=================================

Two steps, stdlib only.

1. ``ratesheet``: every response becomes an anonymous item (``item-001`` ...), shuffled with a seed,
   shown next to the question and the person's own recorded answer, with the judge's declared 0-4
   anchors (read from ``rubric.py``, so people and the model rate on the same scale). The page is
   one self-contained HTML file: no external resources, works opened from disk, exports the
   ratings as JSON through a Blob link. The item -> run_id key is written to a SEPARATE
   ``key.json``, so raters stay blind to which system wrote what.

2. ``agreement``: joins the key, each rater's export and the judge's ``evaluations.json``, and
   reports, for every pair (each human vs the AI judge, each human vs each other human): exact
   agreement, within-one agreement, Spearman rank correlation, quadratic-weighted Cohen's kappa,
   the mean difference and n. A pair where either side is null (insufficient evidence, or a judge
   error) is EXCLUDED and counted, never imputed. The three largest AI-vs-human disagreements are
   listed with both explanations, because where the judge fails is the point of the exercise.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import random
from itertools import combinations
from pathlib import Path
from typing import Any, Sequence

from ..answers import load_answers, load_questions, load_responses
from . import rubric
from .judge import reference_for, resolve_question

AI_JUDGE_NAME = "AI judge"
LARGEST_DISAGREEMENT_COUNT = 3
CATEGORIES = list(range(rubric.SCALE_MINIMUM, rubric.SCALE_MAXIMUM + 1))


# ---------------------------------------------------------------------------
# Rating sheet
# ---------------------------------------------------------------------------


def build_items(responses, questions, reference, seed: int) -> tuple[list[dict], dict[str, str], list[str]]:
    """Shuffle responses into anonymous items. Returns (items, key item_id -> run_id, skipped run_ids).

    A response whose question is unknown, or for which the person has no recorded answer, is skipped:
    the judge marks those insufficient evidence, so there is nothing for a person to compare against.
    """
    seen: set[str] = set()
    usable = []
    skipped = []
    for response in responses:
        if response.run_id in seen:
            raise ValueError(f"run_id {response.run_id} appears more than once; run IDs must be unique")
        seen.add(response.run_id)
        question = resolve_question(response.question_id, questions)
        recorded = reference_for(question, reference) if question is not None else None
        if question is None or recorded is None:
            skipped.append(response.run_id)
            continue
        usable.append((response, question, recorded))
    random.Random(seed).shuffle(usable)
    width = max(3, len(str(len(usable))))
    items: list[dict] = []
    key: dict[str, str] = {}
    for index, (response, question, recorded) in enumerate(usable, start=1):
        item_id = f"item-{index:0{width}d}"
        key[item_id] = response.run_id
        items.append(
            {
                "item_id": item_id,
                "question_type": question.type,
                "question_wording": question.wording,
                "question_options": dict(question.options or {}),
                "recorded": recorded,
                "response_text": response.text,
            }
        )
    return items, key, skipped


_PAGE_STYLE = """
:root { --ink:#1d1d24; --muted:#5d5d6b; --line:#d9d9e3; --paper:#ffffff; --panel:#f5f5fa; --accent:#1f5fbf; --pick:#e6efff; }
@media (prefers-color-scheme: dark) { :root { --ink:#ececf2; --muted:#a6a6b5; --line:#3a3a48; --paper:#15151b; --panel:#1f1f28; --accent:#79a8ff; --pick:#22324f; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--paper); color:var(--ink); font:16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 860px; margin: 0 auto; padding: 24px 16px 96px; }
h1 { font-size: 1.5rem; margin: 0 0 8px; }
h2 { font-size: 1.05rem; margin: 0; }
.muted { color: var(--muted); }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px 16px; margin: 16px 0; }
table.scale { border-collapse: collapse; width: 100%; }
table.scale td { border-top: 1px solid var(--line); padding: 6px 8px; vertical-align: top; }
table.scale td:first-child { font-weight: 700; width: 3em; }
label.rater { display: block; font-weight: 600; }
input[type=text] { font: inherit; padding: 6px 8px; width: 100%; max-width: 360px; border: 1px solid var(--line); border-radius: 6px; background: var(--paper); color: var(--ink); }
article { border: 1px solid var(--line); border-radius: 8px; padding: 16px; margin: 20px 0; }
article header { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; margin-bottom: 8px; }
.block { margin: 10px 0; }
.block .label { font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
.text { white-space: pre-wrap; background: var(--panel); border-left: 3px solid var(--line); padding: 8px 12px; border-radius: 4px; overflow-wrap: anywhere; }
.response { border-left-color: var(--accent); }
ol.options { margin: 4px 0; padding-left: 0; list-style: none; }
ol.options li.chosen { font-weight: 700; }
fieldset { border: 0; padding: 0; margin: 12px 0 0; }
fieldset label { display: flex; gap: 8px; padding: 4px 6px; border-radius: 6px; cursor: pointer; }
fieldset label:has(input:checked) { background: var(--pick); }
textarea { font: inherit; width: 100%; min-height: 3em; border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; background: var(--paper); color: var(--ink); }
.bar { position: fixed; left: 0; right: 0; bottom: 0; background: var(--panel); border-top: 1px solid var(--line); padding: 10px 16px; }
.bar div { max-width: 860px; margin: 0 auto; display: flex; gap: 12px; align-items: center; justify-content: space-between; flex-wrap: wrap; }
button { font: inherit; padding: 8px 16px; border-radius: 6px; border: 1px solid var(--accent); background: var(--accent); color: var(--paper); cursor: pointer; }
@media print { .bar { display: none; } article { break-inside: avoid; } }
"""

_PAGE_SCRIPT = """
(function () {
  var sheet = document.body.getAttribute('data-sheet');
  var storageKey = 'mefile-ratesheet-' + sheet;
  var raterInput = document.getElementById('rater');
  var progress = document.getElementById('progress');
  var articles = Array.prototype.slice.call(document.querySelectorAll('article[data-item]'));

  function collect() {
    var ratings = [];
    articles.forEach(function (article) {
      var picked = article.querySelector('input[type=radio]:checked');
      var note = article.querySelector('textarea').value.trim();
      if (!picked) { return; }
      ratings.push({
        item_id: article.getAttribute('data-item'),
        score: picked.value === 'null' ? null : parseInt(picked.value, 10),
        note: note
      });
    });
    return ratings;
  }
  function save() {
    progress.textContent = collect().length + ' of ' + articles.length + ' rated';
    try {
      var notes = {};
      articles.forEach(function (article) { notes[article.getAttribute('data-item')] = article.querySelector('textarea').value; });
      localStorage.setItem(storageKey, JSON.stringify({ rater: raterInput.value, ratings: collect(), notes: notes }));
    } catch (error) { /* storage unavailable: the page still works, export is the record */ }
  }
  function restore() {
    var saved = null;
    try { saved = JSON.parse(localStorage.getItem(storageKey) || 'null'); } catch (error) { saved = null; }
    if (!saved) { return; }
    raterInput.value = saved.rater || '';
    var notes = saved.notes || {};
    articles.forEach(function (article) {
      var id = article.getAttribute('data-item');
      if (typeof notes[id] === 'string') { article.querySelector('textarea').value = notes[id]; }
    });
    (saved.ratings || []).forEach(function (rating) {
      var article = document.querySelector('article[data-item="' + rating.item_id + '"]');
      if (!article) { return; }
      var value = rating.score === null ? 'null' : String(rating.score);
      var input = article.querySelector('input[type=radio][value="' + value + '"]');
      if (input) { input.checked = true; }
    });
  }
  function exportRatings() {
    var rater = raterInput.value.trim();
    if (!rater) { alert('Enter your name or initials first.'); raterInput.focus(); return; }
    var ratings = collect();
    var unrated = articles.length - ratings.length;
    if (unrated > 0 && !confirm(unrated + ' item(s) are not rated yet. Export anyway?')) { return; }
    var payload = { rater: rater, rubric_version: document.body.getAttribute('data-rubric'), ratings: ratings };
    // served from the team workspace: save straight to the server; opened from disk or refused: download instead
    if (location.protocol !== 'file:') {
      fetch('/api/team/ratings', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
        .then(function (r) { if (!r.ok) { throw new Error(String(r.status)); } return r.json(); })
        .then(function (b) { document.getElementById('progress').textContent = 'Saved to the team as ' + b.rater + ' (' + b.rated + ' rated). You can close this page.'; })
        .catch(function () { downloadRatings(payload, rater); });
      return;
    }
    downloadRatings(payload, rater);
  }
  function downloadRatings(payload, rater) {
    var blob = new Blob([JSON.stringify(payload, null, 2) + '\\n'], { type: 'application/json' });
    var link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'ratings-' + rater.replace(/[^A-Za-z0-9_-]+/g, '_') + '.json';
    document.body.appendChild(link);
    link.click();
    setTimeout(function () { URL.revokeObjectURL(link.href); link.remove(); }, 1000);
  }
  restore();
  save();
  document.addEventListener('input', save);
  document.addEventListener('change', save);
  document.getElementById('export').addEventListener('click', exportRatings);
})();
"""


def _escape(text: Any) -> str:
    return html.escape(str(text), quote=True)


def _scale_rows(anchors: dict[int, str]) -> str:
    return "".join(f"<tr><td>{score}</td><td>{_escape(text)}</td></tr>" for score, text in sorted(anchors.items(), reverse=True))


def _render_item(item: dict, position: int, total: int) -> str:
    item_id = item["item_id"]
    recorded = item["recorded"]
    parts = [f'<article data-item="{_escape(item_id)}">']
    parts.append(f'<header><h2>Item {position} of {total}</h2><span class="muted">{_escape(item_id)} - {_escape(item["question_type"])}</span></header>')
    parts.append(f'<div class="block"><div class="label">Question</div><div>{_escape(item["question_wording"])}</div>')
    if item["question_options"]:
        chosen = recorded.get("choice") if item["question_type"] == "scenario" else None
        options = "".join(
            f'<li{" class=chosen" if letter == chosen else ""}>{_escape(letter)}. {_escape(text)}</li>'
            for letter, text in item["question_options"].items()
        )
        parts.append(f'<ol class="options">{options}</ol>')
    parts.append("</div>")
    if item["question_type"] == "scenario":
        recorded_text = f"Chose {recorded.get('choice', '?')}. Reason: {recorded.get('explanation', '')}"
    else:
        recorded_text = recorded.get("text", "")
    parts.append(f'<div class="block"><div class="label">What the person actually answered</div><div class="text">{_escape(recorded_text)}</div></div>')
    parts.append(f'<div class="block"><div class="label">Response to rate</div><div class="text response">{_escape(item["response_text"])}</div></div>')
    name = f"score-{item_id}"
    radios = "".join(
        f'<label><input type="radio" name="{_escape(name)}" value="{score}"><span><strong>{score}</strong> {_escape(rubric.ANCHORS[score])}</span></label>'
        for score in sorted(rubric.ANCHORS, reverse=True)
    )
    radios += f'<label><input type="radio" name="{_escape(name)}" value="null"><span><strong>-</strong> Insufficient evidence to judge.</span></label>'
    parts.append(f"<fieldset><legend>Resemblance to what the person actually answered</legend>{radios}</fieldset>")
    parts.append(f'<div class="block"><div class="label">Why (one line)</div><textarea aria-label="Note for {_escape(item_id)}"></textarea></div>')
    parts.append("</article>")
    return "".join(parts)


def render_ratesheet(items: list[dict]) -> str:
    fingerprint = hashlib.sha256(json.dumps(items, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    total = len(items)
    body_items = "".join(_render_item(item, index, total) for index, item in enumerate(items, start=1))
    scenario_note = (
        f"For a scenario, the AI judge gives {rubric.SCENARIO_CHOICE_POINTS} points when the response picks the same "
        f"option as the person, plus 0-{rubric.SCENARIO_REASON_MAXIMUM} for the reason:"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Judge rating sheet</title>
<style>{_PAGE_STYLE}</style>
</head>
<body data-sheet="{fingerprint}" data-rubric="{_escape(rubric.RUBRIC_VERSION)}">
<main>
<h1>Rate how much each response resembles the person</h1>
<p class="muted">{total} items, shuffled. You are not told which system wrote a response. Rate resemblance to what the person actually answered, not quality.</p>
<div class="panel">
<label class="rater" for="rater">Your name or initials</label>
<input id="rater" type="text" autocomplete="off">
</div>
<div class="panel">
<h2>The scale (the AI judge uses the same anchors)</h2>
<table class="scale">{_scale_rows(rubric.ANCHORS)}<tr><td>-</td><td>Insufficient evidence to judge.</td></tr></table>
<p>{_escape(scenario_note)}</p>
<table class="scale">{_scale_rows(rubric.SCENARIO_REASON_ANCHORS)}</table>
<p>For a writing task, rate the whole message: content, tone and style together.</p>
<p><strong>Fairness:</strong> polish, formality and correct grammar must not raise a score; plain, informal or non-native English must not lower one.</p>
<p class="muted">Rate every response, then press Save to the team. If saving is not possible, the ratings download as a file to send back.</p>
</div>
{body_items}
</main>
<div class="bar"><div><span id="progress" class="muted"></span><button id="export" type="button">Save to the team</button></div></div>
<script>{_PAGE_SCRIPT}</script>
</body>
</html>
"""


def write_ratesheet(response_paths: Sequence[str | Path], questions_path, reference_path, out_dir, seed: int = 0) -> dict:
    responses = [r for path in response_paths for r in load_responses(path)]
    questions = load_questions(questions_path)
    reference = load_answers(reference_path)
    items, key, skipped = build_items(responses, questions, reference, seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sheet_path = out / "ratesheet.html"
    key_path = out / "key.json"
    sheet_path.write_text(render_ratesheet(items), encoding="utf-8")
    key_path.write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    return {"sheet": sheet_path, "key": key_path, "items": len(items), "skipped": skipped}


# ---------------------------------------------------------------------------
# Agreement statistics
# ---------------------------------------------------------------------------


def _ranks(values: Sequence[float]) -> list[float]:
    """Average ranks (1-based), ties sharing the mean of their positions."""
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while end + 1 < len(order) and values[order[end + 1]] == values[order[position]]:
            end += 1
        average = (position + end) / 2 + 1
        for index in order[position : end + 1]:
            ranks[index] = average
        position = end + 1
    return ranks


def _pearson(first: Sequence[float], second: Sequence[float]) -> float | None:
    count = len(first)
    if count < 2:
        return None
    mean_first = sum(first) / count
    mean_second = sum(second) / count
    covariance = sum((a - mean_first) * (b - mean_second) for a, b in zip(first, second))
    spread_first = math.sqrt(sum((a - mean_first) ** 2 for a in first))
    spread_second = math.sqrt(sum((b - mean_second) ** 2 for b in second))
    if spread_first == 0 or spread_second == 0:
        return None
    return covariance / (spread_first * spread_second)


def spearman(first: Sequence[float], second: Sequence[float]) -> float | None:
    """Spearman rank correlation (Pearson on average ranks). None when undefined (n < 2 or a constant rater)."""
    return _pearson(_ranks(first), _ranks(second))


def quadratic_weighted_kappa(first: Sequence[int], second: Sequence[int], categories: Sequence[int] = CATEGORIES) -> float | None:
    """Cohen's kappa with quadratic weights over a fixed category set. None when undefined (no expected disagreement)."""
    count = len(first)
    if count == 0:
        return None
    index = {category: position for position, category in enumerate(categories)}
    size = len(categories)
    observed = [[0.0] * size for _ in range(size)]
    for a, b in zip(first, second):
        observed[index[a]][index[b]] += 1
    first_marginal = [sum(row) for row in observed]
    second_marginal = [sum(observed[row][column] for row in range(size)) for column in range(size)]
    span = (size - 1) ** 2
    observed_disagreement = 0.0
    expected_disagreement = 0.0
    for row in range(size):
        for column in range(size):
            weight = (row - column) ** 2 / span
            observed_disagreement += weight * observed[row][column] / count
            expected_disagreement += weight * first_marginal[row] * second_marginal[column] / (count * count)
    if expected_disagreement == 0:
        return None
    return 1 - observed_disagreement / expected_disagreement


def compare(first_scores: dict[str, int | None], second_scores: dict[str, int | None], item_ids: Sequence[str]) -> dict:
    """Agreement between two raters over the key's items. Null on either side, or a missing rating, excludes the pair."""
    first_values: list[int] = []
    second_values: list[int] = []
    excluded_null = 0
    excluded_missing = 0
    for item_id in item_ids:
        if item_id not in first_scores or item_id not in second_scores:
            excluded_missing += 1
            continue
        a, b = first_scores[item_id], second_scores[item_id]
        if a is None or b is None:
            excluded_null += 1
            continue
        first_values.append(a)
        second_values.append(b)
    count = len(first_values)

    def rounded(value: float | None) -> float | None:
        return None if value is None else round(value, 3)

    return {
        "n": count,
        "excluded_null": excluded_null,
        "excluded_missing": excluded_missing,
        "exact_agreement": rounded(sum(a == b for a, b in zip(first_values, second_values)) / count) if count else None,
        "within_one_agreement": rounded(sum(abs(a - b) <= 1 for a, b in zip(first_values, second_values)) / count) if count else None,
        "spearman": rounded(spearman(first_values, second_values)),
        "weighted_kappa": rounded(quadratic_weighted_kappa(first_values, second_values)),
        "mean_difference": rounded(sum(a - b for a, b in zip(first_values, second_values)) / count) if count else None,
    }


def _valid_score(value: Any, where: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not rubric.SCALE_MINIMUM <= value <= rubric.SCALE_MAXIMUM:
        raise ValueError(f"{where}: score {value!r} is not null or a whole number from {rubric.SCALE_MINIMUM} to {rubric.SCALE_MAXIMUM}")
    return value


def load_key(path: str | Path) -> dict[str, str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
        raise ValueError(f"{path}: key must be a JSON object mapping item_id to run_id")
    return data


def load_ratings(path: str | Path, key: dict[str, str]) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rater = str(data.get("rater") or "").strip() or Path(path).stem
    scores: dict[str, int | None] = {}
    notes: dict[str, str] = {}
    unknown: list[str] = []
    for record in data.get("ratings") or []:
        item_id = str(record.get("item_id", ""))
        if item_id not in key:
            unknown.append(item_id)
            continue
        scores[item_id] = _valid_score(record.get("score"), f"{path} {item_id}")
        notes[item_id] = str(record.get("note") or "").strip()
    return {"name": rater, "scores": scores, "notes": notes, "unknown_items": unknown}


def load_judge_scores(evaluation_paths: Sequence[str | Path], key: dict[str, str]) -> dict:
    """The judge's reference_resemblance per item. judge_error and insufficient evidence are null."""
    by_run: dict[str, dict] = {}
    for path in evaluation_paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for evaluation in data.get("evaluations") or []:
            by_run[str(evaluation.get("run_id"))] = evaluation
    scores: dict[str, int | None] = {}
    notes: dict[str, str] = {}
    judge_errors = 0
    for item_id, run_id in key.items():
        evaluation = by_run.get(run_id)
        if evaluation is None:
            continue
        dimension = evaluation.get("reference_resemblance") or {}
        if evaluation.get("status") != "ok":
            judge_errors += 1
            scores[item_id] = None
            notes[item_id] = str(evaluation.get("error") or "judge error")
            continue
        scores[item_id] = None if dimension.get("insufficient_evidence") else _valid_score(dimension.get("score"), f"evaluation {run_id}")
        notes[item_id] = str(dimension.get("explanation") or "")
    return {"name": AI_JUDGE_NAME, "scores": scores, "notes": notes, "judge_errors": judge_errors, "by_run": by_run}


def _unique_names(raters: list[dict]) -> None:
    taken = {AI_JUDGE_NAME}
    for rater in raters:
        base = rater["name"]
        name = base
        suffix = 2
        while name in taken:
            name = f"{base} ({suffix})"
            suffix += 1
        rater["name"] = name
        taken.add(name)


def compute_agreement(key: dict[str, str], raters: list[dict], judge: dict) -> dict:
    item_ids = sorted(key)
    _unique_names(raters)
    pairs = []
    for rater in raters:
        pairs.append({"kind": "human_vs_ai", "first": rater["name"], "second": AI_JUDGE_NAME, **compare(rater["scores"], judge["scores"], item_ids)})
    for first, second in combinations(raters, 2):
        pairs.append({"kind": "human_vs_human", "first": first["name"], "second": second["name"], **compare(first["scores"], second["scores"], item_ids)})

    worst_per_item: dict[str, dict] = {}
    for rater in raters:
        for item_id in item_ids:
            human = rater["scores"].get(item_id)
            machine = judge["scores"].get(item_id)
            if human is None or machine is None:
                continue
            gap = abs(machine - human)
            if gap == 0:
                continue
            current = worst_per_item.get(item_id)
            if current is None or gap > current["gap"]:
                evaluation = judge["by_run"].get(key[item_id], {})
                worst_per_item[item_id] = {
                    "item_id": item_id,
                    "run_id": key[item_id],
                    "question_id": evaluation.get("question_id"),
                    "rater": rater["name"],
                    "human_score": human,
                    "ai_score": machine,
                    "gap": gap,
                    "human_note": rater["notes"].get(item_id, ""),
                    "ai_explanation": judge["notes"].get(item_id, ""),
                }
    largest = sorted(worst_per_item.values(), key=lambda row: (-row["gap"], row["item_id"]))[:LARGEST_DISAGREEMENT_COUNT]

    def null_count(scores: dict) -> int:
        return sum(1 for item_id in item_ids if item_id in scores and scores[item_id] is None)

    return {
        "rubric_version": rubric.RUBRIC_VERSION,
        "items_in_key": len(item_ids),
        "raters": [
            {
                "name": rater["name"],
                "scored": sum(1 for item_id in item_ids if rater["scores"].get(item_id) is not None),
                "insufficient_evidence": null_count(rater["scores"]),
                "not_rated": sum(1 for item_id in item_ids if item_id not in rater["scores"]),
                "unknown_items_ignored": len(rater["unknown_items"]),
            }
            for rater in raters
        ],
        "ai_judge": {
            "scored": sum(1 for item_id in item_ids if judge["scores"].get(item_id) is not None),
            "null": null_count(judge["scores"]),
            "of_which_judge_error": judge["judge_errors"],
            "not_in_evaluations": sum(1 for item_id in item_ids if item_id not in judge["scores"]),
        },
        "pairs": pairs,
        "largest_disagreements": largest,
    }


def _format(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:+.2f}" if value < 0 else f"{value:.2f}"
    return str(value)


def _quote(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "/") or "(none given)"


def render_agreement_markdown(result: dict) -> str:
    judge = result["ai_judge"]
    lines = [
        "# Judge versus people: agreement",
        "",
        f"Rubric `{result['rubric_version']}`. Items on the sheet: {result['items_in_key']}. "
        f"AI judge: {judge['scored']} scored, {judge['null']} null ({judge['of_which_judge_error']} judge errors), "
        f"{judge['not_in_evaluations']} not found in the evaluations.",
        "",
        "Raters scored blind: the sheet carried anonymous item IDs only. A pair where either side is null (insufficient "
        "evidence or judge error) or missing is excluded and counted, never filled in.",
        "",
        "| Rater | Scored | Insufficient evidence | Not rated |",
        "|---|---|---|---|",
    ]
    for rater in result["raters"]:
        lines.append(f"| {rater['name']} | {rater['scored']} | {rater['insufficient_evidence']} | {rater['not_rated']} |")
    lines += [
        "",
        "| Pair | n | Exact | Within 1 | Spearman | Weighted kappa | Mean difference (first - second) | Excluded: null | Excluded: missing |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for pair in result["pairs"]:
        lines.append(
            f"| {pair['first']} vs {pair['second']} | {pair['n']} | {_format(pair['exact_agreement'])} | "
            f"{_format(pair['within_one_agreement'])} | {_format(pair['spearman'])} | {_format(pair['weighted_kappa'])} | "
            f"{_format(pair['mean_difference'])} | {pair['excluded_null']} | {pair['excluded_missing']} |"
        )
    lines += [
        "",
        "Kappa is quadratic-weighted Cohen's kappa on the 0-4 scale (1 = perfect, 0 = chance, negative = worse than chance). "
        "A dash means undefined (for example a rater who gave every item the same score). A positive mean difference in a "
        "human-vs-AI row means the person scored higher than the judge. With n this small, read the counts, not the decimals.",
        "",
        "## Largest disagreements between the AI judge and a person",
        "",
    ]
    if not result["largest_disagreements"]:
        lines.append("None: on every item both scored, the judge and the people gave the same score.")
    for number, row in enumerate(result["largest_disagreements"], start=1):
        lines += [
            f"### {number}. {row['item_id']} ({row['question_id'] or 'unknown question'}, run {row['run_id']})",
            "",
            f"- AI judge: **{row['ai_score']}/4**. {_quote(row['ai_explanation'])}",
            f"- {row['rater']}: **{row['human_score']}/4**. {_quote(row['human_note'])}",
            "",
        ]
    return "\n".join(lines) + "\n"


def write_agreement(key_path, rating_paths: Sequence[str | Path], evaluation_paths: Sequence[str | Path], out_dir) -> dict:
    key = load_key(key_path)
    raters = [load_ratings(path, key) for path in rating_paths]
    judge = load_judge_scores(evaluation_paths, key)
    result = compute_agreement(key, raters, judge)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "agreement.json"
    markdown_path = out / "agreement.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_agreement_markdown(result), encoding="utf-8")
    return {"result": result, "json": json_path, "markdown": markdown_path}


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def ratesheet_command(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m mefile.judge ratesheet")
    parser.add_argument("--responses", required=True, nargs="+", help="one or more response files (run_id, question_id, text)")
    parser.add_argument("--questions", required=True, help="question file")
    parser.add_argument("--reference", required=True, help="the person's own answers to the test questions")
    parser.add_argument("--out", required=True, help="directory for ratesheet.html and key.json")
    parser.add_argument("--seed", type=int, default=0, help="shuffle seed (default 0)")
    args = parser.parse_args(list(argv))
    written = write_ratesheet(args.responses, args.questions, args.reference, args.out, args.seed)
    print(f"{written['items']} items; wrote {written['sheet']} (send to raters) and {written['key']} (keep; do not send)")
    if written["skipped"]:
        print(f"skipped {len(written['skipped'])} responses with no question text or no recorded answer: {', '.join(written['skipped'])}")
    return 0


def agreement_command(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m mefile.judge agreement")
    parser.add_argument("--key", required=True, help="key.json written by ratesheet")
    parser.add_argument("--ratings", required=True, nargs="+", help="ratings JSON exported from the sheet, one per rater")
    parser.add_argument("--evaluations", required=True, nargs="+", help="the judge's evaluations.json (one or more)")
    parser.add_argument("--out", required=True, help="directory for agreement.md and agreement.json")
    args = parser.parse_args(list(argv))
    written = write_agreement(args.key, args.ratings, args.evaluations, args.out)
    for pair in written["result"]["pairs"]:
        print(
            f"{pair['first']} vs {pair['second']}: n={pair['n']} exact={_format(pair['exact_agreement'])} "
            f"within1={_format(pair['within_one_agreement'])} spearman={_format(pair['spearman'])} "
            f"kappa={_format(pair['weighted_kappa'])} (excluded null {pair['excluded_null']}, missing {pair['excluded_missing']})"
        )
    print(f"wrote {written['markdown']} and {written['json']}")
    return 0
