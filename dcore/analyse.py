"""Signal and Analyse: what stands on each sub-claim, and what it hinges on.

All of this is computed, never judged by a model. For each sub-claim:

  1. Build the abstract framework from live arguments (`dcore.compile`).
  2. Label every argument with argkit's grounded semantics (accepted / rejected /
     undecided). Grounded is the sceptical choice: it only accepts what survives
     every challenge.
  3. Turn the labels into a plain-word signal for the sub-claim.
  4. Find the hinges: for every unresolved mutual attack, say what the sub-claim
     would become if either side were judged the stronger one.

Parts are resolved in order, so a part that rests on another (evidence with
`from_part`) sees that part's result: if it does not hold, the arguments
resting on it fall, or stay open while it is contested.

There is deliberately no signal for the overall question. It is made of parts
of different kinds (facts, interpretations, an intent), and collapsing them
into one verdict would be the engine taking a side.
"""

from __future__ import annotations

from enum import Enum

from argkit.aaf import grounded_labelling
from argkit.schema import ArgumentGraph, PreferenceNode, Stance as KitStance

from dcore.compile import DEFAULT_LIVE, compile_all, live_ids, part_order, to_framework
from dcore.model import Deliberation, Role


class Signal(str, Enum):
    SUPPORTED = "supported"      # the supporting case stands; no challenge stands
    CHALLENGED = "challenged"    # a challenge stands; no supporting case does
    BOTH_HOLD = "both hold in part"  # each side has a standing argument that the other does not defeat
    CONTESTED = "contested"      # the two sides block each other; nothing is settled
    UNPROVEN = "unproven either way"  # every live argument on both sides was defeated
    UNVERIFIED = "unverified"    # no argument has passed checking yet


PLAIN = {
    Signal.SUPPORTED: "The supporting case holds up, and no challenge to it stands.",
    Signal.CHALLENGED: "A challenge holds up, and the supporting case does not.",
    Signal.BOTH_HOLD: "Each side makes a point that stands; they are not really in conflict.",
    Signal.CONTESTED: "The two sides block each other; it is open.",
    Signal.UNPROVEN: "Neither side's case survives the challenges against it.",
    Signal.UNVERIFIED: "Nothing on this part has passed checking yet.",
}


# What an argument resting on a part gets from that part's signal.
LINK_EFFECT = {
    Signal.SUPPORTED: "holds",
    Signal.BOTH_HOLD: "holds",
    Signal.CONTESTED: "open",
    Signal.CHALLENGED: "fails",
    Signal.UNPROVEN: "fails",
    Signal.UNVERIFIED: "fails",
}


def signal_for(graph: ArgumentGraph, labels: dict[str, str], live: set[str],
               cases: set[str] | None = None) -> Signal:
    """`cases` are the direct arguments for or against the sub-claim; objections
    shape the outcome only through their attacks. Defaults to every argument."""
    cases = live if cases is None else live & cases
    if not cases:
        return Signal.UNVERIFIED
    stance = {a.argument_id: a.stance for a in graph.arguments}
    accepted = {stance[a] for a in cases if labels.get(a) == "accepted"}
    pro_in, con_in = KitStance.PRO in accepted, KitStance.CON in accepted
    if pro_in and con_in:
        return Signal.BOTH_HOLD
    if pro_in:
        return Signal.SUPPORTED
    if con_in:
        return Signal.CHALLENGED
    if any(labels.get(a) == "undecided" for a in cases):
        return Signal.CONTESTED
    return Signal.UNPROVEN


def _status(graph: ArgumentGraph, live_set: frozenset, cases: set[str] | None = None,
            links: list[dict] | None = None) -> tuple[Signal, dict[str, str]]:
    af = to_framework(graph, live_set, links=links)
    labels = grounded_labelling(af)
    return signal_for(graph, labels, set(af.arguments), cases), labels


def _with_preference(graph: ArgumentGraph, preferred: str, over: str) -> ArgumentGraph:
    """The graph with one hypothetical preference added (and any opposite one removed)."""
    template = graph.arguments[0].provenance
    kept = [p for p in graph.preferences
            if (p.preferred_argument_id, p.dispreferred_argument_id) != (over, preferred)]
    hypothetical = PreferenceNode(preference_id=f"what-if:{preferred}>{over}",
                                  preferred_argument_id=preferred, dispreferred_argument_id=over,
                                  rationale="hypothetical, for hinge analysis", provenance=template)
    return graph.model_copy(update={"preferences": [*kept, hypothetical]})


def hinges(graph: ArgumentGraph, live_set: frozenset = DEFAULT_LIVE,
           cases: set[str] | None = None, links: list[dict] | None = None) -> list[dict]:
    """Every unresolved two-way attack, and what each way of resolving it does.

    A pair (a, b) is a hinge when a and b attack each other in the live
    framework. Resolving it means a curator judges one stronger (a preference).
    Undercuts ignore preferences, so a pair joined by an undercut cannot be
    resolved this way; those are reported as `needs_new_evidence`.
    """
    signal, _ = _status(graph, live_set, cases, links)
    af = to_framework(graph, live_set, links=links)
    pairs = sorted({tuple(sorted((x, y))) for (x, y) in af.attacks
                    if x != y and (y, x) in af.attacks})
    result = []
    for a, b in pairs:
        outcomes = {}
        for preferred, over in ((a, b), (b, a)):
            outcomes[preferred] = _status(_with_preference(graph, preferred, over),
                                          live_set, cases, links)[0].value
        movable = len(set(outcomes.values()) | {signal.value}) > 1
        result.append({
            "between": [a, b],
            "if_stronger": outcomes,
            "moves_the_signal": movable,
            "needs_new_evidence": not movable,
        })
    return result


def rests_on(graph: ArgumentGraph, labels: dict[str, str], cases: set[str]) -> list[str]:
    """For a part that stands, the arguments it would fall without: the only
    accepted case on a side."""
    stance = {a.argument_id: a.stance for a in graph.arguments}
    out = []
    for side in (KitStance.PRO, KitStance.CON):
        accepted = [a for a in sorted(cases) if labels.get(a) == "accepted" and stance[a] == side]
        if len(accepted) == 1:
            out.append(accepted[0])
    return out


def links_for(deliberation: Deliberation, sub_claim_id: str, parts: dict) -> list[dict]:
    """Each piece of evidence in this part that rests on another part, with
    that part's (already computed) signal and what it means here."""
    return [{"argument": a.id, "evidence": e.id, "part": e.from_part,
             "part_signal": parts[e.from_part]["signal"],
             "effect": LINK_EFFECT[Signal(parts[e.from_part]["signal"])]}
            for a in deliberation.arguments_for(sub_claim_id) for e in a.evidence
            if e.from_part is not None]


def analyse(deliberation: Deliberation, live_set: frozenset = DEFAULT_LIVE) -> dict:
    graphs = compile_all(deliberation)
    parts = {}
    for sub_claim_id in part_order(deliberation):
        graph = graphs[sub_claim_id]
        links = links_for(deliberation, sub_claim_id, parts)
        af = to_framework(graph, live_set, links=links)
        labels = grounded_labelling(af)
        arguments = {a.argument_id for a in graph.arguments}
        live = set(af.arguments) & arguments
        cases = {a.id for a in deliberation.arguments_for(sub_claim_id) if a.role == Role.CASE}
        signal = signal_for(graph, labels, live, cases)
        unpreferred = to_framework(graph, live_set, use_preferences=False, links=links)
        without = signal_for(graph, grounded_labelling(unpreferred),
                             set(unpreferred.arguments) & arguments, cases)
        parts[sub_claim_id] = {
            "signal": signal.value,
            "plain": PLAIN[signal],
            "labels": {a: labels[a] for a in sorted(labels) if a in arguments},
            "live_arguments": sorted(live),
            "not_live": sorted(arguments - live_ids(graph, live_set)),
            "attacks": sorted([list(e) for e in af.attacks]),
            "hinges": hinges(graph, live_set, cases, links),
            "rests_on": rests_on(graph, labels, live & cases),
            "links": links,
            # The stated preferences this outcome depends on, if dropping them changes it.
            "depends_on_judgment": (sorted(p.preference_id for p in graph.preferences)
                                    if without != signal else []),
        }
    return {"parts": parts, "live_statuses": sorted(s.value for s in live_set)}
