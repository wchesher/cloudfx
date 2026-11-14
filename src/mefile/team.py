# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# team - the team hub behind lumin8r: the team-code gate, people, paste station, experiment, final, docs

"""
The team hub (docs/team-hub-contract.md is the spec)
====================================================

Everything here is team tooling over consenting teammates' data on disk; a person's own session
(consent, convert, understudy, voice) stays in ``app.py`` and never passes through this module.

The switch. All of it is the hackathon workbench, off unless ``LUMIN8R_WORKBENCH=1``: while off,
``/paste``, ``/api/station/*`` and every ``/api/team/*`` route answer 404 ``{"error": "not available"}``
except sign-in (``login``, ``logout``, ``me``), which ``/admin`` shares.

The gate. ``LUMIN8R_TEAM_CODE`` is the shared code. ``POST /api/team/login`` compares it in constant
time and sets ``lumin8r_team=<HMAC-SHA256 of the code under a per-process random key>``, so a
restart (or a new code) signs everyone out and the cookie never carries the code. Five wrong codes
from one client address inside ten minutes answer 429 until the window passes. With no code set,
a box (``LUMIN8R_REQUIRE_TEAM_CODE=1``, set by update-lumin8r's unit) answers 503 on every team
route, and a laptop runs open (``mode: "local"``).

Paths. Every path component that comes from a request is checked against a strict pattern before
it touches the file system, then resolved and checked to stay inside its folder. Request bodies
are never logged.

Storage. ``LUMIN8R_DATA`` (default ``./private``) holds ``team/`` (results, evaluations, rating
sheet; ``team/keys/`` holds the rating-sheet key, which is not servable) and ``final/`` (the
freeze-day inputs and answers). People live in ``MEFILE_PEOPLE_DIR`` (default ``private/people``).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import io
import json
import os
import random
import re
import secrets
import shutil
import threading
import time
import zipfile
from collections import deque
from dataclasses import dataclass, field
from http.cookies import CookieError, SimpleCookie
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs

from . import kit
from .answers import Answers, Question, Response, load_answers, load_questions, parse_answers, parse_questions, parse_responses
from .converter import convert

STATIC = Path(__file__).parent / "static"
REPOSITORY = Path(__file__).resolve().parents[2]
EXAMPLES = REPOSITORY / "examples"
DOCS = REPOSITORY / "docs"

COOKIE_NAME = "lumin8r_team"
LOGIN_FAILURE_LIMIT = 5
LOGIN_WINDOW_SECONDS = 600
UNCONFIGURED_MESSAGE = "team code not set on this box: update-lumin8r --set-key LUMIN8R_TEAM_CODE"
SIGN_IN_MESSAGE = "team sign-in required"

PERSON_CODE = re.compile(r"[A-Za-z0-9_-]{2,32}")
FILE_NAME = re.compile(r"[A-Za-z0-9._-]+")
QUESTION_ID = re.compile(r"[A-Za-z0-9]+")
DOC_ALLOWLIST = ("strategy", "pitch", "risk-and-acceptance", "market-research", "frameworks-and-wethos", "judge", "voice-intake", "alternative-intake")
MODEL_SHOWN_LIMIT = 120
PASTE_LOADING = "new chat, memory and custom instructions off; me.md as message 1, question as message 2"
PASTE_LOADING_NO_PROFILE = "new chat, memory and custom instructions off; question as the only message"
API_LOADING = "Claude API (runner.ask): me.md as message 1, question as message 2; a fresh conversation per run"
API_LOADING_NO_PROFILE = "Claude API (runner.ask): question as the only message; a fresh conversation per run"
OPENAI_LOADING = ("OpenAI Responses API (openai_runner.ask): me.md as message 1, question as message 2; a fresh "
                  "conversation per run, no instructions, store false")
OPENAI_LOADING_NO_PROFILE = ("OpenAI Responses API (openai_runner.ask): question as the only message; a fresh "
                             "conversation per run, no instructions, store false")
FILE_TYPES = {"html": "text/html", "json": "application/json", "md": "text/markdown", "txt": "text/plain",
              "csv": "text/csv", "zip": "application/zip"}

_PROCESS_KEY = secrets.token_bytes(32)  # signs the team cookie; a restart signs everyone out
_LOGIN_FAILURES: dict[str, deque] = {}
_LOGIN_LOCK = threading.Lock()
_WRITE_LOCK = threading.Lock()  # one writer at a time for the JSON files the hub rewrites


# ---------------------------------------------------------------------------
# Settings (read per request, so the environment of the running process is the only source)
# ---------------------------------------------------------------------------


def data_dir() -> Path:
    return Path(os.environ.get("LUMIN8R_DATA", "private"))


def team_dir() -> Path:
    return data_dir() / "team"


def final_dir() -> Path:
    return data_dir() / "final"


def people_dir() -> Path:
    return Path(os.environ.get("MEFILE_PEOPLE_DIR", "private/people"))


def questions_file() -> Path:
    return Path(os.environ.get("MEFILE_QUESTIONS", str(EXAMPLES / "example_questions.json")))


def variants() -> list[str]:
    return [v for v in os.environ.get("MEFILE_VARIANTS", "evidence_first,trait_first,short").split(",") if v]


def team_name() -> str:
    return os.environ.get("LUMIN8R_TEAM_NAME", "TEAM") or "TEAM"


def final_variant() -> str:
    return os.environ.get("LUMIN8R_FINAL_VARIANT", "evidence_first") or "evidence_first"


# ---------------------------------------------------------------------------
# Replies and errors
# ---------------------------------------------------------------------------


@dataclass
class Request:
    method: str
    path: str
    query: str = ""
    body: dict = field(default_factory=dict)
    cookie_header: str = ""
    client_address: str = ""
    https: bool = False


@dataclass
class Reply:
    status: int
    payload: Any = None
    body: bytes | None = None
    content_type: str = "application/json; charset=utf-8"
    headers: dict[str, str] = field(default_factory=dict)


class TeamError(Exception):
    def __init__(self, status: int, message: str, **extra):
        super().__init__(message)
        self.status = status
        self.message = message
        self.extra = extra


def _require(condition: bool, message: str, status: int = 400) -> None:
    if not condition:
        raise TeamError(status, message)


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def _team_code() -> str:
    return os.environ.get("LUMIN8R_TEAM_CODE", "").strip()


def _cookie_value(code: str) -> str:
    return hmac.new(_PROCESS_KEY, code.encode("utf-8"), hashlib.sha256).hexdigest()


def _presented_cookie(cookie_header: str) -> str:
    try:
        cookies = SimpleCookie(cookie_header or "")
    except CookieError:
        return ""
    morsel = cookies.get(COOKIE_NAME)
    return morsel.value if morsel else ""


def gate_mode() -> str:
    """'code' (a code is set), 'local' (no code, open laptop), 'unconfigured' (no code on a box)."""
    if _team_code():
        return "code"
    return "unconfigured" if os.environ.get("LUMIN8R_REQUIRE_TEAM_CODE") == "1" else "local"


def signed_in(request: Request) -> bool:
    mode = gate_mode()
    if mode == "local":
        return True
    if mode == "unconfigured":
        return False
    return hmac.compare_digest(_presented_cookie(request.cookie_header), _cookie_value(_team_code()))


def _recent_failures(address: str, now: float) -> deque:
    failures = _LOGIN_FAILURES.setdefault(address, deque())
    while failures and now - failures[0] > LOGIN_WINDOW_SECONDS:
        failures.popleft()
    return failures


def _login(request: Request) -> Reply:
    if gate_mode() == "local":
        return Reply(200, {"ok": True})
    now = time.monotonic()
    with _LOGIN_LOCK:
        failures = _recent_failures(request.client_address, now)
        if len(failures) >= LOGIN_FAILURE_LIMIT:
            wait = int(LOGIN_WINDOW_SECONDS - (now - failures[0])) + 1
            return Reply(429, {"error": f"too many wrong codes from this address; try again in {max(1, wait // 60)} minute(s)"},
                         headers={"Retry-After": str(wait)})
        presented = str(request.body.get("code", "")).strip()
        if not presented or not hmac.compare_digest(presented.encode("utf-8"), _team_code().encode("utf-8")):
            failures.append(now)
            return Reply(401, {"error": "wrong team code"})
        _LOGIN_FAILURES.pop(request.client_address, None)
    cookie = f"{COOKIE_NAME}={_cookie_value(_team_code())}; HttpOnly; SameSite=Strict; Path=/"
    if request.https:
        cookie += "; Secure"
    return Reply(200, {"ok": True}, headers={"Set-Cookie": cookie})


def _logout(request: Request) -> Reply:
    cookie = f"{COOKIE_NAME}=; Max-Age=0; HttpOnly; SameSite=Strict; Path=/"
    if request.https:
        cookie += "; Secure"
    return Reply(200, {"ok": True}, headers={"Set-Cookie": cookie})


def _me(request: Request) -> Reply:
    mode = gate_mode()
    return Reply(200, {"signed_in": signed_in(request), "mode": "local" if mode == "local" else "code"})


def is_team_path(path: str) -> bool:
    return path == "/paste" or path.startswith("/api/station/") or path.startswith("/api/team/")


def workbench_enabled() -> bool:
    """The hackathon workbench (/workbench, /paste, /api/station/*, the team API) is on only with LUMIN8R_WORKBENCH=1.

    Sign-in (/api/team/login, logout, me) stays available either way, because /admin uses the same sign-in."""
    return os.environ.get("LUMIN8R_WORKBENCH", "").strip().lower() in ("1", "true", "yes", "on")


NOT_AVAILABLE = "not available"
NOT_AVAILABLE_PAGE = (b"<!doctype html><html lang=en><meta charset=utf-8>"
                      b"<meta name=viewport content='width=device-width, initial-scale=1'>"
                      b"<title>Not found</title><main style='max-width:36rem;margin:4rem auto;padding:0 16px;font-family:system-ui'>"
                      b"<h1>This page is not here</h1><p><a href=/>Go to the home page</a></p></main></html>")


# ---------------------------------------------------------------------------
# Safe paths
# ---------------------------------------------------------------------------


def _inside(folder: Path, name: str, pattern: re.Pattern = FILE_NAME) -> Path:
    """folder/name, only when name is one safe component and the result stays inside folder."""
    _require(bool(pattern.fullmatch(name)) and name not in (".", "..") and not name.startswith("."), "bad name", 400)
    target = (folder / name).resolve()
    _require(target.parent == folder.resolve(), "bad name", 400)
    return target


def _person_folder(code: str) -> Path:
    _require(isinstance(code, str) and bool(PERSON_CODE.fullmatch(code)), "code must be 2-32 letters, digits, '_' or '-'")
    return _inside(people_dir(), code, PERSON_CODE)


def _read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".writing")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".writing")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


# ---------------------------------------------------------------------------
# Paste station (moved here from app.py; same behaviour, now team-gated)
# ---------------------------------------------------------------------------


def _people_folders(require_test: bool = True) -> list[Path]:
    root = people_dir()
    if not root.exists():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "build.json").exists()
                  and (not require_test or (p / "test.json").exists()))


def station_queue(model_filter: str | None) -> dict:
    """Every run the paste station needs: person x model x condition x question, with what to paste and what is saved."""
    from .experiment import pasted_responses
    questions = load_questions(questions_file())
    station_variants = variants()
    runs, profiles = [], {}
    for person_dir in _people_folders():
        build = load_answers(person_dir / "build.json")
        pid = build.person_id
        conditions = ["none"]
        for condition, markdown in _station_profiles(person_dir, build, station_variants):
            profiles[f"{pid}/{condition}"] = markdown
            conditions.append(condition)
        for model in ("A", "B"):
            if model_filter and model != model_filter:
                continue
            saved = pasted_responses(person_dir, model)
            for condition in conditions:
                for question_id, question in questions.items():
                    run_id = f"{pid}-{model}-{condition}-{question_id}"
                    runs.append({"run_id": run_id, "person": pid, "model": model, "condition": condition,
                                 "question_id": question_id, "type": question.type, "word_limit": question.word_limit,
                                 "profile_key": None if condition == "none" else f"{pid}/{condition}",
                                 "question": question.prompt, "answer": saved.get(run_id, "")})
    return {"runs": runs, "profiles": profiles, "people_dir": str(people_dir().resolve()), "variants": station_variants}


def _interview(person_dir: Path, pid: str) -> dict | None:
    """experiment.inspect_transcript for the person's voice_transcript.json, or None when there is none.

    The leakage guard needs the person's test.json; without it the transcript is reported but not used."""
    from .experiment import TRANSCRIPT_FILE, inspect_transcript
    path = person_dir / TRANSCRIPT_FILE
    if not path.exists():
        return None
    if not (person_dir / "test.json").exists():
        return {"evidence": None, "transcript": None, "leakage_guard": None,
                "problem": "no test.json yet, so the leakage guard cannot run; the transcript is not used"}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return {"evidence": None, "transcript": None, "leakage_guard": None,
                "problem": f"voice_transcript.json cannot be read: {type(error).__name__}"}
    return inspect_transcript(raw, pid, load_answers(person_dir / "test.json"))


def _station_profiles(person_dir: Path, build: Answers, station_variants: list[str]) -> list[tuple[str, str]]:
    """(condition, me.md) for every profile the station runs, in order: each variant, then its interview arm
    (<variant>_plus_interview) when the person has a usable transcript that passed the leakage guard."""
    from .experiment import INTERVIEW_SUFFIX
    interview = _interview(person_dir, build.person_id)
    evidence = interview["evidence"] if interview and not interview["problem"] else None
    found = []
    for variant in station_variants:
        profile = convert(build, variant=variant)
        if profile.gate.passed:
            found.append((variant, profile.markdown))
        if evidence is not None:
            with_interview = convert(build, variant=variant, voice=evidence)
            if with_interview.gate.passed:
                found.append((variant + INTERVIEW_SUFFIX, with_interview.markdown))
    return found


def _interview_view(interview: dict | None) -> dict | None:
    """What the hub shows per person: source, minutes, answers, guard result. Never transcript text."""
    if interview is None:
        return None
    guard = interview["leakage_guard"]
    transcript = interview["transcript"] or {}
    return {
        "present": True,
        "used": interview["evidence"] is not None and not interview["problem"],
        "source": transcript.get("source"),
        "interview_minutes": transcript.get("interview_minutes"),
        "employee_answers": transcript.get("employee_answers"),
        "leakage_guard": None if guard is None else ("passed" if guard["passed"] else "refused"),
        "leakage_hits": [] if guard is None else guard["test_ids_found"] + guard["quotes_found"],
        "problem": interview["problem"],
    }


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _model_shown(body: dict) -> str:
    """The model name the chat window displayed, as typed (optional; one line, capped)."""
    value = body.get("model_shown")
    if value is None:
        return ""
    _require(isinstance(value, str), "model_shown must be text")
    return " ".join(value.split())[:MODEL_SHOWN_LIMIT]


def _api_fields(api_record: dict, with_profile: bool) -> dict:
    """The provenance of one API run: source, served and requested model, effort, and the loading protocol used."""
    openai = api_record.get("provider") == "openai"
    if openai:
        loading = OPENAI_LOADING if with_profile else OPENAI_LOADING_NO_PROFILE
    else:
        loading = API_LOADING if with_profile else API_LOADING_NO_PROFILE
    fields = {"source": "api", "model_served": str(api_record.get("model_served") or ""), "loading": loading}
    for key in ("model_requested", "effort"):
        if api_record.get(key):
            fields[key] = str(api_record[key])
    return fields


def _has_text(records: list, run_id: str) -> bool:
    return any(isinstance(r, dict) and r.get("run_id") == run_id and str(r.get("text", "")).strip() for r in records)


def station_save(body: dict, api_record: dict | None = None, overwrite: bool = False) -> dict:
    """Save one pasted run. ``api_record`` ({model_served, model_requested, effort, provider}) is set only by run_missing,
    never by a request. An API answer never replaces a saved answer (a person's paste) unless ``overwrite`` is True."""
    run_id, text = str(body.get("run_id", "")), str(body.get("text", ""))
    match = re.fullmatch(r"(.+)-([AB])-([a-z_]+)-([A-Za-z0-9]+)", run_id)
    if not match:
        raise ValueError("bad run id")
    pid, model, condition, question_id = match.groups()
    model_shown = _model_shown(body)
    person_dir = next((p for p in _people_folders(require_test=False)
                       if json.loads((p / "build.json").read_text(encoding="utf-8")).get("person_id") == pid), None)
    if person_dir is None:
        raise ValueError("unknown person")
    path = person_dir / f"llm_{model.lower()}.json"
    with _WRITE_LOCK:
        data = _read_json(path, {"responses": []})
        if api_record is not None and not overwrite and _has_text(data.get("responses", []), run_id):
            return {"saved": False, "kept": True, "choice": None, "match": None}
        data["responses"] = [r for r in data.get("responses", []) if r.get("run_id") != run_id]
        if text.strip():
            record = {"run_id": run_id, "question_id": question_id, "text": text.strip()}
            if api_record is not None:
                record.update(_api_fields(api_record, condition != "none"))
            else:
                record["source"] = "paste"
                if model_shown:
                    record["model_shown"] = model_shown
                record["loading"] = PASTE_LOADING if condition != "none" else PASTE_LOADING_NO_PROFILE
            record["pasted_at"] = _now()
            data["responses"].append(record)
        _write_json(path, data)
    from .judge.features import parse_choice
    reference = None
    if (person_dir / "test.json").exists():
        reference = load_answers(person_dir / "test.json").scenarios.get(question_id, {}).get("choice")
    chosen = parse_choice(text)
    return {"saved": bool(text.strip()), "choice": chosen, "match": (chosen == reference) if (chosen and reference) else None}


def station_results() -> dict:
    from .experiment import run_experiment
    out = people_dir().parent / "experiment"
    result = run_experiment(people_dir(), load_questions(questions_file()), variants(), out, None)
    return {"summary": result["summary"], "results_md": str((out / "results.md").resolve())}


# ---------------------------------------------------------------------------
# People (step 1)
# ---------------------------------------------------------------------------


def _record_ids(data: dict) -> set[str]:
    """Every ID an organizer answer file names in items, scenarios and writing (skipped is not an answer)."""
    found: set[str] = set()
    for section in ("items", "scenarios", "writing"):
        for record in data.get(section) or []:
            if isinstance(record, dict) and str(record.get("id", "")).strip():
                found.add(str(record["id"]).strip())
    return found


def _check_build(build: Any) -> Answers:
    _require(isinstance(build, dict), "build must be an organizer answer file (a JSON object)")
    leaked = sorted(_record_ids(build) & kit.DEVELOPMENT_TEST_IDS)
    _require(not leaked, f"the build file contains held-out test answers ({', '.join(leaked)}); "
                         "upload them as the test file, never in the build")
    return parse_answers(build)


def _check_test(test: Any) -> Answers:
    _require(isinstance(test, dict), "test must be an organizer answer file (a JSON object)")
    build_ids = sorted(_record_ids(test) - kit.DEVELOPMENT_TEST_IDS)
    _require(not build_ids, f"the test file contains build answers ({', '.join(build_ids)}); "
                            f"it holds only {', '.join(sorted(kit.DEVELOPMENT_TEST_IDS))}")
    return parse_answers(test)


def list_people() -> dict:
    from .experiment import pasted_responses
    questions = load_questions(questions_file())
    station_variants = variants()
    root = people_dir()
    people = []
    folders = sorted(p for p in root.iterdir() if p.is_dir() and PERSON_CODE.fullmatch(p.name)) if root.exists() else []
    for folder in folders:
        has_build, has_test = (folder / "build.json").exists(), (folder / "test.json").exists()
        if not (has_build or has_test):
            continue
        problems: list[str] = []
        pasted = {"A": 0, "B": 0}
        total_runs = 0
        interview = None
        if has_build:
            try:
                build = load_answers(folder / "build.json")
            except (ValueError, OSError) as error:
                problems.append(f"build.json cannot be read: {type(error).__name__}")
                build = None
            if build is not None:
                problems = list(build.problems)
                interview = _interview(folder, build.person_id)
                conditions = ["none"] + [c for c, _ in _station_profiles(folder, build, station_variants)]
                expected = {f"{build.person_id}-{model}-{condition}-{question_id}"
                            for model in ("A", "B") for condition in conditions for question_id in questions}
                total_runs = len(expected)
                for model in ("A", "B"):
                    pasted[model] = sum(1 for run_id in pasted_responses(folder, model) if run_id in expected)
        people.append({"code": folder.name, "has_build": has_build, "has_test": has_test, "build_problems": problems,
                       "pasted": pasted, "total_runs": total_runs, "interview": _interview_view(interview)})
    return {"people": people, "variants": station_variants,
            "questions": [{"id": q.id, "type": q.type} for q in questions.values()], "llm_api": llm_api_status()}


def save_person(body: dict) -> dict:
    code = body.get("code")
    folder = _person_folder(code)
    build_data = body.get("build")
    build = _check_build(build_data)
    _require(str(build_data.get("person_id") or "").strip() == code, f"code {code!r} must equal the build file's person_id")
    test_data = body.get("test")
    test = None
    if test_data is not None:
        test = _check_test(test_data)
        _require(str(test_data.get("person_id") or "").strip() == code, f"code {code!r} must equal the test file's person_id")
    with _WRITE_LOCK:
        folder.mkdir(parents=True, exist_ok=True)
        _write_json(folder / "build.json", build_data)
        if test_data is not None:
            _write_json(folder / "test.json", test_data)
    problems = list(build.problems) + ([f"test: {p}" for p in test.problems] if test else [])
    return {"saved": True, "problems": problems}


def save_voice(body: dict) -> dict:
    """POST /api/team/voice {code, transcript}: put a reviewed interview transcript into a hub person's folder.

    The person must already have build.json and test.json (the leakage guard reads test.json). The transcript is
    validated with intake.parse_transcript, cut to the fields intake reads (text only), checked by the leakage guard,
    and written to <people>/<code>/voice_transcript.json. A guard trip is 400 with the turn and test ID, never the words.
    """
    from .experiment import TRANSCRIPT_FILE, clean_transcript, inspect_transcript
    code = body.get("code")
    folder = _person_folder(code)
    _require((folder / "build.json").exists(), f"no kit for {code} in the hub yet; add the person's build and test files first", 404)
    _require((folder / "test.json").exists(), f"{code} has no test.json yet; the leakage guard needs it before a transcript can be added")
    raw = body.get("transcript")
    _require(isinstance(raw, dict), "transcript must be the voice_transcript.json object")
    transcript = clean_transcript(raw)
    named = str(transcript.get("person_id") or "").strip()
    _require(not named or named == code, f"the transcript names person {named}, not {code}")
    transcript["person_id"] = code
    inspected = inspect_transcript(transcript, code, load_answers(folder / "test.json"))
    guard = inspected["leakage_guard"]
    if guard is not None and not guard["passed"]:
        raise TeamError(400, f"leakage guard refused the transcript: {inspected['problem']}. Remove those passages in review "
                             "and send it again.",
                        leakage_guard={"passed": False, "test_ids_found": guard["test_ids_found"],
                                       "quotes_found": guard["quotes_found"]})
    _require(not inspected["problem"], str(inspected["problem"]))
    _require(inspected["evidence"] is not None, "the transcript has no employee answers")
    with _WRITE_LOCK:
        _write_json(folder / TRANSCRIPT_FILE, transcript)
    return {"saved": True, "interview": _interview_view(inspected)}


def delete_person(body: dict) -> dict:
    folder = _person_folder(body.get("code"))
    _require(folder.is_dir(), "no such person", 404)
    with _WRITE_LOCK:
        shutil.rmtree(folder)
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Run, judge, results (steps 2-4)
# ---------------------------------------------------------------------------


def llm_api_status() -> dict:
    """Which models can answer through an API on this box, and as what model id. Never a key."""
    from . import openai_runner, runner
    llm_b = openai_runner.status()
    return {"A": {"configured": bool(os.environ.get("ANTHROPIC_API_KEY")), "model": runner.DEFAULT_MODEL,
                  "effort": runner.DEFAULT_EFFORT},
            "B": {"configured": llm_b["configured"], "model": llm_b["model"], "effort": llm_b["effort"]}}


def _require_api(model: str) -> None:
    """TeamError 503 when the model cannot answer through its API on this box."""
    if model == "A":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise TeamError(503, "running LLM A needs an Anthropic API key on the server (ANTHROPIC_API_KEY)")
        return
    from . import openai_runner
    missing = openai_runner.status()["missing"]
    if missing:
        raise TeamError(503, "LLM B by API is not configured on this box (" + ", ".join(missing) + " not set): "
                             f"{openai_runner.MODEL_MISSING_MESSAGE}, and sudo update-lumin8r --set-key OPENAI_API_KEY. "
                             "Paste LLM B at /paste?model=B meanwhile.")


def api_answerer_b() -> Callable[[str | None, Question], dict]:
    """LLM B through the OpenAI Responses API (openai_runner.ask, the same two-turn protocol). Tests replace this."""
    from . import openai_runner
    _, model, effort = openai_runner.require_settings(None, None)

    def answer(profile: str | None, question: Question) -> dict:
        return {**openai_runner.ask(profile, question, model, effort), "provider": "openai"}

    return answer


def _answerer_for(model: str) -> Callable[[str | None, Question], str | dict]:
    return api_answerer() if model == "A" else api_answerer_b()


def _reply_parts(reply: str | dict, model: str) -> tuple[str, dict]:
    """(text, api_record) from an answerer's reply; a plain string (the fake answerer) carries no provenance."""
    if isinstance(reply, dict):
        record = {key: reply.get(key) for key in ("model_served", "model_requested", "effort")}
        record["provider"] = reply.get("provider") or ("openai" if model == "B" else "anthropic")
        return str(reply.get("text", "")), record
    return str(reply), {"model_served": "", "provider": "openai" if model == "B" else "anthropic"}


def api_answerer() -> Callable[[str | None, Question], str | dict]:
    """LLM A through the Claude API (runner.ask, the two-turn loading protocol). Tests replace this function.

    The answerer returns runner.ask's record (text plus model_served), so the served model is kept per run; a
    plain string is accepted too (the fake answerer)."""
    import anthropic

    from . import runner
    client = anthropic.Anthropic()

    def answer(profile: str | None, question: Question) -> dict:
        return runner.ask(client, profile, question, runner.DEFAULT_MODEL, runner.DEFAULT_EFFORT)

    return answer


def judge_backend():
    """The real judge, or TeamError 503 when it cannot run honestly. Tests replace this function."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise TeamError(503, "the judge needs an Anthropic API key on the server (ANTHROPIC_API_KEY)")
    from .judge.anthropic_backend import AnthropicJudgeBackend, JudgeConfigError
    try:
        return AnthropicJudgeBackend()
    except JudgeConfigError as error:
        raise TeamError(503, str(error)) from error


def _overwrite_flag(body: dict) -> bool:
    value = body.get("overwrite", False)
    _require(isinstance(value, bool), "overwrite must be true or false")
    return value


def run_missing(body: dict) -> dict:
    """POST /api/team/run {model: "A"|"B", overwrite?}: answer every run with no saved answer through the model's API.

    LLM A runs on the Claude API, LLM B on the OpenAI API, both with the two-turn loading protocol, and the answers land
    in the files the paste station writes (llm_a.json / llm_b.json). A saved answer (a person's paste) is kept unless
    ``overwrite`` is true."""
    model = body.get("model", "A")
    _require(model in ("A", "B"), "model must be A or B")
    overwrite = _overwrite_flag(body)
    _require_api(model)
    queue = station_queue(model)
    todo = [run for run in queue["runs"] if overwrite or not run["answer"]]
    if not todo:
        return {"answered": 0, "kept": 0, "errors": []}
    answer = _answerer_for(model)
    questions = load_questions(questions_file())
    answered, kept, errors = 0, 0, []
    for run in todo:
        profile = queue["profiles"].get(run["profile_key"]) if run["profile_key"] else None
        try:
            text, record = _reply_parts(answer(profile, questions[run["question_id"]]), model)
            if not text.strip():
                raise RuntimeError("empty answer")
            saved = station_save({"run_id": run["run_id"], "text": text}, api_record=record, overwrite=overwrite)
            if saved.get("kept"):
                kept += 1  # a person pasted this run while the API was answering: theirs stays
            else:
                answered += 1
        except Exception as error:  # report the reason, never the key or the body
            errors.append(f"{run['run_id']}: {type(error).__name__}: {str(error)[:200]}")
    return {"answered": answered, "kept": kept, "errors": errors}


def run_team_experiment(body: dict) -> dict:
    from .experiment import recompare, render_comparison, render_markdown, run_experiment, summarize
    from .judge.judge import judge_responses
    backend = judge_backend() if body.get("judge") else None
    questions = load_questions(questions_file())
    experiment_variants = variants()
    out = team_dir() / "experiment"
    try:
        result = run_experiment(people_dir(), questions, experiment_variants, out, None, None)
    except RuntimeError as error:
        raise TeamError(400, str(error)) from error
    rows = result["rows"]
    evaluations: list[dict] = []
    if backend is not None and rows:
        folders = {load_answers(p / "build.json").person_id: p for p in _people_folders()}
        for pid in sorted({row["person"] for row in rows}):
            folder = folders[pid]
            person_rows = [row for row in rows if row["person"] == pid]
            verdicts = judge_responses(load_answers(folder / "build.json"), questions, load_answers(folder / "test.json"),
                                       [Response(r["run_id"], r["question_id"], r["text"]) for r in person_rows], backend)
            by_run = {e["run_id"]: e for e in verdicts["evaluations"]}
            evaluations.extend(verdicts["evaluations"])
            for row in person_rows:
                evaluation = by_run.get(row["run_id"], {})
                row["judge_status"] = evaluation.get("status")
                row["resemblance"] = (evaluation.get("reference_resemblance") or {}).get("score")
                row["generic"] = (evaluation.get("generic_writing") or {}).get("is_generic")
    summary = summarize(rows)
    results_md = render_markdown(summary, rows, experiment_variants)
    comparison = None
    if "comparison" in result:  # a person has an interview transcript: kit only vs kit plus interview, judged
        comparison = recompare(result["comparison"], rows, experiment_variants)
        comparison_md = render_comparison(comparison)
        results_md += "\n" + comparison_md.replace("# Alternative intake", "## Alternative intake", 1)
    with _WRITE_LOCK:
        _write_json(out / "results.json", {"summary": summary, "rows": rows, **({"comparison": comparison} if comparison else {})})
        _write_text(out / "results.md", results_md)
        _write_json(team_dir() / "results.json", {"summary": summary, "results_md": results_md,
                                                  **({"comparison": comparison} if comparison else {})})
        _write_text(team_dir() / "results.md", results_md)
        if comparison is not None:
            _write_json(out / "comparison.json", comparison)
            _write_text(out / "comparison.md", comparison_md)
        if backend is not None:
            _write_json(team_dir() / "experiment_evaluations.json", {"evaluations": evaluations})
    return {"summary": summary, "results_md": results_md, **({"comparison": comparison} if comparison else {})}


def last_results() -> dict:
    data = _read_json(team_dir() / "results.json", None)
    if not isinstance(data, dict):
        return {"summary": [], "results_md": ""}
    return {"summary": data.get("summary", []), "results_md": data.get("results_md", "")}


def _rating_sources() -> list[tuple[list[Response], Answers]]:
    """(responses, the person's held-out answers) for every person's pasted runs and, once judged, the final runs."""
    from .experiment import pasted_responses
    sources = []
    for folder in _people_folders():
        responses = []
        for model in ("A", "B"):
            for run_id, text in pasted_responses(folder, model).items():
                responses.append(Response(run_id, run_id.rsplit("-", 1)[-1], text))
        if responses:
            sources.append((responses, load_answers(folder / "test.json")))
    final_test = final_dir() / "test.json"
    if final_test.exists():
        final = [r for r in _final_responses() if r.text.strip()]
        final += parse_responses(_read_json(final_dir() / "comparisons.json", {}))
        if final:
            sources.append((final, load_answers(final_test)))
    return sources


def build_ratesheet() -> dict:
    from .judge.agreement import build_items, render_ratesheet
    questions = load_questions(questions_file())
    final_questions = final_dir() / "questions.json"
    if final_questions.exists():
        questions = {**questions, **load_questions(final_questions)}
    pooled: list[tuple[str, dict]] = []
    for responses, reference in _rating_sources():
        try:
            items, key, _ = build_items(responses, questions, reference, seed=0)
        except ValueError as error:
            raise TeamError(400, str(error)) from error
        pooled.extend((key[item["item_id"]], item) for item in items)
    _require(bool(pooled), "no pasted responses with a recorded answer to rate yet", 409)
    random.Random(0).shuffle(pooled)
    width = max(3, len(str(len(pooled))))
    items, key = [], {}
    for index, (run_id, item) in enumerate(pooled, start=1):
        item_id = f"item-{index:0{width}d}"
        key[item_id] = run_id
        items.append({**item, "item_id": item_id})
    with _WRITE_LOCK:
        _write_text(team_dir() / "ratesheet.html", render_ratesheet(items))
        _write_json(team_dir() / "keys" / "ratesheet_key.json", key)  # not servable: files serve one level only
    return {"url": "/api/team/files/ratesheet.html"}


def run_agreement(body: dict) -> dict:
    from .judge.agreement import compute_agreement, load_judge_scores, load_key, render_agreement_markdown
    ratings = body.get("ratings")
    _require(isinstance(ratings, list) and bool(ratings) and all(isinstance(r, dict) for r in ratings),
             "ratings must be a list of rating exports (JSON objects)")
    key_path = team_dir() / "keys" / "ratesheet_key.json"
    _require(key_path.exists(), "build the rating sheet first", 409)
    evaluation_paths = [p for p in (team_dir() / "experiment_evaluations.json", team_dir() / "evaluations.json") if p.exists()]
    _require(bool(evaluation_paths), "no judge evaluations yet: run the experiment with the judge, or judge the final", 409)
    key = load_key(key_path)
    raters = []
    for index, data in enumerate(ratings, start=1):
        scores, notes, unknown = {}, {}, []
        for record in data.get("ratings") or []:
            if not isinstance(record, dict):
                continue
            item_id = str(record.get("item_id", ""))
            if item_id not in key:
                unknown.append(item_id)
                continue
            score = record.get("score")
            if score is not None and (isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 4):
                raise TeamError(400, f"rater {index} {item_id}: score must be a whole number 0-4 or null")
            scores[item_id] = score
            notes[item_id] = str(record.get("note") or "").strip()
        raters.append({"name": str(data.get("rater") or "").strip() or f"rater {index}", "scores": scores,
                       "notes": notes, "unknown_items": unknown})
    result = compute_agreement(key, raters, load_judge_scores(evaluation_paths, key))
    agreement_md = render_agreement_markdown(result)
    with _WRITE_LOCK:
        _write_json(team_dir() / "agreement.json", result)
        _write_text(team_dir() / "agreement.md", agreement_md)
    return {"agreement_md": agreement_md}


def serve_team_file(name: str) -> Reply:
    target = _inside(team_dir(), name)
    _require(target.is_file(), "not found", 404)
    kind = FILE_TYPES.get(name.rsplit(".", 1)[-1].lower(), "application/octet-stream")
    if kind.startswith("text/") or kind == "application/json":
        kind += "; charset=utf-8"
    return Reply(200, body=target.read_bytes(), content_type=kind)


# ---------------------------------------------------------------------------
# Final (step 5)
# ---------------------------------------------------------------------------


def _final_questions() -> dict[str, Question]:
    path = final_dir() / "questions.json"
    return load_questions(path) if path.exists() else {}


def _final_runs(questions: dict[str, Question]) -> list[dict]:
    return [{"run_id": f"{team_name()}-{model}-{question_id}", "model": model, "question_id": question_id}
            for question_id in questions for model in ("A", "B")]


def _final_responses() -> list[Response]:
    return parse_responses(_read_json(final_dir() / "responses.json", {"responses": []}))


def _question_view(questions: dict[str, Question]) -> list[dict]:
    return [{"id": q.id, "type": q.type, "prompt": q.prompt, "word_limit": q.word_limit} for q in questions.values()]


def final_inputs(body: dict) -> dict:
    build_data = body.get("build")
    build = _check_build(build_data)
    questions_data = body.get("questions")
    _require(isinstance(questions_data, dict) and isinstance(questions_data.get("questions"), list),
             "questions must be a question file ({\"questions\": [...]})")
    try:
        questions = parse_questions(questions_data)
    except (KeyError, TypeError, ValueError) as error:
        raise TeamError(400, f"questions file cannot be read: {type(error).__name__}: {error}") from error
    _require(bool(questions), "the question file has no questions")
    bad = sorted(q for q in questions if not QUESTION_ID.fullmatch(q))
    _require(not bad, f"question IDs must be letters and digits only: {', '.join(bad)}")
    try:
        profile = convert(build, scope="full", variant=final_variant())
    except ValueError as error:
        raise TeamError(400, str(error)) from error
    gate = {"passed": profile.gate.passed, "blocking": profile.gate.blocking, "warnings": profile.gate.warnings}
    if not profile.gate.passed:
        raise TeamError(400, "claims gate refused the profile; nothing was saved", gate=gate)
    folder = final_dir()
    with _WRITE_LOCK:
        _write_json(folder / "build.json", build_data)
        _write_json(folder / "questions.json", questions_data)
        _write_text(folder / "me.md", profile.markdown)
        _write_json(folder / "me.json", profile.sidecar)
    return {"markdown": profile.markdown, "gate": gate, "problems": build.problems,
            "questions": _question_view(questions), "runs": _final_runs(questions)}


def final_state() -> dict:
    questions = _final_questions()
    me = final_dir() / "me.md"
    answers = {r.run_id: r.text for r in _final_responses()}
    return {"markdown": me.read_text(encoding="utf-8") if me.exists() else None,
            "questions": _question_view(questions),
            "runs": [{**run, "answer": answers.get(run["run_id"], "")} for run in _final_runs(questions)],
            "evaluations_ready": (team_dir() / "evaluations.json").exists(),
            "model_shown": _final_model_shown(), "llm_api": llm_api_status()}


def _final_model_shown() -> dict[str, str]:
    """The model name last typed for each final model (the most recent saved response that carries one)."""
    runs = {run["run_id"]: run["model"] for run in _final_runs(_final_questions())}
    latest: dict[str, tuple[str, str]] = {}
    for record in _read_json(final_dir() / "responses.json", {"responses": []}).get("responses", []):
        model, shown = runs.get(record.get("run_id")), str(record.get("model_shown") or "")
        if model and shown and str(record.get("pasted_at", "")) >= latest.get(model, ("", ""))[0]:
            latest[model] = (str(record.get("pasted_at", "")), shown)
    return {model: shown for model, (_, shown) in latest.items()}


def final_answer(body: dict) -> dict:
    run_id, text = str(body.get("run_id", "")), str(body.get("text", ""))
    model_shown = _model_shown(body)
    runs = {run["run_id"]: run for run in _final_runs(_final_questions())}
    _require(bool(runs), "save the final inputs first", 409)
    _require(run_id in runs, "unknown run id")
    path = final_dir() / "responses.json"
    with _WRITE_LOCK:
        data = _read_json(path, {"responses": []})
        data["responses"] = [r for r in data.get("responses", []) if r.get("run_id") != run_id]
        if text.strip():
            record = {"run_id": run_id, "question_id": runs[run_id]["question_id"], "text": text.strip()}
            if model_shown:
                record["model_shown"] = model_shown
            record.update({"loading": PASTE_LOADING, "pasted_at": _now()})
            data["responses"].append(record)
        order = {rid: index for index, rid in enumerate(runs)}
        data["responses"].sort(key=lambda r: order.get(r.get("run_id"), len(order)))
        _write_json(path, data)
    return {"saved": bool(text.strip()), "run_id": run_id}


def final_run(body: dict) -> dict:
    """POST /api/team/final/run {model: "A"|"B", overwrite?}: answer the final runs of one model through its API.

    The final me.md is message 1 and each final question message 2 (the loading protocol), and every answer lands in
    final/responses.json, the file the final paste station writes, so the judge and the bundle read it unchanged. A saved
    answer (a pasted one) is never replaced unless ``overwrite`` is true."""
    model = body.get("model")
    _require(model in ("A", "B"), "model must be A or B")
    overwrite = _overwrite_flag(body)
    questions = _final_questions()
    me = final_dir() / "me.md"
    _require(bool(questions) and me.exists(), "save the final inputs first", 409)
    _require_api(model)
    profile = me.read_text(encoding="utf-8")
    runs = _final_runs(questions)
    path = final_dir() / "responses.json"
    saved_runs = {r.get("run_id") for r in _read_json(path, {"responses": []}).get("responses", [])
                  if str(r.get("text", "")).strip()}
    todo = [run for run in runs if run["model"] == model and (overwrite or run["run_id"] not in saved_runs)]
    if not todo:
        return {"answered": 0, "kept": 0, "errors": []}
    answer = _answerer_for(model)
    order = {run["run_id"]: index for index, run in enumerate(runs)}
    answered, kept, errors = 0, 0, []
    for run in todo:
        try:
            text, record = _reply_parts(answer(profile, questions[run["question_id"]]), model)
            if not text.strip():
                raise RuntimeError("empty answer")
        except Exception as error:  # report the reason, never the key or the body
            errors.append(f"{run['run_id']}: {type(error).__name__}: {str(error)[:200]}")
            continue
        with _WRITE_LOCK:
            data = _read_json(path, {"responses": []})
            if not overwrite and _has_text(data.get("responses", []), run["run_id"]):
                kept += 1  # pasted while the API was answering: the person's answer stays
                continue
            data["responses"] = [r for r in data.get("responses", []) if r.get("run_id") != run["run_id"]]
            data["responses"].append({"run_id": run["run_id"], "question_id": run["question_id"], "text": text.strip(),
                                      **_api_fields(record, True), "pasted_at": _now()})
            data["responses"].sort(key=lambda r: order.get(r.get("run_id"), len(order)))
            _write_json(path, data)
        answered += 1
    return {"answered": answered, "kept": kept, "errors": errors}


def final_judge(body: dict) -> dict:
    from . import runner
    from .judge.judge import judge_responses
    from .judge.report import write_reports
    folder = final_dir()
    _require((folder / "build.json").exists() and (folder / "questions.json").exists(), "save the final inputs first", 409)
    test_data = body.get("test")
    test = _check_test(test_data)
    comparisons_data = body.get("comparisons")
    _require(isinstance(comparisons_data, dict) and isinstance(comparisons_data.get("responses"), list),
             "comparisons must be a comparison response file ({\"responses\": [...]})")
    try:
        comparisons = parse_responses(comparisons_data)
    except (KeyError, TypeError) as error:
        raise TeamError(400, f"comparisons file cannot be read: {type(error).__name__}: {error}") from error
    ours = [r for r in _final_responses() if r.text.strip()]
    _require(bool(ours), "no final answers saved yet")
    collisions = sorted({r.run_id for r in ours} & {r.run_id for r in comparisons})
    _require(not collisions, f"comparison run IDs collide with ours: {', '.join(collisions)}")
    backend = judge_backend()
    with _WRITE_LOCK:
        _write_json(folder / "test.json", test_data)
        _write_json(folder / "comparisons.json", comparisons_data)
    # Both generating models are UNDER TEST (listed so the judge metadata warns on overlap); neither is ever the judge.
    # The judge is MEFILE_JUDGE_MODEL on Claude, distinct from LLM A; LLM B's id (MEFILE_LLM_B_MODEL) is never a judge.
    from . import openai_runner
    under_test = [runner.DEFAULT_MODEL] + ([openai_runner.configured_model()] if openai_runner.configured_model() else [])
    result = judge_responses(load_answers(folder / "build.json"), _final_questions(), test, ours + comparisons, backend,
                             under_test)
    with _WRITE_LOCK:
        _, markdown_path = write_reports(result, team_dir())
    ok = sum(1 for e in result["evaluations"] if e["status"] == "ok")
    return {"evaluations_md": markdown_path.read_text(encoding="utf-8"),
            "counts": {"ok": ok, "judge_error": len(result["evaluations"]) - ok}}


def _provenance_entry() -> dict:
    return {"model_shown": [], "runs": 0, "pasted_runs": 0, "api_runs": 0, "loading": [], "model_served": []}


def _add_provenance(entry: dict, record: dict) -> None:
    if not str(record.get("text", "")).strip():
        return
    entry["runs"] += 1
    entry["api_runs" if record.get("source") == "api" else "pasted_runs"] += 1
    for key, value in (("model_shown", record.get("model_shown")), ("loading", record.get("loading")),
                       ("model_served", record.get("model_served"))):
        if value and value not in entry[key]:
            entry[key].append(value)


def provenance() -> dict:
    """How every run was produced, per model: the model name the chat window showed, the loading protocol, run counts,
    and the served model for API runs. Built from the saved response records, so it says only what was recorded."""
    final_runs = {run["run_id"]: run["model"] for run in _final_runs(_final_questions())}
    final = {"A": _provenance_entry(), "B": _provenance_entry()}
    for record in _read_json(final_dir() / "responses.json", {"responses": []}).get("responses", []):
        model = final_runs.get(record.get("run_id"))
        if model:
            _add_provenance(final[model], record)
    team_runs = {"A": _provenance_entry(), "B": _provenance_entry()}
    for folder in _people_folders(require_test=False):
        for model in ("A", "B"):
            for record in _read_json(folder / f"llm_{model.lower()}.json", {"responses": []}).get("responses", []):
                _add_provenance(team_runs[model], record)
    judge = None
    evaluations = _read_json(team_dir() / "evaluations.json", None)
    if isinstance(evaluations, dict) and isinstance(evaluations.get("metadata"), dict):
        metadata = evaluations["metadata"]
        judge = {"model_requested": metadata.get("judge_model_requested"), "models_served": metadata.get("judge_models_served", [])}
    unrecorded = [f"final LLM {m}: {e['pasted_runs']} pasted run(s) but no model name shown was recorded"
                  for m, e in final.items() if e["pasted_runs"] and not e["model_shown"]]
    return {"loading_protocol": PASTE_LOADING, "final": final, "team_runs": team_runs, "judge": judge,
            "warnings": unrecorded, "generated_at": _now()}


def final_bundle() -> Reply:
    me = final_dir() / "me.md"
    _require(me.exists(), "no final me.md yet: save the final inputs first", 404)
    members = [("me.md", me), ("responses.json", final_dir() / "responses.json"),
               ("evaluations.json", team_dir() / "evaluations.json"), ("evaluations.md", team_dir() / "evaluations.md"),
               ("results.md", team_dir() / "results.md"), ("selfcheck.md", team_dir() / "selfcheck.md"),
               ("writeup.md", DOCS / "writeup.md"), ("README.md", REPOSITORY / "README.md")]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, path in members:
            if path.is_file():
                archive.writestr(name, path.read_bytes())
        archive.writestr("provenance.json", json.dumps(provenance(), indent=2, ensure_ascii=False))
    file_name = re.sub(r"[^A-Za-z0-9_-]", "", team_name()) or "TEAM"
    return Reply(200, body=buffer.getvalue(), content_type="application/zip",
                 headers={"Content-Disposition": f'attachment; filename="{file_name}-submission.zip"'})


# ---------------------------------------------------------------------------
# Judge self-check (Common Kit section 9: "Report at least one case where it fails")
# ---------------------------------------------------------------------------

_EMPTY_SELFCHECK = {"passed": 0, "total": 0, "probes": [], "selfcheck_md": ""}


def _probe_view(probe: dict, outcome: dict, scores: dict[str, dict]) -> dict:
    first, second = probe["first"], probe.get("second", "")
    kind = probe["kind"]
    expectation = {
        "greater": f"{first} scores higher than {second}",
        "close": f"{first} and {second} score within 1 point of each other",
        "flagged": f"{first} is flagged as generic writing",
        "not_flagged": f"{first} is not flagged as generic writing",
    }.get(kind, probe["name"])
    involved = [scores.get(first, {}), scores.get(second, {})] if second else [scores.get(first, {})]
    if any(e.get("status") != "ok" for e in involved):
        result = "no verdict: the judge errored on a probe response"
    elif kind in ("greater", "close"):
        result = f"{first} scored {involved[0].get('score')}, {second} scored {involved[1].get('score')}"
    else:
        result = f"{first} {'was' if involved[0].get('is_generic') else 'was not'} flagged as generic"
    return {"name": outcome["name"], "expectation": expectation, "result": result, "passed": bool(outcome["passed"]),
            "detail": outcome["detail"]}


def _selfcheck_markdown(view: dict) -> str:
    def cell(text: str) -> str:
        return str(text).replace("|", "\\|").replace("\n", " ")
    served = ", ".join(f"`{m}`" for m in view.get("judge_models_served") or []) or "none"
    lines = [f"# Judge self-check: {view['passed']}/{view['total']} probes passed", "",
             f"Judge model requested: `{view.get('judge_model_requested')}`; served: {served}. Run {view.get('at')}.", "",
             "Each probe is a fixed pair of responses written for the fictional DEMO01 person (never a real person), with "
             "an expectation about the judge's own behaviour. Failures are evidence: the challenge asks for at least one.", "",
             "| Probe | Expectation | Result | Verdict |", "|---|---|---|---|"]
    for probe in view["probes"]:
        lines.append(f"| {cell(probe['name'])} | {cell(probe['expectation'])} | {cell(probe['result'])} | "
                     f"{'pass' if probe['passed'] else 'FAIL'} |")
    failures = [p for p in view["probes"] if not p["passed"]]
    lines += ["", f"## Where the judge fails ({len(failures)})", ""]
    lines += [f"- **{p['name']}**: expected {p['expectation']}; {p['result']}." for p in failures] or \
             ["- No probe failed in this run. The corpus is small; that is not evidence the judge never fails."]
    return "\n".join(lines) + "\n"


def run_selfcheck(body: dict) -> dict:
    from .judge.eval_corpus import PROBES, run_judge_selfcheck
    backend = judge_backend()
    report = run_judge_selfcheck(backend)
    scores = {e["run_id"]: {"status": e.get("status"), "score": (e.get("reference_resemblance") or {}).get("score"),
                            "is_generic": (e.get("generic_writing") or {}).get("is_generic")}
              for e in report["evaluations"]}
    probes = [_probe_view(probe, outcome, scores) for probe, outcome in zip(PROBES, report["probes"])]
    view = {"passed": report["passed"], "total": report["total"], "probes": probes,
            "judge_model_requested": report.get("judge_model_requested"),
            "judge_models_served": report.get("judge_models_served") or [], "at": _now()}
    view["selfcheck_md"] = _selfcheck_markdown(view)
    with _WRITE_LOCK:
        _write_json(team_dir() / "selfcheck.json", {**view, "evaluations": report["evaluations"]})
        _write_text(team_dir() / "selfcheck.md", view["selfcheck_md"])
    return view


def last_selfcheck() -> dict:
    data = _read_json(team_dir() / "selfcheck.json", None)
    if not isinstance(data, dict):
        return dict(_EMPTY_SELFCHECK)
    return {key: value for key, value in data.items() if key != "evaluations"}


# ---------------------------------------------------------------------------
# Docs
# ---------------------------------------------------------------------------


def _doc_path(name: str) -> Path | None:
    if name not in DOC_ALLOWLIST:
        return None
    path = DOCS / f"{name}.md"
    return path if path.is_file() else None


def list_docs() -> dict:
    docs = []
    for name in DOC_ALLOWLIST:
        path = _doc_path(name)
        if path is None:
            continue
        first = next((line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("# ")), "")
        docs.append({"name": name, "title": first[2:].strip() or name})
    return {"docs": docs}


def get_doc(name: str) -> dict:
    path = _doc_path(name)
    _require(path is not None, "not found", 404)
    return {"name": name, "markdown": path.read_text(encoding="utf-8")}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

_OPEN = {("POST", "/api/team/login"): _login, ("POST", "/api/team/logout"): _logout, ("GET", "/api/team/me"): _me}

_GATED_GET: dict[str, Callable[[], Any]] = {
    "/api/team/people": list_people,
    "/api/team/results": last_results,
    "/api/team/final": final_state,
    "/api/team/docs": list_docs,
    "/api/team/selfcheck": last_selfcheck,
}
_GATED_POST: dict[str, Callable[[dict], Any]] = {
    "/api/team/people": save_person,
    "/api/team/people/delete": delete_person,
    "/api/team/voice": save_voice,
    "/api/team/run": run_missing,
    "/api/team/experiment": run_team_experiment,
    "/api/team/ratesheet": lambda body: build_ratesheet(),
    "/api/team/agreement": run_agreement,
    "/api/team/final/inputs": final_inputs,
    "/api/team/final/answer": final_answer,
    "/api/team/final/run": final_run,
    "/api/team/final/judge": final_judge,
    "/api/team/selfcheck": run_selfcheck,
    "/api/station/answer": station_save,
}

_PASTE_SIGN_IN = (b"<!doctype html><html lang=en><meta charset=utf-8>"
                  b"<meta name=viewport content='width=device-width, initial-scale=1'>"
                  b"<title>lumin8r paste station: sign in</title><link rel=stylesheet href=/static/mefile.css>"
                  b"<main class=panel style='width:min(480px,calc(100% - 32px));margin:64px auto;padding:24px;gap:16px'>"
                  b"<span class=eyebrow>paste station</span><h1>Sign in to the team hub first.</h1>"
                  b"<p class=lead>The paste station is for the team. Enter the team code on the team hub, then come back to this page.</p>"
                  b"<p><a class='btn lime big' href=/workbench>Open the team hub</a></p>"
                  b"<p class=small><a href=/>Back to the front page</a></p></main></html>")


def handle(request: Request) -> Reply:
    """Every team route: gate first, then dispatch. Errors become JSON; nothing from the body is logged."""
    try:
        return _dispatch(request)
    except TeamError as error:
        return Reply(error.status, {"error": error.message, **error.extra})
    except Exception as error:  # the reason's type only: never echo a body or a key
        return Reply(500, {"error": f"team route failed: {type(error).__name__}"})


def _dispatch(request: Request) -> Reply:
    method, path = request.method, request.path
    opener = _OPEN.get((method, path))
    if opener is None and not workbench_enabled():
        if path == "/paste":
            return Reply(404, body=NOT_AVAILABLE_PAGE, content_type="text/html; charset=utf-8")
        return Reply(404, {"error": NOT_AVAILABLE})
    if gate_mode() == "unconfigured":
        return Reply(503, {"error": UNCONFIGURED_MESSAGE})
    if opener is not None:
        return opener(request)
    if not signed_in(request):
        if path == "/paste":
            return Reply(401, body=_PASTE_SIGN_IN, content_type="text/html; charset=utf-8")
        return Reply(401, {"error": SIGN_IN_MESSAGE})

    if method == "GET":
        if path == "/paste":
            return Reply(200, body=(STATIC / "paste.html").read_bytes(), content_type="text/html; charset=utf-8")
        if path == "/api/station/queue":
            model = parse_qs(request.query).get("model", [""])[0]
            try:
                return Reply(200, station_queue(model if model in ("A", "B") else None))
            except Exception as error:
                return Reply(500, {"error": str(error)})
        if path == "/api/station/results":
            try:
                return Reply(200, station_results())
            except Exception as error:
                return Reply(500, {"error": str(error)})
        if path in _GATED_GET:
            return Reply(200, _GATED_GET[path]())
        if path.startswith("/api/team/files/"):
            return serve_team_file(path[len("/api/team/files/"):])
        if path == "/api/team/final/bundle":
            return final_bundle()
        if path.startswith("/api/team/docs/"):
            return Reply(200, get_doc(path[len("/api/team/docs/"):]))
        return Reply(404, {"error": "not found"})

    if method == "POST" and path in _GATED_POST:
        if path == "/api/station/answer":
            try:
                return Reply(200, station_save(request.body))
            except Exception as error:
                return Reply(400, {"error": str(error)})
        try:
            return Reply(200, _GATED_POST[path](request.body))
        except TeamError:
            raise
        except (ValueError, KeyError, TypeError, AttributeError, json.JSONDecodeError) as error:
            return Reply(400, {"error": f"{type(error).__name__}: {error}"})
    return Reply(404, {"error": "not found"})
