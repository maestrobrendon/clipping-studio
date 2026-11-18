# Clipping Studio

Turn live streams into credited 9:16 clips with hooks and captions, fast. Built for a GTA 6 fan page; works for any game or streamer.

Claude does the work. This repo gives it the tools, the rules and the context.

## Get started (10 minutes)

1. **Install Claude Code** (desktop app or CLI) and sign in with your own Claude account.
2. **Clone this repo** and open the folder in Claude Code.
3. **Run setup.** In Claude, say **"set up the studio"**, or run it yourself:
   - Windows: `powershell -ExecutionPolicy Bypass -File setup/setup.ps1`
   - macOS / Linux: `bash setup/setup.sh`
4. **Make clips.** Say **"clip who's live"** or **"go clip xQc and Kai Cenat"**.

Finished clips land in `02_OUTPUTS/01_clips_ready_to_post/`, with the caption text in `02_OUTPUTS/03_post_copy/`. You post them yourself.

## What you need

| Thing | Why | Installed by setup? |
|---|---|---|
| Python 3.10+ | runs the clip tool | Windows: yes (winget) |
| ffmpeg (full build) | records and renders | yes |
| faster-whisper | captions, runs on your own computer | yes |
| streamlink | Twitch streams | yes |
| yt-dlp | YouTube streams | yes |
| A Claude account | the assistant | no, sign in yourself |

No API keys, no paid services. Captions run locally.

## What to say to Claude

| You say | Claude does |
|---|---|
| "set up the studio" | installs, checks this computer, asks 4 questions |
| "who's live?" | checks Kick, Twitch and YouTube, updates the watchlist |
| "clip who's live" / "clip xQc" | records, finds the best moments, writes hooks, renders clips |
| "write captions for today's clips" | post text per platform, in a human voice |
| "update the log" / "make the dashboard" | visual log of clips and progress |

## Folders

```
00_TRACKER/    clip_log.csv + link to your visual log
01_WORKING/    recordings, transcripts, notes (in progress)
02_OUTPUTS/    finished clips and post text only
tools/         clipit.py
docs/          playbook.md (the rules) and decisions.md
.claude/       skills Claude follows
```

Media never goes into git. Each person's recordings and clips stay on their own computer.

## Slow computer?

`python tools/clipit.py doctor` rates your machine and picks settings for it. On an older 2-core laptop:
- close Chrome stream tabs while clipping
- record 2 streams at a time
- for the fastest possible pass, set `"captions": "none"` in `studio.config.local.json`

## Rules everyone follows

Credit every creator on screen and in the caption. No story spoilers in hooks. No AI voices or AI footage. Take down anything the same day if asked. The full list is in `docs/playbook.md`.
