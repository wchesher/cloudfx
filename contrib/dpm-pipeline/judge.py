#!/usr/bin/env python3
"""Score me.md against the 5 sequestered items (S02, S04, S06, W02, W04).

Usage:
  pip install anthropic openai
  export ANTHROPIC_API_KEY=... OPENAI_API_KEY=...
  python judge.py intake.json me.md --gen claude --judge gpt

Use a DIFFERENT model family for --judge than --gen (judges favour their own style).
Prints per-item JSON and the two separate scores (never combined).
"""
import argparse, json, re, statistics
from pathlib import Path

from convert import FIELDS, HOLDOUT

HERE = Path(__file__).parent
MODELS = {"claude": "claude-sonnet-5-5", "gpt": "gpt-4o"}   # set the GPT model to whatever your key can use


def call(provider: str, system: str, user: str) -> str:
    if provider == "claude":
        import anthropic
        r = anthropic.Anthropic().messages.create(
            model=MODELS["claude"], max_tokens=2000, system=system or anthropic.NOT_GIVEN,
            messages=[{"role": "user", "content": user}])
        return r.content[0].text
    from openai import OpenAI
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    return OpenAI().chat.completions.create(model=MODELS["gpt"], messages=msgs).choices[0].message.content


def parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {"error": "no JSON", "raw": text}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("intake"); ap.add_argument("me_md")
    ap.add_argument("--gen", default="claude", choices=MODELS)
    ap.add_argument("--judge", default="gpt", choices=MODELS)
    a = ap.parse_args()

    f = FIELDS
    intake = json.loads(Path(a.intake).read_text())
    profile = Path(a.me_md).read_text()
    items = intake[f["items"]]
    held = [i for i in items if str(i[f["id"]]).upper() in HOLDOUT]
    corpus = "\n\n".join(str(i[f["response"]]) for i in items
                         if str(i[f["id"]]).upper() not in HOLDOUT and i[f["type"]] != "likert")
    judge_tpl = (HERE / "judge_prompt.txt").read_text()

    results = []
    for it in held:
        prompt = it[f["prompt"]]
        sim = call(a.gen, profile, f"Respond to this exactly as I would, in my voice:\n\n{prompt}")
        base = call(a.gen, "", f"Respond to this:\n\n{prompt}")
        filled = judge_tpl
        for k, v in {"profile": profile, "item_id": it[f["id"]], "item_type": it[f["type"]],
                     "prompt": prompt, "ground_truth": it[f["response"]], "simulation": sim,
                     "baseline": base, "training_corpus": corpus}.items():
            filled = filled.replace("{" + k + "}", str(v))
        res = parse_json(call(a.judge, "", filled))
        res["_simulation"] = sim
        results.append(res)
        print(json.dumps(res, indent=2))

    df = [r["decision_fidelity"]["score"] for r in results
          if isinstance(r.get("decision_fidelity", {}).get("score"), (int, float))]
    sf = [r["style_fidelity"]["score"] for r in results
          if isinstance(r.get("style_fidelity", {}).get("score"), (int, float))]
    print("\n=== SUMMARY (reported separately, never combined) ===")
    print(f"Decision Fidelity (S items): {statistics.mean(df):.1f}" if df else "Decision Fidelity: n/a")
    print(f"Style Fidelity (all items):  {statistics.mean(sf):.1f}" if sf else "Style Fidelity: n/a")
    Path("judge_results.json").write_text(json.dumps(results, indent=2))
    print("details -> judge_results.json")


if __name__ == "__main__":
    main()
