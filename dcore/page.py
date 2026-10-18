"""The interactive page (graph.html): one self-contained file.

`viz.render_html` fills in __TITLE__ and __DATA__. Everything else is static,
so the page is as reproducible as the artifact it is drawn from: no clock, no
randomness, and the layout is computed in the browser from the data.

Two views, to keep the reading load low:
  the map    every part on one page, how each stands in a word, and which
             parts rest on which (in rows); the question gets no verdict
  a part     its two sides as plain sentences: what holds, what was struck
             and why, what it turns on, and what would settle it
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
/* Layout: one reading column. The map lays the parts out in rows, a row for
   each layer of "rests on"; a part opens as a two-column tally of its sides. */
:root {
  --bg: #f6f7f9; --surface: #ffffff; --ink: #1d2430; --muted: #5d6675; --faint: #8a93a2; --line: #d8dde4;
  --pro: #2c6e8a; --pro-tint: #e6f0f4; --con: #8a4a78; --con-tint: #f5e9f2;
  --open: #6b5d2e; --attack: #9a3b2e; --focus: #3a63c7;
  --display: "Newsreader", "Iowan Old Style", Georgia, serif;
  --body: "Public Sans", "Segoe UI", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #12161d; --surface: #1a2029; --ink: #e6e9ef; --muted: #a3acba; --faint: #7a8494; --line: #2e3643;
  --pro: #82bbd3; --pro-tint: #1b2c35; --con: #d4a0c6; --con-tint: #31212d;
  --open: #d8c48a; --attack: #e48a7a; --focus: #8fb0ff; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #12161d; --surface: #1a2029; --ink: #e6e9ef; --muted: #a3acba; --faint: #7a8494; --line: #2e3643;
  --pro: #82bbd3; --pro-tint: #1b2c35; --con: #d4a0c6; --con-tint: #31212d;
  --open: #d8c48a; --attack: #e48a7a; --focus: #8fb0ff; color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.55 var(--body);
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.wrap { max-width: 1040px; margin: 0 auto; padding-block: 28px 40px; display: grid; gap: 28px; }
.stack { display: grid; gap: 14px; }
.stack.wide { gap: 22px; }
h1 { font: 600 clamp(1.45rem, 3vw, 2.1rem)/1.2 var(--display); margin: 0; text-wrap: balance; max-width: 34ch; }
h2 { font: 600 clamp(1.25rem, 2.4vw, 1.6rem)/1.25 var(--display); margin: 0; text-wrap: balance; max-width: 40ch; }
h3 { font: 600 13px var(--body); text-transform: uppercase; letter-spacing: .07em; color: var(--muted); margin: 0; }
p { margin: 0; }
a { color: var(--focus); }
button { font: inherit; color: inherit; }
button:focus-visible, summary:focus-visible, a:focus-visible, .node:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; border-radius: 4px; }
.lede { color: var(--muted); max-width: 62ch; }
.top { display: grid; gap: 10px; }
details.reframe summary { cursor: pointer; color: var(--muted); font-size: 14px; }
details.reframe p { margin-top: 6px; color: var(--muted); font-size: 14px; max-width: 70ch; }
.meta { font: 12px var(--mono); color: var(--faint); overflow-wrap: anywhere; }

/* The map */
.map { display: grid; gap: 10px; }
.tier { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px; }
.tier-label { font: 12px var(--mono); color: var(--faint); }
.tier-label:not(:first-child) { margin-top: 18px; }
.card { all: unset; box-sizing: border-box; cursor: pointer; display: grid; gap: 6px; align-content: start; padding: 12px 14px; border-radius: 8px; background: var(--surface); border: 1.5px solid var(--line); }
.card:hover { border-color: var(--ink); }
.card:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.card .id { font: 500 12px var(--mono); color: var(--faint); }
.card .txt { font-size: 14.5px; line-height: 1.4; }
.word { font: 600 13px var(--body); }
.st-supported { border-color: var(--pro); } .st-supported .word { color: var(--pro); }
.st-challenged { border-color: var(--con); } .st-challenged .word { color: var(--con); }
.st-both { border-color: var(--ink); }
.st-contested { border-style: dashed; border-color: var(--open); } .st-contested .word { color: var(--open); }
.st-unproven, .st-unverified { border-style: dotted; } .st-unproven .word, .st-unverified .word { color: var(--muted); }
.card .rel { font-size: 12.5px; color: var(--muted); border-top: 1px dashed var(--line); padding-top: 6px; }
.card.lit { border-color: var(--focus); box-shadow: 0 0 0 2px var(--focus); }
.key { display: flex; flex-wrap: wrap; gap: 6px 18px; color: var(--muted); font-size: 13.5px; }
.key b { font-weight: 600; color: var(--ink); }

/* A part */
.back { all: unset; cursor: pointer; color: var(--focus); font-size: 15px; justify-self: start; }
.head { display: grid; gap: 8px; }
.eyebrow { font: 12px var(--mono); color: var(--faint); text-transform: uppercase; letter-spacing: .06em; }
.verdict { font-size: 17px; max-width: 62ch; }
.verdict b { font-weight: 600; }
.turns { display: grid; gap: 6px; padding: 14px 16px; background: var(--surface); border-radius: 8px; border: 1px solid var(--line); }
.turns ul { margin: 0; padding-left: 18px; display: grid; gap: 4px; }
.turns h3:not(:first-child) { margin-top: 6px; }
.tally { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; }
.side { display: grid; gap: 14px; align-content: start; min-width: 0; }
.side > h3 { padding-bottom: 6px; border-bottom: 2px solid currentColor; }
.side.pro > h3 { color: var(--pro); } .side.con > h3 { color: var(--con); }
.points { list-style: none; margin: 0; padding: 0; display: grid; gap: 16px; }
.point { display: grid; gap: 4px; padding: 2px 0 2px 14px; border-left: 4px solid transparent; }
.point.flash { background: var(--pro-tint); }
.pro .point.holds { border-color: var(--pro); } .con .point.holds { border-color: var(--con); }
.point.open { border-left-style: dashed; border-color: var(--open); }
.point .claim { font: 600 17px/1.35 var(--display); }
.point.struck .claim { text-decoration: line-through; text-decoration-thickness: 1.5px; color: var(--faint); font-weight: 400; }
.point .why { font: italic 15px/1.45 var(--display); color: var(--muted); }
.point.struck .why { color: var(--attack); }
.point .tag { font-size: 12.5px; color: var(--faint); }
.point details summary { cursor: pointer; font-size: 13.5px; color: var(--focus); width: max-content; max-width: 100%; }
.point details[open] summary { margin-bottom: 6px; }
.point details p, .point details li { font-size: 14.5px; color: var(--ink); }
.point details ul { margin: 6px 0 0; padding-left: 18px; display: grid; gap: 6px; }
.point details .note { color: var(--muted); font-size: 13px; margin-top: 6px; }
.jump { all: unset; cursor: pointer; color: var(--focus); text-decoration: underline; }
.empty { color: var(--faint); font-style: italic; }
.settle { display: grid; gap: 12px; }
.settle ul { margin: 0; padding-left: 18px; display: grid; gap: 8px; max-width: 70ch; }
.settle .who { color: var(--muted); font-size: 14px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { all: unset; cursor: pointer; font-size: 14px; padding: 4px 12px; border-radius: 999px; border: 1px solid var(--line); background: var(--surface); }
.chip:hover { border-color: var(--ink); }
.chip:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
details.graph { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; min-width: 0; }
details.graph summary { cursor: pointer; color: var(--muted); }
.canvas { overflow-x: auto; min-width: 0; margin-top: 10px; }
.canvas svg { display: block; margin: 0 auto; max-width: 100%; height: auto; }
.edge { fill: none; stroke-width: 1.6; } .edge.for { stroke: var(--pro); } .edge.against { stroke: var(--con); }
.edge.attack { stroke: var(--attack); stroke-width: 2.2; } .edge.link { stroke: var(--muted); stroke-dasharray: 5 4; }
.elabel { font: 11px var(--body); fill: var(--muted); paint-order: stroke; stroke: var(--surface); stroke-width: 4px; }
.elabel.attack { fill: var(--attack); font-weight: 600; }
.mk-for { fill: var(--pro); } .mk-against { fill: var(--con); } .mk-attack { fill: var(--attack); } .mk-link { fill: var(--muted); }
.node { cursor: pointer; } .node rect { fill: var(--surface); stroke: var(--line); stroke-width: 1.2; }
.node.pro rect { fill: var(--pro-tint); stroke: var(--pro); } .node.con rect { fill: var(--con-tint); stroke: var(--con); }
.node.part rect { stroke: var(--ink); stroke-width: 1.6; } .node.linkn rect { stroke-dasharray: 5 4; }
.node.open rect { stroke-dasharray: 6 4; } .node.falls { opacity: .5; } .node.falls .ttl { text-decoration: line-through; }
.node .ttl { font: 600 13px var(--body); fill: var(--ink); } .node .sub { font: 11.5px var(--body); fill: var(--muted); }
.pager { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; border-top: 1px solid var(--line); padding-top: 14px; }
.pager button { all: unset; cursor: pointer; color: var(--focus); max-width: 45%; }
.pager button:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
footer { color: var(--muted); font-size: 13px; max-width: 75ch; display: grid; gap: 6px; }
@media (max-width: 720px) {
  .tally { grid-template-columns: 1fr; }
  .tier { grid-template-columns: 1fr; }
  .canvas svg { max-width: none; }
  .pager button { max-width: 100%; }
}
@media (prefers-reduced-motion: no-preference) { .point { transition: background .4s; } }
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <h1 id="q"></h1>
    <p class="lede">Each part of the question is checked on its own, from both sides. The parts are never added up into one answer about any person or party.</p>
    <details class="reframe"><summary>How the question was reworded</summary><p id="heard"></p></details>
  </div>

  <section id="mapview" aria-labelledby="maph">
    <div class="stack">
      <h3 id="maph">Where each part stands</h3>
      <p class="key" id="key"></p>
      <div class="map" id="map"></div>
    </div>
  </section>

  <section id="partview" hidden>
    <div class="stack wide">
      <button class="back" type="button" id="back">← All parts</button>
      <div class="head">
        <span class="eyebrow" id="eyebrow"></span>
        <h2 id="ptext"></h2>
        <p class="verdict" id="verdict"></p>
      </div>
      <div class="turns" id="turns"></div>
      <div class="tally">
        <div class="side pro"><h3>Points for</h3><ul class="points" id="pro"></ul></div>
        <div class="side con"><h3>Points against</h3><ul class="points" id="con"></ul></div>
      </div>
      <div class="settle" id="settle"></div>
      <details class="graph" id="graphbox"><summary>See how these points meet, as a graph</summary><div class="canvas"><svg id="g" role="img" aria-label="Argument graph"></svg></div></details>
      <div class="pager"><button type="button" id="prev"></button><button type="button" id="next"></button></div>
    </div>
  </section>

  <footer>
    <p id="foot"></p>
    <p class="meta" id="meta"></p>
  </footer>
</div>
<script type="application/json" id="data">__DATA__</script>
<script>
(() => {
  const D = JSON.parse(document.getElementById("data").textContent);
  const $ = (id) => document.getElementById(id);
  const byId = Object.fromEntries(D.parts.map((p) => [p.id, p]));
  const VERB = { rebut: "contradicts it:", undermine: "disputes its evidence:", undercut: "says it doesn't follow:" };
  const WORD = { "supported": "Supported", "challenged": "Challenged", "both hold in part": "Both hold in part",
                 "contested": "Open", "unproven either way": "Unproven either way", "unverified": "Not yet checked" };
  const stClass = (s) => "st-" + s.split(" ")[0];
  const h = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const q = (t) => "“" + t + "”";

  $("q").textContent = D.question.plain;
  $("heard").textContent = "Heard as: " + q(D.question.original) + ". " + D.question.reframe_note;
  $("foot").textContent = "A map of the evidence, not a verdict. Everything here is computed from the checked arguments and their sources, and anyone can rebuild it and get the same result.";
  $("meta").textContent = "As of " + D.as_of + " · version " + D.version + " · artifact sha256 " + D.digest;

  // ---- the map ----
  const depth = {};
  const depthOf = (p) => depth[p.id] ?? (depth[p.id] = p.links.length ? 1 + Math.max(...p.links.map((l) => depthOf(byId[l.part]))) : 0);
  D.parts.forEach(depthOf);
  const counts = {};
  D.parts.forEach((p) => { counts[WORD[p.signal]] = (counts[WORD[p.signal]] || 0) + 1; });
  const key = $("key");
  Object.entries(counts).forEach(([w, n]) => { const s = h("span"); s.append(h("b", null, w), " " + n + (n === 1 ? " part" : " parts")); key.append(s); });
  const map = $("map");
  const tiers = Math.max(...Object.values(depth));
  for (let t = 0; t <= tiers; t++) {
    if (tiers > 0) map.append(h("div", "tier-label", t === 0 ? "Parts that stand on their own evidence" : "Parts that rest on the ones above"));
    const row = h("div", "tier");
    D.parts.filter((p) => depth[p.id] === t).forEach((p) => {
      const b = h("button", "card " + stClass(p.signal)); b.type = "button"; b.dataset.id = p.id;
      b.append(h("span", "id", p.id), h("span", "txt", p.text), h("span", "word", WORD[p.signal]));
      const ups = [...new Set(p.links.map((l) => l.part))], downs = D.parts.filter((x) => x.links.some((l) => l.part === p.id)).map((x) => x.id);
      if (ups.length) b.append(h("span", "rel", "Rests on " + ups.join(", ")));
      if (downs.length) b.append(h("span", "rel", downs.join(", ") + " rests on this"));
      const related = [...ups, ...downs];
      const light = (on) => related.forEach((id) => map.querySelector(`.card[data-id="${id}"]`).classList.toggle("lit", on));
      b.addEventListener("mouseenter", () => light(true)); b.addEventListener("mouseleave", () => light(false));
      b.addEventListener("focus", () => light(true)); b.addEventListener("blur", () => light(false));
      b.addEventListener("click", () => go(p.id));
      row.append(b);
    });
    map.append(row);
  }
  const NS = "http://www.w3.org/2000/svg";

  // ---- a part ----
  const attackersOf = (p, id) => p.edges.filter((e) => e.kind === "attack" && e.to === id).map((e) => ({ e, s: p.nodes.find((n) => n.id === e.from) }));
  function whyLine(p, n) {
    const att = attackersOf(p, n.id);
    const link = p.links.find((l) => l.argument === n.id && l.effect !== "holds");
    if (n.state === "rejected at checking") return "Struck at checking: " + (n.check_note || "it could not be supported.");
    if (n.state === "falls") {
      if (link) return `Struck because it rests on ${link.part}, which is ${link.part_signal}.`;
      const a = att.find((x) => x.s.state === "stands") || att[0];
      return a ? `Struck: ${q(a.s.title)} ${VERB[a.e.type]} ${a.e.note}.` : "Struck.";
    }
    if (n.state === "open") {
      if (link) return `Undecided: it rests on ${link.part}, which is still open.`;
      const a = att.find((x) => x.s.state === "open") || att[0];
      return a ? `Undecided: it and ${q(a.s.title)} cancel each other out until one is shown to be stronger.` : "Undecided.";
    }
    if (n.state === "stands") return att.length ? `Holds: ${att.map((a) => q(a.s.title)).join(" and ")} did not hold up against it.` : "Holds: nothing that stands answers it.";
    return "Not yet checked.";
  }
  function pointEl(p, n) {
    const cls = { stands: "holds", falls: "struck", open: "open", "rejected at checking": "struck" }[n.state] || "";
    const li = h("li", "point " + cls); li.id = "pt-" + n.id;
    li.append(h("p", "claim", n.title), h("p", "why", whyLine(p, n)));
    const target = p.edges.find((e) => e.kind === "attack" && e.from === n.id);
    if (n.role === "objection" && target) li.append(h("p", "tag", "An answer to " + q(p.nodes.find((x) => x.id === target.to).title) + ", not a case on its own"));
    const d = h("details"); d.append(h("summary", null, "Reasoning and sources"), h("p", null, n.reasoning));
    const ul = h("ul");
    n.evidence.forEach((e) => {
      const it = h("li", null, e.text + " ");
      if (e.from_part) {
        const b = h("button", "jump", `(this is part ${e.from_part}, which is ${byId[e.from_part].signal})`); b.type = "button";
        b.addEventListener("click", () => go(e.from_part)); it.append(b);
      } else if (e.sources.length) {
        it.append("(");
        e.sources.forEach((s, i) => { const a = h("a", null, s.publisher + ", " + s.date); a.href = s.url; a.target = "_blank"; a.rel = "noopener"; a.title = s.title; it.append(i ? ", " : "", a); });
        it.append(")");
      }
      ul.append(it);
    });
    d.append(ul);
    if (n.check_note) d.append(h("p", "note", "Checking: " + n.check_note));
    li.append(d);
    return li;
  }
  const chip = (id, text) => { const b = h("button", "chip", text); b.type = "button"; b.addEventListener("click", () => go(id)); return b; };
  function showPart(p) {
    $("eyebrow").textContent = `${p.id} · a question of ${p.kind}`;
    $("ptext").textContent = p.text;
    $("verdict").replaceChildren(h("b", null, WORD[p.signal] + ". "), p.plain);
    const turns = $("turns"); turns.replaceChildren();
    const lines = [...p.hinge_lines, ...p.link_lines, ...p.judgment_lines];
    if (lines.length) { const ul = h("ul"); lines.forEach((t) => ul.append(h("li", null, t))); turns.append(h("h3", null, "It turns on"), ul); }
    turns.append(h("h3", null, "What would settle it"), h("p", null, p.settle_by));
    // Cases first, strongest first; answers to the other side's points after them.
    const rank = (n) => (n.role === "objection" ? 10 : 0) + ({ stands: 0, open: 1, "not yet checked": 2, falls: 3, "rejected at checking": 4 }[n.state] ?? 5);
    for (const [side, stance] of [["pro", "supports"], ["con", "challenges"]]) {
      const ul = $(side); ul.replaceChildren();
      const pts = p.nodes.filter((n) => n.stance === stance).sort((a, b) => rank(a) - rank(b));
      pts.forEach((n) => ul.append(pointEl(p, n)));
      if (!pts.length) ul.append(h("li", "empty", "No point on this side yet."));
    }
    const settle = $("settle"); settle.replaceChildren();
    const steps = D.actions.filter((a) => a.settles.includes(p.id));
    if (steps.length) {
      const ul = h("ul");
      steps.forEach((a) => { const li = h("li"); li.append(h("p", null, a.text), h("p", "who", "Who: " + a.who + ". " + a.why_both_sides)); ul.append(li); });
      settle.append(h("h3", null, "A step both sides could take"), ul);
    }
    const ups = [...new Set(p.links.map((l) => l.part))], downs = D.parts.filter((x) => x.links.some((l) => l.part === p.id));
    if (ups.length || downs.length) {
      const c = h("div", "chips");
      ups.forEach((id) => c.append(chip(id, "Rests on " + id + ": " + WORD[byId[id].signal])));
      downs.forEach((x) => c.append(chip(x.id, x.id + " rests on this: " + WORD[x.signal])));
      settle.append(h("h3", null, "Connected parts"), c);
    }
    const i = D.parts.indexOf(p), prev = D.parts[i - 1], next = D.parts[i + 1];
    $("prev").hidden = !prev; $("next").hidden = !next;
    if (prev) { $("prev").textContent = "← " + prev.id + ". " + prev.text; $("prev").onclick = () => go(prev.id); }
    if (next) { $("next").textContent = next.id + ". " + next.text + " →"; $("next").onclick = () => go(next.id); }
    if ($("graphbox").open) drawGraph(p);
  }

  // ---- the optional graph ----
  const W = 210, H = 76, PW = 290, PH = 84, GX = 26, GY = 100, PAD = 20;
  const el = (tag, attrs = {}, text) => { const n = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); if (text !== undefined) n.textContent = text; return n; };
  const wrap = (text, n, max) => { const out = []; let cur = ""; for (const w of text.split(/\s+/)) { if ((cur + " " + w).trim().length > n && cur) { out.push(cur); cur = w; } else cur = (cur + " " + w).trim(); } if (cur) out.push(cur); if (out.length > max) { out.length = max; out[max - 1] += "…"; } return out; };
  function drawGraph(p) {
    const svg = $("g"); svg.replaceChildren();
    const cases = p.nodes.filter((n) => n.role !== "objection").sort((a, b) => (a.stance === b.stance ? 0 : a.stance === "supports" ? -1 : 1));
    const row2 = [...[...new Set(p.links.map((l) => l.part))].map((id) => ({ id: "link:" + id, part: id })), ...p.nodes.filter((n) => n.role === "objection")];
    const rowW = (n) => n * W + (n - 1) * GX;
    const width = Math.max(PW, rowW(cases.length), rowW(row2.length)) + PAD * 2;
    const pos = { [p.id]: { x: (width - PW) / 2, y: PAD, w: PW, h: PH } };
    const place = (items, y) => { const s = (width - rowW(items.length)) / 2; items.forEach((it, i) => { pos[it.id] = { x: s + i * (W + GX), y, w: W, h: H }; }); };
    place(cases, PAD + PH + GY); place(row2, PAD + PH + GY + H + GY);
    const height = PAD + PH + GY + H + (row2.length ? GY + H : 90) + PAD + 20;
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`); svg.setAttribute("width", width); svg.setAttribute("height", height);
    const defs = el("defs");
    ["for", "against", "attack", "link"].forEach((k) => { const m = el("marker", { id: "mk-" + k, viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" }); m.append(el("path", { d: "M0,0 L10,5 L0,10 z", class: "mk-" + k })); defs.append(m); });
    svg.append(defs);
    const pairs = {};
    p.edges.forEach((e) => {
      const a = pos[e.from], b = pos[e.to]; if (!a || !b) return;
      let d, lx, ly;
      if (Math.abs(a.y - b.y) < 1) {
        const k = (pairs[[e.from, e.to].sort().join("|")] = (pairs[[e.from, e.to].sort().join("|")] || 0) + 1);
        const sx = a.x + a.w / 2 + (a.x < b.x ? 20 : -20), tx = b.x + b.w / 2 + (a.x < b.x ? -20 : 20), y = a.y + a.h, dp = 34 + 30 * (k - 1);
        d = `M${sx},${y} C${sx},${y + dp * 1.4} ${tx},${y + dp * 1.4} ${tx},${y + 2}`; lx = (sx + tx) / 2; ly = y + dp * 1.05 + 4;
      } else {
        const up = a.y > b.y, sx = a.x + a.w / 2, sy = up ? a.y : a.y + a.h, tx = b.x + b.w / 2, ty = up ? b.y + b.h + 2 : b.y - 2, my = (sy + ty) / 2;
        d = `M${sx},${sy} C${sx},${my} ${tx},${my} ${tx},${ty}`; lx = (sx + tx) / 2; ly = my + 4;
      }
      const cls = e.kind === "case" ? (e.stance === "supports" ? "for" : "against") : e.kind === "link" ? "link" : "attack";
      svg.append(el("path", { d, class: "edge " + cls, "marker-end": `url(#mk-${cls})` }));
      const word = e.kind === "case" ? cls : e.kind === "link" ? e.label : { rebut: "rebuts", undermine: "undermines", undercut: "undercuts" }[e.type];
      svg.append(el("text", { x: lx, y: ly, "text-anchor": "middle", class: "elabel " + cls }, word));
    });
    const node = (id, cls, lines, sub, onClick) => {
      const b = pos[id], g = el("g", { class: "node " + cls, tabindex: "0", role: "button" });
      g.append(el("rect", { x: b.x, y: b.y, width: b.w, height: b.h, rx: 7 }));
      const top = b.y + b.h / 2 - ((lines.length + 1) * 16) / 2 + 12;
      lines.forEach((t, i) => g.append(el("text", { x: b.x + 12, y: top + i * 16, class: "ttl" }, t)));
      g.append(el("text", { x: b.x + 12, y: top + lines.length * 16 + 2, class: "sub" }, sub));
      g.addEventListener("click", onClick); g.addEventListener("keydown", (ev) => { if (ev.key === "Enter") onClick(); });
      svg.append(g);
    };
    node(p.id, "part", wrap(p.id + ". " + p.text, 36, 3), WORD[p.signal], () => {});
    p.nodes.forEach((n) => node(n.id, (n.stance === "supports" ? "pro " : "con ") + (n.state === "rejected at checking" ? "falls" : n.state.split(" ")[0]), wrap(n.title, 26, 3), n.state, () => flash(n.id)));
    row2.filter((r) => r.part).forEach((r) => node(r.id, "linkn", wrap("Rests on " + r.part + ": " + byId[r.part].text, 26, 2), WORD[byId[r.part].signal], () => go(r.part)));
  }
  function flash(id) {
    const li = $("pt-" + id); if (!li) return;
    li.scrollIntoView({ block: "center", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    li.classList.add("flash"); setTimeout(() => li.classList.remove("flash"), 1200);
  }
  $("graphbox").addEventListener("toggle", () => { if ($("graphbox").open && current) drawGraph(byId[current]); });

  // ---- routing: #K4 opens a part, anything else shows the map ----
  let current = null;
  function route(id) {
    current = byId[id] ? id : null;
    $("mapview").hidden = !!current; $("partview").hidden = !current;
    if (current) showPart(byId[current]);
    window.scrollTo(0, 0);
  }
  function go(id) {
    const target = id || "map";
    if (location.hash.slice(1) === target) { route(id); return; }
    try { location.hash = target; } catch (e) { route(id); }
  }
  window.addEventListener("hashchange", () => route(location.hash.slice(1)));
  $("back").addEventListener("click", () => go(null));
  document.addEventListener("keydown", (ev) => {
    if (!current || (ev.target.closest && ev.target.closest("input, textarea"))) return;
    const i = D.parts.findIndex((p) => p.id === current);
    if (ev.key === "ArrowRight" && D.parts[i + 1]) go(D.parts[i + 1].id);
    else if (ev.key === "ArrowLeft" && D.parts[i - 1]) go(D.parts[i - 1].id);
    else if (ev.key === "Escape") go(null);
  });
  route(location.hash.slice(1));
})();
</script>
</body>
</html>
"""
