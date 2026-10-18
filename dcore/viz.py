"""Viz: draw each part's argument graph, as Mermaid (graph.md) and as an
interactive page (graph.html).

Rendered from the frozen artifact, like the report, so the picture can never
disagree with the results. Mermaid renders on GitHub and in most markdown
previews, so `graph.md` needs no tooling to view.

  rounded box   the part, with where it stands
  green         an argument that stands
  grey          an argument that falls, or was rejected at checking
  amber         an argument that is still open
  solid arrow   a case for the part; dotted arrow: a case against it
  thick arrow   an attack, labelled rebuts / undermines / undercuts
  rests on      a link to another part's result, with where that part stands
"""

from __future__ import annotations

import html
import json

from dcore.page import PAGE
from dcore.report import KIND_WORDS, _argument_state, _hinge_line, _link_lines

CLASSES = {
    "stands": "stands",
    "falls": "falls",
    "rejected at checking": "falls",
    "open": "open",
    "not yet checked": "unchecked",
}
LINK_ARROWS = {"holds": "-.->|rests on|", "open": "==>|is open, so leaves open|",
               "fails": "==>|does not hold, so undermines|"}
VERBS = {"rebut": "rebuts", "undermine": "undermines", "undercut": "undercuts"}
STYLE = [
    "  classDef part fill:#eef2ff,stroke:#4f46e5,color:#1e1b4b",
    "  classDef stands fill:#dcfce7,stroke:#16a34a,color:#14532d",
    "  classDef falls fill:#f3f4f6,stroke:#9ca3af,color:#6b7280,stroke-dasharray:4 3",
    "  classDef open fill:#fef3c7,stroke:#d97706,color:#78350f",
    "  classDef unchecked fill:#ffffff,stroke:#9ca3af,color:#374151",
]


def _id(raw: str) -> str:
    return raw.replace(".", "_")


def _label(text: str) -> str:
    return text.replace('"', "#quot;")


def _part_diagram(d: dict, claim: dict, part: dict) -> list[str]:
    lines = ["```mermaid", "flowchart BT",
             f'  {_id(claim["id"])}(["{claim["id"]}: {_label(claim["text"])}<br/><b>{part["signal"]}</b>"]):::part']
    own = [a for a in d["arguments"] if a["sub_claim"] == claim["id"]]
    ids = {a["id"] for a in own}
    for a in own:
        state = _argument_state(a, part)
        lines.append(f'  {_id(a["id"])}["{_label(a["title"])}<br/><i>{state}</i>"]:::{CLASSES[state]}')
    for a in own:
        if a.get("role") == "objection":
            continue
        arrow = "-->|for|" if a["stance"] == "supports" else "-.->|against|"
        lines.append(f"  {_id(a['id'])} {arrow} {_id(claim['id'])}")
    for link in part.get("links", []):
        node = f"link_{_id(link['part'])}"
        lines.append(f'  {node}(["{link["part"]}: {link["part_signal"]}"]):::part')
        arrow = LINK_ARROWS[link["effect"]]
        lines.append(f"  {node} {arrow} {_id(link['argument'])}")
    for x in d["attacks"]:
        if x["source"] in ids:
            lines.append(f"  {_id(x['source'])} ==>|{VERBS[x['type']]}| {_id(x['target'])}")
    return [*lines, *STYLE, "```"]


def render_graph(artifact: dict, digest: str) -> str:
    d = artifact["deliberation"]
    parts = artifact["analysis"]["parts"]
    lines = [f"# Graph: {d['question']['plain']}", "",
             f"Artifact `{digest[:12]}`. Green stands, grey falls, amber is open. "
             "Solid arrows argue for a part, dotted arrows against it, thick arrows are attacks."]
    for claim in d["sub_claims"]:
        lines += ["", f"## {claim['id']}. {claim['text']}", "",
                  f"*{KIND_WORDS[claim['kind']].capitalize()} · {parts[claim['id']]['signal']}*", "",
                  *_part_diagram(d, claim, parts[claim["id"]])]
    return "\n".join(lines) + "\n"


LINK_LABELS = {"holds": "rests on", "open": "open, so this stays open", "fails": "does not hold"}


def _page_part(d: dict, claim: dict, part: dict, sources: dict, arguments: dict) -> dict:
    own = [a for a in d["arguments"] if a["sub_claim"] == claim["id"]]
    ids = {a["id"] for a in own}
    nodes = [{
        "id": a["id"], "title": a["title"], "stance": a["stance"], "role": a.get("role", "case"),
        "state": _argument_state(a, part), "reasoning": a["reasoning"], "check_note": a.get("check_note"),
        "evidence": [{"text": e["text"], "from_part": e.get("from_part"),
                      "sources": [{k: sources[i][k] for k in ("publisher", "date", "url", "title")}
                                  for i in e["sources"] if i in sources]}
                     for e in a["evidence"]],
    } for a in own]
    edges = [{"from": a["id"], "to": claim["id"], "kind": "case", "stance": a["stance"]}
             for a in own if a.get("role") != "objection"]
    edges += [{"from": x["source"], "to": x["target"], "kind": "attack", "type": x["type"], "note": x["note"]}
              for x in d["attacks"] if x["source"] in ids]
    edges += [{"from": f"link:{link['part']}", "to": link["argument"], "kind": "link",
               "label": LINK_LABELS[link["effect"]]} for link in part.get("links", [])]
    preferences = [p for p in d["preferences"] if p["preferred"] in ids]
    judgment = [f"This depends on a judgment call: \"{arguments[p['preferred']]['title']}\" was judged "
                f"stronger than \"{arguments[p['over']]['title']}\"."
                for p in preferences if p["id"] in part["depends_on_judgment"]]
    return {
        "id": claim["id"], "text": claim["text"], "kind": KIND_WORDS[claim["kind"]],
        "signal": part["signal"], "plain": part["plain"], "settle_by": claim["settle_by"],
        "links": part.get("links", []), "nodes": nodes, "edges": edges,
        "preferences": [{k: p[k] for k in ("preferred", "over", "rationale")} for p in preferences],
        "hinge_lines": [_hinge_line(hg, arguments) for hg in part["hinges"]],
        "link_lines": _link_lines(part, arguments), "judgment_lines": judgment,
    }


def render_html(artifact: dict, digest: str) -> str:
    """A self-contained page: pick a part, see its graph, tap a box for why."""
    d = artifact["deliberation"]
    parts = artifact["analysis"]["parts"]
    sources = {s["id"]: s for s in d["sources"]}
    arguments = {a["id"]: a for a in d["arguments"]}
    data = {
        "question": d["question"], "as_of": d["as_of"], "version": d["version"], "digest": digest,
        "parts": [_page_part(d, c, parts[c["id"]], sources, arguments) for c in d["sub_claims"]],
    }
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False).replace("</", "<\\/")
    return PAGE.replace("__TITLE__", html.escape(d["question"]["plain"])).replace("__DATA__", payload)
