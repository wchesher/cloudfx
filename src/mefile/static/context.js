/* Copyright (c) 2026 William Chesher. MIT License, see LICENSE. */
/* context.js - saved progress on the server (context.py). The pages keep nothing in browser storage: this gives them
   two Storage-like objects, CTX.localStorage and CTX.sessionStorage, held in memory and saved to /api/context on every
   change, keyed by an HttpOnly cookie that carries no content. Load it before the page's own script and await CTX.ready
   before the first read. CTX.flush() resolves once every change is on the server (await it before navigating). */
(() => {
"use strict";
const items = Object.create(null);   // "<area>:<key>" -> string
const pending = Object.create(null); // "<area>:<key>" -> string | null, not yet sent
let timer = 0, inflight = Promise.resolve(), resume = "", status = "loading";
const DEBOUNCE_MS = 400, KEEPALIVE_MAX = 60000;

function send(keepalive) {
  clearTimeout(timer); timer = 0;
  const batch = Object.assign({}, pending);
  for (const k of Object.keys(batch)) delete pending[k];
  if (!Object.keys(batch).length) return inflight;
  const body = JSON.stringify({set: batch});
  const go = () => fetch("/api/context", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json"},
    body, keepalive: !!keepalive && body.length < KEEPALIVE_MAX}).then((r) => {
      if (!r.ok) throw new Error("the server answered " + r.status);
      setStatus("saved");
    }).catch(() => {
      // put the batch back unless a newer change replaced it, and try again shortly
      for (const k of Object.keys(batch)) if (!(k in pending)) pending[k] = batch[k];
      setStatus("unsaved");
      if (!timer) timer = setTimeout(() => send(false), 3000);
    });
  // keep the order of saves: each batch goes after the one before it; a closing page cannot wait, so it sends now
  inflight = keepalive ? Promise.all([inflight, go()]) : inflight.then(go);
  return inflight;
}
function schedule() { setStatus("saving"); clearTimeout(timer); timer = setTimeout(() => send(false), DEBOUNCE_MS); }

function area(name) {
  return {
    getItem(key) { const k = name + ":" + key; return k in items ? items[k] : null; },
    setItem(key, value) { const k = name + ":" + key, v = String(value); if (items[k] === v) return; items[k] = v; pending[k] = v; schedule(); },
    removeItem(key) { const k = name + ":" + key; if (!(k in items) && !(k in pending)) return; delete items[k]; pending[k] = null; schedule(); },
  };
}

function setStatus(s) {
  status = s;
  const el = document.getElementById("ctx-status"); if (!el) return;
  el.textContent = s === "saving" ? "Saving your progress..." : s === "unsaved" ? "Not saved yet: the server did not answer. Retrying." : s === "offline" ? "Your progress cannot be saved right now: the server did not answer." : "Saved for this session only. Closing the browser or an hour away starts clean.";
  el.dataset.state = s;
}

const ready = fetch("/api/context", {credentials: "same-origin"}).then((r) => r.ok ? r.json() : Promise.reject(new Error(String(r.status))))
  .then((data) => {
    const got = data && data.items && typeof data.items === "object" ? data.items : {};
    for (const k of Object.keys(got)) if (typeof got[k] === "string" && !(k in items)) items[k] = got[k];
    resume = typeof data.resume === "string" ? data.resume : "";
    setStatus("saved");
  }).catch(() => { setStatus("offline"); });

// a closing or hidden tab sends what is left (keepalive lets it outlive the page)
addEventListener("pagehide", () => send(true));
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") send(true); });

// following a link waits (up to 4 s) until every change is saved, so the next page reads it from the server
document.addEventListener("click", (e) => {
  const a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
  if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  if ((a.target && a.target !== "_self") || a.hasAttribute("download") || a.origin !== location.origin) return;
  if (a.pathname === location.pathname && a.search === location.search) return;  // a #section on this page: nothing unloads
  if (!Object.keys(pending).length) return;
  e.preventDefault();
  Promise.race([window.CTX.flush(), new Promise((r) => setTimeout(r, 4000))]).then(() => { location.href = a.href; });
});

// a small line at the end of the page: saved or not, and a link to continue on another device
function footer() {
  if (document.getElementById("ctx-status")) return;
  const p = document.createElement("p"); p.className = "small ctx-note"; p.style.cssText = "text-align:center;margin:1.5rem 16px;opacity:.75";
  const s = document.createElement("span"); s.id = "ctx-status"; s.setAttribute("role", "status");
  const b = document.createElement("button"); b.type = "button"; b.className = "btn small hidden"; b.hidden = true; b.style.marginLeft = ".5rem";
  b.textContent = "Copy a link to continue on another device";
  b.addEventListener("click", async () => {
    await ready;
    if (!resume) return;
    const link = location.origin + "/resume?code=" + encodeURIComponent(resume);
    try { await navigator.clipboard.writeText(link); b.textContent = "Link copied. Keep it private: it opens your saved progress."; }
    catch (_) { window.prompt("Copy this link. Keep it private: it opens your saved progress.", link); }
  });
  p.append(s, b); document.body.append(p); setStatus(status);
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", footer); else footer();

window.CTX = {
  ready,
  localStorage: area("localStorage"),
  sessionStorage: area("sessionStorage"),
  flush() { send(false); return inflight; },
  // delete every saved item on the server and clear the cookie
  forgetAll() { for (const k of Object.keys(items)) delete items[k]; for (const k of Object.keys(pending)) delete pending[k];
    clearTimeout(timer); timer = 0;
    inflight = inflight.then(() => fetch("/api/context/forget", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json"}, body: "{}"}).catch(() => {}));
    return inflight; },
};
})();
