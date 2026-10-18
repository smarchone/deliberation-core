"""Compile a deliberation into argkit graphs: one graph per sub-claim.

Parts are linked through evidence: evidence with `from_part` is another part's
result. argkit has no chaining, so a link is resolved in order instead: the
part it rests on is resolved first, and if that part does not hold, a link
node attacks every argument that rests on it (see `to_framework`).

Each sub-claim becomes the root of its own `ArgumentGraph`. An argument that
supports it concludes the sub-claim's node; an argument that challenges it
concludes a `<id>.not` node ("it is not the case that ..."). Evidence becomes
evidence nodes, and each argument's reasoning becomes its inference node, so
argkit's attack-typing check (undermine -> evidence, undercut -> inference,
rebut -> conclusion) applies unchanged.

The one place dcore departs from argkit: which arguments are *live*. argkit only
admits `curated_accepted` (a human signed off). The MVP has no human curator in
the loop yet, so by default `cross_checked` arguments (a second, independent
model pass agreed) are live too. The report always says how many were checked
by a person, so nobody mistakes a machine check for a human one.
"""

from __future__ import annotations

from datetime import datetime

from argkit.aaf import Af
from argkit.schema import (
    Argument as KitArgument,
    ArgumentGraph,
    ClaimNode,
    ConflictNode,
    CurationStatus,
    EvidenceNode,
    InferenceNode,
    PreferenceNode,
    Provenance,
    Stance as KitStance,
)
from argkit.structured import derive_attacks

from dcore.model import Deliberation, Stance

DEFAULT_LIVE = frozenset({CurationStatus.CROSS_CHECKED, CurationStatus.CURATED_ACCEPTED})


def negation_id(sub_claim_id: str) -> str:
    return f"{sub_claim_id}.not"


def inference_id(argument_id: str) -> str:
    return f"{argument_id}.inference"


def _provenance(deliberation: Deliberation, *, status: CurationStatus = CurationStatus.CANDIDATE,
                citation: str | None = None, note: str | None = None) -> Provenance:
    return Provenance(
        generator_model=deliberation.generation.generator,
        created_at=datetime.fromisoformat(deliberation.generation.created_at),
        source_citation=citation,
        # argkit requires a confidence; dcore never uses it, so it is fixed and neutral.
        confidence=0.5,
        status=status,
        curator_note=note,
    )


def _citation(deliberation: Deliberation, source_ids: list[str]) -> str | None:
    parts = []
    for source_id in source_ids:
        source = deliberation.source(source_id)
        if source is not None:
            parts.append(f"{source.publisher}, {source.title} ({source.date}) {source.url}")
    return "; ".join(parts) or None


def compile_sub_claim(deliberation: Deliberation, sub_claim_id: str) -> ArgumentGraph:
    sub_claim = next(c for c in deliberation.sub_claims if c.id == sub_claim_id)
    base = _provenance(deliberation)
    claims = [
        ClaimNode(node_id=sub_claim.id, text=sub_claim.text, provenance=base),
        ClaimNode(node_id=negation_id(sub_claim.id),
                  text=f"It is not the case that: {sub_claim.text}", provenance=base),
    ]
    evidence, inferences, arguments = [], [], []
    for argument in deliberation.arguments_for(sub_claim.id):
        conclusion = sub_claim.id if argument.stance == Stance.SUPPORTS else negation_id(sub_claim.id)
        for item in argument.evidence:
            evidence.append(EvidenceNode(
                node_id=item.id, text=item.text,
                provenance=_provenance(deliberation, citation=_citation(deliberation, item.sources))))
        inferences.append(InferenceNode(
            node_id=inference_id(argument.id), text=argument.reasoning,
            premise_ids=[e.id for e in argument.evidence], conclusion_id=conclusion,
            provenance=base))
        arguments.append(KitArgument(
            argument_id=argument.id, title=argument.title,
            premise_ids=[e.id for e in argument.evidence], inference_id=inference_id(argument.id),
            conclusion_id=conclusion, strength=0.5,
            stance=KitStance.PRO if argument.stance == Stance.SUPPORTS else KitStance.CON,
            provenance=_provenance(deliberation, status=argument.status, note=argument.check_note)))
    ids = {a.argument_id for a in arguments}
    conflicts = []
    for attack in deliberation.attacks:
        if attack.source not in ids and attack.target not in ids:
            continue
        conflicts.append(ConflictNode(
            conflict_id=attack.id, attack_type=attack.type,
            source_argument_id=attack.source, target_argument_id=attack.target,
            target_node_id=_target_node(deliberation, attack.target, attack.type.value,
                                        attack.target_evidence),
            provenance=base))
    preferences = [
        PreferenceNode(preference_id=p.id, preferred_argument_id=p.preferred,
                       dispreferred_argument_id=p.over, rationale=p.rationale, provenance=base)
        for p in deliberation.preferences if p.preferred in ids or p.over in ids
    ]
    return ArgumentGraph(title=sub_claim.text, root_claim_id=sub_claim.id, claims=claims,
                         evidence=evidence, inferences=inferences, arguments=arguments,
                         conflicts=conflicts, preferences=preferences)


def _target_node(deliberation: Deliberation, target_id: str, attack_type: str,
                 target_evidence: str | None) -> str:
    target = deliberation.argument(target_id)
    if target is None:
        return target_evidence or target_id
    if attack_type == "undermine":
        return target_evidence or ""
    if attack_type == "undercut":
        return inference_id(target.id)
    return target.sub_claim if target.stance == Stance.SUPPORTS else negation_id(target.sub_claim)


def compile_all(deliberation: Deliberation) -> dict[str, ArgumentGraph]:
    return {c.id: compile_sub_claim(deliberation, c.id) for c in deliberation.sub_claims}


def part_order(deliberation: Deliberation) -> list[str]:
    """Sub-claim ids, each after the parts its arguments rest on. Raises
    ValueError naming a part caught in a loop."""
    known = {c.id for c in deliberation.sub_claims}
    needs = {c.id: sorted({e.from_part for a in deliberation.arguments_for(c.id) for e in a.evidence
                           if e.from_part in known and e.from_part != c.id})
             for c in deliberation.sub_claims}
    order, state = [], {}

    def visit(part: str) -> None:
        if state.get(part) == "done":
            return
        if state.get(part) == "visiting":
            raise ValueError(part)
        state[part] = "visiting"
        for needed in needs[part]:
            visit(needed)
        state[part] = "done"
        order.append(part)

    for c in deliberation.sub_claims:
        visit(c.id)
    return order


def link_id(part: str) -> str:
    return f"{part}.link"


def live_ids(graph: ArgumentGraph, live: frozenset = DEFAULT_LIVE) -> set[str]:
    return {a.argument_id for a in graph.arguments if a.provenance.status in live}


def to_framework(graph: ArgumentGraph, live: frozenset = DEFAULT_LIVE, *,
                 use_preferences: bool = True, links: list[dict] | None = None) -> Af:
    """argkit's `to_af`, with dcore's live set instead of curated-only, plus
    one node per link to a part that does not hold.

    A link to a part that fails attacks every argument resting on it, so they
    fall. A link to a contested part attacks itself as well: it stays open,
    and so, at best, do the arguments resting on it.
    """
    members = live_ids(graph, live)
    edges = [(a.attacker_argument_id, a.attacked_argument_id)
             for a in derive_attacks(graph, use_preferences=use_preferences)
             if a.attacker_argument_id in members and a.attacked_argument_id in members]
    nodes = set()
    for link in links or []:
        if link["effect"] == "holds" or link["argument"] not in members:
            continue
        node = link_id(link["part"])
        nodes.add(node)
        edges.append((node, link["argument"]))
        if link["effect"] == "open":
            edges.append((node, node))
    return Af.of(members | nodes, edges)
