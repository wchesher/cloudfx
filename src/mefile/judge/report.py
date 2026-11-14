# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# report - write the judge's evaluations as evaluations.json and a readable evaluations.md

"""
Report writers. evaluations.json is the submission format (Common Kit Section 8: question ID,
run ID, score and declared scale or an insufficient-evidence indication, explanation, evidence
IDs). evaluations.md is the same content as a table a panel can read, followed by a compact
per-response list of the style flags (each with its quoted span) and decision-card mismatches.
"""

from __future__ import annotations

import json
from pathlib import Path


def _score_text(dimension: dict) -> str:
    if dimension.get("insufficient_evidence"):
        return "insufficient evidence"
    score = dimension.get("score")
    return "n/a" if score is None else f"{score}/4"


def _cell(text: str, limit: int = 220) -> str:
    text = " ".join(str(text).split()).replace("|", "/")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _style_summary(evaluation: dict) -> str:
    """Compact flag codes with counts, for example "P1x2 P3 MEMORIZATION"; "-" when none."""
    style = (evaluation.get("features") or {}).get("style_fidelity") or {}
    counts: dict[str, int] = {}
    for flag in style.get("flags", []):
        counts[flag["code"]] = counts.get(flag["code"], 0) + 1
    return " ".join(f"{code}x{n}" if n > 1 else code for code, n in counts.items()) or "-"


def _detail_lines(evaluation: dict, quote_limit: int = 4) -> list[str]:
    """Quoted style flags, the decision-card comparison, and the fix hint, for one response."""
    lines: list[str] = []
    style = (evaluation.get("features") or {}).get("style_fidelity") or {}
    flags = style.get("flags", [])
    counted = {(f["code"], f["quote"]) for f in evaluation.get("style_flags", []) if f.get("counted")}
    if flags:
        shown = [
            f"{f['code']} \"{_cell(f['quote'], 80)}\"" + (" (counted)" if (f["code"], f["quote"]) in counted else "")
            for f in flags[:quote_limit]
        ]
        more = f" and {len(flags) - quote_limit} more" if len(flags) > quote_limit else ""
        lines.append("- Style flags: " + "; ".join(shown) + more)
    reference = evaluation.get("reference_resemblance") or {}
    if reference.get("caps_applied"):
        lines.append(f"- Capped at 2 by the {' and '.join(reference['caps_applied'])} gate")
    if reference.get("style_deduction"):
        lines.append(f"- Style deduction: {reference['style_deduction']} ({', '.join(reference.get('style_categories_counted', []))})")
    cards = evaluation.get("decision_cards")
    if cards and (cards["tradeoff_direction"] != "same" or cards["rationale_overlap"] != "most" or cards["mismatches"]):
        person, response = cards["person_card"], cards["response_card"]
        lines.append(
            f"- Decision cards: tradeoff {cards['tradeoff_direction']} "
            f"(person: {_cell(person['tradeoff'], 60)}; response: {_cell(response['tradeoff'], 60)}), "
            f"rationale overlap {cards['rationale_overlap']}"
            + (f"; {_cell('; '.join(cards['mismatches']), 160)}" if cards["mismatches"] else "")
        )
    if evaluation.get("rejected_style_flags"):
        lines.append(f"- {len(evaluation['rejected_style_flags'])} judge style flag(s) rejected (no exact quote, or the person uses the phrase)")
    for hint in evaluation.get("fix_hints", [])[:1]:
        lines.append(f"- Fix hint: {_cell(hint, 200)}")
    if evaluation.get("fix_hints_withheld"):
        lines.append(f"- {evaluation['fix_hints_withheld']} fix hint(s) withheld: they repeated the recorded test answer")
    return lines


def write_reports(result: dict, out_dir: str | Path) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "evaluations.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    metadata = result["metadata"]
    lines = [
        f"# AI judge evaluations: {metadata['person_id']}",
        "",
        f"Rubric: `{metadata['rubric_version']}`. Judge model requested: `{metadata['judge_model_requested']}`; "
        f"served: {', '.join(f'`{m}`' for m in metadata['judge_models_served']) or 'none'}.",
        "",
        f"**Scale.** {metadata['declared_scale']}",
        "",
        "The judge never saw run IDs or which system wrote a response.",
        "",
    ]
    for warning in metadata.get("warnings", []):
        lines.append(f"> Warning: {warning}")
    if metadata.get("warnings"):
        lines.append("")
    lines += [
        "| Run | Question | Status | Resemblance to recorded answer | Profile consistency | Generic | Choice | Style flags | Evidence | Explanation |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for evaluation in result["evaluations"]:
        reference = evaluation["reference_resemblance"]
        profile = evaluation["profile_consistency"]
        features = evaluation.get("features") or {}
        choice = ""
        if "choice" in features:
            choice = f"{features.get('choice') or '-'} vs {features.get('reference_choice') or '-'}"
        generic = evaluation["generic_writing"].get("is_generic")
        evidence = sorted(set(reference.get("evidence_ids", [])) | set(profile.get("evidence_ids", [])))
        explanation = evaluation.get("error") or reference.get("explanation", "")
        lines.append(
            f"| {evaluation['run_id']} | {evaluation['question_id']} | {evaluation['status']} | "
            f"{_score_text(reference)} | {_score_text(profile)} | "
            f"{'yes' if generic else 'no' if generic is not None else '-'} | {choice} | {_style_summary(evaluation)} | "
            f"{', '.join(evidence)} | {_cell(explanation)} |"
        )
    details = [(e, _detail_lines(e)) for e in result["evaluations"]]
    details = [(e, d) for e, d in details if d]
    if details:
        lines += [
            "",
            "## Style flags and decision cards",
            "",
            "Style flags are computed without a model and relative to the person (P1 assistant register, P2 politeness "
            "in excess of the person's own rate, P3 corporate lexicon or lost signature marker, P4 structure or length, "
            "MEMORIZATION and BASELINE gates). Each quotes the exact span that raised it; \"counted\" means the judge "
            "deducted for it.",
            "",
        ]
        for evaluation, detail in details:
            lines.append(f"**{evaluation['run_id']} / {evaluation['question_id']}**")
            lines += detail
            lines.append("")
    md_path = out / "evaluations.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
