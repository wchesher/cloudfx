# Legal, ethical and risk frameworks, and the Wethos angle

Working notes for the submission write-up and the panel. This is not legal advice; check the
effective dates before quoting any of them on a slide.

## The frameworks we anchor to, and the feature each one justifies

Judges reward evidence over lists. Use NIST AI RMF as the structure for the ethics section and cite
the others only where a feature puts them into practice.

| Framework | What it asks | Our feature that answers it |
|---|---|---|
| **NIST AI RMF 1.0** (Govern, Map, Measure, Manage) | A risk process covering the whole lifecycle | Overall structure: purpose and use limits (Govern), threat model (Map), tested judge with a known failure (Measure), review, correction and revocation (Manage) |
| **NIST AI 600-1, Generative AI Profile** | Confabulation, privacy, harmful bias, over-trust and anthropomorphization | Claims gate (no claim without evidence), the "AI-generated representation" label, insufficient-evidence verdicts, the language-fairness probe |
| **GDPR Art. 20** (data portability), **Arts. 15-17** (access, rectification, erasure) | People can get their data in a portable form and correct or delete it | me.md *is* the portable form; the app lets the person correct source answers and regenerate; withdrawal deletes the file and its key |
| **GDPR Art. 88 and EDPB Guidelines 05/2020 on consent** | An employee's consent is rarely freely given, because of the power imbalance | The employee, not the employer, holds the file and chooses a share version; declining has no effect and is never recorded as a trait |
| **GDPR Art. 22** | No solely automated decisions with significant effects | Hard-coded use limit: no hiring, promotion, discipline or ranking |
| **EU AI Act, Annex III(4)** | AI for recruitment, promotion, termination, task allocation by traits, or performance evaluation is high-risk | Same use limit; it is printed in every me.md |
| **EU AI Act, Art. 5(1)(f)** | Bans emotion recognition in the workplace | We infer nothing from voice, face or behavior; the profile holds self-report only |
| **EU AI Act, Art. 50** | Disclose AI-generated content | Every simulated response is labelled as a representation, never as the person's statement |
| **CCPA/CPRA** (covers employee data since 2023), **CPPA automated-decisionmaking and risk-assessment regulations** | Rights to know, delete and correct; risk assessments for significant decisions | Correction flow, deletion, and this document as the risk assessment |
| **Colorado AI Act (SB 24-205)**, **Illinois HB 3773**, **NYC Local Law 144** | Employment decisions made with AI need notice, bias audits and duty of care | Reason the use limit exists; out of scope by design |
| **AERA/APA/NCME Standards for Educational and Psychological Testing (2014)** | Validity belongs to an interpretation for a stated use, and fairness across language groups | Limits section: IPIP-50 is validated for broad self-reported traits, not for simulating people or for workplace decisions; vocabulary-item caveat (B05, B40) |
| **APA Ethics Code, Standard 9** (9.02 appropriate use, 9.06 cultural and linguistic factors, 9.10 explaining results) | Use assessments only for appropriate purposes and explain results | Plain-language profile, evidence links on every claim, language note |
| **IEEE 7005-2021, Transparent Employer Data Governance** | Employees understand and control the data employers hold about them | Consent ledger, share scopes, a profile the employee can read |
| **OWASP Top 10 for LLM Applications** (prompt injection, sensitive information disclosure) | A pasted file is an attack surface | Free text is quoted as data in me.md; the judge never sees which team or system wrote a response |
| **Belmont Report** (respect for persons, beneficence, justice) | Informed, voluntary participation by the volunteer | Consent screen before any answer is processed |

## What will excite Wethos

What their public materials say (sources at the end):
- They call themselves **"The Human Context Platform"**.
- They offer **Twins** in three kinds: *Observed* (built from organizational context, with assumptions "treated as hypotheses"), *Permissioned* (built with the person's knowledge and explicit participation), and *Expert Agents*.
- They also run a **Human Cyber Range**.
- Their **Wethos Style** assessment measures behavior on four scales: Ideas (Practical to Visionary), Relational (Factual to Interpersonal), Action (Methodical to Expedient) and Order (Flexible to Structured).
- Their stated guardrails rule out personnel decisions, ranking and rigid roles.
- CEO and co-founder Stuart McClure comes from security: *Hacking Exposed*, Foundstone, McAfee CTO, Cylance.

Five angles, from strongest down:
1. **me.md as an employee-owned Permissioned Twin.** It is their own category, made portable: the person carries it between services instead of one platform holding it. Stanford's Human Context Protocol work on user-governed, portable preference context is pushing the same way.
2. **A crosswalk to the four Wethos Style scales, labelled as hypotheses.** Big Five answers and scenario choices are mapped onto Ideas, Relational, Action and Order, each with its evidence IDs. This makes me.md an on-ramp into Wethos without claiming to measure their construct. It uses the same honesty rule as their Observed Twins.
3. **Twin governance built to security standards.** A personality file with verbatim writing samples is a spear-phishing kit. We show:
   - a threat model
   - share scopes (the minimum-necessary version drops verbatim writing)
   - an integrity digest
   - expiry and revocation fields
   - injection-safe rendering

   This speaks directly to a security-founder CEO and their Human Cyber Range.
4. **Measuring human context.** The judge reports how much each model improves with the profile compared with no profile. That number is their core thesis: human context changes the outcome.
5. **Honest benchmarking of their twin.** The judge scores the Wethos responses without knowing their source and reports where Wethos beats us. Their twin may draw on more information than the kit gives us, and we say so.

## Integration plan

| Part | Status |
|---|---|
| Judge ingests the four organizer-provided Wethos responses | Required; the comparison loader is format-agnostic |
| `me.json` sidecar: machine-readable claims, evidence IDs, share scope, expiry, digest, and the Wethos Style crosswalk | To build |
| WethosAI API adapter | Behind a seam; no public API documentation was found, so it waits on whatever the tutorial provided |

Sources: [wethos.ai](https://wethos.ai/), [the science behind WethosAI](https://kb.wethos.ai/the-science-behind-wethosai),
[WethosAI Twins launch profile (secondary)](https://kingy.ai/?p=929137),
[Stanford Human Context Protocol](https://digitaleconomy.stanford.edu/project/loyal-agents/hcp-human-context-protocol).
