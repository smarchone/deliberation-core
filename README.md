# deliberation-core

Turns a heated claim into a shareable, verifiable reasoning artifact: an
argument graph plus a report of what is settled, what is open, what would
settle it, and what both sides could do next. It never gives a verdict on a
person or a side.

## How it works

The work is split in two:

- **Claude makes the judgments.** Through the
  [`deliberate`](.claude/skills/deliberate/SKILL.md) skill, it splits the claim
  into parts, researches each side's strongest case with sources, and builds the
  argument graph: which argument supports, challenges or attacks which. It
  writes this to `claims/<id>/claims.json`, and a second agent cross-checks
  every source.
- **Code resolves what survives, deterministically.** `dcore` checks the file,
  compiles each part into an argument graph, and hands it to
  [argkit](https://github.com/tarionai/defeasible-argumentation) (MIT, pinned to
  one commit). argkit's grounded-semantics engine computes what stands, what
  falls and what stays open. dcore then freezes the result as a hash-stamped
  artifact and report. There's no model, network or clock in this step.

So a sceptic can dispute any judgment in `claims.json`, but not how it was
resolved: anyone can rebuild the artifact and get the same hash.

Each part ends up as one of: **supported**, **challenged**, **both hold in
part**, **contested** (with what it hinges on), **unproven either way**, or
**unverified**.

## Use

```bash
pip install -e ".[dev]"
```

An example pipeline, for the claim "The city's plastic ban failed":

```bash
# 1. In Claude Code, Claude researches and writes claims/plastic-ban/claims.json,
#    runs the checks, and has a second agent cross-check the sources.
/deliberate "The city's plastic ban failed"

# 2. Preview where each part stands (writes nothing).
python -m dcore analyse claims/plastic-ban
#   K1  contested   hinge: K1.C1 vs K1.P1

# 3. A person reviews, signing off on or rejecting arguments.
python -m dcore curate claims/plastic-ban K1.C1 --accept --note "checked the survey"

# 4. Freeze: artifact.v1.json, report.md, graph.md (Mermaid diagrams),
#    graph.html (the whole argument graph on one zoomable page; tap a node to
#    see why it holds or falls) and SHA256SUMS. `viz` redraws both graphs.
python -m dcore freeze claims/plastic-ban

# 5. Anyone can rebuild it and confirm the hash.
python -m dcore verify claims/plastic-ban
#   OK
```

New evidence later: edit `claims.json`, bump `version`, set `based_on` to the
previous hash, and freeze again.

## First claim

[`claims/cec-government-elections`](claims/cec-government-elections/report.md):
"CEC and modi government, together are trying to rig Indian democracy", in 12 parts
([graph](claims/cec-government-elections/graph.md); open `graph.html` in a browser to explore it).

## Debate map (separate skill)

[`debate-map`](.claude/skills/debate-map/SKILL.md) turns a recorded debate,
townhall or podcast on YouTube into one HTML page: the thread of claims,
replies, challenges and questions (each timestamped and linked into the video)
plus a "how this debate went" report with per-voice stats. Claude does the
judging; three small stdlib scripts do the plumbing (`fetch.py` gets captions
or reads a pasted transcript, `check.py` validates the map and counts the
stats, `render.py` draws the page). It doesn't use dcore or argkit, and it
doesn't fact-check.

```bash
S=.claude/skills/debate-map/scripts
python $S/fetch.py <youtube-url> --out debates/<id>     # or --from pasted.txt
# Claude writes debates/<id>/map.json (see the skill)
python $S/check.py debates/<id>
python $S/render.py debates/<id>                         # debates/<id>/page.html
```

## Limits

- Parts link only through evidence: an argument can rest on another part's
  result (`from_part`), and falls or stays open with it. Attacks still stay
  within one part, and links can't loop.
- Cross-checking is a second model pass, not a person, and the report says so.
