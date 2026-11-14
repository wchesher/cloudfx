# Voice intake: research and build notes (optional extra credit, Kit Section 11)

Researched 2026-11-14. Vendor facts come from vendor docs; check them again before quoting.

## Design rules
- **Text only.** The transcript of the employee's own turns is the only thing kept. Nothing about
  tone, emotion or fluency is analyzed. EU AI Act Art. 5(1)(f) bans inferring workers' emotions
  from biometric data, voice included; the Commission's guidelines (C(2025) 5052) leave text
  outside the ban.
- **No voice clone of the person, ever.** Your understudy answers in text, or in a stock synthetic voice.
- **Disclosure and consent come first.** The ElevenLabs Agents terms (section 3.5) require telling
  users, before they start, that they are talking to an AI, that ElevenLabs and its LLM providers
  process the conversation, and that it is recorded; consent proof is kept for 5 years. California
  Penal Code 632 requires every party's consent to record a confidential conversation.
- **Turn audio off and delete it.** Set `platform_settings.privacy.record_voice=false` on the agent
  and delete the conversation (`DELETE /v1/convai/conversations/{id}`) once the transcript is
  saved. This keeps us clear of voiceprint laws (Illinois BIPA, Texas CUBI, Washington's My Health
  My Data Act).
- **The employee reviews and edits the transcript before use.** Speech-to-text is less accurate
  for some accents and dialects (Koenecke et al. 2020, PNAS: word error rate 0.35 vs 0.19), and
  Whisper sometimes invents phrases (Koenecke et al., FAccT 2024).

## ElevenLabs Agents (the path we built)
- **Create the agent:** in the dashboard (elevenlabs.io/app/agents) or with
  `POST /v1/convai/agents/create`.
  - `conversation_config.agent.prompt.prompt` = `voice.AGENT_SYSTEM_PROMPT`
  - `first_message` = the disclosure
  - `conversation.max_duration_seconds` about 660
  - `turn.turn_timeout` raised from the default 7 seconds
- **Lock it down:** `platform_settings.auth.enable_auth=true`, and record_voice off.
- **Session flow:** the server calls `GET /v1/convai/conversation/get-signed-url?agent_id=...` and
  the browser runs `ElevenLabsClient.Conversation.startSession({signedUrl})`. Load the client from
  `https://cdn.jsdelivr.net/npm/@elevenlabs/client@1.32.0/dist/lib.iife.js`. The page must be on
  localhost or https for microphone access.
- **Results:** poll `GET /v1/convai/conversations/{id}` until `status` is `done`. In `transcript[]`,
  each turn has `role` (user or agent), `message` and `time_in_call_secs`.
- **Cost:** the Free plan is about 15 minutes, so one interview. Creator ($11 for the first month)
  gives 275 minutes. The Free plan is disabled behind a VPN.
- **Env vars:** `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`.

## Plaud (fallback for an in-person interview)
- Use the **Plaud CLI** against the teammate's own account:
  - `npm i -g @plaud-ai/cli`, then `plaud login` (OAuth in a browser)
  - `plaud recent` to find the recording
  - `plaud transcript <id> -o t.txt`, which gives lines shaped `[mm:ss - mm:ss] Speaker N: text`
- The **developer APIs** (Embedded SDK, Transcription API) need partner approval and support only
  the Note Pro and NotePin S. Do not plan on them today.
- **Manual export:** the app exports TXT, SRT, DOCX or PDF, with speaker labels optional. SRT is
  the easiest to parse.
- **Identifying the employee:** rename speakers in the app, or let the employee pick their own
  lines in our UI.

## Scientific basis
- **Park et al. 2024**, "Generative Agent Simulations of 1,000 People" (arXiv:2411.10109).
  - Method: 2-hour voice interviews run by an AI interviewer.
  - Agents built from the interviews matched General Social Survey answers at 0.85, normalized
    against how consistently people repeat their own answers two weeks later. Demographic agents
    scored 0.71 and persona-paragraph agents 0.70. Big Five correlation was 0.80.
  - With 80% of the transcript removed it still scored 0.79, which supports a short interview.
  - Bullet-point summaries of the interviews held up at 0.83, so content carries the signal.
  - Gaps between demographic groups were smaller than for the other agent types.
- **Peters, Cerf & Matz 2024** (arXiv:2405.13052): a chatbot told to draw out personality reached
  r = .44 with self-reported traits, against .12 for a default assistant. This is the case for a
  purpose-built interviewer.
- **Behavioral ("tell me about a time") questions** outperform hypothetical ones: Taylor & Small
  2002 (check the exact figures before quoting). The method goes back to the critical incident
  technique (Flanagan 1954).
- **Expect modest results.** Zero-shot trait inference from free text typically lands around
  r = 0.2-0.45. A null result still earns the bonus.

## Comparison protocol (how the bonus is scored)
1. A consenting teammate does both the kit and the voice interview, and we time each.
2. Hold out the teammate's kit test answers (S02, S04, S06, W02, W04). Neither intake sees them.
3. Build two profiles: kit only, and kit plus voice evidence. Run both on the held-out questions
   and on both models.
4. Report choice accuracy, the judge's resemblance scores, minutes and effort for each, and the
   limitations.
