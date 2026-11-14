# lumin8r: the product

**One line:** your working style, in a file you own. Take a 30-minute assessment, get a plain-language file you can
check claim by claim, and share a version of it with a coach, a team lead or your own AI, then take it back.

## Who it is for
| Person | Job to be done | What they get |
|---|---|---|
| **The employee (the owner)** | "Help people and AI tools understand how I say I prefer to work, without handing over a test score" | a file they read, correct and question; share links they control; an understudy to rehearse with |
| **The recipient (coach, team lead, teammate)** | "Know how to work with this person, quickly, without guessing or labelling" | a "How to work with ..." guide built from the person's own answers, with what it can and cannot be used for |
| **The person's AI assistant (Claude, ChatGPT)** | answer and draft in the person's voice and decision style | a portable me.md that loads unchanged in any assistant |
| **The operator (coaching platform or HR tooling admin)** | run it responsibly | `/admin`: consent ledger, data on the box, health, settings |

## The loop
1. **Assess:** take the assessment (`/assessment`). Answers are kept in your browser; they pass through our server, without being saved, to build your file.
2. **Your file:** see your file (`/app`). Every claim shows the answers behind it. Correct an answer and the file
   rebuilds. Question any claim.
3. **Rehearse (optional):** ask your understudy how you would handle a situation. Mark each answer "sounds like me" or
   "not me".
4. **Share:** create a share link for one person and one purpose, as the coaching version or the full version,
   with an expiry date.
5. **Recipient:** opens the link and gets the "How to work with ..." guide, with the use limits on top.
6. **Revoke:** turn the link off at any time. The server copy is deleted and the link stops working.
7. **Use with your AI:** copy me.md into any assistant, with one-line loading instructions.

## Privacy model (the product's spine)
- **Building the file uses no AI and no server storage.** The browser sends the answers to a stateless convert call on our server, which returns the file and saves nothing.
- **Your file lives on your device** only if you choose "Remember on this device". Otherwise it is gone when you
  close the tab.
- **Share links are end-to-end encrypted.**
  - Your browser encrypts the shared version (AES-GCM, WebCrypto) with a fresh key.
  - The server stores only the ciphertext, plus the purpose, version and expiry you chose.
  - The key travels in the link's `#fragment`, which browsers never send to servers. So the server cannot read
    what you shared.
  - Revoking deletes the ciphertext. Expired shares are deleted automatically.
- **The consent ledger records events, never content:** consent, share created, share revoked, withdrawal.
- **Use limit, printed everywhere:** voluntary coaching, reflection and communication support. Never for hiring,
  promotion, performance ratings, pay or discipline. The file itself carries a refusal rule for any AI asked to
  do that.
- **Honest limits:** a file someone already copied cannot be recalled; revoking stops the link, not copies.

## Product surfaces (information architecture)
| Route | Name in the UI | Audience | Notes |
|---|---|---|---|
| `/` | Home | everyone | value, how it works, privacy model, for coaches and teams, FAQ |
| `/kit` | Take the assessment | owner | consent, 60 prompts, timer; on finish, opens Your file with the answers loaded |
| `/app` | Your file | owner | consent, review, question, correct, rehearse, share, use with your AI, withdraw |
| `/s/<id>#<key>` | Shared profile | recipient | decrypts in the browser; the "How to work with ..." guide; who shared it, purpose, expiry; use limits |
| `/privacy` | Privacy | everyone | what is processed, by whom, where, how long, how to withdraw |
| `/responsible-use` | Responsible use | everyone | allowed and prohibited uses, the refusal rule, limits |
| `/admin` | Admin | operator | behind the operator code; not in the public navigation |
| `/workbench` | (not product) | the hackathon team | evaluation tooling; off unless `LUMIN8R_WORKBENCH=1`; never linked from the product |

Public navigation: Home, Take the assessment, Your file. Footer: Privacy, Responsible use, "player two · claude
is an AI".

## Share API (contract)
- `POST /api/shares {ciphertext, iv, version: "coaching"|"full", purpose, recipient_label, expires_at, consent_token}`
  - Needs a valid consent token for `build_profile`.
  - Limits: ciphertext at most 200 KB; purpose and recipient label at most 200 characters; expiry at most 90 days
    out.
  - Returns 201 `{id, manage_token, url_path: "/s/<id>"}`.
  - Writes a ledger event `share_created {person_id, share_id, version, purpose, recipient_label, expires_at}`.
  - The server stores the SHA-256 of `manage_token`, never the token itself.
- `GET /api/shares/<id>`: returns 200 `{ciphertext, iv, version, purpose, recipient_label, created_at, expires_at}`
  while live. Revoked or expired: 410 `{error}`. Unknown: 404.
- `DELETE /api/shares/<id>` with header `X-Manage-Token`: deletes the ciphertext and writes a ledger event
  `share_revoked`. Wrong token: 403.
- Expired shares are deleted on read and on a sweep at startup and hourly.
- IDs are 22-character URL-safe random strings; manage tokens are 32 bytes.

## What is deliberately not in the product
Hackathon evaluation tooling: freeze day, the paste station, the experiment, rating sheets, final submission.
It lives in `/workbench`, off by default.

## Design direction (replaces the spawn design system entirely)
The product no longer uses the spawn design system: no blue void, no lime or royal, no Silkscreen, no "player one"
or "player two" game language in the interface. It gets its own identity: **corporate, and psychologically easing.**

People take this assessment about themselves, often at work, sometimes because a manager suggested it. The design's
job is to lower that tension. It should be calm, warm, unhurried and respectful, and never clinical, surveilling or
judgmental. Corporate without being stodgy: the calm confidence of a well-made professional tool, with moments of
delight.

What psychologically easing means here:
- **Soft, low-saturation palette** with warm neutrals and one gentle, trustworthy accent (a calm teal or sage, or a
  soft indigo). No red except for destructive actions; errors are worded kindly.
- **Rounded, breathable layouts:** generous line height, a short reading width, one task per screen, progress that
  feels achievable ("about 4 minutes left").
- **Language that reassures:**
  - "There are no right answers"
  - "You can change this later"
  - "Skip anything"
  - "You decide who sees it"
- **Motion slow and smooth** (200-400ms, eased), never flashy. Reduced motion respected.
- **Claude is named plainly** as "your understudy (Claude, an AI)": it learns your part from your answers, rehearses with you, and never takes your place. Never "twin", "doppelganger", "clone" or "player two".
- **Light first, with a crafted dark mode.** One confident accent; a quiet neutral palette biased toward the
  accent; no neon, no pixel fonts, no game styling. Avoid the cliché looks: cream with terracotta, black with acid
  green, purple-to-blue gradient heroes, emoji markers.
- **Typography with character:** a refined display face used sparingly, a highly legible text face, and a mono face
  for answer IDs only. One type scale, kept to.
- **Layout:** generous whitespace, real hierarchy, product-grade components (buttons, fields, cards, chips, tabs,
  toasts, dialogs), one primary action per screen.
- **Delight, used with restraint:**
  - **A kinetic hero on the main page.** A living illustration of the product idea: answers flowing into claims,
    each claim drawing a fine line back to the answers behind it, and a share link locking and unlocking. Canvas or
    SVG, 60 fps, reduced-motion friendly, legible at rest, no autoplay video.
  - **In the app:** the file rebuilds with a subtle settle when an answer changes; selecting a claim draws a
    connector to its evidence; creating a share link plays a short lock animation.
- **Accessibility:** WCAG 2.1 AA, visible focus, keyboard everywhere, and every animation off under
  `prefers-reduced-motion`.
- **The main page is a real product landing:**
  1. kinetic hero with the value proposition and one primary call to action, "Take the assessment"
  2. how it works, in three steps
  3. the privacy model, explained simply
  4. for coaches and teams
  5. what it is not for
  6. FAQ
  7. footer
