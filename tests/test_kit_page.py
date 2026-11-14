# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_kit_page - the Take the kit page: kit data injected from kit.py, and a browser walk to the two answer files and the hub

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from mefile import app, kit, team
from mefile.answers import parse_answers

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
KIT_DATA = re.compile(r'<script id="kit-data" type="application/json">(.*?)</script>', re.S)


@pytest.fixture()
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "LEDGER_DIR", tmp_path / "consent")
    monkeypatch.setattr(team, "_LOGIN_FAILURES", {})
    monkeypatch.setenv("LUMIN8R_DATA", str(tmp_path / "data"))
    monkeypatch.setenv("MEFILE_PEOPLE_DIR", str(tmp_path / "people"))
    monkeypatch.setenv("MEFILE_QUESTIONS", str(EXAMPLES / "example_questions.json"))
    monkeypatch.setenv("LUMIN8R_WORKBENCH", "1")  # these tests drive the workbench (team API, paste station)
    for name in ("LUMIN8R_TEAM_CODE", "LUMIN8R_REQUIRE_TEAM_CODE", "LUMIN8R_TEAM_NAME", "LUMIN8R_FINAL_VARIANT",
                 "MEFILE_VARIANTS", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    http_server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{http_server.server_address[1]}"
    finally:
        http_server.shutdown()
        http_server.server_close()


def _get(url: str) -> tuple[int, str]:
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.status, response.read().decode("utf-8")


def test_kit_page_carries_the_kit_verbatim(server):
    status, html = _get(server + "/kit")
    assert status == 200
    assert app.KIT_DATA_TOKEN not in html
    data = json.loads(KIT_DATA.search(html).group(1))
    assert data["items"] == kit.ITEMS and len(data["items"]) == 50
    assert set(data["scenarios"]) == {"S01", "S02", "S03", "S04", "S05", "S06"}
    for scenario_id, scenario in kit.SCENARIOS.items():
        assert data["scenarios"][scenario_id]["options"] == scenario["options"]
        assert data["scenarios"][scenario_id]["wording"] == scenario["wording"]
    assert data["writing"] == kit.WRITING_PROMPTS
    assert data["response_labels"] == {str(k): v for k, v in kit.RESPONSE_LABELS.items()}
    assert data["scenario_word_limit"] == kit.SCENARIO_WORD_LIMIT == 60
    assert data["writing_word_limit"] == kit.WRITING_WORD_LIMIT == 80
    assert sorted(data["test_ids"]) == sorted(kit.DEVELOPMENT_TEST_IDS)


def test_home_links_to_the_kit(server):
    assert 'href="/kit"' in _get(server + "/")[1]


WALK = r"""
const { chromium } = require('playwright');
const fs = require('fs');
const [base, shots] = process.argv.slice(2);
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
  const page = await context.newPage();
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));
  const out = { errors };
  const shoot = async (name, full) => {
    await page.screenshot({ path: `${shots}/kit-${name}-1440.png`, fullPage: !!full });
    await page.setViewportSize({ width: 390, height: 844 });
    out['overflow_' + name] = await page.evaluate(() => document.documentElement.scrollWidth);
    await page.screenshot({ path: `${shots}/kit-${name}-390.png`, fullPage: !!full });
    await page.setViewportSize({ width: 1440, height: 900 });
  };
  const next = () => page.click('#next');

  await page.goto(base + '/kit');
  out.next_disabled_before_consent = await page.isDisabled('#next');
  await shoot('consent');
  await page.check('#agree');
  await next();
  await page.fill('#code', 'bad code!');
  await next();
  out.code_error = await page.textContent('#codeerr');
  await page.fill('#code', 'KIT01');
  await next();

  out.timer_before = await page.evaluate(() => JSON.parse(localStorage.getItem('lumin8r-kit-v1')).startedAt);
  await page.check('input[name=B01][value="4"]');
  await page.check('input[name=B02][value="2"]');
  await page.check('input[name=B03][value="5"]');
  await page.check('input[name=B04][value="skip"]');
  await shoot('items');
  await page.reload();
  out.kept_after_reload = await page.isChecked('input[name=B01][value="4"]');
  for (let i = 0; i < 5; i++) await next();

  const long = Array(70).fill('word').join(' ');
  for (const [id, choice] of [['S01', 'A'], ['S02', 'B'], ['S03', 'D'], ['S04', 'D'], ['S05', 'B'], ['S06', 'C']]) {
    await page.check(`input[name=${id}][value="${choice}"]`);
    await page.fill(`#x-${id}`, id === 'S06' ? long : `I would pick ${choice} because it fits how I work.`);
  }
  out.over_count = await page.textContent('#c-S06');
  out.over_flagged = await page.getAttribute('#c-S06', 'class');
  await shoot('scenarios');
  await next();
  for (const id of ['W01', 'W02', 'W03', 'W04']) await page.fill(`#w-${id}`, `Message for ${id}, in my usual style.`);
  await next();

  out.review_skipped = await page.$$eval('[data-goto]', (b) => b.map((x) => x.dataset.goto));
  out.review_flags = await page.$$eval('.flags li', (l) => l.map((x) => x.textContent));
  await shoot('review', true);
  await next();

  const grab = async (selector) => {
    const [download] = await Promise.all([page.waitForEvent('download'), page.click(selector)]);
    return { name: download.suggestedFilename(), json: JSON.parse(fs.readFileSync(await download.path(), 'utf8')) };
  };
  out.build = await grab('#dl-build');
  out.test = await grab('#dl-test');
  out.send_label = await page.textContent('#next');
  out.send_disabled_without_ai = await page.isDisabled('#next');
  out.send_hint_without_ai = await page.textContent('#nexthint');
  await page.check('#agreeAiDone');
  out.send_disabled_with_ai = await page.isDisabled('#next');
  await next();
  await page.waitForSelector('.result');
  out.send_result = await page.textContent('.result');
  await shoot('done', true);

  await page.click('#clear');
  await page.click('#wipe');
  out.after_clear_storage = await page.evaluate(() => localStorage.getItem('lumin8r-kit-v1'));
  out.after_clear_heading = await page.textContent('h1');
  await browser.close();
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
"""


def _playwright_env() -> dict | None:
    if not shutil.which("node"):
        return None
    env = dict(os.environ)
    env["NODE_PATH"] = os.pathsep.join(p for p in (env.get("NODE_PATH", ""), "/opt/node-tools/node_modules") if p)
    probe = subprocess.run(["node", "-e", "require('playwright')"], env=env, capture_output=True)
    return env if probe.returncode == 0 else None


def test_kit_walk_produces_both_files_and_saves_to_the_hub(server, tmp_path):
    env = _playwright_env()
    if env is None:
        pytest.skip("node with playwright is not available")
    shots = Path(os.environ.get("KIT_SCREENSHOT_DIR") or tmp_path)
    shots.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "walk.js"
    script.write_text(WALK, encoding="utf-8")
    run = subprocess.run(["node", str(script), server, str(shots)], env=env, capture_output=True, text=True, timeout=180)
    assert run.returncode == 0, run.stderr
    out = json.loads(run.stdout)

    assert out["errors"] == []
    assert out["next_disabled_before_consent"] is True
    assert out["code_error"].strip()
    assert out["timer_before"] is None
    assert out["kept_after_reload"] is True
    assert out["over_count"].startswith("71 / 60") and "over" in out["over_flagged"]  # 70 words + the choice
    assert all(width <= 390 for key, width in out.items() if key.startswith("overflow_")), out

    expected_skipped = [f"B{n:02d}" for n in range(4, 51)]
    assert out["review_skipped"] == expected_skipped
    assert any(flag.startswith("S06:") and "over" in flag for flag in out["review_flags"])

    build, test = out["build"], out["test"]
    assert (build["name"], test["name"]) == ("build.json", "test.json")
    build, test = build["json"], test["json"]
    for data in (build, test):
        assert data["person_id"] == "KIT01"
        assert isinstance(data["kit_minutes"], (int, float)) and data["kit_minutes"] >= 0
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", data["completed_at"])
        assert list(data)[:5] == ["person_id", "items", "scenarios", "writing", "skipped"]

    assert build["items"] == [{"id": "B01", "response": 4}, {"id": "B02", "response": 2}, {"id": "B03", "response": 5}]
    assert [s["id"] for s in build["scenarios"]] == ["S01", "S03", "S05"]
    assert [w["id"] for w in build["writing"]] == ["W01", "W03"]
    assert build["skipped"] == expected_skipped
    build_ids = {r["id"] for section in ("items", "scenarios", "writing") for r in build[section]} | set(build["skipped"])
    assert not build_ids & kit.DEVELOPMENT_TEST_IDS and build_ids <= kit.BUILD_IDS

    assert test["items"] == []
    assert [s["id"] for s in test["scenarios"]] == ["S02", "S04", "S06"]
    assert [w["id"] for w in test["writing"]] == ["W02", "W04"]
    assert test["skipped"] == []
    test_ids = {r["id"] for section in ("scenarios", "writing") for r in test[section]}
    assert test_ids == kit.DEVELOPMENT_TEST_IDS

    parsed_build, parsed_test = parse_answers(build), parse_answers(test)
    assert parsed_build.problems == [] and parsed_test.problems == []
    assert parsed_build.skipped == expected_skipped
    assert parsed_test.scenarios["S06"]["choice"] == "C"

    # the files download without AI consent; sending to the hub (the team's AI evaluation) needs it
    assert out["send_disabled_without_ai"] is True and "AI processing" in out["send_hint_without_ai"]
    assert out["send_disabled_with_ai"] is False
    assert "Saved to the team hub as KIT01" in out["send_result"]
    people = json.loads(_get(server + "/api/team/people")[1])["people"]
    saved = next(person for person in people if person["code"] == "KIT01")
    assert saved["has_build"] and saved["has_test"]

    assert out["after_clear_storage"] is None
    assert "Create your personal workplace profile" in out["after_clear_heading"]
