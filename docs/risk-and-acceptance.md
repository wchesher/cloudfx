# Risk and acceptance pack (Mark)

Acceptance, ethics, risk, regulation and Wethos liaison for mefile, 2026-11-14. Not legal advice; check
effective dates before putting any law on a slide.

## 1. Threat model

L/I = likelihood / impact (L low, M medium, H high).

| Threat | Who is harmed | L/I | Our control | Residual risk |
|---|---|---|---|---|
| Employer coercion: consent not freely given | Employee | M/H | Consent screen first (`index.html` `#consent`); ledger (`app.py` `/api/consent`); server stores no answers | A click cannot prove freedom; `/api/convert` does not check consent server-side |
| Function creep into hiring or ranking | Employee | M/H | Use limit in every me.md and `me.json` `use_limits`; 90-day review-by date | Words, not enforcement |
| Spear-phishing with verbatim writing | Employee, colleagues, org | M/H | `coaching` scope drops verbatim messages and reasons (`converter.SHARE_SCOPES`) | The app pre-selects `full`; default should be `coaching` |
| Over-trust in simulated answers | Team leads, employee | H/M | "AI-generated representation" banner and me.md header | me.md instruction 7 tells the model not to say it is an AI; pasted elsewhere, the label depends on the host tool |
| Stereotyping from trait labels | Employee | M/M | Gate blocks fixed labels (`claims.LABEL_PATTERNS`); traits are tie-breaker only | A paraphrase ("a natural loner") passes the regex |
| Language-background bias (polished English scored higher) | Non-native speakers | M/H | Judge fairness rule; `selfcheck` probe (polished vs plain within 1 point); B05/B40 warning | Two fictional probes; run on the live judge and report |
| Prompt injection via free text in me.md | Employee, downstream users | M/M | Free text rendered as quoted data; me.md instruction 6; judge treats inputs as data | Verified: "Ignore previous instructions..." in W01 renders quoted and passes the gate unflagged |
| Real answers leaked into a public repo | Volunteer, teammate | M/H | `.gitignore` excludes `private/`, `consent/`, `*.local.json`; server logs paths only | Judge reports and paste packets quote real answers; check `git status` before every push |
| Voice intake: recording consent, biometrics, emotion inference | Teammate | L/H | Separate opt-in; AI disclosure first; transcript only, `record_voice=false`, conversation deleted (`voice.py`); employee edits transcript | ElevenLabs hears raw audio; Cal. Penal Code 632 all-party consent; STT worse for some accents |
| Judge gamed or biased toward its own model | Teams, Wethos, panel | M/M | Blind run IDs (`tests/test_judge.py`); self-preference warning; fail-closed; probes; blind human ratings | Default judge is Claude Opus 5.5, also LLM A; choice points dominate scenario scores |

## 2. NIST AI RMF map

- **Govern:** use limit in every me.md and `me.json`; append-only consent ledger; this pack is the risk assessment, Mark signs off.
- **Map:** the threat model above; held-out IDs (S02, S04, S06, W02, W04) mapped as leakage and blocked by the gate.
- **Measure:** `python -m mefile.judge selfcheck` (7 probes, fairness included); AI-to-human agreement from two blind raters; profile vs no-profile lift on both models.
- **Manage:** gate fails closed; download needs gate pass plus review tick; correction regenerates and clears the tick; withdrawal; review-by date.

## 3. Regulatory one-pager

| Anchor | How we comply |
|---|---|
| GDPR Art. 20 and 88; EDPB Guidelines 05/2020 on consent | me.md is the portable form; the employee holds it and picks the share version |
| EU AI Act Annex III(4) (employment AI is high-risk) | Out of scope by design: no hiring, promotion, termination or evaluation |
| EU AI Act Art. 5(1)(f) (no workplace emotion recognition) | Text only; nothing inferred from voice, face or behavior |
| EU AI Act Art. 50 (disclose AI content) | Every profile and simulation labelled an AI-generated representation |
| CCPA/CPRA (employee data since 2023) | Know, correct, delete: every claim shown, answers correctable, withdrawal |
| Colorado AI Act (SB 24-205) | No consequential employment decision; effective date has moved, verify |
| IEEE 7005-2021 | Employee reads and controls the file; share scopes; ledger |
| AERA/APA/NCME Standards (2014) | Validity claimed only for broad self-reported traits; B05/B40 language caveat |

## 4. Consent copy review (do not edit index.html; hand to the builder)

Current text, verbatim from `src/mefile/static/index.html`:

> This tool builds a profile from **your** answers so that **you** can use it with AI tools for coaching, reflection and communication support. It is **not** for hiring, promotion, discipline or ranking.
> - Who sees your answers: only you, in this browser. The server keeps no answers and no profile; it records only this consent.
> - AI services: the profile itself is built without AI. If you choose to paste it into an AI model (Claude, GPT) or use the voice interview (ElevenLabs), that service processes it under its own terms.
> - Your control: you can skip questions, correct answers, withhold whole sections, and withdraw. A manager's request does not replace your agreement, and declining is never recorded as a personality characteristic.

Redlines:

- Heading: `- Before anything is processed` / `+ Before you start: this is your choice`
- Voluntariness (add after the first paragraph): `+ Saying no, or stopping partway, changes nothing for you. We do not tell anyone whether you took part.`
- Who sees: `- only you, in this browser. The server keeps no answers and no profile` / `+ Your answers stay in this browser. They pass through the converter on this computer to build the file and are not saved. We save one record: your person code, what you agreed to, and when.`
- AI processors: `- (Claude, GPT) ... (ElevenLabs)` / `+ If you agree, the team tests your file on Claude (Anthropic) and GPT (OpenAI), and an AI judge (Claude, Anthropic) compares the results with your test answers. The voice interview uses ElevenLabs and its model providers. Each keeps data under its own terms.`
- Withdrawal: `- and withdraw.` / `+ and withdraw at any time with the Withdraw button. That clears this page and records the withdrawal; delete any file you downloaded, and the team deletes its copies.`
- Retention (new line): `+ We delete the consent record and any copies of your answers and responses by [date, e.g. 30 days after the event].`
- Checkbox: `- Paste it into AI models I choose, for testing` / `+ Let the team test my file on Claude and GPT, and let an AI judge compare the results with my answers`
- Withdrawal confirmation: `- Nothing was kept on the server` / `+ Only the record of your agreement and withdrawal was kept on the server`
- Share default: pre-select `coaching`, not `full`.

## 5. User acceptance test script

`python -m mefile serve`, then http://localhost:8080. Fictional DEMO01 data only.

1. Load. Expect: consent card only. [ ] pass [ ] fail
2. Click "I agree" with nothing filled. Expect: alert; `consent/ledger.jsonl` unchanged. [ ] pass [ ] fail
3. Enter `TEST-01`, tick "Build a profile" only, agree. Expect: receipt; ledger line with `purposes: ["build_profile"]`, `ai_services: []`. [ ] pass [ ] fail
4. Use the fictional example. Expect: "AI-generated representation" banner; green "Claims gate passed". [ ] pass [ ] fail
5. Click chip C01. Expect: evidence IDs shown, those answers highlighted. [ ] pass [ ] fail
6. Change one highlighted answer. Expect: profile regenerates, C01 changes, review tick clears. [ ] pass [ ] fail
7. Upload a copy of the example with `{"id":"S02","choice":"B","explanation":"x"}` added to `scenarios`. Expect: red "Claims gate refused export" naming S02; download stays disabled. [ ] pass [ ] fail
8. Reload the example, choose `coaching`. Expect: W01 and W03 show "verbatim message withheld"; "Hi team, I'm sorry" is gone. [ ] pass [ ] fail
9. Review box unticked: downloads disabled; ticked: enabled; edit an answer: disabled again. me.md shows Review by and file digest. [ ] pass [ ] fail
10. Withdraw consent, confirm. Expect: page cleared; ledger gains a `withdrawal` line for `TEST-01`. [ ] pass [ ] fail

## 6. The safeguard on stage: the claims gate

The gate, not coaching scope: it is the brief's own example ("flagging unsupported claims"), fails closed, and shows in one click.

Script (30 seconds), after the claim-to-evidence click:
"Every claim must point at answers the person actually gave. Watch what happens when a held-out test answer sneaks into the input. [upload S02 file] The gate refuses export and says why. Download stays locked. It also refuses claims with no evidence and fixed labels like 'is an introvert'. What it cannot do: check that the answers truly support the wording. That is why export also needs the person's own review, and why a reworded label can slip past the regex."

Stated limits: checks pointers, not meaning; finite label list; cannot stop someone sharing `full` scope.

## 7. Wethos liaison: questions for Wethos staff today

1. Is there an API or import path for an employee-held profile like `me.json`, and in what format?
2. How do Permissioned Twins record consent, and what happens to the twin on revocation?
3. How do you validate a twin: against held-out answers, human raters, or outcomes?
4. How should a crosswalk to Ideas, Relational, Action and Order be labelled so it does not claim to measure Wethos Style?
5. What would you consider misuse of a twin, and how do you detect it?
6. How do Observed Twins keep "hypotheses" from being read as facts by managers?
7. What context does your twin use beyond the kit, so we compare fairly?
8. Would your Human Cyber Range treat verbatim writing samples as a phishing asset, and what share scope would you recommend?

Record answers verbatim with name and role; each that changes a design is transdisciplinary evidence.

## 8. Residual risks closed (2026-11-14)

- **Consent is now checked on the server** (threat "Employer coercion", residual "`/api/convert` does not check consent server-side"). `POST /api/consent` returns an opaque `consent_token`; the server holds only its sha256 in memory, mapped to person code, purposes and time, and the ledger records the hash (`token_sha256`), never the token. `/api/convert` needs `build_profile`, `/api/twin` needs `ai_processing`, `/api/voice/session` needs `voice_interview`; otherwise 403 `{"error":"consent required","purpose":...}`. `/api/withdraw` revokes the token and every token for that person code (`revoked_token_sha256` in the ledger). A restart forgets all tokens, so people consent again. Still open: a click still cannot prove the consent was free; `GET /api/voice/transcript` is not gated; `/api/station/*` is ungated on purpose (team tooling over consenting teammates' on-disk data). Tests: `tests/test_app.py`.
- **The judge cannot silently grade its own model** (threat "Judge gamed or biased toward its own model", residual "Default judge is Claude Opus 5.5, also LLM A"). `AnthropicJudgeBackend` raises `JudgeConfigError` at construction when the judge model equals `runner.DEFAULT_MODEL`, naming `MEFILE_JUDGE_MODEL`; `MEFILE_ALLOW_SELF_JUDGE=1` opts in knowingly, and then the run must be reported as self-judged. The default string is unchanged, so a real judge run now needs `MEFILE_JUDGE_MODEL` set to a model not under test. Still open: choice points dominate scenario scores.
