#!/usr/bin/env python3
"""Intake JSON (60 items) -> me.md.

Usage:
  python convert.py intake.json -o me.md          # build
  python convert.py --verify me.md                # check the hash before loading

Edit FIELDS below if your intake JSON uses different key names.
"""
import argparse, datetime, hashlib, json, re, sys
from pathlib import Path

HERE = Path(__file__).parent
TEMPLATE = HERE / "me_template.md"

# ---- adjust to your intake schema -------------------------------------------
FIELDS = {
    "owner": "owner_name",      # top-level name field
    "items": "items",           # top-level list of items
    "id": "id",                 # e.g. "B01", "S03", "W02"
    "type": "type",             # "likert" | "scenario" | "writing"
    "domain": "domain",         # likert only: O, C, E, A, N
    "reverse": "reverse",       # likert only: true if reverse-keyed
    "prompt": "prompt",
    "response": "response",     # likert: 1-5 int; others: text
}
HOLDOUT = {"S02", "S04", "S06", "W02", "W04"}   # never enters me.md
HIGH, LOW = 3.7, 2.3
DOMAINS = {"O": "Openness", "C": "Conscientiousness", "E": "Extraversion",
           "A": "Agreeableness", "N": "Neuroticism"}

# Deliverable 1 matrix, as instructions. N and O are scored but don't drive framing.
STYLE = {
    ("E", "HIGH"): "Outbound: keep energy and first-person verbs; offer a quick call. "
                   "Inbound: point out where a short conversation would settle it.",
    ("E", "LOW"):  "Outbound: concise, no forced warmth or exclamation marks. "
                   "Inbound: give the full ask in writing; suggest an async reply.",
    ("A", "HIGH"): "Prefers high-context, relationship-first framing and indirect negative feedback. "
                   "Outbound: keep their softeners but put the ask in the first two sentences. "
                   "Inbound: norm note before the facts; state what the message does NOT say.",
    ("A", "LOW"):  "Prefers low-context, direct framing. Outbound: keep it blunt; add only the "
                   "context the recipient's norms require. Inbound: strip padding; ask in one line.",
    ("C", "HIGH"): "Wants explicit specs, owners, dates. Outbound: keep their lists and dates. "
                   "Inbound: turn every ask into a dated checklist.",
    ("C", "LOW"):  "Tolerates ambiguity. Outbound: don't add structure they don't use. "
                   "Inbound: one next step and one deadline; leave the rest in the original.",
}
BODY_RE = re.compile(r"<!-- BEGIN PROFILE BODY -->.*?<!-- END PROFILE BODY -->", re.S)


def level(x):
    return "HIGH" if x >= HIGH else "LOW" if x <= LOW else "MID"


def build(intake: dict) -> str:
    f = FIELDS
    owner = intake[f["owner"]]
    items = [i for i in intake[f["items"]] if str(i[f["id"]]).upper() not in HOLDOUT]

    scores = {}
    for d in DOMAINS:
        vals = [(6 - int(i[f["response"]])) if i.get(f["reverse"]) else int(i[f["response"]])
                for i in items if i[f["type"]] == "likert" and i.get(f["domain"]) == d]
        if vals:
            scores[d] = round(sum(vals) / len(vals), 2)

    trait_table = "| Trait | Score | Level |\n| --- | --- | --- |\n" + "\n".join(
        f"| {DOMAINS[d]} | {s} | {level(s)} |" for d, s in scores.items())
    rules = [f"- {DOMAINS[d]} {level(s)}: {STYLE[(d, level(s))]}"
             for d, s in scores.items() if (d, level(s)) in STYLE]
    style = "\n".join(rules) or "- No strong preferences: follow the writing samples."

    def block(kind):
        out = [f"### {i[f['id']]}\nPrompt: {i.get(f['prompt'], '')}\n\n{i[f['response']]}"
               for i in items if i[f["type"]] == kind]
        return "\n\n".join(out) or "(none)"

    tpl = TEMPLATE.read_text()
    fill = {"OWNER_NAME": owner, "VERSION_DATE": datetime.date.today().isoformat(),
            "TRAIT_TABLE": trait_table, "STYLE_RULES": style,
            "SCENARIO_ANSWERS": block("scenario"), "WRITING_SAMPLES": block("writing")}
    for k, v in fill.items():
        tpl = tpl.replace("{{" + k + "}}", str(v))
    body = BODY_RE.search(tpl).group(0)
    return tpl.replace("{{PROFILE_HASH}}", hashlib.sha256(body.encode()).hexdigest())


def verify(text: str) -> bool:
    m = re.search(r"sha256: ([0-9a-f]{64})", text)
    b = BODY_RE.search(text)
    ok = bool(m and b and "<!-- END SYSTEM DIRECTIVE -->" in text
              and hashlib.sha256(b.group(0).encode()).hexdigest() == m.group(1))
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("intake", nargs="?")
    ap.add_argument("-o", "--out", default="me.md")
    ap.add_argument("--verify")
    a = ap.parse_args()
    if a.verify:
        ok = verify(Path(a.verify).read_text())
        print("OK: header and body intact" if ok else "FAIL: header missing or body altered")
        sys.exit(0 if ok else 1)
    if not a.intake:
        ap.error("give an intake JSON or --verify me.md")
    Path(a.out).write_text(build(json.loads(Path(a.intake).read_text())))
    print(f"wrote {a.out}")
