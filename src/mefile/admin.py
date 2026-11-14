# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# admin - the operator's console behind the team gate: health, the consent ledger, data on the box, settings, purges

"""
The operator's console (docs/team-hub-contract.md, "Admin")
===========================================================

``/admin`` sits behind the SAME gate as ``/team``: the team cookie, ``LUMIN8R_TEAM_CODE``, and the
503 on a box (``LUMIN8R_REQUIRE_TEAM_CODE=1``) with no code set. Sign-in itself stays
``/api/team/login``; this module only reads the gate (``team.gate_mode`` / ``team.signed_in``).

What it never does:
- return a secret. Keys are reported as set / not set; the team code, API keys and consent tokens
  (raw or hashed) never leave the process. ``MEFILE_JUDGE_MODEL`` is a model name, not a secret,
  so its value is shown.
- edit or delete the consent ledger. It is the record; the console reads it and exports it with
  every token hash removed, and every purge leaves it in place.
- delete outside the configured people folder (``MEFILE_PEOPLE_DIR``) and data folder
  (``LUMIN8R_DATA``). Each target is a direct child of one of those folders, checked after resolving;
  a symbolic link is removed as a link, never followed; a target that is, or holds, the ledger
  folder is refused.

Settings are read-only here. The page shows the exact command that changes each one on the box,
because every change to a running box goes through ``update-lumin8r`` (a key with ``--set-key``,
a setting through ``/etc/lumin8r/update.env``), never through a web form.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import time
from pathlib import Path

from . import shares, team
from .team import PERSON_CODE, Reply, Request, TeamError

STARTED_AT = dt.datetime.now(dt.timezone.utc)
_STARTED_MONOTONIC = time.monotonic()

KEY_NAMES = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_AGENT_ID", "LUMIN8R_TEAM_CODE")
UPDATE_ENV = "/etc/lumin8r/update.env"
PURGE_SCOPES = ("people", "outputs", "final")
FINAL_EVALUATION_FILES = ("evaluations.json", "evaluations.md")  # written to DATA/team by the final judge

# Every setting the console lists: (name, kind, default, secret, what it does). kind "key" changes with
# update-lumin8r --set-key; "update" through update.env; "box" is set by update-lumin8r itself.
SETTINGS = (
    ("ANTHROPIC_API_KEY", "key", None, True, "Claude API: your understudy, LLM A through the API, the judge."),
    ("MEFILE_JUDGE_MODEL", "key", None, False, "The judge's model. Must differ from the LLM A model under test."),
    ("OPENAI_API_KEY", "key", None, True, "OpenAI API: LLM B (GPT) through the API instead of pasting. Needs MEFILE_LLM_B_MODEL too."),
    ("MEFILE_LLM_B_MODEL", "update", None, False, "LLM B's OpenAI model id, exactly as OpenAI lists it. No default: unset keeps LLM B on paste."),
    ("MEFILE_LLM_B_EFFORT", "update", "medium", False, "LLM B's reasoning effort through the API."),
    ("ELEVENLABS_API_KEY", "key", None, True, "ElevenLabs: the voice interview."),
    ("ELEVENLABS_AGENT_ID", "key", None, True, "ElevenLabs: which voice agent runs the interview."),
    ("LUMIN8R_TEAM_CODE", "key", None, True, "The team code that opens the team hub, the paste station and this console."),
    ("LUMIN8R_HOST", "update", "microverse.cloud", False, "The public host name the edge serves."),
    ("LUMIN8R_PORT", "update", "8097", False, "The loopback port the service answers on."),
    ("MEFILE_VARIANTS", "update", "evidence_first,trait_first,short", False, "The me.md variants the experiment compares."),
    ("LUMIN8R_TEAM_NAME", "update", "TEAM", False, "The team prefix on final run IDs and the submission file name."),
    ("LUMIN8R_FINAL_VARIANT", "update", "evidence_first", False, "The me.md variant the final uses."),
    ("LUMIN8R_WORKBENCH", "update", "", False, "1 turns on the hackathon workbench (/workbench, /paste, the team API); off by default."),
    ("LUMIN8R_RELEASE", "box", "unknown", False, "The live release; set by update-lumin8r on every update."),
    ("LUMIN8R_DATA", "box", "private", False, "Where results, the final and team files live."),
    ("MEFILE_PEOPLE_DIR", "box", "private/people", False, "Where each person's kit and pasted runs live."),
    ("MEFILE_CONSENT_DIR", "box", "consent", False, "Where the append-only consent ledger lives."),
    ("LUMIN8R_REQUIRE_TEAM_CODE", "box", "", False, "1 on a box: team routes answer 503 until a team code is set."),
)


# ---------------------------------------------------------------------------
# Small readers
# ---------------------------------------------------------------------------


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _iso(timestamp: float) -> str:
    return dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _person_folders() -> list[Path]:
    root = team.people_dir()
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and not p.is_symlink() and PERSON_CODE.fullmatch(p.name))


def _pasted(folder: Path, model: str) -> tuple[int, list[str]]:
    """How many runs are saved for one model, and every model name the chat window showed for them."""
    from .experiment import pasted_responses
    try:
        count = len(pasted_responses(folder, model))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        count = 0
    data = _read_json(folder / f"llm_{model.lower()}.json")
    shown: list[str] = []
    for record in (data or {}).get("responses", []) if isinstance(data, dict) else []:
        value = record.get("model_shown") if isinstance(record, dict) else None
        if isinstance(value, str) and value and value not in shown:
            shown.append(value)
    return count, shown


def _ledger_path(ledger_dir: Path) -> Path:
    return Path(ledger_dir) / "ledger.jsonl"


def _ledger_entries(ledger_dir: Path) -> tuple[list[dict], int]:
    """Every readable ledger entry in order, and how many lines could not be read as a JSON object."""
    path = _ledger_path(ledger_dir)
    if not path.is_file():
        return [], 0
    entries, unreadable = [], 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            unreadable += 1
            continue
        if isinstance(entry, dict):
            entries.append(entry)
        else:
            unreadable += 1
    return entries, unreadable


def _without_token_hashes(entry: dict) -> dict:
    """The entry with every token hash removed (consent's token_sha256, withdrawal's revoked_token_sha256)."""
    return {key: value for key, value in entry.items() if not key.endswith("token_sha256")}


# ---------------------------------------------------------------------------
# 1 Health
# ---------------------------------------------------------------------------


def _judge_status() -> tuple[bool, str]:
    """Whether the judge would construct (a key, and a judge model distinct from LLM A), and why not."""
    if not _env("ANTHROPIC_API_KEY"):
        return False, "no ANTHROPIC_API_KEY"
    from .judge.anthropic_backend import AnthropicJudgeBackend, JudgeConfigError
    try:
        AnthropicJudgeBackend()  # constructs only: the client is created lazily, nothing goes over the wire
    except JudgeConfigError as error:
        return False, str(error)
    return True, ""


def _llm_b_api() -> dict:
    """LLM B through the OpenAI API: configured or not, the model id and effort (names, never the key)."""
    from . import openai_runner
    state = openai_runner.status()
    return {"configured": state["configured"], "model": state["model"], "effort": state["effort"], "missing": state["missing"]}


def consent_summary(ledger_dir: Path) -> dict:
    entries, unreadable = _ledger_entries(ledger_dir)
    people: dict[str, dict] = {}
    for entry in entries:
        person_id = str(entry.get("person_id", ""))
        at = str(entry.get("at", ""))
        record = people.setdefault(person_id, {"person_id": person_id, "state": "active", "purposes": [], "ai_services": [],
                                               "share_with": [], "first_at": at, "last_at": at, "events": 0})
        record["events"] += 1
        if at and (not record["first_at"] or at < record["first_at"]):
            record["first_at"] = at
        if at and at >= record["last_at"]:
            record["last_at"] = at
        event = entry.get("event")
        if event == "consent":
            record["state"] = "active"
            for key in ("purposes", "ai_services", "share_with"):
                value = entry.get(key)
                record[key] = [str(v) for v in value] if isinstance(value, list) else []
        elif event == "withdrawal":
            record["state"] = "withdrawn"
    ordered = sorted(people.values(), key=lambda r: r["last_at"], reverse=True)
    return {"people": ordered, "entries_total": len(entries), "unreadable_lines": unreadable,
            "ledger": str(_ledger_path(ledger_dir).resolve())}


def overview(ledger_dir: Path) -> dict:
    from . import voice
    judge_ready, judge_note = _judge_status()
    consent = consent_summary(ledger_dir)
    folders = _person_folders()
    pasted_a = pasted_b = 0
    people = 0
    for folder in folders:
        if (folder / "build.json").exists() or (folder / "test.json").exists():
            people += 1
        pasted_a += _pasted(folder, "A")[0]
        pasted_b += _pasted(folder, "B")[0]
    final = _read_json(team.final_dir() / "responses.json")
    final_responses = sum(1 for r in (final or {}).get("responses", []) if isinstance(r, dict) and str(r.get("text", "")).strip()) \
        if isinstance(final, dict) else 0
    return {
        "release": _env("LUMIN8R_RELEASE") or "unknown",
        "host": _env("LUMIN8R_HOST"),
        "started_at": STARTED_AT.isoformat(timespec="seconds"),
        "uptime_seconds": int(time.monotonic() - _STARTED_MONOTONIC),
        "keys": {name: bool(_env(name)) for name in KEY_NAMES},
        "judge_model": _env("MEFILE_JUDGE_MODEL") or None,
        "judge_ready": judge_ready,
        "judge_note": judge_note,
        "twin_ready": bool(_env("ANTHROPIC_API_KEY")),
        "voice_ready": voice.configured(),
        "llm_b_api": _llm_b_api(),
        "settings": {
            "variants": team.variants(),
            "team_name": team.team_name(),
            "final_variant": team.final_variant(),
            "people_dir": str(team.people_dir().resolve()),
            "data_dir": str(team.data_dir().resolve()),
            "consent_dir": str(Path(ledger_dir).resolve()),
            "require_team_code": os.environ.get("LUMIN8R_REQUIRE_TEAM_CODE") == "1",
        },
        "counts": {
            "people": people,
            "consents_active": sum(1 for p in consent["people"] if p["state"] == "active"),
            "consents_withdrawn": sum(1 for p in consent["people"] if p["state"] == "withdrawn"),
            "pasted_runs_A": pasted_a,
            "pasted_runs_B": pasted_b,
            "final_responses": final_responses,
            "evaluations_ready": (team.team_dir() / "evaluations.json").exists(),
        },
    }


# ---------------------------------------------------------------------------
# 2 Consent
# ---------------------------------------------------------------------------


def consent_export(ledger_dir: Path) -> Reply:
    entries, unreadable = _ledger_entries(ledger_dir)
    lines = [json.dumps(_without_token_hashes(entry), ensure_ascii=False) for entry in entries]
    body = ("\n".join(lines) + "\n" if lines else "").encode("utf-8")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    return Reply(200, body=body, content_type="application/x-ndjson; charset=utf-8",
                 headers={"Content-Disposition": f'attachment; filename="lumin8r-consent-ledger-{stamp}.ndjson"',
                          "X-Lumin8r-Unreadable-Lines": str(unreadable)})


# ---------------------------------------------------------------------------
# 3 Data on the box
# ---------------------------------------------------------------------------


def _footprint(folder: Path) -> tuple[int, float]:
    """Bytes on disk and the latest modification time under a folder (links are not followed)."""
    total, latest = 0, 0.0
    for path in [folder, *folder.rglob("*")]:
        try:
            stat = path.lstat()
        except OSError:
            continue
        if not path.is_dir() or path.is_symlink():
            total += stat.st_size
        latest = max(latest, stat.st_mtime)
    return total, latest


def list_people() -> dict:
    people = []
    for folder in _person_folders():
        build = _read_json(folder / "build.json") if (folder / "build.json").exists() else None
        minutes = build.get("kit_minutes") if isinstance(build, dict) else None
        count_a, shown_a = _pasted(folder, "A")
        count_b, shown_b = _pasted(folder, "B")
        size, latest = _footprint(folder)
        people.append({
            "code": folder.name,
            "has_build": (folder / "build.json").exists(),
            "has_test": (folder / "test.json").exists(),
            "kit_minutes": minutes if isinstance(minutes, (int, float)) and not isinstance(minutes, bool) else None,
            "pasted": {"A": count_a, "B": count_b},
            "model_shown": {"A": shown_a, "B": shown_b},
            "voice_transcript": (folder / "voice_transcript.json").exists(),
            "bytes": size,
            "last_modified": _iso(latest) if latest else None,
        })
    return {"people": people, "people_dir": str(team.people_dir().resolve()),
            "total_bytes": sum(p["bytes"] for p in people)}


def delete_person(body: dict) -> dict:
    return team.delete_person(body)  # validates the code and keeps the folder inside the people dir


def _contains(outer: Path, inner: Path) -> bool:
    return inner == outer or outer in inner.parents


def _children(folder: Path, skip: tuple[str, ...] = ()) -> list[Path]:
    if not folder.is_dir() or folder.is_symlink():
        return []
    return sorted(p for p in folder.iterdir() if p.name not in skip)


def _purge_targets(scope: str) -> tuple[Path, list[Path]]:
    """The root a scope deletes inside, and its targets (direct children of folders inside that root)."""
    data = team.data_dir()
    team_folder = team.team_dir()
    if scope == "people":
        return team.people_dir(), _children(team.people_dir())
    if scope == "outputs":
        return data, _children(team_folder, FINAL_EVALUATION_FILES) + _children(data / "experiment")
    return data, _children(team.final_dir()) + [team_folder / name for name in FINAL_EVALUATION_FILES
                                                 if (team_folder / name).exists() or (team_folder / name).is_symlink()]


def _display(path: Path) -> str:
    for base in (team.data_dir().resolve(), team.people_dir().resolve().parent):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.name


def purge(body: dict, ledger_dir: Path) -> dict:
    scope = body.get("scope")
    if scope not in PURGE_SCOPES:
        raise TeamError(400, f"scope must be one of: {', '.join(PURGE_SCOPES)}")
    phrase = "DELETE " + scope.upper()
    if body.get("confirm") != phrase:
        raise TeamError(400, f'type exactly "{phrase}" to confirm; nothing was deleted')
    root, targets = _purge_targets(scope)
    root_resolved = root.resolve()
    ledger = Path(ledger_dir).resolve()
    if root_resolved == Path(root_resolved.anchor) or root_resolved == Path.home().resolve():
        raise TeamError(409, f"refusing to purge inside {root_resolved}: point the folder at the app's own data")
    if scope == "people" and _contains(root_resolved, team.data_dir().resolve()):
        raise TeamError(409, "the people folder holds the data folder; refusing to purge it as people")
    deleted: list[str] = []
    with team._WRITE_LOCK:
        for target in targets:
            parent = target.parent.resolve()
            if not _contains(root_resolved, parent):
                raise TeamError(400, "refusing a path outside the configured folders")
            absolute = parent / target.name
            if target.is_symlink():
                if _contains(absolute, ledger):
                    continue
                target.unlink()
                deleted.append(_display(absolute))
                continue
            resolved = target.resolve()
            if resolved.parent != parent or not _contains(root_resolved, resolved):
                raise TeamError(400, "refusing a path outside the configured folders")
            if _contains(resolved, ledger):
                continue  # the ledger is the record: never deleted, whatever folder it shares
            if resolved.is_dir():
                shutil.rmtree(resolved)
            elif resolved.exists():
                resolved.unlink()
            else:
                continue
            deleted.append(_display(resolved))
    return {"scope": scope, "deleted": deleted, "kept_consent_ledger": True}


# ---------------------------------------------------------------------------
# 4 Settings
# ---------------------------------------------------------------------------


def _single_quoted(text: str) -> str:
    return "'" + text.replace("'", "'\"'\"'") + "'"


def _update_command(name: str, value: str) -> str:
    import shlex
    line = f"{name}={shlex.quote(value)}"  # update.env is sourced by bash, so the value is quoted for it
    return f"echo {_single_quoted(line)} | sudo tee -a {UPDATE_ENV} && sudo update-lumin8r"


def settings() -> dict:
    rows = []
    for name, kind, default, secret, about in SETTINGS:
        current = _env(name)
        row = {"name": name, "kind": kind, "secret": secret, "set": bool(current), "about": about,
               "value": None if secret else (current or None), "default": default}
        if kind == "key":
            row["command"] = f"sudo update-lumin8r --set-key {name}"
        elif kind == "update":
            row["command"] = _update_command(name, current or default or "")
        else:
            row["command"] = None
        rows.append(row)
    return {"settings": rows, "update_env": UPDATE_ENV}


# ---------------------------------------------------------------------------
# Routing (the team gate, then dispatch)
# ---------------------------------------------------------------------------


def is_admin_path(path: str) -> bool:
    return path.startswith("/api/admin/")


def handle(request: Request, ledger_dir: Path, ledger: shares.Ledger | None = None) -> Reply:
    """Every /api/admin/* route: the team gate first, then dispatch. Errors become JSON; no body or secret is echoed.

    ``ledger`` appends one consent-ledger entry (``app._ledger_append``); the operator's share revoke writes through it."""
    try:
        if team.gate_mode() == "unconfigured":
            return Reply(503, {"error": team.UNCONFIGURED_MESSAGE})
        if not team.signed_in(request):
            return Reply(401, {"error": team.SIGN_IN_MESSAGE})
        return _dispatch(request, Path(ledger_dir), ledger)
    except TeamError as error:
        return Reply(error.status, {"error": error.message, **error.extra})
    except shares.ShareError as error:
        return Reply(error.status, {"error": error.message})
    except Exception as error:  # the reason's type only
        return Reply(500, {"error": f"admin route failed: {type(error).__name__}"})


def _dispatch(request: Request, ledger_dir: Path, ledger: shares.Ledger | None = None) -> Reply:
    method, path = request.method, request.path
    if method == "GET":
        if path == "/api/admin/overview":
            return Reply(200, overview(ledger_dir))
        if path == "/api/admin/consent":
            return Reply(200, consent_summary(ledger_dir))
        if path == "/api/admin/consent/export":
            return consent_export(ledger_dir)
        if path == "/api/admin/people":
            return Reply(200, list_people())
        if path == "/api/admin/settings":
            return Reply(200, settings())
        if path == "/api/admin/shares":
            return Reply(200, shares.admin_listing())
    if method == "POST":
        if path == "/api/admin/people/delete":
            return Reply(200, delete_person(request.body))
        if path == "/api/admin/purge":
            return Reply(200, purge(request.body, ledger_dir))
        if path == "/api/admin/shares/revoke":
            if ledger is None:
                raise TeamError(500, "share revoke needs the consent ledger")
            return Reply(200, shares.operator_revoke(request.body.get("id"), ledger))
    return Reply(404, {"error": "not found"})
