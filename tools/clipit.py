"""Clipping Studio - fast live clipper. Runs on Windows, macOS and Linux.

  python tools/clipit.py doctor                         check this machine, write its profile
  python tools/clipit.py live   kick xqc n3on ...       who is live right now (Kick)
  python tools/clipit.py grab   kick:xqc twitch:kaicenat --secs 60
                                                        record live streams in parallel, find the best
                                                        moments, save transcript + frames for review
  python tools/clipit.py scan   <recording.ts> ...      find moments in recordings you already have
  python tools/clipit.py render <rec_id> --start S --end E --hook "TEXT" [--tag t1]
                                                        make the 9:16 captioned clip + post copy

Sources: kick:<slug> (default if no prefix), twitch:<login> (needs streamlink), yt:<@handle or url> (needs yt-dlp)

Where files go (never mix working files and outputs):
  recordings  01_WORKING/01_capture_stream_segments/<date>/
  transcripts 01_WORKING/06_transcripts/<date>/   (also the review frames and .ass caption files)
  clips       02_OUTPUTS/01_clips_ready_to_post/<date>/
  post copy   02_OUTPUTS/03_post_copy/<date>/
  log         00_TRACKER/clip_log.csv
"""
import argparse, csv, json, os, platform, re, shutil, subprocess, sys, time, urllib.parse, urllib.request
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
OUT = ROOT / "02_OUTPUTS" / "01_clips_ready_to_post" / TODAY
COPY = ROOT / "02_OUTPUTS" / "03_post_copy" / TODAY
LOG = ROOT / "00_TRACKER" / "clip_log.csv"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}
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
    for d in (CAP, TRN, OUT, COPY, LOG.parent):
        d.mkdir(parents=True, exist_ok=True)


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


def twitch_live(login):
    if not shutil.which("streamlink"):
        raise RuntimeError("Twitch needs streamlink: pip install streamlink")
    r = run(["streamlink", "--stream-url", f"https://www.twitch.tv/{login}", "720p60,720p,480p,best"],
            capture_output=True, text=True, timeout=60)
    url = r.stdout.strip()
    if r.returncode or not url.startswith("http"):
        return None
    return {"platform": "twitch", "slug": login, "url": url, "title": "", "viewers": None, "name": login,
            "page": f"https://www.twitch.tv/{login}"}


def youtube_live(handle):
    if not shutil.which("yt-dlp"):
        raise RuntimeError("YouTube needs yt-dlp: pip install yt-dlp")
    page = handle if handle.startswith("http") else f"https://www.youtube.com/{handle}/live"
    r = run(["yt-dlp", "-g", "-f", "best[height<=720]/best", page], capture_output=True, text=True, timeout=90)
    url = (r.stdout.strip().splitlines() or [""])[0]
    if r.returncode or not url.startswith("http"):
        return None
    slug = re.sub(r"[^A-Za-z0-9_-]", "", handle.split("/")[-2] if handle.startswith("http") else handle)
    return {"platform": "youtube", "slug": slug or "youtube", "url": url, "title": "", "viewers": None,
            "name": handle, "page": page}


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
    rid = f"{info['slug']}_{datetime.now().strftime('%H%M%S')}"
    path = CAP / f"{rid}.ts"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-rw_timeout", "15000000", "-i", info["url"],
           "-t", str(secs), "-c", "copy", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        p.wait(timeout=secs + 30)
    except subprocess.TimeoutExpired:            # hard stop: keep whatever arrived
        try:
            p.communicate(b"q", timeout=10)
        except Exception:
            p.kill()
    if not path.exists() or path.stat().st_size < 100_000:
        return None
    meta = dict(info, rid=rid, file=str(path), recorded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    meta.pop("url", None)                         # playback URLs carry short-lived tokens; don't keep them
    (TRN / f"{rid}.meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


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


def best_windows(db, hop, words, length=(12, 28), k=3):
    import numpy as np
    dur = len(db) * hop
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
        c = np.convolve(score, np.ones(n), "valid") / np.sqrt(L)    # dense moments beat long ones
        for i in np.argsort(c)[::-1][:40]:
            cands.append((float(c[i]), t[i], t[i] + L))
    cands.sort(reverse=True)
    picked = []
    for sc, s, e in cands:
        if all(e <= ps or s >= pe for _, ps, pe in picked):
            picked.append((round(sc, 1), max(0, round(s - 0.5, 2)), min(dur, round(e + 1.0, 2))))
        if len(picked) == k:
            break
    return picked


def frames(path, tag, times):
    outs = []
    for i, tt in enumerate(times):
        p = TRN / f"{tag}_f{i}.jpg"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(max(0, tt)), "-i", path,
             "-frames:v", "1", "-vf", "scale=640:-2", str(p)])
        outs.append(str(p))
    return outs


def analyse(meta):
    db, hop = loudness(meta["file"])
    words, done = [], []
    for _, s, e in best_windows(db, hop, [], k=3):     # pass 1: loudness finds hot spots
        s, e = max(0, s - 1), e + 1
        if any(s < de and e > ds for ds, de in done):
            continue
        done.append((s, e))
        words += transcribe(meta["file"], s, e - s)     # pass 2: transcribe only the hot spots
    words.sort(key=lambda w: w["s"])
    meta["words"], meta["windows"] = words, []
    for sc, s, e in best_windows(db, hop, words):
        text = " ".join(w["w"] for w in words if s <= w["s"] <= e)
        meta["windows"].append({"score": sc, "start": s, "end": e, "text": text,
                                "frames": frames(meta["file"], f"{meta['rid']}_{int(s)}", [s + 1, (s + e) / 2, e - 1])})
    (TRN / f"{meta['rid']}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


def report(recs):
    for m in recs:
        t0 = time.time()
        m = analyse(m)
        print(f"\n=== {m['rid']}  [{m.get('platform', 'kick')}]  viewers={m.get('viewers')}  ({round(time.time() - t0)}s)  {m.get('title', '')[:60]}")
        for w in m["windows"]:
            print(f"  score {w['score']:>6}  {w['start']:6.1f}-{w['end']:6.1f}s  | {w['text'][:220]}")
            print(f"    frames: {' | '.join(w['frames'])}")


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
    ws = [w for w in words if start <= w["s"] < end and w["w"]]
    for i in range(0, len(ws), 3):
        grp = ws[i:i + 3]
        s = grp[0]["s"] - start
        e = (ws[i + 3]["s"] - start) if i + 3 < len(ws) else grp[-1]["e"] - start + 0.3
        e = min(e, grp[-1]["e"] - start + 0.6)
        txt = " ".join(re.sub(r"[^\w'!?.,-]", "", g["w"]) for g in grp).upper()
        if txt.strip():
            ev.append(f"Dialogue: 0,{ass_time(s)},{ass_time(max(e, s + 0.25))},Cap,,0,0,0,,"
                      f"{{\\fscx108\\fscy108\\t(0,90,\\fscx100\\fscy100)}}{ass_escape(txt)}")
    Path(path).write_text(hdr + "\n".join(ev) + "\n", encoding="utf-8")


def render(rid, start, end, hook, tag=None):
    meta = json.loads((TRN / f"{rid}.json").read_text(encoding="utf-8"))
    name = f"{rid}_{tag or int(start)}"
    ass = TRN / f"{name}.ass"
    plat = meta.get("platform", "kick")
    page = meta.get("page") or f"https://kick.com/{meta['slug']}"
    credit = f"Clip: {page.replace('https://', '').replace('www.', '')}"
    build_ass(meta["words"], start, end, hook, credit, ass)
    out = OUT / f"{name}.mp4"
    vf = ("[0:v]fps=30,split[a][b];"
          "[a]scale=216:384:force_original_aspect_ratio=increase,crop=216:384,boxblur=6:1,eq=brightness=-0.12,scale=1080:1920[bg];"
          "[b]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2-60[v];"
          f"[v]ass={ass.name}[out]")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start), "-t", str(end - start), "-i", meta["file"],
           "-filter_complex", vf, "-map", "[out]", "-map", "0:a:0", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
           "-c:v", "libx264", "-preset", CFG.get("x264_preset", "superfast"), "-crf", "22", "-pix_fmt", "yuv420p",
           "-threads", str(THREADS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    t0 = time.time()
    run(cmd, check=True, cwd=str(TRN))
    said = " ".join(w["w"] for w in meta["words"] if start <= w["s"] < end)
    (COPY / f"{name}.txt").write_text(
        f"{hook}\n\nClip: @{meta.get('name', meta['slug'])} on {plat.title()} ({page})\n\n"
        f"#gta6 #gtavi #gta6gameplay #{re.sub(r'[^A-Za-z0-9]', '', meta['slug'])}\n\n"
        f"---\nsource: {meta['file']}\nwindow: {start}-{end}s\nsaid: {said}\n", encoding="utf-8")
    log_row(kind="clip", status="ready", creator=meta.get("name", meta["slug"]), platform=plat, title=hook,
            file=str(out.relative_to(ROOT)), note=f"{start}-{end}s of {rid}")
    return str(out), round(time.time() - t0, 1)


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
    for tool, why in (("streamlink", "Twitch"), ("yt-dlp", "YouTube")):
        print(f"  [{'ok' if shutil.which(tool) else '--'}] {tool} (optional, for {why})")
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
    prof = {"low": {"whisper_model": "base.en", "max_parallel_grabs": 2, "x264_preset": "ultrafast"},
            "mid": {"whisper_model": "small.en", "max_parallel_grabs": 4, "x264_preset": "superfast"},
            "high": {"whisper_model": "small.en", "max_parallel_grabs": 8, "x264_preset": "veryfast"}}[tier]
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
    else:
        out, secs = render(a.rid, a.start, a.end, a.hook, a.tag)
        print(f"rendered {out} in {secs}s")


if __name__ == "__main__":
    main()
