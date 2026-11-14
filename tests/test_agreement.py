# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_agreement - the human-agreement kit: blind rating sheet, agreement statistics, null handling, CLI

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from mefile.judge import rubric
from mefile.judge.__main__ import main as judge_main
from mefile.judge.agreement import compare, compute_agreement, quadratic_weighted_kappa, spearman

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
SECRET_RUN_IDS = ["SECRET-OURS-S02-7", "WETHOS-TWIN-W02-3", "NOPROFILE-S04-1", "SECRET-OURS-W04-9"]


def _write(path: Path, data) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def responses_file(tmp_path):
    return _write(
        tmp_path / "team_private_responses.json",
        {
            "responses": [
                {"run_id": SECRET_RUN_IDS[0], "question_id": "S02", "text": "B. A short call sorts it out faster."},
                {"run_id": SECRET_RUN_IDS[1], "question_id": "W02", "text": "Hey, I covered the report. Warn me next time?"},
                {"run_id": SECRET_RUN_IDS[2], "question_id": "S04", "text": "A. Familiar is safer <b>always</b>."},
                {"run_id": SECRET_RUN_IDS[3], "question_id": "W04", "text": "Can we go somewhere else? Anywhere near work."},
                {"run_id": "NO-REFERENCE-RUN", "question_id": "S99", "text": "Unknown question."},
            ]
        },
    )


def _ratesheet(tmp_path, responses_file, seed=7):
    out = tmp_path / "sheet"
    code = judge_main([
        "ratesheet", "--responses", str(responses_file),
        "--questions", str(EXAMPLES / "example_questions.json"),
        "--reference", str(EXAMPLES / "example_test_answers.json"),
        "--out", str(out), "--seed", str(seed),
    ])
    assert code == 0
    return out


def test_perfect_agreement_gives_kappa_one():
    scores = [0, 1, 2, 3, 4, 2, 3]
    assert quadratic_weighted_kappa(scores, scores) == pytest.approx(1.0)
    assert spearman(scores, scores) == pytest.approx(1.0)


def test_reversed_scores_give_negative_kappa_and_correlation():
    first = [0, 1, 2, 3, 4]
    second = [4, 3, 2, 1, 0]
    assert quadratic_weighted_kappa(first, second) == pytest.approx(-1.0)
    assert spearman(first, second) == pytest.approx(-1.0)


def test_constant_rater_is_undefined_not_fabricated():
    assert spearman([2, 2, 2], [1, 2, 3]) is None
    assert quadratic_weighted_kappa([2, 2, 2], [2, 2, 2]) is None


def test_spearman_handles_ties():
    # average ranks: ties share a rank; a monotone relation with ties is still perfectly ranked
    assert spearman([1, 1, 2, 3], [0, 0, 3, 4]) == pytest.approx(1.0)


def test_nulls_and_missing_are_excluded_and_counted():
    items = ["i1", "i2", "i3", "i4", "i5"]
    first = {"i1": 4, "i2": None, "i3": 2, "i4": 1}
    second = {"i1": 4, "i2": 3, "i3": None, "i4": 2, "i5": 0}
    result = compare(first, second, items)
    assert result["n"] == 2
    assert result["excluded_null"] == 2
    assert result["excluded_missing"] == 1
    assert result["exact_agreement"] == 0.5
    assert result["within_one_agreement"] == 1.0
    assert result["mean_difference"] == -0.5


def test_ratesheet_is_blind_and_self_contained(tmp_path, responses_file):
    out = _ratesheet(tmp_path, responses_file)
    page = (out / "ratesheet.html").read_text(encoding="utf-8")
    key = json.loads((out / "key.json").read_text(encoding="utf-8"))

    for run_id in SECRET_RUN_IDS + ["NO-REFERENCE-RUN", "team_private_responses"]:
        assert run_id not in page
    assert "run_id" not in page
    # no external resources: works opened from disk
    assert not re.search(r"""(src|href)\s*=\s*["']?(https?:)?//""", page)
    assert "<link" not in page
    assert "@import" not in page
    # the judge's declared anchors are on the page
    for anchor in rubric.ANCHORS.values():
        assert anchor.split(":")[0] in page
    # response text is escaped, never live markup
    assert "<b>always</b>" not in page and "&lt;b&gt;always&lt;/b&gt;" in page
    # export via Blob, rater name field
    assert "new Blob(" in page and 'id="rater"' in page
    # key maps every rated item to its run, and skips the response with no recorded answer
    assert sorted(key.values()) == sorted(SECRET_RUN_IDS)
    assert all(item_id.startswith("item-") for item_id in key)
    assert all(f'data-item="{item_id}"' in page for item_id in key)


def test_ratesheet_shuffle_is_seeded(tmp_path, responses_file):
    first = json.loads((_ratesheet(tmp_path / "a", responses_file, seed=3) / "key.json").read_text())
    again = json.loads((_ratesheet(tmp_path / "b", responses_file, seed=3) / "key.json").read_text())
    assert first == again
    orders = {tuple(json.loads((_ratesheet(tmp_path / f"s{seed}", responses_file, seed=seed) / "key.json").read_text()).values()) for seed in range(8)}
    assert len(orders) > 1


def _evaluations(key: dict[str, str], ai_scores: dict[str, int | None], error_item: str | None = None) -> dict:
    evaluations = []
    for item_id, run_id in key.items():
        score = ai_scores.get(item_id)
        evaluation = {
            "run_id": run_id,
            "question_id": "Q",
            "status": "ok",
            "reference_resemblance": {"score": score, "insufficient_evidence": score is None, "explanation": f"judge says {item_id}", "evidence_ids": []},
        }
        if item_id == error_item:
            evaluation.update(status="judge_error", error="outage")
            evaluation["reference_resemblance"] = {"score": None, "insufficient_evidence": False, "explanation": "", "evidence_ids": []}
        evaluations.append(evaluation)
    return {"metadata": {}, "evaluations": evaluations}


def test_agreement_cli_end_to_end(tmp_path, responses_file, capsys):
    out = _ratesheet(tmp_path, responses_file)
    key = json.loads((out / "key.json").read_text(encoding="utf-8"))
    items = sorted(key)
    ai = dict(zip(items, [4, 3, 0, 2]))
    evaluations = _write(tmp_path / "evaluations.json", _evaluations(key, ai, error_item=items[3]))
    alice = _write(tmp_path / "alice.json", {"rater": "Alice", "ratings": [
        {"item_id": items[0], "score": 4, "note": "same call"},
        {"item_id": items[1], "score": 3, "note": ""},
        {"item_id": items[2], "score": 4, "note": "same choice really"},
        {"item_id": items[3], "score": None, "note": "cannot tell"},
        {"item_id": "item-999", "score": 2, "note": "not on the sheet"},
    ]})
    bob = _write(tmp_path / "bob.json", {"rater": "Bob", "ratings": [
        {"item_id": items[0], "score": 3, "note": ""},
        {"item_id": items[2], "score": 1, "note": ""},
    ]})
    code = judge_main(["agreement", "--key", str(out / "key.json"), "--ratings", str(alice), str(bob),
                       "--evaluations", str(evaluations), "--out", str(tmp_path / "agree")])
    assert code == 0
    result = json.loads((tmp_path / "agree" / "agreement.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "agree" / "agreement.md").read_text(encoding="utf-8")

    pairs = {(p["first"], p["second"]): p for p in result["pairs"]}
    alice_ai = pairs[("Alice", "AI judge")]
    assert alice_ai["n"] == 3 and alice_ai["excluded_null"] == 1 and alice_ai["excluded_missing"] == 0
    assert alice_ai["exact_agreement"] == pytest.approx(0.667, abs=0.001)
    bob_ai = pairs[("Bob", "AI judge")]
    assert bob_ai["n"] == 2 and bob_ai["excluded_missing"] == 2
    assert pairs[("Alice", "Bob")]["n"] == 2
    assert result["ai_judge"]["of_which_judge_error"] == 1
    assert result["raters"][0]["unknown_items_ignored"] == 1

    worst = result["largest_disagreements"]
    assert worst[0]["item_id"] == items[2] and worst[0]["gap"] == 4
    assert worst[0]["ai_explanation"] == f"judge says {items[2]}" and worst[0]["human_note"] == "same choice really"
    assert len(worst) <= 3
    assert "Largest disagreements" in markdown and "same choice really" in markdown


def test_compute_agreement_dedupes_rater_names():
    key = {"item-001": "r1", "item-002": "r2"}
    raters = [
        {"name": "Sam", "scores": {"item-001": 1, "item-002": 2}, "notes": {}, "unknown_items": []},
        {"name": "Sam", "scores": {"item-001": 1, "item-002": 3}, "notes": {}, "unknown_items": []},
    ]
    judge = {"name": "AI judge", "scores": {"item-001": 1, "item-002": 2}, "notes": {}, "judge_errors": 0, "by_run": {}}
    result = compute_agreement(key, raters, judge)
    assert [r["name"] for r in result["raters"]] == ["Sam", "Sam (2)"]


def test_out_of_scale_rating_is_rejected(tmp_path):
    key = _write(tmp_path / "key.json", {"item-001": "r1"})
    ratings = _write(tmp_path / "r.json", {"rater": "X", "ratings": [{"item_id": "item-001", "score": 7, "note": ""}]})
    evaluations = _write(tmp_path / "e.json", {"evaluations": []})
    with pytest.raises(ValueError, match="score 7"):
        judge_main(["agreement", "--key", str(key), "--ratings", str(ratings), "--evaluations", str(evaluations), "--out", str(tmp_path / "o")])
