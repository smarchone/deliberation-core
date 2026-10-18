---
name: deliberate
description: Turn a heated public claim into a fair, checkable reasoning artifact. Splits the claim into parts, researches each side's strongest case with sources, cross-checks them, and freezes a hash-stamped argument graph and findings report with dcore. Use when asked to deliberate on, fact-map, or break down a claim, question or controversy.
---

# Deliberate

You do the judgment work; `dcore` does the strict work. Never hand-write a
signal, a verdict or a hash: the scripts compute those from the file you write.

The output is a folder `claims/<id>/` holding `claims.json` (yours),
and `artifact.v1.json`, `report.md`, `SHA256SUMS` (built by `dcore`).

## Principles (non-negotiable)

- Judge claims, never people or sides. No verdict on the overall question; the
  report never adds the parts up.
- Loud is not strong. Repetition adds nothing; only distinct reasons and evidence.
- Each side gets its strongest case, in words its own supporters would accept.
- Nothing vanishes: a rejected argument stays in the file with the reason.
- Values are weighed, not judged: they go in `priorities`, never in `arguments`.
- Every report ends with steps both sides could take.

## Steps

1. **Collect.** Write `question.original` exactly as given. Write `question.plain`
   as a neutral restatement both sides would call fair, and say in
   `reframe_note` what you changed. Heated words stay in `original` only;
   `dcore check` warns if they leak into a sub-claim.

2. **Normalise.** Split the claim into 6 to 12 `sub_claims`, each checkable on
   its own, and type each one: `fact` (did it happen?), `interpretation` (what
   does it mean?), `intent` (why?). Merge duplicate wordings into one sub-claim
   and keep them in `merged_from`. Give each a `settle_by`: the evidence or
   event that would settle it.

3. **Explore.** Research each sub-claim from both sides with web search. Prefer
   court records, official documents and data; use news reports for what was
   said and done; treat a party's own analysis as an allegation. For every
   `interpretation` or `intent` part, write at least one `supports` and one
   `challenges` argument. Use recent sources and give each a precise `date`.

4. **Structure.** Each argument is `reasoning` (the inference) over `evidence`
   (single checkable statements, each citing source ids). Then add `attacks`:
   - `rebut`: the conclusions conflict. Add both directions when neither
     obviously wins; the engine will show it as a hinge.
   - `undermine`: attacks one piece of evidence (`target_evidence` required).
   - `undercut`: accepts the evidence but denies the step to the conclusion.
     Undercuts always succeed, so use them only when the step really fails.
   Use `role: "objection"` for an argument that only attacks another one
   (it shapes the outcome but is not itself a case for or against).
   Add a `preference` only when one side is clearly stronger, and say why in
   `rationale`; the report flags every outcome that depends on one.

5. **Values and actions.** Add `priorities`: what each side cares about, with
   who stresses it, described without judging them. Add `actions`: concrete
   steps both sides could accept that would settle an open part (a sample
   audit, publishing a record, a timed pilot), plus one small step any citizen
   can take.

6. **Verify.** Run `python -m dcore check claims/<id>` and fix every
   blocking issue. Then cross-check: start a second, independent agent that
   opens every cited source and reports, per evidence item, `confirmed`,
   `needs_fix` (with corrected text) or `unsupported`. Apply its fixes. Set an
   argument's `status` to `cross_checked` only if all its evidence is
   confirmed, with a `check_note` saying so; set `curated_rejected` with the
   reason if it cannot be supported. Record the checker in
   `generation.cross_checker`. Only a person may set `curated_accepted`, with
   `python -m dcore curate <folder> <argument-id> --accept --note "..."`.

7. **Freeze.** `python -m dcore analyse <folder>` to preview, then
   `python -m dcore freeze <folder>` and `python -m dcore verify <folder>`.
   If anything later changes, bump `version`, set `based_on` to the previous
   artifact's sha256, and freeze again.

8. **Report back** in a few lines: what is settled, what is open and what would
   settle it, and the steps both sides could take. Link `report.md`; do not
   paste it.

## File shape

See `claims/cec-government-elections/claims.json` for a full
example, and `dcore/model.py` for every field.
