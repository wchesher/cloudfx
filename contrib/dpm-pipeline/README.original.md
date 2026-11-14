# DPM pipeline: quick start

| File | What it is | Who sees it |
| --- | --- | --- |
| `me_template.md` | Guardrail header (Deliverable 3) + profile body with translation rules (Deliverable 1) | Employees, via the generated me.md |
| `convert.py` | Intake JSON → `me.md`. Drops holdouts S02/S04/S06/W02/W04, scores traits, fills template, signs with SHA-256 | Your backend |
| `judge_prompt.txt` | AI Judge prompt (Deliverable 2) | Judge model only, never in me.md |
| `judge.py` | Runs the 5 holdouts: sim (with me.md) vs baseline (without) vs ground truth → DF and SF scores | Your backend |
| `redteam.py` | 30 evaluative prompts; checks the exact Section 3 refusal | Your backend |
| `sample_intake.json` / `sample_me.md` | Dummy data showing the expected schema and output | Demo |

## Run it

```bash
python convert.py sample_intake.json -o me.md      # 1. build a twin
python convert.py --verify me.md                    # 2. tamper check (exit 1 if altered)

pip install anthropic openai
export ANTHROPIC_API_KEY=...  OPENAI_API_KEY=...
python judge.py sample_intake.json me.md --gen claude --judge gpt   # 3. fidelity scores
python redteam.py me.md --host claude                               # 4. refusal check
python redteam.py me.md --host gpt
```

## Your intake JSON

Expected shape (see `sample_intake.json`):

```json
{"owner_name": "Alex Rivera",
 "items": [
  {"id": "B01", "type": "likert", "domain": "E", "reverse": false, "prompt": "...", "response": 4},
  {"id": "S01", "type": "scenario", "prompt": "...", "response": "free text"},
  {"id": "W01", "type": "writing",  "prompt": "...", "response": "free text"}]}
```

Different key names? Edit the `FIELDS` dict at the top of `convert.py`; `judge.py` and `redteam.py` reuse it.

## Tuning

- Trait cutoffs: `HIGH` / `LOW` in `convert.py` (defaults 3.7 / 2.3).
- Framing rules per trait level: `STYLE` dict in `convert.py`.
- Models: `MODELS` dict in `judge.py`. Keep generator and judge in different model families.
- Demo tip: sample data is synthetic, so the Judge scores on it are meaningless. Use a real teammate's intake for the demo.
