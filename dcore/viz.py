"""Viz: draw each part's argument graph as a Mermaid diagram.

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

from dcore.report import KIND_WORDS, _argument_state

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
