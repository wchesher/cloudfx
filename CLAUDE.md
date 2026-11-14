# mefile: Digital Personality Modeling (CGU Digital Twin track, Wethos)

Common Kit answers in, a portable, employee-owned `me.md` out; an AI judge that explains resemblance.
Read `docs/strategy.md` first (what we are optimizing and why), then `docs/judge.md`, `docs/frameworks-and-wethos.md`.

## Hard rules (the challenge's, not style)
- The converter is ZERO-LLM and deterministic. Never hand-edit a generated me.md; change the converter.
- Never feed development-test answers (S02, S04, S06, W02, W04) to the converter or to a generating model.
  The claims gate (`src/mefile/claims.py`) refuses export if they leak.
- Every claim cites answer IDs. No fixed personality labels. Middle scores mean "no clear tendency".
- Real people's answers, profiles and transcripts NEVER go in git: put them under `private/` (gitignored).
  Only the fictional DEMO01 files in `examples/` are committed.
- Freeze at 16:30: after that, no change to code, prompts, judge rubric or settings.
- Voice intake: transcript text only. No tone/emotion inference (EU AI Act Art. 5(1)(f)), no voice cloning.

## Layout and owners (claim a file in the team chat before editing)
- `src/mefile/kit.py` Common Kit as data. `answers.py` organizer file formats.
- `scoring.py` IPIP scoring. `style.py` writing-style counts. `claims.py` the gate. `converter.py` me.md.
- `crosswalk.py` Wethos Style hypotheses (labelled, never scores). `runner.py` LLM A two-turn protocol.
- `judge/` the AI judge (backend seam, fail-closed, blind to source). `app.py` + `static/index.html` review app.
- `voice.py` ElevenLabs interview (signed URL, transcript fetch).

## Commands
```bash
python3 -m venv .venv && .venv/bin/pip install pytest anthropic
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m mefile serve --port 8080
PYTHONPATH=src .venv/bin/python -m mefile final BUILD.json QUESTIONS.json --out private/final --team TEAMNAME
PYTHONPATH=src .venv/bin/python -m mefile run QUESTIONS.json --profile private/final/me.md --prefix A --out private/runs/A.json
PYTHONPATH=src .venv/bin/python -m mefile.judge --build B.json --questions Q.json --reference T.json --responses R1.json R2.json --out private/judge
PYTHONPATH=src .venv/bin/python -m mefile.judge selfcheck
```
Env: `ANTHROPIC_API_KEY`, `MEFILE_JUDGE_MODEL` (use a model that is NOT under test), `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`.

## Conventions
Python stdlib only (anthropic SDK lazily imported). Two-line header on every new .py:
`# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.` / `# module_name - brief description`. No emojis.
