---
name: setup-studio
description: First-run setup of the clipping studio on a new computer or a new Claude account. Use when studio.config.local.json is missing, when the person says "set this up", "first time", "new laptop", or when doctor reports problems.
---

# Set up the studio on this machine

## 0. Pick where the studio lives (ask first)

Recordings and renders take a lot of space, so the studio gets its own folder on the drive the person chooses. Before installing anything, list the drives with free space (`Get-PSDrive -PSProvider FileSystem` on Windows, `df -h` elsewhere) and ask: **"Which drive or folder should the Clipping Studio folder go in?"** Suggest the drive with the most free space; Enter/"here" keeps the current folder.

Pass the answer to the setup script. It creates `<their choice>\Clipping Studio`, clones their fork into it (or copies the files if there is no git remote), and runs the rest of setup there. If the folder moved, tell the person to open the new folder in Claude Code and continue from step 2 there.

## 1. Install (one command)

- Windows (PowerShell): `powershell -ExecutionPolicy Bypass -File setup/setup.ps1 -StudioDir "D:\"`
- macOS / Linux: `bash setup/setup.sh /Volumes/Media`

The script installs, in order:

| Package | How | Why |
|---|---|---|
| Python 3.10+ | winget | runs `clipit.py` |
| ffmpeg (full build) | winget / Homebrew / apt | records, renders, QC |
| **ArtCraft suite**: FilmCraft, EffectCraft, SoundCraft, PhotoCraft | winget (`ArtCraft.FilmCraft`, `ArtCraft.EffectCraft`, `ArtCraft.SoundCraft`, `ArtCraft.PhotoCraft`) | edit projects in `01_WORKING/03_edit_projects/<app>/`: video edits, hook/title motion graphics, audio clean-up, thumbnails |
| Python packages from `requirements.txt` | pip | captions (faster-whisper), streamlink, yt-dlp |
| caption model | download | local captions |

After installing the ArtCraft apps it connects each one to Claude Code (`claude mcp add --scope user <app> -- "C:\Program Files\ArtCraft\<App>\<app>-cli.exe" mcp`), skipping any already connected. On macOS/Linux it only prints how; install them from the ArtCraft Launcher. Use `-SkipArtCraft` if the person doesn't want them.

Tell the person before running it: it installs software (several apps plus about 200 MB of downloads). After the ArtCraft apps are connected, Claude Code needs a restart to see their tools.

If they'd rather do it by hand, the steps are in `README.md`.

## 2. Check

`python tools/clipit.py doctor` must end with `ALL GOOD`. It writes `studio.config.local.json` tuned to this machine (caption model, how many streams at once, encoder speed). Fix every `[!!]` line before clipping.

## 3. Ask the person (one message, numbered)

1. Which job is this machine for: the fan page, our own creator, or both?
2. Which platforms will they post to?
3. Do they want the visual log page (needs a Claude account with Artifacts)? If yes, use the `clip-log` skill to create it and save its link as `dashboard_url` in `studio.config.local.json`.
4. Is this a slow laptop that also runs Chrome while clipping? If yes, suggest `"captions": "none"` for the fast lane.

## 4. Test clip

Run the `clip-live` skill once with 1 or 2 live streams at `--secs 45` to prove the whole chain works on this machine. Report how long each step took.

## Never

- Don't commit `studio.config.local.json`, recordings or outputs. `.gitignore` already excludes them.
- Don't ask for or store passwords, stream keys or API keys.
