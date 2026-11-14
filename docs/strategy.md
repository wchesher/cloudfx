# What makes this incredible

## The thesis
Most teams will ship a converter, a prompt and a judge, and assert that they work. We ship an
**experiment**: a measured "human context lift", produced with a judge we checked against human
raters and an employee-owned file the person can audit claim by claim. Every slide carries a
number we measured that day, not a claim.

## Five moves, in priority order

1. **Turn the day into an experiment with N people, not one.**
   - Every consenting teammate takes the kit (around 25 minutes each).
   - For each person we hold out S02, S04, S06, W02 and W04 and measure:
     - scenario choice accuracy, with the profile and without it, on both models
     - writing likeness, rated blind
   - Four people give 4 x 5 x 2 models x 2 conditions = 80 scored responses.
   - That one table answers several criteria at once: the converter (20%), the personality
     performance (25%), "what comparing the models taught you", and the failure the panel asks for.

2. **Design the converter with data, not taste.**
   - A/B test two or three me.md variants on the held-out answers:
     - evidence-first (decision patterns and verbatim voice first; traits only as a tie-breaker)
     - trait-first
     - short
   - Keep the winner and show the loser. The point we expect to prove: an LLM handed trait
     labels stereotypes, and handed the person's own reasons it predicts deviations from the
     "sensible default". The no-profile baseline already gets the default right; the score is won
     on the cases where the person deviates from it.

3. **A judge we caught failing.**
   - Two teammates blind-rate the same responses. We report AI-to-human agreement.
   - Adversarial probes:
     - right letter, wrong reason
     - fluent generic filler
     - the same content in polished English and in plain non-native English (the fairness check)
   - Show the probe it fails, and say why. The criterion literally asks for this.

4. **One hero loop in the demo: "click a claim, see the answers, fix one, watch it change".**
   - Consent, then upload. Every claim is a chip that opens the exact answers behind it.
   - The person corrects one answer and the profile regenerates, with that claim changed.
   - The gate visibly refuses an unsupported claim.
   - The person picks a share scope; the minimum-necessary version drops verbatim writing, which
     is the security answer for a security-founder CEO.
   - The person downloads a digest-stamped me.md.
   - This is the problem statement made tangible, and it matches the panel's required order
     (claim and evidence first, then app to reviewed file).

5. **Voice intake as the bonus, only after the core is frozen-ready.**
   - An ElevenLabs agent runs a 10-minute behavioral interview. We use the transcript only, never
     tone of voice (EU AI Act Art. 5(1)(f) bans emotion recognition at work), and we never clone
     the person's voice.
   - The transcript yields cited evidence (V01...), which goes through the same converter and the
     same held-out test, with time and effort recorded.
   - Basis: interview-grounded agents outperform demographic or persona agents (Park et al. 2024).
     A null finding still counts for the bonus.

## Do not do
- Build a Wethos API integration blind (there is no public API).
- Grow me.md: longer earns nothing.
- Optimize the judge's own scores: they do not rank us.

## The things it would be dumb not to do
- **A one-command freeze pipeline.** `mefile final --build X --questions Y` produces me.md,
  paste-ready prompt packets for both models, and a response template. `mefile judge` produces
  the 20 evaluations. Rehearse it end to end on the fictional files at 3:30.
- **A transdisciplinary cross-check.** Two quotes from a practitioner (a coach or HR person, or a
  Wethos staffer at the event), each tied to a design change. It costs 15 minutes and earns 15% of
  the score.

## The day
| Time | Work |
|---|---|
| 9:00-9:45 | Kit completed by every consenting teammate; consent recorded; model access checked |
| 9:45-12:00 | Converter, review app and judge running on the fictional files; first me.md variants |
| 12:00-14:00 | Experiment: profile and no-profile runs on both models for everyone; blind human ratings |
| 14:00-15:30 | Pick the winning variant; judge probes and failure analysis; voice intake if the core is green |
| 15:30-16:30 | Freeze rehearsal on the fictional files; slides with the measured table |
| 16:30-17:30 | Final runs (frozen); 8 responses by 17:00; 20 evaluations by 17:30 |
