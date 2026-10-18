# deliberation-core

Takes a claim from anywhere, breaks it into checkable parts, gathers each side's
strongest case with sources, and freezes the result as a shareable, verifiable
reasoning artifact: an argument graph plus a findings report that says what is
settled, what is open, what would settle it, and what both sides could do next.

It is the engine behind the JNJ deliberation surfaces. It never gives a verdict
on a person or a side.

## How it works

```
 claim ──▶ Claude (deliberate skill) ──▶ deliberation.json ──▶ dcore ──▶ artifact + report
           collect, split, research,                           check, compute what stands,
           cross-check sources                                 find hinges, freeze + hash
```

- **Claude does the judgment work** through the skill in
  [`.claude/skills/deliberate/SKILL.md`](.claude/skills/deliberate/SKILL.md).
- **`dcore` does the strict work**, with no model and no network: deterministic
  checks, compiling each part into an argument graph, computing what stands,
  and freezing a byte-reproducible, SHA-256-stamped artifact and report.
- **The argument engine is argkit**, vendored unchanged from
  [tarionai/defeasible-argumentation](https://github.com/tarionai/defeasible-argumentation)
  (MIT): a Dung grounded-semantics engine differential-tested against PyArg on
  1,000 random frameworks, typed attacks (rebut, undermine, undercut), and a
  provenance state machine (candidate, cross-checked, accepted, rejected). See
  [`argkit/VENDORED.md`](argkit/VENDORED.md).

## What the report says about each part

| Word | Meaning |
|---|---|
| supported | the supporting case holds up and no challenge stands |
| challenged | a challenge holds up and the supporting case does not |
| both hold in part | each side has a point the other does not defeat |
| contested | the two sides block each other; the report says what it hinges on |
| unproven either way | neither side's case survives the challenges against it |
| unverified | nothing has passed checking yet |

## Use

```bash
pip install -e ".[dev]"
pytest                                             # engine + dcore tests
python -m dcore check   deliberations/<id>         # list issues
python -m dcore analyse deliberations/<id>         # preview where each part stands
python -m dcore freeze  deliberations/<id>         # write artifact.v1.json, report.md, SHA256SUMS
python -m dcore verify  deliberations/<id>         # rebuild and confirm the hash
python -m dcore curate  deliberations/<id> K2.P1 --accept --note "checked the judgment"
```

## First deliberation

[`deliberations/cec-government-elections`](deliberations/cec-government-elections/report.md):
"CEC and modi government, together are trying to rig Indian democracy", split
into 12 parts.

## Limits of this version

- Attacks stay within one part; the parts are not linked to each other yet.
- Cross-checking is a second model pass, not a person. The report says so
  until someone curates it.
- One deliberation, one language (English), sources gathered by hand-run search.
