---
name: clip-live
description: Record live streams and turn the best moments into finished 9:16 clips with hook, captions and credit. Use for "clip", "make clips", "go clip xQc", "get clips from who's live", or any request to produce clips from streams.
---

# Clip live streams

Goal: as many good, credited clips as possible, as fast as possible, with no clip that breaks the playbook.

The target is **10 clean clips per batch** (20+ a day). A clip with a black opening, a frozen picture or missing sound is worse than no clip, so every clip passes an automatic QC check before it counts.

## 1. Pick sources (1 min)

- If the person named streamers, use them.
- Otherwise run `python tools/clipit.py live <slugs from 01_WORKING/08_notes/watchlist_*.csv tier A>` and take the live ones with the most viewers.
- Prefer English-speaking, high-reaction streamers for the fan page. Non-English streams only for moments that work without words.
- For a 10-clip batch: **5 streams x 200 seconds**. Each recording gives 3 or 4 candidate moments, so you get 15+ to choose 10 from.

## 2. Record and score (runs in the background)

```
python tools/clipit.py grab kick:xqc kick:theburntpeanut kick:lordkebun kick:ramee twitch:kaicenat --secs 200
```

Run it in the background. While it runs, write hook ideas from the stream titles. Recording uses streamlink, which does not drop pieces of the stream. If it ever prints `[warn] ... gap(s)`, the clips automatically avoid those gaps.

For each recording it prints a **review sheet** path and its candidate windows (22 to 45 seconds): score, start-end seconds, transcript. The review sheet (`<rec_id>_sheet.jpg`) is one image with a row of 3 frames per window, labelled with its time.

## 3. Choose (this is the judgment step)

Read each recording's review sheet (one image per recording, not one per frame) and the transcripts. Keep a window only if:

- something happens: a reaction, chaos, a fail, a funny line, a useful tip
- it is not an ad, a loading screen, a menu or a long story cutscene
- nothing in it spoils the story, has nudity or could get the account struck

Expect about 40% of windows to be usable: streamers sit in cutscenes, menus and giveaway shout-outs. For N clips, record enough for 2.5 x N windows (each 5-minute recording gives 5). If a batch comes up short, record 2 or 3 more streams while the good ones render, rather than padding with weak clips.

You may trim start and end, but keep clips **22 to 45 seconds** (the person wants them long enough to land). Windows are already cut on word boundaries, so prefer the given times. Never stretch a window across a gap. Drop weak windows. If fewer than 10 are good, say so; don't pad.

## 4. Write the hooks

Use the `hooks-and-copy` skill. One hook per clip, 8 words max, true to the clip, no spoilers.

## 5. Render all of them in one command

Write a plan file into the day's transcripts folder, `01_WORKING/06_transcripts/<date>/plan_<time>.json`:

```json
[
  {"rid": "xqc_231500", "start": 41.2, "end": 78.0, "hook": "He did NOT expect the cops that fast", "tag": "t1"},
  {"rid": "lordkebun_231500", "start": 12.0, "end": 49.5, "hook": "First jet ski in Vice City goes wrong", "tag": "t1"}
]
```

Then:

```
python tools/clipit.py batch 01_WORKING/06_transcripts/<date>/plan_<time>.json
```

Run it in the background. It renders `max_parallel_renders` at a time, QCs every clip and prints one table. For each clip that passes:

- the clip goes to `02_OUTPUTS/01_clips_ready_to_post/<date>/`
- the post text goes to `02_OUTPUTS/03_post_copy/<date>/` (hook, credit, hashtags, QC result)
- a row goes in `00_TRACKER/clip_log.csv`

A clip that fails QC goes to `01_WORKING/09_qc_failed/<date>/` and is logged as `qc_failed`. Never move it to outputs. Pick another window instead.

## 6. What QC checks (automatic)

| Check | Fail means |
|---|---|
| Picture and sound both start at 0.0s | blank or silent opening |
| Picture and sound both run the full clip length | sound cuts out or picture stops early |
| No black frames at the start, no long black stretch | dead opening |
| No silence of 3s or more | audio dropout |
| Lip sync: sound and picture lined up against the source separately | off by 0.1s or more = FAIL. "not measurable" = WARN: tell the person to watch it once |
| Picture frozen 2.5s+ | WARN only (could be a menu or loading screen); look at that clip |

Also look at one frame per clip (`ffmpeg -ss 5 -i clip.mp4 -frames:v 1 -vf scale=540:-2 check.jpg` into your scratch folder, not into `02_OUTPUTS`): hook readable, captions not covering the facecam, credit visible.

## 7. Report and log

- Tell the person in a short table: clip, length, hook, verdict ("strong", "ok", "test only"). QC failures in one line.
- Send the best 1 or 2 clips with SendUserFile if that tool exists.
- If a visual log page exists (`dashboard_url` in config), add the clips with the `clip-log` skill.

## Speed rules

- One `grab` for all streams, one `batch` for all clips. Don't render clips one by one.
- Never re-transcribe what is already in `01_WORKING/06_transcripts/`.
- If the machine is slow (doctor says "low"), close Chrome stream tabs while clipping.
- If transcription alone takes over 5 minutes, tell the person and offer `"captions": "none"` in `studio.config.local.json` for a fast no-caption pass.
