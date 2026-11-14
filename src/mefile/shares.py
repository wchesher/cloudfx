# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# shares - end-to-end encrypted share links: ciphertext-only storage, manage tokens, revoke, expiry, tombstones

"""
Share links (docs/product.md, "Share API (contract)")
=====================================================

The browser encrypts the shared version (AES-GCM) with a fresh key that travels only in the link's
``#fragment``. This module stores what the server is allowed to hold, one JSON file per share in
``LUMIN8R_DATA/shares/<id>.json`` (0600, written atomically):

  live       {id, state: "live", ciphertext, iv, version, purpose, recipient_label, created_at,
              expires_at, manage_sha256, person_id}
  tombstone  {id, state: "revoked"|"expired", revoked_at|expired_at, version, created_at, expires_at}

The raw manage token is returned once, on create, and never stored: only its SHA-256. Revoking or
expiring replaces the file with a tombstone, so the ciphertext and the free text (purpose, recipient
label) are gone from the share file (the consent ledger keeps the purpose and recipient label as the
record) and a read answers 410 instead of 404. Tombstones are dropped
``TOMBSTONE_DAYS`` after they were made; after that the id reads as unknown (404).

The ledger receives ``share_created`` and ``share_revoked`` events through the callable the caller
passes in (``app._ledger_append``): never the ciphertext, the iv, or any token or token hash.

Time comes from ``_now()`` so tests can travel; the rate limiter uses the same clock.
"""

from __future__ import annotations

import base64
import binascii
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import threading
from collections import deque
from pathlib import Path
from typing import Callable

from . import team

VERSIONS = ("coaching", "full")
MAX_CIPHERTEXT_BYTES = 200 * 1024
MIN_CIPHERTEXT_BYTES = 16  # an AES-GCM ciphertext is at least its 16-byte tag
IV_BYTES = 12
MAX_TEXT = 200
DEFAULT_DAYS = 30
MAX_DAYS = 90
TOMBSTONE_DAYS = 90
SWEEP_SECONDS = 3600
RATE_LIMIT = 30  # creates per client address per window
RATE_WINDOW_SECONDS = 3600
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{22}")
PREFIX_PATTERN = re.compile(r"[A-Za-z0-9_-]{6,22}")
BASE64URL = re.compile(r"[A-Za-z0-9_-]+={0,2}")

Ledger = Callable[[dict], dict]

_LOCK = threading.Lock()
_RATE: dict[str, deque] = {}
_RATE_LOCK = threading.Lock()


class ShareError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _iso(moment: dt.datetime) -> str:
    return moment.astimezone(dt.timezone.utc).isoformat(timespec="seconds")


def _parse_time(text: str) -> dt.datetime:
    moment = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=dt.timezone.utc)


def shares_dir() -> Path:
    return team.data_dir() / "shares"


def valid_id(share_id: str) -> bool:
    return isinstance(share_id, str) and bool(ID_PATTERN.fullmatch(share_id))


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _decode_base64url(text, field: str) -> bytes:
    if not isinstance(text, str) or not BASE64URL.fullmatch(text):
        raise ShareError(400, f"{field} must be a base64url string")
    try:
        return base64.urlsafe_b64decode(text.rstrip("=") + "=" * (-len(text.rstrip("=")) % 4))
    except (binascii.Error, ValueError):
        raise ShareError(400, f"{field} must be a base64url string") from None


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


def _path(share_id: str) -> Path:
    return shares_dir() / f"{share_id}.json"


def _read(share_id: str) -> dict | None:
    try:
        record = json.loads(_path(share_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) and record.get("id") == share_id else None


def _write(record: dict) -> None:
    """Atomic 0600 write: a temp file in the same folder, fsync, then rename over the target."""
    folder = shares_dir()
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=folder, prefix=".tmp-", suffix=".json")
    try:
        os.fchmod(handle, 0o600)
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, _path(record["id"]))
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _tombstone(record: dict, state: str, at: dt.datetime) -> dict:
    stamp = "revoked_at" if state == "revoked" else "expired_at"
    tomb = {"id": record["id"], "state": state, stamp: _iso(at)}
    for key in ("version", "created_at", "expires_at"):
        if key in record:
            tomb[key] = record[key]
    _write(tomb)
    return tomb


def _expired(record: dict, now: dt.datetime) -> bool:
    try:
        return _parse_time(str(record.get("expires_at", ""))) <= now
    except ValueError:
        return True  # an unreadable expiry fails toward deleting the ciphertext


def _settle(record: dict, now: dt.datetime) -> dict:
    """A live record past its expiry becomes an expired tombstone (call with _LOCK held)."""
    if record.get("state") == "live" and _expired(record, now):
        return _tombstone(record, "expired", now)
    return record


def _ids() -> list[str]:
    folder = shares_dir()
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob("*.json") if valid_id(p.stem) and not p.is_symlink())


# ---------------------------------------------------------------------------
# Rate limit
# ---------------------------------------------------------------------------


def _rate_check(address: str, now: dt.datetime) -> None:
    moment = now.timestamp()
    with _RATE_LOCK:
        hits = _RATE.setdefault(address or "unknown", deque())
        while hits and moment - hits[0] >= RATE_WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= RATE_LIMIT:
            raise ShareError(429, "too many share links from this address; try again later")
        hits.append(moment)


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def _text(body: dict, field: str) -> str:
    value = body.get(field, "")
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ShareError(400, f"{field} must be text")
    value = value.strip()
    if len(value) > MAX_TEXT:
        raise ShareError(400, f"{field} must be at most {MAX_TEXT} characters")
    return value


def _expiry(body: dict, now: dt.datetime) -> dt.datetime:
    value = body.get("expires_at")
    if value in (None, ""):
        return now + dt.timedelta(days=DEFAULT_DAYS)
    if not isinstance(value, str):
        raise ShareError(400, "expires_at must be an ISO 8601 date and time")
    try:
        moment = _parse_time(value)
    except ValueError:
        raise ShareError(400, "expires_at must be an ISO 8601 date and time") from None
    if moment <= now:
        raise ShareError(400, "expires_at must be in the future")
    if moment > now + dt.timedelta(days=MAX_DAYS):
        raise ShareError(400, f"expires_at must be at most {MAX_DAYS} days from now")
    return moment


def create(body: dict, person_id: str, client_address: str, ledger: Ledger) -> dict:
    """Validate and store one share; returns {id, manage_token, url_path}. The caller has checked consent."""
    now = _now()
    ciphertext = body.get("ciphertext")
    raw = _decode_base64url(ciphertext, "ciphertext")
    if len(raw) > MAX_CIPHERTEXT_BYTES:
        raise ShareError(400, f"ciphertext must be at most {MAX_CIPHERTEXT_BYTES // 1024} KB")
    if len(raw) < MIN_CIPHERTEXT_BYTES:
        raise ShareError(400, "ciphertext is too short to be AES-GCM output")
    iv = body.get("iv")
    if len(_decode_base64url(iv, "iv")) != IV_BYTES:
        raise ShareError(400, f"iv must be {IV_BYTES} bytes")
    version = body.get("version")
    if version not in VERSIONS:
        raise ShareError(400, f"version must be one of: {', '.join(VERSIONS)}")
    purpose = _text(body, "purpose")
    recipient_label = _text(body, "recipient_label")
    expires_at = _iso(_expiry(body, now))
    _rate_check(client_address, now)  # counted only once the request is valid

    manage_token = secrets.token_urlsafe(32)
    with _LOCK:
        share_id = secrets.token_urlsafe(16)
        while _path(share_id).exists():
            share_id = secrets.token_urlsafe(16)
        record = {"id": share_id, "state": "live", "ciphertext": ciphertext, "iv": iv, "version": version,
                  "purpose": purpose, "recipient_label": recipient_label, "created_at": _iso(now),
                  "expires_at": expires_at, "manage_sha256": _hash(manage_token), "person_id": person_id}
        _write(record)
    ledger({"event": "share_created", "person_id": person_id, "share_id": share_id, "version": version,
            "purpose": purpose, "recipient_label": recipient_label, "expires_at": expires_at})
    return {"id": share_id, "manage_token": manage_token, "url_path": f"/s/{share_id}"}


def read(share_id: str) -> dict:
    """The live share for a recipient. 404 unknown, 410 revoked or expired (an expired one is deleted now)."""
    if not valid_id(share_id):
        raise ShareError(404, "not found")
    with _LOCK:
        record = _read(share_id)
        if record is None:
            raise ShareError(404, "not found")
        record = _settle(record, _now())
    if record.get("state") != "live":
        raise ShareError(410, "this link was turned off by its owner or has expired")
    return {key: record[key] for key in ("ciphertext", "iv", "version", "purpose", "recipient_label", "created_at", "expires_at")}


def _revoke_locked(record: dict, by: str, ledger: Ledger) -> dict:
    tomb = _tombstone(record, "revoked", _now())
    person = {"person_id": record["person_id"]} if record.get("person_id") else {}
    ledger({"event": "share_revoked", **person, "share_id": record["id"], "by": by})
    return tomb


def revoke(share_id: str, manage_token: str, ledger: Ledger) -> dict:
    """Owner revoke with the manage token. 404 unknown, 410 already gone, 403 wrong or missing token."""
    if not valid_id(share_id):
        raise ShareError(404, "not found")
    with _LOCK:
        record = _read(share_id)
        if record is None:
            raise ShareError(404, "not found")
        record = _settle(record, _now())
        if record.get("state") != "live":
            raise ShareError(410, "this link is already turned off")
        if not manage_token or not hmac.compare_digest(_hash(manage_token), str(record.get("manage_sha256", ""))):
            raise ShareError(403, "wrong manage token")
        tomb = _revoke_locked(record, "owner", ledger)
    return {"id": share_id, "state": "revoked", "revoked_at": tomb["revoked_at"]}


def revoke_person(person_id: str, ledger: Ledger) -> list[str]:
    """Withdrawal: turn off every live share this person code created. Returns the revoked share ids' 6-character prefixes."""
    if not person_id:
        return []
    revoked = []
    with _LOCK:
        now = _now()
        for share_id in _ids():
            record = _read(share_id)
            if record is None:
                continue
            record = _settle(record, now)
            if record.get("state") == "live" and record.get("person_id") == person_id:
                _revoke_locked(record, "withdrawal", ledger)
                revoked.append(share_id[:6])
    return revoked


def operator_revoke(id_or_prefix: str, ledger: Ledger) -> dict:
    """Operator revoke from /admin: a full id, or the 6+ character prefix the listing shows (must match one live share)."""
    if not isinstance(id_or_prefix, str) or not PREFIX_PATTERN.fullmatch(id_or_prefix):
        raise ShareError(400, "id must be a share id or its first 6 or more characters")
    with _LOCK:
        now = _now()
        matches = []
        for share_id in _ids():
            if share_id.startswith(id_or_prefix):
                record = _read(share_id)
                if record is not None:
                    record = _settle(record, now)
                    if record.get("state") == "live":
                        matches.append(record)
        if not matches:
            raise ShareError(404, "no live share matches that id")
        if len(matches) > 1:
            raise ShareError(409, "more than one live share matches; give more characters of the id")
        tomb = _revoke_locked(matches[0], "operator", ledger)
    return {"id_prefix": matches[0]["id"][:6], "state": "revoked", "revoked_at": tomb["revoked_at"]}


def sweep() -> dict:
    """Turn every expired live share into a tombstone and drop tombstones older than TOMBSTONE_DAYS."""
    expired = dropped = 0
    with _LOCK:
        now = _now()
        horizon = now - dt.timedelta(days=TOMBSTONE_DAYS)
        for share_id in _ids():
            record = _read(share_id)
            if record is None:
                continue
            if record.get("state") == "live":
                if _expired(record, now):
                    _tombstone(record, "expired", now)
                    expired += 1
                continue
            stamp = record.get("revoked_at") or record.get("expired_at") or ""
            try:
                old = _parse_time(str(stamp)) < horizon
            except ValueError:
                old = True
            if old:
                try:
                    _path(share_id).unlink()
                    dropped += 1
                except OSError:
                    pass
        for leftover in shares_dir().glob(".tmp-*.json") if shares_dir().is_dir() else []:
            try:
                leftover.unlink()  # a write that died between create and rename
            except OSError:
                pass
    return {"expired": expired, "dropped": dropped}


def admin_listing() -> dict:
    """Counts and a redacted row per share for /admin: id prefix only, no ciphertext, iv, token hash or person."""
    sweep()
    rows = []
    counts = {"live": 0, "revoked": 0, "expired": 0}
    with _LOCK:
        for share_id in _ids():
            record = _read(share_id)
            if record is None:
                continue
            state = record.get("state")
            if state not in counts:
                continue
            counts[state] += 1
            rows.append({"id_prefix": share_id[:6], "version": record.get("version"), "purpose": record.get("purpose"),
                         "recipient_label": record.get("recipient_label"), "created_at": record.get("created_at"),
                         "expires_at": record.get("expires_at"), "state": state,
                         "ended_at": record.get("revoked_at") or record.get("expired_at")})
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return {"counts": counts, "shares": rows, "tombstone_days": TOMBSTONE_DAYS}


def start_sweeper() -> threading.Thread:
    """Sweep now, then every SWEEP_SECONDS, on a daemon thread (a failed sweep is reported, never fatal)."""
    def loop() -> None:
        stop = threading.Event()
        while True:
            try:
                result = sweep()
                if result["expired"] or result["dropped"]:
                    print(f"shares sweep: {result['expired']} expired, {result['dropped']} tombstones dropped")
            except Exception as error:  # the type only
                print(f"shares sweep failed: {type(error).__name__}")
            stop.wait(SWEEP_SECONDS)

    thread = threading.Thread(target=loop, name="shares-sweeper", daemon=True)
    thread.start()
    return thread
