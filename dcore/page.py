"""The interactive page (graph.html): one self-contained file.

`viz.render_html` fills in __TITLE__ and __DATA__. Everything else is static,
so the page is as reproducible as the artifact it is drawn from: no clock, no
randomness, and the layout is computed in the browser from the data.

The whole deliberation is drawn as one argument graph, read left to right:
the question (with no verdict of its own), every part, each part's arguments,
the answers to them, attacks between arguments, and a dashed edge wherever an
argument rests on another part. Pan and zoom to read; tap a node for why.
"""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="claude:viewport-fit-sides" content="cover">
<title>__TITLE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Public+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a full-height canvas holding one left-to-right graph (question, parts, arguments),
   a slim bar of controls on top, and a details panel at the side (bottom on phones). */
:root {
  --bg: #f4f6f8; --surface: #ffffff; --ink: #1d2430; --muted: #5d6675; --faint: #8a93a2; --line: #d3d9e1; --grid: #e7ebf0;
  --pro: #2c6e8a; --pro-tint: #e3eff4; --con: #8a4a78; --con-tint: #f4e7f0;
  --open: #8a6d1f; --attack: #a33a2b; --focus: #3a63c7;
  --display: "Newsreader", "Iowan Old Style", Georgia, serif;
  --body: "Public Sans", "Segoe UI", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #11151b; --surface: #1a2029; --ink: #e6e9ef; --muted: #a3acba; --faint: #7a8494; --line: #333c4a; --grid: #1a1f27;
  --pro: #82bbd3; --pro-tint: #1b2c35; --con: #d4a0c6; --con-tint: #31212d;
  --open: #e0c47e; --attack: #ec8b7a; --focus: #8fb0ff; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #11151b; --surface: #1a2029; --ink: #e6e9ef; --muted: #a3acba; --faint: #7a8494; --line: #333c4a; --grid: #1a1f27;
  --pro: #82bbd3; --pro-tint: #1b2c35; --con: #d4a0c6; --con-tint: #31212d;
  --open: #e0c47e; --attack: #ec8b7a; --focus: #8fb0ff; color-scheme: dark; }
* { box-sizing: border-box; }
html, body { height: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5 var(--body); display: grid; grid-template-rows: auto minmax(0, 1fr); overflow: hidden; }
.bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; padding-block: 10px; border-bottom: 1px solid var(--line); background: var(--surface);
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.bar h1 { font: 600 16px/1.3 var(--display); margin: 0; flex: 1 1 320px; min-width: 0; }
.bar h1 small { display: block; font: 12.5px var(--body); color: var(--muted); }
.ctrls { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.ctrls select { width: min(240px, 100%); }
.ctrls button, .ctrls select { font: 500 13px var(--body); color: var(--ink); background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 5px 10px; cursor: pointer; }
.ctrls button:hover, .ctrls select:hover { border-color: var(--ink); }
:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.stage { position: relative; min-height: 0; }
svg#g { width: 100%; height: 100%; display: block; cursor: grab; touch-action: none; user-select: none; -webkit-user-select: none; }
svg#g.dragging { cursor: grabbing; }
.legend { position: absolute; left: max(12px, env(safe-area-inset-left, 0px)); bottom: max(12px, env(safe-area-inset-bottom, 0px)); display: flex; flex-wrap: wrap; gap: 4px 14px; max-width: min(560px, calc(100% - 24px));
  font-size: 12px; color: var(--muted); background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; }
.legend i { display: inline-block; width: 18px; height: 0; border-top: 2px solid; vertical-align: middle; margin-right: 6px; }
/* graph */
.edge { fill: none; stroke-width: 1.8; }
.edge.member { stroke: var(--line); stroke-width: 1.4; }
.edge.for { stroke: var(--pro); } .edge.against { stroke: var(--con); }
.edge.attack { stroke: var(--attack); stroke-width: 2.4; }
.edge.link { stroke: var(--ink); stroke-dasharray: 7 5; stroke-width: 1.8; }
.elabel { font: 600 12px var(--body); fill: var(--muted); paint-order: stroke; stroke: var(--bg); stroke-width: 5px; stroke-linejoin: round; }
.elabel.attack { fill: var(--attack); } .elabel.link { fill: var(--ink); }
.mk-for { fill: var(--pro); } .mk-against { fill: var(--con); } .mk-attack { fill: var(--attack); } .mk-link { fill: var(--ink); }
.node { cursor: pointer; }
.node rect { fill: var(--surface); stroke: var(--line); stroke-width: 1.4; }
.node.q rect { fill: var(--ink); stroke: var(--ink); } .node.q .ttl { fill: var(--bg); font: 600 19px var(--display); } .node.q .sub { fill: var(--bg); opacity: .8; }
.node.part rect { stroke: var(--ink); stroke-width: 2; }
.node.part .ttl { font: 600 15px var(--display); }
.node.part.st-supported rect { stroke: var(--pro); } .node.part.st-challenged rect { stroke: var(--con); }
.node.part.st-contested rect { stroke: var(--open); stroke-dasharray: 8 5; }
.node.part.st-unproven rect, .node.part.st-unverified rect { stroke: var(--faint); stroke-dasharray: 2 4; }
.node .word { font: 700 12px var(--body); letter-spacing: .04em; text-transform: uppercase; }
.st-supported .word { fill: var(--pro); } .st-challenged .word { fill: var(--con); } .st-contested .word { fill: var(--open); }
.st-unproven .word, .st-unverified .word, .st-both .word { fill: var(--muted); }
.node.pro rect { fill: var(--pro-tint); stroke: var(--pro); } .node.con rect { fill: var(--con-tint); stroke: var(--con); }
.node.holds rect { stroke-width: 2.6; }
.node.open rect { stroke-dasharray: 7 4; stroke-width: 2; }
.node.struck { opacity: .5; } .node.struck .ttl { text-decoration: line-through; }
.node .ttl { font: 600 13.5px var(--body); fill: var(--ink); }
.node .sub { font: 12px var(--body); fill: var(--muted); }
.node .pid { font: 500 11px var(--mono); fill: var(--faint); }
.node.sel rect { stroke: var(--focus) !important; stroke-width: 3.5 !important; }
svg.focus .node:not(.near), svg.focus .edge:not(.near), svg.focus .elabel:not(.near) { opacity: .15; }
svg.focus .node.struck.near { opacity: .6; }
/* panel */
.panel { position: absolute; top: 12px; right: max(12px, env(safe-area-inset-right, 0px)); bottom: 12px; width: 360px; overflow: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px; display: grid; gap: 10px; align-content: start; box-shadow: 0 6px 24px rgb(0 0 0 / .08); }
.panel .x { justify-self: end; font: 500 13px var(--body); background: none; border: 1px solid var(--line); border-radius: 6px; padding: 2px 8px; color: var(--muted); cursor: pointer; }
.panel h2 { font: 600 18px/1.3 var(--display); margin: 0; text-wrap: balance; }
.panel h3 { font: 600 12px var(--body); text-transform: uppercase; letter-spacing: .07em; color: var(--muted); margin: 6px 0 0; }
.panel p { margin: 0; }
.panel ul { margin: 0; padding-left: 18px; display: grid; gap: 6px; }
.panel .eyebrow { font: 12px var(--mono); color: var(--faint); text-transform: uppercase; letter-spacing: .06em; }
.panel .why { font: italic 15.5px/1.45 var(--display); }
.panel .note { color: var(--muted); font-size: 13px; }
.panel a, .panel .jump { color: var(--focus); }
.panel .jump { background: none; border: 0; padding: 0; font: inherit; text-decoration: underline; cursor: pointer; }
.panel .meta { font: 11.5px var(--mono); color: var(--faint); overflow-wrap: anywhere; }
@media (max-width: 760px) {
  .panel { top: auto; left: max(8px, env(safe-area-inset-left, 0px)); right: max(8px, env(safe-area-inset-right, 0px)); bottom: max(8px, env(safe-area-inset-bottom, 0px)); width: auto; max-height: 48%; }
  .legend { display: none; }
}
</style>
</head>
<body>
<div class="bar">
  <h1 id="q"><small id="sub"></small></h1>
  <div class="ctrls">
    <label for="find" class="sr" style="position:absolute;left:-9999px">Go to part</label>
    <select id="find"><option value="">Go to part…</option></select>
    <button type="button" id="zin" aria-label="Zoom in">+</button>
    <button type="button" id="zout" aria-label="Zoom out">−</button>
    <button type="button" id="fit">Show all</button>
  </div>
</div>
<div class="stage" id="stage">
  <svg id="g" role="img" aria-label="Argument graph of the whole question"><g id="world"></g></svg>
  <div class="legend" aria-hidden="true">
    <span><i style="border-color:var(--pro)"></i>for a part</span><span><i style="border-color:var(--con)"></i>against a part</span>
    <span><i style="border-color:var(--attack);border-top-width:3px"></i>attack</span><span><i style="border-color:var(--ink);border-top-style:dashed"></i>rests on another part</span>
    <span>struck and faded: falls</span><span>dashed box: open</span><span>drag or scroll to move · pinch or ctrl+scroll to zoom · tap for why</span>
  </div>
  <aside class="panel" id="panel" aria-live="polite"></aside>
</div>
<script type="application/json" id="data">__DATA__</script>
<script>
(() => {
  const D = JSON.parse(document.getElementById("data").textContent);
  const $ = (id) => document.getElementById(id);
  const NS = "http://www.w3.org/2000/svg";
  const byId = Object.fromEntries(D.parts.map((p) => [p.id, p]));
  const WORD = { "supported": "Supported", "challenged": "Challenged", "both hold in part": "Both hold in part",
                 "contested": "Open", "unproven either way": "Unproven either way", "unverified": "Not yet checked" };
  const VERB = { rebut: "rebuts", undermine: "undermines", undercut: "undercuts" };
  const WHYVERB = { rebut: "contradicts it:", undermine: "disputes its evidence:", undercut: "says it doesn't follow:" };
  const STATE = { stands: "holds", falls: "struck", open: "open", "rejected at checking": "struck" };
  const q = (t) => "“" + t + "”";
  const h = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const el = (tag, attrs = {}, text) => { const n = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); if (text !== undefined) n.textContent = text; return n; };
  const wrap = (text, n, max) => { const out = []; let cur = ""; for (const w of text.split(/\s+/)) { if ((cur + " " + w).trim().length > n && cur) { out.push(cur); cur = w; } else cur = (cur + " " + w).trim(); } if (cur) out.push(cur); if (out.length > max) { out.length = max; out[max - 1] = out[max - 1].replace(/[,.;:]?$/, "…"); } return out; };

  $("q").prepend(D.question.plain);
  $("sub").textContent = "Every part checked on its own, from both sides. The question as a whole gets no verdict.";

  // ---------- layout: left to right, question -> parts -> cases -> answers ----------
  // One band per part; parts that rest on others come last, so their links run down.
  const QW = 270, PW = 260, PH = 112, W = 240, H = 92, GV = 22, BG = 56;
  const PX = QW + 150, CX = PX + PW + 170, AX = CX + W + 170, width = AX + W;
  const depth = {};
  const depthOf = (p) => depth[p.id] ?? (depth[p.id] = p.links.length ? 1 + Math.max(...p.links.map((l) => depthOf(byId[l.part]))) : 0);
  D.parts.forEach(depthOf);
  const order = D.parts.slice().sort((a, b) => depth[a.id] - depth[b.id]);
  const pos = {}, bands = [];
  let y = 0;
  order.forEach((p) => {
    const cases = p.nodes.filter((n) => n.role !== "objection").sort((a, b) => (a.stance === b.stance ? 0 : a.stance === "supports" ? -1 : 1));
    const answers = p.nodes.filter((n) => n.role === "objection");
    cases.forEach((n, i) => { pos[n.id] = { x: CX, y: y + i * (H + GV), w: W, h: H }; });
    let next = y;
    answers.forEach((n) => {   // an answer sits level with the point it answers
      const e = p.edges.find((x) => x.kind === "attack" && x.from === n.id);
      const want = e && pos[e.to] ? pos[e.to].y : next;
      pos[n.id] = { x: AX, y: Math.max(want, next), w: W, h: H }; next = pos[n.id].y + H + GV;
    });
    const bottomOf = Math.max(y + PH, ...p.nodes.map((n) => pos[n.id].y + H));
    pos[p.id] = { x: PX, y: y + (bottomOf - y - PH) / 2, w: PW, h: PH };
    bands.push({ id: p.id, y, h: bottomOf - y });
    y = bottomOf + BG;
  });
  const fullH = y - BG;
  pos.Q = { x: 0, y: 0, w: QW, h: 170 };

  // ---------- draw ----------
  const world = $("world");
  const defs = el("defs");
  ["for", "against", "attack", "link"].forEach((k) => { const m = el("marker", { id: "mk-" + k, viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" }); m.append(el("path", { d: "M0,0 L10,5 L0,10 z", class: "mk-" + k })); defs.append(m); });
  $("g").prepend(defs);
  const edgeG = el("g"), nodeG = el("g"), labelG = el("g");
  world.append(edgeG, nodeG, labelG);
  const adj = {};  // node id -> neighbour ids, for highlighting
  const join = (a, b) => { (adj[a] = adj[a] || new Set()).add(b); (adj[b] = adj[b] || new Set()).add(a); };
  const edge = (from, to, cls, d, label, lx, ly, marker = true) => {
    join(from, to);
    edgeG.append(el("path", { d, class: "edge " + cls, "data-a": from, "data-b": to, ...(marker ? { "marker-end": `url(#mk-${cls})` } : {}) }));
    if (label) labelG.append(el("text", { x: lx, y: ly, "text-anchor": "middle", class: "elabel " + cls, "data-a": from, "data-b": to }, label));
  };
  const my = (b) => b.y + b.h / 2;
  const across = (a, b) => { const sx = a.x, sy = my(a), tx = b.x + b.w + 2, ty = my(b), mx = (sx + tx) / 2; return [`M${sx},${sy} C${mx},${sy} ${mx},${ty} ${tx},${ty}`, mx, (sy + ty) / 2 - 6]; };

  D.parts.forEach((p) => { const a = pos.Q, b = pos[p.id], sx = a.x + a.w, sy = a.y + a.h / 2, mx = (sx + b.x) / 2;
    edge("Q", p.id, "member", `M${sx},${sy} C${mx},${sy} ${mx},${my(b)} ${b.x},${my(b)}`, null, 0, 0, false); });
  let lane = 0;
  D.parts.forEach((p) => {
    const pairs = {};
    p.edges.forEach((e) => {
      if (e.kind === "link") return;
      const a = pos[e.from], b = pos[e.to]; if (!a || !b) return;
      const cls = e.kind === "case" ? (e.stance === "supports" ? "for" : "against") : "attack";
      if (a.x === b.x) {   // two points in one column answer each other: arcs on the right
        const key = [e.from, e.to].sort().join("|"), k = (pairs[key] = (pairs[key] || 0) + 1);
        const x0 = a.x + a.w, dp = 46 + 34 * (k - 1), sy = my(a) + (a.y < b.y ? 10 : -10), ty = my(b) + (a.y < b.y ? -10 : 10);
        const mutual = p.edges.some((x) => x.kind === "attack" && x.from === e.to && x.to === e.from && x.type === e.type);
        const label = mutual ? (k === 1 ? { rebut: "rebut each other", undermine: "undermine each other", undercut: "undercut each other" }[e.type] : null) : VERB[e.type];
        edge(e.from, e.to, cls, `M${x0},${sy} C${x0 + dp},${sy} ${x0 + dp},${ty} ${x0 + 2},${ty}`, label, x0 + dp + 54, (sy + ty) / 2 + 4);
      } else {
        const [d, lx, ly] = across(a, b);
        edge(e.from, e.to, cls, d, e.kind === "case" ? cls : VERB[e.type], lx, ly);
      }
    });
    [...new Map(p.links.map((l) => [l.argument + l.part, l])).values()].forEach((l) => {
      const a = pos[l.part], b = pos[l.argument]; if (!a || !b) return;
      const lx = PX + PW + 36 + 16 * lane++, ex = b.x + 28, top = b.y - 18;
      edge(l.part, l.argument, "link", `M${a.x + a.w},${my(a)} H${lx} V${top} H${ex} V${b.y - 2}`,
           `rests on ${l.part}, which is ${WORD[l.part_signal].toLowerCase()}`, (lx + ex) / 2 + 40, top - 6);
    });
  });

  const nodeEl = (id, cls, extra) => {
    const b = pos[id], g = el("g", { class: "node " + cls, tabindex: "0", role: "button", "data-id": id });
    g.append(el("rect", { x: b.x, y: b.y, width: b.w, height: b.h, rx: 8 }));
    extra(g, b); nodeG.append(g);
  };
  nodeEl("Q", "q", (g, b) => {
    wrap(D.question.plain, 26, 5).forEach((t, i) => g.append(el("text", { x: b.x + 16, y: b.y + 32 + i * 23, class: "ttl" }, t)));
    g.append(el("text", { x: b.x + 16, y: b.y + b.h - 14, class: "sub" }, "the question · no overall verdict"));
  });
  D.parts.forEach((p) => {
    nodeEl(p.id, "part st-" + p.signal.split(" ")[0], (g, b) => {
      g.append(el("text", { x: b.x + 14, y: b.y + 20, class: "pid" }, p.id + " · " + p.kind));
      wrap(p.text, 31, 3).forEach((t, i) => g.append(el("text", { x: b.x + 14, y: b.y + 42 + i * 19, class: "ttl" }, t)));
      g.append(el("text", { x: b.x + 14, y: b.y + b.h - 12, class: "word" }, WORD[p.signal]));
    });
    p.nodes.forEach((n) => nodeEl(n.id, (n.stance === "supports" ? "pro " : "con ") + (STATE[n.state] || ""), (g, b) => {
      wrap(n.title, 30, 3).forEach((t, i) => g.append(el("text", { x: b.x + 12, y: b.y + 24 + i * 18, class: "ttl" }, t)));
      g.append(el("text", { x: b.x + 12, y: b.y + b.h - 11, class: "sub" }, (n.stance === "supports" ? "for" : "against") + " · " + (n.state === "stands" ? "holds" : n.state) + (n.role === "objection" ? " · an answer" : "")));
    }));
  });
  const clusters = bands;

  // ---------- pan and zoom ----------
  const svg = $("g");
  let view = { k: 1, tx: 0, ty: 0 };
  const apply = () => world.setAttribute("transform", `translate(${view.tx},${view.ty}) scale(${view.k})`);
  const box = () => svg.getBoundingClientRect();
  const panelW = () => (window.innerWidth > 760 && !$("panel").hidden ? 384 : 0);
  function fitTo(x0, y0, w, h0, max = 1.2) {
    const r = box(), aw = r.width - panelW() - 40, ah = r.height - 40;
    const k = Math.min(aw / w, ah / h0, max);
    view = { k, tx: 20 + (aw - w * k) / 2 - x0 * k, ty: 20 + (ah - h0 * k) / 2 - y0 * k }; apply();
  }
  const fitAll = () => fitTo(-20, -20, width + 40, fullH + 40);
  const fitWidth = () => { const r = box(), aw = r.width - panelW() - 40, k = Math.min(aw / (width + 40), 1); view = { k, tx: 20 + (aw - (width + 40) * k) / 2 + 20 * k, ty: 20 + 20 * k }; apply(); };
  function zoomAt(f, px, py) { const k = Math.min(3, Math.max(0.08, view.k * f)); f = k / view.k; view = { k, tx: px - (px - view.tx) * f, ty: py - (py - view.ty) * f }; apply(); }
  svg.addEventListener("wheel", (ev) => {   // scroll moves; pinch or ctrl+scroll zooms
    ev.preventDefault(); const r = box();
    if (ev.ctrlKey || ev.metaKey) zoomAt(Math.exp(-ev.deltaY * 0.01), ev.clientX - r.left, ev.clientY - r.top);
    else { view.tx -= ev.deltaX; view.ty -= ev.deltaY; apply(); }
  }, { passive: false });
  const pts = new Map(); let moved = 0, pinch = null;
  svg.addEventListener("pointerdown", (ev) => { svg.setPointerCapture(ev.pointerId); pts.set(ev.pointerId, { x: ev.clientX, y: ev.clientY }); moved = 0; svg.classList.add("dragging");
    if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch = Math.hypot(a.x - b.x, a.y - b.y); } });
  svg.addEventListener("pointermove", (ev) => {
    const prev = pts.get(ev.pointerId); if (!prev) return;
    const cur = { x: ev.clientX, y: ev.clientY }; pts.set(ev.pointerId, cur);
    if (pts.size === 2 && pinch) { const [a, b] = [...pts.values()], d = Math.hypot(a.x - b.x, a.y - b.y), r = box(); zoomAt(d / pinch, (a.x + b.x) / 2 - r.left, (a.y + b.y) / 2 - r.top); pinch = d; moved += 10; return; }
    view.tx += cur.x - prev.x; view.ty += cur.y - prev.y; moved += Math.abs(cur.x - prev.x) + Math.abs(cur.y - prev.y); apply();
  });
  const up = (ev) => { pts.delete(ev.pointerId); if (pts.size < 2) pinch = null; if (!pts.size) svg.classList.remove("dragging"); };
  svg.addEventListener("pointerup", (ev) => {
    up(ev);
    if (moved > 6) return;
    const g = document.elementFromPoint(ev.clientX, ev.clientY)?.closest(".node");
    g ? select(g.dataset.id) : select(null);
  });
  svg.addEventListener("pointercancel", up);
  nodeG.addEventListener("keydown", (ev) => { const g = ev.target.closest(".node"); if (g && (ev.key === "Enter" || ev.key === " ")) { ev.preventDefault(); select(g.dataset.id, true); } });
  $("zin").onclick = () => { const r = box(); zoomAt(1.3, r.width / 2, r.height / 2); };
  $("zout").onclick = () => { const r = box(); zoomAt(1 / 1.3, r.width / 2, r.height / 2); };
  $("fit").onclick = () => { select(null); fitAll(); };
  D.parts.forEach((p) => { const o = h("option", null, p.id + ". " + p.text); o.value = p.id; $("find").append(o); });
  $("find").onchange = () => { const id = $("find").value; if (id) select(id, true); $("find").value = ""; };
  window.addEventListener("resize", fitWidth);

  // ---------- selection and the details panel ----------
  const partOf = (id) => D.parts.find((p) => p.id === id || p.nodes.some((n) => n.id === id));
  function select(id, zoom) {
    svg.classList.toggle("focus", !!id && id !== "Q");
    // A part lights up its whole band; an argument lights up what it touches.
    const part = byId[id];
    const near = new Set(!id ? [] : part ? [id, ...part.nodes.map((n) => n.id), ...part.links.map((l) => l.part)] : [id, ...(adj[id] || [])]);
    const edgeNear = (a, b) => !!id && (part ? near.has(a) && near.has(b) : a === id || b === id);
    svg.querySelectorAll(".node").forEach((g) => { g.classList.toggle("sel", g.dataset.id === id); g.classList.toggle("near", near.has(g.dataset.id)); });
    svg.querySelectorAll("[data-a]").forEach((e) => e.classList.toggle("near", edgeNear(e.dataset.a, e.dataset.b)));
    const panel = $("panel");
    panel.hidden = false;
    if (!id || id === "Q") overview(panel);
    else if (byId[id]) partPanel(panel, byId[id]);
    else { const p = partOf(id); argPanel(panel, p, p.nodes.find((n) => n.id === id)); }
    if (zoom && id && id !== "Q") { const c = clusters.find((c) => c.id === partOf(id).id); fitTo(PX - 30, c.y - 40, width - PX + 60, c.h + 80, 1); }
  }
  function whyLine(p, n) {
    const att = p.edges.filter((e) => e.kind === "attack" && e.to === n.id).map((e) => ({ e, s: p.nodes.find((x) => x.id === e.from) }));
    const l = p.links.find((x) => x.argument === n.id && x.effect !== "holds");
    if (n.state === "rejected at checking") return "Struck at checking: " + (n.check_note || "it could not be supported.");
    if (n.state === "falls") { if (l) return `Falls because it rests on ${l.part}, which is ${l.part_signal}.`; const a = att.find((x) => x.s.state === "stands") || att[0]; return a ? `Falls: ${q(a.s.title)} ${WHYVERB[a.e.type]} ${a.e.note}.` : "Falls."; }
    if (n.state === "open") { if (l) return `Open: it rests on ${l.part}, which is still open.`; const a = att.find((x) => x.s.state === "open") || att[0]; return a ? `Open: it and ${q(a.s.title)} block each other until one is shown to be stronger.` : "Open."; }
    if (n.state === "stands") return att.length ? `Holds: ${att.map((a) => q(a.s.title)).join(" and ")} did not hold up against it.` : "Holds: nothing that stands answers it.";
    return "Not yet checked.";
  }
  const close = () => { const b = h("button", "x", "Close"); b.type = "button"; b.onclick = () => select(null); return b; };
  function overview(panel) {
    const hide = h("button", "x", "Hide"); hide.type = "button"; hide.onclick = () => { panel.hidden = true; };
    panel.replaceChildren(hide, h("p", "eyebrow", "How to read this"), h("h2", null, D.question.plain));
    panel.append(h("p", null, "Read left to right: the question, its parts, the arguments for and against each part, and the answers to those arguments. Red arrows are attacks. Nothing adds the parts up."));
    const counts = {}; D.parts.forEach((p) => { counts[WORD[p.signal]] = (counts[WORD[p.signal]] || 0) + 1; });
    const ul = h("ul"); Object.entries(counts).forEach(([w, n]) => ul.append(h("li", null, `${w}: ${n} ${n === 1 ? "part" : "parts"}`)));
    panel.append(h("h3", null, "Where the parts stand"), ul, h("p", "note", "Tap any box to see why it stands, falls or stays open. Drag or scroll to move around; pinch or ctrl+scroll to zoom."));
    panel.append(h("h3", null, "How it was reworded"), h("p", "note", "Heard as " + q(D.question.original) + ". " + D.question.reframe_note));
    panel.append(h("p", "meta", "As of " + D.as_of + " · version " + D.version + " · artifact sha256 " + D.digest));
  }
  function partPanel(panel, p) {
    panel.replaceChildren(close(), h("p", "eyebrow", `${p.id} · a question of ${p.kind}`), h("h2", null, p.text));
    const v = h("p"); v.append(h("b", null, WORD[p.signal] + ". "), p.plain); panel.append(v);
    const lines = [...p.hinge_lines, ...p.link_lines, ...p.judgment_lines];
    if (lines.length) { const ul = h("ul"); lines.forEach((t) => ul.append(h("li", null, t))); panel.append(h("h3", null, "It turns on"), ul); }
    panel.append(h("h3", null, "What would settle it"), h("p", null, p.settle_by));
    const steps = D.actions.filter((a) => a.settles.includes(p.id));
    if (steps.length) { const ul = h("ul"); steps.forEach((a) => { const li = h("li", null, a.text + " "); li.append(h("span", "note", "Who: " + a.who + ".")); ul.append(li); }); panel.append(h("h3", null, "A step both sides could take"), ul); }
  }
  function argPanel(panel, p, n) {
    panel.replaceChildren(close(), h("p", "eyebrow", `${n.stance === "supports" ? "For" : "Against"} ${p.id}${n.role === "objection" ? " · an answer" : ""}`), h("h2", null, n.title), h("p", "why", whyLine(p, n)), h("p", null, n.reasoning));
    const ul = h("ul");
    n.evidence.forEach((e) => {
      const li = h("li", null, e.text + " ");
      if (e.from_part) { const b = h("button", "jump", `(this is part ${e.from_part}: ${WORD[byId[e.from_part].signal].toLowerCase()})`); b.type = "button"; b.onclick = () => select(e.from_part, true); li.append(b); }
      else if (e.sources.length) { li.append("("); e.sources.forEach((s, i) => { const a = h("a", null, s.publisher + ", " + s.date); a.href = s.url; a.target = "_blank"; a.rel = "noopener"; a.title = s.title; li.append(i ? ", " : "", a); }); li.append(")"); }
      ul.append(li);
    });
    panel.append(h("h3", null, "Evidence"), ul);
    const meets = p.edges.filter((e) => e.kind === "attack" && (e.from === n.id || e.to === n.id));
    if (meets.length) { const m = h("ul"); meets.forEach((e) => m.append(h("li", null, `${q(p.nodes.find((x) => x.id === e.from).title)} ${VERB[e.type]} ${q(p.nodes.find((x) => x.id === e.to).title)}: ${e.note}`))); panel.append(h("h3", null, "How it meets the other side"), m); }
    p.preferences.filter((x) => x.preferred === n.id || x.over === n.id).forEach((x) => panel.append(h("p", "note", `Judged stronger: ${q(p.nodes.find((y) => y.id === x.preferred).title)} over ${q(p.nodes.find((y) => y.id === x.over).title)}. ${x.rationale} This is a judgment call, open to challenge.`)));
    if (n.check_note) panel.append(h("p", "note", "Checking: " + n.check_note));
  }

  select(null);
  fitWidth();
})();
</script>
</body>
</html>
"""
