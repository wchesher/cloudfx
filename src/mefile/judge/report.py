# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# report - write the judge's evaluations as evaluations.json and a readable evaluations.md

"""
Report writers. evaluations.json is the submission format (Common Kit Section 8: question ID,
run ID, score and declared scale or an insufficient-evidence indication, explanation, evidence
IDs). evaluations.md is the same content as a table a panel can read.
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
        "| Run | Question | Status | Resemblance to recorded answer | Profile consistency | Generic | Choice | Evidence | Explanation |",
        "|---|---|---|---|---|---|---|---|---|",
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
            f"{'yes' if generic else 'no' if generic is not None else '-'} | {choice} | "
            f"{', '.join(evidence)} | {_cell(explanation)} |"
        )
    md_path = out / "evaluations.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
