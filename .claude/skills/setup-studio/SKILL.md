---
name: setup-studio
description: First-run setup of the clipping studio on a new computer or a new Claude account. Use when studio.config.local.json is missing, when the person says "set this up", "first time", "new laptop", or when doctor reports problems.
---

# Set up the studio on this machine

## 1. Install (one command)

- Windows (PowerShell): `powershell -ExecutionPolicy Bypass -File setup/setup.ps1`
- macOS / Linux: `bash setup/setup.sh`

The script installs ffmpeg (winget or Homebrew or apt), Python packages from `requirements.txt`, downloads the caption model, and runs the doctor. Tell the person before running it: it installs software and downloads about 200 MB.

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
