# Vendored: argkit

These files are copied unchanged from
[tarionai/defeasible-argumentation](https://github.com/tarionai/defeasible-argumentation)
at commit `5e0194b00533fa2f2fbe9be74228dc80c83be6f6`, under the MIT licence in
[LICENSE](LICENSE) (Copyright (c) 2026 Ed Sosa).

Kept: `aaf.py` (Dung engine), `schema.py` (typed nodes + provenance),
`structured.py` (attack types -> defeats), `qc.py` (deterministic checks),
`curate.py` (human curation), `export.py` (grounded summary).

Left out: `pipeline.py`, `llm_adapters.py`, `seed.py`, `build.py` (their LLM
pipeline and worked example). In deliberation-core, Claude does the population
work through the `deliberate` skill, and `dcore` does the build.

The engine's correctness tests come along too: `tests/test_aaf_textbook.py`,
`tests/test_aaf_differential.py` (1,000 random frameworks against PyArg),
`tests/test_structured.py`, `tests/test_qc.py`.

Do not edit these files in place; wrap them in `dcore/` instead, so a later
upstream update stays a plain copy.
