---
name: find-streamers
description: Find who is streaming the niche game right now on Kick, Twitch and YouTube, and update the watchlist. Use for "who's live", "who should we clip", "update the watchlist", "find streamers".
---

# Find streamers

The watchlist lives in `01_WORKING/08_notes/watchlist_<niche>_<event>.csv` with columns:
`id, tier, name, platform, status, language, viewers, snapshot, url, note`

Tiers: **A** English and live now (best for the fan page), **B** biggest non-English, **C** official event streams (for example YouTube's launch stream), **D** expected but not confirmed.

## Kick (fast and reliable)

1. `python tools/clipit.py live <slug> <slug> ...` checks known channels.
2. To discover new channels, open `https://kick.com/category/<game-slug>` in a browser tool and, from that page, read `/stream/livestreams/en?page=1&limit=24&subcategory=<game-slug>&sort=desc` (Kick's own page uses this list). Pages 1 and 2 cover the top 48.

## Twitch

Twitch's directory often won't render for automated browsers, and its stats sites block bots. Use a web search for current roundups ("<game> twitch top streamers live now") and mark those numbers as "news snapshot, rough". Don't call Twitch's private APIs.

## YouTube

Search for the official event lineup and for big creators' live pages. Mark creators as tier C or D unless you can see them live.

## Rules

- Record where every viewer number came from and when (the `snapshot` column).
- Never present "expected" creators as confirmed.
- Keep the CSV sorted by tier, then viewers.
- If the visual log page exists, update its "Who to clip" section with the `clip-log` skill.
- Log the refresh in `00_TRACKER/clip_log.csv` (kind `setup`).
