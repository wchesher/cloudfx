# Mark's M3 risk register, mapped to lumin8r

Source: `contrib/consent/M3-ethical-ai-risks-and-safeguards.pdf` (Mark, employee-side lead). For each risk: the safeguard
built, where it lives, and the residual risk we say out loud. Status as of 14 November 2026.

| # | Risk (M3) | Safeguard built | Where | Status | Residual risk (stated) |
|---|---|---|---|---|---|
| 1 | Employees feel pressured to participate | Voluntary consent screen in Mark's own words. Declining has no penalty and is never recorded as a trait. A manager's request does not replace consent. Nothing is shared without the person's action | `/app` and `/assessment` consent; server-enforced consent token | built | Pressure from the employment relationship cannot be removed by software |
| 2 | Employers use profiles for unintended purposes | Prohibited-use rules and an exact refusal in every me.md. Use limits on every page and in the recipient view. Shares go to one named recipient for one purpose, with expiry and revoke. Red-team of 30 misuse attempts | converter guardrails, `/responsible-use`, share API, `python -m mefile redteam` | built; red-team not yet run live | Once shared, a copy can be misused despite the rules |
| 3 | Personal information exposed or retained without understanding | Consent copy names each AI service and what it receives. The server keeps no answers in the product. Share links are end-to-end encrypted, so the server holds only ciphertext. Teammates' data stays behind a code and out of git | consent copy, `/privacy`, `shares.py`, `.gitignore` | built | Outside AI providers keep requests under their own policies |
| 4 | Inaccurate or exaggerated claims | Every claim cites real answers. The claims gate refuses uncited, skipped, held-out or labelled claims. Claims come from fixed templates (no free-form AI text), and middle scores read "no clear tendency". The employee reviews, corrects answers and questions claims | `converter.py`, `claims.py`, `/app` review | built | A claim can cite a real answer and still misrepresent the person (see Q1) |
| 5 | Cultural, language or personal differences misread | Vocabulary items (B05, B40) carry a language note. No fixed labels. The judge's fairness rule says polish never raises a score, and politeness is judged only against the person's own rate. Fairness probe in the self-check | converter limits section, `judge/rubric.py`, self-check | built; fairness probe not yet run live | A short questionnaire cannot capture everyone's background; broad fairness is not established |
| 6 | The AI evaluator misjudges resemblance | Blind rating sheet for human reviewers; agreement statistics (exact, within one point, kappa, Spearman) and the largest disagreements listed | `python -m mefile.judge ratesheet` and `agreement`; workbench judge station | built; needs two raters | Human raters can be biased too; limited testing cannot establish accuracy |
| 7 | Voice interviews add privacy or fairness concerns | Transcript text only, no vocal analysis, no emotion detection, no voice cloning, audio recording off, the person reviews the transcript | `voice.py`, `intake.py`, `docs/voice-intake.md` | built but **not in use today** (no ElevenLabs agent) | Even temporary audio processing exposes sensitive information |
| 8 | Employees cannot fully control or delete information after sharing | Withdraw consent revokes tokens and turns off the person's share links. Revoke any link. Admin can delete a person's team-hub data; the consent record is kept. The copy states that downloaded or third-party copies cannot be recalled | `/api/withdraw`, share revoke, `/admin` | built | Copies already downloaded or kept by third parties are not recoverable |

## Answers to Mark's questions for Will

1. **Unsupported claims (D3).** The gate cannot detect an exaggerated conclusion that cites a valid answer; it checks
   that claims point at real answers, not that the wording fits. The design limits the risk in three ways: claims
   come only from fixed templates (no free-form AI text), middle scores are worded as no tendency, and the person
   reviews every claim and can question it. A planned next step is to mark claims that rest on a single answer as
   "based on one answer". We state this limit in the presentation.
2. **Employee control.** Yes. The person reviews the file, sees the answers behind every claim, corrects any answer
   (the file rebuilds), questions claims (questions stay on the person's page today), and must confirm the review before downloading or sharing.
3. **Privacy.**
   - **Answers and the profile:** kept in the person's browser (on the device only if they choose); the server keeps
     neither.
   - **Shares:** stored encrypted, so the server cannot read them.
   - **Teammates' assessment data:** kept on the box behind the team code.
   - **Outside AI services:** only when used. The understudy sends the file and the question to Anthropic. The
     team's evaluation sends the file and questions to Claude and GPT. The judge sends the file, responses and
     reference answers to Anthropic.
4. **Voice (D7).** Not used today. If enabled: transcript text only, audio recording off, no tone or emotion
   analysis, no voice cloning, and the person reviews the transcript.
5. **Sharing and deletion.** Yes: a limited coaching version or the full file, to a named recipient for a stated
   purpose, with an expiry. The owner can revoke at any time; withdrawal turns off all their links. A copy the
   recipient already saved cannot be recalled.
6. **Demonstration.** The claims gate: a file that leaks a held-out answer or uses a fixed label is refused, live.
   Limitation to acknowledge: it checks references, not meaning (Q1). Second option: the red-team refusal on a
   misuse prompt, with the limit that a refusal stops the model, not a person who has copied the file.
