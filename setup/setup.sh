#!/usr/bin/env bash
# Clipping Studio setup for macOS and Linux.
# Run from the repo folder:  bash setup/setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."

have() { command -v "$1" >/dev/null 2>&1; }
PY=python3; have python3 || PY=python

echo "1/5 Python"
have "$PY" || { echo "Install Python 3.10+ first (https://www.python.org/downloads/)"; exit 1; }

echo "2/5 ffmpeg"
if ! have ffmpeg; then
  if have brew; then brew install ffmpeg
  elif have apt-get; then sudo apt-get update && sudo apt-get install -y ffmpeg fonts-dejavu
  elif have dnf; then sudo dnf install -y ffmpeg
  else echo "Install ffmpeg (with libass) for your system, then run this again."; exit 1; fi
fi

echo "3/5 Python packages"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements.txt

echo "4/5 Machine check (writes studio.config.local.json)"
"$PY" tools/clipit.py doctor || true

echo "5/5 Caption model download (one time, ~150 MB)"
MODEL=$("$PY" -c "import json;print(json.load(open('studio.config.local.json'))['whisper_model'])")
"$PY" -c "from faster_whisper import WhisperModel; WhisperModel('$MODEL', device='cpu', compute_type='int8'); print('model ready: $MODEL')"

echo
echo "Done. Open this folder in Claude Code and say: set up the studio"
