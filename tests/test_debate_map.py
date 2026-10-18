"""Tests for the debate-map skill's scripts (fetch, check, render)."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude/skills/debate-map/scripts"))
import check  # noqa: E402
import fetch  # noqa: E402
import render  # noqa: E402

TR = {
    "video": {"id": "abcdefghijk", "url": "https://www.youtube.com/watch?v=abcdefghijk",
              "title": "Test debate", "channel": "Test channel"},
    "source": "given", "lang": "en", "auto_generated": None, "duration": 300,
    "segments": [{"n": 1, "start": 0, "dur": 300, "text": "..."}],
}
MAP = {
    "topic": "Should the city add bus lanes?",
    "voices": [
        {"id": "A", "role": "anchor", "basis": "Asks the questions"},
        {"id": "B", "role": "panelist", "basis": "Argues for bus lanes"},
        {"id": "C", "role": "panelist", "basis": "Argues against"},
    ],
    "turns": [
        {"voice": "A", "start": 0, "end": 20},
        {"voice": "B", "start": 20, "end": 120},
        {"voice": "C", "start": 120, "end": 180},
        {"voice": "A", "start": 180, "end": 200},
        {"voice": "C", "start": 200, "end": 290},
    ],
    "points": [
        {"id": "P1", "parent": None, "kind": "question", "voice": "A", "to": "B", "t": 10,
         "text": "Asks what bus lanes cost", "outcome": "answered", "answered_at": "P2"},
        {"id": "P2", "parent": "P1", "kind": "reply", "voice": "B", "t": 30, "text": "Gives a cost figure"},
        {"id": "P3", "parent": "P2", "kind": "challenge", "voice": "C", "t": 130, "text": "Says shops lose parking"},
        {"id": "P4", "parent": None, "kind": "question", "voice": "A", "to": "C", "t": 185,
         "text": "Asks for evidence on shop losses", "outcome": "not_answered", "followed_up": False,
         "note": "Voice C spoke about traffic instead", "label": "dodge"},
    ],
    "moments": [{"t": 125, "kind": "interruption", "by": "C", "of": "B", "note": "Before B finished"}],
    "report": {"summary": "A short debate.", "takeaways": ["One"], "actions": ["Check the cost figure"]},
}


def test_video_id_forms():
    for u in ["abcdefghijk", "https://youtu.be/abcdefghijk?t=3",
              "https://www.youtube.com/watch?v=abcdefghijk&t=10s",
              "https://www.youtube.com/live/abcdefghijk"]:
        assert fetch.video_id(u) == "abcdefghijk"


def test_parse_panel_both_layouts():
    two_line = "0:00\nnamaste\n0 seconds\n0:05\naaj ki bahas\n1:02:03\nend"
    segs = fetch.parse_given(two_line)
    assert [s["start"] for s in segs] == [0, 5, 3723]
    assert segs[1]["text"] == "aaj ki bahas" and segs[0]["dur"] == 5
    one_line = fetch.parse_given("0:00 hello there\n0:04 next line\ncontinued")
    assert one_line[1]["text"] == "next line continued"


def test_parse_vtt_drops_repeats():
    vtt = ("WEBVTT\n\n00:00:01.000 --> 00:00:03.500\n<c>hello</c>\n\n"
           "00:00:03.500 --> 00:00:05.000\nhello\n\n00:00:05.000 --> 00:00:07.000\nworld\n")
    segs = fetch.parse_given(vtt)
    assert [(s["start"], s["text"]) for s in segs] == [(1.0, "hello"), (5.0, "world")]


def test_clean_map_passes():
    err, warn = check.check(TR, MAP)
    assert err == [] and warn == []


def test_check_catches_errors():
    m = copy.deepcopy(MAP)
    m["points"][2]["parent"] = "P9"
    m["points"][3]["outcome"] = "maybe"
    m["turns"][1]["voice"] = "Z"
    m["moments"][0]["by"] = None
    err, _ = check.check(TR, m)
    joined = " ".join(err)
    assert "P9" in joined and "outcome" in joined and "'Z'" in joined and "interruption" in joined


def test_label_words_warn_only_in_shown_text():
    m = copy.deepcopy(MAP)
    m["points"][3]["note"] = "Voice C dodged the question"
    _, warn = check.check(TR, m)
    assert any("dodged" in w for w in warn)


def test_stats():
    rows = {r["voice"]: r for r in check.stats(TR, MAP)}
    assert rows["B"]["seconds"] == 100 and rows["C"]["seconds"] == 150
    assert rows["A"]["asked"] == 2
    assert rows["B"]["answered"] == 1 and rows["C"]["not_answered"] == 1
    assert rows["C"]["interrupted_others"] == 1 and rows["B"]["was_interrupted"] == 1
    assert abs(sum(r["share"] for r in rows.values()) - 1) < 1e-9


def test_render(tmp_path):
    (tmp_path / "transcript.json").write_text(json.dumps(TR))
    (tmp_path / "map.json").write_text(json.dumps(MAP))
    assert render.main([str(tmp_path)]) == 0
    html = (tmp_path / "page.html").read_text()
    assert "watch?v=abcdefghijk&amp;t=185s" in html
    assert "No direct answer by Voice C. Not asked again" in html
    assert "dodge" not in html  # private labels never reach the page
    assert "vh" not in html.replace("vhs", "")


def test_render_refuses_bad_map(tmp_path):
    m = copy.deepcopy(MAP)
    del m["report"]
    (tmp_path / "transcript.json").write_text(json.dumps(TR))
    (tmp_path / "map.json").write_text(json.dumps(m))
    assert render.main([str(tmp_path)]) == 1
    assert not (tmp_path / "page.html").exists()
