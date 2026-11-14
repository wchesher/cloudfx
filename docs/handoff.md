# Handoff: lumin8r, 14 November 2026

Read this first, then `CLAUDE.md`, `docs/product.md` and `docs/requirements-check.md`.

## The setting
- **Event:** Will (GitHub `wchesher`, the builder) is in the CGU Digital Twin hackathon, Wethos track, on 2026-11-14.
- **Challenge sources:** the DPM Problem Statement and Common Kit. They are not in git; ask Will for the zip if you need the text.
- **Schedule (Pacific):** freeze 4:30pm; 8 model responses by 5:00; 20 judge evaluations by 5:30; submission 6:00; panel 6:30.
- **Teammates:**
  - Mark, the employee side: ethics, legal, risk, regulatory, and the Wethos liaison.
  - Steven, the company side: research, market and use cases. Practitioner quotes are still owed.

## What the product is
**lumin8r** at https://microverse.cloud:
- a 30-minute work-style assessment (`/assessment`)
- the answers become a plain-language file (me.md) built by fixed rules, with no AI; every statement cites answer IDs, and a claims gate refuses uncited claims
- the person checks, corrects or disputes each statement ("Other ways to read this", "This reading doesn't fit me")
- shares a version through an end-to-end encrypted, revocable link
- can rehearse with "your understudy" (Claude, practice only)
- an optional interview (`/interview`: talk with an ElevenLabs AI interviewer, bring a Plaud transcript, or type) adds cited evidence V01...

**Never for hiring, promotion, ratings, pay or discipline.** The hackathon evaluation tooling lives in `/workbench` and `/paste`. It is off unless `LUMIN8R_WORKBENCH=1`, and the product never links to it.

## Repo, box, deploy
- **Repo:** `wchesher/cloudfx` (MIT). The old CircuitPython project is preserved at tag `cloudfx-circuitpython-v1.0`.
- **Box:** 187.124.93.240 (teenyverse.dev). The app runs as docker container `lumin8r` on the shared Caddy edge network `lariac-edge`, port 127.0.0.1:8097.
- **Deploy:** one command, `sudo update-lumin8r`, which is `deploy/update-lumin8r`:
  - It is idempotent and tests each release before swapping it in.
  - Secrets go in only through `sudo update-lumin8r --set-key NAME`. Settings live in `/etc/lumin8r/update.env`.
- **Auto-pull (commit `f5884f8`):** once that commit is deployed, a systemd timer deploys every new commit on main within about a minute.
  - Watch it with `journalctl -u lumin8r-autopull -f`.
  - A commit whose tests fail is skipped and the live release is kept.
- **Pushing:** the previous session could not push to cloudfx, because its git proxy was scoped to another repo. Will uploaded zips by hand through https://github.com/wchesher/cloudfx/upload/main. A session started from the cloudfx repo can push directly, and with auto-pull, pushing is deploying.
- **Tests:** `PYTHONPATH=src .venv/bin/python -m pytest -q`. 309 passed at `f5884f8`. A fresh checkout needs a venv with `anthropic` and `pytest`.

## Code map (src/mefile)
| Area | Modules |
|---|---|
| Assessment data | `kit.py` |
| Answers, scoring, style measures | `answers.py`, `scoring.py`, `style.py` |
| Claims gate | `claims.py` |
| Converter: me.md plus sidecar; variants; share scopes full/coaching; guardrails and the exact refusal text; `disputed` | `converter.py` |
| Other readings per claim | `readings.py` |
| Wethos Style hypotheses | `crosswalk.py` |
| LLM A, Claude; two-turn loading protocol | `runner.py` |
| LLM B, GPT via the OpenAI Responses API; model `gpt-6.1-sol`, set by update-lumin8r | `openai_runner.py` |
| Profile vs no-profile, the `kit_plus_interview` arm, leakage guard | `experiment.py` |
| Judge: blind, 0-4, fails closed, never the model under test | `judge/` |
| Voice (ElevenLabs agent, provisioning, safeguards); Plaud TXT/SRT import; transcript to evidence | `voice.py`, `plaud.py`, `intake.py` |
| Understudy practice library and ask-your-own | `practice.py` |
| Encrypted shares | `shares.py` |
| Workbench API | `team.py` |
| Operator console | `admin.py` |
| Routes | `app.py` |
| Command line | `cli.py` |

Static pages are in `static/`: home (canvas hero in `hero.js`), assessment (`kit.html`), Your file (`index.html` plus `app.js`), `interview.html` plus `interview.js`, `share.html`, `privacy.html`, `responsible-use.html`, `admin.html`, `team.html` (workbench), `paste.html`.

## Docs that matter for the 6:00 submission
- `docs/writeup.md`, `docs/pitch.md`: placeholders to fill in from real results.
- `docs/alternative-intake.md`: the bonus (Section 11) write-up, with a results table to fill and a 60-second script.
- `docs/m3-status-for-mark.md`: every M3 risk checked against the code, the answers to Mark's questions, overclaims fixed, limitations, and future work.
- `docs/judge-mistake-example.md`: a real judge failure. The style check counts a possessive as a contraction and flags a formal writer. It is pinned by `tests/test_judge_known_mistakes.py`. Do not fix it before the panel: it is the documented failure the kit asks for.
- `docs/judge.md`, `docs/team-hub-contract.md`, `docs/voice-intake.md`, `docs/product.md`.

## Open items, in order
1. **Deploy `f5884f8`** (Will uploads the zip). Box steps:
   - `echo 'LUMIN8R_WORKBENCH=1' | sudo tee -a /etc/lumin8r/update.env`
   - `sudo update-lumin8r --set-key OPENAI_API_KEY`
   - `sudo update-lumin8r --set-key ELEVENLABS_API_KEY`
   - `sudo update-lumin8r`
   - then `sudo update-lumin8r --check`
2. **First live calls, all unverified:**
   - OpenAI: three field names are marked UNVERIFIED in `openai_runner.py`.
   - ElevenLabs: agent read, update and search shapes are marked UNVERIFIED in `voice.py`.
   - Try one of each. Paste and the Plaud or typed interview are the fallbacks.
3. **The live run on the workbench:**
   - teammates take `/assessment` and send their answers to the hub
   - an interview with a consenting teammate (Plaud or voice), sent to the hub
   - run LLM A and LLM B by API, then score and judge
   - judge self-check, red-team, two blind human ratings and the agreement statistics
4. **The final, at 4:30:** the volunteer's 55 answers and 4 questions; me.md; 8 responses; at 5:30 the 12 comparison responses; judge all 20; submission.
5. **Fill** `writeup.md`, `pitch.md` and `alternative-intake.md` from the results. Mark each number as measured or not run.
6. **Optional automation, not built:**
   - a one-button final run
   - write-up placeholders filled from the results files
   - a phone link for raters
   - a red-team button
   - the comparison table on `/api/station/results`
7. **Cleanup after the panel:**
   - remove the old inline voice panel `#voiceBox` in Your file (`/interview` replaces it)
   - fix the contraction counter in `judge/features.py`

## Will's words (keep them verbatim; they are the design brief)
- "make the website the product. DOnt include anything that is not product related (like freeze protocol, etc)"
- "this needs productization. Step back from a design perspective and build this out to be an actual product"
- "elegance and delight by design. Make a professional implementation of this that looks corporate without being stodgy"
- "Make a main page and delightful kinetic hero"
- "take this off the spawn design system AND MAKE A CORPORATE psycologically easing design"
- "that looks so generic" / "not beige" / "it looks like publisher 1993"
- "why are we calling it a "kit"" / "that is not pleasing" (the user-facing name is "assessment")
- "convert the verbiage to understudy" (never "twin", "doppelganger", "clone" or "player two")
- "we shouldnt have prompt instructions in the survey"
- "we need to integrate plaud and the voice. its a showstealer"
- "we need some hero kinetic and elegant" / "on theme" / "ELEGANT AF"
- "dont do 7" (he declined a freeze lock)
- "I need this to land"

## Standing rules
- **Privacy:**
  - No secrets in chat; keys only through `--set-key`.
  - Real teammates' answers, profiles and transcripts never go in git (`private/` and the box only).
  - Never put Will's personal details in requests to outside services.
- **Honesty about the person and the product:**
  - Never present simulated answers as the person's statements.
  - Use bounded wording: "your reported preferences", "a starting point, not a complete picture". Never "the way you actually work" or "in your voice".
  - Answers go to the server for one conversion and come straight back; they are not saved. Never say the file is "built in your browser".
- **Voice:** text only; no emotion inference; no voice clone; recording off; the conversation is deleted after the transcript is saved.
- **Style:** no emojis. Short, plain sentences in docs. Teammates have consented to their work being aligned and used.
- **Commits** end with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01DpJ8FXLf2FTyvGM8iKkhBg
  ```

## Shared pages
- **Team plan** (database-backed, shared by link): https://claude.ai/artifact/JKTtNziv7f3KCN8koWhP6d
- **Cohort explainer, "How lumin8r works"** (version 3, bounded wording): https://claude.ai/artifact/HJzsen2jUSjQazjhkGbqPR
