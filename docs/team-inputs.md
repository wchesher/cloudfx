# Team inputs, ingested

What the team has put down outside the repo, and how it lines up with what is built. Checked 2026-11-14.

## Sources looked at
| Source | Owner | What it holds |
|---|---|---|
| "Digital Twin Game Plan" (claude.ai artifact AB4KLfJj...) | the team's account, updated today | the challenge in one minute, the clock, three build plans with rubric-fit estimates, required-in-every-plan rules, observations from the example files, open questions |
| mefile Team Plan (JKTtNziv...): drafts, inbox, tasks | Mark, Steven, Builder | empty so far |
| Shared with the account: "A Strawman AI Taxonomy", "Teenyverse SDG UCD Framing", "AI Startup Collaboration Matching Tool" | outside the organization, unsigned | not hackathon material: an AI-use taxonomy (tier and mode), a page with no readable content, a startup-matching prototype. Nothing ingested |

## Game Plan: decision and how the build compares

The Game Plan recommends **Hybrid**: code does the math, a model writes the decision habits and style notes,
and a validator strips any line without a valid source ID, with the rules-only file as the fallback switch.

**The build today is the Game Plan's "Rules only" plan, plus everything around it**: zero-AI converter, claims
gate (the Game Plan's validator, applied to every claim), evidence-first ordering, variant test, live judge with
code checks first and one model call per response, review app, team hub.

| Point | Game Plan | Built | Note |
|---|---|---|---|
| Who writes habits and style | a model, validated | code (option signals, style counts, verbatim quotes) | **Open decision, below** |
| Validator that strips uncited lines | yes, the demo safeguard | the claims gate refuses export instead of stripping | same intent; refusal is stricter and demoable |
| Fallback if the API fails at 4:30 | switch to rules only | no API in the converter, so nothing to fall back from | met by design |
| Judge | code checks, then one API batch for 20 | code checks, then one call per response, blind, fails closed | met |
| Bonus intake only if the base works by 1:30 | yes | voice intake built; agent not created | on the Game Plan's rule, skip it unless the base is green |
| Run sheet for 4:30-5:00, who runs the 8 chats | open | `/team#final` with copy buttons and model-name capture | assign a person |

## Observations from the example files, checked against the converter
| Game Plan observation | In me.md today |
|---|---|
| Trait means sit near the middle, so trait means alone read like no profile | yes: middle domains are marked "no clear tendency; do not lean on this domain", and the evidence-first order puts choices and writing first |
| The useful evidence is item-level conflict (B27 soft heart 5, B12 insult people 4) | yes: section 4 lists the B27 versus B12 conflict |
| Decision habits carry over (a time limit in S03) | yes: "takes a bounded, time-boxed risk with a fallback [S03]" (S04 is held out and never used) |
| Messages run 13 to 50 words, each ends with an ask | partly: the length range is a claim; "ends with a question or request" is only caught when the message ends in a question mark (W03, not W01) |
| Comparison responses carry no source; the judge scores blind | yes |
| Scorer checkpoint (3.10, 3.50, 3.11 with 9 items, 2.80, 3.00) | yes, pinned by tests/test_scoring_and_runner.py |

## Open decision for the team
**Keep the converter rules-only, or add the Game Plan's model-written habits?**
- Rules-only (built): reproducible, no failure point at 4:30, every line traceable by construction. Risk: the
  file can read mechanically on new scenarios.
- Hybrid: richer habit statements. Cost: a model call inside the frozen pipeline, run-to-run variation to pin and
  record, and about 90 minutes of build and test before 3:30.
- Recommendation: settle it with data, not taste. The variant experiment (`/team#results`) already compares
  file designs on held-out answers. Add hybrid only if rules-only loses clearly on the teammates' data.

## Still open from the Game Plan
- Who is modelled during development, and has each agreed to both AI services (the `/kit` consent records it)
- Who runs the 8 chats between 4:30 and 5:00 (`/team#final`)
- Who owns the write-up (`docs/writeup.md`) and the talk (`docs/pitch.md`)
- Where we submit (announced at kickoff)
