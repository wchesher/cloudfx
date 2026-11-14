# lumin8r: evaluation guide and five-minute presentation

CGU Hackathon, Digital Twin track, sponsored by Wethos. From Mark's draft, checked against the Problem Statement, the Common Kit and what the code does today.

**In one line:** lumin8r is an employee-held, evidence-linked profile for voluntary coaching and communication support. It is not a replica of a person. We win on evidence: a real with-profile versus no-profile comparison, one safeguard shown working with its limit, and one failure we found ourselves.

**How we are graded** (Problem Statement; Common Kit section 13)

| Criterion | Weight | What earns it |
|---|---|---|
| Converter and portable profile | 20% | Answers in, a supported, understandable me.md out, claims linked to answers, unchanged on both models |
| Personality performance | 25% | Panel 15: the three private scenarios match the volunteer's choices and reasons. Volunteer 10: our two writing responses, rated blind. Both models count equally |
| AI judge quality | 20% | Useful, evidence-based evaluations; tested; where it fails shown |
| Ethical AI and responsible design | 20% | Protects the person, real consent and control, addresses misuse and over-trust |
| Transdisciplinary research | 15% | Several disciplines plus real user or practitioner insight, fitted to the workplace |
| Optional intake | up to 10 bonus | Working pathway (4), rationale (2), comparison with time, effort and limits (4) |

Personality performance is decided by the volunteer's answers after the freeze, so it cannot be tuned now. Everything else is earned by the evidence we show and how clearly we explain it.

## Part I: Evaluation guide

Status as of 15:25 Pacific. Our own judge's scores do not decide the ranking (Kit section 8); the panel rewards evidence and clear explanations, not more features or longer profiles (section 13). Met: built and tested (315 tests pass) or met in `docs/requirements-check.md`. Open: built, needs a live run. Gap: not done.

### 1. Criteria, owners and evidence

| Criterion | Weight | Owner | What the panel needs to see | Our evidence | Status |
|---|---|---|---|---|---|
| Converter and portable profile | 20% | Will | Answers in, me.md out, every important claim linked to answers, same file on both models | `converter.py` (no AI), `claims.py` gate, `/app` review, `mefile final`, DEMO01 me.md | Met. Two-model use shown in the live runs |
| Personality performance | 25% | Will + Steven | Panel, 15 points: our responses to the three private scenarios match the volunteer's choices and reasons. Volunteer, 10 points: the volunteer rates our two writing responses blind. Both models count equally | `mefile experiment`, `/workbench#run`, `#results`, `docs/results.md` section 1 | Open: experiment not run |
| AI judge quality | 20% | Will + Mark | Evidence-based scores, tested, one shown failure | `judge/`, `docs/judge.md`, `docs/judge-mistake-example.md`, `/workbench#judge` | Built and met offline. Open: live self-check not run, no human-agreement number |
| Ethics and responsible design | 20% | Mark | Consent, employee control, one safeguard with its limits | Consent screen, `/app` review and share scopes, claims gate, `private/` gitignored | Met. Open: live fairness probe |
| Transdisciplinary research | 15% | Steven + Mark | Real practitioner insight that changed the design | Discipline sources in `docs/`, `docs/market-research.md` | Gap: practitioner interviews not done |
| Optional intake | up to 10 bonus | Will + Steven | Working alternative intake compared with the assessment on quality, time and effort | `/interview` (typed), Plaud import, `docs/alternative-intake.md` | Open: needs one run with a consenting teammate, timed against the assessment. Voice interview working since the 15:20 deploy; typed and Plaud also work |

### 2. Verification checklist

**A. Converter**
- [x] `mefile convert examples/example_build_answers.json`: DEMO01 me.md with 32 claims, each citing answer IDs.
- [x] Reverse scoring, missing-answer rule and the Emotional Stability label pass `tests/test_scoring_and_runner.py`.
- [x] The claims gate refuses uncited claims and any claim citing S02, S04, S06, W02 or W04.
- [ ] `mefile final` on the volunteer's build file (`/workbench#final`): me.md generated, gate passes, no hand edits.
- [ ] The same me.md loaded unchanged into LLM A and LLM B. Served model versions recorded.

**B. Personality testing**
- [x] Loading protocol coded: new conversation, me.md first, then the question exactly (`runner.py`, `openai_runner.py` with `store: false`).
- [ ] `mefile experiment` on teammates' files: profile versus no-profile on both models, scored against held-out answers. Summary copied to `docs/results.md` section 1.
- [ ] Eight responses (4 questions x 2 models) submitted and locked by 5:00.

**C. AI judge**
- [x] Each verdict carries question ID, run ID, a 0-4 score or null with insufficient evidence, explanation and evidence IDs, on two dimensions (`reference_resemblance`, `profile_consistency`).
- [x] Generic-writing flag. The judge never sees the run ID or source.
- [x] Fails closed: an error or invalid verdict gives null scores, never a guessed one.
- [x] Documented failure reproduces: `docs/judge-mistake-example.md`, pinned in `tests/test_judge_known_mistakes.py`.
- [ ] Live self-check (`/workbench#judge`, "Run the self-check") with `MEFILE_JUDGE_MODEL` set to a model not under test. Pass count recorded.
- [ ] Two teammates rate blind (rating sheet, then "Compare with the judge"). No agreement number is quoted until this is done.
- [ ] Twenty evaluations (our 8, 8 no-profile, 4 Wethos) submitted by 5:30.

**D. Ethics and controls**
- [x] Consent recorded before any processing. The server enforces the consent token.
- [x] Download in `/app` stays locked until the person reviews the file and the gate passes.
- [x] Real answers stay under `private/` (gitignored). Only DEMO01 is in git.
- [x] Every me.md states it is an AI-generated representation and not for hiring, promotion, discipline or ranking.
- [ ] Fairness probe run live: polished English does not score higher.
- [ ] Safeguard shown live: the gate refuses a claim that cites S02.

**E. Workplace fit and submission**
- [x] Finish on the assessment sends both answer files to the team and opens Your file on the review. Nothing to download. Progress is saved on the server.
- [ ] Two practitioner interviews (Steven), with one design change traced to them.
- [ ] Typed or Plaud interview with a consenting teammate, timed against the assessment.
- [ ] Submission package from `/workbench#final`, `docs/writeup.md` with results, repo link, by 6:00.

### 3. Show results, not features

The panel scores what the responses did. Fill one row per claim we present, from frozen results only. Unmeasured cells say "not run".

| Claim and answer IDs | Observed influence on the response | Resemblance to the recorded answer | Judge score and explanation | Counterexample or failure | Safeguard |
|---|---|---|---|---|---|
| DEMO01 C01: "Deals with disagreement or unfairness directly rather than letting it pass or going around people" [S01, S05] | [from results: with-profile response versus no-profile on the same question] | [from results] | [from results: 0-4 or null, with the judge's explanation] | A generic reply that picks the popular choice still earns at least 2 of 4 on a scenario (`docs/judge.md`) | C01 cites build answers only. A claim citing S02 would be refused by the gate |


### 4. Schedule

| Time | Step | Owner | Tool |
|---|---|---|---|
| 4:30 | Freeze code, prompts, rubric and settings. Record the commit. | Will | git |
| by 5:00 | Volunteer's me.md (gate passes, unedited) and eight responses, submitted and locked | Will + Steven | `/workbench#final` (LLM A by API; LLM B by API or paste) |
| 5:00-5:30 | Twenty evaluations, blind to source | Will + Mark | `/workbench#final`, judge step |
| by 6:00 | Submission package, write-up and results filled | Steven + Mark | `/workbench#final` package, `docs/results.md`, `docs/writeup.md` |
| 6:30 | Panel: 5 minutes plus 3 minutes of questions | Steven, Will present; Mark leads Q&A | Slides |

## Part II: Five-minute presentation

The order is fixed by Common Kit section 13: (1) me.md with one claim and the answers behind it, (2) the app from answers to a reviewed file, (3) the judge on one response and how we checked it, (4) what comparing the two models and the no-profile responses taught us, including one failure. Three minutes of questions follow.

**Ground rules for the five minutes**

- Every number is a `[RESULT: ...]` placeholder. Fill it from the frozen results only. If it was not measured, cut the line; do not round, estimate or carry a number over from a practice run.
- Demo data is the fictional DEMO01 unless the volunteer has authorized showing their own file.
- Spoken words total about 590, which is 118 words a minute. Rehearse with a timer; if you run long, cut the sentences marked *(cut if long)*.
- Have every backup screenshot open in a second browser window before the panel starts, in slide order.

| Slide | Time | Speaker | Kit item |
|---|---|---|---|
| S1 | 0:00-0:45 | Steven | (1) me.md, one claim, its answers |
| S2 | 0:45-2:00 | Will | (2) from answers to a reviewed file |
| S3 | 2:00-3:15 | Will | (3) the judge on one response, and how we checked it |
| S4 | 3:15-4:30 | Steven | (4) two models and no-profile, one failure |
| S5 | 4:30-5:00 | Steven (or Mark) | responsible use and close |

---

## S1. One claim and the answers behind it (Steven, 0:00-0:45)

**On screen**

- microverse.cloud/app#file, DEMO01's file open on Your file.
- Claim C01 selected: "Deals with disagreement or unfairness directly rather than letting it pass or going around people [S01, S05]".
- Its two evidence chips, S01 and S05, open beside it, showing the choice and the person's own reason for each.

**Say** (about 90 words)

"This is lumin8r. An employee answers a 20 to 30 minute assessment and gets one file, me.md, that they own. Here is one claim from it: deals with disagreement directly rather than letting it pass. Click it and you see the two answers behind it. In S01, the manager sets a deadline everyone nods at, and this person says so in the meeting. In S05, a colleague takes credit, and they raise it privately. Every statement cites its answers. Middle scores say no clear tendency. No AI writes this file: same answers, same file."

**Backup if the demo fails:** screenshot of C01 selected with the S01 and S05 chips open. If the site is down, open a local copy of DEMO01's generated me.md (built from `examples/example_build_answers.json`) and point at the line ending `[S01, S05] (C01)`.

---

## S2. From answers to a reviewed file (Will, 0:45-2:00)

**On screen** (in this order, about 15 seconds each)

1. microverse.cloud/assessment, the last page with the Finish button.
2. Finish lands on /app#file, already on the review. Point out that nothing was downloaded.
3. Click the S05 chip under C01, change the answer, and show the file rebuild.
4. "Other ways to read this" under a claim, then the "This reading doesn't fit me" button.
5. "Rehearse with your understudy", with its label visible: "AI-generated simulation. Your understudy is Claude, an AI."
6. The share step: coaching or full version, and an end-to-end encrypted link with its "Turn off" button.

**Say** (about 150 words)

"Here is the path from answers to a reviewed file. The employee finishes the assessment. Finish sends the two answer files to us and opens Your file straight on the review. No downloads.

The converter uses no AI and gives the same file every time. Before anything is exported, our claims gate checks every claim. A claim with no answer behind it, or one that leans on a held-out test answer, blocks export. That gate has a limit: it checks that the citations exist, not that the reading is right. So the second safeguard is the person.

They can correct an answer, and the file rebuilds. They can see other ways to read a claim, or dispute it with 'This reading doesn't fit me'. They can rehearse with an understudy, clearly labelled as an AI simulation. Then they choose a coaching or a full version and share it through an encrypted link they can turn off."

**Backup if the demo fails:** a short screen recording of Finish landing on the review, the S05 edit rebuilding the file, and the share step. Stills of "Other ways to read this", the dispute button, the understudy label and the "Turn off" control. A still of the gate refusing an export that cites S02 *(the safeguard; show it even if the live demo works, if time allows)*.

---

## S3. The judge on one response, and how we checked it (Will, 2:00-3:15)

**On screen**

- microverse.cloud/workbench#judge, one row from the final evaluations: `[RESULT: question ID, model]`.
- The response, the person's recorded answer, and the two scores side by side: resemblance to the person `[RESULT: x/4]`, consistency with the profile `[RESULT: x/4]`.
- The cited evidence IDs `[RESULT: IDs]` and the generic-writing flag `[RESULT: yes/no]`.
- A second panel: self-check `[RESULT: x of N probes passed]`; agreement with blind human ratings `[RESULT: exact and within-1 agreement, n=]`.

**Say** (about 150 words)

"Here is our judge on one response. It scores 0 to 4, or returns no score when there is not enough evidence. It scores two things separately: does this resemble what the person actually said, and is it consistent with the profile. A response can fit the profile and still miss the person. This one got `[RESULT: x]` on resemblance and `[RESULT: y]` on consistency, citing `[RESULT: IDs]`. It also flags generic writing and ignores polish. It never knows who wrote the response, and it never runs on a model we are testing.

How did we check it? We built probes that should break it: a good answer against a contradicting one, fluent filler, and the same content in polished and in plain non-native English, which must land within one point. It passed `[RESULT: x of N]`. *(cut if not measured)* Two teammates also rated blind, and the judge agreed with them `[RESULT: agreement, n=]`."

**Backup if the demo fails:** screenshot of the same row in `evaluations.md`, and the printed output of `python -m mefile.judge selfcheck` from the final run, with the `judge_model_served` line visible.

---

## S4. What comparing taught us, and one failure (Steven, 3:15-4:30)

**On screen**

- One table: the same questions answered by LLM A with the profile, LLM B with the profile, and each with no profile. Columns: resemblance score per condition `[RESULT: mean, n=]`.
- One row highlighted for the failure: `[RESULT: question ID, model]`, where no-profile scored at or above the profile.

**Say** (about 145 words)

"What did comparing teach us? With no profile, `[RESULT: what the no-profile answers did]`. With the profile, LLM A moved `[RESULT: change]` and LLM B moved `[RESULT: change]`. The same file, unchanged, moved the two models by different amounts. `[RESULT: which model gained more, and on what kind of question]`. *(cut any sentence whose number was not measured)*

Our design bet was that the person's own choices and reasons help a model more than trait labels. `[RESULT: whether the comparison supports it]`. *(cut if not measured)*

Now one failure. On `[RESULT: question, model]`, the no-profile answer scored as well as ours or better. `[RESULT: cause, for example the person chose the popular option, so the profile added nothing]`. With one recorded answer per question, a low score is evidence, not proof."

**If no such row exists in the frozen results**, use the documented judge mistake instead (docs/judge-mistake-example.md) and say: "Now one failure, and it is in our own judge. A formal writer who never uses contractions was flagged for losing contractions they never use. The cause: our counter read possessives like 'supplier's' as contractions. The flag costs at most one point and the judge model can dismiss it, but it falls on formal and non-native writers, the people our fairness rules protect. It is pinned in a test, and the fix is written down."

**Backup if the demo fails:** the experiment table and the failure row as stills. For the judge-mistake version, a still of the reproduce output showing `P3 "I am": lost signature marker`.

---

## S5. Responsible use and close (Steven or Mark, 4:30-5:00)

**On screen**

- Three lines: "Held by the employee. Every claim cited. Reviewed before it is shared."
- The use limit as printed in every me.md: voluntary coaching, reflection and communication support only. Not for hiring, promotion, discipline or ranking.
- microverse.cloud

**Say** (about 60 words)

"lumin8r is a voluntary coaching tool, not a replica of a person. The employee holds the file, sees the answers behind every claim, can correct or dispute it, and decides who sees it and for how long. Every me.md states its own limit: never for hiring, promotion or ranking. Try it at microverse.cloud. Thank you."

**Backup:** a single still of this slide. No live element.

---

## Words to avoid on stage

- Say "assessment" for what the participant takes. Use "Common Kit" only when naming the challenge document.
- Do not call the understudy "you" or "the person". It is an AI simulation, and the slide says so.
- Do not describe the judge's score as a ranking of teams, or as proof that the profile is right.
- Do not say the gate checks that a claim is true. It checks that the citations exist and that no held-out test answer is used.

## Part III: Team roles

| Person | On stage | Owns |
|---|---|---|
| Steven | Principal presenter: opening, comparisons, close | Workplace context, research, practitioner quotes |
| Will | Technical presenter: converter demo, judge demo | Implementation, runs, reproducibility |
| Mark | Ethics and risk lead; optionally the last 30 seconds | Consent, misuse tests, fairness, limitations |

Who answers in Q&A:

- **Will:** how the converter, judge, runs and data storage work, and what the numbers mean.
- **Mark:** consent, employer use, impersonation, fairness, language, limits of our safeguards.
- **Steven:** workplace fit, the Wethos use case, research and practitioner input.

If a question crosses areas, the owner answers first and one other person adds at most one sentence.

## Part IV: Q&A brief

**1. How do you know the model actually used the profile? (Will)**
The same prompts go to each model with and without me.md, and the judge compares both against the person's held-out answers, which never reach the converter or the models. The organizers' no-profile responses give a shared baseline. The claims gate blocks export if a held-out answer (S02, S04, S06, W02, W04) leaks in. We report only the difference we measured; if a comparison was not run, we say so.

**2. How reliable is your judge? (Will)**
It scores 0 to 4, or returns null with "insufficient evidence", and every score cites answer IDs. It fails closed: a bad or missing verdict gives no score, never an invented one. It never grades the model under test, and `mefile.judge selfcheck` runs fixed probes for fairness, generic filler and memorization. We document a real mistake in `docs/judge-mistake-example.md`. We have no human-agreement figure yet, and we do not claim one.

**3. Can an employer compel this, or use it for pay or personnel decisions? (Mark)**
Consent is recorded on the server, and the consent screen says a manager's invitation does not make it required. Every me.md must carry a refusal of hiring, promotion, rating, pay and discipline use, or export is blocked. That is a written rule, not a technical lock: a recipient can ignore it, so the real protection is an organizational policy.

**4. Could the twin's answers be passed off as the person's? (Mark)**
Every me.md opens with "AI-generated representation" and states that simulated answers are not the person's statements, approval or commitments. The app labels each answer a simulation, and the file tells the model not to deny being an AI if asked. Once a file is pasted elsewhere, we cannot control how it is presented.

**5. What is the realistic Wethos use? (Steven)**
An employee shares the coaching version with a coach to prepare for a session, or uses it to plan a hard conversation with a teammate. We map answers to the four Wethos Style scales as labelled hypotheses with evidence IDs, never as scores.

**6. What about language background and writing style? (Mark)**
The judge prompt has an explicit fairness rule: polish and corporate phrasing do not raise the score. A self-check probe tests that a polished and a plain version of the same answer land within one point. Claims that rest on the vocabulary items B05 and B40 carry a language caveat in the file.

**7. Where is the data stored? (Will)**
Saved progress sits on our server under a random ID in an HttpOnly cookie, never in browser storage. It is deleted 30 days after the last change, or at once on "Forget this device" or "Withdraw consent". Share links are encrypted in the browser, and the server never holds the key. Real participants' data never goes in git.

**8. Why no AI in the converter? (Will)**
The converter uses fixed rules, so the same answers always give the same file. Every claim traces to the answers behind it, and nothing is invented. Models only read the file.

**9. What fails? (Will, then Mark)**
The judge's style check counted a possessive ("the supplier's") as a contraction and flagged a formal writer for "losing" contractions they never use. It is pinned in tests and the fix is documented. Our results rest on small samples: one recorded answer per question and a one-day test, so a score is evidence, not proof.

**10. Can a claim cite a real answer and still be wrong? (Mark)**
Yes. The gate checks that claims point at real answers, not that the answers support the wording. That is why export needs the person's own review, and why the app shows other ways to read each claim and lets the person dispute one.

## Part V: What to protect in the last hour

- **Freeze at 16:30.** After that, no change to code, prompts, the judge rubric or settings. Run only what is frozen.
- **The 5:00 and 5:30 deadlines come first.** Eight responses locked by 5:00, twenty evaluations by 5:30. Slides and polish wait.
- **The optional interview is bonus only.** Voice works again, but run it only if a teammate has 15 minutes that nothing above needs. It never replaces the core deliverables.
- **Show meaningful use against a no-profile baseline.** The comparison with and without me.md is our strongest evidence. Show it before any feature.
- **Never invent a number.** If a figure was not measured, cut the line. A blank is better than a guess.
- **Present red-team results as bounded evidence.** Our misuse probes cover specific attacks on fictional data. Say which ones were run and what held, not that the system is safe.
