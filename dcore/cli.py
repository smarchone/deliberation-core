"""Command line: python -m dcore <command> <deliberation folder>

  check    run the deterministic checks and list every issue
  analyse  print where each part stands (no files written)
  freeze   write artifact.v1.json, report.md and SHA256SUMS
  verify   rebuild from claims.json and confirm the hashes match
  curate   record a person's decision on an argument (accept or reject, with a note)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from dcore.analyse import analyse
from dcore.checks import blocking, run_checks
from dcore.freeze import ARTIFACT_NAME, SUMS_NAME, build_artifact, freeze, load, render_json


def _check(folder: Path) -> int:
    issues = run_checks(load(folder / "claims.json"))
    for issue in issues:
        print(f"{issue.severity.value:8} {issue.kind:28} {issue.target_id}: {issue.message}")
    stopping = blocking(issues)
    print(f"\n{len(stopping)} blocking, {len(issues) - len(stopping)} warnings")
    return 1 if stopping else 0


def _analyse(folder: Path) -> int:
    deliberation = load(folder / "claims.json")
    if blocking(run_checks(deliberation)):
        print("blocking issues; run `check` first")
        return 1
    parts = analyse(deliberation)["parts"]
    for sub_claim in deliberation.sub_claims:
        part = parts[sub_claim.id]
        print(f"{sub_claim.id:5} {part['signal']:20} {sub_claim.text}")
        for hinge in part["hinges"]:
            print(f"      hinge {' vs '.join(hinge['between'])}: {hinge['if_stronger']}")
    return 0


def _freeze(folder: Path) -> int:
    path, digest = freeze(folder)
    print(f"wrote {path}\nsha256 {digest}")
    return 0


def _verify(folder: Path) -> int:
    rebuilt = hashlib.sha256(render_json(build_artifact(load(folder / "claims.json")))
                             .encode("utf-8")).hexdigest()
    on_disk = hashlib.sha256((folder / ARTIFACT_NAME).read_bytes()).hexdigest()
    recorded = (folder / SUMS_NAME).read_text(encoding="utf-8").split()[0]
    ok = rebuilt == on_disk == recorded
    print(f"rebuilt {rebuilt}\non disk {on_disk}\nsums    {recorded}\n{'OK' if ok else 'MISMATCH'}")
    return 0 if ok else 1


def _curate(folder: Path, argument_id: str, accept: bool, note: str) -> int:
    path = folder / "claims.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    argument = next((a for a in data["arguments"] if a["id"] == argument_id), None)
    if argument is None:
        print(f"unknown argument {argument_id}")
        return 1
    argument["status"] = "curated_accepted" if accept else "curated_rejected"
    argument["check_note"] = note
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{argument_id} -> {argument['status']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dcore")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "analyse", "freeze", "verify"):
        sub.add_parser(name).add_argument("folder", type=Path)
    curate = sub.add_parser("curate")
    curate.add_argument("folder", type=Path)
    curate.add_argument("argument_id")
    decision = curate.add_mutually_exclusive_group(required=True)
    decision.add_argument("--accept", action="store_true")
    decision.add_argument("--reject", action="store_true")
    curate.add_argument("--note", required=True)
    args = parser.parse_args(argv)
    if args.command == "curate":
        return _curate(args.folder, args.argument_id, args.accept, args.note)
    return {"check": _check, "analyse": _analyse, "freeze": _freeze, "verify": _verify}[args.command](args.folder)


if __name__ == "__main__":
    sys.exit(main())
