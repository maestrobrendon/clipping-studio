# Clipping Studio setup for Windows.
# Run from the repo folder:  powershell -ExecutionPolicy Bypass -File setup/setup.ps1
# Optional: -StudioDir "D:\"   (where the dedicated "Clipping Studio" folder goes; asked if left out)
#           -SkipArtCraft      (don't install the ArtCraft apps)
param(
    [string]$StudioDir = "",
    [switch]$SkipArtCraft
)
$ErrorActionPreference = "Stop"
$moved = $false
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Have($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

# ---------------------------------------------------------------------------
# 0. Dedicated studio folder on the drive the person chooses
# ---------------------------------------------------------------------------
Write-Host "0/7 Studio folder"
if (-not $StudioDir) {
    $drives = (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Free } |
        ForEach-Object { "{0}:\ ({1:N0} GB free)" -f $_.Name, ($_.Free / 1GB) }) -join ", "
    Write-Host "  Drives: $drives"
    Write-Host "  Recordings take a lot of space. Pick a drive or folder for the studio."
    $StudioDir = Read-Host "  Where should the 'Clipping Studio' folder go? (Enter = keep it here: $root)"
}
if ($StudioDir) {
    $target = Join-Path $StudioDir "Clipping Studio"
    $here = (Resolve-Path $root).Path.TrimEnd('\')
    if ($target.TrimEnd('\') -ne $here) {
        if (Test-Path (Join-Path $target "tools\clipit.py")) {
            Write-Host "  Studio already exists at $target, using it."
        } else {
            New-Item -ItemType Directory -Force $StudioDir | Out-Null
            $origin = ""
            if (Have git) { $origin = (git -C $root remote get-url origin 2>$null) }
            if ($origin) {
                Write-Host "  Cloning your repo into $target"
                git clone $origin $target
            } else {
                Write-Host "  Copying the studio into $target"
                robocopy $root $target /E /XD .git 01_capture_stream_segments 06_transcripts 09_qc_failed __pycache__ /NFL /NDL /NJH /NJS | Out-Null
            }
        }
        $root = $target
        Set-Location $root
        $moved = $true
    }
}

# ---------------------------------------------------------------------------
Write-Host "1/7 Python"
if (-not (Have python)) {
    if (-not (Have winget)) { throw "Install Python 3.10+ from python.org, then run this again." }
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    Write-Host "Python installed. Close this window, open a new one, and run setup again." ; exit 0
}

Write-Host "2/7 ffmpeg (full build, includes captions support)"
if (-not (Have ffmpeg)) {
    if (-not (Have winget)) { throw "Install ffmpeg from https://www.gyan.dev/ffmpeg/builds/ (full build) and add it to PATH." }
    winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
    Write-Host "ffmpeg installed. Close this window, open a new one, and run setup again." ; exit 0
}

# ---------------------------------------------------------------------------
# ArtCraft suite: the editing apps Claude drives through MCP
#   FilmCraft   video edit projects      EffectCraft  hook / title motion graphics
#   SoundCraft  audio clean-up, mixes    PhotoCraft   thumbnails and cover frames
# ---------------------------------------------------------------------------
$artcraft = @(
    @{ name = "filmcraft";   id = "ArtCraft.FilmCraft";   dir = "FilmCraft" },
    @{ name = "effectcraft"; id = "ArtCraft.EffectCraft"; dir = "EffectCraft" },
    @{ name = "soundcraft";  id = "ArtCraft.SoundCraft";  dir = "SoundCraft" },
    @{ name = "photocraft";  id = "ArtCraft.PhotoCraft";  dir = "PhotoCraft" }
)
Write-Host "3/7 ArtCraft suite (FilmCraft, EffectCraft, SoundCraft, PhotoCraft)"
if ($SkipArtCraft) {
    Write-Host "  skipped (-SkipArtCraft)"
} elseif (-not (Have winget)) {
    Write-Host "  [!!] winget not found. Install the ArtCraft apps from the ArtCraft Launcher, then run setup again."
} else {
    foreach ($app in $artcraft) {
        $installed = winget list -e --id $app.id 2>$null | Select-String $app.id
        if ($installed) { Write-Host "  $($app.dir): installed" ; continue }
        Write-Host "  installing $($app.dir)"
        winget install -e --id $app.id --accept-package-agreements --accept-source-agreements
    }
    # Register each app with Claude Code so the assistant can use it (skipped if already there)
    if (Have claude) {
        foreach ($app in $artcraft) {
            $exe = Join-Path $env:ProgramFiles "ArtCraft\$($app.dir)\$($app.name)-cli.exe"
            if (-not (Test-Path $exe)) { Write-Host "  [!!] $($app.dir) CLI not found at $exe (open a new window if it was just installed)"; continue }
            claude mcp get $app.name *> $null
            if ($LASTEXITCODE -eq 0) { Write-Host "  $($app.name): already connected to Claude" ; continue }
            claude mcp add --scope user $app.name -- $exe mcp
            Write-Host "  $($app.name): connected to Claude"
        }
    } else {
        Write-Host "  Claude Code CLI not on PATH; the ArtCraft apps are installed but not yet connected to Claude."
    }
}

# ---------------------------------------------------------------------------
Write-Host "4/7 Python packages"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "5/7 Machine check (writes studio.config.local.json)"
python tools/clipit.py doctor

Write-Host "6/7 Caption model download (one time, ~150 MB)"
$model = (Get-Content studio.config.local.json | ConvertFrom-Json).whisper_model
python -c "from faster_whisper import WhisperModel; WhisperModel('$model', device='cpu', compute_type='int8'); print('model ready: $model')"

Write-Host "7/7 Done"
Write-Host ""
Write-Host "Your studio folder: $root"
if ($moved) {
    Write-Host "Open THAT folder in Claude Code (not the one you ran setup from) and say: set up the studio"
} else {
    Write-Host "Open this folder in Claude Code and say: set up the studio"
}
