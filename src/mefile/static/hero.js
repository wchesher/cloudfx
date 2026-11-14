/* Copyright (c) 2026 William Chesher. MIT License, see LICENSE. */
/* hero.js - the front page's luminous field. lumin8r illuminates: your answers are points of light drifting in a
   calm field. A few gather and a statement from a file resolves out of them; fine threads of amber light travel
   back from the statement to the two or three answers behind it, which glow and show their IDs. Then it dims and
   another forms elsewhere. Now and then a statement passes through a lock ("Shared with Dana") and goes dark when
   the link is turned off. Plain 2D canvas, DPR-aware, one requestAnimationFrame loop; a few dozen points, one cached
   glow sprite, a few lines of text per frame. A single still frame under prefers-reduced-motion; pauses when the
   tab is hidden, when the hero scrolls away, and on the Pause button. */
(function () {
  "use strict";
  var canvas = document.getElementById("hero-canvas");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  var host = canvas.parentNode;
  var reduce = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  var button = document.getElementById("hero-pause");

  /* what lights up: real statements and the answers behind them */
  var STATEMENTS = [
    { kind: "How you handle situations", text: "Raises a disagreement openly, with reasons", ev: [["S01", "Chose A"], ["B21", "4 of 5"]] },
    { kind: "How you describe yourself", text: "Likes time to think before deciding", ev: [["B45", "5 of 5"], ["S03", "Chose D"], ["B43", "4 of 5"]] },
    { kind: "How you write", text: "Short, warm messages that start with thanks", ev: [["W01", "38 words"], ["W03", "opens with thanks"]], share: true },
    { kind: "How you handle situations", text: "Gathers the facts before a hard call", ev: [["S03", "Chose D"], ["B33", "4 of 5"]] },
    { kind: "How you describe yourself", text: "Makes people feel at ease", ev: [["B47", "5 of 5"], ["B17", "4 of 5"], ["W03", "warm words"]] }
  ];
  var CYCLE = 7.8;                 /* seconds per statement, including a quiet rest */
  var STILL_AT = 3.6;              /* the composed moment used for reduced motion */

  /* ---- sizing and theme ---- */
  var W = 0, H = 0, dpr = 1, narrow = false, stage = { x: 0, y: 0, w: 0, h: 0 };
  var colors = {}, sprite = null, soft = null;
  function readTheme() {
    var cs = getComputedStyle(document.documentElement);
    var get = function (n, d) { var v = cs.getPropertyValue(n).trim(); return v || d; };
    colors = { ink: get("--ink", "#0b0d12"), muted: get("--muted", "#565d69"), panel: get("--panel", "#ffffff"),
      line: get("--line", "#e6e8ec"), glow: get("--glow", "#ffb224"), accent: get("--accent", "#8a4f00") };
    var bg = get("--surface", "#fafbfc").replace("#", "");
    var lum = bg.length >= 6 ? (parseInt(bg.slice(0, 2), 16) * 0.299 + parseInt(bg.slice(2, 4), 16) * 0.587 + parseInt(bg.slice(4, 6), 16) * 0.114) : 250;
    colors.dark = lum < 90;
    colors.dot = colors.dark ? "rgb(214, 222, 236)" : "rgb(60, 72, 92)";
    sprite = makeSprite();
    soft = document.createElement("canvas"); soft.width = soft.height = 64;
    var sg = soft.getContext("2d"), rg = sg.createRadialGradient(32, 32, 0, 32, 32, 32);
    var tone = colors.dark ? "214, 222, 236" : "60, 72, 92";
    rg.addColorStop(0, "rgba(" + tone + ", 1)"); rg.addColorStop(.45, "rgba(" + tone + ", .45)"); rg.addColorStop(1, "rgba(" + tone + ", 0)");
    sg.fillStyle = rg; sg.fillRect(0, 0, 64, 64);
  }
  function makeSprite() {
    var s = document.createElement("canvas"); s.width = s.height = 128;
    var g = s.getContext("2d"), r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    r.addColorStop(0, "rgba(255, 192, 76, 1)"); r.addColorStop(.22, "rgba(255, 178, 36, .55)"); r.addColorStop(.6, "rgba(255, 170, 30, .12)"); r.addColorStop(1, "rgba(255, 170, 30, 0)");
    g.fillStyle = r; g.fillRect(0, 0, 128, 128);
    return s;
  }
  function resize() {
    var rect = host.getBoundingClientRect();
    W = Math.max(1, Math.round(rect.width)); H = Math.max(1, Math.round(rect.height));
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    narrow = W < 760;
    /* the stage: where statements form. Right of the headline on wide screens, below it on phones */
    var copy = document.querySelector(".hero-copy");
    var cb = copy ? copy.getBoundingClientRect() : { right: rect.left + W * .45, bottom: rect.top + H * .55 };
    if (narrow) { stage.x = 20; stage.y = Math.min(H - 230, cb.bottom - rect.top + 48); stage.w = W - 40; stage.h = H - stage.y - 70; }
    else { stage.x = Math.max(W * .5, cb.right - rect.left + 56); stage.y = H * .17; stage.w = W - stage.x - Math.max(40, W * .05); stage.h = H * .66; }
    seedPoints();
    cycles = {};
  }

  /* ---- the field: answer points drifting slowly, denser where statements form ---- */
  var points = [], bokeh = [];
  function rand(seed) { var x = Math.sin(seed * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
  function seedPoints() {
    var n = narrow ? 34 : Math.round(Math.min(84, Math.max(52, W / 18)));
    points = [];
    bokeh = [];
    for (var b = 0; b < (narrow ? 5 : 11); b++) bokeh.push({ hx: stage.x - 60 + rand(b + 501) * (stage.w + 120), hy: rand(b + 511) * H, r: 5 + rand(b + 521) * 12, a: .035 + rand(b + 531) * .05,
      f1: .02 + rand(b + 541) * .03, f2: .02 + rand(b + 551) * .03, p1: rand(b + 561) * 6.28, p2: rand(b + 571) * 6.28, amp: 18 + rand(b + 581) * 20, z: 1.4 });
    for (var i = 0; i < n; i++) {
      var inStage = rand(i + 1) < .72;
      var hx = inStage ? stage.x - 30 + rand(i + 11) * (stage.w + 60) : rand(i + 21) * W;
      var hy = inStage ? stage.y - 40 + rand(i + 31) * (stage.h + 80) : rand(i + 41) * H;
      points.push({ hx: hx, hy: hy, z: .35 + rand(i + 51) * .65, r: .8 + rand(i + 61) * 1.3, a: .18 + rand(i + 71) * .36,
        f1: .05 + rand(i + 81) * .08, f2: .04 + rand(i + 91) * .07, p1: rand(i + 101) * 6.28, p2: rand(i + 111) * 6.28, amp: 8 + rand(i + 121) * 14 });
    }
  }
  function drift(p, t, out) {
    out.x = p.hx + Math.sin(t * p.f1 + p.p1) * p.amp + par.x * p.z * 10;
    out.y = p.hy + Math.cos(t * p.f2 + p.p2) * p.amp * .8 + par.y * p.z * 8;
    return out;
  }

  /* ---- one statement's moment: where it forms, which points carry its evidence ---- */
  var cycles = {};
  var SLOTS_WIDE = [[.04, .30], [.24, .66], [.0, .86], [.2, .14], [.1, .5]];
  var SLOTS_NARROW = [[0, .1], [0, .16], [0, .1], [0, .14], [0, .12]];
  function cycleFor(n) {
    if (cycles[n]) return cycles[n];
    var s = STATEMENTS[n % STATEMENTS.length];
    var slot = (narrow ? SLOTS_NARROW : SLOTS_WIDE)[n % 5];
    ctx.font = font(narrow ? 19 : 23, 500);
    if ("letterSpacing" in ctx) ctx.letterSpacing = narrow ? "-0.2px" : "-0.45px";
    var lines = wrap(s.text, narrow ? stage.w - 8 : Math.min(580, stage.w * .94));
    var tw = 0; lines.forEach(function (l) { tw = Math.max(tw, ctx.measureText(l).width); });
    if ("letterSpacing" in ctx) ctx.letterSpacing = "0px";
    var lh = narrow ? 25 : 30;
    var x = stage.x + slot[0] * stage.w, y = stage.y + slot[1] * stage.h;
    x = Math.min(x, stage.x + stage.w - tw - 8);
    var c = { s: s, lines: lines, x: x, y: y, tw: tw, lh: lh, targets: [], picks: [], dust: [] };
    /* evidence settles in a loose arc around the statement, never on top of it */
    var below = narrow || slot[1] < .5;
    var cx = x + tw * .5, cy = y + (lines.length - 1) * lh * .5;
    var count = s.ev.length;
    s.ev.forEach(function (e, k) {
      var spread = count === 2 ? [-.36, .36][k] : [-.42, 0, .42][k];
      var tx = cx + spread * Math.max(narrow ? stage.w * .9 : tw * 1.25, 240) + (narrow ? 0 : 40);
      var ty = cy + (below ? 1 : -1) * ((narrow ? 64 : 104) + (k % 2) * (narrow ? 22 : 34) + (lines.length - 1) * lh);
      tx = Math.max(stage.x + 14, Math.min(stage.x + stage.w - 120, tx));
      ty = Math.max(stage.y - 30, Math.min(H - 40, ty));
      c.targets.push({ x: tx, y: ty, id: e[0], val: e[1] });
    });
    /* pick the nearest free points to carry the evidence, and a few nearby points to resolve into the line */
    var used = {}, tmp = { x: 0, y: 0 };
    c.targets.forEach(function (tg) {
      var best = -1, bd = 1e9;
      points.forEach(function (p, i) { if (used[i]) return; drift(p, n * CYCLE, tmp); var d = (tmp.x - tg.x) * (tmp.x - tg.x) + (tmp.y - tg.y) * (tmp.y - tg.y); if (d < bd) { bd = d; best = i; } });
      used[best] = 1; c.picks.push(best);
    });
    var near = points.map(function (p, i) { drift(p, n * CYCLE, tmp); return { i: i, d: Math.abs(tmp.x - (x + tw / 2)) + Math.abs(tmp.y - y) * 1.6 }; })
      .filter(function (o) { return !used[o.i]; }).sort(function (a, b) { return a.d - b.d; }).slice(0, narrow ? 4 : 7);
    near.forEach(function (o, k) { c.dust.push({ i: o.i, x: x + (k + .5) / near.length * tw, y: y - 7 }); used[o.i] = 1; });
    cycles[n] = c;
    var keys = Object.keys(cycles); if (keys.length > 6) delete cycles[keys[0]];
    return c;
  }
  function font(size, weight) { return weight + " " + size + "px Geist, 'Inter Tight', Inter, system-ui, -apple-system, sans-serif"; }
  function wrap(text, max) {
    var words = text.split(" "), lines = [], line = "";
    words.forEach(function (w) { var test = line ? line + " " + w : w; if (ctx.measureText(test).width > max && line) { lines.push(line); line = w; } else line = test; });
    if (line) lines.push(line);
    return lines;
  }

  /* ---- easing ---- */
  var clamp = function (v) { return v < 0 ? 0 : v > 1 ? 1 : v; };
  var span = function (t, a, d) { return clamp((t - a) / d); };
  var inOut = function (t) { return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
  var out3 = function (t) { return 1 - Math.pow(1 - t, 3); };
  var spring = function (t) { var c1 = 1.1, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); };
  function cubic(a, b, c, d, u) { var v = 1 - u; return v * v * v * a + 3 * v * v * u * b + 3 * v * u * u * c + u * u * u * d; }

  /* ---- drawing ---- */
  var par = { x: 0, y: 0 }, parTarget = { x: 0, y: 0 }, pos = [];
  function frame(t) {
    par.x += (parTarget.x - par.x) * .045; par.y += (parTarget.y - par.y) * .045;
    var n = Math.floor(t / CYCLE), local = t - n * CYCLE;
    var c = cycleFor(n);
    var out = 1 - inOut(span(local, 5.1, 1.1));                       /* everything dims together */
    var pull = spring(span(local, .1, 1.2)) * (1 - inOut(span(local, 5.7, 1.3)));
    var dust = out3(span(local, 0, 1.15)) * (1 - inOut(span(local, 5.6, 1.6)));
    var textIn = out3(span(local, .7, 1.0)) * out;
    var glowIn = inOut(span(local, .8, 1.3)) * out;
    var labelIn = out3(span(local, 2.1, .7)) * (1 - inOut(span(local, 5.0, .8)));
    var light = colors.dark ? "lighter" : "source-over";

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    var tmp = { x: 0, y: 0 }, roles = {};
    c.picks.forEach(function (i, k) { roles[i] = { ev: k }; });
    c.dust.forEach(function (d) { roles[d.i] = { dust: d }; });

    /* depth: a few large, very soft points far behind */
    ctx.fillStyle = colors.dot;
    for (var bi = 0; bi < bokeh.length; bi++) {
      var bk = bokeh[bi]; drift(bk, t, tmp);
      ctx.globalAlpha = bk.a * (colors.dark ? 1.6 : 1.3);
      ctx.drawImage(soft, tmp.x - bk.r * 2, tmp.y - bk.r * 2, bk.r * 4, bk.r * 4);
    }
    /* the field */
    for (var i = 0; i < points.length; i++) {
      var p = points[i]; drift(p, t, tmp);
      var role = roles[i], a = p.a, x = tmp.x, y = tmp.y;
      if (role && role.ev !== undefined) { var tg = c.targets[role.ev]; x += (tg.x - x) * pull; y += (tg.y - y) * pull; }
      else if (role && role.dust) { x += (role.dust.x - x) * dust; y += (role.dust.y - y) * dust; a *= 1 - dust; }
      pos[i] = { x: x, y: y };
      a *= .78 + .22 * Math.sin(t * .5 + p.p1 * 3);
      if (a < .02) continue;
      ctx.globalAlpha = a;
      ctx.beginPath(); ctx.arc(x, y, p.r, 0, 6.283); ctx.fill();
    }

    var tx0 = c.x + par.x * 5, ty0 = c.y + par.y * 4;
    var midY = ty0 - c.lh * .32 + (c.lines.length - 1) * c.lh / 2;
    /* the light behind the statement */
    if (glowIn > .01) {
      ctx.globalCompositeOperation = light;
      ctx.globalAlpha = glowIn * (colors.dark ? .42 : .3);
      var gw = c.tw + 260, gh = c.lines.length * c.lh + 170;
      ctx.drawImage(sprite, tx0 + c.tw / 2 - gw / 2, midY - gh / 2, gw, gh);
      ctx.globalCompositeOperation = "source-over";
    }

    /* threads: light travelling from the statement back to each answer */
    c.picks.forEach(function (pi, k) {
      var e = pos[pi]; if (!e) return;
      var tg2 = c.targets[k];
      var down = e.y > midY, count = c.picks.length;
      var sx = tx0 + c.tw * (.3 + .4 * (count === 1 ? .5 : k / (count - 1)));
      var sy = down ? ty0 + (c.lines.length - 1) * c.lh + 16 : ty0 - (narrow ? 42 : 50);
      var dy = e.y - sy;
      var c1x = sx, c1y = sy + dy * .58, c2x = e.x, c2y = e.y - dy * .42;
      var drawn = inOut(span(local, 1.35 + k * .16, 1.0));
      if (drawn > .01 && out > .01) {
        ctx.save();
        ctx.globalCompositeOperation = light; ctx.strokeStyle = colors.glow; ctx.lineCap = "round";
        var steps = 40, upto = Math.max(1, Math.round(steps * drawn));
        ctx.beginPath();
        for (var s2 = 0; s2 <= upto; s2++) { var u = s2 / steps, qx = cubic(sx, c1x, c2x, e.x, u), qy = cubic(sy, c1y, c2y, e.y, u); if (s2 === 0) ctx.moveTo(qx, qy); else ctx.lineTo(qx, qy); }
        ctx.globalAlpha = .14 * out; ctx.lineWidth = 4; ctx.stroke();
        ctx.globalAlpha = .95 * out; ctx.lineWidth = 1.05; ctx.stroke();
        /* the thread starts at a small lit node on the statement */
        ctx.globalAlpha = out * clamp(drawn * 3); ctx.fillStyle = colors.glow;
        ctx.beginPath(); ctx.arc(sx, sy, 1.8, 0, 6.283); ctx.fill();
        /* a bead of light travels the thread once as it draws, then again every so often */
        var beadT = local < 2.6 ? span(local, 1.35 + k * .16, 1.0) : ((local - 2.6 - k * .3) % 2.0) / 1.2;
        if (!reduce.matches && beadT > 0 && beadT < 1 && out > .05) {
          var ub = inOut(beadT);
          ctx.globalAlpha = .95 * out * Math.sin(beadT * Math.PI);
          ctx.drawImage(sprite, cubic(sx, c1x, c2x, e.x, ub) - 10, cubic(sy, c1y, c2y, e.y, ub) - 10, 20, 20);
        }
        ctx.restore();
      }
      /* the answer glows and shows its ID */
      var glow = pull * clamp(drawn * 1.6) * out + 0;
      if (glow > .02) {
        ctx.globalCompositeOperation = light;
        ctx.globalAlpha = glow * (colors.dark ? .95 : .85);
        ctx.drawImage(sprite, e.x - 24, e.y - 24, 48, 48);
        ctx.globalCompositeOperation = "source-over";
        ctx.globalAlpha = glow; ctx.fillStyle = colors.glow;
        ctx.beginPath(); ctx.arc(e.x, e.y, 2.8, 0, 6.283); ctx.fill();
      }
      if (labelIn > .02) {
        ctx.globalAlpha = labelIn;
        ctx.font = "500 11px 'Geist Mono', ui-monospace, monospace"; ctx.textBaseline = "middle";
        var idW = ctx.measureText(tg2.id).width + 12, lx = e.x + 13, ly = e.y + (labelIn - 1) * 3;
        roundRect(lx, ly - 10, idW, 20, 5); ctx.fillStyle = colors.panel; ctx.fill(); ctx.strokeStyle = colors.line; ctx.lineWidth = 1; ctx.stroke();
        ctx.fillStyle = colors.ink; ctx.fillText(tg2.id, lx + 6, ly + .5);
        ctx.font = "400 12.5px Geist, Inter, system-ui, sans-serif"; ctx.fillStyle = colors.muted;
        ctx.fillText(tg2.val, lx + idW + 7, ly + .5);
        ctx.textBaseline = "alphabetic";
      }
    });

    /* the statement itself, resolving out of the points */
    if (textIn > .01) {
      ctx.globalAlpha = textIn * .9; ctx.fillStyle = colors.muted;
      ctx.font = font(narrow ? 11.5 : 12.5, 500);
      ctx.fillText(c.s.kind, tx0, ty0 - (narrow ? 25 : 31) + (1 - textIn) * 6);
      ctx.globalAlpha = textIn; ctx.fillStyle = colors.ink;
      ctx.font = font(narrow ? 19 : 23, 500);
      if ("letterSpacing" in ctx) ctx.letterSpacing = narrow ? "-0.2px" : "-0.45px";
      c.lines.forEach(function (l, li) { ctx.fillText(l, tx0, ty0 + li * c.lh + (1 - textIn) * 8); });
      if ("letterSpacing" in ctx) ctx.letterSpacing = "0px";
      var ul = inOut(span(local, 1.0, 1.1)) * out;
      ctx.globalAlpha = ul * .85; ctx.fillStyle = colors.glow;
      ctx.fillRect(tx0, ty0 + (c.lines.length - 1) * c.lh + 10, c.tw * ul, 1.2);
    }

    /* sharing: the statement passes through a lock, and goes dark when the link is turned off */
    if (c.s.share) {
      var pin = out3(span(local, 2.9, .7)) * (1 - inOut(span(local, 5.0, .9)));
      if (pin > .01) {
        var locked = spring(span(local, 3.4, .6)), off = inOut(span(local, 4.4, .6));
        var label = off > .5 ? "Link turned off" : "Shared with Dana · coaching · 30 days";
        ctx.font = font(12.5, 500);
        var lw = ctx.measureText(label).width + 48;
        var px = tx0 + (narrow ? 0 : c.tw + 24), py = narrow ? ty0 + (c.lines.length - 1) * c.lh + 26 : ty0 - 21;
        if (!narrow && px + lw > W - 16) { px = tx0; py = ty0 + (c.lines.length - 1) * c.lh + 26; }
        py += (1 - pin) * 6;
        ctx.globalAlpha = pin;
        roundRect(px, py, lw, 30, 9); ctx.fillStyle = colors.panel; ctx.fill(); ctx.strokeStyle = colors.line; ctx.lineWidth = 1; ctx.stroke();
        var lit2 = clamp(locked) * (1 - off);
        if (lit2 > .02) { ctx.globalCompositeOperation = light; ctx.globalAlpha = pin * lit2 * .75; ctx.drawImage(sprite, px + 2, py - 7, 40, 44); ctx.globalCompositeOperation = "source-over"; }
        ctx.globalAlpha = pin;
        var kx = px + 22, ky = py + 17, lift = (1 - locked) * 3 + off * 3;
        ctx.strokeStyle = lit2 > .5 ? colors.accent : colors.muted; ctx.fillStyle = lit2 > .5 ? colors.glow : colors.muted; ctx.lineWidth = 1.6;
        ctx.beginPath(); ctx.moveTo(kx - 3.6, ky - 2 - lift); ctx.arc(kx, ky - 4.8 - lift, 3.6, Math.PI, 0); ctx.lineTo(kx + 3.6, ky - 2 - lift); ctx.stroke();
        roundRect(kx - 5.2, ky - 2.4, 10.4, 7.8, 2); ctx.fill();
        ctx.fillStyle = off > .5 ? colors.muted : colors.ink; ctx.textBaseline = "middle";
        ctx.fillText(label, px + 36, py + 15.5); ctx.textBaseline = "alphabetic";
      }
    }
    ctx.globalAlpha = 1;
  }
  function roundRect(x, y, w, h, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }

  /* ---- the clock: runs only while visible, playing, and motion is welcome ---- */
  var clock = .2, last = 0, raf = 0, playing = true, visible = true, cost = 0;
  function tick(now) {
    if (!last) last = now;
    clock += Math.min(.05, (now - last) / 1000);
    last = now;
    var t0 = performance.now(); frame(clock); cost = cost * .95 + (performance.now() - t0) * .05;
    raf = requestAnimationFrame(tick);
  }
  function still() { frame(STILL_AT); }
  function run() {
    var should = playing && visible && !document.hidden && !reduce.matches;
    if (should && !raf) { last = 0; raf = requestAnimationFrame(tick); }
    if (!should && raf) { cancelAnimationFrame(raf); raf = 0; }
    if (reduce.matches) still();
    if (button) {
      button.hidden = reduce.matches;
      button.setAttribute("aria-pressed", String(!playing));
      button.querySelector("span").textContent = playing ? "Pause animation" : "Play animation";
      button.classList.toggle("paused", !playing);
    }
  }
  function redraw() { if (raf) return; if (reduce.matches) still(); else frame(clock); }
  host.addEventListener("pointermove", function (e) {
    if (e.pointerType === "touch") return;
    var r = host.getBoundingClientRect();
    parTarget.x = ((e.clientX - r.left) / r.width - .5) * 2; parTarget.y = ((e.clientY - r.top) / r.height - .5) * 2;
  });
  host.addEventListener("pointerleave", function () { parTarget.x = 0; parTarget.y = 0; });
  document.addEventListener("visibilitychange", run);
  if ("IntersectionObserver" in window) new IntersectionObserver(function (e) { visible = e[0].isIntersecting; run(); }, { threshold: .02 }).observe(host);
  if (button) button.addEventListener("click", function () { playing = !playing; run(); });
  if (reduce.addEventListener) reduce.addEventListener("change", run);
  var scheme = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  if (scheme && scheme.addEventListener) scheme.addEventListener("change", function () { readTheme(); redraw(); });
  var rt = 0;
  window.addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(function () { resize(); redraw(); }, 120); });
  readTheme(); resize();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { cycles = {}; redraw(); });
  run();
  window.__hero = { clock: function () { return clock; }, running: function () { return !!raf; }, cost: function () { return cost; },
    seek: function (t) { clock = t; frame(t); } };
})();
