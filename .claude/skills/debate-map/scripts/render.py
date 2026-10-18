"""Render a debate map into one self-contained HTML page.

    python render.py debates/my-debate        # writes debates/my-debate/page.html

Reads transcript.json and map.json, checks them (see check.py), computes the
per-voice stats, and draws the page: a timeline of who held the floor, the
thread of points as a tree, and the report. Every time on the page opens the
video at that moment. Private labels in the map are never shown.
"""

from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check import check, load, stats  # noqa: E402

VERB = {"question": "asks", "claim": "claims", "reply": "replies", "challenge": "challenges",
        "concession": "concedes", "agreement": "agrees"}
ROLE = {"anchor": "anchor", "panelist": "panelist", "guest": "guest", "audience": "audience", "other": "voice"}
MOMENT = {"interruption": "talks over", "crosstalk": "Several voices at once",
          "topic_change": "Topic changes", "other": ""}
N_COLORS = 6


def mmss(t: float) -> str:
    t = int(t)
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class Page:
    def __init__(self, tr: dict, m: dict):
        self.tr, self.m = tr, m
        self.url = tr["video"]["url"]
        self.dur = float(tr["duration"]) or 1
        self.voices = {v["id"]: v for v in m["voices"]}
        # Anchors get the ink colour; everyone else a colour of their own.
        n = 0
        self.color = {}
        for v in m["voices"]:
            if v["role"] == "anchor":
                self.color[v["id"]] = "ink"
            else:
                self.color[v["id"]] = str(n % N_COLORS)
                n += 1
        self.pts = {p["id"]: p for p in m["points"]}
        self.kids: dict = {}
        for p in sorted(m["points"], key=lambda p: p["t"]):
            self.kids.setdefault(p.get("parent"), []).append(p)

    def at(self, t: float, label: str | None = None) -> str:
        return (f'<a class="tc" href="{escape(self.url)}&amp;t={int(t)}s" target="_blank" '
                f'rel="noopener" title="Open the video at {mmss(t)}">{escape(label or mmss(t))}</a>')

    def chip(self, vid: str, with_role=True) -> str:
        v = self.voices[vid]
        role = f' <span class="role">{ROLE[v["role"]]}</span>' if with_role else ""
        return f'<span class="voice" data-c="{self.color[vid]}">Voice {escape(vid)}{role}</span>'

    # --- timeline -----------------------------------------------------------

    def timeline(self) -> str:
        W, lane, top = 1000, 16, 6
        ids = [v["id"] for v in self.m["voices"]]
        H = top + lane * len(ids) + 28
        x = lambda t: 60 + (W - 90) * min(t, self.dur) / self.dur
        out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Who held the floor, over the length of the video">']
        for i, vid in enumerate(ids):
            y = top + i * lane
            out.append(f'<text x="0" y="{y + 11}" class="lane">Voice {escape(vid)}</text>')
            out.append(f'<rect x="60" y="{y + 3}" width="{W - 90}" height="{lane - 6}" class="track"/>')
        for t in self.m["turns"]:
            i = ids.index(t["voice"])
            y = top + i * lane
            w = max(x(t["end"]) - x(t["start"]), 1.5)
            out.append(f'<a href="{escape(self.url)}&amp;t={int(t["start"])}s" target="_blank" rel="noopener">'
                       f'<rect x="{x(t["start"]):.1f}" y="{y + 2}" width="{w:.1f}" height="{lane - 4}" '
                       f'class="seg" data-c="{self.color[t["voice"]]}"><title>Voice {escape(t["voice"])}, '
                       f'{mmss(t["start"])} to {mmss(t["end"])}</title></rect></a>')
        base = top + lane * len(ids) + 4
        for mo in self.m.get("moments", []):
            if mo["kind"] in ("interruption", "crosstalk"):
                cx = x(mo["t"])
                out.append(f'<a href="{escape(self.url)}&amp;t={int(mo["t"])}s" target="_blank" rel="noopener">'
                           f'<path d="M{cx:.1f} {base} l4 7 h-8 z" class="mark"><title>{mmss(mo["t"])} '
                           f'{escape(self.moment_text(mo))}</title></path></a>')
        step = 300 if self.dur > 1200 else 120 if self.dur > 300 else 60
        t = 0
        while t <= self.dur:
            out.append(f'<text x="{x(t):.1f}" y="{H - 2}" class="tick" text-anchor="middle">{mmss(t)}</text>')
            t += step
        out.append("</svg>")
        return "".join(out)

    def moment_text(self, mo: dict) -> str:
        if mo["kind"] == "interruption":
            s = f"Voice {mo['by']} talks over Voice {mo['of']}"
        else:
            s = MOMENT[mo["kind"]]
        note = mo.get("note")
        return f"{s}. {note}" if s and note else (s or note or "")

    # --- thread -------------------------------------------------------------

    def outcome(self, p: dict) -> str:
        o = p["outcome"]
        to = f" by Voice {escape(p['to'])}" if p.get("to") else ""
        ans = self.pts.get(p.get("answered_at"))
        link = f" at {self.at(ans['t'])}" if ans else ""
        if o == "answered":
            s, cls = f"Answered{to}{link}", "ok"
        elif o == "partly":
            s, cls = f"Partly answered{to}{link}", "part"
        else:
            again = "Asked again later" if p.get("followed_up") else "Not asked again"
            s, cls = f"No direct answer{to}. {again}", "none"
        return f'<div class="outcome" data-o="{cls}">{s}</div>'

    def node(self, p: dict) -> str:
        unanswered = p["kind"] == "question" and p["outcome"] != "answered"
        quote = (f'<details><summary>In their words</summary><blockquote lang="{escape(self.tr.get("lang") or "")}">'
                 f'{escape(p["quote"])}</blockquote></details>') if p.get("quote") else ""
        note = f'<p class="note">{escape(p["note"])}</p>' if p.get("note") else ""
        kids = "".join(self.node(k) for k in self.kids.get(p["id"], []))
        to = f' <span class="to">to Voice {escape(p["to"])}</span>' if p.get("to") and p["kind"] == "question" else ""
        return (f'<li class="pt" data-voice="{escape(p["voice"])}" data-kind="{p["kind"]}"'
                f'{" data-open" if unanswered else ""}>'
                f'<div class="head">{self.at(p["t"])}{self.chip(p["voice"], False)}'
                f'<span class="verb">{VERB[p["kind"]]}</span>{to}</div>'
                f'<p class="text">{escape(p["text"])}</p>'
                f'{self.outcome(p) if p["kind"] == "question" else ""}{note}{quote}'
                f'{"<ul>" + kids + "</ul>" if kids else ""}</li>')

    # --- report -------------------------------------------------------------

    def stats_table(self) -> str:
        rows = []
        for r in stats(self.tr, self.m):
            pct = round(100 * r["share"])
            rows.append(
                f'<tr><th scope="row">{self.chip(r["voice"])}</th>'
                f'<td><span class="bar"><span style="width:{pct}%" data-c="{self.color[r["voice"]]}"></span></span>'
                f'{pct}%<span class="sub">{mmss(r["seconds"])}</span></td>'
                f'<td>{r["turns"]}</td><td>{r["interrupted_others"]}</td><td>{r["was_interrupted"]}</td>'
                f'<td>{r["asked"]}</td><td>{r["put_to"]}</td><td>{r["answered"]}</td>'
                f'<td>{r["partly"]}</td><td>{r["not_answered"]}</td><td>{r["followed_up"]}</td></tr>')
        return ('<div class="scroll"><table class="stats"><thead><tr><th>Voice</th><th>Talk time</th>'
                '<th>Turns</th><th>Talked over others</th><th>Was talked over</th><th>Questions asked</th>'
                '<th>Questions put to them</th><th>Answered</th><th>Partly</th><th>No direct answer</th>'
                '<th>Asked again after no answer</th></tr></thead><tbody>'
                + "".join(rows) + "</tbody></table></div>")

    def report(self) -> str:
        rep = self.m["report"]
        li = lambda xs: "<ul>" + "".join(f"<li>{escape(x)}</li>" for x in xs) + "</ul>"
        parts = [f'<section><h2>Summary</h2><p>{escape(rep["summary"])}</p></section>',
                 f'<section><h2>Takeaways</h2>{li(rep["takeaways"])}</section>',
                 f'<section><h2>Action items</h2>{li(rep["actions"])}</section>']
        if rep.get("left_open"):
            parts.append(f'<section><h2>Left open</h2>{li(rep["left_open"])}</section>')
        moments = [mo for mo in self.m.get("moments", [])]
        if moments:
            items = "".join(f'<li>{self.at(mo["t"])} {escape(self.moment_text(mo))}</li>'
                            for mo in sorted(moments, key=lambda mo: mo["t"]))
            parts.append(f'<section><h2>Moments</h2><ul class="moments">{items}</ul></section>')
        return "".join(parts)

    def render(self) -> str:
        v, m, tr = self.tr["video"], self.m, self.tr
        title = v.get("title") or m["topic"]
        caps = ("YouTube's automatic captions" if tr.get("auto_generated") else
                "YouTube captions" if tr["source"] == "youtube" else "a transcript supplied by hand")
        voices = "".join(f'<button type="button" class="filter" id="f-{escape(i)}" data-voice="{escape(i)}" '
                         f'aria-pressed="false">{self.chip(i)}</button>' for i in self.voices)
        roots = "".join(self.node(p) for p in self.kids.get(None, []))
        n_q = sum(p["kind"] == "question" for p in m["points"])
        n_open = sum(p["kind"] == "question" and p["outcome"] != "answered" for p in m["points"])
        return TEMPLATE.format(
            title=escape(title),
            channel=escape(v.get("channel") or ""),
            topic=escape(m["topic"]),
            url=escape(v["url"]),
            length=mmss(self.dur),
            timeline=self.timeline(),
            voices=voices,
            roots=roots,
            report=self.report(),
            stats=self.stats_table(),
            caps=caps,
            n_points=len(m["points"]),
            n_q=n_q,
            n_open=n_open,
            basis="".join(f"<li>{self.chip(i)}: {escape(x.get('basis', ''))}</li>" for i, x in self.voices.items()),
            data=escape(json.dumps({"voices": list(self.voices)}), quote=False),
        )


TEMPLATE = """<title>{title}</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=JetBrains+Mono:wght@500&display=swap">
<style>
/* Layout: a broadcast rundown. Timeline across the top, the thread of points on the left, the report alongside. */
:root {{
  --paper: #f6f7f8; --card: #ffffff; --ink: #1d232b; --muted: #5d6773; --rule: #d9dee4;
  --accent: #1f5f8b; --tc-bg: #e6edf3;
  --v0: #b4572e; --v1: #2e7d6b; --v2: #7a4fa3; --v3: #a8801a; --v4: #b03a6b; --v5: #3f6fb5; --vink: #4a535e;
  --ok: #2e7d4f; --part: #9a6a12; --none: #a3412e;
  --display: "Bricolage Grotesque", "Avenir Next", "Segoe UI", sans-serif;
  --body: "Atkinson Hyperlegible", "Segoe UI", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --paper: #14181d; --card: #1b2027; --ink: #e5e9ee; --muted: #9aa5b1; --rule: #2c333c;
  --accent: #7fb6dd; --tc-bg: #24303b;
  --v0: #e08a63; --v1: #63bfa9; --v2: #b38fd8; --v3: #d8b450; --v4: #e07aa5; --v5: #82a9e6; --vink: #aab4bf;
  --ok: #6cc28f; --part: #d9a94a; --none: #e5856f; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --paper: #14181d; --card: #1b2027; --ink: #e5e9ee; --muted: #9aa5b1; --rule: #2c333c;
  --accent: #7fb6dd; --tc-bg: #24303b;
  --v0: #e08a63; --v1: #63bfa9; --v2: #b38fd8; --v3: #d8b450; --v4: #e07aa5; --v5: #82a9e6; --vink: #aab4bf;
  --ok: #6cc28f; --part: #d9a94a; --none: #e5856f; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--paper); color: var(--ink); font: 16px/1.55 var(--body); }}
.wrap {{ max-width: 1240px; margin: 0 auto; padding-block: 28px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
header {{ display: grid; gap: 6px; margin-bottom: 18px; }}
.eyebrow {{ font: 500 12px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }}
h1 {{ font: 700 clamp(26px, 4.2vw, 40px)/1.12 var(--display); margin: 0; text-wrap: balance; max-width: 30ch; }}
.topic {{ font-size: 18px; color: var(--muted); margin: 0; max-width: 65ch; }}
.meta {{ display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; font-size: 14px; color: var(--muted); }}
.meta a {{ color: var(--accent); }}
h2 {{ font: 700 19px/1.2 var(--display); margin: 0 0 8px; }}
.timeline {{ background: var(--card); border: 1px solid var(--rule); border-radius: 6px; padding: 12px 14px 8px; margin-bottom: 22px; overflow-x: auto; }}
.timeline svg {{ display: block; width: 100%; min-width: 560px; height: auto; }}
.timeline .cap {{ font-size: 13px; color: var(--muted); margin: 0 0 6px; }}
.lane {{ font: 500 11px var(--mono); fill: var(--muted); }}
.tick {{ font: 500 10px var(--mono); fill: var(--muted); }}
.track {{ fill: var(--rule); opacity: .45; rx: 2; }}
.seg {{ rx: 1.5; }}
.mark {{ fill: var(--none); }}
[data-c="0"] {{ --vc: var(--v0); }} [data-c="1"] {{ --vc: var(--v1); }} [data-c="2"] {{ --vc: var(--v2); }}
[data-c="3"] {{ --vc: var(--v3); }} [data-c="4"] {{ --vc: var(--v4); }} [data-c="5"] {{ --vc: var(--v5); }}
[data-c="ink"] {{ --vc: var(--vink); }}
.seg {{ fill: var(--vc); }}
.grid {{ display: grid; gap: 28px; grid-template-columns: minmax(0, 1fr); }}
@media (min-width: 980px) {{ .grid {{ grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr); }} aside {{ align-self: start; }} }}
@media (max-width: 979px) {{ aside {{ order: -1; }} }}
.tc {{ font: 500 13px/1 var(--mono); font-variant-numeric: tabular-nums; color: var(--accent); background: var(--tc-bg);
  padding: 4px 6px; border-radius: 4px; text-decoration: none; white-space: nowrap; }}
.tc:hover, .tc:focus-visible {{ text-decoration: underline; }}
a:focus-visible, button:focus-visible, summary:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.voice {{ display: inline-flex; align-items: baseline; gap: 5px; font-weight: 700; font-size: 14px; color: var(--vc); white-space: nowrap; }}
.voice::before {{ content: ""; width: 9px; height: 9px; border-radius: 50%; background: var(--vc); align-self: center; }}
.role {{ font-weight: 400; color: var(--muted); }}
.controls {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 14px; }}
.filter, .toggle {{ font: inherit; font-size: 14px; background: var(--card); color: var(--ink); border: 1px solid var(--rule);
  border-radius: 999px; padding: 5px 12px; cursor: pointer; }}
.filter[aria-pressed="true"], .toggle[aria-pressed="true"] {{ border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }}
.thread ul {{ list-style: none; margin: 0; padding: 0; }}
.thread > ul > li {{ border-top: 1px solid var(--rule); padding-block: 14px; }}
.thread li li {{ margin-top: 12px; padding-left: 16px; border-left: 2px solid var(--rule); }}
.pt .head {{ display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; }}
.verb {{ color: var(--muted); font-size: 14px; }}
.to {{ color: var(--muted); font-size: 14px; }}
.text {{ margin: 6px 0 0; max-width: 68ch; }}
.note {{ margin: 4px 0 0; color: var(--muted); font-size: 14px; max-width: 68ch; }}
.outcome {{ margin-top: 6px; font-size: 14px; font-weight: 700; display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }}
.outcome[data-o="ok"] {{ color: var(--ok); }} .outcome[data-o="part"] {{ color: var(--part); }} .outcome[data-o="none"] {{ color: var(--none); }}
details {{ margin-top: 6px; font-size: 14px; }}
summary {{ cursor: pointer; color: var(--muted); }}
blockquote {{ margin: 6px 0 0; padding-left: 10px; border-left: 2px solid var(--rule); color: var(--muted); max-width: 68ch; }}
.dim {{ opacity: .28; }}
.hide {{ display: none; }}
aside {{ display: grid; gap: 22px; background: var(--card); border: 1px solid var(--rule); border-radius: 6px; padding: 18px; }}
aside ul {{ margin: 0; padding-left: 20px; display: grid; gap: 6px; }}
aside p {{ margin: 0; }}
.moments {{ list-style: none; padding: 0 !important; }}
.moments li {{ display: flex; gap: 8px; align-items: baseline; }}
.stats-wrap {{ margin-top: 30px; }}
.scroll {{ overflow-x: auto; }}
table.stats {{ border-collapse: collapse; font-size: 14px; font-variant-numeric: tabular-nums; min-width: 760px; width: 100%; }}
.stats th, .stats td {{ text-align: right; padding: 8px 10px; border-bottom: 1px solid var(--rule); vertical-align: middle; }}
.stats thead th {{ font-weight: 400; color: var(--muted); font-size: 12px; vertical-align: bottom; }}
.stats th:first-child, .stats td:nth-child(2) {{ text-align: left; }}
.bar {{ display: inline-block; width: 70px; height: 7px; background: var(--rule); border-radius: 4px; margin-right: 8px; overflow: hidden; vertical-align: middle; }}
.bar span {{ display: block; height: 100%; background: var(--vc); }}
.sub {{ color: var(--muted); margin-left: 6px; }}
.method {{ margin-top: 30px; font-size: 14px; color: var(--muted); max-width: 75ch; display: grid; gap: 6px; }}
.method ul {{ margin: 0; padding-left: 20px; }}
@media (prefers-reduced-motion: no-preference) {{ .pt {{ transition: opacity .15s; }} }}
</style>
<div class="wrap">
<header>
  <div class="eyebrow">How this debate went</div>
  <h1>{title}</h1>
  <p class="topic">{topic}</p>
  <div class="meta"><span>{channel}</span><span>{length} long</span><span>{n_points} points, {n_q} questions, {n_open} without a full answer</span><a href="{url}" target="_blank" rel="noopener">Open the video</a></div>
</header>
<div class="timeline"><p class="cap">Who held the floor. Each band is a stretch of talk; triangles mark talking over. Tap any band to open the video there.</p>{timeline}</div>
<div class="grid">
<main class="thread">
  <h2>The thread</h2>
  <div class="controls" role="group" aria-label="Filter the thread">{voices}<button type="button" class="toggle" id="f-open" aria-pressed="false">Questions without a full answer</button></div>
  <ul>{roots}</ul>
</main>
<aside>{report}</aside>
</div>
<section class="stats-wrap"><h2>Who did what</h2>{stats}</section>
<section class="method">
  <h2>How this was made</h2>
  <p>Built from {caps}. The captions don't say who is speaking, so voices are anonymous and inferred from context; every count above is approximate. Points are paraphrased; open "In their words" or tap a time to check the original. This page describes what was said and done, not who was right.</p>
  <ul>{basis}</ul>
</section>
</div>
<script id="dm-data" type="application/json">{data}</script>
<script>
(function () {{
  var pts = Array.prototype.slice.call(document.querySelectorAll('.pt'));
  var filters = Array.prototype.slice.call(document.querySelectorAll('.filter'));
  var openBtn = document.getElementById('f-open');
  var active = null, openOnly = false;
  function apply() {{
    pts.forEach(function (li) {{
      li.classList.toggle('dim', !!active && li.dataset.voice !== active);
      var keep = !openOnly || li.hasAttribute('data-open') || li.querySelector('[data-open]') || li.parentElement.closest('[data-open]');
      li.classList.toggle('hide', !keep);
    }});
    filters.forEach(function (b) {{ b.setAttribute('aria-pressed', String(b.dataset.voice === active)); }});
    openBtn.setAttribute('aria-pressed', String(openOnly));
  }}
  filters.forEach(function (b) {{ b.addEventListener('click', function () {{ active = active === b.dataset.voice ? null : b.dataset.voice; apply(); }}); }});
  openBtn.addEventListener('click', function () {{ openOnly = !openOnly; apply(); }});
}})();
</script>
"""


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    folder = Path(argv[0])
    tr, m = load(folder)
    err, warn = check(tr, m)
    for w in warn:
        print("warning:", w)
    if err:
        for e in err:
            print("error:", e)
        print("Not rendered: fix the errors above (python check.py shows them too).")
        return 1
    out = folder / "page.html"
    out.write_text(Page(tr, m).render(), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
