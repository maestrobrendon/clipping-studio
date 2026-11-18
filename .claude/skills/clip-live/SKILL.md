---
name: clip-live
description: Record live streams and turn the best moments into finished 9:16 clips with hook, captions and credit. Use for "clip", "make clips", "go clip xQc", "get clips from who's live", or any request to produce clips from streams.
---

# Clip live streams

Goal: as many good, credited clips as possible, as fast as possible, with no clip that breaks the playbook.

## 1. Pick sources (1 min)

- If the person named streamers, use them.
- Otherwise run `python tools/clipit.py live <slugs from 01_WORKING/08_notes/watchlist_*.csv tier A>` and take the live ones with the most viewers.
- Prefer English-speaking, high-reaction streamers for the fan page. Non-English streams only for moments that work without words.
- Batch size = `max_parallel_grabs` in `studio.config.local.json`.

## 2. Record and score (runs in the background)

```
python tools/clipit.py grab kick:xqc kick:n3on twitch:kaicenat --secs 60
```

Run it in the background. While it runs, write hook ideas from the stream titles. For each recording it prints up to 3 windows: score, start-end seconds, transcript, and 3 frame paths.

## 3. Choose (this is the judgment step)

For each window, read its 3 frames (they are .jpg files you can view) and the transcript. Keep a window only if:

- something happens: a reaction, chaos, a fail, a funny line, a useful tip
- it is not an ad, a loading screen, a menu or a long story cutscene
- nothing in it spoils the story, has nudity or could get the account struck

Adjust start and end if needed: start just before the peak, end right after the payoff, 7 to 30 seconds total. Drop weak windows. Two good clips beat five weak ones.

## 4. Write the hook

Use the `hooks-and-copy` skill. One hook per clip, 8 words max, true to the clip, no spoilers.

## 5. Render (parallel, up to the machine's limit)

```
python tools/clipit.py render <rec_id> --start 12.5 --end 31 --hook "He needed guns. Then he saw the old man" --tag t1
```

Run several renders at once (the `&` + `wait` pattern in bash, or `Start-Job` in PowerShell), up to `max_parallel_grabs`. Each render writes:

- the clip to `02_OUTPUTS/01_clips_ready_to_post/<date>/`
- the post text to `02_OUTPUTS/03_post_copy/<date>/` (hook, credit, hashtags)
- a row in `00_TRACKER/clip_log.csv`

## 6. Check one frame per clip

Grab one frame from each finished clip (`ffmpeg -ss 5 -i clip.mp4 -frames:v 1 -vf scale=540:-2 check.jpg` into your scratch folder, not into `02_OUTPUTS`) and look at it: hook readable, captions not covering the facecam, credit visible.

## 7. Report and log

- Tell the person in a short table: file, creator, hook, verdict ("strong", "ok", "test only").
- Send the best 1 or 2 clips with SendUserFile if that tool exists.
- If a visual log page exists (`dashboard_url` in config), add the clips with the `clip-log` skill.

## Speed rules

- Never re-transcribe what is already in `01_WORKING/06_transcripts/`.
- The caption model loads once per command, so analyze several recordings in one `grab` or `scan` call.
- If the machine is slow (doctor says "low"), close Chrome stream tabs, use `--secs 45`, and render at most 2 at once.
- If transcription alone takes over 3 minutes, tell the person and offer `"captions": "none"` in `studio.config.local.json` for a fast no-caption pass.
