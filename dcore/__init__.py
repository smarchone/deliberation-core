"""dcore: the deterministic half of the deliberation core.

Claude does the judgment work through the `deliberate` skill (collect,
normalise, research, cross-check). dcore does the strict work: check the file,
compile it into argument graphs, compute what stands, and freeze a hash-stamped
artifact and report. The argument engine is argkit, from
tarionai/defeasible-argumentation, pinned in pyproject.toml.

  model    the deliberation file schema
  compile  deliberation -> one argkit graph per sub-claim
  checks   deterministic checks (dcore's own, then argkit's)
  analyse  signals per sub-claim, and what each one hinges on
  report   the findings report, templated from the artifact
  freeze   deliberation.json -> artifact + report + SHA256SUMS
  cli      python -m dcore {check,analyse,freeze,verify}
"""

__version__ = "0.1.0"
ARGKIT_COMMIT = "5e0194b00533fa2f2fbe9be74228dc80c83be6f6"
