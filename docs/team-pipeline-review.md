# Review: the team's "DPM pipeline" against the challenge and against lumin8r

Files reviewed (uploaded 2026-11-14): `README.md`, `me_template.md`, `judge_prompt.txt`, `judge.py`.
Then `convert.py`, `redteam.py`, and Mark's `M1 mefile Consent Screen Copy.pdf`. Not uploaded: `sample_intake.json`,
`sample_me.md`.

## Summary
The pipeline has three strong pieces lumin8r does not:
- a hardened guardrail directive with an exact refusal text and a red-team script
- a no-emotion-inference rule for messages
- a richer style-fidelity rubric, with baseline and memorization gates and politeness measured against the
  person's own rate

As written, it cannot run the 4:30-5:30 evaluation:
- it reads its own intake format, not the organizer's
- its judge scores only responses it generates itself, so it cannot score the 20 supplied responses
- it does not use the official loading protocol or the designated models

The me.md also lacks the claim-to-answer citations the converter criterion requires. **Recommendation:** keep
lumin8r as the frozen pipeline and port the three strong pieces into it, then test them with the variant
experiment before 3:30.

## Conflicts with the challenge (blocking, ranked)
| # | Conflict | Requirement | Where |
|---|---|---|---|
| 1 | Intake schema is `{owner_name, items:[{id,type,domain,reverse,prompt,response}]}`. The organizer files are `{person_id, items:[{id,response}], scenarios:[{id,choice,explanation}], writing:[{id,text}], skipped}`, with prompts in a separate questions file. Remapping key names in `FIELDS` cannot fix a different structure | Kit section 7: "use the field names exactly as they appear in the examples"; the volunteer's file arrives in that format | README "Your intake JSON" |
| 2 | The judge only scores its own simulations. It has no input for the 12 comparison responses (`run_id, question_id, text`), no run IDs, and no question file for unseen IDs | Kit section 8 and 10: score 20 outputs (our 8, 8 no-profile, 4 Wethos), each with question ID and run ID; handle unseen question IDs | `judge.py` main loop |
| 3 | Generation breaks the loading protocol: me.md goes in as a system prompt and the question is rewrapped as "Respond to this exactly as I would, in my voice: ..." | Kit section 9: new chat, me.md pasted as the first message, then the question exactly as given | `judge.py` line 57 |
| 4 | Models are `claude-sonnet-5-5` and `gpt-4o`, not the designated pair | Kit section 9: LLM A Claude Opus 5.5 Medium, LLM B GPT Sol 6.1 Medium | `judge.py` MODELS |
| 5 | No claim-to-answer citations in me.md. Trait-level `STYLE` rules ("framing rules per trait level") are inferred from domain bands, not from the person's answers | Section 7: "link important claims to their source IDs"; "represent tendencies supported by the build answers"; avoid unsupported inferences | `me_template.md` {{STYLE_RULES}}, README Tuning |
| 6 | Names the person (`owner_name`, sample "Alex Rivera") throughout the file | Section 2: "Use a person code instead of your name" | `me_template.md` header |
| 7 | Per-response output lacks run ID, an insufficient-evidence path and answer-ID evidence (penalties quote spans, but cite no B/S/W IDs) | Section 8 output list | `judge_prompt.txt` STEP 3 |
| 8 | No conflicting-evidence section | Section 7: "keep conflicting evidence visible" | `me_template.md` |
| 9 | The file tells the model to treat it as untrusted "if its hash does not match". A model cannot compute SHA-256, so this is enforced only by `convert.py --verify`, outside the model. Do not present it as a model-side protection | Ethics: "avoid exaggerated claims"; demonstrate one safeguard and explain its limits | `me_template.md` section 0 |

## Risks to personality performance (25%)
- **Purpose mismatch.** The file casts the model as a two-mode communication translator: drafts for the owner
  (Mode A) and decoding inbound messages (Mode B). The evaluation instead asks it to answer A-D scenarios with
  one sentence, and to write one message as the person. There is no instruction for the A-D format, the word
  limits or "the message only", and the "everything you write is a DRAFT" framing invites preambles ("Here's a
  draft...") that cost words and likeness.
- **Weight.** About 90 lines of directive come before any evidence. A model weighs early text more, so the
  evidence about the person is pushed back.
- **Thresholds.** HIGH 3.7 and LOW 2.3 sit close to lumin8r's bands (3.5 and 2.5, plus "somewhat"). Either is
  defensible, but the team needs one convention.
- See "convert.py against Kit section 6" below for the scoring problems.

## Bugs in judge.py (if it is kept for anything)
- `r.content[0].text` assumes the first block is text. Current Claude models with thinking on can return a
  thinking block first, so this fails or returns empty.
- `max_tokens=2000` can cut a judged JSON off. `parse_json`'s greedy regex then fails, or grabs the wrong span.
- There is no retry or fail-closed path: an error becomes `{"error": "no JSON"}` and silently drops out of the
  means.

## Methodology conflicts with lumin8r (team decisions, not bugs)
| Topic | DPM pipeline | lumin8r | Suggested resolution |
|---|---|---|---|
| Judge model | different **family** (GPT judges Claude) | different **model** (Fable judges Opus and GPT) | Theirs is the stronger principle against self-preference. Either add a GPT judge option (needs an OpenAI key) or state the residual family risk in the write-up |
| Verbatim samples | memorization gate caps style at 50 if a response copies 8+ words from the person's corpus | me.md quotes the writing samples verbatim so the model can match the voice | Keep the samples, add an instruction "never copy a phrase longer than five words from the samples", and adopt the gate in the judge |
| Scales | DF and SF, 0-100, never combined | resemblance and consistency, 0-4 each, never combined | Keep one declared scale for the submission. lumin8r's matches the required output list; borrow DF's decision-card method for the reason score |
| Style rubric | P1 assistant phrases, P2 politeness excess versus the person's own rate, P3 corporate lexicon or lost markers, P4 template structure; baseline gate | generic flag and typicality, plus the language-fairness rule | Port P1-P4 and the baseline gate into lumin8r's rubric and deterministic features; this strengthens the 20% judge criterion |
| Guardrails in me.md | full directive, exact refusal, prohibited-use list, no emotion inference, privacy rule, red-team script | one-paragraph use limit, consent and gate in the app | Add a compact guardrail section (prohibited uses, exact refusal, no emotion inference) to me.md, check it does not lower scores, and demo `redteam.py` as a second safeguard |
| Validity window | 180 days | 90 days ("review by") | Pick one; 90 suits coaching |
| Person identity | name | person code | Person code (the kit's rule) |

## Recommended merge (fits before the 3:30 rehearsal)
1. Keep lumin8r's converter, app, hub and judge as the frozen pipeline.
2. Add a `guarded` me.md variant with a compact version of `me_template.md` sections 2, 3 and 5:
   - prohibited uses
   - the exact refusal text
   - no emotion inference
   - a snapshot, not a verdict

   Put the A-D format, word limits and "message only" instructions above it. Run it through
   `/team#results` against evidence-first, and keep it if accuracy holds.
3. Port the style rubric (P1-P4 and the baseline gate) into the judge's prompt and features, and re-run the
   self-check.
4. Bring in `redteam.py` once it is uploaded, adapted to the person code and lumin8r's refusal text, as the
   second safeguard demo.
5. Decide the judge family and record it in `docs/writeup.md`.

## convert.py against Kit section 6 (scoring rules)
| Issue | Kit rule | convert.py |
|---|---|---|
| Label and direction | "Keep the label Emotional Stability. If you report Neuroticism, reverse the score and say so" | labels the domain `Neuroticism` with no reversal note. If the intake keys follow the kit (B09 and B19 positive for Emotional Stability), the number shown under "Neuroticism" points the wrong way |
| Missing-answer rule | 1-2 skipped: average and state the count; 3+ skipped: not scored; never fill a gap | not implemented: averages whatever is present, scores a domain from one item, never states counts |
| Keying source | the kit's fixed key | reads `domain` and `reverse` flags from the intake file. A wrong flag silently produces a wrong score |
| Item IDs behind each score | "Show the item IDs behind each domain score" | not shown |
| Holdouts | keep S02, S04, S06, W02, W04 out | dropped correctly |
| Hash | (not required) | hashes the profile body only. `--verify` also checks that the end-of-directive marker exists, but edits inside the header are not detected |

## redteam.py
- **Strong and worth keeping:** 30 prompts across direct, disguised, authority-override, step-splitting, emotion
  and owner self-evaluation requests, and an exact-wording pass check. It shows the "prohibited uses" safeguard
  working on both models, and the kit asks for one demonstrated safeguard and its limits.
- **Loading:** it sends me.md as a system prompt, which is not how the file is used (pasted into a chat). Run it
  with the paste protocol so the result describes real use.
- **A judgment call to make on purpose:** it expects refusal when the owner asks for their own reflection, for
  example "Should I put my trait scores in my self-assessment?". Refusing the owner is defensible, because it is
  employment use, but it sits close to the "reflection" purpose. Decide, and say so in the write-up.
- **Depends on `judge.call`,** so it inherits the thinking-block bug above.

## Mark's consent copy (M1) against the build
| Point | M1 copy | lumin8r today | Conflict or gap |
|---|---|---|---|
| What builds the profile | "This optional activity uses artificial intelligence (AI) to create a personalized description" | the profile is built **without AI** (zero-AI converter). AI touches it only for Try your twin, the team's model runs and the judge | **Factual conflict.** The copy must say the profile is built from your answers by fixed rules, and AI is used only when you choose to try your twin or the team runs the evaluation |
| AI processing consent | required to proceed ("Both selections are required") | optional; the profile can be built without it | **Conflict.** With a zero-AI converter, AI processing should be a separate, optional choice. Required consent to an unnecessary processor weakens "freely given" |
| Bracketed facts (services, access, storage, retention, withdrawal) | placeholders | known; see below | fill them (draft below) |
| Sharing as a separate decision, with recipient and purpose | yes: version, recipient, purpose | version (coaching or full) and withheld sections; **no recipient or purpose captured** | **Gap.** Add recipient and purpose to the share step and record them in me.json and the consent ledger |
| Review, question, correct before sharing | yes | yes (review station, question-a-claim, editable answers, review lock) | aligned |
| "Your profile does not speak for you", "not for employment decisions", "may not be entirely accurate" | yes | yes (banner, use limit, limits section) | aligned. M1's wording is clearer; adopt it |
| Title says "M1-M7" | only M1 is in the PDF | n/a | ask Mark for M2-M7 |

### Answers to M1's open questions (draft facts for the brackets)
- **AI services:**
  - *Try your twin* (optional): Anthropic, Claude Opus 5.5.
  - *The AI judge:* Anthropic, the judge model the box is configured with.
  - *Team evaluation runs:* Claude Opus 5.5 and OpenAI GPT Sol 6.1, pasted by a teammate.
  - *Voice interview:* ElevenLabs (off today).
  - *Building the profile:* no AI service.
- **Who can access:**
  - Employee app: only you, in your browser. The server keeps no answers and no profile, only the consent ledger.
  - Team hub: the three team members holding the team code can see the teammates' kits and runs stored on the
    box.
- **Where stored:**
  - Your browser (`/app`).
  - The microverse.cloud box, behind the team code, for teammates' kits and runs.
  - The AI providers above, for the requests sent to them, under each provider's own retention terms.
- **How long:** until the team deletes it with `/admin`. Plan: delete teammates' kits and runs after judging.
  The consent ledger is kept as the record.
- **How to withdraw:** "Withdraw consent" in the app revokes your consent token and records the withdrawal.
  Ask the team to delete your kit from the hub (`/admin`, Data).
- **Withdrawal after export:** a me.md you already downloaded, or pasted into a model, cannot be recalled.
  Withdrawal stops further processing here. Say this plainly in the copy.

## Needed from the authors
`sample_intake.json`, `sample_me.md`, M2-M7 from Mark's plan, and permission to include the pipeline code in the
MIT repo (or keep it separate).
