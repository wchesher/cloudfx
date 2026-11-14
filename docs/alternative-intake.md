# Alternative intake: a short behavioral interview (Common Kit Section 11)

Our bonus submission for Section 11. One consenting teammate did the Common Kit and a short interview.
We built two profiles from them and tested both on the teammate's held-out kit answers.
Values in [brackets] are filled from the run before submission. Delete any that were not measured.
Vendor facts marked "check before quoting" come from vendor docs (see `docs/voice-intake.md`).

## (a) The working pathway

### What it is
- Eight "tell me about a time" questions about work (`voice.INTERVIEW_GUIDE`).
- About 10 minutes.
- The person's answers become cited evidence in me.md, numbered V01, V02 and so on.
- Each V item is tagged with the question it answers. Claims that use it cite its ID, like kit answers do.

### Three ways in
1. **By voice, with an AI interviewer.** An ElevenLabs agent asks the eight questions, one at a time.
   It says first that it is an AI and that the talk is transcribed.
2. **In person, recorded on a Plaud device.** A teammate asks the same questions. The Plaud transcript
   (TXT or SRT) is imported. The person picks which speaker is them (`plaud.py`).
3. **Typed.** The person types answers to the same questions.

All three produce the same file, `voice_transcript.json`. The file records which way it was taken
(`source`: elevenlabs, plaud or typed). The converter treats all three the same.

### What is kept
- The text of the person's own answers. Nothing else.
- The interviewer's questions, only to tag which question each answer belongs to.
- The interview length in seconds, for the effort comparison.

### Safeguards
- **Text only.** No audio is analyzed.
- **No emotion inference.** Nothing reads tone, pace or feeling. The EU AI Act, Art. 5(1)(f), bans inferring
  workers' emotions from biometric data, voice included. Text is outside that ban.
- **No voice clone.** The person's voice is never copied. Their understudy answers in text.
- **Recording off, conversation deleted.** The agent runs with audio recording off
  (`record_voice=false`). The app checks this and refuses to start if it is on. The conversation is deleted
  from ElevenLabs once the transcript is saved. (Vendor settings: check before quoting.)
- **Consent first.** The person agrees before the interview starts. The agent repeats the disclosure.
  California requires every party's consent to record a confidential conversation (Penal Code 632).
- **The person reviews and edits the transcript.** They can fix, shorten or delete any answer before use.
  A deleted answer drops out. The other IDs keep their numbers.
- **Work situations only.** The agent never asks about health, family, religion, politics, age or ethnicity.
- **Same rules as the kit.** The claims gate still runs. Real transcripts stay out of git.

## (b) Rationale and scientific basis

### Why an interview
- **Park et al. 2024** ("Generative Agent Simulations of 1,000 People", arXiv:2411.10109).
  - An AI interviewer ran 2-hour voice interviews.
  - Agents built from them matched people's survey answers at 0.85, scaled to how well people match
    themselves two weeks later.
  - Agents built from demographics scored 0.71. Agents built from a persona paragraph scored 0.70.
  - With 80% of each transcript removed, agents still scored 0.79. A short interview keeps much of the signal.
  - Bullet summaries scored 0.83. The content carries the signal, not the voice.
- **Peters, Cerf and Matz 2024** (arXiv:2405.13052). A chatbot told to draw out personality reached
  r = .44 with self-reported traits. A default assistant reached .12. A purpose-built interviewer matters.
- **Behavioral questions.** "Tell me about a time" questions predict better than "what would you do"
  questions (Taylor and Small 2002; check the exact figures before quoting).
  The method goes back to the critical incident technique (Flanagan 1954).
- **The kit's gap.** The kit has three build scenarios and two build messages. The interview adds real
  incidents in the person's own words: how they disagree, decline, and word a message upward.

### What we adapted
- **8 questions, about 10 minutes**, instead of a 2-hour life-story interview.
- **Work situations only**, to match the use: coaching and communication at work.
- **Cited evidence instead of a summary.** Each answer is quoted with its V ID. No model summarizes it.
  The converter stays deterministic and has no AI in it.
- **One short follow-up per question** ("What did you do?" or "What did you say?"), to get actions and words.

### Intended benefit
- Answers to held-out situations that sound more like the person and pick their actual choice more often.
- Most likely gain: the writing questions and the reasons behind scenario choices.
- **Expected effect: modest.** Zero-shot trait inference from free text usually lands around r = 0.2 to 0.45.
  With one person and three scored choices, we may see no difference. A null finding counts.

## (c) Comparison with the common-kit pathway

### Method
1. The teammate consented, then took the kit on the assessment page. The page timed it (`kit_minutes`).
2. The page split the answers into `build.json` and `test.json`. The test file holds only the held-out
   answers: S02, S04, S06, W02 and W04.
3. The teammate did the interview: [by voice / in person on Plaud / typed]. They reviewed the transcript.
4. **Leakage guard.** The run refuses to start if the transcript names a test ID or shares 8 or more
   consecutive words with any held-out test answer. Result: [passed].
5. Two profiles per me.md variant: kit only, and kit plus interview. Both use the same build answers.
   Neither sees the test answers.
6. Both profiles answered the same held-out questions on both models. Claude Opus 5.5 Medium ran through the
   API. GPT Sol 6.1 Medium was pasted by hand. Each was a new chat with memory off, the profile first, then the
   question. We also ran a no-profile baseline.
7. **Scoring.** Choice accuracy on S02, S04 and S06 is an exact letter match. No model computes it.
   The AI judge rated resemblance to the person's own answers, 0 to 4, blind to which arm wrote each answer.

### Results
Variant: [evidence_first]. Person: 1 teammate.

| Model | Arm | Choices correct (of 3) | Judge: scenario resemblance (0-4) | Judge: writing resemblance (0-4) | me.md words |
|---|---|---|---|---|---|
| Claude Opus 5.5 | no profile | [ ] | [ ] | [ ] | - |
| Claude Opus 5.5 | kit only | [ ] | [ ] | [ ] | [ ] |
| Claude Opus 5.5 | kit plus interview | [ ] | [ ] | [ ] | [ ] |
| GPT Sol 6.1 | no profile | [ ] | [ ] | [ ] | - |
| GPT Sol 6.1 | kit only | [ ] | [ ] | [ ] | [ ] |
| GPT Sol 6.1 | kit plus interview | [ ] | [ ] | [ ] | [ ] |

[RESULT: one sentence. Did the interview change any choice or score? Name the question.]

### Time and effort

| Pathway | Minutes | Source | Effort notes |
|---|---|---|---|
| Common Kit | [ ] | timed by the assessment page | [60 questions, self-paced, on screen] |
| Interview | [ ] | transcript duration_seconds ([source]) | [talking, no typing; plus review time] |
| Transcript review | [ ] | stopwatch | [fixes the person made, e.g. names, misheard words] |
| Team setup | [ ] | stopwatch | [agent setup or Plaud import; one-time] |

[RESULT: what the teammate said was easier or harder.]

### Limitations
- **One teammate, n = 1.** Three scored choices per arm and model. One answer is 33 points. Treat any
  difference as noise, not evidence.
- **Speech-to-text is less accurate for some accents and dialects.** Koenecke et al. 2020 (PNAS) found an
  average word error rate of 0.35 for Black speakers vs 0.19 for white speakers across five major systems.
  Whisper sometimes invents phrases (Koenecke et al. 2024). Review catches some of this. It also costs some
  people more time. The typed way in avoids it.
- **The teammate knows the system.** They know what the kit asks and what the profile does. That can shape
  their answers.
- **The interview may repeat the kit's topics.** Disagreement and declining appear in both. Overlap can make
  the arms look alike. The guard stops quotes of the test answers, not similar topics.
- **Longer profile.** Kit plus interview adds words. A model may weigh a longer file differently.
- **The judge is a model.** It was blind to the arm, but its scores carry its own errors (`docs/judge.md`).
- **Different ways in may differ.** We tested one of the three. The others share the file, not the experience.

## How to run the comparison

### On the box (the workbench)
1. Add the teammate's kit on the team hub (build and test files), as for any person.
2. On the interview page in workbench mode, press "Send to the team hub". It posts the reviewed transcript to
   `POST /api/team/voice`. The hub runs the leakage guard first and refuses a transcript that names a test ID
   or quotes a test answer. The people table then shows the interview: how it was taken, minutes, guard result.
3. The paste station now lists the `<variant>_plus_interview` runs next to the kit-only runs. Run LLM A, paste
   LLM B, then run the experiment. The results include the kit only vs kit plus interview table.

### From the command line

Put the teammate's files in `private/people/<CODE>/` (gitignored): `build.json`, `test.json`, and the reviewed
`voice_transcript.json`. A folder without a transcript runs kit only, as before.

```bash
# 1. plumbing check, no API calls
PYTHONPATH=src .venv/bin/python -m mefile experiment --people private/people --variants evidence_first --out private/experiment --dry-run --judge

# 2. Claude through the API; writes the GPT paste sheet
PYTHONPATH=src .venv/bin/python -m mefile experiment --people private/people --variants evidence_first --out private/experiment

# 3. paste GPT answers under each '=== RUN_ID' line in private/people/<CODE>/llm_b.txt
#    (sheet: private/experiment/<CODE>/PASTE_SHEET_LLM_B.md), then score everything with the judge
PYTHONPATH=src .venv/bin/python -m mefile experiment --people private/people --variants evidence_first --out private/experiment --judge
```

The table is in `private/experiment/comparison.md` and `comparison.json`. The guard result is in
`private/experiment/<CODE>/leakage_guard.json`. Add `--manual` to paste Claude by hand too.
Use `--voice PATH` to point at a transcript somewhere else.

## How to present it (60 seconds)

> The kit takes about [25] minutes and gives us three build scenarios and two build messages. That is thin.
> Research says interviews carry more signal. Park and colleagues built agents from two-hour interviews that
> matched people's survey answers about as well as people match themselves. So we built a ten-minute version.
> Eight "tell me about a time" questions, about work only. You can take it with our AI interviewer, in person
> on a Plaud recorder, or typed. We keep only the text. No audio, no emotion reading, no voice clone. The
> recording is off and the conversation is deleted. The person reviews every word before it is used.
> Each answer becomes cited evidence, V01 to V08, in the same me.md.
> We tested it on one teammate. Same held-out questions, both models, kit only versus kit plus interview.
> A guard refused to run if the interview quoted any test answer. Result: [result]. It took [N] extra minutes.
> One person and three choices is not enough to prove anything, and speech-to-text is less accurate for some
> accents. But the pathway works end to end, and the method is ready for more people.
