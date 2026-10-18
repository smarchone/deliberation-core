"""Report: the findings for progress, rendered from the frozen artifact.

Templated from structure, never from a model, so no wording here can change
what the engine found. Claude may write a friendlier summary on top, but this
file is the authority and every line traces back to the artifact.

Words, not numbers: arguments "stand", "fall" or are "open"; parts are
"supported", "challenged", "contested" and so on.
"""

from __future__ import annotations

from collections import Counter

LABEL_WORDS = {"accepted": "stands", "rejected": "falls", "undecided": "open"}
KIND_WORDS = {"fact": "fact", "interpretation": "meaning", "intent": "intent"}
SETTLED = ("supported", "challenged", "both hold in part")
STANCE_WORDS = {"supports": "For", "challenges": "Against"}


def _index(artifact: dict):
    d = artifact["deliberation"]
    return (d, {s["id"]: s for s in d["sources"]}, {a["id"]: a for a in d["arguments"]},
            {c["id"]: c for c in d["sub_claims"]})


def _source_links(ids: list[str], sources: dict) -> str:
    return ", ".join(f"[{sources[i]['publisher']}, {sources[i]['date']}]({sources[i]['url']})"
                     for i in ids if i in sources)


def _argument_state(argument: dict, part: dict) -> str:
    if argument["id"] in part["labels"]:
        return LABEL_WORDS[part["labels"][argument["id"]]]
    if argument["status"] == "curated_rejected":
        return "rejected at checking"
    return "not yet checked"


def _hinge_line(hinge: dict, arguments: dict) -> str:
    a, b = hinge["between"]
    ta, tb = arguments[a]["title"], arguments[b]["title"]
    if hinge["needs_new_evidence"]:
        return f"\"{ta}\" and \"{tb}\" block each other, and judging one stronger would not change the outcome; new evidence is needed."
    oa, ob = hinge["if_stronger"][a], hinge["if_stronger"][b]
    return (f"Hinges on which is stronger: \"{ta}\" (then this part is {oa}) "
            f"or \"{tb}\" (then it is {ob}).")


def _at_a_glance(d: dict, parts: dict) -> list[str]:
    lines = ["| Part | Kind | Where it stands |", "|---|---|---|"]
    for c in d["sub_claims"]:
        lines.append(f"| {c['id']}. {c['text']} | {KIND_WORDS[c['kind']]} | {parts[c['id']]['signal']} |")
    return lines


def _settled(d: dict, parts: dict, arguments: dict) -> list[str]:
    lines = []
    for c in d["sub_claims"]:
        part = parts[c["id"]]
        if part["signal"] not in SETTLED:
            continue
        line = f"- **{c['id']}. {c['text']}** {part['signal'].capitalize()}. {part['plain']}"
        for preference_id in part["depends_on_judgment"]:
            p = next(x for x in d["preferences"] if x["id"] == preference_id)
            line += (f" This depends on a judgment call: \"{arguments[p['preferred']]['title']}\" "
                     f"was judged stronger than \"{arguments[p['over']]['title']}\".")
        if part["rests_on"] and c["kind"] != "fact":
            titles = "; ".join(f"\"{arguments[a]['title']}\"" for a in part["rests_on"])
            line += f" It rests on one argument: {titles}."
        lines.append(line)
    return lines or ["- Nothing is settled yet."]


def _open(d: dict, parts: dict, arguments: dict) -> list[str]:
    lines = []
    for c in d["sub_claims"]:
        part = parts[c["id"]]
        if part["signal"] in SETTLED:
            continue
        lines.append(f"- **{c['id']}. {c['text']}** {part['signal'].capitalize()}. {part['plain']}")
        for hinge in part["hinges"]:
            lines.append(f"  - {_hinge_line(hinge, arguments)}")
        lines.append(f"  - *What would settle it:* {c['settle_by']}")
    return lines or ["- Nothing is open."]


def _detail(d: dict, parts: dict, sources: dict, arguments: dict) -> list[str]:
    lines = []
    for c in d["sub_claims"]:
        part = parts[c["id"]]
        lines += ["", f"### {c['id']}. {c['text']}", "",
                  f"*{KIND_WORDS[c['kind']].capitalize()} · {part['signal']}*"]
        if c["merged_from"]:
            lines.append("")
            lines.append("Also heard as: " + "; ".join(f"\"{m}\"" for m in c["merged_from"]))
        for stance in ("supports", "challenges"):
            own = [a for a in d["arguments"] if a["sub_claim"] == c["id"] and a["stance"] == stance]
            if not own:
                continue
            lines += ["", f"**{STANCE_WORDS[stance]}**", ""]
            for a in own:
                role = ", an objection" if a.get("role") == "objection" else ""
                lines.append(f"- **{a['title']}** ({_argument_state(a, part)}{role}). {a['reasoning']}")
                for e in a["evidence"]:
                    lines.append(f"  - {e['text']} ({_source_links(e['sources'], sources)})")
                if a["status"] == "curated_rejected" and a.get("check_note"):
                    lines.append(f"  - *Rejected because:* {a['check_note']}")
        attacks = [x for x in d["attacks"]
                   if arguments.get(x["source"], {}).get("sub_claim") == c["id"]]
        if attacks:
            lines += ["", "**How they meet**", ""]
            for x in attacks:
                lines.append(f"- \"{arguments[x['source']]['title']}\" {x['type']}s "
                             f"\"{arguments[x['target']]['title']}\": {x['note']}")
        preferences = [p for p in d["preferences"]
                       if arguments.get(p["preferred"], {}).get("sub_claim") == c["id"]]
        for p in preferences:
            lines.append(f"- *Judged stronger:* \"{arguments[p['preferred']]['title']}\" over "
                         f"\"{arguments[p['over']]['title']}\". {p['rationale']} "
                         "This is a judgment call, open to challenge.")
    return lines


def _audit(artifact: dict, arguments: dict) -> list[str]:
    statuses = Counter(a["status"] for a in arguments.values())
    warnings = Counter(i["kind"] for i in artifact["qc"]["issues"] if i["severity"] == "warning")
    d = artifact["deliberation"]
    lines = [
        f"- Drafted by {d['generation']['generator']}"
        + (f"; each argument cross-checked against its sources by {d['generation']['cross_checker']}."
           if d["generation"].get("cross_checker") else "."),
        f"- Arguments: {len(arguments)} in total; {statuses.get('cross_checked', 0)} machine cross-checked, "
        f"{statuses.get('curated_accepted', 0)} accepted by a person, "
        f"{statuses.get('curated_rejected', 0)} rejected, {statuses.get('candidate', 0)} still unchecked.",
        f"- Counted as live in this analysis: {', '.join(artifact['analysis']['live_statuses'])}.",
    ]
    if statuses.get("curated_accepted", 0) == 0:
        lines.append("- **No person has reviewed this yet.** Treat it as a first draft for both sides to correct.")
    if warnings:
        lines.append("- Open warnings: " + ", ".join(f"{k.replace('_', ' ')} ({n})"
                                                       for k, n in sorted(warnings.items())) + ".")
    lines.append(f"- Engine: {artifact['engine']['semantics']} semantics, argkit {artifact['engine']['argkit']}.")
    return lines


def render_report(artifact: dict, digest: str) -> str:
    d, sources, arguments, _ = _index(artifact)
    parts = artifact["analysis"]["parts"]
    q = d["question"]
    lines = [
        f"# {q['plain']}",
        "",
        f"As of {d['as_of']} · version {d['version']} · artifact `{digest[:12]}`",
        "",
        f"> Heard as: \"{q['original']}\"",
        f"> {q['reframe_note']}",
        "",
        "This is a map of the evidence, not a verdict on any person or party. "
        "Each part of the claim is checked on its own, and the parts are never added up into one answer.",
        "",
        "## At a glance",
        "",
        *_at_a_glance(d, parts),
        "",
        "## What is settled",
        "",
        *_settled(d, parts, arguments),
        "",
        "## What is open, and what would settle it",
        "",
        *_open(d, parts, arguments),
    ]
    if d["priorities"]:
        lines += ["", "## What each side weighs", "",
                  "These are values, not facts. They show where people differ in what they care about, not who is right.", ""]
        lines += [f"- {p['text']} *(stressed by {p['emphasised_by']})*" for p in d["priorities"]]
    if d["actions"]:
        lines += ["", "## Steps both sides could take", ""]
        for a in d["actions"]:
            settles = ", ".join(a["settles"])
            lines.append(f"- **{a['text']}** Who: {a['who']}. Helps settle {settles}. {a['why_both_sides']}")
    lines += ["", "## Each part in detail", *_detail(d, parts, sources, arguments)]
    lines += ["", "## Audit", "", *_audit(artifact, arguments), "",
              f"Verify: `sha256sum -c SHA256SUMS` in this folder; artifact sha256 `{digest}`."]
    return "\n".join(lines) + "\n"
