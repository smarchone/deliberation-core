"""Get a video's timestamped transcript into debates/<id>/transcript.json.

Plumbing only: no judgment happens here.

    # From YouTube (needs network access to youtube.com):
    python fetch.py https://www.youtube.com/watch?v=VIDEO_ID --out debates/my-debate

    # From a transcript you already have: YouTube's "Show transcript" panel
    # copied as text, or a .vtt / .srt subtitle file.
    python fetch.py https://www.youtube.com/watch?v=VIDEO_ID --out debates/my-debate --from pasted.txt

Writes transcript.json (segments with start times in seconds) and
transcript.txt (one "[mm:ss] text" line per segment, for reading).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

LANGS = ["hi", "en", "en-IN", "hi-IN"]


def video_id(url_or_id: str) -> str:
    """Pull the 11-character video id out of any common YouTube URL form."""
    s = url_or_id.strip()
    if re.fullmatch(r"[\w-]{11}", s):
        return s
    u = urlparse(s)
    if u.hostname and u.hostname.endswith("youtu.be"):
        return u.path.lstrip("/")[:11]
    if "v" in parse_qs(u.query):
        return parse_qs(u.query)["v"][0][:11]
    m = re.search(r"/(?:shorts|live|embed)/([\w-]{11})", u.path)
    if m:
        return m.group(1)
    raise SystemExit(f"Can't find a YouTube video id in {url_or_id!r}")


# --- reading transcripts we were given -------------------------------------

_CLOCK = r"(?:(\d+):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?"


def clock_to_seconds(h: str | None, m: str, s: str, frac: str | None = None) -> float:
    t = int(h or 0) * 3600 + int(m) * 60 + int(s)
    if frac:
        t += int(frac.ljust(3, "0")) / 1000
    return t


def parse_cues(text: str) -> list[dict]:
    """.vtt / .srt: blocks with an "a --> b" line followed by caption text."""
    segs = []
    for block in re.split(r"\n\s*\n", text.replace("\r", "")):
        lines = [l for l in block.split("\n") if l.strip()]
        for i, line in enumerate(lines):
            m = re.match(rf"\s*{_CLOCK}\s*-->\s*{_CLOCK}", line)
            if m:
                g = m.groups()
                start, end = clock_to_seconds(*g[:4]), clock_to_seconds(*g[4:])
                body = " ".join(re.sub(r"<[^>]+>", "", l).strip() for l in lines[i + 1:])
                if body:
                    segs.append({"start": start, "dur": max(end - start, 0), "text": body})
                break
    # Auto-captions repeat each line as the next cue scrolls in; drop exact repeats.
    out = []
    for s in segs:
        if out and s["text"] == out[-1]["text"]:
            continue
        out.append(s)
    return out


def parse_panel(text: str) -> list[dict]:
    """YouTube's "Show transcript" panel copied as text.

    Either "0:05 some words" on one line, or the time on its own line with the
    words below it. Screen-reader lines like "5 seconds" are skipped.
    """
    segs: list[dict] = []
    for raw in text.replace("\r", "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if re.fullmatch(r"(\d+ hours?,? ?)?(\d+ minutes?,? ?)?(\d+ seconds?)?", line):
            continue
        m = re.match(rf"^{_CLOCK}\s*(.*)$", line)
        if m:
            g = m.groups()
            segs.append({"start": clock_to_seconds(*g[:4]), "text": g[4].strip()})
        elif segs:
            segs[-1]["text"] = (segs[-1]["text"] + " " + line).strip()
    segs = [s for s in segs if s["text"]]
    for a, b in zip(segs, segs[1:]):
        a["dur"] = max(b["start"] - a["start"], 0)
    if segs:
        segs[-1].setdefault("dur", 4.0)
    return segs


def parse_given(text: str) -> list[dict]:
    segs = parse_cues(text) if "-->" in text else parse_panel(text)
    if not segs:
        raise SystemExit("Couldn't find any timestamped lines in that transcript.")
    return segs


# --- fetching from YouTube ---------------------------------------------------

def fetch_youtube(vid: str) -> tuple[list[dict], str, bool]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        raise SystemExit("pip install youtube-transcript-api, or pass --from with a transcript file.")
    try:
        api = YouTubeTranscriptApi()
        found = api.list(vid)
        try:
            tr = found.find_transcript(LANGS)
        except Exception:
            tr = next(iter(found))
        got = tr.fetch()
    except Exception as e:  # network blocks, no captions, etc.
        raise SystemExit(
            f"Couldn't get captions from YouTube ({type(e).__name__}: {str(e)[:200]}).\n"
            "Open the video, choose ... > Show transcript, copy it into a file, "
            "and rerun with --from that file."
        )
    segs = [{"start": s.start, "dur": s.duration, "text": s.text.replace("\n", " ").strip()}
            for s in got.snippets if s.text.strip()]
    return segs, tr.language_code, tr.is_generated


def mmss(t: float) -> str:
    t = int(t)
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", help="YouTube URL or video id")
    p.add_argument("--out", required=True, help="output folder, e.g. debates/my-debate")
    p.add_argument("--from", dest="given", help="transcript file to use instead of fetching")
    p.add_argument("--lang", help="language code of a given transcript, e.g. hi or en")
    p.add_argument("--title", default="", help="video title, shown on the page")
    p.add_argument("--channel", default="", help="channel name, shown on the page")
    a = p.parse_args(argv)

    vid = video_id(a.video)
    if a.given:
        segs = parse_given(Path(a.given).read_text(encoding="utf-8"))
        source, lang, generated = "given", a.lang or "", None
    else:
        segs, lang, generated = fetch_youtube(vid)
        source = "youtube"

    for i, s in enumerate(segs, 1):
        s["n"] = i
        s["start"] = round(s["start"], 2)
        s["dur"] = round(s.get("dur", 0), 2)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    doc = {
        "video": {"id": vid, "url": f"https://www.youtube.com/watch?v={vid}",
                  "title": a.title, "channel": a.channel},
        "source": source,
        "lang": lang,
        "auto_generated": generated,
        "duration": round(segs[-1]["start"] + segs[-1]["dur"], 2),
        "segments": segs,
    }
    (out / "transcript.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "transcript.txt").write_text(
        "".join(f"[{mmss(s['start'])}] {s['text']}\n" for s in segs), encoding="utf-8")
    print(f"{len(segs)} lines, {mmss(doc['duration'])} long -> {out}/transcript.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
