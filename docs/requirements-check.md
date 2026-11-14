# Requirements check

Every requirement in the problem statement and the Common Kit, where it is met, and how we know. Status:
**met** (built and tested), **open** (built, needs a live run or a person), **gap** (not built).
Last checked 2026-11-14 against https://microverse.cloud (release d618b5a and later).

## Converter and profile (20%), Kit sections 6 and 7

| Requirement | Where | Status |
|---|---|---|
| Accept the organizer's build file and generate a downloadable me.md, with no manual editing | `converter.py`, `/app`, `/team#final`, `mefile final` | met (tests; live site) |
| Field names exactly as the examples; keep question IDs unchanged | `answers.py` | met |
| Represent only tendencies the build answers support | zero-AI converter; middle scores read "no clear tendency" | met |
| Link important claims to source IDs (B13, S01, W03) | every claim cites IDs inline and in the claim index | met |
| Distinguish measured traits, reported preferences, writing style | claim kinds: measured, reported, observed_style, limit | met |
| Keep conflicting evidence visible | section 4 lists opposite-direction items per domain | met |
| Readable and available for review before sharing | `/app` review station, download locked until reviewed and the gate passes | met |
| Work unchanged on both designated LLMs | plain markdown, no model-specific syntax; same file pasted to both | met (to be shown in the live runs) |
| Person can correct source answers and regenerate | edit any answer in `/app`; the file rebuilds | met |
| Label the profile and simulated answers as AI-generated representations | banner in me.md and the app; the twin's answers are labelled a simulation | met |
| Scoring: reverse items with 6 minus the response; mean from 1 to 5; keep the label Emotional Stability | `scoring.py`, `tests/test_scoring_and_runner.py` | met |
| Missing-answer rule: 1-2 skipped, average and say how many; 3+, not scored; never fill a gap | `scoring.py`, tested | met |
| Show the item IDs behind each domain score | trait table lists the items; claims cite the answered items | met |
| Vocabulary items: record the language limitation, do not change scores | limit claim on B05 and B40 | met |
| Do not equate a domain score with intelligence, competence or suitability | trait section wording | met |

## Personality performance (25%), Kit sections 9 and 10

| Requirement | Where | Status |
|---|---|---|
| Loading protocol: new chat, memory off, me.md as the first message, then the question exactly | `runner.py` (API), paste station and final rows (manual), run sheet | met |
| Same questions and word limits in every condition | the question file drives every run | met |
| Profile versus no-profile comparison on both models | `experiment.py`, `/team#run` and `#results` | open: needs teammates' kits and runs |
| Record the model versions and how the file was loaded | API runs record the served model; pasted runs record the model name shown and the protocol | met |
| Final: the volunteer's me.md and eight responses by 5:00 | `/team#final` | open: on the day |

## AI judge (20%), Kit section 8

| Requirement | Where | Status |
|---|---|---|
| Identify meaningful matches and mismatches | judge output fields `matches`, `mismatches` | met |
| Separate consistency with the profile from resemblance to recorded answers | two scored dimensions | met |
| Distinguish personality evidence from fluent or generic writing | `generic_writing` flag plus a typicality measure | met |
| Recognize insufficient evidence | null score with `insufficient_evidence` | met |
| Cite the answers behind each rating | `evidence_ids`, checked against the build file | met |
| Declare the scale | in every report and in the prompt | met |
| Per response: question ID, run ID, score and scale or insufficient evidence, explanation, evidence IDs | `judge.py`, `report.py` | met |
| Handle question IDs it has not seen | uses the question file; tested | met |
| Show it tells good from poor, and at least one case where it fails | self-check probes (button in `/team#judge`); AI-to-human agreement kit | open: press the self-check button on the live site (stand-in model fails 2 of 7) |
| Score 20 outputs: our 8, 8 no-profile, 4 Wethos; blind to source | `/team#final` judge step | open: on the day |

## Ethics and responsible design (20%), problem statement

| Requirement | Where | Status |
|---|---|---|
| Agreement to collecting, sharing and AI processing; an employer's request does not replace it | consent screen; consent token enforced on the server | met |
| Explain who can access the answers and profile, and why | consent copy, front door, kit page | met |
| Keep real personal materials out of public repositories | `private/` and `consent/` gitignored; teammates' data stays on the box | met |
| Employee reviews the profile, questions claims, corrects answers, decides on sharing | review station, question-a-claim, share scopes, withheld sections | met |
| Avoid unsupported inferences, fixed labels, exaggerated claims | claims gate | met |
| Language background: polished English must not score higher | judge rule and the fairness probe | open: live probe |
| Demonstrate one safeguard and its limits | the gate refusing a leaked or unsupported claim; limits documented | met |
| Not for hiring, promotion, discipline or ranking; simulated answers are not the person's statements | printed in every me.md and on the site | met |

## Transdisciplinary research (15%)

| Requirement | Where | Status |
|---|---|---|
| Knowledge from several disciplines | psychometrics, law, security, HCI, sociolinguistics (docs) | met |
| Real user or practitioner insight | two practitioner interviews (Steven) | gap: needs the interviews |

## Process and submission, Kit sections 2, 11, 12, 13

| Requirement | Where | Status |
|---|---|---|
| A consenting teammate completes the kit without AI help; record the actual time | `/kit`: consent, timer, organizer files, send to the hub | met |
| Keep test answers out of profile generation | gate refuses test IDs; uploads refuse mixed files; tests prove the answerer never sees them | met |
| Optional alternative intake with a time and effort comparison | voice interview built; ElevenLabs agent not created | gap: needs the agent and a run |
| Submit code and run instructions, me.md, both models' responses, 20 evaluations, a short write-up, optional intake | GitHub repo; `/team#final` zip; `docs/writeup.md` | open: write-up results on the day |
| Presentation order: me.md claim, app, judge, comparisons with one failure | `docs/pitch.md` | met (results are placeholders) |

## Assumptions we are relying on

| Assumption | Basis | If it is wrong |
|---|---|---|
| The volunteer's build file uses the same build IDs (B01-B50, S01, S03, S05, W01, W03) | Kit section 2; README "same structure" | Scenario patterns rely on `OPTION_SIGNALS` for S01, S03, S05; other IDs still render but lose the pattern claims |
| Private questions come in the example question format with a ready `prompt` | 00-examples README | The final step needs `prompt`; without it, paste the wording by hand |
| Comparison responses are `{run_id, question_id, text}` with no source | example file | The judge reads only those three fields |
| The volunteer's test answers come in the test-answers format | README | The judge's reference comes from `scenarios[]` and `writing[]` |
| Pasting a ~2,800-word me.md into both chat UIs works | typical context limits | Use the short variant (about 1,800 words), same claims |
| A different model judging is fairer than the model under test | self-preference risk | The judge refuses Opus 5.5 unless overridden |
| Restarting the shared edge is acceptable when the site file changes | Saturday, no classes | Run `update-lumin8r` outside school hours on school days |
| The team code is enough protection for teammates' data on the box | small team, short event | Delete `/var/lib/lumin8r/people` after the event |
