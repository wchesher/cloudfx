# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# context - server-side saved progress: the pages keep nothing in the browser, only a random ID cookie

"""
Saved progress on the server (no browser storage)
=================================================

Every page used to keep the person's work in localStorage or sessionStorage: the assessment in
progress, the answers handed to Your file, the consent receipt, the interview draft and transcript,
the share links' manage tokens, the model name the workbench saw. A closed tab, a cleared browser or
a second device lost it. Now the pages hold it in memory and save every change here, keyed by one
random ID in an HttpOnly cookie (``lumin8r_ctx``) that carries no content.

Storage: ``DATA/context/<sha256(id)>.json`` = ``{"items": {"<area>:<key>": "<string>"}, "updated": iso}``.
The file name is the hash, so a directory listing never yields a working cookie. ``<area>`` is the
browser storage area the page used to name (``localStorage`` or ``sessionStorage``), kept so the
pages' existing logic (for example "Remember on this device" off clears only the remembered copy)
works unchanged. Removing the last item deletes the file; "Forget" and withdrawal remove every item.
A context untouched for ``RETENTION_DAYS`` is deleted by the sweeper.

Endpoints (app.py)
  GET  /api/context            -> {items, resume}; sets the cookie when absent or unknown
  POST /api/context            {set: {key: string|null}} -> {ok, count}; null removes the key
  POST /api/context/forget     delete this context entirely and clear the cookie
  GET  /resume?code=<id>       continue on another device: sets the cookie to an existing context, then /app
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import secrets
import threading
import time
from http.cookies import CookieError, SimpleCookie
from pathlib import Path

from . import team

COOKIE_NAME = "lumin8r_ctx"
RETENTION_DAYS = 30
MAX_CONTEXT_BYTES = 3_000_000  # all items of one context together
MAX_KEYS = 64
MAX_CONTEXTS = 20_000  # refuse new contexts beyond this, so nobody can fill the disk with empty ones
SWEEP_SECONDS = 3600
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{32,64}$")
_KEY_RE = re.compile(r"^(localStorage|sessionStorage):[A-Za-z0-9_.:-]{1,80}$")
_LOCK = threading.Lock()


class ContextError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def context_dir() -> Path:
    return team.data_dir() / "context"


def valid_id(context_id: str) -> bool:
    return bool(context_id) and bool(_ID_RE.match(context_id))


def _path(context_id: str) -> Path:
    return context_dir() / (hashlib.sha256(context_id.encode("utf-8")).hexdigest() + ".json")


def presented_id(cookie_header: str) -> str:
    try:
        cookies = SimpleCookie(cookie_header or "")
    except CookieError:
        return ""
    morsel = cookies.get(COOKIE_NAME)
    value = morsel.value if morsel else ""
    return value if valid_id(value) else ""


def cookie(context_id: str, https: bool) -> str:
    value = f"{COOKIE_NAME}={context_id}; Max-Age={RETENTION_DAYS * 86400}; HttpOnly; SameSite=Lax; Path=/"
    return value + ("; Secure" if https else "")


def clear_cookie(https: bool) -> str:
    return f"{COOKIE_NAME}=; Max-Age=0; HttpOnly; SameSite=Lax; Path=/" + ("; Secure" if https else "")


def exists(context_id: str) -> bool:
    return valid_id(context_id) and _path(context_id).is_file()


def new_id() -> str:
    return secrets.token_urlsafe(32)


def load(context_id: str) -> dict[str, str]:
    if not valid_id(context_id):
        return {}
    try:
        data = json.loads(_path(context_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    items = data.get("items") if isinstance(data, dict) else None
    return {k: v for k, v in items.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(items, dict) else {}


def _write(context_id: str, items: dict[str, str]) -> None:
    path = _path(context_id)
    if not items:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{secrets.token_hex(4)}.tmp")
    payload = {"items": items, "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def update(context_id: str, changes) -> int:
    """Apply {key: string|None}; return how many items the context now holds."""
    if not valid_id(context_id):
        raise ContextError(400, "no saved-progress cookie; reload the page")
    if not isinstance(changes, dict) or not changes:
        raise ContextError(400, "set must be an object of key -> string or null")
    for key, value in changes.items():
        if not isinstance(key, str) or not _KEY_RE.match(key):
            raise ContextError(400, f"bad key: {str(key)[:90]}")
        if value is not None and not isinstance(value, str):
            raise ContextError(400, f"value for {key} must be a string or null")
    with _LOCK:
        is_new = not _path(context_id).is_file()
        if is_new and any(v is not None for v in changes.values()) and _count() >= MAX_CONTEXTS:
            raise ContextError(507, "the server is holding too much saved progress; try again later")
        items = load(context_id)
        for key, value in changes.items():
            if value is None:
                items.pop(key, None)
            else:
                items[key] = value
        if len(items) > MAX_KEYS:
            raise ContextError(413, "too many saved items")
        if sum(len(k) + len(v.encode("utf-8")) for k, v in items.items()) > MAX_CONTEXT_BYTES:
            raise ContextError(413, "saved progress is over 3 MB")
        _write(context_id, items)
        return len(items)


def forget(context_id: str) -> None:
    if valid_id(context_id):
        with _LOCK:
            _path(context_id).unlink(missing_ok=True)


def _count() -> int:
    try:
        return sum(1 for _ in context_dir().glob("*.json"))
    except OSError:
        return 0


def sweep(now: float | None = None) -> int:
    """Delete contexts untouched for RETENTION_DAYS (and stray temp files); return how many went."""
    cutoff = (now if now is not None else time.time()) - RETENTION_DAYS * 86400
    gone = 0
    with _LOCK:
        for path in list(context_dir().glob("*.json")) + list(context_dir().glob("*.tmp")):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
                    gone += 1
            except OSError:
                continue
    return gone


def start_sweeper() -> threading.Thread:
    def loop() -> None:
        stop = threading.Event()
        while True:
            try:
                gone = sweep()
                if gone:
                    print(f"context sweep: {gone} saved progress files older than {RETENTION_DAYS} days deleted")
            except Exception as error:  # the type only
                print(f"context sweep failed: {type(error).__name__}")
            stop.wait(SWEEP_SECONDS)

    thread = threading.Thread(target=loop, name="context-sweeper", daemon=True)
    thread.start()
    return thread
