# lumin8r: your work style, your file

CGU Digital Twin hackathon, Digital Personality Modeling track (sponsored by Wethos), 14 November 2026.
Live: https://microverse.cloud. License: MIT. The earlier CircuitPython project in this repo is kept at tag
`cloudfx-circuitpython-v1.0`.

lumin8r turns the 30-minute Common Kit into a portable, employee-owned `me.md`. An AI judge then explains how
closely AI answers built from that file resemble the person.

- **Converter, no AI in it.** The same answers always produce the same file. Every claim cites the answer IDs
  behind it, and a claims gate refuses to export a file with an uncited claim, a fixed label or a leaked test answer.
- **Review app.** The person consents first, checks each claim against its answers, corrects or disputes it,
  picks what to share and downloads the file.
- **AI judge.** Scores 0 to 4 on resemblance and on consistency with the evidence, cites evidence IDs, never sees
  which system wrote a response, and fails closed.

**Use limit, printed in every file:** voluntary coaching, reflection and communication support only. Not for
hiring, promotion, performance ratings, pay, discipline or ranking. Simulated answers are not the person's statements.

## The submission package

Downloaded from the workbench (`/workbench#final`, "Download submission"; route `GET /api/team/final/bundle`)
as `TEAM-submission.zip`:

| File | What it is | Common Kit |
|---|---|---|
| `me.md` | The volunteer's profile, generated at the freeze and never hand-edited | 10 |
| `responses.json` | Eight responses: four private questions x LLM A and LLM B | 10 |
| `evaluations.json`, `evaluations.md` | The judge on all twenty responses (our eight, eight no-profile, four Wethos) | 8, 10 |
| `results.md` | Development comparison, final scores by source | 9, 10 |
| `selfcheck.md` | Judge self-check probes, including the ones it fails | 9 |
| `writeup.md` | Method, testing, safeguards and limitations (`docs/writeup.md`) | 12 |
| `README.md` | This file: code and run instructions | 12 |
| `provenance.json` | Loading protocol, models requested and served per run, judge model, warnings | 10 |

Optional alternative intake (Section 11): `docs/alternative-intake.md`.

Real people's answers, profiles and transcripts are never committed. They live under `private/` (gitignored) and
on the server. The only kit files in git are the fictional DEMO01 examples in `examples/`.

## Run it

Python 3, standard library only. The `anthropic` SDK is needed only for live model calls.

```bash
python3 -m venv .venv && .venv/bin/pip install pytest anthropic
```

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

```bash
PYTHONPATH=src .venv/bin/python -m mefile serve --port 8080
```

Then open http://localhost:8080. The evaluation workbench (`/workbench`, `/paste`) is off unless
`LUMIN8R_WORKBENCH=1` is set.

### Reproduce the final run

1. Build the profile, paste packets and run sheet. `final` refuses to write a profile that fails the claims gate.

   ```bash
   PYTHONPATH=src .venv/bin/python -m mefile final BUILD.json QUESTIONS.json --out private/final --team TEAMNAME --llm-b api
   ```

2. LLM A (Claude Opus 5.5, medium) by API, using the two-turn protocol: a new conversation per question, me.md
   as message one, the question as message two.

   ```bash
   PYTHONPATH=src .venv/bin/python -m mefile run QUESTIONS.json --profile private/final/me.md --prefix A --out private/runs/A.json
   ```

3. Judge all responses against the volunteer's test answers, with a judge model that is not under test.

   ```bash
   PYTHONPATH=src .venv/bin/python -m mefile.judge --build BUILD.json --questions QUESTIONS.json --reference TEST.json --responses RESPONSES.json COMPARISONS.json --out private/judge
   ```

4. Judge self-check.

   ```bash
   PYTHONPATH=src .venv/bin/python -m mefile.judge selfcheck
   ```

Development comparison across teammates (add `--dry-run` to test without API keys):

```bash
PYTHONPATH=src .venv/bin/python -m mefile experiment --people private/people --judge --llm-b api --out private/experiment
```

### Settings

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | LLM A and the judge |
| `MEFILE_JUDGE_MODEL` | Judge model; must not be a model under test |
| `OPENAI_API_KEY`, `MEFILE_LLM_B_MODEL`, `MEFILE_LLM_B_EFFORT` | LLM B through the OpenAI Responses API (no model default in code; effort defaults to medium). Without them, LLM B is pasted |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID` | Optional voice interview |
| `LUMIN8R_WORKBENCH=1` | Turns on the evaluation workbench |

Deployment: `deploy/update-lumin8r` (idempotent, tests each release before swapping it in; secrets only via `--set-key`).

## Code map (`src/mefile`)

| Area | Modules |
|---|---|
| Common Kit as data, answer file formats | `kit.py`, `answers.py` |
| IPIP-50 scoring, writing-style counts | `scoring.py`, `style.py` |
| Claims gate | `claims.py` |
| me.md converter, variants, share scopes | `converter.py`, `readings.py` |
| Wethos Style crosswalk (labelled hypotheses, never scores) | `crosswalk.py` |
| LLM A and LLM B runners | `runner.py`, `openai_runner.py` |
| Development comparison and leakage guard | `experiment.py` |
| AI judge | `judge/` |
| Interview intake (voice, Plaud, typed) | `voice.py`, `plaud.py`, `intake.py` |
| Encrypted, revocable shares | `shares.py` |
| Workbench API and submission bundle | `team.py` |
| Web routes and command line | `app.py`, `cli.py` |

## Further reading

- `docs/writeup.md`: the submission write-up.
- `docs/strategy.md`: what we optimize for and why.
- `docs/judge.md`: judge design, scale and checks. `docs/judge-mistake-example.md`: a documented judge failure.
- `docs/frameworks-and-wethos.md`, `docs/m3-risk-mapping.md`, `docs/risk-and-acceptance.md`: ethics, law and risk.
- `docs/requirements-check.md`: every challenge requirement mapped to where it is met.
