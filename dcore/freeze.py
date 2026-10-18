"""Freeze: claims file -> frozen, hash-stamped artifact plus report and graph.

Deterministic end to end: no model, no clock, no network. The same
claims.json always produces the same bytes, so anyone can rebuild an
artifact and check its hash. A deliberation with blocking issues is never
frozen.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dcore import ARGKIT_COMMIT, __version__
from dcore.analyse import analyse
from dcore.checks import blocking, run_checks
from dcore.compile import compile_all
from dcore.model import Deliberation
from dcore.report import render_report
from dcore.viz import render_graph

ARTIFACT_NAME = "artifact.v1.json"
REPORT_NAME = "report.md"
GRAPH_NAME = "graph.md"
SUMS_NAME = "SHA256SUMS"


def load(path: Path) -> Deliberation:
    return Deliberation.model_validate_json(Path(path).read_text(encoding="utf-8"))


def build_artifact(deliberation: Deliberation) -> dict:
    issues = run_checks(deliberation)
    stopping = blocking(issues)
    if stopping:
        raise ValueError("blocking issues:\n" + "\n".join(
            f"  {i.target_id}: {i.message}" for i in stopping))
    return {
        "schema_version": "dcore/1",
        "engine": {"dcore": __version__, "argkit": ARGKIT_COMMIT[:12], "semantics": "grounded",
                   "build": "deterministic; no model call at build time"},
        "deliberation": deliberation.model_dump(mode="json"),
        "graphs": {k: g.model_dump(mode="json") for k, g in compile_all(deliberation).items()},
        "analysis": analyse(deliberation),
        "qc": {"issues": [i.model_dump(mode="json") for i in issues]},
    }


def render_json(artifact: dict) -> str:
    return json.dumps(artifact, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def freeze(folder: Path) -> tuple[Path, str]:
    """Build `folder/claims.json` into the artifact, report, graph and sums."""
    folder = Path(folder)
    artifact = build_artifact(load(folder / "claims.json"))
    payload = render_json(artifact).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    (folder / ARTIFACT_NAME).write_bytes(payload)
    report = render_report(artifact, digest).encode("utf-8")
    (folder / REPORT_NAME).write_bytes(report)
    graph = render_graph(artifact, digest).encode("utf-8")
    (folder / GRAPH_NAME).write_bytes(graph)
    sums = (f"{digest}  {ARTIFACT_NAME}\n"
            f"{hashlib.sha256(graph).hexdigest()}  {GRAPH_NAME}\n"
            f"{hashlib.sha256(report).hexdigest()}  {REPORT_NAME}\n")
    (folder / SUMS_NAME).write_bytes(sums.encode("utf-8"))
    return folder / ARTIFACT_NAME, digest
