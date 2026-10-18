"""Deterministic checks on a deliberation. No model, no network.

Two layers. dcore's own checks cover the front half (references resolve, every
piece of evidence is sourced, each side was researched, the wording is plain).
Then each sub-claim graph goes through argkit's checks (attack typing, dangling
edges, self-attacks, duplicates, missing citations).

Blocking issues stop the freeze. Warnings are carried into the artifact and
shown in the report, so a reader sees the same gaps the scripts saw.
"""

from __future__ import annotations

import re
from collections import Counter

from argkit.qc import CheckIssue, Severity, run_deterministic_checks
from argkit.schema import AttackType, CurationStatus

from dcore.compile import compile_all, part_order
from dcore.model import Deliberation, SourceKind, Stance, SubClaimKind

# Heated words that belong in `question.original`, not in a sub-claim. A sub-claim
# should read the same to both sides; the original wording is kept separately.
LOADED_WORDS = (
    "rig", "rigged", "rigging", "chor", "chori", "steal", "stolen", "traitor",
    "anti-national", "puppet", "slave", "godi", "urban naxal", "fascist", "dictator",
    "scam", "propaganda", "destroy", "murder of democracy",
)


def _issue(kind: str, severity: Severity, target: str, message: str) -> CheckIssue:
    return CheckIssue(kind=kind, severity=severity, target_id=target, message=message)


def _blocking(kind: str, target: str, message: str) -> CheckIssue:
    return _issue(kind, Severity.BLOCKING, target, message)


def _warning(kind: str, target: str, message: str) -> CheckIssue:
    return _issue(kind, Severity.WARNING, target, message)


def _check_unique_ids(d: Deliberation) -> list[CheckIssue]:
    ids = [s.id for s in d.sources] + [c.id for c in d.sub_claims] + [a.id for a in d.arguments]
    ids += [e.id for a in d.arguments for e in a.evidence]
    ids += [x.id for x in d.attacks] + [p.id for p in d.preferences]
    ids += [p.id for p in d.priorities] + [a.id for a in d.actions]
    return [_blocking("duplicate_id", i, f"id {i} is used {n} times")
            for i, n in sorted(Counter(ids).items()) if n > 1]


def _check_references(d: Deliberation) -> list[CheckIssue]:
    issues = []
    sub_claims = {c.id for c in d.sub_claims}
    sources = {s.id for s in d.sources}
    for argument in d.arguments:
        if argument.sub_claim not in sub_claims:
            issues.append(_blocking("unknown_sub_claim", argument.id,
                                    f"argument points at unknown sub-claim {argument.sub_claim}"))
        if not argument.evidence:
            issues.append(_blocking("no_evidence", argument.id, "an argument needs evidence"))
        for item in argument.evidence:
            if item.from_part is not None:
                if item.from_part not in sub_claims:
                    issues.append(_blocking("unknown_part", item.id,
                                            f"evidence rests on unknown part {item.from_part}"))
                elif item.from_part == argument.sub_claim:
                    issues.append(_blocking("self_link", item.id, "a part cannot rest on itself"))
            elif not item.sources:
                issues.append(_blocking("unsourced_evidence", item.id, "evidence cites no source"))
            for source_id in item.sources:
                if source_id not in sources:
                    issues.append(_blocking("unknown_source", item.id, f"unknown source {source_id}"))
    for attack in d.attacks:
        source, target = d.argument(attack.source), d.argument(attack.target)
        if source is None or target is None:
            issues.append(_blocking("dangling_attack", attack.id, "attack endpoint is not an argument"))
            continue
        if source.sub_claim != target.sub_claim:
            issues.append(_blocking("cross_sub_claim_attack", attack.id,
                                    "attacks stay within one sub-claim; link parts with from_part evidence"))
        if attack.type == AttackType.UNDERMINE:
            if attack.target_evidence not in {e.id for e in target.evidence}:
                issues.append(_blocking("undermine_without_evidence", attack.id,
                                        "an undermine must name one of the target's evidence ids"))
    for preference in d.preferences:
        for argument_id in (preference.preferred, preference.over):
            if d.argument(argument_id) is None:
                issues.append(_blocking("dangling_preference", preference.id,
                                        f"unknown argument {argument_id}"))
    for action in d.actions:
        for sub_claim_id in action.settles:
            if sub_claim_id not in sub_claims:
                issues.append(_blocking("unknown_sub_claim", action.id,
                                        f"action settles unknown sub-claim {sub_claim_id}"))
    return issues


def _check_link_cycles(d: Deliberation) -> list[CheckIssue]:
    """Parts may rest on each other, but never in a loop: each part is resolved
    after the parts it rests on."""
    try:
        part_order(d)
    except ValueError as error:
        return [_blocking("link_cycle", str(error), "parts rest on each other in a loop")]
    return []


def _check_status_notes(d: Deliberation) -> list[CheckIssue]:
    noted = {CurationStatus.CROSS_CHECKED, CurationStatus.CURATED_ACCEPTED,
             CurationStatus.CURATED_REJECTED}
    return [_blocking("status_without_note", a.id,
                      f"status {a.status.value} needs a check_note saying what checked it")
            for a in d.arguments if a.status in noted and not a.check_note]


def _check_sources(d: Deliberation) -> list[CheckIssue]:
    issues = [_blocking("source_without_url", s.id, "every source needs a url")
              for s in d.sources if not s.url.startswith(("http://", "https://"))]
    by_id = {s.id: s for s in d.sources}
    for argument in d.arguments:
        for item in argument.evidence:
            cited = [by_id[i] for i in item.sources if i in by_id]
            if cited and all(s.kind == SourceKind.PARTY for s in cited):
                issues.append(_warning("party_source_only", item.id,
                                       "backed only by a party's own claim; read it as an allegation"))
            if len({s.publisher for s in cited}) == 1 \
                    and cited[0].kind not in (SourceKind.COURT, SourceKind.OFFICIAL):
                issues.append(_warning("single_publisher", item.id,
                                       f"only one publisher ({cited[0].publisher}) backs this"))
    used = {i for a in d.arguments for e in a.evidence for i in e.sources}
    issues += [_warning("unused_source", s.id, "source is listed but never cited")
               for s in d.sources if s.id not in used]
    return issues


def _check_balance(d: Deliberation) -> list[CheckIssue]:
    """Fairness: anything beyond a plain fact must carry each side's best case."""
    issues = []
    for sub_claim in d.sub_claims:
        stances = {a.stance for a in d.arguments_for(sub_claim.id)
                   if a.status != CurationStatus.CURATED_REJECTED}
        if not stances:
            issues.append(_warning("unresearched", sub_claim.id, "no argument on either side yet"))
        elif sub_claim.kind != SubClaimKind.FACT and len(stances) < 2:
            missing = "challenge" if Stance.SUPPORTS in stances else "support"
            issues.append(_warning("one_sided", sub_claim.id,
                                   f"no {missing} researched for a {sub_claim.kind.value} claim"))
    return issues


def _check_wording(d: Deliberation) -> list[CheckIssue]:
    issues = []
    for sub_claim in d.sub_claims:
        lowered = sub_claim.text.lower()
        hits = [w for w in LOADED_WORDS if re.search(rf"\b{re.escape(w)}\b", lowered)]
        if hits:
            issues.append(_warning("loaded_wording", sub_claim.id,
                                   f"heated wording in a sub-claim: {', '.join(hits)}"))
    return issues


def run_checks(d: Deliberation) -> list[CheckIssue]:
    issues = (_check_unique_ids(d) + _check_references(d) + _check_link_cycles(d)
              + _check_status_notes(d) + _check_sources(d) + _check_balance(d) + _check_wording(d))
    if any(i.severity == Severity.BLOCKING for i in issues):
        return issues
    for sub_claim_id, graph in compile_all(d).items():
        for issue in run_deterministic_checks(graph):
            issues.append(issue.model_copy(update={"target_id": f"{sub_claim_id}:{issue.target_id}"}))
    return issues


def blocking(issues: list[CheckIssue]) -> list[CheckIssue]:
    return [i for i in issues if i.severity == Severity.BLOCKING]
