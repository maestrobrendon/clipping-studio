---
name: clip-log
description: Create or update the visual clip log, a dashboard page showing clips ready and posted, setup progress, activity by day and who to clip. Use for "log this", "update the log", "show me the dashboard", or after clips are rendered.
---

# The visual clip log

There are two logs:

- `00_TRACKER/clip_log.csv`: written automatically by `clipit.py` on every recording and render. Works everywhere, always up to date.
- The visual log page: a Claude Artifact (Data / Dashboard type) on the person's Claude account. Each account needs its own copy.

## Create the page (once per Claude account)

1. Use the Artifact tool's quickstart with intent "other". Create from the **Data** (dashboard) type, titled "Clip Log".
2. Follow that type's instructions. Write, in one batch:
   - `dash/meta`: `{title: "Clip Log"}`
   - `datasets/items`: store source at `data/log/items` (the log)
   - `datasets/watch`: store source at `data/watch/channels` (the watchlist)
   - `files/index.html`: the text of `dashboard/index.html` from this repo
3. Seed `data/log/items` from `00_TRACKER/clip_log.csv` and `data/watch/channels` from the watchlist CSV.
4. Save the page link as `dashboard_url` in `studio.config.local.json`, and write a shortcut file in `00_TRACKER/`.

## Row shapes

Log rows (`data/log/items/<YYYY-MM-DD-NNN>`):
`{when: "2026-11-18T19:44", kind: "clip"|"setup"|"tool"|"decision", title, status, platform}`

- Clip status: `editing`, `ready`, `posted`, `dropped`. Add `views` (number) once posted.
- Setup status: `todo`, `in-progress`, `done`.

Watchlist rows (`data/watch/channels/<wNNN>`):
`{tier: "A".."D", name, platform, status, language, viewers (number or null), snapshot, url, note}`

## Rules

- Add rows; don't rewrite history. Update a row's status with an `update`, pinned to its version.
- Titles are short. The person reads this page instead of chat, so it must stay visual and brief.
- When the person says a clip was posted, set `status: "posted"` and ask for its views later.
