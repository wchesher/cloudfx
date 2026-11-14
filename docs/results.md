# Results

**Status: nothing measured yet.** Every table below is empty until its run happens. Fill in only numbers from frozen runs; if something was not run, write "not run" and keep the row. Never put a person's answers, choices or messages here: this file is in git. Aggregates only; the full per-response tables stay on the server (`/var/lib/lumin8r/experiment/`).

## 1. Development comparison (Common Kit section 9)

Teammates' kits, each with their held-out answers (S02, S04, S06, W02, W04), run in every condition: no profile and each me.md variant, on LLM A and LLM B. Same questions and word limits in every condition; a new conversation per question; me.md as the first message, then the question exactly.

How it was produced (on the server, workbench `/workbench#run` and `#results`, or):

```bash
PYTHONPATH=src .venv/bin/python -m mefile experiment --people private/people --judge --llm-b api --out private/experiment
```

Copy only the first table of `private/experiment/results.md` (the summary) here.

| Model | Condition | Scenario choices correct | Accuracy | Lift over no profile | Scenario resemblance (0-4) | Writing resemblance (0-4) | Over word limit | Flagged generic |
|---|---|---|---|---|---|---|---|---|
| A | none | not run | | - | | | | |
| A | evidence_first | not run | | | | | | |
| B | none | not run | | - | | | | |
| B | evidence_first | not run | | | | | | |

- People: not run (n = ). Models as served: LLM A `...`, LLM B `...` (from `results.json`). Judge model: `...`.
- Small samples: a few people times three scenarios. Give counts with every percentage; one or two answers either way is noise.
- What the comparison taught us (one or two sentences, including one failure):

## 2. Judge self-check (Common Kit section 9: tells good from poor; at least one failure)

`/workbench#judge` "Run self-check", or `PYTHONPATH=src .venv/bin/python -m mefile.judge selfcheck --out private/selfcheck` with `MEFILE_JUDGE_MODEL` set to a model that is not under test.

| Probe | Expected | Result |
|---|---|---|
| live run | | not run |

- Judge model: `...`. Passed: of . The offline stand-in (`--fake`, plumbing only) passes 7 of 10; it is not the judge.
- Documented failure: `docs/judge-mistake-example.md` (the style count reads a possessive as a contraction and flags a formal writer).

## 3. Judge agreement with people

Two teammates rate the same answers blind (`ratesheet`, then `agreement`).

- Not run. Do not claim an agreement number unless this row is filled.

## 4. Final evaluation (Common Kit section 10)

| Item | Due | Status |
|---|---|---|
| Volunteer's me.md (generated at the freeze, unedited) | 5:00 | not run |
| Eight responses (4 questions x 2 models) | 5:00 | not run |
| Twenty judge evaluations (our 8, 8 no-profile, 4 Wethos) | 5:30 | not run |

Judge mean resemblance by source, once scored (0-4, null counted separately):

| Source | n | Mean | Insufficient evidence |
|---|---|---|---|
| Our profile, LLM A | 4 | | |
| Our profile, LLM B | 4 | | |
| No profile (both models) | 8 | | |
| Wethos twin | 4 | | |

Our judge's scores do not decide the ranking (Kit section 8); they are reported as evidence of how the judge behaves.
