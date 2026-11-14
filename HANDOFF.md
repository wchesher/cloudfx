# Handoff: continue in Claude Desktop

## Get it running (5 minutes)
1. Clone the bundle:
   ```bash
   git clone https://github.com/wchesher/cloudfx
   ```
   (The old CircuitPython project is at tag `cloudfx-circuitpython-v1.0`.)
2. Open the `cloudfx` folder in Claude Desktop (the Code tab), so Claude reads `CLAUDE.md`.
3. Set up and run the tests:
   ```bash
   python3 -m venv .venv
   ```
   ```bash
   .venv/bin/pip install pytest anthropic
   ```
   ```bash
   PYTHONPATH=src .venv/bin/python -m pytest -q
   ```
   Expect 19 passed.
4. Start the app and open http://localhost:8080. Click "Use the fictional example" to rehearse.
   ```bash
   PYTHONPATH=src .venv/bin/python -m mefile serve
   ```
5. Set the keys in your shell, never in a file in git: `ANTHROPIC_API_KEY`, `MEFILE_JUDGE_MODEL`
   (a model that is NOT one being tested), and optionally `ELEVENLABS_API_KEY` and
   `ELEVENLABS_AGENT_ID`.

## Paste this as your first message to Claude Desktop
> Read CLAUDE.md, docs/strategy.md, docs/judge.md and docs/voice-intake.md. Today is the hackathon;
> code freeze is 4:30pm. The converter, claims gate, review app, freeze pipeline, Claude runner and
> judge are built and tested only with fake backends; nothing has run against a live model yet.
> Next, in order:
> (1) run `python -m mefile.judge selfcheck` with the live judge and record which probes fail;
> (2) for each teammate's answers in private/, generate me.md, run profile and no-profile on
> LLM A (`mefile run`), collect LLM B by paste, and score with the judge;
> (3) tune the converter on what fails (not the judge); write the comparison table into
> docs/results.md;
> (4) rehearse `mefile final` on the fictional files by 3:30pm.
> Keep all real data in private/.

## State at handoff
- **Built and tested:**
  - the kit as data, scoring, style counts and the claims gate
  - the converter (me.md and me.json, full and coaching versions, sections the person can
    withhold), plus the Wethos Style crosswalk, labelled as hypotheses
  - the review app (consent ledger, claim-to-evidence highlighting, edit and regenerate, review
    lock, withdrawal)
  - `mefile final` (paste packets, response template, run sheet)
  - `mefile run` (Claude Opus 5.5 at medium effort, two-turn loading)
  - the judge (blind to source, fails closed, self-check probes)
  - the ElevenLabs voice session in the app
- **Not yet done:**
  - live runs of every model
  - measuring the profile lift with teammates' data
  - AI-to-human agreement for the judge
  - turning voice transcripts into cited evidence (V01...) inside the converter
  - the slides
- **The one known open finding:** with the fake backend, the judge self-check fails the
  generic-filler and fairness-pair probes. Run it live to see whether the real model passes.
