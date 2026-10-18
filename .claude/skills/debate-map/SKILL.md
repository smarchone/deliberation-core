---
name: debate-map
description: Turn a recorded debate, townhall or podcast on YouTube into one HTML page with the argument thread (claims, replies, challenges, questions left unanswered, each timestamped) and a "how this debate went" report with per-voice stats. Use when asked to map, break down or report on a video debate or discussion.
---

# Debate map

You do the judgment work; the scripts do the plumbing. Never hand-count a stat
or hand-write HTML: `check.py` and `render.py` compute those from the file you
write. There is no fact-checking here: the map shows what was said and done,
not whether it is true.

Everything lives in one folder, `debates/<id>/`:

| File | Written by |
| --- | --- |
| `transcript.json`, `transcript.txt` | `fetch.py` |
| `map.json` | you |
| `page.html` | `render.py` |

Scripts are in `.claude/skills/debate-map/scripts/` and need only Python 3.10+
(plus `youtube-transcript-api` to fetch captions).

## Principles (non-negotiable)

- **Actions, not labels.** The page describes what someone did, with a time:
  "no direct answer; turned to fuel prices at 12:40". Never "dodged", "lied",
  "biased", "propaganda". A private `label` on a point may carry your tag
  (`"dodge"`, `"loaded question"`); it is never shown. `check.py` warns when a
  label word leaks into shown text.
- **Take no sides.** No winner, no score, no verdict on a person or a side. The
  report is "how this debate went", never "the anchor failed".
- **Anonymous voices.** Voice A, B, C. No names, even if the video says them.
- **Fair paraphrase.** Each point in words its own speaker would accept, in the
  language of the person asking. Keep the original words in `quote`.
- **Say what you inferred.** Voices come from context, so every count is
  approximate, and each voice's `basis` says how you told it apart.

## Steps

1. **Fetch.** `python fetch.py <youtube-url> --out debates/<id> --title "..." --channel "..."`.
   If YouTube is blocked (common from cloud machines) it says so. Then ask for
   the transcript: on YouTube, "... > Show transcript", copy it all, paste it;
   or a `.vtt`/`.srt` file. Save it and rerun with `--from <file> --lang hi`.
   `<id>` is a short kebab-case slug of the topic.

2. **Read** `transcript.txt` end to end before writing anything.

3. **Voices.** Work out the distinct voices from context: who asks and hands
   the floor (usually the anchor), who answers which line of argument,
   addressing ("aap bataiye..."), stance continuity. Use as few voices as the
   transcript supports. Don't guess when it's unclear: give the stretch to the
   most likely voice and say so in `basis`.

4. **Turns.** Mark who held the floor, in order, covering the talk:
   `{"voice": "B", "start": 61.0, "end": 118.5}`. Use caption start times.

5. **Points.** Pull out the moves that matter, not every sentence:
   - `question`: a question put to someone. Needs `to` (or `null` for the room),
     `outcome` (`answered`, `partly`, `not_answered`), `answered_at` (the point
     that answers it) and `followed_up` (did anyone come back to it).
   - `claim`: a statement offered as true or as a reason.
   - `reply`, `challenge`, `concession`, `agreement`: responses; set `parent` to
     the point they respond to.
   A point with no `parent` starts a line of the thread. Every point has a `t`
   (seconds) near where it is said. `note` (shown) describes an action, e.g.
   "Moved to the opposition's record instead". Merge repeats into one point.

6. **Moments.** Talk-overs and turns in the debate:
   `{"t": 402, "kind": "interruption", "by": "C", "of": "B", "note": "..."}`.
   Kinds: `interruption` (needs `by` and `of`), `crosstalk`, `topic_change`,
   `other`. Only mark what the captions show (cut-off sentences, "let me
   finish", a new voice mid-answer); crosstalk often garbles captions.

7. **Report.** `summary` (3 to 5 sentences: what was discussed and how it
   went), `takeaways` (3 to 6: what a viewer should notice), `actions` (2 to 5
   concrete things a viewer could do next: what to check, which question to
   ask), optional `left_open` (questions the debate raised and never settled).
   Describe the debate's actions; don't judge people.

8. **Check and render.** `python check.py debates/<id>` until it prints OK
   and the warnings are dealt with, then `python render.py debates/<id>`.
   Read the page once as someone on either side would. If either side would
   call a line unfair, rewrite it.

## map.json

```json
{
  "topic": "Neutral one-line question the debate is about",
  "voices": [
    {"id": "A", "role": "anchor", "basis": "Asks the questions and hands the floor"}
  ],
  "turns": [{"voice": "A", "start": 0, "end": 42.5}],
  "points": [
    {"id": "P1", "parent": null, "kind": "question", "voice": "A", "to": "B", "t": 30,
     "text": "Asks whether prices rose this year", "quote": "...",
     "outcome": "not_answered", "answered_at": null, "followed_up": false,
     "note": "Voice B spoke about the previous government instead", "label": "dodge"}
  ],
  "moments": [{"t": 95, "kind": "interruption", "by": "C", "of": "B", "note": "..."}],
  "report": {"summary": "...", "takeaways": ["..."], "actions": ["..."], "left_open": ["..."]}
}
```

Roles: `anchor`, `panelist`, `guest`, `audience`, `other`.

## Stats the page shows (computed, per voice)

Talk time and share, turns, talked over others, was talked over, questions
asked, questions put to them (answered, partly, no direct answer) and how many
of the unanswered ones were asked again. The last one, read across voices, shows
how the moderation went without anyone saying so.

## Limits

- No speaker labels in captions, so voices and every count are approximate.
- Crosstalk garbles auto-captions; the thread is thinnest where it was loudest.
- No fact-checking: a claim on the map is what was said, not what is true.
