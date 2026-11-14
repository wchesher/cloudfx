# M3 risks: what works today, checked against the code

For Mark. 14 November 2026.

This answers the red-yellow-green review of lumin8r ("lumin8r: Ethical Risk Review") against the eight M3
risks. That review judged the product description. This document judges the code. Each protection was traced
in the source, and where a doc and the code disagree, the code wins and the doc is listed as an overclaim.

How to read the statuses:

- **GREEN, works today.** The code does it now. The evidence column says where.
- **YELLOW, partly built.** Part of it works. The row says exactly which part is missing.
- **RED, not built.** Describe it as a limitation or a future enhancement. Do not say it works.

What was checked: the committed code at commit `5f9d97a` on `main`. Whether microverse.cloud runs this exact
commit was not checked. File:line references are to that commit unless marked "(in progress)".

**Work in progress right now.** While this audit ran, other teammates were editing the pages in
`src/mefile/static/`, `src/mefile/app.py` and `src/mefile/converter.py`, and adding a new module, `src/mefile/readings.py` ("other ways to read this"). Some fixes
below are already half-built in their unsaved work: a "what is sent" notice before the understudy, softer
wording, a "this reading doesn't fit me" button, and alternative readings for each claim. None of it is
committed yet, and the server does not use any of it yet. Rows that depend on it say "(in progress)". Check them
again before the presentation.

---

**Update, later the same afternoon (commit `66d61bf`).** Points 2 and 3 are now built on the server, with the
screens being wired:
- Every claim now carries 2 or 3 "other ways to read this" lines (`src/mefile/readings.py`). They name settings
  such as job role, team norms, language, being new or working remotely, and never a kind of person. They
  appear in the file data and on the recipient's guide, not in the me.md text.
- A person can say "this reading doesn't fit me" even when the answer is right, with a note of up to 300
  characters. The claim leaves me.md in both versions and leaves the coaching version entirely. The answers
  stay, because the person says the answers are right. The claims gate still passes. There are 30 tests in
  `tests/test_readings.py`.
- Demo case: S01=C and S05=C gives "Tends to let disagreements pass...". The page now shows readings such as
  workplace hierarchy and being new, and the person can dispute the claim.

---

## Answers to Mark's questions

**Risk 3, Ask Will: "When someone uses the AI twin, exactly what information goes to Claude, and do they
actively agree before it is sent?"**
Each time the person presses Ask, the browser sends two things to our server: the me.md file shown on screen
and the question. The server forwards them to Anthropic's Claude API (model `claude-opus-5-5`). Nothing else is
sent: no answers file, no name, no email, no IP address. The file is the version the person picked under
sharing. The limited coaching version is the default. The full version, which includes their own written
messages and reasons, goes only if they switched to it. Yes, they agree first. AI processing is a separate,
optional checkbox. The server refuses every understudy request without it (HTTP 403, meaning "refused"), so
the agreement is enforced by the server, not just by the page. The full trace is in section 2.

**Risk 5, Ask Will: "Can the system recognize that the same answer may have several reasonable
explanations?"**
Not today. The file adds one general warning for two vocabulary questions (B05, B40), and some general
cautions. It does not offer other explanations for a specific claim. Here is a real case we tested. A person
who picks "go along in the meeting" in the situations S01 and S05 gets the claim "Tends to let disagreements
pass or go along rather than push back". The claim cites S01 and S05 and passes the claims gate, with nothing
flagged. The same choices could come from workplace hierarchy, a culture where you do not contradict a
manager in public, being new or on a visa, or a past bad experience. The file says none of that. A fix is in
progress (`src/mefile/readings.py`). It adds two or three fixed, cautious "other ways to read this" lines for
each claim. Today they would go into me.json only, not into the me.md text.

**Risk 1, Ask Steven: "How would an employee know their manager cannot see whether they participated?"**
There are no accounts. The server keeps a consent ledger: an append-only file, meaning entries are added and
never edited. Each entry holds a time, the person code the person typed (for example SAM-07, never a name), the
event, and the choices they made. Events are consent, withdrawal, share created and share revoked. A share
entry also records the recipient label and the purpose. Someone who declines everything leaves no record,
because nothing is sent. Someone who agrees to build a profile but says no to AI processing does leave a
record, and it shows that "no". Anyone with the team code can read the ledger in `/admin`. It lists each person
code with their choices, whether they withdrew, and who they shared with and why (`src/mefile/admin.py:160-183`).
In a real workplace, whoever runs the server could see this. If the person codes can be linked to people, they
would see who took part. Today, an employee knows only what the privacy page tells them
(`src/mefile/static/privacy.html:98`). That page says the operator sees the consent record but not answers or
files. No code keeps a manager from seeing it. That protection would have to be a rule in the organization.

**Risk 2, Ask Will: "What stops a manager from using a downloaded file in another system?"**
Nothing technical. Every me.md must contain the exact refusal text, or export is blocked
(`src/mefile/claims.py:95-97`, `src/mefile/converter.py:531`). That text tells any AI to refuse use for hiring,
promotion, ratings, pay or discipline. The rule is written into the file, but nothing enforces it. A person can
delete it or ignore it, and another AI tool may not follow it. Say it is a use restriction, not a guarantee.

**Risk 4, Ask Will: "What if an exaggerated claim cites a valid answer?"**
The gate lets it through. It checks that each claim points at real answers. It does not check that the answers
support the wording (`src/mefile/claims.py:24-26`). The S01/S05 case above is exactly this. Today the person can
mark a claim with "Question this claim", but that note stays on their page. It does not change the file and is not
shared with anyone. See point 3.

**Risk 6, Ask Will: "Can we show a real failure of our judge and what we learned?"**
Yes, two. The stronger one is in the real judge's own pipeline, not a stand-in. The judge's style check
(`judge/features.py`, `style_fidelity()`) runs before the AI judge and hands it flags as evidence. It counts a
possessive ("the supplier's") as a contraction. So a person who writes formally and never contracts ("I will",
"I am"), but uses one possessive, is recorded as "a person who contracts". A response in her exact formal
register is then flagged for "losing her contractions". Remove the possessives from her writing and the flag
disappears. The flag also misses the reverse case. The AI judge is told about the flag and may mark the answer
down. What we learned: a deterministic check can be confidently wrong about a person, which is why humans rate
blind alongside the judge. The fix is small and listed in `docs/judge-mistake-example.md`. Three tests pin the
mistake (`tests/test_judge_known_mistakes.py`). The second failure, below, is the stand-in judge.
With one caveat. The judge's built-in self-test, run with the simple stand-in judge, fails 3 of 10 tests.
Rerun today: `python -m mefile.judge selfcheck --fake` gives 7/10. The clearest failure is the fairness test.
The same answer written in polished English scored 2, and in plain English scored 4, a 2-point gap where the
rule allows 1. The caveat: the stand-in judge only counts shared words. It is not the real AI judge. The repo
has no recorded run of the real judge and no human ratings to compare with. So this is a real failure of a
simple judge, which is why the real judge reads for meaning and has an explicit fairness rule. Whether the real
judge passes has not been measured.

---

## 1. The table

| Protection | Status | Evidence (file:line) | What to say in the presentation |
|---|---|---|---|
| **Point 1. Explain what leaves the browser when Claude is used** | YELLOW | Separate optional checkbox: `static/index.html:149`. Server refuses without it: `app.py:72`, `app.py:291-293`, test `tests/test_app.py:92-98`. Privacy page says file and question go to Anthropic: `static/privacy.html:87`. What is sent: `static/index.html:671` (in progress: `static/app.js:719-720`), `runner.py:50-59`. Nothing stored, logs show path only: `app.py:134-135`. | "When you press Ask, your file and your question go through our server to Anthropic. We keep neither. You agree to this separately, and the server enforces it." Missing: the consent text says "your file" but not "and your question". It does not say which version is sent. The provider terms are not spelled out. A notice at the moment of sending is in progress (`index.html:330`, `:372`, unsaved). |
| Point 1, paste into your own AI | RED (outside our control) | Download me.md (committed); Copy button (in progress: `static/app.js:897-900`) | "If you paste your file into ChatGPT, Claude or another tool, that company's terms and your own account settings apply. We cannot see or recall it." The in-progress copy screen suggests the full version for your own AI, and that version includes your own words. |
| **Point 2. Show that an answer may have several explanations** | RED | Only the B05/B40 vocabulary note: `converter.py:354-356`, gate warning `claims.py:93-94`. General cautions: `converter.py:360-364`. Probe: S01=C, S05=C gives claim C01 "Tends to let disagreements pass..." and the gate passes. | "Today the file gives one reading per claim. It warns that answers are small evidence, but it does not list other explanations. We are adding fixed 'other ways to read this' lines." (in progress: `src/mefile/readings.py`, me.json only) |
| **Point 3. Challenge an interpretation when the answer is correct** | YELLOW | "Question this claim" saves a note in the browser only: `static/index.html:479-499`. The note goes only into `answers_corrected.json`, not me.md or me.json: `static/index.html:629`. Withholding a trait area removes trait claims but not situation claims: `converter.py:118` (no withhold input), probe confirms C01 survives withholding all five areas. | "You can flag a claim you disagree with, and you can choose not to share. Today the flag does not change or travel with the file." A "this reading doesn't fit me, rebuild" button is in progress. The server ignores it today (`app.py:317-321`). |
| **Point 4. Show a real judge mistake** | GREEN (shown) | Real pipeline: the style check counts a possessive as a contraction and flags a formal writer's own register, `docs/judge-mistake-example.md`, `tests/test_judge_known_mistakes.py`. Stand-in judge fails 3 of 10 self-tests, rerun today: fairness S06 polished 2 vs plain 4; generic filler not flagged; assistant phrases not penalised. Written up: `docs/judge.md`, "Known failure modes". Known design flaw: matching letter earns at least 2 of 4 even with a generic reason: `docs/judge.md`. | "A simple word-counting judge favoured one writing style by 2 points. That is why ours reads for meaning and has a fairness rule. We have not yet measured the real judge against people." Do not show a real-judge agreement number: none exists in the repo. |
| **Risk 1. Pressure to participate** | YELLOW | Voluntary wording and optional choices: `static/index.html:144-154`. Declining everything sends nothing. Partial "no" is recorded: `app.py:301-303`. Operator view per person code: `admin.py:160-183`. | "Saying no to everything leaves no trace. Saying no to AI processing is recorded against your person code, and whoever runs the server can see it. Stopping employer pressure needs an organizational rule, not software." |
| **Risk 2. Employer misuse** | YELLOW | Refusal text required in every file or export is blocked: `converter.py:51-56`, `claims.py:95-97`, `converter.py:531`. Prohibited uses also in me.json: `converter.py` sidecar `prohibited_uses`. Red-team script exists (`redteam.py`) with no recorded live run. | "The file carries its own use rules and an exact refusal. These are restrictions, not technical guarantees. A recipient can ignore them." |
| **Risk 3. Personal info and outside AI** | YELLOW | Server keeps no answers or files: `app.py:8-12`, `app.py:317-331` (returns, never writes). Share links encrypted in the browser, key after `#`: `shares.py:8-14`. Logs show path only: `app.py:134-135`. Consent gate for AI: `app.py:291-293`. | "Answers pass through our server to build the file and are not saved. Shared files are encrypted, and we cannot read them. Anthropic receives what you send to the understudy and keeps it under its own terms." Missing: answers do leave the browser for each build, so "built in your browser" is wrong (see section 3). The ledger keeps recipient labels and purposes permanently. |
| **Risk 4. Inaccurate or exaggerated claims** | YELLOW | Gate refuses: no evidence, skipped or unknown IDs, held-out test IDs, fixed labels, missing refusal: `claims.py:67-103`. Middle scores say "no clear tendency": `converter.py:321`. Download needs gate pass and the person's review tick (app). | "Every claim points at real answers, and the gate refuses ones that do not, live. It cannot check that the wording fits the answers. A claim can cite a true answer and still misread you." Demo the S02 refusal. |
| **Risk 5. Cultural, language, personal differences** | YELLOW, close to RED | B05/B40 language note: `converter.py:354-356`. Fixed-label block: `claims.py:39-43` (a list of phrases, so a reworded label gets past it). Judge fairness rule: `judge/rubric.py:95`. Fairness test fails on the stand-in judge; real judge not measured. | "We flag two vocabulary questions and block fixed labels. We have not built a way to show other explanations, and we cannot establish broad fairness from a one-day test." |
| **Risk 6. AI judge misjudges resemblance** | YELLOW | Blind rating sheet and agreement statistics built: `judge/agreement.py:331`, `:458`. Judge cannot grade its own model unless overridden: `judge/anthropic_backend.py:44-49`. Fails closed (no score rather than an invented one): `docs/judge.md` Method step 5. | "The tools to compare the judge with human raters exist. We have no measured agreement yet." Report any number only after two people have rated. |
| **Risk 7. Voice interviews** | GREEN (not in use) | Off unless ElevenLabs keys are set: `voice.py:32`, `voice.py:49-52`. Text only, no voice analysis, by design: `voice.py:8-15`. | "Voice is switched off. Keep it out of the demo." If it is ever turned on: "conversation deleted" is not true today, because `voice.delete_conversation` is never called. "Recording off" is a setting on ElevenLabs, not enforced in our code. The transcript route has no consent check (`app.py:271-278`). |
| **Risk 8. Sharing, withdrawal, deletion** | GREEN, with limits | Revoke deletes the encrypted copy and keeps a stub: `shares.py:146`, `shares.py:281-296`. Expiry at most 90 days, with an hourly sweep: `app.py:433`. Withdraw revokes all consent tokens and turns off that person's links: `app.py:305-316`, `shares.py:299`. | "Turn off a link and it stops working at once. Withdraw and your links go off." Limits: saved copies and AI-provider records cannot be recalled. The consent ledger is never deleted, by design (`admin.py:16-17`). It keeps who you shared with and why. Withdraw turns off links only from the browser that holds your consent. |

---

## 2. Point 1 in detail: exactly what goes to Anthropic

**The understudy (Rehearse with your understudy).**

1. **Agreement.** The AI processing box is separate and optional (`static/index.html:149`). With it unticked, the
   Ask button stays disabled (`static/index.html:655`). If the request is sent anyway, the server refuses it, because
   the consent token does not include `ai_processing` (`app.py:72`, `app.py:291-293`). A consent token is a random
   code the server issues when the person agrees. The server keeps only a scrambled copy (a hash), in memory.
2. **Browser to our server** (`POST /api/twin`). The request carries:
   - `markdown`: the me.md currently on screen. That is the version chosen under sharing: limited coaching by
     default (`static/index.html:268`), full if the person switched. Any trait areas they withheld are already
     removed.
   - Either `question_id` (one of the practice situations P01 to P20, `practice.py`), or `own_question` (their
     own text, up to 600 characters, `practice.py:25`) with `kind`. The server accepts both (`app.py:386-405`). The committed page
     sends practice IDs only; the in-progress page adds "ask your own".
   - The consent token, in a header.
3. **What the file contains.** The person code, not a name. Their scenario choices, trait scores and the
   claims. The full version also has their own written messages and reasons, word for word
   (`converter.py:72-75`, `converter.py:135-138`). The coaching version leaves those out.
4. **Our server to Anthropic** (`runner.py:50-59`). Two calls to the Claude Messages API, using the team's key:
   first the whole me.md, then the me.md, the model's reply and the question. There is no hidden system prompt.
   Model `claude-opus-5-5`, effort `medium` (`runner.py:32-33`). The file is cut off at 200,000 characters
   (`app.py:214`). The person's IP address and token are not forwarded.
5. **What our server keeps.** Nothing from the request. The log line is the method, the path and the status
   code (`app.py:134-135`). On an error, the page gets only the error type, never the content (`app.py:217-218`).
   The answer goes back to the browser. Reactions ("sounds like me" or "not me") stay in that browser tab.
6. **Rate limit.** 30 understudy answers per consent token per hour, then a "try again later" message
   (`app.py:77-78`, `app.py:208-212`). Each answer is two API calls. Agreeing again issues a new token, so this
   limits cost. It is not a hard cap per person.
7. **What Anthropic may keep.** Per Anthropic's published API terms; verify before quoting. Commercial API
   inputs and outputs are deleted from Anthropic's systems within 30 days by default. Content flagged by its
   safety systems may be kept up to 2 years. API data is not used to train models without permission. A zero
   data retention agreement can shorten this. Whether the team's key has one was not checked. Anthropic's privacy
   center and its developer docs describe the default slightly differently, so read the current pages before
   putting any number on a slide (sources at the end).

**Pasting me.md into your own AI.** The person downloads me.md (or, in the in-progress page, copies it). After that, lumin8r has no
part in it. The tool's own terms and the person's account settings decide what is kept and whether it is used
for training. We cannot see, limit or recall it. Say so plainly.

**Other AI paths, for completeness.** The team's evaluation (Claude, GPT and the judge) runs only on the
hackathon workbench, which is off by default (`team.py:243`, `LUMIN8R_WORKBENCH`). Building the profile uses no
AI at all (`converter.py:1-10`).

---

## 3. Docs that say more than the code does

Fix these before the presentation, or do not quote them.

**Data-flow claims**

| Where | Says | Problem | Suggested wording |
|---|---|---|---|
| `src/mefile/static/index.html:350` (in progress, new) | "Your file is built from your answers, in your browser. Nothing is stored on our server." | The file is built on our server (`/api/convert`). The server stores consent records and encrypted shares. | "Your answers go to our server for one conversion and come straight back as your file. We do not save them." |
| `docs/how-lumin8r-works.html:67` | "Nothing leaves your browser unless you choose." | Answers go to the server for every build. | Same as above. Add that the understudy sends the file and question to Anthropic. |
| `docs/product.md:15`, `docs/product.md:27`; `static/home.html:83`, `:99` (committed) | "Answers stay in your browser" / "runs in your browser" | Same. | "Answers are kept in your browser. They pass through our server, without being saved, to build your file." |
| `docs/risk-and-acceptance.md` section 4, "Who sees" redline | "They pass through the converter on this computer" | The converter runs on the server. | "...pass through our server to build the file and are not saved." |
| `docs/risk-and-acceptance.md` threat model, voice row | "conversation deleted (`voice.py`)" | `delete_conversation` is never called. | "deletion is written but not wired in". |
| `docs/risk-and-acceptance.md` threat model, over-trust row | "instruction 7 tells the model not to say it is an AI" | Out of date. Instruction 7 now says do not deny being an AI (`converter.py:396`). | Update the row. |
| `src/mefile/shares.py:17-18` (code comment) and `privacy.html` "never content" | "the free text (purpose, recipient label) are gone from disk" | Gone from the share file, but kept for good in the consent ledger (`shares.py:256-257`). | "...gone from the share file. The consent ledger keeps the purpose and recipient label as the record." |
| `docs/m3-risk-mapping.md` row 4 | "The employee ... questions claims" | True, but the question does not change or travel with the file. | Add: "questions stay on the person's page". |
| `docs/m3-risk-mapping.md` row 8 | "Admin can delete a person's data" | Admin deletes team-hub folders only. The ledger is never deleted. | "Admin can delete a person's team-hub data. The consent record is kept." |
| `static/index.html:371` (committed) and `static/app.js:169` (in progress) | "Try your twin" in the ledger's `ai_services` label | Old name. The ledger records the wrong feature name. | "Rehearse with your understudy". |

**Wording that overstates accuracy (the review's "additional wording concern")**

The review's suggested replacement for the headline: *"A coach, teammate, or AI assistant can use your reviewed
profile to better understand your reported preferences and adapt how they communicate and collaborate with you.
The profile offers a starting point for conversation, not a complete picture of who you are."*

| Where | Current | Suggested |
|---|---|---|
| `docs/how-lumin8r-works.html:57` | "...can then work with you the way you actually work." | The review's replacement, above. |
| `static/responsible-use.html:58` (committed; being edited now) | "helps people and AI tools work with you the way you actually work" | "helps people and AI tools understand your reported preferences. It is a starting point, not a complete picture." |
| `docs/product.md:9` | "work with me the way I actually work" | "understand how I say I prefer to work" |
| `docs/how-lumin8r-works.html:70` | "...so it drafts and answers in your voice." | "...so its drafts can follow how you described yourself and how you write. Check every draft before you use it." |
| `docs/pitch.md:79`, `docs/pitch.md:81` | "your voice in any LLM" / "keep your voice through your company's next AI switch" | "your reviewed preferences in any AI tool" / "keep your preferences through the next AI switch" |
| `docs/market-research.md:45` | "Drafting in your own voice ... Your voice and preferences survive..." | "Drafts that follow your stated style ... Your stated preferences survive..." |
| `static/index.html:184`, `:676` (committed); `static/app.js:782`, `:888` (in progress) | "Does it sound like you?" / "When it sounds like you, tick..." | Fine for the person checking their own file. Keep "Does it sound like you?" as a question. Change "When it sounds like you" to "When you have checked it". |
| `src/mefile/practice.py:131` | understudy prompt "in your own voice" | Instruction to the model, not a product claim. No change needed. |

Several of the home-page "in your voice" lines were removed from the working copy during this audit (in
progress). Check them again in the committed version before quoting.

---

## 4. Say as limitations

- The claims gate checks that claims point at real answers. It cannot check that the wording is fair to the person.
- The file gives one reading per claim. It does not show other explanations: culture, hierarchy, disability, being new, past experience.
- Flagging a claim you disagree with stays on your page. It does not change or travel with the file today.
- Use rules in the file are words. A recipient or another AI tool can ignore them.
- Saying no to AI processing is recorded against your person code, and whoever runs the server can read the consent record.
- Anything sent to Anthropic is kept under Anthropic's terms, not ours. Anything pasted into another AI is outside our control.
- The consent record is never deleted. It keeps who you shared with and why.
- Copies already saved, downloaded or pasted cannot be recalled by revoking or withdrawing.
- The judge has not been measured against human raters, and the real judge's self-test result is not recorded. A simple stand-in judge failed the fairness test.
- A short questionnaire on one day cannot establish broad fairness or accuracy.
- The understudy rate limit is per consent token. It limits cost, not people.

## 5. Future enhancements

- Show "other ways to read this" next to each claim, in the file as well as in me.json (started: `src/mefile/readings.py`).
- Let the person dispute a reading, and carry that dispute into the file, or drop the claim (UI started; server not wired).
- Mark claims that rest on a single answer as "based on one answer".
- Show a "what is sent, which version" notice each time before the first understudy request (started in the working copy). Name the version in it.
- Spell out Anthropic's retention terms on the privacy page once verified, and record whether the key has zero data retention.
- Add a consent-record retention date, and delete records after it. Or record share purposes without the free text.
- Let withdrawal turn off links from any device, not only the browser holding the consent.
- Run the judge self-test against the real judge and collect two blind human ratings. Report agreement and at least one real-judge failure.
- Run the red-team misuse probes live and report the refusal rate.
- If voice is ever turned on: wire in conversation deletion, check "recording off" in code, and add a consent check on the transcript route.
- For real workplace use: an organizational non-retaliation rule, and a server run by someone other than the employer.

## Sources for the Anthropic terms

- [API and data retention (Claude developer docs)](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention)
- [How long do you store my organization's data? (Anthropic privacy center)](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data)
- [I have a commercial account, how do you handle my data? (Anthropic privacy center)](https://privacy.claude.com/en/articles/8956058-i-have-a-commercial-account-how-do-you-handle-my-data)
