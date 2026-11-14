/* Copyright (c) 2026 William Chesher. MIT License, see LICENSE. */
/* interview.js - Tell it in your own words (/interview): agree, choose a way (talk with the AI interviewer through
   ElevenLabs, bring a Plaud transcript, or type), review every answer, then hand the reviewed transcript to Your file
   through the saved progress on the server (context.js, key VOICE_KEY) or download it as voice_transcript.json.

   The transcript shape is what intake.parse_transcript reads:
     {person_id, conversation_id, duration_seconds, source, employee_turns: [{index, seconds, text}],
      interviewer_turns: [{index, text}]}
   plus minutes and review_seconds, so the team can compare effort between the three ways.
   An answer emptied in review stays in employee_turns with empty text: intake numbers answers by position and drops
   empty ones WITHOUT renumbering, so V03 always names the answer the person reviewed as V03.
   Text only: nothing here reads, measures or keeps audio. */
(() => {
"use strict";

// storage keys. CONSENT and REMEMBER are Your file's (app.js); this page reads them for the person code and never
// overwrites them, so a token Your file holds keeps its own purposes. This page's own agreement lives in OWN_CONSENT.
const VOICE_KEY = "lumin8r-voice-v1", TYPING_KEY = "lumin8r-voice-typing-v1", OWN_CONSENT = "lumin8r-interview-consent-v1";
const CONSENT = "lumin8r-consent-v1", HANDOFF = "lumin8r-answers-v1", REMEMBER = "lumin8r-remember";
const VOICE_CLIENT = "https://cdn.jsdelivr.net/npm/@elevenlabs/client@1.32.0/dist/lib.iife.js";
const MAX_TRANSCRIPT_BYTES = 400000; // the server takes at most 512 KB per request
const POLL_MS = 3000, POLL_TRIES = 40; // about two minutes for ElevenLabs to finish the transcript
const SOURCE_NAMES = {elevenlabs: "talked with the AI interviewer", plaud: "Plaud recording", typed: "typed"};

const $ = (s) => document.querySelector(s);
const calm = () => !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
// saved progress on the server (context.js): nothing is kept in browser storage
const store = {
  get(area, key) { try { const v = CTX[area].getItem(key); return v ? JSON.parse(v) : null; } catch (_) { return null; } },
  set(area, key, value) { try { CTX[area].setItem(key, JSON.stringify(value)); return true; } catch (_) { return false; } },
  del(area, key) { try { CTX[area].removeItem(key); } catch (_) {} },
};
const remembered = () => { try { return CTX.localStorage.getItem(REMEMBER) === "1"; } catch (_) { return false; } };

const state = {
  step: "intro", way: "", resume: "", pid: "", token: "", purposes: [], voiceEnabled: false, workbench: false,
  guide: [], typed: null, transcript: null, reviewStartedAt: 0, convo: null, talkStartedAt: 0, timer: 0, ending: false,
};

/* ---------- small helpers ---------- */
function el(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; }
function vid(position) { return "V" + String(position + 1).padStart(2, "0"); }
function clock(seconds) { const s = Math.max(0, Math.round(seconds)); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); }
function minutesText(seconds) {
  if (!(seconds > 0)) return "time not recorded";
  const m = Math.round(seconds / 60);
  return m < 1 ? "under a minute" : m === 1 ? "about 1 minute" : `about ${m} minutes`;
}
function announce(text) { const a = $("#announce"); a.textContent = ""; setTimeout(() => { a.textContent = text; }, 30); }
function toast(text) {
  const t = el("div", "toast", text); $("#toasts").append(t);
  setTimeout(() => { t.classList.add("out"); setTimeout(() => t.remove(), calm() ? 0 : 320); }, 3600);
}
function status(where, kind, text, action) {
  const box = $(where); box.replaceChildren();
  if (!text) return;
  const p = el("p", "notice" + (kind ? " " + kind : ""), text);
  if (action) { p.append(" "); const b = el("button", "btn link", action.label); b.type = "button"; b.addEventListener("click", action.run); p.append(b); }
  box.append(p);
}

/* ---------- the server: every failure becomes a calm sentence ---------- */
async function call(method, url, body) {
  const headers = {"Accept": "application/json"};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (state.token) headers["X-Consent-Token"] = state.token;
  let r;
  try { r = await fetch(url, {method, headers, body: body === undefined ? undefined : JSON.stringify(body)}); }
  catch (_) { const e = new Error("We could not reach the server. Check your connection and try again."); e.status = 0; throw e; }
  let j = null; try { j = await r.json(); } catch (_) {}
  if (r.ok) return j;
  const reason = j && typeof j.error === "string" ? j.error : "";
  const e = new Error(kindly(r.status, reason, j && j.purpose)); e.status = r.status; e.purpose = j && j.purpose; throw e;
}
function kindly(code, reason, purpose) {
  if (code === 403) {
    return purpose === "voice_interview"
      ? "Talking with the AI interviewer, or bringing a Plaud transcript, needs your agreement to choice 2. Go back to the agreement and tick it, or type your answers instead."
      : "Your agreement needs renewing (the server may have restarted). Agree again; nothing you wrote here is lost.";
  }
  if (code === 400) return "That did not work: " + (reason || "the server could not read it") + ".";
  if (code === 404) return "This step is not available on this server yet. Try another way.";
  if (code === 502 || code === 503) return "The service behind this step did not answer" + (reason ? " (" + reason + ")" : "") + ". Your answers are safe here; try again in a minute.";
  return "Something went wrong (the server answered " + code + "). Please try again.";
}
function consentAction(e) {
  return e && e.status === 403 ? {label: "Go to the agreement", run: () => { state.resume = state.step === "intro" ? "" : currentSection(); go("intro"); }} : null;
}

/* ---------- steps ---------- */
const SECTIONS = ["intro", "choose", "talk", "plaud", "type", "review", "done"];
const STATION = {intro: "intro", choose: "choose", talk: "answer", plaud: "answer", type: "answer", review: "review", done: "done"};
const ORDER = ["intro", "choose", "answer", "review", "done"];
function currentSection() { return SECTIONS.find((s) => !$("#s-" + s).hidden) || "intro"; }
function go(section) {
  for (const s of SECTIONS) $("#s-" + s).hidden = s !== section;
  state.step = section;
  const at = ORDER.indexOf(STATION[section]);
  document.querySelectorAll("#stations .st").forEach((n) => {
    const i = ORDER.indexOf(n.dataset.step);
    n.classList.toggle("on", i === at); n.classList.toggle("done", i < at);
    if (i === at) n.setAttribute("aria-current", "step"); else n.removeAttribute("aria-current");
  });
  const heading = $("#s-" + section + " h1");
  if (heading) heading.focus({preventScroll: true});
  window.scrollTo({top: 0, behavior: calm() ? "auto" : "smooth"});
}
document.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", () => go(b.dataset.go)));

/* ---------- 1 agree ---------- */
function agreeReady() {
  const pid = $("#pid").value.trim(), ok = pid.length > 0 && $("#c-build").checked;
  $("#agreeBtn").disabled = !ok;
  $("#agreeHint").textContent = ok ? "" : pid ? "Tick choice 1 to continue." : "Type your person code and tick choice 1 to continue.";
}
$("#pid").addEventListener("input", agreeReady);
$("#c-build").addEventListener("change", agreeReady);
$("#agreeBtn").addEventListener("click", async () => {
  const b = $("#agreeBtn"), pid = $("#pid").value.trim();
  const purposes = ["build_profile"].concat($("#c-voice").checked ? ["voice_interview"] : []);
  b.disabled = true; b.setAttribute("aria-busy", "true"); b.textContent = "Recording your agreement...";
  try {
    const r = await call("POST", "/api/consent", {person_id: pid, purposes,
      ai_services: purposes.includes("voice_interview") ? ["ElevenLabs (voice interview, AI interviewer and transcription)"] : [], share_with: []});
    state.pid = pid; state.purposes = purposes; state.token = (r && r.consent_token) || "";
    store.set("sessionStorage", OWN_CONSENT, {pid, token: state.token, purposes, at: (r && r.receipt && r.receipt.at) || new Date().toISOString()});
    $("#agreeStatus").textContent = "";
    renderWays();
    const back = state.resume; state.resume = "";
    go(back || "choose");
    toast("Agreement recorded.");
  } catch (e) {
    $("#agreeStatus").textContent = "Your agreement was not recorded. " + e.message;
  } finally { b.removeAttribute("aria-busy"); b.textContent = "Agree and continue"; agreeReady(); }
});

/* ---------- 2 choose a way ---------- */
function renderWays() {
  const talk = $("#way-talk"), btn = $("#pickTalk"), chip = $("#talkChip"), text = $("#talkText");
  const agreed = state.purposes.includes("voice_interview");
  talk.classList.toggle("off", !state.voiceEnabled || !agreed);
  btn.hidden = false;
  if (!state.voiceEnabled) {
    chip.textContent = "Unavailable right now";
    text.textContent = "Talking with the AI interviewer is switched off on this server today. You can bring a Plaud transcript or type your answers instead.";
    btn.hidden = true;
  } else if (!agreed) {
    chip.textContent = "Needs your agreement";
    text.textContent = "To talk with the AI interviewer, tick choice 2 in the agreement. ElevenLabs runs the interviewer and turns the conversation into text; recording is off.";
    btn.textContent = "Go to the agreement"; btn.className = "btn";
  } else {
    chip.textContent = "About 10 minutes";
    text.textContent = "A calm spoken conversation. The AI interviewer asks each question and may ask one short follow-up. Your browser will ask to use the microphone.";
    btn.textContent = "Start talking"; btn.className = "btn primary";
  }
  // the server reads a Plaud transcript under the same voice_interview agreement
  const plaud = $("#way-plaud"), pbtn = $("#pickPlaud");
  plaud.classList.toggle("off", !agreed);
  $("#plaudChip").textContent = agreed ? "Recorded in person" : "Needs your agreement";
  $("#plaudCardText").textContent = agreed
    ? "Had the interview in person with a Plaud recorder? Bring its text transcript, then choose which speaker is you."
    : "Had the interview in person with a Plaud recorder? To bring its transcript, tick choice 2 in the agreement.";
  pbtn.textContent = agreed ? "Bring a transcript" : "Go to the agreement";
}
$("#pickTalk").addEventListener("click", () => {
  if (!state.purposes.includes("voice_interview")) { state.resume = "choose"; go("intro"); $("#c-voice").focus(); return; }
  state.way = "elevenlabs"; resetTalk(); go("talk");
});
$("#pickPlaud").addEventListener("click", () => {
  if (!state.purposes.includes("voice_interview")) { state.resume = "choose"; go("intro"); $("#c-voice").focus(); return; }
  state.way = "plaud"; go("plaud");
});
$("#pickType").addEventListener("click", () => { state.way = "typed"; startTyping(); });

/* ---------- 3a talk (ElevenLabs Agents) ---------- */
function loadVoiceClient() {
  if (window.ElevenLabsClient) return Promise.resolve();
  return new Promise((ok, bad) => {
    const s = document.createElement("script"); s.src = VOICE_CLIENT; s.async = true;
    s.onload = () => window.ElevenLabsClient ? ok() : bad(new Error("The voice service did not load. Try again, or choose another way."));
    s.onerror = () => bad(new Error("The voice service did not load. Check your connection, or choose another way."));
    document.head.append(s);
  });
}
function setMode(mode, words) { $("#live").dataset.mode = mode; $("#liveState").textContent = words; }
function resetTalk() {
  setMode("idle", "Not started"); $("#liveElapsed").textContent = "0:00";
  $("#talkStart").hidden = false; $("#talkStart").disabled = false; $("#talkEnd").hidden = true; status("#talkStatus");
}
function tick() { $("#liveElapsed").textContent = clock((Date.now() - state.talkStartedAt) / 1000); }
$("#talkStart").addEventListener("click", async () => {
  const b = $("#talkStart"); b.disabled = true; b.setAttribute("aria-busy", "true"); status("#talkStatus");
  setMode("idle", "Getting ready...");
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) throw new Error("This browser cannot use a microphone here. Choose another way, or open the page over https.");
    try { const stream = await navigator.mediaDevices.getUserMedia({audio: true}); stream.getTracks().forEach((t) => t.stop()); }
    catch (_) { throw new Error("The microphone is not available. Allow it in your browser settings, or choose another way."); }
    await loadVoiceClient();
    const session = await call("POST", "/api/voice/session", {});
    if (!session || !session.signed_url) throw new Error("The voice service did not start a conversation. Try again in a minute.");
    state.ending = false;
    state.convo = await window.ElevenLabsClient.Conversation.startSession({
      signedUrl: session.signed_url,
      onConnect: () => setMode("listening", "Connected. The AI interviewer will begin."),
      onModeChange: (m) => { const mode = (m && m.mode) || m; setMode(mode === "speaking" ? "speaking" : "listening", mode === "speaking" ? "The AI interviewer is speaking" : "Listening to you"); },
      onError: () => status("#talkStatus", "warn", "The connection had a problem. If the conversation stopped, your transcript so far is still saved."),
      onDisconnect: () => endTalk(),
    });
    state.talkStartedAt = Date.now(); clearInterval(state.timer); state.timer = setInterval(tick, 1000);
    b.hidden = true; $("#talkEnd").hidden = false; $("#talkEnd").focus();
    announce("The conversation has started.");
  } catch (e) {
    setMode("idle", "Not started");
    status("#talkStatus", "warn", e.message, consentAction(e));
  } finally { b.disabled = false; b.removeAttribute("aria-busy"); }
});
$("#talkEnd").addEventListener("click", async () => {
  $("#talkEnd").disabled = true;
  try { if (state.convo) await state.convo.endSession(); } catch (_) {}
  endTalk();
});
$("#talkBack").addEventListener("click", async () => {
  if (state.convo) { try { await state.convo.endSession(); } catch (_) {} }
  go("choose");
});
async function endTalk() {
  if (state.ending || !state.convo) return;
  state.ending = true;
  const convo = state.convo; state.convo = null; clearInterval(state.timer);
  let id = ""; try { id = convo.getId(); } catch (_) {}
  const measured = state.talkStartedAt ? Math.round((Date.now() - state.talkStartedAt) / 1000) : null;
  $("#talkEnd").hidden = true; $("#talkEnd").disabled = false;
  setMode("idle", "Conversation ended");
  if (!id) { status("#talkStatus", "warn", "The conversation ended before it started, so there is no transcript. Start again when you are ready."); $("#talkStart").hidden = false; return; }
  await fetchTranscript(id, measured);
}
async function fetchTranscript(id, measured) {
  status("#talkStatus", "", "Saving your transcript. This usually takes under a minute...");
  for (let i = 0; i < POLL_TRIES; i++) {
    try {
      const t = await call("GET", "/api/voice/transcript?conversation_id=" + encodeURIComponent(id));
      if (t && t.status === "failed") throw Object.assign(new Error("ElevenLabs could not finish the transcript. Please try the conversation again, or choose another way."), {status: 0});
      if (t && (t.status === "done" || (t.status === undefined && Array.isArray(t.employee_turns)))) {
        state.transcript = {
          person_id: state.pid, conversation_id: t.conversation_id || id,
          duration_seconds: typeof t.duration_seconds === "number" ? t.duration_seconds : measured,
          source: "elevenlabs", employee_turns: cleanEmployee(t.employee_turns), interviewer_turns: cleanInterviewer(t.interviewer_turns),
          deleted: typeof t.deleted === "boolean" ? t.deleted : null,
          ...(t.delete_error ? {delete_error: String(t.delete_error)} : {}),
        };
        status("#talkStatus");
        return openReview();
      }
    } catch (e) {
      if (e.status === 403 || e.status === 400 || e.status === 404 || e.status === 0) {
        return status("#talkStatus", "warn", e.message, e.status === 403 ? consentAction(e) : {label: "Try again", run: () => fetchTranscript(id, measured)});
      }
      if (i >= 4) return status("#talkStatus", "warn", e.message, {label: "Try again", run: () => fetchTranscript(id, measured)});
    }
    await new Promise((r) => setTimeout(r, POLL_MS));
  }
  status("#talkStatus", "warn", "The transcript is not ready yet. It is kept safe at ElevenLabs until it is saved here.", {label: "Check again", run: () => fetchTranscript(id, measured)});
}
function cleanEmployee(turns) {
  return (Array.isArray(turns) ? turns : []).map((t, i) => ({
    index: Number.isInteger(t && t.index) ? t.index : i,
    seconds: typeof (t && t.seconds) === "number" ? t.seconds : null,
    text: String((t && t.text) || "").trim(),
  }));
}
function cleanInterviewer(turns) {
  return (Array.isArray(turns) ? turns : []).filter((t) => t && Number.isInteger(t.index)).map((t) => ({index: t.index, text: String(t.text || "").trim()}));
}

/* ---------- 3b Plaud ---------- */
let plaudSpeakers = [];
$("#plaudFile").addEventListener("change", async (e) => {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  if (file.size > MAX_TRANSCRIPT_BYTES) { status("#plaudStatus", "warn", "That file is larger than a ten-minute transcript should be (over 400 KB). Choose the text export, not the audio."); return; }
  try {
    $("#plaudText").value = await file.text();
    $("#plaudFileName").textContent = file.name;
    status("#plaudStatus"); hideSpeakers();
    announce("Transcript loaded from " + file.name + ".");
  } catch (_) { status("#plaudStatus", "warn", "That file could not be read. Open it and paste the text instead."); }
});
$("#plaudText").addEventListener("input", hideSpeakers);
function hideSpeakers() { $("#plaudSpeakers").hidden = true; plaudSpeakers = []; }
$("#plaudRead").addEventListener("click", async () => {
  const text = $("#plaudText").value.trim(), b = $("#plaudRead");
  if (!text) { status("#plaudStatus", "warn", "Choose a transcript file or paste its text first."); $("#plaudText").focus(); return; }
  if (new Blob([text]).size > MAX_TRANSCRIPT_BYTES) { status("#plaudStatus", "warn", "That transcript is longer than this interview needs (over 400 KB). Trim it to the interview and try again."); return; }
  b.disabled = true; b.setAttribute("aria-busy", "true"); status("#plaudStatus");
  try {
    const r = await call("POST", "/api/voice/plaud", {text, person_id: state.pid});
    plaudSpeakers = (r && Array.isArray(r.speakers)) ? r.speakers : [];
    if (!plaudSpeakers.length) throw Object.assign(new Error("No speakers were found. Export the transcript again with speaker labels turned on."), {status: 400});
    renderSpeakers();
  } catch (e) { status("#plaudStatus", "warn", e.message, consentAction(e)); }
  finally { b.disabled = false; b.removeAttribute("aria-busy"); }
});
function renderSpeakers() {
  const list = $("#speakerList"); list.replaceChildren();
  plaudSpeakers.forEach((s, i) => {
    const label = el("label", "choicecard");
    const input = el("input"); input.type = "radio"; input.name = "speaker"; input.value = String(s.label); input.id = "speaker-" + i;
    input.addEventListener("change", () => { $("#plaudUse").disabled = false; });
    const body = el("span");
    const turns = Number(s.turns) || 0;
    body.append(el("b", "", String(s.label)), document.createTextNode(` · ${turns} ${turns === 1 ? "turn" : "turns"}`));
    if (s.sample) { const sample = el("span", "sample"); const q = el("q", "", String(s.sample)); sample.append(q); body.append(sample); }
    label.append(input, body); list.append(label);
  });
  $("#plaudUse").disabled = true;
  $("#plaudSpeakers").hidden = false;
  const first = list.querySelector("input"); if (first) first.focus();
  announce(`${plaudSpeakers.length} speakers found. Choose which one is you.`);
}
$("#plaudUse").addEventListener("click", async () => {
  const picked = document.querySelector("input[name=speaker]:checked"), b = $("#plaudUse");
  if (!picked) return;
  b.disabled = true; b.setAttribute("aria-busy", "true"); status("#plaudStatus");
  try {
    const r = await call("POST", "/api/voice/plaud", {text: $("#plaudText").value.trim(), speaker: picked.value, person_id: state.pid});
    const t = (r && r.transcript) || r || {};
    const employee = cleanEmployee(t.employee_turns);
    if (!employee.length) throw Object.assign(new Error("That speaker has no lines to use. Choose the other speaker."), {status: 400});
    state.transcript = {
      person_id: state.pid, conversation_id: t.conversation_id || ("plaud-" + Date.now().toString(36)),
      duration_seconds: typeof t.duration_seconds === "number" ? t.duration_seconds : null,
      source: "plaud", employee_turns: employee, interviewer_turns: cleanInterviewer(t.interviewer_turns),
    };
    openReview();
  } catch (e) { status("#plaudStatus", "warn", e.message, consentAction(e)); }
  finally { b.disabled = false; b.removeAttribute("aria-busy"); }
});

/* ---------- 3c type ---------- */
async function startTyping() {
  go("type");
  if (!state.guide.length) {
    $("#typeQuestion").textContent = "Loading the questions...";
    $("#typeAnswer").disabled = true; $("#typeNext").disabled = true; $("#typeSkip").disabled = true; $("#typeBack").disabled = true;
    try {
      const r = await call("GET", "/api/voice/guide");
      const list = Array.isArray(r) ? r : (r && (r.questions || r.guide)) || [];
      state.guide = list.filter((q) => q && q.key && q.question).map((q) => ({key: String(q.key), question: String(q.question)}));
      if (!state.guide.length) throw Object.assign(new Error("The questions did not load. Try again in a minute."), {status: 502});
    } catch (e) {
      $("#typeQuestion").textContent = "The questions could not load.";
      status("#typeStatus", "warn", e.message, consentAction(e) || {label: "Try again", run: () => { status("#typeStatus"); startTyping(); }});
      return;
    }
    status("#typeStatus");
  }
  const draft = store.get("sessionStorage", TYPING_KEY);
  const sameGuide = draft && Array.isArray(draft.answers) && draft.answers.length === state.guide.length && draft.pid === state.pid;
  state.typed = sameGuide ? draft : {pid: state.pid, at: 0, startedAt: Date.now(), answers: state.guide.map(() => ({text: "", skipped: false, seconds: null}))};
  if (sameGuide) toast("Picked up where you left off.");
  showQuestion(state.typed.at || 0);
}
function saveTyping() { store.set("sessionStorage", TYPING_KEY, state.typed); }
function showQuestion(i) {
  const t = state.typed, total = state.guide.length;
  t.at = Math.max(0, Math.min(i, total - 1));
  const q = state.guide[t.at], a = t.answers[t.at];
  $("#typeCount").textContent = `Question ${t.at + 1} of ${total}`;
  $("#typeBar").style.width = Math.round((t.at / total) * 100) + "%";
  $("#typeQuestion").textContent = q.question;
  const box = $("#typeAnswer"); box.disabled = false; box.value = a.text;
  $("#typeBack").disabled = t.at === 0;
  $("#typeSkip").disabled = false; $("#typeNext").disabled = false;
  $("#typeNext").textContent = t.at === total - 1 ? "Finish and review" : "Next question";
  $("#typeSaved").textContent = a.skipped ? "Skipped" : "";
  saveTyping();
  box.focus({preventScroll: true});
}
function elapsed() { return Math.round((Date.now() - state.typed.startedAt) / 1000); }
$("#typeAnswer").addEventListener("input", (e) => {
  const a = state.typed.answers[state.typed.at]; a.text = e.target.value; a.skipped = false; $("#typeSaved").textContent = ""; saveTyping();
});
$("#typeBack").addEventListener("click", () => showQuestion(state.typed.at - 1));
$("#typeSkip").addEventListener("click", () => {
  const a = state.typed.answers[state.typed.at]; a.text = ""; a.skipped = true; a.seconds = null; advance();
});
$("#typeNext").addEventListener("click", () => {
  const a = state.typed.answers[state.typed.at]; a.text = $("#typeAnswer").value; a.skipped = !a.text.trim(); a.seconds = a.skipped ? null : elapsed(); advance();
});
$("#typeLeave").addEventListener("click", () => go("choose"));
function advance() {
  saveTyping();
  if (state.typed.at < state.guide.length - 1) { showQuestion(state.typed.at + 1); announce($("#typeCount").textContent); return; }
  finishTyping();
}
function finishTyping() {
  const t = state.typed, employee = [], interviewer = [];
  let index = 0;
  t.answers.forEach((a, i) => {
    if (a.skipped || !a.text.trim()) return; // a skipped question was never answered, so it is not in the transcript
    interviewer.push({index: index++, text: state.guide[i].question});
    employee.push({index: index++, seconds: a.seconds, text: a.text.trim()});
  });
  if (!employee.length) { status("#typeStatus", "warn", "You skipped every question, so there is nothing to add. Answer at least one, or choose another way."); return; }
  status("#typeStatus");
  state.transcript = {person_id: state.pid, conversation_id: "typed-" + Date.now().toString(36), duration_seconds: elapsed(),
    source: "typed", employee_turns: employee, interviewer_turns: interviewer};
  openReview();
}

/* ---------- 4 review ---------- */
function askedBefore(index) {
  let asked = "";
  for (const q of state.transcript.interviewer_turns) { if (q.index < index && q.text) asked = q.text; else if (q.index >= index) break; }
  return asked;
}
function openReview() {
  const t = state.transcript;
  t.interviewer_turns.sort((a, b) => a.index - b.index);
  state.reviewStartedAt = Date.now();
  renderReview();
  go("review");
}
function renderReview() {
  const t = state.transcript, list = $("#turnList"); list.replaceChildren();
  $("#reviewSttNote").hidden = t.source === "typed";
  t.employee_turns.forEach((turn, position) => {
    const li = el("li", "turn"), id = vid(position);
    const tag = el("span", "vid", id); tag.setAttribute("aria-hidden", "true");
    const body = el("div", "body");
    const asked = askedBefore(turn.index);
    const label = el("label", "asked", asked ? "Answering: " + asked : "Answer");
    const box = el("textarea"); box.id = "turn-" + position; label.htmlFor = box.id;
    box.setAttribute("aria-label", `${id}, your answer${asked ? " to: " + asked : ""}`);
    box.value = turn.text; box.dataset.position = String(position);
    const row = el("div", "row");
    const note = el("span", "small");
    const remove = el("button", "btn small ghost danger", "Remove this answer"); remove.type = "button";
    remove.setAttribute("aria-label", "Remove answer " + id);
    const undo = el("button", "btn small", "Put it back"); undo.type = "button";
    undo.setAttribute("aria-label", "Put answer " + id + " back");
    let before = "";
    const sync = () => {
      turn.text = box.value;
      const gone = !box.value.trim();
      li.classList.toggle("removed", gone);
      note.textContent = gone ? `Removed. ${id} will not be used; the other numbers stay the same.` : turn.seconds != null ? "At " + clock(turn.seconds) : "";
      remove.hidden = gone;
      undo.hidden = !(gone && before);
      renderSummary();
    };
    box.addEventListener("input", sync);
    remove.addEventListener("click", () => { before = box.value; box.value = ""; sync(); undo.focus(); announce(`${id} removed.`); });
    undo.addEventListener("click", () => { box.value = before; before = ""; sync(); box.focus(); announce(`${id} is back.`); });
    row.append(note, remove, undo);
    body.append(label, box, row);
    li.append(tag, body);
    list.append(li);
    sync();
  });
}
function kept() { return state.transcript.employee_turns.filter((t) => String(t.text || "").trim()).length; }
function chips(where, extra) {
  const t = state.transcript, box = $(where); box.replaceChildren();
  const n = kept();
  for (const text of [`${n} ${n === 1 ? "answer" : "answers"} to use`, "Time taken: " + minutesText(t.duration_seconds), SOURCE_NAMES[t.source]].concat(extra || [])) {
    box.append(el("span", "chip", text));
  }
}
function renderSummary() {
  chips("#reviewSummary");
  const n = kept();
  $("#reviewSave").disabled = n === 0;
  $("#reviewHint").textContent = n === 0 ? "Every answer is removed, so there is nothing to save. Put an answer back, or leave this page." : "";
}
$("#reviewSave").addEventListener("click", () => {
  const t = state.transcript;
  t.employee_turns.forEach((turn) => { turn.text = String(turn.text || "").trim(); });
  t.minutes = t.duration_seconds > 0 ? Math.round(t.duration_seconds / 6) / 10 : null;
  t.review_seconds = Math.round((Date.now() - state.reviewStartedAt) / 1000);
  t.reviewed_at = new Date().toISOString();
  t.person_id = state.pid || t.person_id;
  const saved = store.set("sessionStorage", VOICE_KEY, t);
  store.del("sessionStorage", TYPING_KEY);
  renderDone(saved);
  go("done");
});

/* ---------- 5 done ---------- */
function renderDone(saved) {
  const t = state.transcript;
  chips("#doneSummary", t.review_seconds ? ["Review: " + minutesText(t.review_seconds)] : []);
  $("#doneLead").textContent = saved
    ? "They are saved in this browser tab only. Add them to your file, or keep a copy for yourself."
    : "This browser would not save them, so add them to your file from the download: keep a copy now.";
  $("#addToFile").hidden = !saved;
  $("#hubBox").hidden = !state.workbench;
  $("#hubCode").textContent = state.pid || t.person_id || "";
  status("#hubStatus");
  const notes = [];
  if (t.source === "elevenlabs") {
    notes.push(t.deleted === true ? "ElevenLabs deleted the conversation after your transcript was saved."
      : t.deleted === false ? "The conversation could not be deleted from ElevenLabs just now" + (t.delete_error ? " (" + t.delete_error + ")" : "") + ". It holds no recording, only the text, until it is deleted; ask the team to delete it."
      : "Deletion of the conversation at ElevenLabs was not confirmed to this page.");
  }
  notes.push("Removed answers stay out of your file, and nothing about your tone of voice was used.");
  $("#doneNote").textContent = notes.join(" ");
}
/* workbench only: hand the reviewed transcript to the team hub (team sign-in cookie), behind its leakage guard */
$("#hubSend").addEventListener("click", async () => {
  const b = $("#hubSend"), t = state.transcript;
  b.disabled = true; b.setAttribute("aria-busy", "true"); status("#hubStatus");
  let r, j = {};
  try {
    r = await fetch("/api/team/voice", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({code: state.pid || t.person_id, transcript: t})});
    try { j = await r.json(); } catch (_) {}
  } catch (_) { r = null; }
  b.disabled = false; b.removeAttribute("aria-busy");
  if (!r) return status("#hubStatus", "warn", "We could not reach the server. Check your connection and try again.");
  if (r.ok) {
    const i = j.interview || {}, n = Number(i.employee_answers) || 0;
    const mins = typeof i.interview_minutes === "number" ? `, ${i.interview_minutes} minutes` : "";
    return status("#hubStatus", "ok", `Sent to the team hub: ${n} ${n === 1 ? "answer" : "answers"}${mins}, ${SOURCE_NAMES[i.source] || i.source || "interview"}. The leakage check ${i.leakage_guard === "passed" ? "passed" : "result: " + i.leakage_guard}.`);
  }
  if (r.status === 404 && j.error === "not available") { state.workbench = false; $("#hubBox").hidden = true; return; }
  if (r.status === 401) {
    status("#hubStatus", "warn", "Sign in to the team hub first.");
    const p = $("#hubStatus .notice"), a = el("a", "", "Open the team hub"); a.href = "/workbench"; p.append(" ", a, ", then send again.");
    return;
  }
  const guard = j.leakage_guard;
  if (r.status === 400 && guard && (guard.test_ids_found || guard.quotes_found)) return renderLeaks(guard);
  status("#hubStatus", "warn", j.error ? "The team hub did not take it: " + j.error : kindly(r.status, "", ""));
});
function renderLeaks(guard) {
  const box = $("#hubStatus"); box.replaceChildren();
  const wrap = el("div", "notice warn");
  wrap.append(el("p", "", "Some interview answers repeat assessment answers that are kept aside, so this interview cannot be sent yet. Edit or remove each one below in review, save, and send again."));
  const list = el("ul", "howto");
  const hits = (guard.test_ids_found || []).map((h) => ({turn: h.turn, what: "mentions a question that is kept aside"}))
    .concat((guard.quotes_found || []).map((h) => ({turn: h.turn, what: "repeats words from an answer that is kept aside"})));
  for (const hit of hits) {
    const li = el("li"), m = /V(\d+)/.exec(String(hit.turn || ""));
    if (m) {
      const id = "V" + m[1], position = Number(m[1]) - 1;
      li.append(el("b", "", id), document.createTextNode(" " + hit.what + ". "));
      const jump = el("button", "btn link", "Go to " + id); jump.type = "button";
      jump.addEventListener("click", () => {
        go("review");
        const turn = $("#turn-" + position);
        if (turn) { turn.focus(); turn.scrollIntoView({block: "center", behavior: calm() ? "auto" : "smooth"}); }
      });
      li.append(jump);
    } else li.textContent = `A question in the transcript (${hit.turn}) ${hit.what}.`;
    list.append(li);
  }
  wrap.append(list); box.append(wrap);
  const first = box.querySelector("button"); if (first) first.focus();
}
$("#download").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(state.transcript, null, 2) + "\n"], {type: "application/json"});
  const a = el("a"); a.href = URL.createObjectURL(blob); a.download = "voice_transcript.json";
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  toast("Downloaded voice_transcript.json.");
});
$("#startOver").addEventListener("click", () => {
  store.del("sessionStorage", VOICE_KEY); store.del("sessionStorage", TYPING_KEY);
  state.transcript = null; state.typed = null; go("choose");
});

/* ---------- start ---------- */
(async () => {
  await CTX.ready;
  let config = {};
  try { const r = await fetch("/api/config"); if (r.ok) config = await r.json(); } catch (_) {}
  state.voiceEnabled = !!config.voice_enabled;
  state.workbench = config.workbench_enabled === true;
  const own = store.get("sessionStorage", OWN_CONSENT);
  const app = store.get("sessionStorage", CONSENT) || (remembered() ? store.get("localStorage", CONSENT) : null);
  const handoff = store.get("sessionStorage", HANDOFF) || (remembered() ? store.get("localStorage", HANDOFF) : null);
  $("#pid").value = (own && own.pid) || (app && app.pid) || (handoff && handoff.person_id) || "";
  if (own && own.token) {
    state.pid = own.pid; state.token = own.token; state.purposes = Array.isArray(own.purposes) ? own.purposes : [];
    $("#c-build").checked = state.purposes.includes("build_profile");
    $("#c-voice").checked = state.purposes.includes("voice_interview");
  }
  agreeReady(); renderWays();
  const saved = store.get("sessionStorage", VOICE_KEY);
  if (own && own.token && saved && Array.isArray(saved.employee_turns)) { state.transcript = saved; state.reviewStartedAt = Date.now() - (Number(saved.review_seconds) || 0) * 1000; renderReview(); renderDone(true); go("done"); }
  else if (own && own.token) go("choose");
  else go("intro");
})();
})();
