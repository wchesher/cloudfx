# lumin8r: method, testing, safeguards and limitations

Submission write-up for the CGU Digital Twin track (Digital Personality Modeling, sponsored by Wethos).
Code and run instructions: https://github.com/wchesher/cloudfx (README). Live: https://microverse.cloud.
Values in [brackets] are filled from the day's measured results before submission; delete any that were not measured.

## 1. What we built

lumin8r turns the 30-minute Common Kit into a portable, employee-owned me.md and judges how well AI responses
built from it resemble the person.

- **Converter**, with no AI in it: the same answers always produce the same file.
- **Review app**: the employee consents, reviews every claim against the answers behind it, corrects answers,
  questions claims, chooses what to share, and downloads the file.
- **AI judge**: explains each rating with evidence, and never sees which system wrote a response.

## 2. How we scored and interpreted the answers

- **Scoring:** IPIP-50 scored exactly as Kit section 6 says. Reverse items are 6 minus the response, each domain
  is a mean from 1 to 5, and the label stays Emotional Stability. With one or two items skipped, the domain is
  averaged over the rest and says how many. With three or more skipped, it is not scored. A gap is never filled.
- **Interpretation:** deliberately wide bands. A mean from 2.51 to 3.49 reads "no clear tendency" and is never
  turned into a label.
- **Evidence order:** the person's own scenario choices and reasons come first, their own messages (with measured
  style counts) second, and trait scores last, as a tie-breaker. The reason: a model given trait labels
  stereotypes, while a model given the person's own reasons can predict where they depart from the textbook option.
- **Variant test:** we tested this order against a trait-first variant and a short variant. Result:
  [RESULT: choice accuracy per variant and model, with counts].
- **Language:** items B05 and B40 (vocabulary) carry a stated limitation and their scores are not changed.

## 3. How claims link to evidence

- Every claim in me.md carries the answer IDs behind it inline (for example `[S01, S05]`) and appears in a claim
  index with its kind: measured, reported, observed style, or limit.
- **The claims gate** refuses export when:
  - a claim cites nothing
  - a claim cites a skipped or unknown answer
  - the file mentions a held-out test ID
  - a claim uses a fixed personality label
- **Limit of the gate:** it checks that a claim points at real answers, not that the answers support the
  wording. That second check is the employee's review, which is why the download stays locked until the person
  confirms they read it, and why they can question any claim.

## 4. Model comparisons

- **Protocol:** both designated models (Claude Opus 5.5 Medium, GPT Sol 6.1 Medium) received the same file
  through the same loading protocol: a new chat with memory and custom instructions off, me.md as the first
  message, the question as the second.
- **Records:** API runs record the served model; pasted runs record the model name the chat window showed.
- [RESULT: table of choice accuracy and resemblance per model and condition, and the lift over no profile].
- [RESULT: what differed between the two models].
- [RESULT: one failure: a question where the no-profile answer matched as well as or better than ours, and why].

## 5. The AI judge and how we checked it

- **Scale:** 0 to 4 on two separate dimensions:
  - resemblance to the person's own recorded answer
  - consistency with the build evidence
- **Scenario scoring:** a same-choice match is computed without a model (2 points), and the model rates the
  reason (0 to 2).
- **Other outputs:** the judge flags fluent but generic writing and returns "insufficient evidence" rather than
  guess.
- **Fairness rule:** polish, grammar and corporate tone neither raise nor lower a score.
- **Independence:** the judge runs on a different model from the one under test, and it fails closed: a broken
  call produces no score, never an invented one.
- **Checks:**
  - Self-check probes: good beats bad, generic is flagged, and the same content in polished and in plain
    non-native English scores within one point. Result: [RESULT: probes passed of 7; the one that failed and why].
  - AI-to-human agreement on a blind rating sheet scored by two teammates: [RESULT: exact, within-one and
    weighted kappa per rater].

## 6. Safeguards

- **Consent first:** enforced on the server with a consent token. Withdrawal revokes it, and declining is never
  recorded as a characteristic.
- **The server keeps no answers and no profile** in the employee app; only an append-only consent ledger.
- **Share scopes:** the coaching version, the default, omits verbatim messages. This is the guard against the
  file being used for impersonation or phishing. People can also withhold whole sections.
- **Claims gate:** demonstrated live, with the limits stated in section 3.
- **Data handling:** teammates' kit answers stay on the box behind a team code, never in git.
- **Voice intake:** transcript text only. No tone or emotion inference (EU AI Act Art. 5(1)(f)) and no voice
  clone.
- **Use limit:** printed in every file. Voluntary coaching, reflection and communication support only; not for
  hiring, promotion, discipline or ranking.

## 7. Limitations

- **Small evidence:** three scenario choices, two short messages and fifty self-ratings. Every statement is a
  tendency, and our measured differences rest on few answers, so we report counts with every percentage.
- **Self-report:** the profile describes how the person sees themselves, not how they behave.
- **The gate cannot judge meaning.** A reworded label can pass it; the employee's review is the real check.
- **Revocation cannot reach a file already pasted into a model.** Holding the file does not remove the pressure
  an employee may feel to share it.
- **The Wethos crosswalk is a labelled hypothesis.** Wethos Style measures behavior with its own instrument.
- [RESULT: optional intake: kit time versus voice interview time, and whether the voice evidence changed accuracy].
