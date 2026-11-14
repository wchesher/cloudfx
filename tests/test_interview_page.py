# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_interview_page - Tell it in your own words (/interview): the shell and copy, the route, and the typed and Plaud
# paths walked in a real browser against the real server, through review, into Your file

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

from mefile import app, intake, voice

STATIC = Path(__file__).resolve().parents[1] / "src" / "mefile" / "static"
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕]")
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")
VOICE_KEY = "lumin8r-voice-v1"


def _playwright_env() -> dict | None:
    if not shutil.which("node"):
        return None
    env = dict(os.environ)
    env["NODE_PATH"] = os.pathsep.join(p for p in (env.get("NODE_PATH", ""), "/opt/node-tools/node_modules") if p)
    probe = subprocess.run(["node", "-e", "require('playwright')"], env=env, capture_output=True)
    return env if probe.returncode == 0 else None


@pytest.fixture()
def base_url(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "LEDGER_DIR", tmp_path / "consent")
    monkeypatch.setattr(app, "_CONSENTS", {})
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


# ---- static checks: the shell, the copy, the hard limits ----

def test_interview_page_shares_the_product_shell():
    html = (STATIC / "interview.html").read_text(encoding="utf-8")
    assert re.search(r"<title>[^<]+· lumin8r</title>", html)
    assert 'href="/static/mefile.css"' in html and 'class="skip-link" href="#main"' in html
    assert 'class="wordmark" href="/"' in html and 'src="/static/interview.js"' in html
    assert re.search(r'href="/app"><span class="long">Your file</span>', html)
    assert "Your understudy is Claude, an AI." in html
    local_css = "".join(re.findall(r"<style>(.*?)</style>", html, re.S)) + " ".join(re.findall(r'style="([^"]*)"', html))
    assert not HEX_COLOR.search(local_css), HEX_COLOR.findall(local_css)
    assert "rgb" not in local_css


def test_interview_copy_says_what_is_kept_and_who_processes_it():
    html = (STATIC / "interview.html").read_text(encoding="utf-8")
    script = (STATIC / "interview.js").read_text(encoding="utf-8")
    for fact in ("an AI interviewer", "ElevenLabs", "Recording is switched off", "deleted from ElevenLabs",
                 "stays in your Plaud account", "The text of your own answers", "About 10 minutes",
                 "Nothing about your tone of voice", "never copied", "plaud transcript &lt;id&gt; -o transcript.txt",
                 'value="build_profile"', 'value="voice_interview"'):
        assert fact in html, fact
    assert "https://cdn.jsdelivr.net/npm/@elevenlabs/client@1.32.0/dist/lib.iife.js" in script
    assert f'VOICE_KEY = "{VOICE_KEY}"' in script and "X-Consent-Token" in script
    for text in (html, script):
        assert not EMOJI.search(text)
        for word in ("twin", "kit", "player", "level", "score"):  # no game or internal words in front of a person
            assert not re.search(rf"\b{word}\b", text, re.I), word


def test_interview_route_serves_the_page(base_url):
    with urllib.request.urlopen(base_url + "/interview", timeout=10) as response:
        assert response.status == 200
        assert "Tell it in your own words" in response.read().decode("utf-8")
    with urllib.request.urlopen(base_url + "/static/interview.js", timeout=10) as response:
        assert response.headers["Content-Type"].startswith("text/javascript")


# ---- the browser walk: typed and Plaud, review, then Your file ----

PLAUD = "\n".join([
    f"[00:00 - 00:06] Speaker 1: {voice.INTERVIEW_GUIDE[0][1]}",
    "[00:07 - 00:30] Speaker 2: We disagreed on the release date. I asked for a short call and laid out the risks.",
    f"[00:31 - 00:35] Speaker 1: {voice.INTERVIEW_GUIDE[3][1]}",
    "[00:36 - 00:58] Speaker 2: A new intake form confused people, so I rolled it back and asked three users what they needed.",
])

WALK = r"""
const { chromium } = require('playwright');
const [base, shots, plaud] = process.argv.slice(2);
(async () => {
  const browser = await chromium.launch();
  const out = { pageErrors: [], requests: [], cases: {} };
  for (const width of [1280, 390]) {
    const ctx = await browser.newContext({ viewport: { width, height: width > 500 ? 900 : 844 }, deviceScaleFactor: 1, acceptDownloads: true });
    await ctx.route('https://fonts.googleapis.com/**', (r) => r.fulfill({ status: 200, contentType: 'text/css', body: '' }));
    const page = await ctx.newPage();
    page.on('pageerror', (e) => out.pageErrors.push(e.message));
    page.on('request', (r) => out.requests.push(r.url()));
    const c = out.cases[width] = { overflow: [] };
    const overflow = async () => c.overflow.push(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth));
    const shot = async (name) => { await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished))).catch(() => {});
      await page.screenshot({ path: `${shots}/interview-${name}-${width}.png`, fullPage: true }); };

    await page.goto(base + '/interview');
    await page.waitForSelector('#s-intro:not([hidden])');
    c.blockedAtStart = await page.isDisabled('#agreeBtn');
    await overflow(); await shot('intro');
    await page.fill('#pid', 'DEMO01'); await page.check('#c-build'); await page.check('#c-voice');
    await page.click('#agreeBtn');
    await page.waitForSelector('#s-choose:not([hidden])');
    c.talkChip = await page.textContent('#talkChip');
    await overflow(); await shot('choose');

    // typed: answer 7 of 8, skipping the third question
    await page.click('#pickType');
    await page.waitForSelector('#typeAnswer:not([disabled])');
    const total = await page.evaluate(() => Number(document.querySelector('#typeCount').textContent.match(/of (\d+)/)[1]));
    for (let i = 0; i < total; i++) {
      if (i === 2) { await page.click('#typeSkip'); continue; }
      await page.fill('#typeAnswer', `When it happened, I said what I saw and asked what they needed. Example ${i + 1}.`);
      if (i === 0) { await overflow(); await shot('type'); }
      await page.click('#typeNext');
    }
    await page.waitForSelector('#s-review:not([hidden])');
    c.typedIds = await page.$$eval('.turn .vid', (n) => n.map((x) => x.textContent));
    await page.click('.turn:nth-child(2) .btn.danger');          // remove V02: the others keep their numbers
    await page.fill('#turn-2', 'Edited in review.');
    await overflow(); await shot('review');
    await page.click('#reviewSave');
    await page.waitForSelector('#s-done:not([hidden])');
    c.typed = await page.evaluate((k) => JSON.parse(sessionStorage.getItem(k)), '""" + VOICE_KEY + r"""');
    const [download] = await Promise.all([page.waitForEvent('download'), page.click('#download')]);
    c.download = download.suggestedFilename();
    await overflow(); await shot('done');

    if (width === 1280) {
      // Your file reads the transcript from this tab, sends it as `voice`, and cites V IDs
      await page.click('#addToFile');
      await page.fill('#pid', 'DEMO01'); await page.check('#p-build'); await page.click('#agreeBtn');
      await page.waitForSelector('#example', { state: 'visible' }); await page.click('#example');
      await page.waitForFunction(() => [...document.querySelectorAll('.crail .ev-id')].some((x) => x.textContent[0] === 'V'), null, { timeout: 20000 });
      c.app = await page.evaluate(() => ({ line: document.querySelector('#voiceLine').innerText,
        invite: !document.querySelector('#interviewInvite').classList.contains('hidden'),
        cited: [...new Set([...document.querySelectorAll('.crail .ev-id')].map((x) => x.textContent).filter((t) => t[0] === 'V'))] }));
      await page.click('#voiceRemove');
      await page.waitForFunction(() => ![...document.querySelectorAll('.crail .ev-id')].some((x) => x.textContent[0] === 'V'), null, { timeout: 20000 });
      c.appAfterRemove = await page.evaluate((k) => ({ stored: sessionStorage.getItem(k),
        invite: !document.querySelector('#interviewInvite').classList.contains('hidden') }), '""" + VOICE_KEY + r"""');
      await page.goto(base + '/interview');
      await page.waitForSelector('#s-choose:not([hidden])');
    } else {
      await page.click('#startOver');
    }

    // Plaud: the real route finds the speakers, the person picks themselves
    await page.click('#pickPlaud');
    await page.fill('#plaudText', plaud);
    await page.click('#plaudRead');
    await page.waitForSelector('#plaudSpeakers:not([hidden])');
    c.speakers = await page.$$eval('#speakerList input', (n) => n.map((x) => x.value));
    await overflow(); await shot('plaud');
    await page.check('#speakerList input[value="Speaker 2"]');
    await page.click('#plaudUse');
    await page.waitForSelector('#s-review:not([hidden])');
    c.plaudAsked = await page.$$eval('.turn .asked', (n) => n.map((x) => x.textContent));
    await page.click('#reviewSave');
    await page.waitForSelector('#s-done:not([hidden])');
    c.plaud = await page.evaluate((k) => JSON.parse(sessionStorage.getItem(k)), '""" + VOICE_KEY + r"""');
    await ctx.close();
  }
  await browser.close();
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
"""


def test_interview_in_the_browser(base_url, tmp_path):
    env = _playwright_env()
    if env is None:
        pytest.skip("node with playwright is not available")
    shots = Path(os.environ.get("PRODUCT_SCREENSHOT_DIR") or tmp_path)
    shots.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "walk.js"
    script.write_text(WALK, encoding="utf-8")
    run = subprocess.run(["node", str(script), base_url, str(shots), PLAUD], env=env, capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr
    out = json.loads(run.stdout)
    assert out["pageErrors"] == []
    # nothing leaves for anywhere but this server and the font host (the voice client loads only when talking)
    assert all(url.startswith(base_url) or url.startswith("https://fonts.googleapis.com/") for url in out["requests"])

    guide = voice.INTERVIEW_GUIDE
    for width, case in out["cases"].items():
        assert all(o <= 0 for o in case["overflow"]), (width, case["overflow"])
        assert case["blockedAtStart"] is True
        assert case["talkChip"] == "Unavailable right now"  # no ElevenLabs key in tests
        assert case["typedIds"] == [f"V{i:02d}" for i in range(1, len(guide))]
        assert case["download"] == "voice_transcript.json"

        typed = case["typed"]
        assert typed["source"] == "typed" and typed["person_id"] == "DEMO01"
        assert isinstance(typed["duration_seconds"], int) and "minutes" in typed and "review_seconds" in typed
        assert [t["text"] for t in typed["interviewer_turns"]] == [q for i, (_, q) in enumerate(guide) if i != 2]
        indexes = sorted([t["index"] for t in typed["interviewer_turns"]] + [t["index"] for t in typed["employee_turns"]])
        assert indexes == list(range(len(indexes)))  # alternating question, answer
        evidence = intake.parse_transcript(typed)
        assert [item.id for item in evidence] == ["V01"] + [f"V{i:02d}" for i in range(3, len(guide))]  # V02 removed, not renumbered
        assert [item.question for item in evidence] == [key for i, (key, _) in enumerate(guide) if i not in (1, 2)]
        assert evidence[1].text == "Edited in review."

        assert case["speakers"] == ["Speaker 1", "Speaker 2"]
        assert case["plaudAsked"] == ["Answering: " + guide[0][1], "Answering: " + guide[3][1]]
        plaud = case["plaud"]
        assert plaud["source"] == "plaud" and plaud["person_id"] == "DEMO01"
        assert [(i.id, i.question) for i in intake.parse_transcript(plaud)] == [("V01", guide[0][0]), ("V02", guide[3][0])]

    desk = out["cases"]["1280"]
    assert desk["app"]["line"].startswith(f"Includes your interview ({len(guide) - 2} answers, typed)")
    assert desk["app"]["invite"] is False and desk["app"]["cited"] and set(desk["app"]["cited"]) <= {i.id for i in intake.parse_transcript(desk["typed"])}
    assert desk["appAfterRemove"] == {"stored": None, "invite": True}


# ---- workbench only: Send to the team hub (the hub's answers stubbed; never shown in the product) ----

HUB_WALK = r"""
const { chromium } = require('playwright');
const [base, shots] = process.argv.slice(2);
(async () => {
  const browser = await chromium.launch();
  const out = { pageErrors: [], sent: [] };
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
  await ctx.route('https://fonts.googleapis.com/**', (r) => r.fulfill({ status: 200, contentType: 'text/css', body: '' }));
  const replies = [
    [401, { error: 'team sign-in required' }],
    [400, { error: 'leakage guard refused the transcript', leakage_guard: { passed: false,
      test_ids_found: [{ turn: 'employee turn V02', test_id: 'S02' }], quotes_found: [{ turn: 'employee turn V03', test_answer: 'W04', shared_8_word_runs: 1 }] } }],
    [200, { saved: true, interview: { source: 'typed', interview_minutes: 1.5, employee_answers: 3, leakage_guard: 'passed' } }],
    [404, { error: 'not available' }],
  ];
  await ctx.route('**/api/team/voice', (r) => { out.sent.push(JSON.parse(r.request().postData())); const [status, body] = replies[out.sent.length - 1];
    r.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) }); });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => out.pageErrors.push(e.message));
  const finish = async () => {
    await page.click('#pickType'); await page.waitForSelector('#typeAnswer:not([disabled])');
    for (let i = 0; i < 3; i++) { await page.fill('#typeAnswer', 'An example answer ' + i); await page.click('#typeNext'); }
    while (await page.isVisible('#s-type')) await page.click('#typeSkip');
    await page.click('#reviewSave'); await page.waitForSelector('#s-done:not([hidden])');
  };
  // product mode first: the button is never there
  await page.goto(base + '/interview');
  await page.fill('#pid', 'DEMO01'); await page.check('#c-build'); await page.click('#agreeBtn');
  await page.waitForSelector('#s-choose:not([hidden])');
  await finish();
  out.productHidden = await page.isHidden('#hubBox');
  // workbench mode
  await ctx.route('**/api/config', async (r) => { const j = await (await r.fetch()).json(); j.workbench_enabled = true;
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(j) }); });
  await page.goto(base + '/interview');
  await page.waitForSelector('#s-done:not([hidden])');
  out.workbenchShown = await page.isVisible('#hubSend');
  await page.click('#hubSend'); await page.waitForSelector('#hubStatus .notice');
  out.signIn = await page.textContent('#hubStatus'); out.signInLink = await page.getAttribute('#hubStatus a', 'href');
  await page.click('#hubSend'); await page.waitForSelector('#hubStatus li');
  out.leaks = await page.$$eval('#hubStatus li', (n) => n.map((x) => x.textContent));
  await page.screenshot({ path: `${shots}/interview-hub-leak-1280.png`, fullPage: true });
  await page.click('#hubStatus li button');
  out.jumpedTo = await page.evaluate(() => document.activeElement.id);
  await page.click('#reviewSave'); await page.waitForSelector('#s-done:not([hidden])');
  await page.click('#hubSend'); await page.waitForSelector('#hubStatus .notice.ok');
  out.saved = await page.textContent('#hubStatus');
  await page.click('#hubSend'); await page.waitForSelector('#hubBox', { state: 'hidden' });
  out.hiddenAfter404 = await page.isHidden('#hubBox');
  await browser.close();
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
"""


def test_send_to_the_team_hub_only_in_the_workbench(base_url, tmp_path):
    env = _playwright_env()
    if env is None:
        pytest.skip("node with playwright is not available")
    shots = Path(os.environ.get("PRODUCT_SCREENSHOT_DIR") or tmp_path)
    shots.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "hub.js"
    script.write_text(HUB_WALK, encoding="utf-8")
    run = subprocess.run(["node", str(script), base_url, str(shots)], env=env, capture_output=True, text=True, timeout=180)
    assert run.returncode == 0, run.stderr
    out = json.loads(run.stdout)
    assert out["pageErrors"] == []
    assert out["productHidden"] is True and out["workbenchShown"] is True
    assert "Sign in to the team hub first." in out["signIn"] and out["signInLink"] == "/workbench"
    assert out["leaks"][0].startswith("V02 names the held-out test question S02")
    assert out["leaks"][1].startswith("V03 repeats words from the held-out test answer W04")
    assert out["jumpedTo"] == "turn-1"
    assert "Sent to the team hub: 3 answers, 1.5 minutes, typed. The leakage check passed." in out["saved"]
    assert out["hiddenAfter404"] is True
    first = out["sent"][0]
    assert first["code"] == "DEMO01" and first["transcript"]["source"] == "typed" and first["transcript"]["employee_turns"]
