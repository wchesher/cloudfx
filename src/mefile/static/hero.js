/* Copyright (c) 2026 William Chesher. MIT License, see LICENSE. */
/* hero.js - the front page's product demo loop: a statement in a file lights up, the answers behind it slide in as
   evidence chips joined by fine animated lines, one statement at a time; then a share link locks. The markup is in
   home.html; this file only times it (CSS transitions do the motion) and draws the lines. Calm by design: long
   holds, soft easing. Static final state under prefers-reduced-motion; pauses when the tab is hidden, when the demo
   scrolls out of view, and on the Pause button. */
(function () {
  "use strict";
  var demo = document.getElementById("demo");
  if (!demo) return;
  var NS = "http://www.w3.org/2000/svg";
  var reduce = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  var claims = Array.prototype.slice.call(demo.querySelectorAll(".demo-claim[data-i]"));
  var groups = Array.prototype.slice.call(demo.querySelectorAll(".demo-group[data-for]"));
  var share = demo.querySelector(".demo-share");
  var svg = demo.querySelector(".demo-lines");
  var paths = [];

  /* lay the evidence groups beside their statement and draw one line per chip */
  function layout() {
    var box = svg.parentNode.getBoundingClientRect();
    svg.setAttribute("viewBox", "0 0 " + box.width + " " + box.height);
    svg.setAttribute("width", box.width); svg.setAttribute("height", box.height);
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    paths = [];
    var stacked = window.matchMedia("(max-width: 640px)").matches;
    groups.forEach(function (g) {
      var i = Number(g.getAttribute("data-for"));
      var claim = claims[i];
      if (!claim) return;
      if (!stacked) {
        var col = g.parentNode.getBoundingClientRect();
        var c = claim.getBoundingClientRect();
        var top = c.top - col.top + c.height / 2 - g.offsetHeight / 2;
        g.style.top = Math.max(0, top) + "px";
      } else g.style.top = "";
      if (stacked) return;
      var cr = claim.querySelector(".demo-text").getBoundingClientRect();
      var gx = g.getBoundingClientRect().left;
      Array.prototype.forEach.call(g.querySelectorAll(".ev"), function (chip) {
        var r = chip.getBoundingClientRect();
        r = { left: gx, top: r.top, height: r.height };
        var x1 = cr.right - box.left + 10, y1 = cr.top - box.top + cr.height / 2;
        var x2 = r.left - box.left - 4, y2 = r.top - box.top + r.height / 2;
        var dx = Math.max(16, (x2 - x1) * .5);
        var p = document.createElementNS(NS, "path");
        p.setAttribute("d", "M" + x1 + " " + y1 + " C" + (x1 + dx) + " " + y1 + " " + (x2 - dx) + " " + y2 + " " + x2 + " " + y2);
        svg.appendChild(p);
        var len = p.getTotalLength ? p.getTotalLength() : 120;
        p.style.strokeDasharray = len; p.style.strokeDashoffset = len;
        p.setAttribute("data-for", i);
        var dot = document.createElementNS(NS, "circle");
        dot.setAttribute("cx", x2); dot.setAttribute("cy", y2); dot.setAttribute("r", 2.5); dot.setAttribute("data-for", i);
        svg.appendChild(dot);
        paths.push({ el: p, dot: dot, i: i, len: len });
      });
    });
    apply(clock, true);
  }

  /* the timeline: each statement holds for STEP seconds, then the share locks, then a long calm pause */
  var STEP = 3.0, LOCK_AT = claims.length * STEP + .4, PERIOD = LOCK_AT + 6.2;
  var current = { active: -2, locked: null, shown: null };
  function apply(t, force) {
    var local = t % PERIOD;
    var active = local < LOCK_AT ? Math.floor(local / STEP) : -1;
    if (reduce.matches) active = 0;
    var showShare = reduce.matches || local >= LOCK_AT - .2;
    var locked = reduce.matches || local >= LOCK_AT + .7;
    var fading = !reduce.matches && local >= PERIOD - .8;
    if (force || active !== current.active) {
      claims.forEach(function (c, i) { c.classList.toggle("lit", i === active); });
      groups.forEach(function (g) { g.classList.toggle("on", Number(g.getAttribute("data-for")) === active); });
      paths.forEach(function (p) { var on = p.i === active; p.el.style.strokeDashoffset = on ? 0 : p.len; p.el.classList.toggle("on", on); p.dot.classList.toggle("on", on); });
      current.active = active;
    }
    if (force || showShare !== current.shown || fading !== current.fading) {
      share.classList.toggle("shown", showShare && !fading);
      current.shown = showShare; current.fading = fading;
    }
    if (force || locked !== current.locked) { share.classList.toggle("locked", locked && !fading); current.locked = locked; }
  }

  var clock = 0, last = 0, raf = 0, playing = !reduce.matches, visible = true;
  var button = document.getElementById("hero-pause");
  function tick(now) {
    if (!last) last = now;
    clock += Math.min(.05, (now - last) / 1000); /* a long gap (tab switch) never jumps the scene */
    last = now;
    apply(clock, false);
    raf = requestAnimationFrame(tick);
  }
  function run() {
    var should = playing && visible && !document.hidden && !reduce.matches;
    if (should && !raf) { last = 0; raf = requestAnimationFrame(tick); }
    if (!should && raf) { cancelAnimationFrame(raf); raf = 0; }
    demo.classList.toggle("paused", !should);
    if (button) {
      button.hidden = reduce.matches;
      button.setAttribute("aria-pressed", String(!playing));
      button.querySelector("span").textContent = playing ? "Pause animation" : "Play animation";
      button.classList.toggle("paused", !playing);
    }
  }
  document.addEventListener("visibilitychange", run);
  if ("IntersectionObserver" in window) new IntersectionObserver(function (e) { visible = e[0].isIntersecting; run(); }, { threshold: .05 }).observe(demo);
  if (button) button.addEventListener("click", function () { playing = !playing; run(); });
  if (reduce.addEventListener) reduce.addEventListener("change", function () { apply(clock, true); run(); });
  var resizeTimer = 0;
  window.addEventListener("resize", function () { clearTimeout(resizeTimer); resizeTimer = setTimeout(layout, 120); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(layout);
  layout();
  run();
  window.__hero = { clock: function () { return clock; }, running: function () { return !!raf; } };
})();
