"""dcore: checks, signals, hinges, and a reproducible freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


from dcore.analyse import analyse
from dcore.checks import blocking, run_checks
from dcore.freeze import ARTIFACT_NAME, SUMS_NAME, build_artifact, freeze, load, render_json
from dcore.model import Deliberation

EXAMPLE = Path(__file__).resolve().parent.parent / "claims" / "cec-government-elections"


def _evidence(argument_id: str, source: str = "S1") -> list[dict]:
    return [{"id": f"{argument_id}.e1", "text": "a checkable statement", "sources": [source]}]


def _argument(argument_id: str, stance: str, **extra) -> dict:
    return {"id": argument_id, "sub_claim": "K1", "stance": stance, "title": argument_id,
            "reasoning": "because", "evidence": _evidence(argument_id),
            "status": "cross_checked", "check_note": "checked", **extra}


def _base(**overrides) -> dict:
    data = {
        "id": "t", "as_of": "2026-01-01",
        "question": {"original": "x", "plain": "x?", "reframe_note": "none"},
        "sources": [{"id": "S1", "title": "t", "publisher": "p", "url": "https://example.org",
                     "date": "2026-01-01", "kind": "court"}],
        "sub_claims": [{"id": "K1", "kind": "interpretation", "text": "a claim",
                        "settle_by": "a test"}],
        "arguments": [_argument("P", "supports"), _argument("C", "challenges")],
        "generation": {"generator": "test", "created_at": "2026-01-01T00:00:00+00:00"},
    }
    data.update(overrides)
    return data


def _signal(data: dict) -> str:
    return analyse(Deliberation.model_validate(data))["parts"]["K1"]["signal"]


def test_unanswered_case_is_supported_and_unanswered_challenge_both_hold():
    assert _signal(_base(arguments=[_argument("P", "supports")])) == "supported"
    assert _signal(_base()) == "both hold in part"


def test_mutual_rebut_is_contested_with_a_hinge_each_way():
    data = _base(attacks=[
        {"id": "X1", "source": "C", "target": "P", "type": "rebut", "note": ""},
        {"id": "X2", "source": "P", "target": "C", "type": "rebut", "note": ""},
    ])
    part = analyse(Deliberation.model_validate(data))["parts"]["K1"]
    assert part["signal"] == "contested"
    assert part["hinges"] == [{"between": ["C", "P"],
                               "if_stronger": {"C": "challenged", "P": "supported"},
                               "moves_the_signal": True, "needs_new_evidence": False}]


def test_preference_settles_a_hinge_and_is_reported_as_a_judgment():
    data = _base(
        attacks=[{"id": "X1", "source": "C", "target": "P", "type": "rebut", "note": ""},
                 {"id": "X2", "source": "P", "target": "C", "type": "rebut", "note": ""}],
        preferences=[{"id": "PR1", "preferred": "C", "over": "P", "rationale": "r"}])
    part = analyse(Deliberation.model_validate(data))["parts"]["K1"]
    assert part["signal"] == "challenged"
    assert part["depends_on_judgment"] == ["PR1"]


def test_objections_shape_the_outcome_but_do_not_count_as_cases():
    data = _base(
        arguments=[_argument("P", "supports"), _argument("C", "challenges"),
                   _argument("O1", "challenges", role="objection"),
                   _argument("O2", "supports", role="objection")],
        attacks=[{"id": "X1", "source": "O1", "target": "P", "type": "undercut", "note": ""},
                 {"id": "X2", "source": "O2", "target": "C", "type": "undercut", "note": ""}])
    assert _signal(data) == "unproven either way"


def test_unchecked_arguments_are_not_live():
    data = _base(arguments=[_argument("P", "supports", status="candidate", check_note=None)])
    assert _signal(data) == "unverified"


def test_blocking_checks():
    unknown_source = _base(arguments=[{**_argument("P", "supports"),
                                       "evidence": _evidence("P", source="S9")}])
    no_note = _base(arguments=[_argument("P", "supports", check_note=None)])
    loose_undermine = _base(attacks=[{"id": "X1", "source": "C", "target": "P",
                                      "type": "undermine", "note": ""}])
    for data in (unknown_source, no_note, loose_undermine):
        assert blocking(run_checks(Deliberation.model_validate(data)))


def test_warnings_for_one_sided_and_loaded_wording():
    data = _base(arguments=[_argument("P", "supports")])
    data["sub_claims"][0]["text"] = "they rigged it"
    kinds = {i.kind for i in run_checks(Deliberation.model_validate(data))}
    assert {"one_sided", "loaded_wording"} <= kinds


def test_freeze_is_byte_reproducible(tmp_path):
    for run in ("a", "b"):
        folder = tmp_path / run
        folder.mkdir()
        (folder / "claims.json").write_text(json.dumps(_base()), encoding="utf-8")
        freeze(folder)
    assert (tmp_path / "a" / ARTIFACT_NAME).read_bytes() == (tmp_path / "b" / ARTIFACT_NAME).read_bytes()


def test_frozen_example_matches_its_source():
    """Deploy guard: the committed example artifact is exactly what its
    claims.json builds to, and its recorded hash is right."""
    payload = (EXAMPLE / ARTIFACT_NAME).read_bytes()
    recorded = (EXAMPLE / SUMS_NAME).read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(payload).hexdigest() == recorded
    assert render_json(build_artifact(load(EXAMPLE / "claims.json"))).encode("utf-8") == payload
