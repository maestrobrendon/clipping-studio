"""Clipping Studio - fast live clipper. Runs on Windows, macOS and Linux.

  python tools/clipit.py doctor                         check this machine, write its profile
  python tools/clipit.py live   kick xqc n3on ...       who is live right now (Kick)
  python tools/clipit.py grab   kick:xqc twitch:kaicenat --secs 200
                                                        record live streams in parallel, find the best
                                                        moments, save transcript + frames for review
  python tools/clipit.py scan   <recording.ts> ...      find moments in recordings you already have
  python tools/clipit.py render <rec_id> --start S --end E --hook "TEXT" [--tag t1]
                                                        make one 9:16 captioned clip + post copy, then QC it
  python tools/clipit.py batch  plan.json               render many clips at once (the normal way), QC each,
                                                        print one table. plan = [{"rid","start","end","hook","tag"}]
  python tools/clipit.py compile plan.json              join several moments into one ranked video: a Top 5 Short
                                                        (layout "short", 9:16) or a weekly Top 15 (layout "long", 16:9).
                                                        Rank number in the corner, a label per moment, each creator
                                                        credited, YouTube chapters in the post copy. Items in play
                                                        order: the first is #N, the last is #1.

Every clip is quality-checked (picture and sound both start at 0 and run the full length, no black
opening, no dead audio). Failures go to 01_WORKING/09_qc_failed/, never to the outputs folder.

Sources: kick:<slug> (default if no prefix), twitch:<login>, yt:<@handle or url>. Recording uses streamlink.

Where files go (never mix working files and outputs):
  recordings  01_WORKING/01_capture_stream_segments/<date>/
  transcripts 01_WORKING/06_transcripts/<date>/   (also the review frames and .ass caption files)
  clips       02_OUTPUTS/01_clips_ready_to_post/<channel>/  (clip.mp4 + clip.txt caption side by side)
  clip notes  01_WORKING/06_transcripts/clip_details/  (source, QC, transcript)
  log         00_TRACKER/clip_log.csv
"""
import argparse, csv, json, os, platform, re, shutil, subprocess, sys, threading, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
TODAY = datetime.now().strftime("%Y-%m-%d")
CAP = ROOT / "01_WORKING" / "01_capture_stream_segments" / TODAY
TRN = ROOT / "01_WORKING" / "06_transcripts" / TODAY
OUT = ROOT / "02_OUTPUTS" / "01_clips_ready_to_post"       # <channel>/<clip>.mp4 + <clip>.txt caption, no date folders
DETAILS = ROOT / "01_WORKING" / "06_transcripts" / "clip_details"   # source, window, QC and transcript per clip
CHANNELS = ("main", "channel_2", "channel_3")
QCF = ROOT / "01_WORKING" / "09_qc_failed" / TODAY
LOG = ROOT / "00_TRACKER" / "clip_log.csv"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}
LOCK = threading.Lock()                                   # one transcription / meta write at a time
HYPE = re.compile(r"\b(bro+|yo+|what+|no+ way|oh my god|omg|wtf|let'?s go+|chat|hell no|holy|insane|crazy|dude|wait|look)\b", re.I)


# ---------- config ----------
def load_config():
    cfg = json.loads((ROOT / "studio.config.json").read_text(encoding="utf-8"))
    local = ROOT / "studio.config.local.json"           # per-machine overrides, written by `doctor`, not in git
    if local.exists():
        cfg.update(json.loads(local.read_text(encoding="utf-8")))
    return cfg

CFG = load_config()
THREADS = int(CFG.get("threads") or max(1, (os.cpu_count() or 2)))
os.environ.setdefault("OMP_NUM_THREADS", str(THREADS))


def need_dirs():
    for d in (CAP, TRN, OUT, DETAILS, LOG.parent):
        d.mkdir(parents=True, exist_ok=True)


def channel_of(ch):
    """Which channel folder a clip goes to. Plans say "channel" (old plans used "date")."""
    ch = (ch or "").replace("\\", "/").strip("/").split("/")[0]    # channel folders are flat: never a date below
    return ch if ch in CHANNELS else "unsorted"


def write_caption(folder, name, title, body, details, spoiler=False):
    """Caption .txt beside the clip, laid out so anyone can open it and copy-paste. Tech notes go to DETAILS."""
    bar = "-" * 50
    lines = [f"CLIP: {name}.mp4", "=" * 50, ""]
    if spoiler:
        lines += ["!! SPOILER: story scene. Keep the word SPOILER at the top of the caption.",
                  "!! No story details in the title or the cover.", ""]
    lines += ["TITLE", title, "", "CAPTION  (copy everything between the lines)", bar]
    lines += (["SPOILER (story scene)", ""] if spoiler else []) + list(body) + [bar, ""]
    (Path(folder) / f"{name}.txt").write_text("\r\n".join(lines), encoding="utf-8-sig")   # opens cleanly in Notepad
    DETAILS.mkdir(parents=True, exist_ok=True)
    (DETAILS / f"{name}.txt").write_text(details.rstrip() + "\n", encoding="utf-8")


def log_row(**row):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    cols = ["when", "kind", "status", "creator", "platform", "title", "file", "note"]
    new = not LOG.exists()
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow({"when": datetime.now().strftime("%Y-%m-%dT%H:%M"), **row})


def run(cmd, **kw):
    return subprocess.run(cmd, **kw)


# ---------- sources ----------
def parse_source(s):
    if ":" in s and not s.startswith("http"):
        p, h = s.split(":", 1)
    elif "twitch.tv/" in s:
        p, h = "twitch", s.rstrip("/").split("/")[-1]
    elif "youtube.com" in s or "youtu.be" in s:
        p, h = "yt", s
    elif "kick.com/" in s:
        p, h = "kick", s.rstrip("/").split("/")[-1]
    else:
        p, h = "kick", s
    return {"kick": "kick", "twitch": "twitch", "yt": "youtube", "youtube": "youtube"}.get(p.lower(), p.lower()), h


def kick_live(slug):
    req = urllib.request.Request(f"https://kick.com/api/v2/channels/{slug}", headers=UA)
    j = json.load(urllib.request.urlopen(req, timeout=20))
    ls = j.get("livestream")
    if not ls or not ls.get("is_live") or not j.get("playback_url"):
        return None
    return {"platform": "kick", "slug": slug, "url": pick_variant(j["playback_url"]),
            "title": ls.get("session_title", ""), "viewers": ls.get("viewer_count"),
            "name": (j.get("user") or {}).get("username", slug), "page": f"https://kick.com/{slug}"}


QUALITY = "720p60,720p,720p30,480p,best"


def streamlink_live(page):
    """True if streamlink sees a live stream at this page (Twitch, YouTube)."""
    r = run(["streamlink", "--json", page], capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=90)                                  # stream titles are full of emoji
    try:
        return bool(json.loads(r.stdout or "{}").get("streams"))
    except Exception:
        return False


def twitch_live(login):
    page = f"https://www.twitch.tv/{login}"
    if not streamlink_live(page):
        return None
    return {"platform": "twitch", "slug": login, "url": page, "quality": QUALITY, "title": "", "viewers": None,
            "name": login, "page": page}


def youtube_live(handle):
    page = handle if handle.startswith("http") else f"https://www.youtube.com/{handle}/live"
    if not streamlink_live(page):
        return None
    slug = re.sub(r"[^A-Za-z0-9_-]", "", handle.split("/")[-2] if handle.startswith("http") else handle)
    return {"platform": "youtube", "slug": slug or "youtube", "url": page, "quality": QUALITY, "title": "",
            "viewers": None, "name": handle, "page": page}


def resolve(src):
    p, h = parse_source(src)
    return {"kick": kick_live, "twitch": twitch_live, "youtube": youtube_live}[p](h)


def pick_variant(master_url):
    """One quality level only (<= max_height, lowest fps) so several streams fit the connection."""
    max_h = int(CFG.get("record_max_height", 720))
    txt = urllib.request.urlopen(urllib.request.Request(master_url, headers=UA), timeout=20).read().decode()
    lines, best = txt.splitlines(), None
    for i, l in enumerate(lines):
        if l.startswith("#EXT-X-STREAM-INF") and i + 1 < len(lines):
            h = int(re.search(r"RESOLUTION=\d+x(\d+)", l).group(1)) if "RESOLUTION=" in l else 0
            fps = float(re.search(r"FRAME-RATE=([\d.]+)", l).group(1)) if "FRAME-RATE=" in l else 30
            if h <= max_h and (best is None or (h, -fps) > best[0]):
                best = ((h, -fps), urllib.parse.urljoin(master_url, lines[i + 1].strip()))
    return best[1] if best else master_url


def record(info, secs):
    """Record with streamlink: it downloads stream pieces in parallel and retries, so nothing goes missing.
    (ffmpeg's own HLS reader fell behind and lost 30-40% of every recording: black frames, dead audio.)"""
    if not shutil.which("streamlink"):
        raise RuntimeError("recording needs streamlink: pip install -r requirements.txt")
    rid = f"{info['slug']}_{datetime.now().strftime('%H%M%S')}"
    path = CAP / f"{rid}.ts"
    url = info["url"] if info.get("quality") else "hls://" + info["url"]
    cmd = ["streamlink", "--stream-segment-threads", "3", "--hls-live-edge", "6", "--stream-timeout", "30",
           "--stream-segmented-duration", str(secs), "--loglevel", "error", "-f", "-o", str(path),
           url, info.get("quality", "best")]
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        p.wait(timeout=secs + 90)
    except subprocess.TimeoutExpired:            # hard stop: keep whatever arrived
        p.kill()
    if not path.exists() or path.stat().st_size < 100_000:
        print(f"[fail] {rid}: {(p.stderr.read() or b'').decode(errors='replace')[-300:]}")
        return None
    meta = dict(info, rid=rid, file=str(path), recorded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    meta.pop("url", None)                         # playback URLs carry short-lived tokens; don't keep them
    meta["holes"] = holes(str(path))
    if meta["holes"]:
        print(f"[warn] {rid}: {len(meta['holes'])} gap(s) in the recording, clips will avoid them: {meta['holes']}")
    (TRN / f"{rid}.meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


def holes(path, min_gap=0.5):
    """Missing stretches in a recording, in seconds from its start. Clips must never cross one."""
    def times(sel):
        out = run(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries", "packet=pts_time",
                   "-of", "csv=p=0", path], capture_output=True, text=True).stdout.split()
        return [float(x.strip(",")) for x in out if x.strip(",") not in ("", "N/A")]
    found = []
    vt, at = times("v:0"), times("a:0")
    t0 = min([x[0] for x in (vt, at) if x] or [0])
    for ts in (sorted(vt), sorted(at)):
        found += [(round(a - t0, 2), round(b - t0, 2)) for a, b in zip(ts, ts[1:]) if b - a > min_gap]
    if not vt or not at:
        found.append((0.0, 1e9))                 # no video or no audio at all: nothing here is usable
    return sorted(set(found))


# ---------- analysis ----------
def pcm(path, start=0.0, dur=None):
    import numpy as np
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(start), "-i", path]
    if dur:
        cmd += ["-t", str(dur)]
    raw = run(cmd + ["-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def loudness(path, hop=0.25):
    import numpy as np
    a = pcm(path)
    n = int(16000 * hop)
    a = a[: len(a) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((a ** 2).mean(1)) + 1e-6), hop


_model = None
def get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        name = CFG.get("whisper_model", "base.en")
        try:                                       # use the local copy first; never stall on the network
            os.environ["HF_HUB_OFFLINE"] = "1"
            _model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=THREADS)
        except Exception:
            os.environ["HF_HUB_OFFLINE"] = "0"
            _model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=THREADS)
    return _model


def transcribe(path, start=0.0, dur=None):
    """Words with times in recording time. Returns [] when captions are switched off."""
    if CFG.get("captions", "local") == "none":
        return []
    segs, _ = get_model().transcribe(pcm(path, start, dur), word_timestamps=True, vad_filter=True, beam_size=1)
    return [{"w": w.word.strip(), "s": round(w.start + start, 2), "e": round(w.end + start, 2)}
            for s in segs for w in (s.words or [])]


def clip_length():
    lo, hi = CFG.get("clip_length_seconds", [22, 45])
    return int(lo), int(hi)


def snap(s, e, words, dur):
    """Start a beat before the first word, end after the last word finishes: no clipped speech."""
    for w in words:
        if w["s"] < s < w["e"]:
            s = w["s"]
        if w["s"] < e < w["e"] + 0.4:
            e = w["e"] + 0.4
    return max(0.0, round(s - 0.4, 2)), min(dur, round(e + 0.6, 2))


def best_windows(db, hop, words, length=None, k=None, bad=()):
    import numpy as np
    length = length or clip_length()
    dur = len(db) * hop
    k = k or max(2, min(5, int(dur // 50)))
    med = float(np.median(db))
    score = np.clip(db - (med + 8), 0, None)                       # shouting, laughing, explosions
    for w in words:
        i = min(len(db) - 1, int(w["s"] / hop))
        score[i] += 0.3 + (4 if HYPE.search(w["w"]) else 0)          # talking, and hype words
    t = np.arange(len(db)) * hop
    cands = []
    for L in range(length[0], length[1] + 1, 4):
        n = int(L / hop)
        if n >= len(score):
            continue
        c = np.convolve(score, np.ones(n), "valid") / L ** 0.35     # dense moments win, but longer is fine
        for i in range(0, len(c), max(1, int(1 / hop))):             # every start second, so moments spread out
            cands.append((float(c[i]), t[i], t[i] + L))
    if not cands and dur >= 8:                                        # short recording: offer the whole thing
        cands = [(0.0, 0.0, dur - 1)]
    cands.sort(reverse=True)
    picked = []
    for sc, s, e in cands:
        s, e = snap(s, e, words, dur)
        if any(s < he + 0.5 and e > hs - 0.5 for hs, he in bad):      # never cross a hole in the recording
            continue
        if all(e <= ps or s >= pe for _, ps, pe in picked):
            picked.append((round(sc, 1), s, e))
        if len(picked) == k:
            break
    return picked


_dur = {}
def last_t(path):
    if path not in _dur:
        _dur[path] = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                               capture_output=True, text=True).stdout.strip() or 1e9)
    return _dur[path]


def frames(path, tag, times):
    outs = []
    times = [min(tt, max(0, last_t(path) - 2)) for tt in times]   # the last second of a recording can be cut mid-frame
    for i, tt in enumerate(times):
        p = TRN / f"{tag}_f{i}.jpg"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(max(0, tt)), "-i", path,
             "-frames:v", "1", "-vf", "scale=640:-2:out_range=full,format=yuvj420p", "-q:v", "3", str(p)])
        outs.append(str(p))
    return outs


def analyse(meta):
    if "holes" not in meta:
        meta["holes"] = holes(meta["file"])
    bad = meta["holes"]
    db, hop = loudness(meta["file"])
    k = max(2, min(5, int(len(db) * hop // 50)))
    words, done = [], []
    for _, s, e in best_windows(db, hop, [], k=k + 1, bad=bad):   # pass 1: loudness finds hot spots
        s, e = max(0, s - 1), e + 1
        if any(s < de and e > ds for ds, de in done):
            continue
        done.append((s, e))
        words += transcribe(meta["file"], s, e - s)     # pass 2: transcribe only the hot spots
    words.sort(key=lambda w: w["s"])
    meta["words"], meta["windows"], meta["transcribed"] = words, [], done
    for sc, s, e in best_windows(db, hop, words, k=k, bad=bad):
        text = " ".join(w["w"] for w in words if s <= w["s"] <= e)
        meta["windows"].append({"score": sc, "start": s, "end": e, "text": text,
                                "frames": frames(meta["file"], f"{meta['rid']}_{int(s)}", [s + 1, (s + e) / 2, e - 1])})
    (TRN / f"{meta['rid']}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


def contact_sheet(meta):
    """One image per recording: a row of 3 frames for each candidate window, labelled with its time.
    Review this instead of opening every frame."""
    if not meta.get("windows"):
        return None
    inputs, fc, rows, k = [], [], [], 0
    for r, w in enumerate(meta["windows"]):
        for f in w["frames"][:3]:
            inputs += ["-i", f] if Path(f).exists() else ["-f", "lavfi", "-i", "color=gray:s=640x360"]
            fc.append(f"[{k}:v]scale=400:225,setsar=1,format=yuv420p[c{k}]")
            k += 1
        fc.append(f"[c{k-3}][c{k-2}][c{k-1}]hstack=3,drawbox=x=0:y=0:w=170:h=34:color=black@0.8:t=fill,"
                  f"drawtext=text='{int(w['start'])}-{int(w['end'])}s':x=6:y=6:fontsize=24:fontcolor=yellow[r{r}]")
        rows.append(f"[r{r}]")
    fc.append(f"{''.join(rows)}vstack={len(rows)}[out]" if len(rows) > 1 else f"{rows[0]}null[out]")
    out = TRN / f"{meta['rid']}_sheet.jpg"
    run(["ffmpeg", "-v", "quiet", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[out]",
         "-frames:v", "1", "-q:v", "4", str(out)], stderr=subprocess.DEVNULL)
    return str(out) if out.exists() else None


def report(recs):
    for m in recs:
        t0 = time.time()
        m = analyse(m)
        sheet = contact_sheet(m)
        print(f"\n=== {m['rid']}  [{m.get('platform', 'kick')}]  viewers={m.get('viewers')}  ({round(time.time() - t0)}s)  {m.get('title', '')[:60]}")
        print(f"  review sheet: {sheet}")
        for w in m["windows"]:
            print(f"  score {w['score']:>6}  {w['start']:6.1f}-{w['end']:6.1f}s  | {w['text'][:220]}")


# ---------- render ----------
def ass_time(x):
    x = max(0, x)
    return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"


def ass_escape(s):
    return s.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def fonts():
    f = CFG.get("fonts", {})
    sysname = platform.system()
    default = {"Windows": ("Impact", "Segoe UI"), "Darwin": ("Impact", "Helvetica Neue")}.get(sysname, ("DejaVu Sans", "DejaVu Sans"))
    return f.get("display") or default[0], f.get("small") or default[1]


def build_ass(words, start, end, hook, credit, path):
    big, small = fonts()
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,{big},84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,3,18,0,8,70,70,250,1
Style: Cap,{big},92,&H00FFFFFF,&H0000E5FF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,7,2,2,60,60,560,1
Style: Credit,{small},34,&H00E6E6E6,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,3,0,2,60,60,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dur = end - start
    ev = [f"Dialogue: 1,{ass_time(0)},{ass_time(dur)},Hook,,0,0,0,,{ass_escape(hook.upper())}",
          f"Dialogue: 1,{ass_time(0)},{ass_time(dur)},Credit,,0,0,0,,{ass_escape(credit)}"]
    Path(path).write_text(hdr + "\n".join(ev + caption_events(words, start, end)) + "\n", encoding="utf-8")


def caption_events(words, start, end):
    """3-word captions, timed to the words, relative to `start`."""
    ev = []
    ws = [w for w in words if start <= w["s"] < end and w["w"]]
    for i in range(0, len(ws), 3):
        grp = ws[i:i + 3]
        s = grp[0]["s"] - start
        e = (ws[i + 3]["s"] - start) if i + 3 < len(ws) else grp[-1]["e"] - start + 0.3
        e = min(e, grp[-1]["e"] - start + 0.6, end - start)
        txt = " ".join(re.sub(r"[^\w'!?.,-]", "", g["w"]) for g in grp).upper()
        if txt.strip() and e > s:
            ev.append(f"Dialogue: 0,{ass_time(s)},{ass_time(max(e, s + 0.25))},Cap,,0,0,0,,"
                      f"{{\\fscx108\\fscy108\\t(0,90,\\fscx100\\fscy100)}}{ass_escape(txt)}")
    return ev


def covered(spans, s, e):
    return any(a <= s + 0.5 and b >= e - 0.5 for a, b in spans)


def prepare(rid, start, end, force=False, exact=False):
    """Load a recording's analysis, make sure every second of start-end has captions, snap to word edges.
    Returns (meta, start, end)."""
    mpath = TRN / f"{rid}.json"
    if not mpath.exists():                       # recorded before midnight: look in earlier days
        found = sorted(TRN.parent.glob(f"*/{rid}.json"))
        if not found:
            raise SystemExit(f"no analysis found for {rid}; run grab or scan first")
        mpath = found[-1]
    meta = json.loads(mpath.read_text(encoding="utf-8"))
    if "holes" not in meta:
        meta["holes"] = holes(meta["file"])
    cross = [h for h in meta["holes"] if start < h[1] and end > h[0]]
    if cross and not force:
        raise SystemExit(f"{rid} {start}-{end}s crosses a gap in the recording {cross}. Pick another window.")
    if CFG.get("captions", "local") != "none" and not covered(meta.get("transcribed", []), start, end):
        with LOCK:                                                   # captions for every second of the clip
            meta = json.loads(mpath.read_text(encoding="utf-8"))
            meta.setdefault("holes", [])
            if not covered(meta.get("transcribed", []), start, end):
                new = transcribe(meta["file"], start, end - start)
                meta["words"] = sorted([w for w in meta["words"] if not start <= w["s"] < end] + new, key=lambda w: w["s"])
                meta.setdefault("transcribed", []).append((start, end))
                mpath.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    fdur = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", meta["file"]],
                     capture_output=True, text=True).stdout.strip() or end)
    if not exact:                                                    # exact: times already final (re-render)
        start, end = snap(start, end, meta["words"], fdur)           # never cut someone off mid-word
    return meta, start, end


def credit_line(meta):
    page = meta.get("page") or f"https://kick.com/{meta['slug']}"
    return page, f"Clip: {page.replace('https://', '').replace('www.', '')}"


def render(rid, start, end, hook, tag=None, force=False, day=None, spoiler=False, exact=False, title=None):
    """Render one clip, then QC it. A clip that fails QC goes to 01_WORKING/09_qc_failed, never to outputs."""
    meta, start, end = prepare(rid, start, end, force, exact)
    name = f"{rid}_{tag or int(start)}"
    ass = TRN / f"{name}.ass"
    plat = meta.get("platform", "kick")
    page, credit = credit_line(meta)
    build_ass(meta["words"], start, end, hook, credit, ass)
    dur = round(end - start, 3)
    tmp = TRN / f"{name}.render.mp4"
    # LIP SYNC: seek PRE seconds early so the picture is decodable (keyframes every ~2s), then cut BOTH
    # tracks at the same timestamp and shift both by the same constant. Never reset each track to its
    # own first frame (PTS-STARTPTS): after a seek the first decodable video frame can be up to a
    # keyframe interval late, which pulled the picture ~1s away from the sound.
    # aresample async + apad + -t: audio covers the whole clip, never shorter than the picture
    pre = round(min(3.0, start), 3)
    vf = (f"[0:v]trim=start={pre},setpts=PTS-{pre}/TB,fps=30:start_time=0,split[a][b];"
          "[a]scale=216:384:force_original_aspect_ratio=increase,crop=216:384,boxblur=6:1,eq=brightness=-0.12,scale=1080:1920[bg];"
          "[b]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2-60[v];"
          f"[v]ass={ass.name}[vout];"
          f"[0:a:0]atrim=start={pre},asetpts=PTS-{pre}/TB,aresample=48000:async=1:first_pts=0,"
          "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,apad[aout]")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-fflags", "+discardcorrupt",
           "-ss", str(round(start - pre, 3)), "-t", str(dur + pre + 0.5), "-i", meta["file"],
           "-filter_complex", vf, "-map", "[vout]", "-map", "[aout]", "-t", str(dur),
           "-c:v", "libx264", "-preset", CFG.get("x264_preset", "superfast"), "-crf", "22", "-pix_fmt", "yuv420p",
           "-r", "30", "-threads", str(THREADS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
           "-movflags", "+faststart", str(tmp)]
    t0 = time.time()
    run(cmd, check=True, cwd=str(TRN))
    problems = qc(str(tmp), dur)
    if not any(p.startswith("FAIL") for p in problems):
        problems += sync_check(str(tmp), meta["file"], start, dur)   # every clip: sound must match the picture
    fails = [p for p in problems if p.startswith("FAIL")]
    dest_dir = QCF if fails else OUT / channel_of(day)     # one flat folder per channel
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"{name}.mp4"
    os.replace(tmp, out)
    said = " ".join(w["w"] for w in meta["words"] if start <= w["s"] < end)
    if not fails:
        who = meta.get("name", meta["slug"])
        write_caption(dest_dir, name, title or hook,
                      [hook, "", f"Clip: @{who} on {plat.title()} ({page})", f"Go follow {who} on {plat.title()}.", "",
                       "Fan channel. Not affiliated with Rockstar Games.", "",
                       f"#gta6 #gtavi #gta6gameplay #{re.sub(r'[^A-Za-z0-9]', '', meta['slug'])}"],
                      f"source: {meta['file']}\nwindow: {start}-{end}s ({dur:.0f}s)\n"
                      f"qc: {'; '.join(problems) or 'clean'}\nsaid: {said}", spoiler)
    log_row(kind="clip", status="qc_failed" if fails else "ready", creator=meta.get("name", meta["slug"]),
            platform=plat, title=hook, file=str(out.relative_to(ROOT)),
            note=f"{start}-{end}s of {rid}; qc: {'; '.join(problems) or 'clean'}")
    return {"clip": name, "file": str(out), "secs": round(time.time() - t0, 1), "len": dur,
            "ok": not fails, "qc": problems, "hook": hook}


# ---------- quality check ----------
def qc(path, dur):
    """Every clip is checked before it counts. FAIL = never post. WARN = watch it once."""
    p = []
    info = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,start_time,duration",
                           "-of", "json", path], capture_output=True, text=True).stdout or "{}")
    st = {s["codec_type"]: s for s in info.get("streams", [])}
    for kind in ("video", "audio"):
        s = st.get(kind)
        if not s:
            p.append(f"FAIL no {kind}")
            continue
        if float(s.get("start_time") or 0) > 0.1:
            p.append(f"FAIL {kind} starts late ({float(s['start_time']):.1f}s)")
        if abs(float(s.get("duration") or 0) - dur) > 0.35:
            p.append(f"FAIL {kind} is {float(s.get('duration') or 0):.1f}s, clip is {dur:.1f}s")
    if p:
        return p
    # one cheap decode pass: black opening, frozen picture, dead audio
    log = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vf",
               "fps=10,scale=180:320,blackdetect=d=0.2:pic_th=0.90:pix_th=0.08,freezedetect=n=0.002:d=2.5",
               "-af", "silencedetect=noise=-50dB:d=2", "-f", "null", "-"],
              capture_output=True, text=True).stderr
    for m in re.finditer(r"black_start:([\d.]+) black_end:([\d.]+)", log):
        a, b = float(m.group(1)), float(m.group(2))
        p.append(f"FAIL black {a:.1f}-{b:.1f}s" if a < 0.5 or b - a > 1 else f"WARN black flash {a:.1f}s")
    for m in re.finditer(r"freeze_duration: ([\d.]+)", log):
        p.append(f"WARN picture still for {float(m.group(1)):.1f}s (menu or loading?)")
    for m in re.finditer(r"silence_duration: ([\d.]+)", log):
        d = float(m.group(1))
        p.append(f"FAIL silent for {d:.1f}s" if d >= 3 else f"WARN quiet {d:.1f}s")
    return p


def _lag(ref, x, rate, max_s=3.0):
    """Seconds x lags behind ref (best normalized cross-correlation), and how confident the match is."""
    import numpy as np
    n = min(len(ref), len(x))
    if n < rate * 4:
        return 0.0, 0.0
    ref, x = ref[:n] - ref[:n].mean(), x[:n] - x[:n].mean()
    best, L = (-1.0, 0), int(max_s * rate)
    for lag in range(-L, L + 1):
        a, b = (ref[: n - lag], x[lag:]) if lag >= 0 else (ref[-lag:], x[: n + lag])
        c = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
        best = max(best, (c, lag))
    return best[1] / rate, best[0]


def sync_check(clip, src, start, dur, layout="short", clip_off=0.0):
    """Lip-sync check: line the clip's sound and picture up against the source recording separately.
    If they need different shifts, sound and picture are out of sync by the difference.
    clip_off: where this piece starts inside `clip` (for a compilation, each segment is checked in place)."""
    """Method (2026-11-19): picture = for sample frames of the clip, find the source frame they came from by
    pixel difference; sound = cross-correlate the raw waveform. Accurate to ~1 frame and ~1 ms. (The older
    movement/loudness correlation gave false fails of 0.1-0.2s on short compilation segments.)"""
    import numpy as np
    M = 1.5                                                     # how far either track may have moved, seconds
    s0 = max(0.0, start - M)
    pre = min(8.0, s0)
    src_a = ["-ss", str(round(s0 - pre, 3)), "-i", src, "-ss", str(pre), "-t", str(dur + 2 * M)]   # exact, decoded from before
    cl = (["-ss", str(clip_off)] if clip_off else []) + ["-i", clip, "-t", str(dur)]
    W, H = 96, 54

    def frames(args, vf, fps):
        raw = run(["ffmpeg", "-v", "error", *args, "-an", "-vf", f"{vf}fps={fps},scale={W}:{H},format=gray",
                   "-f", "rawvideo", "-"], capture_output=True).stdout
        f = np.frombuffer(raw, np.uint8)
        return f[: len(f) // (W * H) * (W * H)].reshape(-1, H, W).astype(np.float32)

    def wave(args):
        raw = run(["ffmpeg", "-v", "error", *args, "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                  capture_output=True).stdout
        return np.frombuffer(raw, np.int16).astype(np.float64)

    sw, sh = (int(v) for v in re.findall(r"\d+", run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                                       "-show_entries", "stream=width,height", "-of", "csv=p=0", src],
                                                      capture_output=True, text=True).stdout)[:2])
    if layout == "long":                                                          # 16:9, gameplay fills the frame
        w, h = (1920, int(round(1920 * sh / sw / 2) * 2)) if sw / sh >= 16 / 9 else (int(round(1080 * sw / sh / 2) * 2), 1080)
        crop = f"crop={w}:{h}:{(1920 - w) // 2}:{(1080 - h) // 2},"
    else:
        h = int(round(1080 * sh / sw / 2) * 2)
        crop = f"crop=1080:{h}:0:{(1920 - h) // 2 - 60},"                           # the gameplay area of the clip
    # Measure picture movement only in the middle of the gameplay, in both files: the rank number (top
    # left), the moment label (bottom) and captions are animated overlays the source doesn't have, and
    # their pops and fades fooled the match by a few frames.
    inner = "crop=trunc(iw*0.7/2)*2:trunc(ih*0.5/2)*2:trunc(iw*0.25/2)*2:trunc(ih*0.22/2)*2,"
    sf, cf = frames(src_a, inner, 60), frames(cl, crop + inner, 30)
    offs = []
    for k in range(3, len(cf) - 3, max(1, len(cf) // 20)):
        diff = ((sf - cf[k]) ** 2).mean((1, 2))
        offs.append((s0 + int(diff.argmin()) / 60) - (start + k / 30))   # + = clip shows a later source moment
    sw_, cw = wave(src_a), wave(cl)
    a_conf, v_lag, a_lag = 0.0, 0.0, 0.0
    if len(cw) > 8000 and len(sw_) > len(cw):
        n = len(cw)
        N = 1 << int(np.ceil(np.log2(len(sw_) + n)))
        corr = np.fft.irfft(np.fft.rfft(sw_, N) * np.conj(np.fft.rfft(cw, N)), N)[: len(sw_) - n + 1]
        e = np.concatenate([[0.0], np.cumsum(sw_ ** 2)])
        norm = np.sqrt(e[n:] - e[:-n]) * (np.linalg.norm(cw) + 1e-9) + 1e-9
        c = corr / norm
        j = int(c.argmax())
        a_conf, a_lag = float(c[j]), (s0 + j / 8000) - start
    # still frames (a room, a menu) match anywhere; use the frames that agree, if at least half of them do
    med = float(np.median(offs)) if offs else 0.0
    agree = [o for o in offs if abs(o - med) <= 0.05]
    if len(agree) < max(3, len(offs) / 2) or a_conf < 0.5:
        return [f"WARN lip sync not measurable (little movement or sound), watch it once"]
    v_lag = float(np.median(agree))
    d = v_lag - a_lag                         # + = sound shows an earlier moment than the picture = sound late
    if abs(d) >= 0.1:
        return [f"FAIL out of sync: sound {'late' if d > 0 else 'early'} by {abs(d):.2f}s"]
    return [f"WARN sound {'late' if d > 0 else 'early'} by {abs(d):.2f}s"] if abs(d) >= 0.06 else []


def batch(plan_path):
    """Render a list of clips from a plan file, a few at a time, and print one table."""
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    n = max(1, int(CFG.get("max_parallel_renders", 2)))
    print(f"rendering {len(plan)} clips, {n} at a time ...", flush=True)
    def one(c):
        try:
            return render(c["rid"], float(c["start"]), float(c["end"]), c["hook"], c.get("tag"),
                          day=c.get("channel") or c.get("date"), spoiler=bool(c.get("spoiler")),
                          exact=bool(c.get("exact")), title=c.get("title"))
        except SystemExit as e:
            return {"clip": f"{c['rid']}_{c.get('tag', '')}", "ok": False, "qc": [f"FAIL {e}"], "hook": c["hook"], "len": 0, "secs": 0}
        except Exception as e:
            return {"clip": f"{c['rid']}_{c.get('tag', '')}", "ok": False, "qc": [f"FAIL render error: {e}"], "hook": c["hook"], "len": 0, "secs": 0}
    t0 = time.time()
    with ThreadPoolExecutor(n) as ex:
        res = list(ex.map(one, plan))
    good = sum(r["ok"] for r in res)
    print(f"\n{good}/{len(res)} clips passed QC in {round(time.time() - t0)}s\n")
    print(f"{'clip':<34} {'len':>4}  {'QC':<6} hook")
    for r in res:
        print(f"{r['clip']:<34} {r['len']:>4.0f}  {'ok' if r['ok'] else 'FAILED':<6} {r['hook'][:60]}")
        for q in r["qc"]:
            print(f"{'':<42}{q}")
    (TRN / f"batch_{datetime.now().strftime('%H%M%S')}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


# ---------- compile: ranked Shorts and long videos from several moments ----------
FPS = 30
LABEL_SECS = 3.5


def src_size(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
               "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return tuple(int(v) for v in re.findall(r"\d+", out)[:2])


def seg_ass(words, start, end, path, layout, title, rank, label, credit, video_top, video_bottom):
    """Captions + overlays for one segment of a compilation: the rank number stays in the corner the whole
    segment, the label (why it's ranked there) shows for the first few seconds, credit is this creator's."""
    big, small = fonts()
    if layout == "long":
        res = (1920, 1080)
        styles = [
            f"Style: Rank,{big},150,&H0000E5FF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,9,3,7,60,60,30,1",
            f"Style: Label,{big},62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,3,14,0,7,75,600,215,1",
            f"Style: Cap,{big},80,&H00FFFFFF,&H0000E5FF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,6,2,2,80,80,70,1",
            f"Style: Credit,{small},32,&H00E6E6E6,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,3,0,9,40,40,30,1"]
    else:
        res = (1080, 1920)
        styles = [
            f"Style: Hook,{big},84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,3,18,0,8,70,70,250,1",
            f"Style: Rank,{big},150,&H0000E5FF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,9,3,7,40,40,{video_top + 10},1",
            f"Style: Label,{big},58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,3,12,0,2,70,70,{1920 - video_bottom + 25},1",
            f"Style: Cap,{big},92,&H00FFFFFF,&H0000E5FF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,7,2,2,60,60,560,1",
            f"Style: Credit,{small},34,&H00E6E6E6,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,3,0,2,60,60,150,1"]
    hdr = ("[Script Info]\nScriptType: v4.00+\nPlayResX: %d\nPlayResY: %d\nWrapStyle: 0\n\n[V4+ Styles]\n"
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
           "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
           "MarginR, MarginV, Encoding\n%s\n\n[Events]\n"
           "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n") % (*res, "\n".join(styles))
    dur = end - start
    T0, T1 = ass_time(0), ass_time(dur)
    ev = [f"Dialogue: 1,{T0},{T1},Credit,,0,0,0,,{ass_escape(credit)}"]
    if layout != "long" and title:
        ev.append(f"Dialogue: 1,{T0},{T1},Hook,,0,0,0,,{ass_escape(title.upper())}")
    if rank:
        ev.append(f"Dialogue: 2,{T0},{T1},Rank,,0,0,0,,{{\\fscx150\\fscy150\\t(0,220,\\fscx100\\fscy100)}}{ass_escape(rank)}")
    if label:
        ev.append(f"Dialogue: 2,{T0},{ass_time(min(LABEL_SECS, dur))},Label,,0,0,0,,{{\\fad(120,250)}}{ass_escape(label.upper())}")
    Path(path).write_text(hdr + "\n".join(ev + caption_events(words, start, end)) + "\n", encoding="utf-8")


def level_segment(path, target=-14.0):
    """Every moment in a compilation plays at the same volume. loudnorm alone doesn't settle on 7-15s pieces
    (measured spreads of up to 4.4 LU between moments), so measure the finished piece and correct it exactly,
    with a limiter so a boost can't clip. Audio is PCM here, so this costs no quality."""
    log = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128", "-f", "null", "-"],
              capture_output=True, text=True, errors="replace").stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", log)
    if not m or float(m[-1]) < -60:                              # silent piece: leave it alone
        return
    gain = max(-8.0, min(8.0, target - float(m[-1])))
    if abs(gain) < 0.5:
        return
    tmp = Path(path).with_suffix(".lvl.mkv")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(path), "-c:v", "copy",
         "-af", f"volume={gain:.2f}dB,alimiter=limit=0.79:attack=5:release=50:level=disabled:latency=1",  # -2 dBFS (AAC adds ~0.5); latency=1: no delay
         "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(tmp)], check=True)
    os.replace(tmp, path)


def compile_segment(seg, layout, title, work):
    """Render one segment to an intermediate .mkv (H.264 + PCM, frame-exact length) so segments join
    without the sound drifting from the picture."""
    meta, s, e = prepare(seg["rid"], float(seg["start"]), float(seg["end"]), exact=bool(seg.get("exact")))
    if seg.get("secs"):                                          # tease: just the first few seconds
        e = min(e, s + float(seg["secs"]))
    s = round(s, 3)
    dur = round((e - s) * FPS) / FPS                             # whole frames: 1600 samples each at 48 kHz
    sw, sh = src_size(meta["file"])
    h = int(round(1080 * sh / sw / 2) * 2)
    top = (1920 - h) // 2 - 60
    page, credit = credit_line(meta)
    ass = work / f"seg{seg['i']:02d}.ass"
    seg_ass(meta["words"], s, s + dur, ass, layout, title, seg.get("rank_text"), seg.get("label"), credit, top, top + h)
    pre = round(min(3.0, s), 3)
    trim = f"[0:v]trim=start={pre},setpts=PTS-{pre}/TB,fps={FPS}:start_time=0"
    if layout == "long":
        vf = (f"{trim},scale=1920:1080:force_original_aspect_ratio=decrease,"
              "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[v];")
    else:
        vf = (f"{trim},split[a][b];"
              "[a]scale=216:384:force_original_aspect_ratio=increase,crop=216:384,boxblur=6:1,eq=brightness=-0.12,scale=1080:1920[bg];"
              "[b]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2-60,setsar=1[v];")
    vf += (f"[v]ass={ass.name}[vout];"
           f"[0:a:0]atrim=start={pre},asetpts=PTS-{pre}/TB,aresample=48000:async=1:first_pts=0,"
           "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,"
           f"afade=t=in:d=0.04,afade=t=out:st={max(0, dur - 0.04):.3f}:d=0.04,"   # no click at the joins
           "apad[aout]")
    out = work / f"seg{seg['i']:02d}.mkv"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-fflags", "+discardcorrupt",
         "-ss", str(round(s - pre, 3)), "-t", str(dur + pre + 0.5), "-i", meta["file"],
         "-filter_complex", vf, "-map", "[vout]", "-map", "[aout]", "-t", str(dur),
         "-c:v", "libx264", "-preset", CFG.get("x264_preset", "superfast"), "-crf", "21", "-pix_fmt", "yuv420p",
         "-r", str(FPS), "-g", str(FPS * 2), "-threads", str(THREADS), "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
         str(out)], check=True, cwd=str(work))
    level_segment(out)
    return {**seg, "file": str(out), "src": meta["file"], "s": s, "dur": dur, "page": page,
            "creator": meta.get("name", meta["slug"]), "platform": meta.get("platform", "kick")}


def mmss(x):
    x = int(x)
    return f"{x // 3600}:{x % 3600 // 60:02d}:{x % 60:02d}" if x >= 3600 else f"{x // 60}:{x % 60:02d}"


def compile_plan(plan_path):
    """Join several moments into one ranked video (Top 5 Short, weekly Top 15, wholesome countdown...).
    plan = {"title", "layout": "short"|"long", "ranked": true, "tease": 0, "spoiler": false, "name",
            "items": [{"rid","start","end","label"}]}   items in PLAY order: with ranked, the first is #N, the last is #1.
    Each moment keeps its own creator credit; the joined file is QC'd and every segment is lip-sync checked in place."""
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    title = plan["title"]
    layout = plan.get("layout", "short")
    if layout not in ("short", "long"):
        raise SystemExit('layout must be "short" (9:16) or "long" (16:9)')
    items = plan["items"]
    if len(items) < 2:
        raise SystemExit("a compilation needs at least 2 items")
    ranked = plan.get("ranked", True)
    name = "compile_" + (plan.get("name") or re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:40])
    day = channel_of(plan.get("channel") or plan.get("date"))
    work = TRN / name
    work.mkdir(parents=True, exist_ok=True)

    segs = []
    tease = float(plan.get("tease") or 0)
    if tease and ranked:                                          # open on a few seconds of #1, then count down
        segs.append({**items[-1], "secs": tease, "rank_text": None, "label": plan.get("tease_label", "wait for #1"), "tease": True})
    for k, it in enumerate(items):
        segs.append({**it, "rank_text": f"#{len(items) - k}" if ranked else None, "rank": len(items) - k if ranked else k + 1})
    for i, sg in enumerate(segs):
        sg["i"] = i

    n = max(1, int(CFG.get("max_parallel_renders", 2)))
    print(f"compiling {len(segs)} segments ({layout}), {n} at a time ...", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(n) as ex:
        done = list(ex.map(lambda sg: compile_segment(sg, layout, title, work), segs))

    lst = work / "segments.txt"
    lst.write_text("".join(f"file '{Path(d['file']).name}'\n" for d in done), encoding="utf-8")
    tmp = work / f"{name}.render.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst.name,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", tmp.name],
        check=True, cwd=str(work))

    total = round(sum(d["dur"] for d in done), 3)
    problems = qc(str(tmp), total)
    if layout == "short":
        if total > 180:
            problems.append(f"FAIL {total:.0f}s is over the 3 min Shorts limit")
        elif total > 60:
            problems.append(f"WARN {total:.0f}s; ranked Shorts work best at 45 to 60s")
    off = 0.0
    if not any(p.startswith("FAIL") for p in problems):
        for d in done:                                           # lip sync of every segment, measured in the joined file
            who = "tease" if d.get("tease") else (d["rank_text"] or f"part {d['rank']}")
            problems += [f"{p.split(' ', 1)[0]} {who} {d['creator']}: {p.split(' ', 1)[1]}"
                         for p in sync_check(str(tmp), d["src"], d["s"], d["dur"], layout, off)]
            off += d["dur"]
    fails = [p for p in problems if p.startswith("FAIL")]
    dest = QCF if fails else OUT / day
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / f"{name}.mp4"
    os.replace(tmp, out)

    creators = list(dict.fromkeys(d["creator"] for d in done))
    if not fails:
        lines = [title, ""]
        if layout == "long":                                     # YouTube chapters: first at 0:00, each 10s+
            t, chapters = 0.0, []
            for d in done:
                if not d.get("tease"):
                    lab = f"{d['rank_text'] + ' ' if d['rank_text'] else ''}{d.get('label') or d['creator']} ({d['creator']})"
                    chapters.append([t, lab])
                t += d["dur"]
            chapters[0][0] = 0
            lines += [f"{mmss(c[0])} {c[1]}" for c in chapters] + [""]
        lines += ["Clips:"] + [f"{d['rank_text'] or ''} @{d['creator']} on {d['platform'].title()} ({d['page']})".strip()
                               for d in done if not d.get("tease")]
        lines += ["", "Fan channel. Not affiliated with Rockstar Games.", "",
                  "#gta6 #gtavi #gta6gameplay " + " ".join("#" + re.sub(r"[^A-Za-z0-9]", "", c) for c in creators)
                  + (" #shorts" if layout == "short" else "")]
        det = [f"length: {total:.0f}s  layout: {layout}", f"qc: {'; '.join(problems) or 'clean'}"]
        det += [f"segment {d['i']}: {Path(d['src']).stem} {d['s']}-{round(d['s'] + d['dur'], 2)}s" for d in done]
        write_caption(dest, name, plan.get("yt_title") or title, lines, "\n".join(det), bool(plan.get("spoiler")))
    for d in done:                                               # intermediates are big; the .ass files stay for review
        Path(d["file"]).unlink(missing_ok=True)
    log_row(kind="compile", status="qc_failed" if fails else "ready", creator=", ".join(creators), platform="mixed",
            title=title, file=str(out.relative_to(ROOT)), note=f"{len(items)} moments, {total:.0f}s; qc: {'; '.join(problems) or 'clean'}")

    print(f"\n{'ready' if not fails else 'QC FAILED'}: {out}  ({total:.0f}s, {layout}, {round(time.time() - t0)}s to make)")
    print(f"{'seg':<4} {'rank':<5} {'len':>4}  creator / label")
    for d in done:
        print(f"{d['i']:<4} {('tease' if d.get('tease') else d['rank_text'] or '-'):<5} {d['dur']:>4.0f}  {d['creator']} / {d.get('label') or ''}")
    for p in problems:
        print(f"  {p}")
    return {"file": str(out), "ok": not fails, "qc": problems, "len": total}


# ---------- doctor ----------
def doctor():
    ok = True
    def line(label, good, detail=""):
        nonlocal ok
        ok = ok and good
        print(f"  [{'ok' if good else '!!'}] {label}{(' - ' + detail) if detail else ''}")
    print(f"Clipping Studio doctor  ({platform.system()} {platform.release()}, Python {platform.python_version()})")
    line("Python 3.9+", sys.version_info >= (3, 9))
    ff = shutil.which("ffmpeg")
    line("ffmpeg", bool(ff), ff or "install ffmpeg (see README)")
    if ff:
        flt = run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        line("ffmpeg has libass (captions)", " ass " in flt, "" if " ass " in flt else "use a 'full' ffmpeg build")
    for mod in ("numpy", "faster_whisper"):
        try:
            __import__(mod); line(f"python package {mod}", True)
        except Exception:
            line(f"python package {mod}", False, "pip install -r requirements.txt")
    line("streamlink (records every stream)", bool(shutil.which("streamlink")), "" if shutil.which("streamlink") else "pip install -r requirements.txt")
    cores = os.cpu_count() or 1
    ram = None
    try:
        if platform.system() == "Windows":
            import ctypes
            class M(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("tot", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong),
                            ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong), ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong)]
            m = M(); m.l = ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); ram = m.tot / 2**30
        elif hasattr(os, "sysconf"):
            ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
    except Exception:
        pass
    tier = "low" if cores <= 4 or (ram and ram < 12) else ("high" if cores >= 12 else "mid")
    # recording is network work (streamlink), so even a slow laptop can record 5 at once
    prof = {"low": {"whisper_model": "base.en", "max_parallel_grabs": 5, "max_parallel_renders": 2, "x264_preset": "ultrafast"},
            "mid": {"whisper_model": "small.en", "max_parallel_grabs": 6, "max_parallel_renders": 3, "x264_preset": "superfast"},
            "high": {"whisper_model": "small.en", "max_parallel_grabs": 8, "max_parallel_renders": 4, "x264_preset": "veryfast"}}[tier]
    prof["threads"] = cores
    print(f"  CPU threads: {cores}   RAM: {round(ram, 1) if ram else '?'} GB   -> machine tier: {tier}")
    (ROOT / "studio.config.local.json").write_text(json.dumps(prof, indent=2), encoding="utf-8")
    print(f"  wrote studio.config.local.json: {prof}")
    print("ALL GOOD" if ok else "FIX THE [!!] LINES, then run doctor again")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor")
    lv = sub.add_parser("live"); lv.add_argument("slugs", nargs="+")
    g = sub.add_parser("grab"); g.add_argument("sources", nargs="+"); g.add_argument("--secs", type=int, default=60)
    sc = sub.add_parser("scan"); sc.add_argument("files", nargs="+")
    r = sub.add_parser("render"); r.add_argument("rid"); r.add_argument("--start", type=float, required=True)
    r.add_argument("--end", type=float, required=True); r.add_argument("--hook", required=True); r.add_argument("--tag")
    r.add_argument("--force", action="store_true", help="render even across a gap in the recording")
    b = sub.add_parser("batch"); b.add_argument("plan", help='JSON list of {"rid","start","end","hook","tag"}')
    c = sub.add_parser("compile", help="join several moments into one ranked Short or long video")
    c.add_argument("plan", help='JSON {"title","layout":"short|long","ranked":true,"tease":0,"items":[{"rid","start","end","label"}]}')
    a = ap.parse_args()

    if a.cmd == "doctor":
        sys.exit(0 if doctor() else 1)
    need_dirs()
    if a.cmd == "live":
        for s in a.slugs:
            if s.lower() == "kick":
                continue
            try:
                i = kick_live(parse_source(s)[1])
                print(f"  LIVE  {i['slug']:<20} {i['viewers']:>8} viewers  {i['title'][:60]}" if i else f"  off   {s}")
            except Exception as e:
                print(f"  ??    {s}: {e}")
    elif a.cmd == "grab":
        live = []
        for s in a.sources:
            try:
                info = resolve(s)
            except Exception as e:
                info = None; print(f"[skip] {s}: {e}")
            if info:
                live.append(info)
            else:
                print(f"[offline] {s}")
        n = max(1, min(len(live), int(CFG.get("max_parallel_grabs", 4))))
        print(f"recording {len(live)} streams for {a.secs}s, {n} at a time ...", flush=True)
        with ThreadPoolExecutor(n) as ex:
            recs = [m for m in ex.map(lambda i: record(i, a.secs), live) if m]
        for m in recs:
            log_row(kind="recording", status="done", creator=m["name"], platform=m["platform"], title=m.get("title", ""),
                    file=str(Path(m["file"]).relative_to(ROOT)))
        report(recs)
    elif a.cmd == "scan":
        recs = []
        for f in a.files:
            f = Path(f).resolve(); rid = f.stem
            mp = TRN / f"{rid}.meta.json"
            recs.append(json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else
                        {"platform": "kick", "slug": rid.rsplit("_", 1)[0], "name": rid.rsplit("_", 1)[0],
                         "title": "", "viewers": None, "rid": rid, "file": str(f)})
        report(recs)
    elif a.cmd == "batch":
        batch(a.plan)
    elif a.cmd == "compile":
        compile_plan(a.plan)
    else:
        r = render(a.rid, a.start, a.end, a.hook, a.tag, a.force)
        print(f"{'ready' if r['ok'] else 'QC FAILED'}: {r['file']} ({r['len']:.0f}s clip, {r['secs']}s to render)")
        for q in r["qc"]:
            print(f"  {q}")


if __name__ == "__main__":
    main()
