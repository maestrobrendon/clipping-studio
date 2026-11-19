"""Live alert: push a phone notification when a watchlist creator goes live (or schedules a YouTube stream).

Reads 01_WORKING/08_notes/watchlist_gta6_launch.csv, checks Kick, Twitch and YouTube, and sends a push
through ntfy (free app for iPhone/Android). Only state changes are pushed: offline -> live, and new
YouTube "upcoming" streams. State is kept in 01_WORKING/08_notes/live_alert_state.json.

  python tools/live_alert.py              one check, push changes (what the scheduled task runs)
  python tools/live_alert.py --dry        one check, print only, no push
  python tools/live_alert.py --test       send a test push to the phone
  python tools/live_alert.py --watch 180  keep checking every 180 s (for a terminal window)
  python tools/live_alert.py --tiers A,B  limit to watchlist tiers (default: all)

Phone setup: install "ntfy" from the App Store / Play Store, tap +, subscribe to the topic printed by --test
(stored as "ntfy_topic" in studio.config.local.json).
"""
import argparse, csv, json, re, secrets, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WATCH = ROOT / "01_WORKING/08_notes/watchlist_gta6_launch.csv"
STATE = ROOT / "01_WORKING/08_notes/live_alert_state.json"
LOCAL_CFG = ROOT / "studio.config.local.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/130.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9"}
TWITCH_CLIENT = "kimne78kx3ncx6brgo4mv6wki5h1ko"  # Twitch's public web client id


# ---------- config ----------
def topic():
    cfg = json.loads(LOCAL_CFG.read_text(encoding="utf-8")) if LOCAL_CFG.exists() else {}
    if not cfg.get("ntfy_topic"):
        cfg["ntfy_topic"] = "clipstudio-live-" + secrets.token_hex(6)
        LOCAL_CFG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg["ntfy_topic"]


def push(title, body, url=None, tags="red_circle", priority="high"):
    h = {"Title": title.encode("utf-8"), "Tags": tags, "Priority": priority}
    if url:
        h["Click"] = url
    req = urllib.request.Request(f"https://ntfy.sh/{topic()}", data=body.encode("utf-8"), headers=h, method="POST")
    urllib.request.urlopen(req, timeout=20).read()


# ---------- watchlist ----------
def load_watchlist(tiers):
    out, seen = [], set()
    for r in csv.DictReader(open(WATCH, encoding="utf-8")):
        if tiers and r["tier"] not in tiers:
            continue
        url = r["url"].strip().rstrip("/")
        name = r["name"]
        if url.endswith("/@YouTube"):  # tier C: all on YouTube's official 24h stream
            name = "YouTube official GTA 6 stream"
        if not url or url in seen:
            continue
        seen.add(url)
        if "kick.com/" in url:
            out.append({"key": url, "name": name, "platform": "kick", "id": url.split("/")[-1], "page": url})
        elif "twitch.tv/" in url:
            out.append({"key": url, "name": name, "platform": "twitch", "id": url.split("/")[-1].lower(), "page": url})
        elif "youtube.com/" in url:
            out.append({"key": url, "name": name, "platform": "youtube", "id": url, "page": url + "/live"})
    return out


# ---------- checks: each returns {"state": "live"|"upcoming"|"off", ...} ----------
def check_kick(c):
    req = urllib.request.Request(f"https://kick.com/api/v2/channels/{c['id']}", headers={**UA, "Accept": "application/json"})
    j = json.load(urllib.request.urlopen(req, timeout=20))
    ls = j.get("livestream")
    if not ls or not ls.get("is_live"):
        return {"state": "off"}
    cats = ls.get("categories") or []
    return {"state": "live", "title": ls.get("session_title") or "", "viewers": ls.get("viewer_count"),
            "game": cats[0].get("name") if cats else ""}


def check_twitch_all(chans):
    """One GraphQL call for every Twitch channel."""
    if not chans:
        return {}
    q = "query($l: String!) { user(login: $l) { stream { title viewersCount game { name } } } }"
    body = json.dumps([{"query": q, "variables": {"l": c["id"]}} for c in chans]).encode()
    req = urllib.request.Request("https://gql.twitch.tv/gql", data=body, method="POST",
                                 headers={"Client-ID": TWITCH_CLIENT, "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req, timeout=25))
    out = {}
    for c, d in zip(chans, data):
        s = (((d.get("data") or {}).get("user")) or {}).get("stream")
        out[c["key"]] = ({"state": "live", "title": s.get("title") or "", "viewers": s.get("viewersCount"),
                          "game": (s.get("game") or {}).get("name", "")} if s else {"state": "off"})
    return out


def check_youtube(c):
    req = urllib.request.Request(c["page"], headers={**UA, "Cookie": "CONSENT=YES+1; SOCS=CAI"})
    html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
    vid = re.search(r'"videoDetails":\{"videoId":"([\w-]{11})"', html)
    title = re.search(r'"videoDetails":\{.*?"title":"((?:[^"\\]|\\.)*)"', html)
    title = json.loads(f'"{title.group(1)}"') if title else ""
    watch = f"https://www.youtube.com/watch?v={vid.group(1)}" if vid else c["page"]
    if '"isLiveNow":true' in html or re.search(r'"videoDetails":\{[^}]*"isLive":true', html):
        v = re.search(r'"concurrentViewers":"(\d+)"', html)
        return {"state": "live", "title": title, "viewers": int(v.group(1)) if v else None, "url": watch, "game": ""}
    if '"isUpcoming":true' in html:
        st = re.search(r'"scheduledStartTime":"(\d+)"', html)
        return {"state": "upcoming", "title": title, "url": watch,
                "start": int(st.group(1)) if st else None, "vid": vid.group(1) if vid else ""}
    return {"state": "off"}


def check_all(chans):
    res = {}
    try:
        res.update(check_twitch_all([c for c in chans if c["platform"] == "twitch"]))
    except Exception as e:
        print(f"twitch check failed: {e}", file=sys.stderr)
    others = [c for c in chans if c["platform"] != "twitch"]
    fn = {"kick": check_kick, "youtube": check_youtube}

    def one(c):
        try:
            return c["key"], fn[c["platform"]](c)
        except Exception as e:
            return c["key"], {"state": "error", "err": str(e)[:120]}
    with ThreadPoolExecutor(8) as ex:
        res.update(dict(ex.map(one, others)))
    return res


# ---------- main ----------
def fmt_viewers(v):
    return "" if v is None else (f"{v/1000:.1f}K viewers" if v >= 1000 else f"{v} viewers")


def run_once(chans, dry=False):
    first = not STATE.exists()  # first run: one summary push instead of one per live creator
    state = {} if first else json.loads(STATE.read_text(encoding="utf-8"))
    res = check_all(chans)
    sent, summary = 0, []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for c in chans:
        r = res.get(c["key"], {"state": "error"})
        prev = state.get(c["key"], {})
        if r["state"] == "error":  # keep the old state, never alert on a failed check
            print(f"  ?  {c['name']:<32} check failed {r.get('err', '')}")
            continue
        msg = None
        if r["state"] == "live" and prev.get("state") != "live":
            bits = [b for b in (r.get("game"), fmt_viewers(r.get("viewers"))) if b]
            gta = "gta" in (r.get("game", "") + r.get("title", "")).lower()
            msg = (f"{c['name']} is LIVE on {c['platform'].title()}",
                   " | ".join(bits + [r.get("title", "")[:120]]).strip(" |") or "Live now",
                   r.get("url") or c["page"], "red_circle,video_game" if gta else "red_circle")
        elif r["state"] == "upcoming" and prev.get("vid") != r.get("vid"):
            when = (datetime.fromtimestamp(r["start"]).strftime("%a %H:%M") if r.get("start") else "soon")
            msg = (f"{c['name']} is going live {when}", r.get("title", "")[:150] or "Scheduled stream",
                   r.get("url") or c["page"], "alarm_clock")
        mark = {"live": "LIVE", "upcoming": "SOON", "off": " -  "}[r["state"]]
        print(f"  {mark} {c['name']:<32} {c['platform']:<8} {r.get('game', '') or ''} {fmt_viewers(r.get('viewers'))}")
        if msg and first:
            summary.append(c["name"] + (" (soon)" if r["state"] == "upcoming" else ""))
        elif msg:
            if dry:
                print(f"       would push: {msg[0]} / {msg[1]}")
            else:
                try:
                    push(msg[0], msg[1], msg[2], msg[3])
                    sent += 1
                except Exception as e:
                    print(f"       push failed: {e}", file=sys.stderr)
                    continue  # retry next run
        state[c["key"]] = {**{k: r.get(k) for k in ("state", "vid")}, "seen": now}
    if summary:
        print(f"first run summary: {len(summary)} live/soon")
        if not dry:
            push(f"{len(summary)} watchlist creators live or scheduled", ", ".join(summary)[:1000],
                 tags="red_circle", priority="default")
            sent += 1
    if not dry:
        STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")
    live = sum(1 for k in res.values() if k.get("state") == "live")
    print(f"{datetime.now():%H:%M} checked {len(chans)}, {live} live, {sent} pushed")


def main():
    if sys.stdout is None:  # pythonw (scheduled task): log to a file, keep only recent lines
        logf = STATE.with_name("live_alert.log")
        if logf.exists() and logf.stat().st_size > 200_000:
            logf.write_text(logf.read_text(encoding="utf-8")[-50_000:], encoding="utf-8")
        sys.stdout = sys.stderr = open(logf, "a", encoding="utf-8")
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--watch", type=int, metavar="SECS")
    ap.add_argument("--tiers", default="")
    a = ap.parse_args()
    if a.test:
        push("Clipping Studio alerts are on", "You'll get a push when a watchlist creator goes live.",
             tags="white_check_mark", priority="default")
        print(f"Test sent. Subscribe in the ntfy app to topic: {topic()}")
        return
    chans = load_watchlist(set(t.strip().upper() for t in a.tiers.split(",") if t.strip()))
    while True:
        run_once(chans, a.dry)
        if not a.watch:
            break
        time.sleep(a.watch)


if __name__ == "__main__":
    main()
