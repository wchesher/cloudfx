# lumin8r UX review

Walked on 2026-11-14 against a local server with the fictional DEMO01, at 1440x900 and 390x844, covering every page
and state: empty, loading, error, success. Before screenshots: `/tmp/claude-0/ux-before/`. Ranking: **P0** broken
or confusing, **P1** friction, **P2** polish.

## Across the whole journey

The brand holds: blue void, lime for the person, royal for player two, Bricolage, Silkscreen labels, the spawn-in.
What breaks the flow is the shell around it. Each page invents its own top bar, so the two halves of the product
(employee: home, kit, app; team: hub, paste) never point at each other.

- **P0 No site navigation.** The wordmark is the only way between pages. From the kit you cannot reach your file;
  from the app you cannot reach the kit that makes the file it asks for; the hub and the paste station have no way
  to the employee side.
- **P0 The paste station shows a fake progress line.** Its top bar says "1 consent, 2 answers, 3 review, 4 share,
  5 test" and every link goes to `/`. It tells a teammate they are on step 5 of the employee app.
- **P0 The paste station's signed-out page is unstyled.** A bare white page in Times, the only off-brand screen.
- **P1 The station line reads as tabs, not a path.** Numbers in a muted pixel font, no connection between them,
  "done" shown only as a slightly greener digit.
- **P1 The background tiles every 900px.** The two radial washes are sized to the body and repeat, so a long page
  (final, docs, review) shows a hard seam as it scrolls.
- **P1 File pickers are keyboard-dead.** "Choose an answer file" and every hub "Pick files" are labels for
  `display: none` inputs, which take no focus.
- **P1 Disabled primary actions never say why.** A dimmed lime button with no reason (consent, upload, download
  submission; the hub hid it in a `title`).
- **P2 No spacing scale.** Gaps of 6, 8, 10, 12, 14, 16 and 18px sit side by side; the rhythm shifts from page to page.

## Page by page

**Home.** Clear claim and one lime action. *P1* The kit, which comes first in the real order, is a small text link,
and the team door is a bare "Team" button that does not say what the hub is for. *P2* An eyebrow repeating the
wordmark.

**Kit.** The strongest page: one task per screen, saved as you go, a real progress bar. *P0* If you send to the hub
without signing in, the warning breaks into three stacked lines ("Sign in at" / "/team" / "first...") because
`.result` is a grid. *P1* "step 3 of 11" is the only sense of place. The live-region step label also holds the
timer, so a screen reader announces every second.

**App (employee bench).** The three-column bench is right. *P1* "Withdraw consent" sits in red right next to the
primary action; on a phone the action bar grows to three rows and covers the share form. *P1* Review textareas are
64px high and cut off the person's own sentences. *P1* No loading feedback for consent, the example or rebuilds; a
failed load turns text red inline. *P1* After withdrawing, the whole body is replaced, top bar included: a dead end.
*P2* The AI label is shown twice above the file; claim chips are lime outlines on every line, which is noisy; the
`[S01, S05]` citations have the same weight as the prose. When player two is off, the rail still shows an empty,
disabled select.

**Team hub.** The station model and the one lime action per station work. *P0* The kits table pushes the page to
405px wide at 390 (a grid track sized to its content). *P1* Final shows three timeline cards and then three panels
saying the same thing, with no done/not done status: at 4:30 nobody can tell at a glance what is left. *P1* Docs
renders numbered lists as "1. 1. 1." and flattens nested bullets into run-on paragraphs (strategy, pitch).
*P1* Errors appear as a "not done" pixel chip ("not done: that code is not right"), which reads as a status, not an
error. *P2* Empty states say "No results yet" without saying what will appear or how long scoring takes.

**Paste station.** Good flow: a numbered recipe, copy buttons, live scoring. *P1* The copy buttons are royal,
which the system reserves for player two (LLM B is GPT). *P1* "Not saved" errors are pixel chips; a failed queue
load leaves a heading and no way to retry; the empty state explains `private/people/<CODE>` and env vars to a
researcher. *P2* On a phone the queue (40 rows) comes before the run you are pasting.

## Accessibility (WCAG 2.1 AA)

Text tokens all clear 4.5:1 (faint #7f8bab is the floor at 4.76 on panel-2). Focus rings exist. Gaps: keyboard-dead
file inputs (2.1.1), a timer inside a live region (4.1.3), disabled buttons without a stated reason (3.3.2), no
skip link past a two-row header (2.4.1), no `aria-invalid` on errored fields, smooth scroll ignoring reduced motion.

---

## What changed

All five pages and `mefile.css`. One Python edit, to fix a page-serving defect: the `/paste` signed-out page in
`team.py` (`_PASTE_SIGN_IN`) now links the stylesheet and offers "Open the team hub". The 401 status and gating
are unchanged. After screenshots: `/tmp/claude-0/ux-after/`.

- **One top bar everywhere.** Row one: the wordmark, then site navigation (Take the kit, Your file | Team hub),
  with the current page marked; short labels on phones. Row two: where you are. The app and hub show their station
  line, the kit shows its sections plus the step and timer, the paste station shows a breadcrumb (Team hub / 2 run /
  Paste station) with the model switch. The fake paste stations are gone. Skip link on every page.
- **The station line is a path.** Numbered nodes joined by a rail; done nodes fill lime and the rail behind them
  turns lime; the current node is outlined. Docs sits apart, unnumbered.
- **One lime action, always bottom right, with its reason.** Disabled primaries now carry a hint in the bar
  ("Type a person code and tick the first box", "Put the inputs in first (step 1)"). Withdraw moved to a quiet foot of
  the station column with an inline confirm; me.json and corrected answers moved into a share panel. On phones the
  bar is one full-width row.
- **Spacing scale** (`--s-1` to `--s-8`), a 68ch reading measure, and panels and cards that never let content
  widen the page. The background wash is fixed: no seam.
- **Final is a checklist.** A frozen notice ("From 4:30 nothing changes"), then four rows (4:30 inputs, 5:00 eight
  responses, 5:30 twenty evaluations, download), each with live status (to do / 3 of 8 / done) and the next row
  highlighted. Each step panel repeats its time and number.
- **States.** Every async action has a busy label (Recording consent..., Loading the example..., Rebuilding your
  file..., Uploading..., Scoring and judging..., Saving..., Sending...). Errors are inline notices in plain words that
  say what to do next. Empty states say what will appear and the next step. The paste queue error has a Try again.
- **The file.** Brackets stay put while it scrolls; the duplicate AI label moved below; claim chips are quiet until
  hovered or active; citations are dimmed; the metadata table is lighter; numbered lists render. Review textareas
  grow to fit. Withdrawal keeps the top bar and offers a way home.
- **Fixes.** Kit sign-in warning on one line; timer out of the live region; file inputs focusable with a visible ring;
  `aria-invalid` on errored fields; docs lists nest and count properly; kits table no longer overflows; reduced motion
  respected for claim scrolling; royal removed from the paste copy buttons.

Verified: 83 tests pass, 30 states re-walked with no horizontal scroll at 390px and no script errors. The only
console lines are the browser logging three deliberate 401s (signed-out `/paste`, the hub's signed-out
`/api/team/me` check, and the kit's send before sign-in).

**Left on purpose.** The 401s stay, because they are server behaviour. The me.md text is unchanged (the converter is
deterministic and owns it), as is the blind rating sheet generated by `team.py`. Team station names are unchanged.
On phones the hub's station line wraps to two rows instead of hiding labels.
