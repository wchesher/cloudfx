# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_product_pages - the shared-profile page (decrypts in the browser), Privacy and Responsible use, walked in a real browser

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from mefile import converter
from mefile.answers import parse_answers

STATIC = Path(__file__).resolve().parents[1] / "src" / "mefile" / "static"
EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
PAGES = {"share": "share.html", "privacy": "privacy.html", "responsible-use": "responsible-use.html"}

LIVE_ID = "LiveShare0123456789abc"
HOSTILE_ID = "HostileShare0123456789"
REVOKED_ID = "RevokedShare0123456789"
UNKNOWN_ID = "UnknownShare0123456789"

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕]")
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _playwright_env() -> dict | None:
    if not shutil.which("node"):
        return None
    env = dict(os.environ)
    env["NODE_PATH"] = os.pathsep.join(p for p in (env.get("NODE_PATH", ""), "/opt/node-tools/node_modules") if p)
    probe = subprocess.run(["node", "-e", "require('playwright')"], env=env, capture_output=True)
    return env if probe.returncode == 0 else None


NODE_ENCRYPT = r"""
const crypto = require('crypto');
const [keyHex, ivHex] = process.argv.slice(1);
const chunks = [];
process.stdin.on('data', (c) => chunks.push(c));
process.stdin.on('end', () => {
  const cipher = crypto.createCipheriv('aes-256-gcm', Buffer.from(keyHex, 'hex'), Buffer.from(ivHex, 'hex'));
  const body = Buffer.concat([cipher.update(Buffer.concat(chunks)), cipher.final(), cipher.getAuthTag()]);
  process.stdout.write(body.toString('base64'));
});
"""


def _encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes | None:
    """AES-256-GCM, ciphertext || tag (the WebCrypto layout). cryptography if installed, else node's crypto."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        if not shutil.which("node"):
            return None
        run = subprocess.run(["node", "-e", NODE_ENCRYPT, key.hex(), iv.hex()], input=plaintext, capture_output=True, timeout=30)
        return base64.b64decode(run.stdout) if run.returncode == 0 else None
    return AESGCM(key).encrypt(iv, plaintext, None)


def _share_record(payload: dict, key: bytes, version: str, purpose: str, recipient: str) -> dict | None:
    iv = os.urandom(12)
    ciphertext = _encrypt(key, iv, json.dumps(payload).encode("utf-8"))
    if ciphertext is None:
        return None
    return {"ciphertext": _b64url(ciphertext), "iv": _b64url(iv), "version": version, "purpose": purpose,
            "recipient_label": recipient, "created_at": "2026-11-14T10:00:00Z", "expires_at": "2026-12-14T10:00:00Z"}


def _demo_payload() -> dict:
    answers = parse_answers(json.loads((EXAMPLES / "example_build_answers.json").read_text(encoding="utf-8")))
    profile = converter.convert(answers, scope="coaching")
    return {"person_id": answers.person_id, "version": "coaching", "generated": profile.sidecar["generated"],
            "markdown": profile.markdown, "sidecar": profile.sidecar}


HOSTILE_TEXT = '<img src=x onerror="window.pwned=1">'


def _hostile_payload() -> dict:
    return {"person_id": "<b>X1</b>", "version": "full", "generated": "2026-11-14",
            "markdown": "# Title <script>window.pwned=1</script>\n\n> <img src=x onerror=\"window.pwned=1\">\n",
            "sidecar": {"claims": [{"id": "C01", "kind": "reported", "text": HOSTILE_TEXT, "evidence": ["S01"]}]}}


@pytest.fixture(scope="module")
def site():
    key, hostile_key = os.urandom(32), os.urandom(32)
    shares = {}
    live = _share_record(_demo_payload(), key, "coaching", "Prepare for our first coaching session", "Sam, my coach")
    hostile = _share_record(_hostile_payload(), hostile_key, "full", "<i>purpose</i>", "<i>recipient</i>")
    if live and hostile:
        shares = {LIVE_ID: live, HOSTILE_ID: hostile}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep test output quiet
            pass

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802 - http.server's name
            path = self.path.split("?", 1)[0]
            page = None
            if re.fullmatch(r"/s/[A-Za-z0-9_-]+/?", path):
                page = "share.html"
            elif path in ("/privacy", "/responsible-use"):
                page = PAGES[path[1:]]
            if page:
                return self._send(200, (STATIC / page).read_bytes(), "text/html; charset=utf-8")
            if path == "/static/mefile.css":
                return self._send(200, (STATIC / "mefile.css").read_bytes(), "text/css; charset=utf-8")
            match = re.fullmatch(r"/api/shares/([A-Za-z0-9_-]+)", path)
            if match:
                share_id = match.group(1)
                if share_id in shares:
                    return self._send(200, json.dumps(shares[share_id]).encode(), "application/json")
                if share_id == REVOKED_ID:
                    return self._send(410, b'{"error": "this share was revoked or has expired"}', "application/json")
                return self._send(404, b'{"error": "no such share"}', "application/json")
            return self._send(404, b"not found", "text/plain")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield {"base": f"http://127.0.0.1:{server.server_address[1]}", "key": _b64url(key),
               "hostile_key": _b64url(hostile_key), "wrong_key": _b64url(os.urandom(32)), "encrypted": bool(shares)}
    finally:
        server.shutdown()
        server.server_close()


# ---- static checks: the shell, the copy, the hard limits ----

@pytest.mark.parametrize("name", sorted(PAGES))
def test_pages_share_the_product_shell(name):
    html = (STATIC / PAGES[name]).read_text(encoding="utf-8")
    assert re.search(r"<title>[^<]+· lumin8r</title>", html)
    assert 'href="/static/mefile.css"' in html and 'class="skip-link" href="#main"' in html
    assert 'class="wordmark" href="/"' in html
    assert re.search(r'href="/assessment"><span class="long">Take the assessment</span>', html)
    assert re.search(r'href="/app"><span class="long">Your file</span>', html)
    assert 'href="/privacy"' in html and 'href="/responsible-use"' in html
    assert "Your understudy is Claude, an AI." in html
    assert not EMOJI.search(html)
    for word in ("hackathon", "CGU", "judge", "4:30", "team hub", "twin", "player two"):
        assert word.lower() not in html.lower(), word
    # the visual identity is mefile.css's alone: no page-local colors or pixel-font choices
    local_css = "".join(re.findall(r"<style>(.*?)</style>", html, re.S)) + " ".join(re.findall(r'style="([^"]*)"', html))
    assert not HEX_COLOR.search(local_css), HEX_COLOR.findall(local_css)
    assert "rgb" not in local_css and "Silkscreen" not in local_css and "--pixel" not in local_css


def test_privacy_copy_carries_the_facts():
    html = (STATIC / "privacy.html").read_text(encoding="utf-8")
    for fact in ("Last updated 14 November 2026", "[operator contact]", "30 days after your last change", "HttpOnly", "Anthropic",
                 "ElevenLabs", "never send to servers", "at most 90 days", "never content", "Withdraw consent",
                 "stops the link, not copies"):
        assert fact in html, fact


def test_responsible_use_carries_the_refusal_rule_and_the_never_list():
    html = (STATIC / "responsible-use.html").read_text(encoding="utf-8")
    assert "I can&#39;t use this profile for that." in html or "I can't use this profile for that." in html
    for use in ("Hiring", "culture fit", "Promotion readiness", "Performance ratings", "Pay, discipline or layoffs",
                "Predicting", "Inferring emotions, mental health, or protected characteristics", "in disguise",
                "Declining has no consequence", "Employee-held", "Voluntary"):
        assert use in html, use


# ---- the browser walk ----

WALK = r"""
const { chromium } = require('playwright');
const [base, shots, key, hostileKey, wrongKey, liveId, hostileId, revokedId, unknownId, encrypted] = process.argv.slice(2);
(async () => {
  const browser = await chromium.launch();
  const out = { cases: {}, requests: [], pageErrors: [] };
  async function open(name, path, width, waitFor, shot) {
    const context = await browser.newContext({ viewport: { width, height: width > 500 ? 900 : 844 } });
    await context.route('https://fonts.googleapis.com/**', (r) => r.fulfill({ status: 200, contentType: 'text/css', body: '' }));
    const page = await context.newPage();
    const consoleErrors = [];
    page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
    page.on('pageerror', (e) => out.pageErrors.push(name + ': ' + e.message));
    page.on('request', (r) => out.requests.push(r.url()));
    await page.goto(base + path);
    await page.waitForSelector(waitFor, { timeout: 15000 });
    const result = await page.evaluate(() => ({
      title: document.title,
      h1: (document.querySelector('main h1') || {}).textContent || '',
      main: document.querySelector('main').innerText,
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      pwned: window.pwned === 1,
      injected: document.querySelectorAll('main img, main script, main b b, #view i').length,
      focused: document.activeElement && document.activeElement.tagName,
    }));
    result.consoleErrors = consoleErrors;
    await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)));
    if (shot) await page.screenshot({ path: `${shots}/product-${shot}-${width}.png`, fullPage: true });
    return { page, context, result };
  }

  for (const width of [1440, 390]) {
    if (encrypted === '1') {
      const live = await open('live', `/s/${liveId}#${key}`, width, '[data-state=live]', 'share');
      live.result.groups = await live.page.$$eval('section.group', (s) => s.map((g) => ({
        kind: g.dataset.kind, title: g.querySelector('h2').textContent, claims: g.querySelectorAll('li').length,
        cites: g.querySelectorAll('.cite').length })));
      live.result.banner = await live.page.textContent('[data-part=use-limits]');
      live.result.meta = await live.page.$$eval('.meta > div', (d) => d.map((x) => [x.querySelector('dt').textContent, x.querySelector('dd').textContent]));
      live.result.fileHiddenBefore = !(await live.page.isVisible('.full .file'));
      await live.page.click('.full summary');
      live.result.fileTables = await live.page.$$eval('.full .file table', (t) => t.length);
      live.result.fileHeadings = await live.page.$$eval('.full .file h2', (h) => h.map((x) => x.textContent));
      live.result.overflowOpen = await live.page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      out.cases[`live-${width}`] = live.result;
      await live.context.close();
    }
    for (const [name, path, state, shot] of [
      ['revoked', `/s/${revokedId}#${key}`, 'gone', 'share-revoked'],
      ['unknown', `/s/${unknownId}#${key}`, 'not-found', null],
      ['missing-key', `/s/${liveId}`, 'incomplete', 'share-incomplete'],
      ['empty-key', `/s/${liveId}#`, 'incomplete', null],
      ['wrong-key', `/s/${liveId}#${wrongKey}`, encrypted === '1' ? 'cannot-open' : 'gone', null],
    ]) {
      if (name === 'wrong-key' && encrypted !== '1') continue;
      const c = await open(name, path, width, `[data-state=${state}]`, shot);
      out.cases[`${name}-${width}`] = c.result;
      await c.context.close();
    }
    for (const name of ['privacy', 'responsible-use']) {
      const c = await open(name, `/${name}`, width, 'footer', name);
      c.result.footer = await c.page.$$eval('footer a', (a) => a.map((x) => [x.textContent, x.getAttribute('href'), x.getAttribute('aria-current')]));
      out.cases[`${name}-${width}`] = c.result;
      await c.context.close();
    }
  }
  if (encrypted === '1') {
    const c = await open('hostile', `/s/${hostileId}#${hostileKey}`, 1440, '[data-state=live]', null);
    await c.page.click('.full summary');
    await c.page.waitForTimeout(200);
    c.result.pwnedAfterOpen = await c.page.evaluate(() => window.pwned === 1);
    c.result.injectedAfterOpen = await c.page.$$eval('main img, main script', (n) => n.length);
    c.result.claimText = await c.page.textContent('[data-claim=C01]');
    out.cases.hostile = c.result;
    await c.context.close();
  }
  await browser.close();
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
"""


def test_product_pages_in_the_browser(site, tmp_path):
    env = _playwright_env()
    if env is None:
        pytest.skip("node with playwright is not available")
    shots = Path(os.environ.get("PRODUCT_SCREENSHOT_DIR") or tmp_path)
    shots.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "walk.js"
    script.write_text(WALK, encoding="utf-8")
    args = [site["base"], str(shots), site["key"], site["hostile_key"], site["wrong_key"],
            LIVE_ID, HOSTILE_ID, REVOKED_ID, UNKNOWN_ID, "1" if site["encrypted"] else "0"]
    run = subprocess.run(["node", str(script), *args], env=env, capture_output=True, text=True, timeout=240)
    assert run.returncode == 0, run.stderr
    out = json.loads(run.stdout)
    cases = out["cases"]

    assert out["pageErrors"] == []
    # the key never leaves the page: no request carries it, and nothing goes anywhere but this server and the font host
    for key in (site["key"], site["hostile_key"], site["wrong_key"]):
        assert not [url for url in out["requests"] if key in url]
    assert all(url.startswith(site["base"]) or url.startswith("https://fonts.googleapis.com/") for url in out["requests"])

    expected_resource_errors = {"revoked": "410", "unknown": "404"}
    for name, case in cases.items():
        assert case["overflow"] <= 0, (name, case["overflow"])
        allowed = expected_resource_errors.get(name.rsplit("-", 1)[0])
        unexpected = [e for e in case["consoleErrors"] if not (allowed and f"status of {allowed}" in e)]
        assert unexpected == [], (name, unexpected)

    for width in (1440, 390):
        assert cases[f"revoked-{width}"]["main"].count("The owner turned this link off, or it expired. Ask them for a new one.") == 1
        assert "This link does not exist" in cases[f"unknown-{width}"]["h1"]
        assert cases[f"missing-key-{width}"]["h1"] == "This link is incomplete: the part after # is missing"
        assert cases[f"empty-key-{width}"]["h1"] == "This link is incomplete: the part after # is missing"
        assert cases[f"privacy-{width}"]["h1"] and "14 November 2026" in cases[f"privacy-{width}"]["main"]
        assert ["Privacy", "/privacy", "page"] in cases[f"privacy-{width}"]["footer"]
        assert "I can't use this profile for that." in cases[f"responsible-use-{width}"]["main"]
        assert ["Responsible use", "/responsible-use", "page"] in cases[f"responsible-use-{width}"]["footer"]

    if not site["encrypted"]:
        pytest.skip("no AES-GCM encryptor (cryptography or node) to build a live share; the decrypt walk did not run")

    for width in (1440, 390):
        live = cases[f"live-{width}"]
        assert live["h1"] == "How to work with DEMO01"
        assert live["title"] == "How to work with DEMO01 · lumin8r"
        meta = dict(live["meta"])
        assert meta["Shared by"] == "DEMO01" and meta["For"] == "Sam, my coach"
        assert meta["Why"] == "Prepare for our first coaching session"
        assert meta["Version"].startswith("Coaching") and meta["Shared on"] == "14 November 2026"
        assert meta["Expires"] == "14 December 2026"
        assert "Never for hiring, promotion, performance ratings, pay or discipline." in live["banner"]
        assert "not a type" in live["banner"]
        groups = {g["kind"]: g for g in live["groups"]}
        assert [g["kind"] for g in live["groups"]] == ["reported", "observed_style", "measured", "limit"]
        assert groups["reported"]["title"] == "How they handle situations"
        assert groups["observed_style"]["title"] == "How they communicate"
        assert groups["measured"]["title"] == "Self-described traits"
        assert groups["limit"]["title"] == "What this file cannot tell you"
        assert all(g["claims"] > 0 for g in live["groups"])
        assert groups["reported"]["cites"] == groups["reported"]["claims"]
        assert groups["limit"]["cites"] == 0
        assert "middle score means no clear tendency" in live["main"]
        assert live["fileHiddenBefore"] is True and live["fileTables"] >= 1
        assert live["fileHeadings"][0] == "me.md: workplace communication profile for DEMO01"
        assert live["overflowOpen"] <= 0
        assert cases[f"wrong-key-{width}"]["h1"] == "This file could not be unlocked"

    hostile = cases["hostile"]
    assert hostile["pwned"] is False and hostile["pwnedAfterOpen"] is False
    assert hostile["injected"] == 0 and hostile["injectedAfterOpen"] == 0
    assert HOSTILE_TEXT in hostile["claimText"]
    assert hostile["h1"] == "How to work with <b>X1</b>"
