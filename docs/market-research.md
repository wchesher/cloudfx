# Market research: mefile (first pass)

For Steven, 2026-11-14. Fast desk research. Vendor claims are marked as vendor claims; anything not confirmed on a primary page is "(unverified)".

## 1. Landscape

| Player | What it does | How the profile is built | Who owns / controls it | Portable? | Primary buyer |
|---|---|---|---|---|---|
| **Wethos** (WethosAI) | "The Human Context Platform": Twins that simulate how specific people may respond to decisions; Wethos Style assessment | Observed Twins: customer-approved org context and professional info, no participation needed, thin evidence "treated as hypotheses". Permissioned Twins: consent and participation. Style: 8- or 84-question self-report, or LinkedIn connect, plus 360 input | The customer organization (Observed); the person participates (Permissioned) | Export not mentioned on site | Enterprises; site copy targets security leaders and executives |
| **Cloverleaf** | AI coaching pushed into Slack, Teams, email, calendar | Synthesizes up to 13 licensed assessments (DISC, Enneagram, 16 Types, CliftonStrengths...) plus behavioral signals and HRIS data | Employer platform | Not stated (unverified) | HR / L&D, coaches |
| **Crystal Knows** | DISC prediction for sales and communication | Inferred from public data (LinkedIn etc.) plus a database of anonymous assessment results; ~80-85% accuracy (vendor claim) | Crystal and its paying user; the profiled person is not asked | No | Sales teams |
| **Humantic AI** | "Buyer intelligence": DISC and Big Five per stakeholder | Inferred from open-web data; shows confidence score and source list per profile | The vendor's customer | No (CRM integrations) | Sales / RevOps; hiring per third-party reviews (unverified) |
| **Delphi** (now delphi.co) | "Digital Minds" of experts people can chat with | Creator uploads writing, podcasts, video, sites | Creator ("all data is owned by you") | Export not stated | Experts, coaches, creators |
| **Personal.ai** | Per-user small personal language models with a memory stack | Observed: the user's own content and conversations | User (consumer); now carrier deployments (MODEL-4, Comcast trial) | Unverified | Consumers; telecom operators |
| **Microsoft 365 Copilot memory** | Personalizes Copilot from saved memories and communication | Observed behavior plus explicit "remember" | Tenant admin: can toggle, eDiscovery-export, delete; no memory audit logs | Admin export via Purview; user export noted in one message-center post (unverified) | Enterprise IT |
| **ChatGPT / Claude memory** | Assistant remembers facts and chat history | Observed chats plus explicit saves | The user, inside one vendor | Partial: Claude has a prompt-based import from ChatGPT/Gemini (experimental, reviews mixed) | Consumers, teams |
| **Truity / 16Personalities teams** | 16-type assessments for team building | Self-report questionnaire | Vendor account; team admin sees results | PDF reports only | Team leads, HR, coaches |
| **Stanford Human Context Protocol** (research) | Proposed protocol for user-governed preference context across AI systems | User-stated preferences, not provider inference | The user, with "scoped access" and revocation | Yes, by design; prototype only | None yet (working paper, Dec 2025) |

## 2. The gap

**Where mefile is genuinely different.** No player found combines all four of these:
1. **The employee holds the artifact.** Every workplace tool above is employer-, buyer- or vendor-held. The person being profiled is either the customer's subject (Crystal, Humantic, Observed Twins) or a tenant user (Copilot, Cloverleaf).
2. **Per-claim evidence from the person's own answers.** Humantic shows sources, but for traits inferred from public web data. mefile cites the specific item and scenario IDs and allows no claim without evidence.
3. **Works with any model, as a plain file.** It is not a vendor memory store and needs no protocol adoption. It loads into Copilot, ChatGPT or Claude today.
4. **It measures itself.** The judge reports how closely each model resembles the person with and without the profile. None of the vendors publishes an equivalent fidelity score (unverified; no public benchmarks found).

**Where it is NOT different (say this before a judge does):**
- **Portable, scoped, revocable context is Stanford HCP's thesis.** mefile is a working instance of that idea, not the invention of it.
- **Consent-based twins exist.** Wethos Permissioned Twins are already consent-based.
- **Thin evidence.** A 30-minute self-report gives far less to work with than observed behavior (Copilot, Personal.ai) or a lifetime of content (Delphi). Self-report can be gamed.
- **Revocation is a promise, not an enforcement.** Once a markdown file is pasted into an LLM, it cannot be recalled.
- **Employee-held does not remove the power imbalance.** "Share it with your manager" can still feel compulsory.
- **No validation that it works for the stated uses.** IPIP-50 is validated for broad self-reported traits, not for simulating a person or for coaching outcomes.
- **No distribution and no network effect.** Cloverleaf's moat is seeing both sides of every relationship.

## 3. Buyers and why they would care

- **Coaching and HR platforms** (Cloverleaf-type, coaching marketplaces): cheaper onboarding of a coachee, and a consent story that makes privacy review easier.
- **Team leads**: a "how to work with me" view that a teammate chose to share, rather than a type label from HR.
- **Employees**: context that survives job changes and AI-vendor changes, and that they can read and correct.

**Three use cases**
1. **Coaching kickoff.** The coachee brings a scoped me.md to a human or AI coach. *Coaching starts at session one, not session three, and the coachee decides what the coach sees.*
2. **Drafting in your own voice.** The employee loads me.md into whichever LLM the company licenses. *Your voice and preferences survive your employer's next AI-vendor switch.*
3. **Team "user manual of me".** The employee shares a minimum-necessary version with a new team, then revokes or updates it. *A teammate's how-to-work-with-me, with receipts, that they wrote and can withdraw.*

**Three extensions or adaptations**
- **Onboarding**: a new hire shares a profile with their buddy or manager in week one. *Risk:* putting it on an onboarding checklist makes it mandatory in practice. It must stay off checklists, and declining must leave no trace.
- **Manager 1:1 prep**: the employee generates a short brief before a 1:1 ("what I want to discuss, how I take feedback"). *Risk:* drift into evaluation. Keep it employee-initiated, single-use and unretained, and never put it in the HRIS (EU AI Act Annex III(4) territory if it touches performance).
- **Cross-cultural / second-language communication support**: help a second-language speaker get drafts that keep their intent, or help a reader interpret a direct versus indirect style. *Risk:* IPIP vocabulary items and English writing samples can misrepresent second-language speakers. Let people add first-language samples, flag language-sensitive items, and never infer nationality or culture.

## 4. How it complements Wethos (not competes)

- **A consent-native on-ramp to Permissioned Twins.** A person arrives with a reviewed, cited me.md. Wethos ingests it instead of building from scratch, and the person's control is visible, which helps adoption.
- **Turns Observed Twin hypotheses into confirmed or corrected claims.** Wethos already labels thin-evidence assumptions as hypotheses. mefile's evidence citations and correction flow are a way for the person to confirm or correct them. The Wethos Style crosswalk is labelled as hypotheses for the same reason.
- **A neutral fidelity harness.** The blind judge can score any twin, Wethos included, against the person's real answers. That gives Wethos a third-party number for its core claim that human context changes outcomes.

## 5. Two practitioner prompts (10 minutes)

1. "Think of a time an employee's assessment results ended up somewhere the employee didn't expect. What happened? Now suppose an employee hands you a profile they edited themselves. Would you trust it more or less than one the platform generated, and what would you need to see to trust it?"
   *Decides:* whether employee edits show as an edit trail ("changed by employee, original answer X") or are silent. It also tests whether the review-and-correct step reduces trust.
2. "Here are three things an employee could share: (a) full writing samples, (b) trait summaries with the answers behind them, (c) communication tips only. Which would you let an employee give a manager, which a coach, and which would you never allow? (Wethos staffer: which would you need to seed a Permissioned Twin?)"
   *Decides:* the default share scope and the minimum fields for a Wethos import. Listen for a line like "I'd never let a manager see X". That is a quotable design constraint.

## 6. Sources

- Wethos home: https://wethos.ai/
- Wethos science and guardrails: https://kb.wethos.ai/the-science-behind-wethosai
- Wethos Twins launch, Aug 18 2026 (secondary): https://kingy.ai/?p=929137 ; https://www.techdogs.com/tech-news/globe-newswire/wethosai-opens-stuart-mcclures-twin-to-the-public
- Cloverleaf: https://cloverleaf.me/how-does-cloverleaf-work ; https://brandonhall.com/cloverleaf-an-ai-coaching-platform-built-for-teams/
- Crystal: https://crystalknows.com/how-predictions-work ; https://business.com/articles/crystal-knows-all-youre-being-profiled/
- Humantic AI: https://humantic.ai/product ; https://toolsforhumans.ai/ai-tools/humantic-ai
- Delphi: https://www.delphi.co/ ; https://www.businesswire.com/news/home/20240806868061/en
- Personal.ai: https://Personal.AI/your-true-personal-ai ; https://lite.aol.com/tech/story/0022/20260317/9673238.htm
- Microsoft 365 Copilot memory: https://learn.microsoft.com/en-us/microsoft-365/copilot/copilot-personalization-memory ; https://mc.merill.net/message/MC1158329
- ChatGPT memory: https://help.openai.com/en/articles/8590148-memory-faq
- Claude memory import: https://pcworld.com/article/3076376/claude-can-now-import-chat-histories-from-chatgpt-and-other-ais.html ; https://www.tomsguide.com/ai/you-can-move-your-chatgpt-memory-to-claude-in-60-seconds-heres-how
- Truity TypeFinder for the Workplace: https://www.truity.com/test/type-finder-workplace
- 16Personalities Team Assessments: https://www.16personalities.com/teams
- Stanford HCP paper: https://digitaleconomy.stanford.edu/publication/robust-ai-personalization-controls-the-human-context-protocol/ ; project page: https://digitaleconomy.stanford.edu/project/loyal-agents/hcp-human-context-protocol/
