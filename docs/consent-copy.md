# Consent copy (M1), as shipped

Written by **Mark** (the team's employee-side, legal and ethics lead) as "M1 Consent-screen" in the team plan
(`contrib/consent/M1-consent-screen-copy.pdf`), integrated with his consent. His structure and wording are kept; the
changes below make it true for lumin8r, whose profile is built by a zero-AI, deterministic converter. Conflicts
were first listed in `docs/team-pipeline-review.md`, "Mark's consent copy (M1) against the build".

It ships on two screens:
- **/app**, station 1 consent (`src/mefile/static/index.html`), with the sharing decision in station 4 share.
- **/kit**, the consent step (`src/mefile/static/kit.html`), with the AI choice repeated on the done screen next to
  Send to the team hub.

## What changed from M1, and why

| M1 | Shipped | Why |
|---|---|---|
| "This optional activity uses artificial intelligence (AI) to create a personalized description" | "...creates a personalized description... It is built from your answers by fixed rules; no AI service writes it." | Factual: the converter is zero-AI. AI touches the profile only in Rehearse with your understudy, the team's evaluation runs and the judge |
| Bullet 2: "AI can misinterpret answers or overlook..." | "It is built from your answers by fixed rules, and those rules can misinterpret answers or overlook... An AI that answers as you from the profile can get it wrong too." | Same correction; the warning keeps its point and names where AI does come in |
| Bullet 3: "an AI-generated interpretation" | kept verbatim | The file carries the "AI-generated representation" label on purpose (EU AI Act Art. 50, `docs/risk-and-acceptance.md`). Open question for Mark: reword both together if he prefers |
| Five bracketed facts | filled (below) | From the review doc's drafted facts |
| "After you complete": "Review what the AI says about you" | "Review what the profile says about you" | The profile, not an AI, makes the claims |
| Choice 2, AI processing: required. "Both selections are required to proceed with this AI-supported activity." | **Optional**, labelled so. /app: "Only Rehearse with your understudy needs this... if you leave this unticked everything else still works. You may decline without penalty." /kit: needed only to Send to the team hub | Building the profile needs no AI, so requiring consent to an unnecessary processor would weaken "freely given". Declining keeps the build, review and downloads working |
| (none) | /app choice 3, Voice interview (optional), ElevenLabs, text only | Existing purpose `voice_interview` kept |
| Sharing: "Person or organization receiving it", "Purpose of sharing", version | /app share station: "Who is it for?", "Why are you sharing it?", then "Version to share" (Limited coaching profile, default; Full profile) | His separate sharing decision; recipient and purpose were not captured before |
| "If you do not select this option, your profile will not be voluntarily disclosed..." | "If you do not choose to share, your profile is not disclosed to anyone else; you can still review your results." | Shorter, same meaning; no separate share checkbox: an empty recipient is the personal download |
| "60 questions, 20-30 minutes" | kept on both; /app adds "If you took the kit already, bring its answer file." | /app loads the kit's file rather than asking the questions |

## Wiring (unchanged server)

- /app purposes: `build_profile` (required, choice 1), `ai_processing` (choice 2), `voice_interview` (choice 3), sent
  to `POST /api/consent` as before; the consent token flow is unchanged. `ai_services` now records the true services:
  "Anthropic Claude Opus 5.5 (Rehearse with your understudy)", "ElevenLabs (voice interview)".
- With AI processing declined, Rehearse with your understudy says: "Rehearse with your understudy is off because you declined AI processing. Your file
  was built without AI and everything else works."
- Sharing, when a recipient is given and the person downloads me.md or me.json after ticking "I read this file":
  - `POST /api/consent` with `{person_id, purposes: ["share_profile"], ai_services: [], share_with: ["<recipient> |
    purpose: <purpose> | version: <coaching|full>"]}`, recorded once per distinct decision. The new token it returns
    is not used; the page keeps its original token. Errors show inline and the file still downloads.
  - me.json gets `sharing: {recipient, purpose, version, decided_at}` added client-side; `sharing: null` for a
    personal download (empty recipient, no ledger call).
- /kit: choice 1 (`#agree`) starts the kit; choice 2 (`#agreeAi`, and `#agreeAiDone` on the done screen) is held in the
  browser with the kit and gates only Send to the team hub. Not recorded on the server: the kit has no consent call.

## Final copy

### Create your personal workplace profile

**About this activity**

This optional activity creates a personalized description of your workplace preferences, communication style, and how
you might approach different situations. It is built from your answers by fixed rules; no AI service writes it.
(/kit adds: Then the team checks how well an AI using it predicts your answers to five held-out questions.)

You will answer up to **60 questions**, which should take approximately **20 to 30 minutes**.

Your answers will be used to create a personal profile that you can read, question, and correct. The purpose is to
support self-reflection, workplace communication, and coaching.

**Important things to know**

- **Participation is your choice.** You may skip questions or decline to participate without penalty or disadvantage.
  A manager's invitation does not mean you are required to participate.
- **Your profile may not be entirely accurate.** It is built from your answers by fixed rules, and those rules can
  misinterpret answers or overlook important aspects of your experiences, background, or communication style. An AI
  that answers as you from the profile can get it wrong too.
- **Your profile does not speak for you.** It is an AI-generated interpretation, not a diagnosis, a formal employment
  assessment, or a statement you have personally made or endorsed.
- **Your profile is not for employment decisions.** It must not be used for hiring, promotion, disciplinary actions,
  or employee ranking.
- **You control whether to share your profile.** You will have an opportunity to review it before deciding whether to
  share any version of it with others.

**How your information will be used**

Your answers will be processed to create and evaluate your personal profile. Before deciding whether to participate,
please review the following information:

- **AI services used:** building your profile uses no AI service. If you choose *Rehearse with your understudy*, your file is sent to
  Anthropic (Claude Opus 5.5). If you send your kit to your team, the team's evaluation runs use Claude Opus 5.5 and
  OpenAI GPT Sol 6.1, and an Anthropic judge model scores the results. The optional voice interview uses ElevenLabs;
  it is switched off today.
- **Who can access your information:** on this page, only you: your answers and profile stay in your browser, and the
  server keeps no answers and no profile, only a record of your consent. In the team hub, the three team members who
  hold the team code can see the kits and evaluation results sent there.
- **Where your information is stored:** in your browser; on the microverse.cloud server, behind the team code, for
  kits sent to the team hub and the team's evaluation results; and at the AI providers above, for the requests sent to
  them, under each provider's own retention terms.
- **How long information is kept:** until the team deletes it. The team plans to delete teammates' kits and evaluation
  results after judging. The consent record is kept as the record of what you agreed to. (/kit: *Clear my answers*
  removes them from this browser at any time.)
- **How to withdraw:** press *Withdraw consent* on this page at any time; it revokes your consent and records the
  withdrawal. Ask the team to delete your kit from the team hub. A file you already downloaded, or pasted into an AI
  model, cannot be recalled after you withdraw; withdrawal stops further processing here. (/kit: stop at any time and
  press *Clear my answers*; if you already sent your kit, ask the team to delete it.)

**After you complete the questionnaire**

Before sharing your profile with anyone else, you will have an opportunity to:
1. **Review** what the profile says about you and see which answers support its conclusions.
2. **Question or correct** information that seems inaccurate or misleading.
3. **Choose whether to share** your profile, which version to share, and with whom.

**Your choices**

1. Participation (required)
   - [ ] **Yes, I voluntarily agree to complete the questionnaire and create a personal workplace profile.**
   I understand the purpose of the activity, that participation is optional, and that the resulting profile may not
   fully or accurately reflect who I am.
2. AI processing (optional)
   - /app: [ ] **Yes, I agree to have my file processed by the AI services identified above when I choose Try your
     twin.** I understand which AI services will receive my information, why they need it, and the applicable
     data-handling and retention limitations. Only Rehearse with your understudy needs this. Your profile is built without AI, so if
     you leave this unticked everything else still works. You may decline without penalty.
   - /kit: [ ] **Yes, I agree to have my answers processed by the AI services identified above for this activity.**
     (Needed only to send to the team hub.) When you send your kit to the team hub, the team's evaluation runs it
     through Claude Opus 5.5, OpenAI GPT Sol 6.1 and an Anthropic judge model. Without this you can still take the
     kit and download your two files. You may decline without penalty.
3. Voice interview (optional, /app only)
   - [ ] Yes, I agree to a voice interview with ElevenLabs, kept as text only. No voice analysis, no voice clone.

Only the first choice is needed to build your profile. You may decline the others without penalty, and declining is
never recorded as a trait.

### Sharing your profile, a separate decision (/app, station 4)

- **Who is it for?** (person or organization receiving it)
- **Why are you sharing it?**
- **Version to share:** Limited coaching profile (default) or Full profile.

Leave both empty for a personal download that you keep. If you do not choose to share, your profile is not disclosed
to anyone else; you can still review your results.

## Credit

Consent copy by Mark, M1 of the team plan ("mefile Team Plan", 14 Nov 2026). Corrections for the zero-AI build and
the filled facts by the lumin8r build, from `docs/team-pipeline-review.md`.
