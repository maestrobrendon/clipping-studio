# Clipping Studio setup for Windows.
# Run from the repo folder:  powershell -ExecutionPolicy Bypass -File setup/setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Have($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

Write-Host "1/5 Python"
if (-not (Have python)) {
    if (-not (Have winget)) { throw "Install Python 3.10+ from python.org, then run this again." }
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    Write-Host "Python installed. Close this window, open a new one, and run setup again." ; exit 0
}

Write-Host "2/5 ffmpeg (full build, includes captions support)"
if (-not (Have ffmpeg)) {
    if (-not (Have winget)) { throw "Install ffmpeg from https://www.gyan.dev/ffmpeg/builds/ (full build) and add it to PATH." }
    winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
    Write-Host "ffmpeg installed. Close this window, open a new one, and run setup again." ; exit 0
}

Write-Host "3/5 Python packages"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "4/5 Machine check (writes studio.config.local.json)"
python tools/clipit.py doctor

Write-Host "5/5 Caption model download (one time, ~150 MB)"
$model = (Get-Content studio.config.local.json | ConvertFrom-Json).whisper_model
python -c "from faster_whisper import WhisperModel; WhisperModel('$model', device='cpu', compute_type='int8'); print('model ready: $model')"

Write-Host ""
Write-Host "Done. Open this folder in Claude Code and say: set up the studio"
