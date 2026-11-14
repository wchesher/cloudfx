# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_shares - share links over HTTP: consent, validation, revoke, expiry, tombstones, ledger, admin listing, workbench switch

from __future__ import annotations

import base64
import datetime as dt
import http.client
import json
import os
import secrets
import stat
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from mefile import app, shares, team

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
CODE = "correct horse battery"
START = dt.datetime(2026, 11, 14, 12, 0, tzinfo=dt.timezone.utc)


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


CIPHERTEXT = b64(secrets.token_bytes(400))
IV = b64(secrets.token_bytes(12))


class Clock:
    def __init__(self):
        self.now = START

    def __call__(self):
        return self.now


class Client:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.cookie = ""

    def call(self, method: str, path: str, body: dict | None = None, headers: dict | None = None):
        sent = {"Content-Type": "application/json", **(headers or {})}
        if self.cookie:
            sent["Cookie"] = self.cookie
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base_url + path, data=data, headers=sent, method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                status, raw, response_headers = response.status, response.read(), dict(response.headers)
        except urllib.error.HTTPError as error:
            status, raw, response_headers = error.code, error.read(), dict(error.headers)
        set_cookie = response_headers.get("Set-Cookie", "")
        if set_cookie.startswith(team.COOKIE_NAME + "="):
            self.cookie = set_cookie.split(";")[0]
        if response_headers.get("Content-Type", "").startswith("application/json"):
            return status, json.loads(raw), response_headers
        return status, raw, response_headers


@pytest.fixture()
def clock(monkeypatch):
    fake = Clock()
    monkeypatch.setattr(shares, "_now", fake)
    return fake


@pytest.fixture()
def server(tmp_path, monkeypatch, clock):
    monkeypatch.setattr(app, "LEDGER_DIR", tmp_path / "data" / "consent")
    monkeypatch.setattr(app, "_CONSENTS", {})
    monkeypatch.setattr(team, "_LOGIN_FAILURES", {})
    monkeypatch.setattr(shares, "_RATE", {})
    monkeypatch.setenv("LUMIN8R_DATA", str(tmp_path / "data"))
    monkeypatch.setenv("MEFILE_PEOPLE_DIR", str(tmp_path / "data" / "people"))
    monkeypatch.setenv("MEFILE_QUESTIONS", str(EXAMPLES / "example_questions.json"))
    for name in ("LUMIN8R_TEAM_CODE", "LUMIN8R_REQUIRE_TEAM_CODE", "LUMIN8R_WORKBENCH", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    http_server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{http_server.server_address[1]}"
    finally:
        http_server.shutdown()
        http_server.server_close()


@pytest.fixture()
def client(server):
    return Client(server)


def consent(client: Client, purposes=("build_profile",), person_id: str = "SHARE-01") -> str:
    status, payload, _ = client.call("POST", "/api/consent", {"person_id": person_id, "purposes": list(purposes)})
    assert status == 200
    return payload["consent_token"]


def share_body(**overrides) -> dict:
    return {"ciphertext": CIPHERTEXT, "iv": IV, "version": "coaching", "purpose": "Coaching sessions in November",
            "recipient_label": "Sam (coach)", **overrides}


def create(client: Client, token: str, **overrides):
    return client.call("POST", "/api/shares", share_body(**overrides), {"X-Consent-Token": token})


def ledger_lines(tmp_path: Path) -> list[dict]:
    path = tmp_path / "data" / "consent" / "ledger.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Create and read
# ---------------------------------------------------------------------------


def test_create_needs_build_profile_consent(client):
    status, payload, headers = client.call("POST", "/api/shares", share_body())
    assert status == 403 and payload == {"error": "consent required", "purpose": "build_profile"}
    assert headers["Cache-Control"] == "no-store"
    token = consent(client, purposes=("ai_processing",))
    assert create(client, token)[0] == 403


def test_create_then_read_live(client, tmp_path):
    token = consent(client)
    status, created, headers = create(client, token)
    assert status == 201 and headers["Cache-Control"] == "no-store"
    assert set(created) == {"id", "manage_token", "url_path"}
    assert shares.valid_id(created["id"]) and created["url_path"] == f"/s/{created['id']}"
    assert len(base64.urlsafe_b64decode(created["manage_token"] + "=")) == 32

    status, share, headers = client.call("GET", f"/api/shares/{created['id']}")
    assert status == 200 and headers["Cache-Control"] == "no-store"
    assert share == {"ciphertext": CIPHERTEXT, "iv": IV, "version": "coaching", "purpose": "Coaching sessions in November",
                     "recipient_label": "Sam (coach)", "created_at": "2026-11-14T12:00:00+00:00",
                     "expires_at": "2026-12-14T12:00:00+00:00"}  # default 30 days

    stored = tmp_path / "data" / "shares" / f"{created['id']}.json"
    assert stat.S_IMODE(os.stat(stored).st_mode) == 0o600
    record = json.loads(stored.read_text(encoding="utf-8"))
    assert created["manage_token"] not in stored.read_text(encoding="utf-8")
    assert record["manage_sha256"] == shares._hash(created["manage_token"])
    assert not list((tmp_path / "data" / "shares").glob(".tmp-*"))


def test_consent_token_in_body_and_explicit_expiry(client):
    token = consent(client)
    expires = (START + dt.timedelta(days=90)).isoformat().replace("+00:00", "Z")
    status, created, _ = client.call("POST", "/api/shares", {**share_body(version="full", expires_at=expires), "consent_token": token})
    assert status == 201
    share = client.call("GET", f"/api/shares/{created['id']}")[1]
    assert share["version"] == "full" and share["expires_at"] == "2027-02-12T12:00:00+00:00"


@pytest.mark.parametrize("overrides, fragment", [
    ({"ciphertext": "not base64!"}, "ciphertext"),
    ({"ciphertext": b64(b"x" * (200 * 1024 + 1))}, "200 KB"),
    ({"ciphertext": b64(b"short")}, "too short"),
    ({"ciphertext": 12345}, "ciphertext"),
    ({"iv": b64(b"x" * 16)}, "12 bytes"),
    ({"iv": None}, "iv"),
    ({"version": "everything"}, "version"),
    ({"purpose": "p" * 201}, "purpose"),
    ({"recipient_label": "r" * 201}, "recipient_label"),
    ({"recipient_label": ["a list"]}, "recipient_label"),
    ({"expires_at": "next tuesday"}, "ISO 8601"),
    ({"expires_at": "2026-11-13T12:00:00Z"}, "future"),
    ({"expires_at": "2027-02-13T12:00:01Z"}, "90 days"),
])
def test_validation_400(client, overrides, fragment):
    token = consent(client)
    status, payload, _ = create(client, token, **overrides)
    assert status == 400 and fragment in payload["error"]


def test_limits_are_inclusive(client):
    token = consent(client)
    assert create(client, token, ciphertext=b64(b"x" * (200 * 1024)), purpose="p" * 200, recipient_label="r" * 200)[0] == 201


def test_id_format_and_unknown(client):
    for path in ("/api/shares/short", "/api/shares/" + "a" * 23, "/api/shares/..%2F..%2Fetc", "/api/shares/"):
        assert client.call("GET", path)[0] == 404, path
    status, payload, _ = client.call("GET", "/api/shares/" + "A" * 22)
    assert status == 404 and payload == {"error": "not found"}
    assert client.call("DELETE", "/api/shares/" + "A" * 22, headers={"X-Manage-Token": "x"})[0] == 404


def test_share_page_routes(client):
    token = consent(client)
    share_id = create(client, token)[1]["id"]
    status, body, headers = client.call("GET", f"/s/{share_id}")
    assert status == 200 and headers["Content-Type"].startswith("text/html")
    assert headers["X-Robots-Tag"].startswith("noindex") and headers["Cache-Control"] == "no-store"
    if (app.STATIC / "share.html").is_file():
        assert body == (app.STATIC / "share.html").read_bytes()
    assert client.call("GET", "/s/" + "Z" * 22)[0] == 200  # the page itself reports unknown links after its fetch
    for path in ("/s/short", "/s/" + "a" * 23, "/s/a/b", "/s/"):
        assert client.call("GET", path)[0] == 404, path
    for path, name in (("/privacy", "privacy.html"), ("/responsible-use", "responsible-use.html")):
        status, body, headers = client.call("GET", path)
        assert status == 200 and headers["Content-Type"].startswith("text/html")
        if (app.STATIC / name).is_file():
            assert body == (app.STATIC / name).read_bytes()


def test_pages_fall_back_when_files_are_missing(client, monkeypatch, tmp_path):
    monkeypatch.setattr(app, "STATIC", tmp_path / "no-static")
    for path in ("/privacy", "/responsible-use", "/s/" + "Z" * 22):
        status, body, _ = client.call("GET", path)
        assert status == 200 and body.startswith(b"<!doctype html>"), path


# ---------------------------------------------------------------------------
# Revoke, expiry, tombstones
# ---------------------------------------------------------------------------


def test_revoke_with_manage_token(client, tmp_path):
    token = consent(client)
    created = create(client, token)[1]
    path = f"/api/shares/{created['id']}"
    assert client.call("DELETE", path)[0] == 403  # no token
    status, payload, _ = client.call("DELETE", path, headers={"X-Manage-Token": "wrong"})
    assert status == 403 and payload == {"error": "wrong manage token"}
    assert client.call("GET", path)[0] == 200

    status, payload, headers = client.call("DELETE", path, headers={"X-Manage-Token": created["manage_token"]})
    assert status == 200 and payload["state"] == "revoked" and headers["Cache-Control"] == "no-store"
    status, payload, _ = client.call("GET", path)
    assert status == 410 and "error" in payload
    assert client.call("DELETE", path, headers={"X-Manage-Token": created["manage_token"]})[0] == 410

    stored = (tmp_path / "data" / "shares" / f"{created['id']}.json").read_text(encoding="utf-8")
    tomb = json.loads(stored)
    assert tomb["state"] == "revoked" and tomb["id"] == created["id"] and tomb["revoked_at"]
    for gone in ("ciphertext", "iv", "purpose", "recipient_label", "manage_sha256", "person_id"):
        assert gone not in tomb
    assert CIPHERTEXT not in stored


def test_expiry_after_time_travel(client, clock, tmp_path):
    token = consent(client)
    created = create(client, token, expires_at="2026-11-15T12:00:00Z")[1]
    other = create(client, token)[1]
    path = f"/api/shares/{created['id']}"
    clock.now = START + dt.timedelta(hours=23, minutes=59)
    assert client.call("GET", path)[0] == 200
    clock.now = START + dt.timedelta(days=1)
    assert client.call("GET", path)[0] == 410  # deleted on read
    tomb = json.loads((tmp_path / "data" / "shares" / f"{created['id']}.json").read_text(encoding="utf-8"))
    assert tomb["state"] == "expired" and "ciphertext" not in tomb
    assert client.call("DELETE", path, headers={"X-Manage-Token": created["manage_token"]})[0] == 410

    clock.now = START + dt.timedelta(days=31)
    assert shares.sweep() == {"expired": 1, "dropped": 0}  # the sweep deletes without any read
    assert "ciphertext" not in json.loads((tmp_path / "data" / "shares" / f"{other['id']}.json").read_text(encoding="utf-8"))
    clock.now = START + dt.timedelta(days=1 + shares.TOMBSTONE_DAYS + 1)
    assert shares.sweep()["dropped"] == 1
    assert client.call("GET", path)[0] == 404  # tombstone aged out


# ---------------------------------------------------------------------------
# Ledger, rate limit
# ---------------------------------------------------------------------------


def test_ledger_events_carry_no_content_or_tokens(client, tmp_path):
    token = consent(client)
    created = create(client, token)[1]
    client.call("DELETE", f"/api/shares/{created['id']}", headers={"X-Manage-Token": created["manage_token"]})
    entries = ledger_lines(tmp_path)
    made = next(e for e in entries if e["event"] == "share_created")
    revoked = next(e for e in entries if e["event"] == "share_revoked")
    assert made == {"at": made["at"], "event": "share_created", "person_id": "SHARE-01", "share_id": created["id"],
                    "version": "coaching", "purpose": "Coaching sessions in November", "recipient_label": "Sam (coach)",
                    "expires_at": "2026-12-14T12:00:00+00:00"}
    assert revoked == {"at": revoked["at"], "event": "share_revoked", "person_id": "SHARE-01", "share_id": created["id"],
                       "by": "owner"}
    raw = (tmp_path / "data" / "consent" / "ledger.jsonl").read_text(encoding="utf-8")
    for secret in (CIPHERTEXT, IV, created["manage_token"], shares._hash(created["manage_token"]), token):
        assert secret not in raw


def test_rate_limit_per_address(client, monkeypatch, clock):
    monkeypatch.setattr(shares, "RATE_LIMIT", 3)
    token = consent(client)
    assert create(client, token, version="nope")[0] == 400  # invalid requests do not use up the allowance
    for _ in range(3):
        assert create(client, token)[0] == 201
    status, payload, _ = create(client, token)
    assert status == 429 and "too many" in payload["error"]
    clock.now = START + dt.timedelta(hours=1)
    assert create(client, token)[0] == 201


# ---------------------------------------------------------------------------
# Admin listing and operator revoke
# ---------------------------------------------------------------------------


def test_admin_shares_listing_redacts_and_operator_revokes(client, monkeypatch, tmp_path):
    monkeypatch.setenv("LUMIN8R_TEAM_CODE", CODE)
    token = consent(client)
    first = create(client, token)[1]
    second = create(client, token, version="full", purpose="Team onboarding", recipient_label="Ana")[1]
    client.call("DELETE", f"/api/shares/{first['id']}", headers={"X-Manage-Token": first["manage_token"]})

    assert client.call("GET", "/api/admin/shares")[0] == 401
    assert client.call("POST", "/api/admin/shares/revoke", {"id": second["id"]})[0] == 401
    assert client.call("POST", "/api/team/login", {"code": CODE})[0] == 200  # sign-in works with the workbench off

    status, listing, headers = client.call("GET", "/api/admin/shares")
    assert status == 200 and headers["Cache-Control"] == "no-store"
    assert listing["counts"] == {"live": 1, "revoked": 1, "expired": 0}
    live = next(row for row in listing["shares"] if row["state"] == "live")
    assert live == {"id_prefix": second["id"][:6], "version": "full", "purpose": "Team onboarding", "recipient_label": "Ana",
                    "created_at": "2026-11-14T12:00:00+00:00", "expires_at": "2026-12-14T12:00:00+00:00", "state": "live",
                    "ended_at": None}
    raw = json.dumps(listing)
    for secret in (first["id"], second["id"], first["manage_token"], second["manage_token"], CIPHERTEXT, IV, "SHARE-01",
                   shares._hash(second["manage_token"])):
        assert secret not in raw

    assert client.call("POST", "/api/admin/shares/revoke", {"id": "abc"})[0] == 400
    assert client.call("POST", "/api/admin/shares/revoke", {"id": first["id"][:6]})[0] == 404  # already revoked
    status, payload, _ = client.call("POST", "/api/admin/shares/revoke", {"id": second["id"][:6]})
    assert status == 200 and payload["state"] == "revoked" and payload["id_prefix"] == second["id"][:6]
    assert client.call("GET", f"/api/shares/{second['id']}")[0] == 410
    revoked = [e for e in ledger_lines(tmp_path) if e["event"] == "share_revoked"]
    assert [e["by"] for e in revoked] == ["owner", "operator"]
    assert client.call("GET", "/api/admin/shares")[1]["counts"] == {"live": 0, "revoked": 2, "expired": 0}


# ---------------------------------------------------------------------------
# The workbench switch
# ---------------------------------------------------------------------------

HUB_GETS = ("/api/team/people", "/api/team/results", "/api/team/final", "/api/team/docs", "/api/team/selfcheck",
            "/api/team/docs/strategy", "/api/team/files/ratesheet.html", "/api/team/final/bundle", "/api/station/queue",
            "/api/station/results")
HUB_POSTS = ("/api/team/people", "/api/team/people/delete", "/api/team/run", "/api/team/experiment", "/api/team/ratesheet",
             "/api/team/agreement", "/api/team/final/inputs", "/api/team/final/answer", "/api/team/final/judge",
             "/api/team/selfcheck", "/api/station/answer")


def test_workbench_off_hides_the_hub_and_keeps_admin(client, monkeypatch):
    monkeypatch.setenv("LUMIN8R_TEAM_CODE", CODE)
    assert client.call("GET", "/api/config")[1]["workbench_enabled"] is False
    for path in ("/team", "/workbench", "/paste"):
        status, body, headers = client.call("GET", path)
        assert status == 404 and headers["Content-Type"].startswith("text/html"), path
    client.call("POST", "/api/team/login", {"code": CODE})
    for path in HUB_GETS:
        assert client.call("GET", path)[:2] == (404, {"error": "not available"}), path
    for path in HUB_POSTS:
        assert client.call("POST", path, {})[:2] == (404, {"error": "not available"}), path
    assert client.call("GET", "/api/team/me")[1] == {"signed_in": True, "mode": "code"}
    for path in ("/api/admin/overview", "/api/admin/consent", "/api/admin/people", "/api/admin/settings", "/api/admin/shares"):
        assert client.call("GET", path)[0] == 200, path
    assert client.call("GET", "/admin")[0] == 200
    workbench = next(row for row in client.call("GET", "/api/admin/settings")[1]["settings"] if row["name"] == "LUMIN8R_WORKBENCH")
    assert workbench["set"] is False and workbench["kind"] == "update"
    assert client.call("POST", "/api/team/logout", {})[0] == 200


def test_workbench_on_serves_workbench_and_redirects_team(client, server, monkeypatch):
    monkeypatch.setenv("LUMIN8R_WORKBENCH", "1")
    assert client.call("GET", "/api/config")[1]["workbench_enabled"] is True
    status, body, _ = client.call("GET", "/workbench")
    assert status == 200
    if (app.STATIC / "team.html").is_file():
        assert body == (app.STATIC / "team.html").read_bytes()
    connection = http.client.HTTPConnection(server.split("//")[1], timeout=10)
    connection.request("GET", "/team")
    response = connection.getresponse()
    assert response.status == 302 and response.getheader("Location") == "/workbench"
    connection.close()
    assert client.call("GET", "/api/team/people")[0] == 200  # local mode: open
    assert client.call("GET", "/paste")[0] == 200


def test_withdrawal_with_own_token_turns_off_that_persons_shares(tmp_path, monkeypatch):
    from mefile import app, shares
    monkeypatch.setenv("LUMIN8R_DATA", str(tmp_path))
    events = []
    import base64
    body = {"ciphertext": base64.urlsafe_b64encode(b"x" * 32).decode().rstrip("="),
            "iv": base64.urlsafe_b64encode(b"y" * 12).decode().rstrip("="), "version": "coaching",
            "purpose": "coaching", "recipient_label": "Dana"}
    mine = shares.create(dict(body), "WD-01", "127.0.0.1", events.append)
    other = shares.create(dict(body), "WD-02", "127.0.0.2", events.append)
    assert shares.revoke_person("WD-01", events.append) == [mine["id"][:6]]
    import pytest
    with pytest.raises(shares.ShareError):
        shares.read(mine["id"])
    assert shares.read(other["id"])["version"] == "coaching"
    assert any(e.get("event") == "share_revoked" and e.get("by") == "withdrawal" for e in events)
