#!/usr/bin/env bash
# Clipping Studio setup for macOS and Linux.
# Run from the repo folder:  bash setup/setup.sh [/path/where/the/studio/goes]
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
MOVED=0

have() { command -v "$1" >/dev/null 2>&1; }
PY=python3; have python3 || PY=python

echo "0/6 Studio folder"
STUDIO_DIR="${1:-}"
if [ -z "$STUDIO_DIR" ] && [ -t 0 ]; then
  df -h 2>/dev/null | awk 'NR==1 || /^\/dev\//' || true
  read -r -p "  Where should the 'Clipping Studio' folder go? (Enter = keep it here: $ROOT) " STUDIO_DIR
fi
if [ -n "$STUDIO_DIR" ]; then
  TARGET="${STUDIO_DIR%/}/Clipping Studio"
  if [ "$TARGET" != "$ROOT" ]; then
    if [ -f "$TARGET/tools/clipit.py" ]; then echo "  Studio already exists at $TARGET, using it."
    else
      mkdir -p "$STUDIO_DIR"
      ORIGIN="$(git -C "$ROOT" remote get-url origin 2>/dev/null || true)"
      if [ -n "$ORIGIN" ]; then git clone "$ORIGIN" "$TARGET"
      else rsync -a --exclude .git --exclude '01_WORKING/01_capture_stream_segments/*' --exclude '01_WORKING/06_transcripts/*' "$ROOT/" "$TARGET/"; fi
    fi
    ROOT="$TARGET"; cd "$ROOT"; MOVED=1
  fi
fi

echo "1/6 Python"
have "$PY" || { echo "Install Python 3.10+ first (https://www.python.org/downloads/)"; exit 1; }

echo "2/6 ffmpeg"
if ! have ffmpeg; then
  if have brew; then brew install ffmpeg
  elif have apt-get; then sudo apt-get update && sudo apt-get install -y ffmpeg fonts-dejavu
  elif have dnf; then sudo dnf install -y ffmpeg
  else echo "Install ffmpeg (with libass) for your system, then run this again."; exit 1; fi
fi

echo "3/6 ArtCraft suite (FilmCraft, EffectCraft, SoundCraft, PhotoCraft)"
echo "  The ArtCraft apps are installed with winget on Windows. On this system install them"
echo "  from the ArtCraft Launcher, then connect each to Claude, e.g.:"
echo "    claude mcp add --scope user filmcraft -- <path to filmcraft-cli> mcp"

echo "4/6 Python packages"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements.txt

echo "5/6 Machine check (writes studio.config.local.json)"
"$PY" tools/clipit.py doctor || true

echo "6/6 Caption model download (one time, ~150 MB)"
MODEL=$("$PY" -c "import json;print(json.load(open('studio.config.local.json'))['whisper_model'])")
"$PY" -c "from faster_whisper import WhisperModel; WhisperModel('$MODEL', device='cpu', compute_type='int8'); print('model ready: $MODEL')"

echo
echo "Your studio folder: $ROOT"
if [ "$MOVED" = 1 ]; then echo "Open THAT folder in Claude Code and say: set up the studio"
else echo "Done. Open this folder in Claude Code and say: set up the studio"; fi
