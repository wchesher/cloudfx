/* Copyright (c) 2026 William Chesher. MIT License, see LICENSE. */
/* app.js - Your file (/app): consent, the file with its claims and evidence, question and correct, rehearse with your
   AI twin, end-to-end encrypted share links, use with your AI, and settings (downloads, this device, withdraw).
   The build is a stateless /api/convert call; the person's progress is saved on the server through context.js (no browser
   storage), and a share is ciphertext encrypted here with a key that only ever travels in the link's #fragment. */
(() => {
"use strict";

const ORDER = ["agree", "file", "rehearse", "share", "ai"];
const DOMAINS = {extraversion: "Extraversion", agreeableness: "Agreeableness", conscientiousness: "Conscientiousness", emotional_stability: "Emotional Stability", intellect: "Intellect/Imagination"};
const LABELS = {1: "1 · very inaccurate", 2: "2 · moderately inaccurate", 3: "3 · neither", 4: "4 · moderately accurate", 5: "5 · very accurate"};
const SCOPE_NAMES = {coaching: "Limited coaching profile", full: "Full profile"};
const SCOPE_SHORT = {coaching: "Coaching version", full: "Full version"};
const KIND_NAMES = {reported: "how you handle situations", observed_style: "how you write", measured: "self-described trait", limit: "a stated limit"};
// storage keys: the kit hands answers over in HANDOFF; REMEMBER is the person's "Remember on this device" choice
const HANDOFF = "lumin8r-answers-v1", REMEMBER = "lumin8r-remember", CONSENT = "lumin8r-consent-v1", SHARES = "lumin8r-shares-v1", KIT = "lumin8r-kit-v1";
// the reviewed interview transcript /interview leaves in this tab (intake.parse_transcript's shape); sent as `voice` on every build
const VOICE = "lumin8r-voice-v1";
const VOICE_SOURCES = {elevenlabs: "talked with the AI interviewer", plaud: "Plaud recording", typed: "typed"};

const state = {token: "", pid: "", purposes: [], consented: false, receiptAt: "", answers: null, result: null, resultKey: "", scope: "coaching", withhold: [], reviewed: false,
  activeClaim: null, notes: [], claimQuestions: {}, questioning: null, questionDraft: "", from: "",
  twin: {enabled: false, practice: [], reason: "", picked: null}, voiceEnabled: false, scopes: {}, station: "agree", remember: false, built: false, voiceFile: null};

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const calm = () => !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
const narrow = () => !!(window.matchMedia && matchMedia("(max-width: 900px)").matches);

/* ---------- storage: saved progress on the server (context.js); nothing is kept in the browser ---------- */
const store = {
  get(area, key) { try { const v = CTX[area].getItem(key); return v ? JSON.parse(v) : null; } catch (_) { return null; } },
  set(area, key, value) { try { CTX[area].setItem(key, JSON.stringify(value)); return true; } catch (_) { return false; } },
  del(area, key) { try { CTX[area].removeItem(key); } catch (_) {} },
};
function rememberOn() { return true; }  // progress is always saved on the server; the old per-device choice is gone
function persist() {
  if (!state.answers) return;
  const file = {answers: state.answers, person_id: state.pid || state.answers.person_id || "", from: state.from || "app", claim_questions: state.claimQuestions, twin_reactions: state.notes, at: new Date().toISOString()};
  store.set("sessionStorage", HANDOFF, file);
  if (state.remember) store.set("localStorage", HANDOFF, file);
}
function persistConsent() {
  const c = state.consented ? {pid: state.pid, token: state.token, purposes: state.purposes, at: state.receiptAt} : null;
  if (c) store.set("sessionStorage", CONSENT, c); else store.del("sessionStorage", CONSENT);
  if (c && state.remember) store.set("localStorage", CONSENT, c); else store.del("localStorage", CONSENT);
}

/* ---------- toasts ---------- */
function toast(text) {
  const t = document.createElement("div"); t.className = "toast"; t.textContent = text;
  $("#toasts").append(t);
  setTimeout(() => { t.classList.add("out"); setTimeout(() => t.remove(), calm() ? 0 : 320); }, 3600);
}

/* ---------- the server ---------- */
async function post(url, body, extraHeaders) {
  const headers = Object.assign({"Content-Type": "application/json"}, extraHeaders || {});
  if (state.token) headers["X-Consent-Token"] = state.token;
  let r;
  try { r = await fetch(url, {method: "POST", headers, body: JSON.stringify(body)}); }
  catch (_) { const err = new Error("we could not reach the server; check your connection"); err.status = 0; throw err; }
  let j = {}; try { j = await r.json(); } catch (_) {}
  if (!r.ok) {
    const err = new Error(j.error || ("the server answered " + r.status)); err.status = r.status; err.purpose = j.purpose;
    err.retryAfter = Number(r.headers.get("Retry-After")) || 0;
    if (r.status === 403 && j.error === "consent required" && j.purpose === "build_profile") consentLost();
    throw err;
  }
  return j;
}
function consentLost() {
  state.consented = false; state.token = ""; persistConsent();
  $("#receipt").textContent = "Your agreement needs renewing (the server may have restarted). Agree again to keep going; your answers are still here.";
  go("agree");
}

/* ---------- steps ---------- */
function allowed(st) {
  if (st === "agree") return true;
  if (st === "file") return state.consented;
  return state.consented && !!state.result;
}
function go(st, focus) {
  if (!ORDER.includes(st)) st = "agree";
  if (!allowed(st)) st = [...ORDER].reverse().find(allowed);
  const changed = state.station !== st;
  state.station = st;
  if (location.hash !== "#" + st) history.replaceState(null, "", "#" + st);
  const bring = st === "file" && !state.answers;
  $("#st-agree").classList.toggle("hidden", st !== "agree");
  $("#st-bring").classList.toggle("hidden", !bring);
  $("#workspace").classList.toggle("hidden", st === "agree" || bring);
  $("#workspace").classList.toggle("mode-file", st === "file");
  $("#workspace").classList.toggle("mode-side", st !== "file");
  for (const s of ORDER.slice(1)) $("#st-" + s).classList.toggle("hidden", s !== st);
  document.querySelectorAll("#steps li").forEach((li) => {
    const s = li.dataset.st, b = li.querySelector("button"), i = ORDER.indexOf(s);
    b.disabled = !allowed(s);
    li.classList.toggle("done", i < ORDER.indexOf(st) && allowed(s) || (s === "agree" && state.consented && st !== "agree"));
    if (s === st) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
  });
  if (st === "file" && (changed || !$("#answers").childElementCount)) { renderAnswers(); renderQuestioned(); }
  if (changed && state.result) requestAnimationFrame(() => drawConnector(false));
  if (st === "share") { renderShareGate(); renderShares(); }
  if (st === "ai") renderAiStep();
  if (st === "rehearse") updateTwin();
  renderActions();
  drawConnector(false);
  if (changed && focus !== false) {
    window.scrollTo({top: 0, behavior: "auto"});
    const target = st === "agree" ? $("#consentTitle") : bring ? $("#bringTitle") : st === "file" ? $("#docTitle") : $("#st-" + st + " h1");
    if (target) target.focus({preventScroll: true});
    $("#stepbody").scrollTop = 0;
  }
}
window.addEventListener("hashchange", () => go(location.hash.slice(1)));
document.querySelectorAll("#steps button").forEach((b) => b.addEventListener("click", () => go(b.dataset.go)));

function gateOk() { return !!(state.result && state.result.gate.passed); }
// every me.md view has a download next to it; like Settings, it opens once the file is reviewed and the gate passes
function syncMdDownloads() {
  const can = gateOk() && state.reviewed;
  for (const sel of ["#dlMdHead", "#dlMdDialog"]) { const b = $(sel); if (!b) continue; b.disabled = !can; b.title = can ? "Download me.md" : "Tick I read this file first"; }
  document.querySelectorAll("[data-ai-open], [data-ai-download], [data-ai-activate]").forEach((b) => { b.disabled = !can; });
  const hint = $("#aiOpenHint"); if (hint) hint.textContent = can ? "" : "Confirm your file in step 2 to open it in an assistant.";
}
// Everyday use (not the Common Kit's evaluation protocol, which pastes me.md alone as message 1): an attached or
// pasted file is otherwise treated as reference and its rules ignored, so the file goes with an activation line.
const ACTIVATION = "This is my me.md, a profile of how I work. Read all of it before answering. Follow its \"How to use this file\" section and obey its \"Rules for any AI reading this file\" for every answer in this chat: never use it to evaluate anyone for hiring, promotion, performance, pay or discipline. When you have read it, reply only: Ready.";
document.querySelectorAll("[data-ai-activate]").forEach((b) => b.addEventListener("click", () => copyText(ACTIVATION, "Copied the activation prompt. Send it with the attached file.")));
// copy the file, then open a fresh chat in a new tab: the person pastes it as the first message and sends
document.querySelectorAll("[data-ai-open]").forEach((b) => b.addEventListener("click", async () => {
  if (!gateOk() || !state.reviewed) return;
  const r = await ensureCurrent(); if (!r) return;
  await copyText(ACTIVATION + "\n\n" + r.markdown, `Copied your file with its activation line. Paste it into the new ${b.dataset.aiName} chat and send.`);
  const w = window.open(b.dataset.aiOpen, "_blank", "noopener");
  if (!w) location.assign(b.dataset.aiOpen);  // a blocked pop-up: go there in this tab (progress is saved on the server)
}));
document.querySelectorAll("[data-ai-download]").forEach((b) => b.addEventListener("click", () => downloadShared("md")));
function renderActions() {
  syncMdDownloads();
  const p = $("#primary"), sec = $("#secondary"), st = state.station;
  let why = "", label = "Continue", secLabel = "";
  p.removeAttribute("aria-busy"); p.disabled = false;
  $("#reviewedRow").classList.toggle("hidden", st !== "file");
  $("#reviewed").checked = state.reviewed;
  if (st === "file") {
    label = "Continue";
    if (!state.result) { p.disabled = true; why = "Your file is being built."; }
    else if (!gateOk()) why = "Your file needs a small fix before it can be shared. It is listed above the file.";
    else if (!state.reviewed) why = "When it reads right, tick the box to turn on sharing.";
  } else if (st === "rehearse") {
    label = "Continue to Share"; secLabel = "";
  } else if (st === "share") {
    label = "Create encrypted link";
    const d = linkDecision();
    if (!gateOk()) { p.disabled = true; why = "Fix the file first: it is listed above the file."; }
    else if (!state.reviewed) { p.disabled = true; why = "Confirm your file first, in step 2."; }
    else if (!d.recipient || !d.purpose) { p.disabled = true; why = "Say who it is for and why."; }
    secLabel = "Next: use with your AI";
  } else if (st === "ai") {
    label = "Copy me.md";
    if (!gateOk() || !state.reviewed) { p.disabled = true; why = !gateOk() ? "Fix the file first: it is listed above the file." : "Confirm your file first, in step 2."; }
  }
  p.textContent = label;
  $("#primaryHint").textContent = why;
  sec.classList.toggle("hidden", !secLabel); sec.textContent = secLabel;
  renderSettings();
}
$("#primary").addEventListener("click", () => {
  const st = state.station;
  if (st === "file") return go("rehearse");
  if (st === "rehearse") return go("share");
  if (st === "share") return createShare();
  if (st === "ai") return copyFile();
});
$("#secondary").addEventListener("click", () => { if (state.station === "share") go("ai"); });
$("#reviewed").addEventListener("change", (e) => { state.reviewed = e.target.checked; renderActions(); if (state.reviewed) toast("Sharing is on. You can still change anything."); });

/* ---------- 1 agree ---------- */
function consentReady() { return $("#pid").value.trim().length > 0 && $("#p-build").checked; }
function agreeHint() {
  const ok = consentReady();
  $("#agreeBtn").disabled = !ok;
  $("#agreeHint").textContent = ok ? "" : $("#pid").value.trim() ? "Tick 1, Participation, to continue." : "Type a person code and tick 1, Participation, to continue.";
}
$("#pid").addEventListener("input", agreeHint);
document.querySelectorAll(".purpose").forEach((c) => c.addEventListener("change", agreeHint));
$("#agreeBtn").addEventListener("click", agree);
async function agree() {
  const pid = $("#pid").value.trim();
  const b = $("#agreeBtn"); b.disabled = true; b.setAttribute("aria-busy", "true"); b.textContent = "Recording your agreement...";
  const purposes = [...document.querySelectorAll(".purpose:checked")].map((x) => x.value);
  const ai = []; if (purposes.includes("ai_processing")) ai.push("Anthropic Claude Opus 5.5 (Rehearse with your understudy)"); if (purposes.includes("voice_interview")) ai.push("ElevenLabs (voice interview)");
  const priorToken = state.token;
  try {
    const r = await post("/api/consent", {person_id: pid, purposes, ai_services: ai, share_with: []});
    state.pid = pid; state.purposes = purposes; state.consented = true; state.token = r.consent_token || priorToken || ""; state.receiptAt = r.receipt && r.receipt.at || new Date().toISOString();
    $("#receipt").textContent = "Agreement recorded " + state.receiptAt + ".";
    persistConsent();
    $("#voiceBox").classList.toggle("hidden", !(state.voiceEnabled && purposes.includes("voice_interview")));
    updateTwin();
    if (state.answers) { go("file"); await regen(); } else go("file");
  } catch (err) { $("#receipt").textContent = "Your agreement was not recorded: " + err.message + ". Please try again."; }
  finally { b.removeAttribute("aria-busy"); b.textContent = "Agree and continue"; agreeHint(); }
}

/* ---------- bring answers ---------- */
$("#example").addEventListener("click", async () => {
  const b = $("#example"), label = b.textContent; b.disabled = true; b.setAttribute("aria-busy", "true"); b.textContent = "Loading the example...";
  try { const r = await fetch("/api/example"); if (!r.ok) throw new Error("the server answered " + r.status); setAnswers(await r.json(), "example"); }
  catch (e) { loadedNote("The example did not load (" + e.message + "). Try again, or choose your own answer file.", true); }
  finally { b.disabled = false; b.removeAttribute("aria-busy"); b.textContent = label; }
});
$("#fileInput").addEventListener("change", async (e) => {
  const f = e.target.files[0]; if (!f) return;
  try { setAnswers(JSON.parse(await f.text()), "file"); } catch (err) { loadedNote("That file is not one lumin8r can read. Choose the answer file you downloaded from the assessment.", true); }
  e.target.value = "";
});
function loadedNote(text, bad) { const c = $("#loaded"); c.className = "notice " + (bad ? "bad" : "ok"); c.textContent = text; }
function normalize(a) { a.items = a.items || []; a.scenarios = a.scenarios || []; a.writing = a.writing || []; a.skipped = a.skipped || []; return a; }
function setAnswers(a, from) {
  state.answers = normalize(a); state.from = from || "app"; state.reviewed = false; state.result = null; state.built = false;
  persist();
  go("file");
  regen();
}

/* ---------- build: a stateless call, the file settles when it changes ---------- */
let timer = null, building = 0;
function regenSoon() { clearTimeout(timer); $("#buildStatus").textContent = "Rebuilding your file..."; timer = setTimeout(regen, 400); }
async function regen() {
  if (!state.answers || !state.consented) return null;
  const mine = ++building;
  const key = state.scope + "|" + state.withhold.join(",");
  $("#buildStatus").textContent = state.result ? "Rebuilding your file..." : "Building your file from your answers...";
  try {
    const body = {answers: state.answers, scope: state.scope, withhold: state.withhold};
    const disputed = disputesNow();
    if (Object.keys(disputed).length) body.disputed = disputed; /* resent on every build, so a withhold change keeps them */
    renderVoiceLine();
    if (state.voiceFile && !voiceMismatch()) body.voice = state.voiceFile;
    const r = await post("/api/convert", body);
    if (mine !== building) return null;
    state.result = r; state.resultKey = key;
    renderFile(); renderGate(); updateTwin(); go(state.station, false);
    $("#buildStatus").textContent = "";
    return r;
  } catch (err) {
    if (mine !== building) return null;
    $("#buildStatus").textContent = "";
    if (err.status === 403 && err.purpose === "build_profile") return null;
    $("#gate").innerHTML = `<div class="notice bad" role="alert"><b>We could not build your file just now.</b> ${esc(err.message)}. Your answers are safe on this page; change one or try again in a moment.</div>`;
    return null;
  }
}
async function ensureCurrent() {
  const key = state.scope + "|" + state.withhold.join(",");
  clearTimeout(timer);
  if (!state.result || state.resultKey !== key || $("#buildStatus").textContent) return regen();
  return state.result;
}

/* ---------- the file: every statement, with the answers behind it ---------- */
function md(src) {
  const lines = src.replace(/<!--[\s\S]*?-->/g, "").split("\n"); let out = "", inTable = false, inList = false, inQuote = false, inOl = false;
  const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[((?:[BSWV]\d\d(?:, )?)+)\]/g, '<span class="cite">[$1]</span>')
    .replace(/\((C\d\d)\)/g, '<button type="button" class="claim" data-c="$1" aria-label="Statement $1: show the answers behind it">$1</button>');
  const close = () => { if (inTable) { out += "</table>"; inTable = false; } if (inList) { out += "</ul>"; inList = false; } if (inOl) { out += "</ol>"; inOl = false; } if (inQuote) { out += "</blockquote>"; inQuote = false; } };
  for (const l of lines) {
    if (/^\|/.test(l)) { if (/^\|[-| :]+\|$/.test(l)) continue; if (!inTable) { close(); out += "<table>"; inTable = true; } out += "<tr>" + l.slice(1, -1).split("|").map((c) => `<td>${inline(c.trim())}</td>`).join("") + "</tr>"; continue; }
    if (/^>/.test(l)) { if (!inQuote) { close(); out += "<blockquote>"; inQuote = true; } else out += "<br>"; out += inline(l.replace(/^>\s?/, "")); continue; }
    if (/^- /.test(l)) { if (!inList) { close(); out += "<ul>"; inList = true; } out += `<li>${inline(l.slice(2))}</li>`; continue; }
    if (/^\d+\. /.test(l)) { if (!inOl) { close(); out += "<ol>"; inOl = true; } out += `<li>${inline(l.replace(/^\d+\. /, ""))}</li>`; continue; }
    close();
    if (/^# /.test(l)) out += `<h1>${inline(l.slice(2))}</h1>`;
    else if (/^## /.test(l)) out += `<h2>${inline(l.slice(3))}</h2>`;
    else if (/^### /.test(l)) out += `<h3>${inline(l.slice(4))}</h3>`;
    else if (l.trim()) out += `<p>${inline(l)}</p>`;
  }
  close(); return out;
}
const GROUPS = [
  {kind: "reported", title: "How you handle situations", note: "From the choices you made in workplace situations"},
  {kind: "observed_style", title: "How you write", note: "Measured from the messages you wrote"},
  {kind: "measured", title: "How you describe yourself", note: "From your 50 self-ratings. A middle score means no clear tendency"},
  {kind: "limit", title: "What this can't tell you", note: "Stated limits; they need no answers behind them"},
];
let pendingRender = false;
function renderFile() {
  const wrap = $("#fileWrap");
  // never rebuild under someone who is typing an answer: wait until they leave the field
  const ae = document.activeElement;
  if (state.built && ae && wrap.contains(ae) && ae.matches("textarea, select, input")) { pendingRender = true; return; }
  pendingRender = false;
  const first = !state.built; state.built = true;
  const claims = state.result.claims || [];
  const person = (state.answers && state.answers.person_id) || state.pid || "you";
  $("#docEyebrow").textContent = "Your file · " + person;
  $("#versionChip").textContent = SCOPE_SHORT[state.scope] || state.scope;
  wrap.replaceChildren();
  const known = GROUPS.map((g) => g.kind);
  const groups = GROUPS.concat(claims.some((c) => !known.includes(c.kind)) ? [{kind: null, title: "Other notes", note: ""}] : []);
  for (const g of groups) {
    const mine = claims.filter((c) => g.kind ? c.kind === g.kind : !known.includes(c.kind));
    if (!mine.length) continue;
    const sect = document.createElement("section"); sect.className = "sect" + (first ? " spawn-in" : " settle"); sect.setAttribute("aria-label", g.title);
    const head = document.createElement("div"); head.className = "sect-head";
    const h = document.createElement("h2"); h.textContent = g.title;
    const note = document.createElement("span"); note.className = "note"; note.textContent = g.note;
    head.append(h, note); sect.append(head);
    for (const c of mine) sect.append(claimRow(c));
    wrap.append(sect);
  }
  renderWethos(first);
  renderDetails();
  if (state.activeClaim) showClaim(state.activeClaim, false); else markQuestioned();
}
$("#fileWrap").addEventListener("focusout", () => { setTimeout(() => { if (pendingRender && state.result && !$("#fileWrap").contains(document.activeElement)) renderFile(); }, 0); });

function claimRow(c) {
  const row = document.createElement("div"); row.className = "crow" + (c.kind === "limit" ? " limit" : ""); row.dataset.c = c.id;
  const t = document.createElement("button"); t.type = "button"; t.className = "ctext"; t.textContent = sentence(c.text);
  t.setAttribute("aria-expanded", "false"); t.setAttribute("aria-label", c.text + (c.evidence.length ? ". Show the answers behind it." : ""));
  t.addEventListener("click", () => showClaim(state.activeClaim === c.id ? null : c.id, true));
  const rail = document.createElement("div"); rail.className = "crail";
  row.append(t, rail);
  compactRail(rail, c);
  return row;
}
// what a person sees instead of an answer code (B13, S01, W03, V02); me.md keeps the codes, the screen does not
const KIND_WORD = {B: ["Statement", "statements"], S: ["Situation", "situations"], W: ["Message", "messages"], V: ["Interview answer", "interview answers"]};
function label(id) { const k = KIND_WORD[String(id)[0]]; return k ? k[0] + " " + Number(String(id).slice(1)) : String(id); }
function railGroups(ids) {
  const groups = [];
  for (const k of ["S", "W", "V", "B"]) {
    const of = ids.filter((id) => id[0] === k); if (!of.length) continue;
    const w = KIND_WORD[k], nums = of.map((id) => Number(id.slice(1)));
    groups.push({ids: of, text: of.length === 1 ? label(of[0]) : of.length <= 3 ? w[1].charAt(0).toUpperCase() + w[1].slice(1) + " " + nums.join(", ") : of.length + " " + w[1]});
  }
  return groups;
}
const sentence = (s) => { const x = String(s || "").trim(); return /[.!?)]$/.test(x) ? x : x + "."; };
function compactRail(rail, c) {
  rail.replaceChildren();
  for (const g of railGroups(c.evidence)) { const b = document.createElement("span"); b.className = "ev-id"; b.dataset.ids = g.ids.join(" "); b.textContent = g.text; b.addEventListener("click", () => showClaim(c.id, true)); rail.append(b); }
}
// what you said, in a few words, for an evidence chip
function evidenceSummary(id) {
  const a = state.answers || {items: [], scenarios: [], writing: []};
  if (id[0] === "B") { const it = a.items.find((x) => x.id === id); return {txt: window.ITEMS[id] || id, val: it ? it.response + " of 5" : "skipped"}; }
  if (id[0] === "S") { const s = a.scenarios.find((x) => x.id === id); return s ? {txt: "Chose " + s.choice + (s.explanation ? " · “" + s.explanation + "”" : ""), val: ""} : {txt: "Situation", val: "skipped"}; }
  if (id[0] === "W") { const w = a.writing.find((x) => x.id === id); return w ? {txt: "“" + w.text + "”", val: words(w.text) + " words"} : {txt: "Message", val: "skipped"}; }
  if (id[0] === "V") { const turn = voiceTurn(id); return turn ? {txt: "“" + turn.text + "”", val: "interview"} : {txt: "From your interview", val: ""}; }
  return {txt: "From your voice interview", val: ""};
}
const words = (s) => String(s || "").trim().split(/\s+/).filter(Boolean).length;
function evChip(id, onOpen) {
  const s = evidenceSummary(id);
  const b = document.createElement("button"); b.type = "button"; b.className = "evchip"; b.dataset.id = id; b.setAttribute("aria-expanded", "false");
  b.innerHTML = `<span class="id">${esc(label(id))}</span><span class="txt">${esc(s.txt)}</span>${s.val ? `<span class="val">${esc(s.val)}</span>` : ""}`;
  b.setAttribute("aria-label", `${label(id)}: ${s.txt}${s.val ? ", " + s.val : ""}. Edit this answer.`);
  b.addEventListener("click", () => onOpen(b, id));
  return b;
}

/* ---------- selecting a statement: it lights up, its answers slide in, a fine line joins them ---------- */
let chipEl = null, openEditor = null;
function showClaim(id, user) {
  if (!state.result) return;
  const fresh = state.activeClaim !== id;
  if (user && state.station !== "file") go("file", false);
  state.activeClaim = id;
  const c = id ? state.result.claims.find((x) => x.id === id) : null;
  document.querySelectorAll("#fileWrap .crow").forEach((row) => {
    const on = !!c && row.dataset.c === id;
    row.classList.toggle("sel", on);
    row.querySelector(".ctext").setAttribute("aria-expanded", String(on));
    const claim = state.result.claims.find((x) => x.id === row.dataset.c);
    if (!on && row.dataset.full) { compactRail(row.querySelector(".crail"), claim); delete row.dataset.full; }
  });
  document.querySelectorAll("#answers .ans").forEach((x) => x.classList.toggle("hl", !!c && c.evidence.includes(x.dataset.id)));
  markQuestioned();
  if (!c) { chipEl = null; drawConnector(false); return; }
  const row = document.querySelector(`#fileWrap .crow[data-c="${id}"]`);
  if (!row) return;
  chipEl = row.querySelector(".ctext");
  if (fresh || !row.dataset.full || state.questioning === id) fullRail(row, c);
  if (user && narrow()) row.scrollIntoView({block: "nearest", behavior: calm() ? "auto" : "smooth"});
  drawConnector(fresh && user);
}
function fullRail(row, c) {
  const rail = row.querySelector(".crail"); rail.replaceChildren(); row.dataset.full = "1"; openEditor = null;
  for (const ev of c.evidence) rail.append(evChip(ev, (chip, evId) => toggleEditor(rail, chip, evId)));
  if (!c.evidence.length) { const p = document.createElement("span"); p.className = "small"; p.textContent = "A stated limit of the file. It needs no answers behind it."; rail.append(p); }
  if (Array.isArray(c.other_readings) && c.other_readings.length) {
    const box = document.createElement("div"); box.className = "readings";
    const t = document.createElement("b"); t.textContent = "Other ways to read this";
    const ul = document.createElement("ul"); for (const r of c.other_readings) { const li = document.createElement("li"); li.textContent = String(r); ul.append(li); }
    box.append(t, ul); rail.append(box);
  }
  if (c.kind !== "limit") rail.append(questionControl(c));
}
function toggleEditor(rail, chip, id) {
  const open = chip.getAttribute("aria-expanded") === "true";
  rail.querySelectorAll(".editor").forEach((e) => e.remove());
  rail.querySelectorAll(".evchip").forEach((x) => x.setAttribute("aria-expanded", "false"));
  openEditor = null;
  if (open) { drawConnector(false); return; }
  chip.setAttribute("aria-expanded", "true");
  const ed = document.createElement("div"); ed.className = "editor"; ed.append(...editorControls(id));
  chip.after(ed); openEditor = id;
  const f = ed.querySelector("select, textarea"); if (f) f.focus();
  drawConnector(false);
}
// the controls that change one answer; changes write into state.answers and rebuild the file
function editorControls(id) {
  const a = state.answers, out = [];
  if (id[0] === "B") {
    const byId = Object.fromEntries(a.items.map((i) => [i.id, i.response]));
    const st = document.createElement("span"); st.className = "stmt"; st.textContent = "I " + lower(window.ITEMS[id] || "");
    out.push(st, itemSelect(id, byId[id]));
  } else if (id[0] === "S") {
    const s = a.scenarios.find((x) => x.id === id);
    if (s) out.push(...scenarioControls(s)); else out.push(muted("You skipped this situation, so nothing here counts."));
  } else if (id[0] === "W") {
    const w = a.writing.find((x) => x.id === id);
    if (w) out.push(writingControl(w)); else out.push(muted("You skipped this message."));
  } else if (id[0] === "V" && voiceTurn(id)) {
    const note = muted("From your interview. To change it, "), link = document.createElement("a");
    link.href = "/interview"; link.textContent = "open your interview answers"; note.append(link, ".");
    out.push(note);
  } else out.push(muted("From your voice interview."));
  return out;
}
const lower = (s) => s.charAt(0).toLowerCase() + s.slice(1);
function muted(t) { const p = document.createElement("span"); p.className = "small"; p.textContent = t; return p; }
function itemSelect(id, value, withId) {
  const a = state.answers, sel = document.createElement("select"); if (withId) sel.id = "it-" + id;
  sel.setAttribute("aria-label", id + " " + (window.ITEMS[id] || ""));
  const skip = document.createElement("option"); skip.value = ""; skip.textContent = "Skipped"; sel.append(skip);
  for (const x of [1, 2, 3, 4, 5]) { const o = document.createElement("option"); o.value = x; o.textContent = LABELS[x]; o.selected = x === value; sel.append(o); }
  sel.addEventListener("change", () => {
    a.items = a.items.filter((i) => i.id !== id); a.skipped = a.skipped.filter((s) => s !== id);
    if (sel.value) a.items.push({id, response: +sel.value}); else a.skipped.push(id);
    edited(id);
  });
  return sel;
}
function scenarioControls(s, withId) {
  const sel = document.createElement("select"); if (withId) sel.id = "ch-" + s.id; sel.setAttribute("aria-label", s.id + " choice");
  for (const x of "ABCD") { const o = document.createElement("option"); o.value = x; o.textContent = "Chose " + x; o.selected = x === s.choice; sel.append(o); }
  sel.addEventListener("change", () => { s.choice = sel.value; edited(s.id); });
  const ta = document.createElement("textarea"); if (withId) ta.id = "ex-" + s.id; ta.value = s.explanation || ""; ta.setAttribute("aria-label", s.id + " reason");
  ta.addEventListener("input", () => { s.explanation = ta.value; edited(s.id, true); });
  return [sel, ta];
}
function writingControl(w, withId) {
  const ta = document.createElement("textarea"); if (withId) ta.id = "wr-" + w.id; ta.value = w.text; ta.setAttribute("aria-label", w.id + " message");
  ta.addEventListener("input", () => { w.text = ta.value; edited(w.id, true); });
  return ta;
}
function edited(id, typing) {
  state.reviewed = false; persist(); regenSoon(); renderActions();
  if (!typing && $("#allAnswers").open && !$("#allAnswers").contains(document.activeElement)) renderAnswers();
}

/* "This reading doesn't fit me": kept on this page and sent with every build as disputed {claim_id: note}; the
   server marks the claim, and the coaching version leaves it out */
function disputesNow() {
  const out = {};
  for (const q of Object.values(state.claimQuestions)) if (q && q.claim_id) out[q.claim_id] = String(q.note || "").slice(0, 300);
  return out;
}
function questionControl(c) {
  const saved = state.claimQuestions[c.id];
  const box = document.createElement("div"); box.className = "qbox";
  if (state.questioning !== c.id) {
    const acts = document.createElement("div"); acts.className = "railacts";
    if (saved || c.disputed) {
      const note = saved ? saved.note : (c.dispute_note || "");
      const p = document.createElement("p"); p.className = "qnote";
      p.textContent = "You said this doesn't fit" + (note ? ": " + note : ".");
      box.append(p);
      acts.append(button("Edit note", "btn ghost small", () => openQuestion(c.id, note)),
        button("Undo", "btn ghost small", () => { delete state.claimQuestions[c.id]; state.questioning = null; renderQuestioned(); persist(); regen(); toast("Undone. Your file rebuilds without the mark."); }));
    } else acts.append(button("This reading doesn't fit me", "btn ghost small", () => openQuestion(c.id, "")));
    box.append(acts);
    return box;
  }
  const label = document.createElement("label"); label.className = "small"; label.htmlFor = "claimQuestion"; label.textContent = "What fits better? Optional, up to 300 characters. Your file rebuilds with this marked.";
  const ta = document.createElement("textarea"); ta.id = "claimQuestion"; ta.maxLength = 300; ta.value = state.questionDraft;
  ta.addEventListener("input", () => { state.questionDraft = ta.value; });
  const row = document.createElement("div"); row.className = "reactions";
  row.append(button("Save and rebuild", "btn small primary", () => {
    const note = ta.value.trim().slice(0, 300);
    state.claimQuestions[c.id] = {claim_id: c.id, claim_text: c.text, evidence: [...c.evidence], note, at: new Date().toISOString()};
    state.questioning = null; renderQuestioned(); persist(); refreshRail(c.id); regen();
    toast("Marked as not fitting. Your file rebuilds.");
  }), button("Cancel", "btn small ghost", () => { state.questioning = null; refreshRail(c.id); }));
  box.append(label, ta, row);
  return box;
}
function refreshRail(id) { const row = document.querySelector(`#fileWrap .crow[data-c="${id}"]`); const c = state.result.claims.find((x) => x.id === id); if (row && c) { fullRail(row, c); markQuestioned(); drawConnector(false); } }
function openQuestion(id, draft) {
  state.questioning = id; state.questionDraft = draft; refreshRail(id);
  const ta = document.getElementById("claimQuestion"); if (ta) ta.focus();
}
function markQuestioned() {
  const marked = new Set((state.result && state.result.claims || []).filter((c) => c.disputed).map((c) => c.id));
  document.querySelectorAll("#fileWrap .crow").forEach((row) => row.classList.toggle("questioned", !!state.claimQuestions[row.dataset.c] || marked.has(row.dataset.c)));
}
function renderQuestioned() {
  const list = Object.values(state.claimQuestions);
  $("#questioned").classList.toggle("hidden", !list.length);
  $("#questionedList").replaceChildren(...list.map((q) => {
    const li = document.createElement("li");
    const b = document.createElement("b"); b.textContent = q.claim_id;
    li.append(b, ": " + q.claim_text + " ");
    const n = document.createElement("span"); n.className = "small"; n.textContent = q.note ? "Your note: " + q.note : "No note.";
    li.append(document.createElement("br"), n);
    return li;
  }));
}
function closeSheet() {}

function renderGate() {
  const g = state.result.gate, problems = state.result.problems || [];
  const n = (state.result.claims || []).filter((c) => c.kind !== "limit").length;
  const word = !g.passed ? "breaks" : (g.warnings.length ? "works" : "solid");
  const head = !g.passed ? "Your file needs a small fix before it can be shared. This is about the file, not about you."
    : `All ${n} statements cite your answers.` + (g.warnings.length ? ` ${g.warnings.length} worth a look.` : " Nothing held back shows, and there are no fixed labels.");
  const bar = document.createElement("div"); bar.className = "gatebar " + word; bar.setAttribute("role", "status");
  const lamp = document.createElement("span"); lamp.className = "lamp"; lamp.setAttribute("aria-hidden", "true");
  const t = document.createElement("span"); t.textContent = head;
  bar.append(lamp, t);
  const list = (title, items) => { if (!items.length) return; const d = document.createElement("details"); const s = document.createElement("summary"); s.textContent = title; const ul = document.createElement("ul"); for (const x of items) { const li = document.createElement("li"); li.textContent = x; ul.append(li); } d.append(s, ul); bar.append(d); };
  if (g.blocking.length) { const ul = document.createElement("ul"); ul.style.flex = "1 1 100%"; for (const x of g.blocking) { const li = document.createElement("li"); li.textContent = x; ul.append(li); } bar.append(ul); }
  list(g.warnings.length === 1 ? "See the one worth a look" : `See the ${g.warnings.length} worth a look`, g.warnings);
  list(`${problems.length} note${problems.length === 1 ? "" : "s"} about your answer file`, problems);
  $("#gate").replaceChildren(bar);
}

/* ---------- Your file in Wethos Style terms: hypotheses, never scores ---------- */
const WETHOS_ORDER = ["ideas", "relational", "order", "action"];
function renderWethos(first) {
  const box = $("#wethos");
  const w = state.result.sidecar && state.result.sidecar.wethos_style_hypotheses;
  if (!w) { box.classList.add("hidden"); return; }
  box.classList.remove("hidden"); box.replaceChildren();
  const head = document.createElement("div"); head.style.display = "grid"; head.style.gap = "var(--s-2)";
  head.innerHTML = `<span class="eyebrow">Optional lens</span><h2 id="wethosTitle" style="font-size: var(--t-xl)">Your file in Wethos Style terms</h2>
    <p class="label"><b>Hypotheses, not Wethos scores.</b> Wethos Style is Wethos's own behavioral assessment; lumin8r maps your answers onto its four scales so you can start a conversation. To measure it properly, <a href="https://wethos.ai/style" target="_blank" rel="noopener">take Wethos Style</a>.</p>`;
  box.append(head);
  for (const key of WETHOS_ORDER) {
    const h = w[key]; if (!h || typeof h !== "object") continue;
    const m = /^(.*?)\s*\((.*?)\s+to\s+(.*?)\)\s*$/.exec(h.scale || "") || [null, h.scale || key, "", ""];
    const [, name, left, right] = m;
    const hyp = String(h.hypothesis || "");
    let pos = null;
    if (/between/i.test(hyp)) pos = 50; else if (right && hyp.toLowerCase().includes(right.toLowerCase())) pos = 88; else if (left && hyp.toLowerCase().includes(left.toLowerCase())) pos = 12;
    const row = document.createElement("div"); row.className = "wrow" + (first ? " spawn-in" : "");
    const main = document.createElement("div");
    main.innerHTML = `<h3>${esc(name)}</h3>
      <div class="track" role="img" aria-label="${esc(name)}: ${esc(hyp)}"><span>${esc(left)}</span><span class="bar">${pos === null ? "" : `<span class="marker" style="left:${pos}%"></span>`}</span><span>${esc(right)}</span></div>
      <p class="basis"><span class="hyp">${esc(hyp.charAt(0).toUpperCase() + hyp.slice(1))}.</span> ${esc(h.basis || "")}</p>
      <p class="strength">Strength: ${esc(h.strength || "not stated")}</p>`;
    const rail = document.createElement("div"); rail.className = "crail";
    const ev = Array.isArray(h.evidence) ? h.evidence : [];
    for (const id of ev) {
      const chip = document.createElement("button"); chip.type = "button"; chip.className = "ev-id"; chip.dataset.ids = id; chip.textContent = label(id); chip.style.border = "1px solid var(--line)"; chip.style.background = "var(--panel-2)";
      chip.setAttribute("aria-label", label(id) + ": " + evidenceSummary(id).txt + ". Show it.");
      chip.addEventListener("click", () => {
        const open = rail.querySelector(".evchip");
        rail.querySelectorAll(".evchip, .editor").forEach((x) => x.remove());
        if (open && open.dataset.id === id) return;
        const full = evChip(id, (b, evId) => toggleEditor(rail, b, evId)); rail.append(full); full.focus();
      });
      rail.append(chip);
    }
    if (!ev.length) rail.append(muted(/withheld/i.test(hyp) ? "You withheld this section." : "No answers point here."));
    row.append(main, rail);
    box.append(row);
  }
}

/* ---------- file details: the technical part, kept quiet ---------- */
function renderDetails() {
  const sc = state.result.sidecar || {};
  const rows = [["Version", SCOPE_NAMES[sc.share_scope] || sc.share_scope], ["Generated", sc.generated], ["Review by", sc.review_by], ["Rules version", sc.converter_version],
    ["Assessment version", sc.kit_version], ["Input digest", sc.input_digest], ["File digest", sc.file_digest], ["Sections withheld", (sc.withheld_domains || []).map((d) => DOMAINS[d] || d).join(", ") || "none"]];
  const dl = document.createElement("dl"); dl.className = "details-grid";
  for (const [k, v] of rows) { if (v === undefined || v === null || v === "") continue; const dt = document.createElement("dt"); dt.textContent = k; const dd = document.createElement("dd"); dd.textContent = String(v); dl.append(dt, dd); }
  const n = (state.result.claims || []).length;
  const meta = document.createElement("p"); meta.className = "small"; meta.id = "fileMeta"; meta.textContent = `${n} statements, built ${new Date().toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})}. The file is built from your answers by fixed rules; the digests let anyone check it was not changed.`;
  const banner = document.createElement("p"); banner.className = "label-banner"; banner.innerHTML = "<b>AI-generated representation.</b> This file describes tendencies your answers support. Simulated answers made from it are not your statements, approval or commitments.";
  $("#detailsBody").replaceChildren(meta, dl, banner);
  $("#mdView").innerHTML = `<div class="file" id="file-view" tabindex="0" aria-label="Your me.md file">${md(state.result.markdown)}</div>`;
  $("#mdView").querySelectorAll(".claim").forEach((el) => el.addEventListener("click", () => { $("#mdDialog").close(); showClaim(el.dataset.c, true); const r = document.querySelector(`#fileWrap .crow[data-c="${el.dataset.c}"]`); if (r) r.scrollIntoView({block: "center", behavior: calm() ? "auto" : "smooth"}); }));
}
$("#viewMd").addEventListener("click", () => { if (!state.result) return; const d = $("#mdDialog"); if (d.showModal) d.showModal(); else d.setAttribute("open", ""); });
$("#closeMd").addEventListener("click", () => $("#mdDialog").close());
$("#mdDialog").addEventListener("click", (e) => { if (e.target === e.currentTarget) e.currentTarget.close(); });

/* ---------- the connector: a fine lit line from the selected statement to each answer chip ---------- */
const NS = "http://www.w3.org/2000/svg";
let drawQueued = false;
function drawConnector(animate) {
  const svg = $("#connector");
  svg.replaceChildren(); svg.classList.remove("draw");
  if (!state.activeClaim || state.station !== "file" || narrow() || !chipEl || !document.body.contains(chipEl)) return;
  const top = document.querySelector(".topbar").getBoundingClientRect().bottom;
  const t = chipEl.getBoundingClientRect();
  const row = chipEl.closest(".crow");
  const chips = row ? row.querySelectorAll(".crail .evchip") : [];
  chips.forEach((chip, i) => {
    const r = chip.getBoundingClientRect();
    if (r.bottom < top || r.top > innerHeight) return;
    const x1 = t.right + 4, y1 = Math.min(Math.max(t.top + 22, t.top), t.bottom - 10);
    const x2 = r.left - 4, y2 = r.top + r.height / 2;
    if (y1 < top) return;
    const dx = Math.max(14, (x2 - x1) * .5);
    const path = document.createElementNS(NS, "path");
    path.setAttribute("d", `M${x1} ${y1} C${x1 + dx} ${y1} ${x2 - dx} ${y2} ${x2} ${y2}`);
    svg.append(path);
    const len = path.getTotalLength();
    path.style.setProperty("--len", len);
    path.style.strokeDasharray = animate && !calm() ? len : "none";
    path.style.animationDelay = (i * 60) + "ms";
    const dot = document.createElementNS(NS, "circle"); dot.setAttribute("cx", x2); dot.setAttribute("cy", y2); dot.setAttribute("r", 2.5); svg.append(dot);
  });
  if (animate && !calm()) { void svg.getBoundingClientRect(); svg.classList.add("draw"); }
}
function queueDraw() { if (drawQueued) return; drawQueued = true; requestAnimationFrame(() => { drawQueued = false; drawConnector(false); }); }
window.addEventListener("scroll", queueDraw, {passive: true});
window.addEventListener("resize", queueDraw);
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && state.activeClaim && state.station === "file" && !document.querySelector("dialog[open]")) showClaim(null); });

/* ---------- all your answers ---------- */
function renderAnswers() {
  const a = state.answers; if (!a) return;
  const box = $("#answers"); box.replaceChildren();
  const h = (t) => { const e = document.createElement("h3"); e.textContent = t; return e; };
  box.append(h("Situations"));
  for (const s of a.scenarios) { const row = ansRow(s.id); const g = grow(); g.append(...scenarioControls(s, true)); row.append(g); box.append(row); }
  box.append(h("Messages"));
  for (const w of a.writing) { const row = ansRow(w.id); row.append(writingControl(w, true)); box.append(row); }
  box.append(h("About you"));
  const byId = Object.fromEntries(a.items.map((i) => [i.id, i.response]));
  for (let n = 1; n <= 50; n++) {
    const id = "B" + String(n).padStart(2, "0");
    const row = ansRow(id); const g = grow();
    const st = document.createElement("span"); st.className = "stmt"; st.textContent = "I " + lower(window.ITEMS[id] || "");
    g.append(st, itemSelect(id, byId[id], true)); row.append(g); box.append(row);
  }
  if (state.activeClaim && state.result) {
    const c = state.result.claims.find((x) => x.id === state.activeClaim);
    document.querySelectorAll("#answers .ans").forEach((x) => x.classList.toggle("hl", !!c && c.evidence.includes(x.dataset.id)));
  }
}
function grow() { const g = document.createElement("div"); g.className = "grow"; return g; }
function ansRow(id) { const r = document.createElement("div"); r.className = "ans"; r.dataset.id = id; const s = document.createElement("span"); s.className = "id"; s.textContent = label(id); r.append(s); return r; }
function button(text, cls, onclick, disabled) { const b = document.createElement("button"); b.type = "button"; b.className = cls; b.textContent = text; b.addEventListener("click", onclick); if (disabled) b.disabled = true; return b; }

/* ---------- 3 rehearse with your understudy (Claude, an AI) ---------- */
const TWIN_OFF = "Rehearsing is not switched on for this server, so your understudy cannot answer here. Everything else works.";
const TWIN_DECLINED = "Rehearsing is off because you declined AI processing. Your file was built without AI and everything else works. To rehearse, choose Change my choices in Settings and tick 2, AI processing.";
async function initTwin(config) {
  if (config && config.twin_enabled === false) { state.twin.reason = TWIN_OFF; }
  try {
    const r = await fetch("/api/twin/questions");
    if (!r.ok) throw new Error();
    const j = await r.json();
    state.twin.practice = Array.isArray(j.practice) ? j.practice : [];
    state.twin.enabled = !(config && config.twin_enabled === false);
    renderPractice();
  } catch (e) { state.twin.reason = TWIN_OFF; state.twin.enabled = false; }
}
function twinReady() { return state.twin.enabled && !!state.result && state.consented && state.purposes.includes("ai_processing"); }
function updateTwin() {
  const ready = twinReady();
  const declined = state.consented && !state.purposes.includes("ai_processing");
  const box = $("#twinStatusBox");
  let msg = "";
  if (!state.twin.enabled) msg = state.twin.reason || TWIN_OFF;
  else if (declined) msg = TWIN_DECLINED;
  else if (!state.result) msg = "Your understudy is ready once your file is built.";
  box.textContent = msg; box.className = "notice twin" + (msg ? "" : " hidden");
  $("#twinTools").classList.toggle("hidden", !state.twin.enabled || declined);
  $("#askOwn").disabled = !ready;
  const pa = document.getElementById("askPractice"); if (pa) pa.disabled = !ready;
}
// tabs: Ask your own / Practice library (arrow keys move between them)
const tabs = [$("#tab-own"), $("#tab-lib")];
function selectTab(t) {
  tabs.forEach((x) => { const on = x === t; x.setAttribute("aria-selected", String(on)); x.tabIndex = on ? 0 : -1; document.getElementById(x.getAttribute("aria-controls")).classList.toggle("hidden", !on); });
}
tabs.forEach((t, i) => {
  t.addEventListener("click", () => selectTab(t));
  t.addEventListener("keydown", (e) => { if (e.key === "ArrowRight" || e.key === "ArrowLeft") { const n = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length]; selectTab(n); n.focus(); } });
});
$("#ownQ").addEventListener("input", () => { $("#ownCount").textContent = $("#ownQ").value.length + " / 600"; });
$("#askOwn").addEventListener("click", () => {
  const text = $("#ownQ").value.trim();
  if (!text) { $("#twinStatus").textContent = "Write a situation first, in a sentence or two."; $("#ownQ").focus(); return; }
  const kind = document.querySelector("input[name=ownKind]:checked").value;
  ask({markdown: null, own_question: text, kind}, {question_id: "OWN", question_text: text, kind}, $("#askOwn"));
});
function renderPractice() {
  const groups = [["scenario", "Situations: what would you do?"], ["writing", "Messages: what would you write?"]];
  const box = $("#practice"); box.replaceChildren();
  for (const [type, title] of groups) {
    const items = state.twin.practice.filter((p) => p.type === type);
    if (!items.length) continue;
    const h = document.createElement("h3"); h.textContent = title; box.append(h);
    for (const p of items) {
      const b = document.createElement("button"); b.type = "button"; b.className = "pcard"; b.dataset.id = p.id; b.setAttribute("aria-pressed", "false");
      const t = document.createElement("b"); t.textContent = p.topic;
      const w = document.createElement("span"); w.textContent = p.wording;
      b.append(t, w);
      b.addEventListener("click", () => pickPractice(p.id));
      box.append(b);
    }
  }
}
function pickPractice(id) {
  const p = state.twin.practice.find((x) => x.id === id); if (!p) return;
  state.twin.picked = id;
  document.querySelectorAll(".pcard").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.id === id)));
  const box = $("#picked"); box.classList.remove("hidden"); box.replaceChildren();
  const t = document.createElement("span"); t.className = "eyebrow"; t.textContent = p.topic;
  const w = document.createElement("p"); w.textContent = p.wording;
  box.append(t, w);
  if (p.options) {
    const ol = document.createElement("ol");
    for (const [L, text] of Object.entries(p.options)) { const li = document.createElement("li"); const b = document.createElement("b"); b.textContent = L; li.append(b, text); ol.append(li); }
    box.append(ol);
  }
  const ask2 = button("Ask your understudy", "btn p2 small", () => ask({question_id: id}, {question_id: id, question_text: p.wording, kind: p.type}, ask2));
  ask2.id = "askPractice"; ask2.disabled = !twinReady();
  box.append(ask2);
  ask2.focus();
}
async function ask(body, meta, btn) {
  if (!twinReady()) return;
  const label = btn.textContent;
  btn.disabled = true; btn.setAttribute("aria-busy", "true"); btn.textContent = "Your understudy is thinking...";
  $("#twinStatus").textContent = "Your understudy is answering. This takes a few seconds.";
  try {
    const payload = Object.assign({}, body, {markdown: state.result.markdown});
    const r = await post("/api/twin", payload);
    const q = r.question || {};
    const note = {question_id: q.id || meta.question_id, question_text: meta.question_text, question_prompt: q.prompt || "", kind: meta.kind, file_scope: state.scope,
      answer: r.text, model: r.model || "", reaction: null, note: "", at: new Date().toISOString()};
    state.notes.push(note); persist();
    const card = twinCard(note);
    $("#twinOut").prepend(card);
    if (!narrow()) { const sb = $("#stepbody"); sb.scrollBy({top: card.getBoundingClientRect().top - sb.getBoundingClientRect().top - 16, behavior: calm() ? "auto" : "smooth"}); }
    else card.scrollIntoView({block: "nearest", behavior: calm() ? "auto" : "smooth"});
    $("#twinStatus").textContent = "Does it sound like you? Your reaction stays on this page.";
  } catch (err) {
    $("#twinStatus").textContent = err.status === 429 ? `Your understudy needs a short pause. Try again in ${err.retryAfter || 30} seconds.`
      : err.status === 503 ? TWIN_OFF
      : err.status === 403 ? TWIN_DECLINED
      : err.status === 400 ? "Your understudy could not take that: " + err.message + "."
      : "Your understudy could not answer just now (" + err.message + "). Please try again.";
  } finally { btn.removeAttribute("aria-busy"); btn.textContent = label; btn.disabled = !twinReady(); }
}
function twinCard(note) {
  const wrap = document.createElement("div"); wrap.className = "twin-answer spawn-in";
  const msg = document.createElement("div"); msg.className = "p2-msg";
  const who = document.createElement("span"); who.className = "who"; who.textContent = "AI-generated simulation. Your understudy is Claude, an AI. It rehearses your part from your answers. It\u2019s practice, not you.";
  const q = document.createElement("span"); q.className = "q"; q.textContent = note.question_text;
  const t = document.createElement("p"); t.className = "a"; t.textContent = note.answer;
  msg.append(who, q, t);
  const row = document.createElement("div"); row.className = "reactions";
  const yes = button("Sounds like me", "btn small", () => react("like_me"));
  const no = button("Not me", "btn small", () => react("not_me"));
  yes.setAttribute("aria-pressed", "false"); no.setAttribute("aria-pressed", "false");
  const ta = document.createElement("textarea"); ta.placeholder = "Optional: what would you have said?"; ta.setAttribute("aria-label", "Your note on this answer"); ta.rows = 2;
  ta.addEventListener("input", () => { note.note = ta.value; persist(); });
  function react(v) { note.reaction = v; yes.setAttribute("aria-pressed", String(v === "like_me")); no.setAttribute("aria-pressed", String(v === "not_me")); persist(); }
  row.append(yes, no);
  wrap.append(msg, row, ta);
  return wrap;
}

/* ---------- 4 share: end-to-end encrypted links ---------- */
function renderScopes() {
  const box = $("#scopes"); box.replaceChildren();
  const entries = Object.entries(state.scopes).sort(([a], [b]) => (a === "coaching" ? -1 : b === "coaching" ? 1 : 0));
  for (const [k, v] of entries) {
    const l = document.createElement("label"); l.className = "choicecard";
    const r = document.createElement("input"); r.type = "radio"; r.name = "scope"; r.value = k; r.id = "scope-" + k; r.checked = k === state.scope;
    r.addEventListener("change", () => { state.scope = k; regenSoon(); renderAiStep(); });
    const t = document.createElement("span"); t.innerHTML = `<b>${esc(SCOPE_NAMES[k] || k)}</b>${k === "coaching" ? ' <span class="chip accent">default</span>' : ""}<br><span class="small">${esc(v)}</span>`;
    l.append(r, t); box.append(l);
  }
  $("#withhold").replaceChildren();
  for (const [k, v] of Object.entries(DOMAINS)) {
    const l = document.createElement("label"); l.className = "check";
    const c = document.createElement("input"); c.type = "checkbox"; c.id = "wh-" + k; c.value = k;
    c.addEventListener("change", () => { state.withhold = [...document.querySelectorAll("#withhold input:checked")].map((x) => x.value); regenSoon(); });
    l.append(c, document.createTextNode(v)); $("#withhold").append(l);
  }
}
function syncScopeRadios() { document.querySelectorAll("input[name=scope]").forEach((r) => { r.checked = r.value === state.scope; }); }
function linkDecision() { return {recipient: $("#shareRecipient").value.trim(), purpose: $("#sharePurpose").value.trim(), version: state.scope}; }
["#shareRecipient", "#sharePurpose"].forEach((s) => $(s).addEventListener("input", () => { renderActions(); }));
function renderShareGate() {
  const g = $("#shareGate");
  if (!gateOk()) { g.classList.remove("hidden"); g.textContent = "Your file needs a small fix before it can be shared. It is listed above your file."; }
  else if (!state.reviewed) { g.classList.remove("hidden"); g.innerHTML = ""; g.append("Read your file first. When it sounds like you, tick “I read this file” in step 2. ", button("Go to Your file", "btn link", () => go("file"))); }
  else g.classList.add("hidden");
}

const b64url = (bytes) => { let s = ""; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000)); return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); };
function loadShares() { const s = store.get("localStorage", SHARES); return Array.isArray(s) ? s : []; }
function saveShares(list) { store.set("localStorage", SHARES, list); }
async function createShare() {
  const d = linkDecision(), p = $("#primary");
  if (!d.recipient || !d.purpose || !gateOk() || !state.reviewed) return;
  if (!window.crypto || !crypto.subtle) { shareNote("bad", "This browser cannot encrypt a link here. Open lumin8r over https in a current browser."); return; }
  p.disabled = true; p.setAttribute("aria-busy", "true"); p.textContent = "Locking your link...";
  try {
    const result = await ensureCurrent();
    if (!result) throw Object.assign(new Error("your file could not be built"), {status: -1});
    const days = Number((document.querySelector("input[name=expiry]:checked") || {}).value || 30);
    const payload = {person_id: (state.answers && state.answers.person_id) || state.pid, version: state.scope, generated: (result.sidecar && result.sidecar.generated) || new Date().toISOString(), markdown: result.markdown, sidecar: result.sidecar};
    const keyBytes = crypto.getRandomValues(new Uint8Array(32));
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const key = await crypto.subtle.importKey("raw", keyBytes, {name: "AES-GCM"}, false, ["encrypt"]);
    const ct = new Uint8Array(await crypto.subtle.encrypt({name: "AES-GCM", iv}, key, new TextEncoder().encode(JSON.stringify(payload))));
    const expires = new Date(Date.now() + days * 86400000 - 60000).toISOString();
    const r = await post("/api/shares", {ciphertext: b64url(ct), iv: b64url(iv), version: state.scope, purpose: d.purpose, recipient_label: d.recipient, expires_at: expires, consent_token: state.token});
    const link = location.origin + (r.url_path || ("/s/" + r.id)) + "#" + b64url(keyBytes);
    keyBytes.fill(0);
    const entry = {id: r.id, manage_token: r.manage_token, recipient: d.recipient, purpose: d.purpose, version: state.scope, created_at: new Date().toISOString(), expires_at: expires, url_path: r.url_path || "/s/" + r.id};
    if (state.remember) entry.link = link; /* the key stays on this device only if the person chose to remember */
    saveShares([entry].concat(loadShares()));
    showLink(link, entry);
    renderShares();
    $("#shareRecipient").value = ""; $("#sharePurpose").value = "";
  } catch (err) {
    if (err.status === 404) shareNote("warn", "Share links are not switched on for this server yet. You can still download your file from Settings.");
    else if (err.status === 429) shareNote("warn", "That is a lot of links at once. Please wait a minute and try again.");
    else if (err.status === 403) shareNote("warn", "Your agreement needs renewing before you can share. Agree again in step 1; your file is safe.");
    else if (err.status === 400 || err.status === 413) shareNote("warn", "The link was not made: " + err.message + ".");
    else shareNote("bad", "The link was not made: " + err.message + ". Nothing was shared. Please try again.");
  } finally { p.removeAttribute("aria-busy"); renderActions(); }
}
function shareNote(kind, text) { const box = $("#shareResult"); box.classList.remove("hidden"); box.innerHTML = ""; const n = document.createElement("p"); n.className = "notice " + kind; n.setAttribute("role", "alert"); n.textContent = text; box.append(n); }
function showLink(link, entry) {
  const box = $("#shareResult"); box.classList.remove("hidden");
  box.innerHTML = `<div class="lockbox open" id="lockbox">
      <span class="lk" aria-hidden="true"><svg viewBox="0 0 24 24"><path class="shackle" d="M8 11V8a4 4 0 0 1 8 0v3"/><rect x="5" y="11" width="14" height="9" rx="2.5"/></svg></span>
      <div><b>Your encrypted link is ready</b><p class="small">For ${esc(entry.recipient)}. It ends on ${esc(fmtDate(entry.expires_at))}. We cannot read it.</p></div>
    </div>
    <div class="field" style="margin-top: var(--s-3)"><label for="shareLink">Your link</label>
      <div class="linkrow"><input id="shareLink" type="text" readonly value="${esc(link)}"><button class="btn primary small" id="copyLink" type="button">Copy link</button></div>
      <p class="small">Send it to ${esc(entry.recipient)} however you like. Anyone with the whole link can open it until it ends, and the part after # is the key, so keep it whole.${state.remember ? "" : " This page will not show it again once you leave, so copy it now."}</p></div>`;
  $("#copyLink").addEventListener("click", () => copyText(link, "Link copied."));
  $("#shareLink").addEventListener("focus", (e) => e.target.select());
  const lock = $("#lockbox");
  requestAnimationFrame(() => requestAnimationFrame(() => { lock.classList.remove("open"); lock.classList.add("locked"); }));
  box.scrollIntoView({block: "nearest", behavior: calm() ? "auto" : "smooth"});
  toast("Locked and ready. Only someone with the link can open it.");
}
const fmtDate = (iso) => { try { return new Date(iso).toLocaleDateString(undefined, {day: "numeric", month: "long", year: "numeric"}); } catch (_) { return iso; } };
function daysLeft(iso) { const d = Math.ceil((new Date(iso) - Date.now()) / 86400000); return d; }
function renderShares() {
  const now = Date.now();
  let list = loadShares();
  const live = list.filter((s) => new Date(s.expires_at).getTime() > now);
  if (live.length !== list.length) { saveShares(live); list = live; }
  const ul = $("#shareList"); ul.replaceChildren();
  if (!list.length) { const li = document.createElement("li"); li.className = "small"; li.style.border = "1px dashed var(--line-2)"; li.textContent = "No links yet. When you make one, it appears here with its end date and a way to turn it off."; ul.append(li); return; }
  for (const s of list) {
    const li = document.createElement("li"); li.dataset.share = s.id;
    const who = document.createElement("div"); who.className = "who";
    const name = document.createElement("b"); name.textContent = s.recipient;
    const meta = document.createElement("span"); meta.className = "small"; const left = daysLeft(s.expires_at);
    meta.textContent = `${SCOPE_SHORT[s.version] || s.version} · ends ${fmtDate(s.expires_at)} (${left <= 1 ? "within a day" : "in " + left + " days"})`;
    who.append(name, meta);
    const why = document.createElement("span"); why.className = "small"; why.textContent = s.purpose;
    const row = document.createElement("div"); row.className = "row";
    if (s.link) row.append(button("Copy link", "btn small", () => copyText(s.link, "Link copied.")));
    row.append(button("Turn off", "btn small danger", () => confirmRevoke(li, s)));
    li.append(who, why, row);
    ul.append(li);
  }
}
function confirmRevoke(li, s) {
  const box = document.createElement("div"); box.className = "confirmbox"; box.setAttribute("role", "alertdialog"); box.setAttribute("aria-label", "Turn off this link");
  const p = document.createElement("p"); p.textContent = `Turn off the link for ${s.recipient}? It stops working at once and the locked copy is deleted.`;
  const row = document.createElement("div"); row.className = "reactions";
  const keep = button("Keep it", "btn small", () => { box.remove(); });
  row.append(keep, button("Turn off", "btn small danger solid", () => revoke(s, box)));
  box.append(p, row); li.append(box); keep.focus();
}
async function revoke(s, box) {
  let status = 0;
  try { const r = await fetch("/api/shares/" + encodeURIComponent(s.id), {method: "DELETE", headers: {"X-Manage-Token": s.manage_token}}); status = r.status; }
  catch (_) { status = -1; }
  if (status === 200 || status === 204 || status === 404 || status === 410) {
    saveShares(loadShares().filter((x) => x.id !== s.id));
    renderShares();
    toast(status === 404 || status === 410 ? "That link had already ended." : "Link turned off. The locked copy is deleted.");
    return true;
  }
  if (box) { const p = box.querySelector("p"); p.textContent = status === 403 ? "This device's key does not match that link, so it could not be turned off from here." : status === -1 ? "We could not reach the server. Check your connection and try again." : "It could not be turned off just now (status " + status + "). Please try again."; }
  return false;
}

/* ---------- 5 use with your AI ---------- */
function renderAiStep() {
  const g = $("#aiGate");
  if (!gateOk()) { g.classList.remove("hidden"); g.textContent = "Your file needs a small fix first. It is listed above your file."; }
  else if (!state.reviewed) { g.classList.remove("hidden"); g.innerHTML = ""; g.append("Read your file first. When it sounds like you, tick “I read this file” in step 2. ", button("Go to Your file", "btn link", () => go("file"))); }
  else g.classList.add("hidden");
  const v = $("#aiVersion");
  v.classList.remove("hidden"); v.innerHTML = "";
  if (state.scope === "coaching") {
    v.append("You are copying the coaching version. For your own AI, the full version usually helps more: it includes your own words, so drafts can follow how you write. ",
      button("Use the full version", "btn link", () => { state.scope = "full"; syncScopeRadios(); regenSoon(); renderAiStep(); }));
  } else v.textContent = "You are copying the full version, including your own words. Keep it to your own assistants.";
}
async function copyFile() {
  if (!gateOk() || !state.reviewed) return;
  const r = await ensureCurrent(); if (!r) return;
  copyText(r.markdown, "Copied me.md. Start a new chat and paste it in.");
}
async function copyText(text, done) {
  let ok = false;
  try { if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(text); ok = true; } } catch (_) {}
  if (!ok) {
    const ta = document.createElement("textarea"); ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0"; document.body.append(ta); ta.select();
    try { ok = document.execCommand("copy"); } catch (_) {}
    ta.remove();
  }
  toast(ok ? done : "Copying was blocked by the browser. Select the text and copy it by hand.");
}

/* ---------- settings: this device, downloads, consent ---------- */
const dlg = $("#settings");
$("#openSettings").addEventListener("click", () => { renderSettings(); if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", ""); });
$("#closeSettings").addEventListener("click", () => dlg.close());
dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
function renderSettings() {
  $("#remember").checked = state.remember;
  const can = gateOk() && state.reviewed;
  $("#dlMd").disabled = !can; $("#dlJson").disabled = !can; $("#dlAnswers").disabled = !state.answers;
  $("#dlNote").textContent = can ? "me.json is the same file as data. Corrected answers carry your edits, your questions and your reactions to your understudy."
    : "me.md and me.json are available once you have read your file and ticked “I read this file” in step 2. Corrected answers are always available.";
  const d = shareDecision();
  if (!(d && can) && $("#shareStatus").className === "small") $("#shareStatus").textContent = "";
  if (d && can) { $("#shareStatus").className = "small"; $("#shareStatus").textContent = `Downloading now records it as shared with ${d.recipient} (${SCOPE_NAMES[d.version]}), because “Who is it for?” is filled in under Share. Clear it for a personal download.`; }
  $("#consentSummary").textContent = state.consented ? `You agreed as ${state.pid}${state.receiptAt ? " on " + fmtDate(state.receiptAt) : ""}. AI processing for your understudy: ${state.purposes.includes("ai_processing") ? "yes" : "no"}.` : "You have not agreed yet.";
  $("#changeChoices").disabled = !state.consented;
  if (!$("#forgetSlot .confirmbox")) renderForget(false);
  renderWithdraw();
}
$("#remember").addEventListener("change", (e) => {
  state.remember = e.target.checked;
  if (state.remember) { try { CTX.localStorage.setItem(REMEMBER, "1"); } catch (_) {} persist(); persistConsent(); toast("Your file will be here next time on this device."); }
  else { store.del("localStorage", REMEMBER); store.del("localStorage", HANDOFF); store.del("localStorage", CONSENT); store.del("localStorage", KIT);
    saveShares(loadShares().map((s) => { const c = Object.assign({}, s); delete c.link; return c; }));
    toast("This device will not keep your file after you close the tab."); }
});
function renderForget(confirming) {
  const slot = $("#forgetSlot"); slot.replaceChildren();
  if (!confirming) { slot.append(button("Forget this device", "btn small", () => renderForget(true))); return; }
  const box = document.createElement("div"); box.className = "confirmbox"; box.setAttribute("role", "alertdialog"); box.setAttribute("aria-label", "Forget this device");
  const n = loadShares().length;
  const p = document.createElement("p"); p.textContent = "Forget this device? Your saved answers, your file and your choices are deleted from the lumin8r server." + (n ? ` This also removes the keys that turn off your ${n} active link${n === 1 ? "" : "s"}; turn them off first if you want them off.` : "");
  const row = document.createElement("div"); row.className = "reactions";
  const keep = button("Keep everything", "btn small", () => renderForget(false));
  row.append(keep, button("Forget this device", "btn small danger solid", forgetDevice));
  box.append(p, row); slot.append(box); keep.focus();
}
async function forgetDevice() {
  state.voiceFile = null; renderVoiceLine();
  await CTX.forgetAll();  // every saved item on the server, and the cookie
  location.replace("/app");
}
$("#changeChoices").addEventListener("click", () => {
  dlg.close();
  $("#pid").value = state.pid;
  document.querySelectorAll(".purpose").forEach((c) => { c.checked = state.purposes.includes(c.value); });
  agreeHint(); go("agree");
});
let confirmingWithdraw = false;
function renderWithdraw() {
  const slot = $("#withdrawSlot"); slot.replaceChildren();
  if (!state.consented) return;
  if (confirmingWithdraw) {
    const box = document.createElement("div"); box.className = "confirmbox"; box.setAttribute("role", "alertdialog"); box.setAttribute("aria-label", "Withdraw consent");
    const p = document.createElement("p"); p.textContent = "Withdraw? Your saved answers, file and interview are deleted from the server, your share links are turned off, and the server records the withdrawal. A file you already downloaded cannot be recalled.";
    const row = document.createElement("div"); row.className = "reactions";
    const keep = button("Keep going", "btn small", () => { confirmingWithdraw = false; renderWithdraw(); });
    row.append(keep, button("Withdraw", "btn small danger solid", withdraw));
    box.append(p, row); slot.append(box); keep.focus();
  } else {
    const note = document.createElement("p"); note.className = "small"; note.textContent = "Changed your mind? You can withdraw at any time, without penalty.";
    slot.append(note, button("Withdraw consent", "btn small danger", () => { confirmingWithdraw = true; renderWithdraw(); }));
  }
}

/* sharing by download: Mark's separate decision, recorded in me.json and the consent ledger */
let shareRecorded = null;
function shareDecision() {
  const recipient = $("#shareRecipient").value.trim();
  if (!recipient) return null;
  return {recipient, purpose: $("#sharePurpose").value.trim(), version: state.scope};
}
async function recordShare() {
  const d = shareDecision(), status = $("#shareStatus");
  if (!d) { status.className = "small"; status.textContent = "A personal download: no recipient, so nothing is recorded as shared."; return null; }
  const key = [d.recipient, d.purpose, d.version].join("\u0000");
  if (shareRecorded && shareRecorded.key === key) return shareRecorded.sharing;
  const sharing = Object.assign({}, d, {decided_at: new Date().toISOString()});
  status.className = "small"; status.textContent = "Recording your sharing decision...";
  try {
    await post("/api/consent", {person_id: state.pid, purposes: ["share_profile"], ai_services: [], share_with: [d.recipient + " | purpose: " + d.purpose + " | version: " + d.version]});
    shareRecorded = {key, sharing};
    status.className = "notice ok"; status.textContent = `Recorded: shared with ${d.recipient}, ${SCOPE_NAMES[d.version] || d.version}.`;
  } catch (err) {
    status.className = "notice warn"; status.textContent = "Your sharing decision was not recorded (" + err.message + "). The file still downloaded; download again to retry.";
  }
  return sharing;
}
async function downloadShared(kind) {
  const r = await ensureCurrent(); if (!r) return;
  const sharing = await recordShare();
  if (kind === "md") { download("me.md", r.markdown, "text/markdown"); state.downloadedMd = true; }
  else download("me.json", JSON.stringify(Object.assign({}, r.sidecar, {sharing}), null, 2), "application/json");
}
function download(name, text, type) { const b = new Blob([text], {type}); const u = URL.createObjectURL(b); const a = document.createElement("a"); a.href = u; a.download = name; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 1000); }
function downloadAnswers() {
  const base = state.result ? state.result.answers : state.answers;
  const review_notes = {twin_reactions: state.notes, claim_questions: Object.values(state.claimQuestions), disputed: disputesNow()};
  download("answers_corrected.json", JSON.stringify(Object.assign({}, base, {review_notes}), null, 2), "application/json");
}
$("#dlMd").addEventListener("click", () => downloadShared("md"));
// Finish: this person is done. Everything saved for this browser is wiped, as Start over does, so the next person
// starts a clean assessment in the same browser. Warn first if the file was not downloaded in this visit.
async function endSession(button, verb) {
  const sure = state.downloadedMd
    ? confirm(verb + "? Your answers and file are wiped from this browser, and the assessment starts blank.")
    : confirm("You have not downloaded your file. If you " + verb.toLowerCase() + " now it is wiped from this browser, and you will have to ask the site admin for a copy. Are you sure?");
  if (!sure) return;
  button.disabled = true;
  await CTX.forgetAll();
  location.replace("/assessment");
}
$("#finishSession").addEventListener("click", (e) => endSession(e.currentTarget, "Finish"));
// Start over, on every step (Rehearse included): the same wipe as Finish, the same warning
$("#startOver").addEventListener("click", (e) => endSession(e.currentTarget, "Start over"));
$("#dlMdHead").addEventListener("click", () => downloadShared("md"));
$("#dlMdDialog").addEventListener("click", () => downloadShared("md"));
$("#dlJson").addEventListener("click", () => downloadShared("json"));
$("#dlAnswers").addEventListener("click", downloadAnswers);

async function withdraw() {
  try { await post("/api/withdraw", {person_id: state.pid, consent_token: state.token}); } catch (e) {}
  const shares = loadShares();
  await Promise.all(shares.map((s) => revoke(s, null).catch(() => false)));
  // the interview's draft and agreement too (interview.js keys), so nothing of theirs stays in the saved progress
  for (const k of [HANDOFF, CONSENT, KIT, VOICE, "lumin8r-voice-typing-v1", "lumin8r-interview-consent-v1"]) { store.del("localStorage", k); store.del("sessionStorage", k); }
  try { await CTX.flush(); } catch (_) {}
  state.voiceFile = null; renderVoiceLine();
  state.token = ""; state.answers = null; state.result = null; state.consented = false;
  if (dlg.open) dlg.close();
  $("#connector").replaceChildren();
  document.querySelector(".pathbar").remove();
  $("#main").innerHTML = `<section class="done-banner panel spawn-in" aria-labelledby="wdH"><span class="eyebrow">Consent withdrawn</span><h1 id="wdH" tabindex="-1">Done. Thank you for trying lumin8r.</h1><p class="lead">Your withdrawal is recorded. Your saved answers and file are deleted from the server, this page is cleared${shares.length ? ", and your links from this device are turned off" : ""}. A file you already downloaded, or pasted into an AI model, cannot be recalled: delete any me.md you downloaded.</p><div class="btnrow"><a class="btn" href="/">Back to home</a></div></section>`;
  $("#wdH").focus();
}

/* ---------- your own words: the reviewed transcript from /interview ---------- */
function loadVoiceFile() {
  const v = store.get("sessionStorage", VOICE);
  return v && typeof v === "object" && Array.isArray(v.employee_turns) && v.employee_turns.some((t) => String(t && t.text || "").trim()) ? v : null;
}
// V IDs are positional over employee_turns, emptied turns included (intake.parse_transcript's rule)
function voiceTurn(id) {
  const turns = state.voiceFile ? state.voiceFile.employee_turns : [], t = turns[Number(id.slice(1)) - 1];
  return t && String(t.text || "").trim() ? t : null;
}
// the server refuses an interview recorded under another person code, so it is left out of the build and said so
function voiceMismatch() {
  const v = state.voiceFile, pid = state.answers && state.answers.person_id;
  return !!(v && v.person_id && pid && v.person_id !== pid);
}
function renderVoiceLine() {
  const v = state.voiceFile;
  $("#voiceLine").classList.toggle("hidden", !v);
  $("#interviewInvite").classList.toggle("hidden", !!v);
  if (!v) return;
  if (voiceMismatch()) { $("#voiceLineText").textContent = `Your interview is for ${v.person_id}, but these answers are for ${state.answers.person_id}, so it is not included.`; return; }
  const n = v.employee_turns.filter((t) => String(t && t.text || "").trim()).length;
  $("#voiceLineText").textContent = `Includes your interview (${n} ${n === 1 ? "answer" : "answers"}, ${VOICE_SOURCES[v.source] || "interview"}).`;
}
$("#voiceRemove").addEventListener("click", () => {
  store.del("sessionStorage", VOICE); state.voiceFile = null; renderVoiceLine();
  toast("Your interview is no longer part of your file.");
  if (state.consented && state.answers) regenSoon();
});

/* ---------- voice interview (ElevenLabs Agents, text only) ---------- */
let convo = null;
$("#voiceStart").addEventListener("click", async () => {
  try {
    if (!state.purposes.includes("voice_interview")) throw new Error("you did not agree to the voice interview");
    if (!window.ElevenLabsClient) await new Promise((ok, bad) => { const s = document.createElement("script"); s.src = "https://cdn.jsdelivr.net/npm/@elevenlabs/client@1.32.0/dist/lib.iife.js"; s.onload = ok; s.onerror = () => bad(new Error("the voice library did not load")); document.head.appendChild(s); });
    const {signed_url} = await post("/api/voice/session", {});
    convo = await window.ElevenLabsClient.Conversation.startSession({signedUrl: signed_url, onModeChange: (m) => { $("#voiceStatus").textContent = "The interviewer is " + (m.mode || m) + "."; }, onDisconnect: () => finishVoice()});
    $("#voiceStart").disabled = true; $("#voiceStop").disabled = false;
  } catch (err) { $("#voiceStatus").textContent = "The voice interview is unavailable: " + err.message + "."; }
});
$("#voiceStop").addEventListener("click", async () => { if (convo) await convo.endSession(); });
async function finishVoice() {
  if (!convo) return; const id = convo.getId(); convo = null; $("#voiceStop").disabled = true; $("#voiceStatus").textContent = "Fetching the transcript...";
  for (let i = 0; i < 20; i++) {
    const r = await fetch("/api/voice/transcript?conversation_id=" + encodeURIComponent(id)); const t = await r.json();
    if (t.status === "done" || t.status === "failed") {
      state.voice = t; const box = $("#voiceTranscript"); box.replaceChildren();
      const p = document.createElement("p"); p.className = "small"; p.textContent = `${t.employee_turns.length} answers, ${t.duration_seconds || "?"} seconds. Edit or delete any line before it is used.`; box.append(p);
      t.employee_turns.forEach((x, j) => { const row = ansRow("V" + String(j + 1).padStart(2, "0")); const ta = document.createElement("textarea"); ta.value = x.text; ta.addEventListener("input", () => { state.voice.employee_turns[j].text = ta.value; }); row.append(ta); box.append(row); });
      box.append(button("Download the reviewed transcript", "btn small", () => download("voice_transcript.json", JSON.stringify(Object.assign({person_id: state.pid}, state.voice), null, 2), "application/json")));
      $("#voiceStatus").textContent = "Done."; return;
    }
    await new Promise((r) => setTimeout(r, 3000));
  }
  $("#voiceStatus").textContent = "The transcript is not ready yet. Try again in a minute.";
}

/* ---------- start ---------- */
(async () => {
  await CTX.ready;
  state.remember = rememberOn();
  let config = {};
  try { const r = await fetch("/api/config"); if (r.ok) config = await r.json(); } catch (e) {}
  state.scopes = config.scopes || {coaching: "Choices, measured style and trait scores, without your own words.", full: "Everything, including your own words. For your own AI tools."};
  state.voiceEnabled = !!config.voice_enabled;
  // participants come from the assessment: no answer files, no example, no JSON downloads unless the team workspace is on
  const team = config.workbench_enabled === true;
  document.querySelectorAll(".team-only").forEach((el) => el.classList.toggle("hidden", !team));
  $("#voiceChoice").classList.toggle("hidden", !state.voiceEnabled);
  renderScopes();
  // answers handed over by the assessment (this tab), or remembered on this device
  const handoff = store.get("sessionStorage", HANDOFF) || (state.remember ? store.get("localStorage", HANDOFF) : null);
  if (handoff && handoff.answers && typeof handoff.answers === "object") {
    state.answers = normalize(handoff.answers); state.from = handoff.from || "";
    state.claimQuestions = handoff.claim_questions && typeof handoff.claim_questions === "object" ? handoff.claim_questions : {};
    state.notes = Array.isArray(handoff.twin_reactions) ? handoff.twin_reactions : [];
    if (handoff.person_id) $("#pid").value = handoff.person_id;
    const n = state.answers.items.length + state.answers.scenarios.length + state.answers.writing.length;
    const note = $("#handoffNote"); note.classList.remove("hidden");
    note.textContent = `Your ${n} answers${handoff.person_id ? " for " + handoff.person_id : ""} are ready${handoff.from === "assessment" ? " from the assessment" : ""}. Read the agreement below and agree to open your file.`;
  }
  const consent = store.get("sessionStorage", CONSENT) || (state.remember ? store.get("localStorage", CONSENT) : null);
  if (consent && consent.token) {
    state.consented = true; state.token = consent.token; state.pid = consent.pid || ""; state.purposes = consent.purposes || []; state.receiptAt = consent.at || "";
    $("#pid").value = state.pid; document.querySelectorAll(".purpose").forEach((c) => { c.checked = state.purposes.includes(c.value); });
    $("#voiceBox").classList.toggle("hidden", !(state.voiceEnabled && state.purposes.includes("voice_interview")));
  }
  state.voiceFile = loadVoiceFile(); renderVoiceLine();
  agreeHint();
  await initTwin(config);
  updateTwin();
  go(location.hash.slice(1) || "agree");
  if (state.consented && state.answers) regen();
})();
})();
