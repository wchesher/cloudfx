# lumin8r: the 5-minute pitch

Panel at 6:30pm: 5 minutes, then 3 minutes of questions. The order is fixed by Common Kit section 13. lumin8r
(microverse.cloud) is the product. It has four stations (consent,
answers, review, share), with your me.md in the middle.

Fill every `[RESULT: ...]` from frozen results only; if it was not measured, cut the line. Demo data is fictional DEMO01 unless the volunteer authorized their own.

Speakers: Builder 115s, Mark 75s, Steven 110s. Total 300s.

## Run of show

### 1. Your file: one claim, its answers (Builder, 40s)
**On screen:** me.md open, with chip C01 expanded.
- "Deals with disagreement directly rather than letting it pass [S01, S05]"
- S01 and S05 answers highlighted beside it

**Say:** "This is lumin8r. You take a 30-minute assessment and you get one file, me.md, that you own. Here's one claim: 'deals with disagreement directly rather than letting it pass.' Click it and you see the two answers behind it. In S01 you raised a disagreement openly with the group. In S05 you took it to the colleague one-to-one. Every claim carries its answers. No fixed labels, and no AI builds the file: same answers, same file."

**Evidence:** a screenshot of C01 expanded. [RESULT: claims in the volunteer's me.md, n=, all cited, gate verdict].

### 2. From your answers to a reviewed file (Mark, 45s)
**On screen:** consent / answers / review / share, with me.md in the center.
- Understudy panel: "sounds like me" / "not me"
- Share: coaching (no verbatim writing) / full

**Say:** "You start at consent, before any answer is touched, and saying no changes nothing. Then answers, then review. In review you rehearse with your understudy: it is Claude, an AI, that learns your part from your answers and answers the way you would, labelled as practice, not you. You mark each answer 'sounds like me' or 'not me.' If it's wrong, you fix the answer behind the claim. The file regenerates and the review tick clears. At share you pick the version. The default, coaching, drops your verbatim writing, because a file full of your writing is a phishing kit."

**Evidence:** a recording of the hero loop: correct one answer, C01 changes, the tick clears. [RESULT: sounds like me / not me marks from teammates, n=], or cut.

### 3. The gate before export (Mark, 30s)
**On screen:** three verdicts.
- breaks: "S02 is a held-out test answer"
- Limit: checks pointers, not meaning

**Say:** "Our safeguard is the claims gate. Solid means every claim cites real answers. Works means it passes with a caution: a claim that leans on vocabulary items a second-language speaker may read differently. Breaks means export locks. Watch: I slip in a held-out test answer. Breaks, and it names S02. Its limit: it checks that a claim points at answers, not that they support the wording. So export also needs your review."

**Evidence:** recording of the S02 upload ending in breaks; works on DEMO01 (C18, B05/B40 caveat).

### 4. The judge on one response (Builder, 40s)
**On screen:** one row from evaluations.md.
- [RESULT: question ID, model] response, scored [RESULT: reference resemblance, x/4]
- Cited: [RESULT: evidence IDs]; generic: [RESULT: yes/no]

**Say:** "Here's our judge on one of the twenty responses. The choice is checked without a model: [RESULT: match or not], worth two points. The reason gets [RESULT: 0-2] from the judge model, which cites [RESULT: IDs]. We score two things separately: does it resemble what you actually said, and does it fit your profile. It never sees who wrote a response, and on any failure it returns an error, never a guessed score."

**Evidence:** an evaluations.md excerpt. [RESULT: judge_model_served for the final run].

### 5. We tried to break our judge (Builder, 35s)
**On screen:**
- Probes passed: [RESULT: live selfcheck, x of 7]
- AI-to-human agreement: [RESULT: agreement, n= responses, 2 blind raters]

**Say:** "Then we tried to break it. We used seven probes: the right letter with the wrong reason, fluent filler, and the same answer in polished English and in plain non-native English, which must score within one point. A naive word-overlap judge failed two of the seven. It favored the plain version for reusing your words and missed corporate filler. Our live judge passed [RESULT: x of 7]. Two teammates also rated blind, and the judge agreed with them [RESULT: agreement, n=]."

**Evidence:** selfcheck output; blind-rating totals only.

### 6. What human context bought, measured (Steven, 45s)
**On screen:**
- Profile lift: LLM A [RESULT: n=] / LLM B [RESULT: n=]
- Wethos twin vs ours, blind: [RESULT: mean resemblance, n=4]

**Say:** "Here's what comparing taught us. With no profile, both models pick the sensible default. With the profile, LLM A moved [RESULT: lift] and LLM B moved [RESULT: lift]. The same file, unchanged, moved the two models by different amounts. [RESULT: which model gained more, on what]. Evidence-first [RESULT: beat / did not beat] trait-first. Give a model trait labels and it stereotypes. Give it your reasons and it can predict where you break from the default. We also judged the Wethos twin blind: [RESULT]. It may know more than the kit gives us."

**Evidence:** the experiment table ([RESULT: people n=] x 5 held-out x 2 models x 2 conditions) and the summary of the 20 final evaluations.

### 7. One failure, and what it means (Steven, 30s)
**On screen:**
- [RESULT: question ID, model]: no-profile scored at or above ours
- Why: [RESULT: one-line cause]

**Say:** "One failure. On [RESULT: question, model], the no-profile answer scored as well as ours or better. [RESULT: cause, for example the person chose the popular option, so the profile added nothing]. It also exposes a judge weakness we wrote down in advance: the choice points can flatter a generic answer that guessed the popular option. With one recorded answer per question, a low score is evidence, not proof."

**Evidence:** the evaluations.md rows; if no such case, use the worst live probe.

### 8. Your file, any model, your call (Steven, 35s)
**On screen:**
- Employee-held, cited, any model, self-measuring
- Coaching kickoff / your reviewed preferences in any AI tool / a team manual you can withdraw

**Say:** "Every workplace profiling tool we found is held by the employer, the buyer or the vendor. lumin8r is held by you, cites every claim, loads into any model as a plain file, and measures itself. Stanford's Human Context Protocol argued for portable context; this is a working instance. Use it to start coaching at session one, to keep your preferences through the next AI switch, or to share a how-to-work-with-me you can withdraw. Never for hiring, promotion or ranking."

**Evidence:** market-research.md landscape table; [RESULT: practitioner quote, name and role], or cut.

## Panel questions

1. **Why trust a file the employee can edit? (Mark)** Editing changes a source answer, never a claim; the file regenerates and the gate still demands answers behind every claim. [RESULT: practitioner view on showing an edit trail].
2. **Isn't consent at work coerced anyway? (Mark)** Often, yes (EDPB 05/2020), so you hold the file, coaching is the default share, and declining is recorded nowhere. A click cannot prove freedom, and we say so.
3. **What stops use in hiring? (Mark)** The use limit is printed in every me.md and me.json, and employment use is high-risk under EU AI Act Annex III(4). It is words, not enforcement, so we built no HR-system integration and set a 90-day review-by date.
4. **Your judge and LLM A are both Claude. Self-preference? (Builder)** The judge never sees which run it is scoring, and the pipeline warns when the judge model is also under test. The final run used [RESULT: judge model], and the blind human ratings are the outside check.
5. **How do you treat non-native English? (Builder)** The fairness rule sits at the top of the judge prompt, and a probe tests it: polished and plain versions must land within one point. The gate returns "works" with a caution on vocabulary-sensitive claims.
6. **Why not have an LLM write the profile? (Builder)** A deterministic converter is auditable and invents nothing. Models only ever read the file.
7. **Do you compete with Wethos? (Steven)** No. lumin8r is a consent-native on-ramp to a Permissioned Twin and a neutral harness that can score any twin. Our blind judge reported where Wethos [RESULT: beat / trailed] us.
8. **What happens on revocation? (Mark)** me.md carries expiry, revocation and a digest, and withdrawal clears the app and logs it. Once pasted into a model, a file cannot be recalled, which is why the coaching version drops verbatim writing.
9. **Is 30 minutes of self-report enough? (Steven)** It gives an honest picture of a few tendencies, not a copy of a person, and self-report can be gamed. Our voice intake: [RESULT: result, or "not run"].
10. **What did a practitioner change? (Steven)** [RESULT: quote, name, role]. It changed [RESULT: design change, for example the default share scope].

## The 60-second Wethos version (Mark)

"You call Wethos the human context platform, and you separate Observed from Permissioned Twins. lumin8r is a Permissioned Twin the employee carries. They take a 30-minute assessment, review every claim against their own answers, try the twin as player two, and mark 'sounds like me' or 'not me' before sharing. We crosswalk to your four Style scales (Ideas, Relational, Action, Order) as hypotheses with evidence IDs, never scores. That's the same honesty rule you apply to Observed Twins. Your founder comes from security, so we treated the file as an attack asset: a threat model, a default share without verbatim writing, a digest, expiry and revocation, and free text rendered as quoted data. And our blind judge gives you a third-party number for your core thesis: [RESULT: profile lift, n=]. Human context changes the outcome, and here is by how much."

## Capture before 6:00pm

- [ ] Slide 1: C01 expanded with S01 and S05 highlighted (DEMO01, or the volunteer's file if authorized)
- [ ] Recording: correct one answer, the claim changes, the review tick clears
- [ ] The understudy answering, with the "sounds like me" / "not me" marks
- [ ] Recording: S02 upload, gate shows breaks; a still of works (C18 caution); a still of solid
- [ ] Share step: coaching vs full, with "verbatim message withheld" visible
- [ ] evaluations.md row for slide 4; the judge_model_served line
- [ ] Live `selfcheck` output; the blind-rating agreement total
- [ ] Experiment table: lift per model and per variant, with n
- [ ] Twenty-evaluation summary, including the Wethos rows; the failure row for slide 7
- [ ] Practitioner quote, verbatim, with name and role
- [ ] `git status` clean of real answers before anything is pushed or projected
