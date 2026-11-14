# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_context - saved progress on the server: cookie, save, reload, forget, resume on another device, limits, sweep

from __future__ import annotations

import http.client
import json
import os
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from mefile import app, context


@pytest.fixture()
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMIN8R_DATA", str(tmp_path / "data"))
    monkeypatch.setattr(app, "LEDGER_DIR", tmp_path / "data" / "consent")
    http_server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    threading.Thread(target=http_server.serve_forever, daemon=True).start()
    try:
        yield http_server.server_address[1], tmp_path / "data" / "context"
    finally:
        http_server.shutdown()
        http_server.server_close()


def call(port, method, path, body=None, cookie=""):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    conn.request(method, path, body=None if body is None else json.dumps(body), headers=headers)
    response = conn.getresponse()
    raw = response.read()
    set_cookie = response.getheader("Set-Cookie") or ""
    payload = json.loads(raw) if (response.getheader("Content-Type") or "").startswith("application/json") else raw
    return response.status, payload, set_cookie, response.getheader("Location")


def test_progress_survives_a_new_page_and_only_the_cookie_holds_an_id(server):
    port, folder = server
    status, payload, set_cookie, _ = call(port, "GET", "/api/context")
    assert status == 200 and payload["items"] == {}
    assert "HttpOnly" in set_cookie and "SameSite=Lax" in set_cookie and set_cookie.startswith(context.COOKIE_NAME + "=")
    cookie = set_cookie.split(";")[0]
    status, saved, _, _ = call(port, "POST", "/api/context", {"set": {"localStorage:lumin8r-kit-v1": '{"step":3}'}}, cookie)
    assert status == 200 and saved["count"] == 1
    status, payload, again, _ = call(port, "GET", "/api/context", cookie=cookie)
    assert payload["items"] == {"localStorage:lumin8r-kit-v1": '{"step":3}'} and again.split(";")[0] == cookie
    # the file is named by the hash: a directory listing never yields a working cookie
    files = list(folder.glob("*.json"))
    assert len(files) == 1 and payload["resume"] not in files[0].name
    assert oct(files[0].stat().st_mode & 0o777) == "0o600"
    # another browser sees nothing
    _, other, _, _ = call(port, "GET", "/api/context")
    assert other["items"] == {}


def test_removing_every_item_or_forgetting_deletes_the_file(server):
    port, folder = server
    _, _, set_cookie, _ = call(port, "GET", "/api/context")
    cookie = set_cookie.split(";")[0]
    call(port, "POST", "/api/context", {"set": {"sessionStorage:a": "1", "sessionStorage:b": "2"}}, cookie)
    call(port, "POST", "/api/context", {"set": {"sessionStorage:a": None}}, cookie)
    assert len(list(folder.glob("*.json"))) == 1
    call(port, "POST", "/api/context", {"set": {"sessionStorage:b": None}}, cookie)
    assert list(folder.glob("*.json")) == []
    call(port, "POST", "/api/context", {"set": {"sessionStorage:a": "1"}}, cookie)
    status, _, cleared, _ = call(port, "POST", "/api/context/forget", {}, cookie)
    assert status == 200 and "Max-Age=0" in cleared and list(folder.glob("*.json")) == []


def test_resume_link_opens_the_same_progress_on_another_device(server):
    port, _ = server
    _, payload, set_cookie, _ = call(port, "GET", "/api/context")
    cookie = set_cookie.split(";")[0]
    call(port, "POST", "/api/context", {"set": {"sessionStorage:lumin8r-answers-v1": "{}"}}, cookie)
    status, _, resumed, location = call(port, "GET", "/resume?code=" + payload["resume"])
    assert status == 302 and location == "/app" and resumed.split(";")[0] == cookie
    status, _, _, _ = call(port, "GET", "/resume?code=" + "x" * 43)
    assert status == 404


def test_bad_keys_values_and_missing_cookie_are_refused(server):
    port, _ = server
    assert call(port, "POST", "/api/context", {"set": {"localStorage:a": "1"}})[0] == 400  # no cookie
    _, _, set_cookie, _ = call(port, "GET", "/api/context")
    cookie = set_cookie.split(";")[0]
    assert call(port, "POST", "/api/context", {"set": {"../etc": "1"}}, cookie)[0] == 400
    assert call(port, "POST", "/api/context", {"set": {"localStorage:a": 5}}, cookie)[0] == 400
    assert call(port, "POST", "/api/context", {"set": {}}, cookie)[0] == 400
    many = {f"localStorage:k{i}": "v" for i in range(context.MAX_KEYS + 1)}
    assert call(port, "POST", "/api/context", {"set": many}, cookie)[0] == 413


def test_sweep_deletes_progress_untouched_for_the_retention_period(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMIN8R_DATA", str(tmp_path))
    fresh, stale = context.new_id(), context.new_id()
    context.update(fresh, {"localStorage:a": "1"})
    context.update(stale, {"localStorage:a": "1"})
    old = time.time() - (context.RETENTION_DAYS + 1) * 86400
    os.utime(context._path(stale), (old, old))
    assert context.sweep() == 1
    assert context.load(fresh) == {"localStorage:a": "1"} and context.load(stale) == {}


def test_finished_assessment_reaches_the_hub_without_a_team_sign_in(server, monkeypatch, tmp_path):
    port, _ = server
    examples = Path(__file__).resolve().parents[1] / "examples"
    build = json.loads((examples / "example_build_answers.json").read_text(encoding="utf-8"))
    test = json.loads((examples / "example_test_answers.json").read_text(encoding="utf-8"))
    body = {"code": "DEMO01", "build": build, "test": test}
    monkeypatch.delenv("LUMIN8R_WORKBENCH", raising=False)
    assert call(port, "POST", "/api/kit/submit", body)[0] == 404  # product mode: no hub at all
    monkeypatch.setenv("LUMIN8R_WORKBENCH", "1")
    monkeypatch.setenv("MEFILE_PEOPLE_DIR", str(tmp_path / "people"))
    monkeypatch.setenv("LUMIN8R_TEAM_CODE", "team-secret")  # the team gate is on, and the participant still gets through
    _, _, mine, _ = call(port, "GET", "/api/context")
    _, _, theirs, _ = call(port, "GET", "/api/context")
    mine, theirs = mine.split(";")[0], theirs.split(";")[0]
    assert call(port, "POST", "/api/kit/submit", body)[0] == 400  # no saved-progress cookie
    status, payload, _, _ = call(port, "POST", "/api/kit/submit", body, mine)
    assert status == 200 and payload["saved"] is True
    folder = tmp_path / "people" / "DEMO01"
    assert (folder / "build.json").exists() and (folder / "test.json").exists()
    assert call(port, "POST", "/api/kit/submit", body, mine)[0] == 200  # the same browser may resend
    status, payload, _, _ = call(port, "POST", "/api/kit/submit", body, theirs)
    assert status == 409 and "already used" in payload["error"]  # nobody overwrites someone else's code
    assert call(port, "POST", "/api/kit/submit", {"code": "DEMO01", "build": build}, mine)[0] == 400  # both files
