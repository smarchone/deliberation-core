"""The interactive graph page (graph.html): one self-contained file.

`viz.render_html` fills in __TITLE__ and __DATA__. Everything else is static,
so the page is as reproducible as the artifact it is drawn from: no clock, no
randomness, and the layout is computed in the browser from the data.
"""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="claude:viewport-fit-sides" content="cover">
<title>__TITLE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600&family=Public+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a reading column of parts on the left, the selected part's argument
   graph in the middle, and what a tapped point means on the right. */
:root {
  --bg: #f6f7f9; --surface: #ffffff; --ink: #1d2430; --muted: #5d6675; --line: #d5dae2;
  --pro: #2c6e8a; --pro-tint: #e3eff4; --con: #8a4a78; --con-tint: #f4e6f0;
  --part: #273246; --part-tint: #e8ebf1; --attack: #9a3b2e; --focus: #3a63c7;
  --display: "Newsreader", "Iowan Old Style", Georgia, serif;
  --body: "Public Sans", "Segoe UI", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #12161d; --surface: #1a2029; --ink: #e6e9ef; --muted: #9aa3b2; --line: #2e3643;
  --pro: #7fb8d1; --pro-tint: #1c2e37; --con: #d29cc4; --con-tint: #33222f;
  --part: #c9d2e3; --part-tint: #232b38; --attack: #e48a7a; --focus: #8fb0ff; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #12161d; --surface: #1a2029; --ink: #e6e9ef; --muted: #9aa3b2; --line: #2e3643;
  --pro: #7fb8d1; --pro-tint: #1c2e37; --con: #d29cc4; --con-tint: #33222f;
  --part: #c9d2e3; --part-tint: #232b38; --attack: #e48a7a; --focus: #8fb0ff; color-scheme: dark; }
* { box-sizing: border-box; }
html, body { height: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5 var(--body);
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
header { padding-block: 20px 12px; max-width: 1400px; margin: 0 auto; display: grid; gap: 4px; }
h1 { font: 600 clamp(1.3rem, 2.4vw, 1.8rem)/1.2 var(--display); margin: 0; text-wrap: balance; max-width: 60ch; }
.heard { color: var(--muted); margin: 0; max-width: 75ch; }
.meta { color: var(--muted); font: 12px var(--mono); margin: 0; }
main { max-width: 1400px; margin: 0 auto; display: grid; grid-template-columns: 300px minmax(0, 1fr) 360px; gap: 16px; padding-block: 8px 24px; }
nav ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
nav button { all: unset; box-sizing: border-box; width: 100%; display: grid; grid-template-columns: 36px 1fr; gap: 2px 8px; padding: 8px 10px; border-radius: 6px; cursor: pointer; }
nav button:hover { background: var(--part-tint); }
nav button[aria-current="true"] { background: var(--surface); box-shadow: inset 0 0 0 1px var(--line); }
nav button:focus-visible, .node:focus-visible, .panel button:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.pid { font: 500 12px/1.6 var(--mono); color: var(--muted); }
.ptext { font-size: 13.5px; line-height: 1.35; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.chip { grid-column: 2; justify-self: start; font-size: 11.5px; letter-spacing: .02em; padding: 1px 8px; border-radius: 999px; border: 1px solid var(--line); color: var(--muted); }
.chip.s-supported, .chip.s-challenged, .chip.s-both { color: var(--ink); border-color: var(--ink); }
.chip.s-contested { border-style: dashed; color: var(--ink); }
.stage { min-width: 0; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; display: grid; grid-template-rows: auto 1fr auto; }
.stage-head { padding: 14px 16px 0; display: grid; gap: 2px; }
.stage-head .kind { font: 12px var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
.stage-head h2 { font: 600 1.15rem/1.3 var(--display); margin: 0; text-wrap: balance; }
.canvas { overflow: auto; padding: 8px; min-width: 0; }
svg { display: block; margin: 0 auto; max-width: 100%; height: auto; }
nav { min-width: 0; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; padding: 10px 16px 14px; color: var(--muted); font-size: 12px; border-top: 1px solid var(--line); }
.legend span::before { content: ""; display: inline-block; width: 18px; height: 0; vertical-align: middle; margin-right: 6px; border-top: 2px solid var(--muted); }
.legend .l-for::before { border-color: var(--pro); }
.legend .l-against::before { border-color: var(--con); }
.legend .l-attack::before { border-color: var(--attack); border-top-width: 3px; }
.legend .l-falls::before { border-top-style: dotted; }
.edge { fill: none; stroke-width: 1.6; }
.edge.for { stroke: var(--pro); } .edge.against { stroke: var(--con); }
.edge.attack { stroke: var(--attack); stroke-width: 2.4; }
.edge.link { stroke: var(--part); stroke-dasharray: 5 4; }
.elabel { font: 11px var(--body); fill: var(--muted); paint-order: stroke; stroke: var(--surface); stroke-width: 4px; }
.elabel.attack { fill: var(--attack); font-weight: 600; }
.mk-for { fill: var(--pro); } .mk-against { fill: var(--con); } .mk-attack { fill: var(--attack); } .mk-link { fill: var(--part); }
.node { cursor: pointer; }
.node rect { fill: var(--surface); stroke: var(--line); stroke-width: 1.2; }
.node.pro rect { fill: var(--pro-tint); stroke: var(--pro); }
.node.con rect { fill: var(--con-tint); stroke: var(--con); }
.node.part rect { fill: var(--part-tint); stroke: var(--part); stroke-width: 1.6; }
.node.linkn rect { fill: var(--surface); stroke: var(--part); stroke-dasharray: 5 4; }
.node.open rect { stroke-dasharray: 6 4; stroke-width: 1.8; }
.node.falls { opacity: .55; }
.node.falls .ttl { text-decoration: line-through; }
.node .ttl { font: 600 13px var(--body); fill: var(--ink); }
.node.part .ttl { font: 600 14px var(--display); }
.node .sub { font: 11.5px var(--body); fill: var(--muted); }
.node.sel rect { stroke: var(--focus); stroke-width: 2.6; }
svg.focused .node:not(.near), svg.focused .edge:not(.near), svg.focused .elabel:not(.near) { opacity: .22; }
.panel { min-width: 0; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px; align-self: start; position: sticky; top: max(12px, env(safe-area-inset-top, 0px)); max-height: calc(100vh - 24px); overflow: auto; display: grid; gap: 10px; }
.panel .eyebrow { font: 12px var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin: 0; }
.panel h3 { font: 600 1.1rem/1.3 var(--display); margin: 0; text-wrap: balance; }
.panel p { margin: 0; max-width: 65ch; }
.panel .state { font-weight: 600; }
.panel h4 { font: 600 12px var(--body); text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 6px 0 0; }
.panel ul { margin: 0; padding-left: 18px; display: grid; gap: 6px; }
.panel a { color: var(--focus); }
.panel button.jump { all: unset; color: var(--focus); text-decoration: underline; cursor: pointer; }
.panel .note { color: var(--muted); font-size: 13px; }
footer { max-width: 1400px; margin: 0 auto; padding-block: 0 24px; color: var(--muted); font-size: 12.5px; overflow-wrap: anywhere; }
@media (max-width: 1100px) { main { grid-template-columns: 260px minmax(0, 1fr); } .panel { grid-column: 1 / -1; position: static; max-height: none; } }
@media (max-width: 720px) {
  main { grid-template-columns: minmax(0, 1fr); }
  nav ol { display: flex; overflow-x: auto; gap: 6px; padding-bottom: 4px; }
  nav li { flex: 0 0 210px; }
  svg { max-width: none; }
}
@media (prefers-reduced-motion: no-preference) { .node, .edge, .elabel { transition: opacity .15s; } }
</style>
</head>
<body>
<header>
  <h1 id="q"></h1>
  <p class="heard" id="heard"></p>
  <p class="meta" id="meta"></p>
</header>
<main>
  <nav aria-label="Parts of the claim"><ol id="parts"></ol></nav>
  <section class="stage" aria-live="polite">
    <div class="stage-head"><span class="kind" id="kind"></span><h2 id="ptitle"></h2></div>
    <div class="canvas"><svg id="g" role="img" aria-label="Argument graph"></svg></div>
    <div class="legend">
      <span class="l-for">for the part</span><span class="l-against">against the part</span>
      <span class="l-attack">attack</span><span class="l-falls">struck through: falls</span>
      <span>dashed outline: open</span><span>tap a box for details · ↑ ↓ switch parts</span>
    </div>
  </section>
  <aside class="panel" id="panel"></aside>
</main>
<footer id="foot"></footer>
<script type="application/json" id="data">__DATA__</script>
<script>
(() => {
  const D = JSON.parse(document.getElementById("data").textContent);
  const $ = (id) => document.getElementById(id);
  const NS = "http://www.w3.org/2000/svg";
  const W = 220, H = 84, PW = 300, PH = 96, GX = 28, GY = 120, PAD = 24;
  const SIDE = { supports: "pro", challenges: "con" };
  const SIDE_WORD = { supports: "For", challenges: "Against" };
  const VERB = { rebut: "rebuts", undermine: "undermines", undercut: "undercuts" };
  const byId = Object.fromEntries(D.parts.map((p) => [p.id, p]));
  let current = null, selected = null;

  const el = (tag, attrs = {}, text) => {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (text !== undefined) n.textContent = text;
    return n;
  };
  const h = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const chipClass = (s) => "chip s-" + s.split(" ")[0];
  const wrap = (text, n, max) => {
    const lines = []; let cur = "";
    for (const w of text.split(/\s+/)) {
      if ((cur + " " + w).trim().length > n && cur) { lines.push(cur); cur = w; } else cur = (cur + " " + w).trim();
    }
    if (cur) lines.push(cur);
    if (lines.length > max) { lines.length = max; lines[max - 1] = lines[max - 1].replace(/\s*\S*$/, "") + "…"; }
    return lines;
  };

  $("q").textContent = D.question.plain;
  $("heard").textContent = "Heard as: “" + D.question.original + "”. " + D.question.reframe_note;
  $("meta").textContent = "As of " + D.as_of + " · version " + D.version + " · artifact " + D.digest.slice(0, 12);
  $("foot").textContent = "A map of the evidence, not a verdict on any person or party. Each part is checked on its own and the parts are never added up. Drawn from artifact sha256 " + D.digest + ".";

  const list = $("parts");
  D.parts.forEach((p) => {
    const li = h("li"), b = h("button");
    b.type = "button"; b.dataset.id = p.id;
    b.append(h("span", "pid", p.id), h("span", "ptext", p.text), h("span", chipClass(p.signal), p.signal));
    b.addEventListener("click", () => show(p.id));
    li.append(b); list.append(li);
  });

  function layout(p) {
    const cases = p.nodes.filter((n) => n.role !== "objection");
    cases.sort((a, b) => (a.stance === b.stance ? 0 : a.stance === "supports" ? -1 : 1));
    const pos = {};
    const rowW = (n, w) => n * w + (n - 1) * GX;
    const linked = [...new Set(p.links.map((l) => l.part))];
    const objections = p.nodes.filter((n) => n.role === "objection");
    const row2 = [...linked.map((part) => ({ kind: "link", id: "link:" + part, link: p.links.find((l) => l.part === part) })),
                  ...objections.map((n) => ({ kind: "arg", id: n.id }))];
    const width = Math.max(PW, rowW(cases.length, W), rowW(row2.length, W)) + PAD * 2;
    const place = (items, y, w) => { const start = (width - rowW(items.length, w)) / 2; items.forEach((it, i) => { pos[it.id] = { x: start + i * (w + GX), y, w, h: w === PW ? PH : H }; }); };
    pos[p.id] = { x: (width - PW) / 2, y: PAD, w: PW, h: PH };
    place(cases, PAD + PH + GY, W);
    // Objections sit under what they attack, when that is free.
    const order = row2.slice().sort((a, b) => {
      const tx = (it) => { const e = p.edges.find((x) => x.from === it.id && x.kind !== "case"); return e && pos[e.to] ? pos[e.to].x : (it.kind === "link" ? -1 : 1e6); };
      return tx(a) - tx(b);
    });
    place(order, PAD + PH + GY + H + GY, W);
    const height = PAD + PH + GY + H + (row2.length ? GY + H : 90) + PAD + 30;
    return { pos, width, height, row2 };
  }

  function draw(p) {
    const svg = $("g"); svg.replaceChildren(); svg.classList.remove("focused");
    const { pos, width, height, row2 } = layout(p);
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`); svg.setAttribute("width", width); svg.setAttribute("height", height);
    const defs = el("defs");
    for (const k of ["for", "against", "attack", "link"]) {
      const m = el("marker", { id: "mk-" + k, viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" });
      m.append(el("path", { d: "M0,0 L10,5 L0,10 z", class: "mk-" + k })); defs.append(m);
    }
    svg.append(defs);
    const edgeLayer = el("g"), labelLayer = el("g"), nodeLayer = el("g");
    svg.append(edgeLayer, nodeLayer, labelLayer);
    const pairCount = {};
    p.edges.forEach((e) => {
      const a = pos[e.from], b = pos[e.to]; if (!a || !b) return;
      let d, lx, ly;
      if (Math.abs(a.y - b.y) < 1) {
        const key = [e.from, e.to].sort().join("|"); const k = (pairCount[key] = (pairCount[key] || 0) + 1);
        const sx = a.x + a.w / 2 + (a.x < b.x ? 20 : -20), tx = b.x + b.w / 2 + (a.x < b.x ? -20 : 20);
        const y = a.y + a.h, depth = 34 + 30 * (k - 1);
        d = `M${sx},${y} C${sx},${y + depth * 1.4} ${tx},${y + depth * 1.4} ${tx},${y + 2}`;
        lx = (sx + tx) / 2; ly = y + depth * 1.05 + 4;
      } else {
        const up = a.y > b.y;
        const sx = a.x + a.w / 2, sy = up ? a.y : a.y + a.h, tx = b.x + b.w / 2, ty = up ? b.y + b.h + 2 : b.y - 2;
        const my = (sy + ty) / 2;
        d = `M${sx},${sy} C${sx},${my} ${tx},${my} ${tx},${ty}`;
        lx = (sx + tx) / 2; ly = my + 4;
      }
      const cls = e.kind === "case" ? (e.stance === "supports" ? "for" : "against") : e.kind === "link" ? "link" : "attack";
      const near = [e.from, e.to].join(" ");
      edgeLayer.append(el("path", { d, class: "edge " + cls, "marker-end": `url(#mk-${cls})`, "data-ends": near }));
      const word = e.kind === "case" ? (e.stance === "supports" ? "for" : "against") : e.kind === "link" ? e.label : VERB[e.type];
      labelLayer.append(el("text", { x: lx, y: ly, "text-anchor": "middle", class: "elabel " + cls, "data-ends": near }, word));
    });
    const addNode = (id, cls, lines, sub, onClick, label) => {
      const b = pos[id]; const g = el("g", { class: "node " + cls, tabindex: "0", role: "button", "aria-label": label, "data-id": id });
      g.append(el("rect", { x: b.x, y: b.y, width: b.w, height: b.h, rx: 7 }));
      const top = b.y + b.h / 2 - ((lines.length + (sub ? 1 : 0)) * 17) / 2 + 13;
      lines.forEach((t, i) => g.append(el("text", { x: b.x + 12, y: top + i * 17, class: "ttl" }, t)));
      if (sub) g.append(el("text", { x: b.x + 12, y: top + lines.length * 17 + 2, class: "sub" }, sub));
      g.addEventListener("click", onClick);
      g.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); onClick(); } });
      nodeLayer.append(g);
    };
    addNode(p.id, "part", wrap(p.id + ". " + p.text, 38, 3), p.signal, () => select(null), p.id + ", " + p.signal);
    p.nodes.forEach((n) => {
      const state = n.state.split(" ")[0];
      const sub = n.state + (n.role === "objection" ? " · objection" : "");
      addNode(n.id, `${SIDE[n.stance]} ${state === "rejected" ? "falls" : state}`, wrap(n.title, 27, 3), sub, () => select(n.id), `${SIDE_WORD[n.stance]}: ${n.title}, ${n.state}`);
    });
    row2.filter((r) => r.kind === "link").forEach((r) => {
      const l = r.link;
      addNode(r.id, "linkn", wrap("Rests on " + l.part + ": " + byId[l.part].text, 27, 2), l.part_signal, () => show(l.part), "Open part " + l.part);
    });
  }

  function argDetail(p, n) {
    const panel = $("panel"); panel.replaceChildren();
    panel.append(h("p", "eyebrow", `${SIDE_WORD[n.stance]} ${p.id} · ${n.role === "objection" ? "objection" : "case"}`), h("h3", null, n.title));
    const attackers = p.edges.filter((e) => e.kind === "attack" && e.to === n.id);
    const links = p.links.filter((l) => l.argument === n.id);
    const state = h("p"); state.append(h("span", "state", n.state.charAt(0).toUpperCase() + n.state.slice(1) + ". "));
    const why = [];
    attackers.forEach((e) => { const s = p.nodes.find((x) => x.id === e.from); why.push(`“${s.title}” ${VERB[e.type]} it (${s.state})`); });
    links.filter((l) => l.effect !== "holds").forEach((l) => why.push(`it rests on ${l.part}, which is ${l.part_signal}`));
    if (why.length) state.append(document.createTextNode(why.join("; ") + "."));
    else if (n.state === "stands") state.append(document.createTextNode("Nothing that stands attacks it."));
    panel.append(state, h("p", null, n.reasoning));
    panel.append(h("h4", null, "Evidence"));
    const ul = h("ul");
    n.evidence.forEach((e) => {
      const li = h("li", null, e.text + " ");
      if (e.from_part) {
        const b = h("button", "jump", `Rests on ${e.from_part}, which is ${byId[e.from_part].signal}`); b.type = "button";
        b.addEventListener("click", () => show(e.from_part)); li.append(b);
      } else e.sources.forEach((s, i) => {
        const a = h("a", null, `${s.publisher}, ${s.date}`); a.href = s.url; a.target = "_blank"; a.rel = "noopener"; a.title = s.title;
        li.append(i ? ", " : "(", a); if (i === e.sources.length - 1) li.append(")");
      });
      ul.append(li);
    });
    panel.append(ul);
    const out = p.edges.filter((e) => e.kind === "attack" && e.from === n.id);
    if (out.length || attackers.length) {
      panel.append(h("h4", null, "How it meets the other side"));
      const m = h("ul");
      [...attackers, ...out].forEach((e) => {
        const s = p.nodes.find((x) => x.id === e.from), t = p.nodes.find((x) => x.id === e.to);
        m.append(h("li", null, `“${s.title}” ${VERB[e.type]} “${t.title}”: ${e.note}`));
      });
      panel.append(m);
    }
    p.preferences.filter((x) => x.preferred === n.id || x.over === n.id).forEach((x) => {
      const a = p.nodes.find((y) => y.id === x.preferred), b = p.nodes.find((y) => y.id === x.over);
      panel.append(h("p", "note", `Judged stronger: “${a.title}” over “${b.title}”. ${x.rationale} This is a judgment call, open to challenge.`));
    });
    if (n.check_note) panel.append(h("p", "note", "Checking: " + n.check_note));
  }

  function partDetail(p) {
    const panel = $("panel"); panel.replaceChildren();
    panel.append(h("p", "eyebrow", `${p.id} · ${p.kind} · ${p.signal}`), h("h3", null, p.text), h("p", null, p.plain));
    const open = [...p.hinge_lines, ...p.link_lines, ...p.judgment_lines];
    if (open.length) { panel.append(h("h4", null, "What it turns on")); const ul = h("ul"); open.forEach((t) => ul.append(h("li", null, t))); panel.append(ul); }
    panel.append(h("h4", null, "What would settle it"), h("p", null, p.settle_by));
    const users = D.parts.filter((q) => q.links.some((l) => l.part === p.id));
    if (users.length) {
      panel.append(h("h4", null, "Parts that rest on this one"));
      const ul = h("ul");
      users.forEach((q) => { const li = h("li"), b = h("button", "jump", `${q.id}. ${q.text}`); b.type = "button"; b.addEventListener("click", () => show(q.id)); li.append(b, ` (${q.signal})`); ul.append(li); });
      panel.append(ul);
    }
    panel.append(h("p", "note", "Tap an argument in the graph to see its evidence and what it faces."));
  }

  function select(id) {
    selected = id;
    const svg = $("g"), p = byId[current];
    svg.classList.toggle("focused", !!id);
    svg.querySelectorAll(".node").forEach((n) => { n.classList.toggle("sel", n.dataset.id === (id || current)); n.classList.toggle("near", !!id && n.dataset.id === id); });
    svg.querySelectorAll("[data-ends]").forEach((e) => {
      const ends = e.dataset.ends.split(" "); const hit = !!id && ends.includes(id);
      e.classList.toggle("near", hit);
      if (hit) ends.forEach((x) => { const n = svg.querySelector(`.node[data-id="${CSS.escape(x)}"]`); if (n) n.classList.add("near"); });
    });
    if (id) argDetail(p, p.nodes.find((n) => n.id === id)); else partDetail(p);
  }

  function show(id) {
    if (!byId[id]) return;
    current = id;
    const p = byId[id];
    list.querySelectorAll("button").forEach((b) => b.setAttribute("aria-current", String(b.dataset.id === id)));
    $("kind").textContent = `${p.kind} · ${p.signal}`; $("ptitle").textContent = `${p.id}. ${p.text}`;
    draw(p); select(null);
    const canvas = document.querySelector(".canvas");
    canvas.scrollLeft = (canvas.scrollWidth - canvas.clientWidth) / 2;
    const cur = list.querySelector(`button[data-id="${CSS.escape(id)}"]`).parentElement;
    if (list.scrollWidth > list.clientWidth) list.scrollLeft = cur.offsetLeft - list.offsetLeft - 8;
    try { history.replaceState(null, "", "#" + id); } catch (e) {}
  }

  document.addEventListener("keydown", (ev) => {
    if (ev.target.closest && ev.target.closest("input, textarea")) return;
    const i = D.parts.findIndex((p) => p.id === current);
    if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
      ev.preventDefault();
      const next = D.parts[(i + (ev.key === "ArrowDown" ? 1 : D.parts.length - 1)) % D.parts.length];
      show(next.id); list.querySelector(`button[data-id="${CSS.escape(next.id)}"]`).focus();
    } else if (ev.key === "Escape") select(null);
  });

  const start = location.hash.slice(1);
  show(byId[start] ? start : D.parts[0].id);
})();
</script>
</body>
</html>
"""
