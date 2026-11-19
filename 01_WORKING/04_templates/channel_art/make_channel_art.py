"""Channel art, concept "control room": a wall of stream tiles, a highlighter swipe over the key word,
camera-viewfinder corners. Original artwork, no Rockstar or platform assets.

  python make_channel_art.py                 writes banner.png, profile_picture.png, watermark_150.png
  python make_channel_art.py --name "STREAM HIGHLIGHTS HUB" --mark HIGHLIGHTS --tagline "..." --schedule "..."

Older concepts: v1_cartoon/, v2_five_star/, v3_sunset_hub/ (each with its own script).
Fonts: Anton (OFL), Bebas Neue (OFL), Consolas (Windows).
"""
import argparse, math, os, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts", Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts"]
S = 2  # supersample

INK = (10, 10, 15, 255)
LIME = (198, 255, 26, 255)
RED = (255, 48, 64, 255)
WHITE = (255, 255, 255, 255)
GREY = (150, 150, 165, 255)


def font(name, px):
    for d in FONTS:
        if (d / name).exists():
            return ImageFont.truetype(str(d / name), int(px * S))
    raise SystemExit(f"font {name} not found")


def tracked(draw, xy, text, fnt, fill, tracking=0, anchor="ls"):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill, anchor=anchor)
        x += draw.textlength(ch, font=fnt) + tracking * S
    return x


def tracked_len(draw, text, fnt, tracking=0):
    return sum(draw.textlength(ch, font=fnt) for ch in text) + tracking * S * len(text)


def tile(w, h, rnd):
    """One fake stream thumbnail: dim two-tone gradient + soft blobs + progress bar."""
    pal = [((40, 20, 70), (10, 60, 80)), ((70, 30, 20), (20, 20, 50)), ((15, 55, 45), (40, 15, 60)),
           ((60, 45, 15), (15, 30, 60)), ((25, 25, 35), (55, 20, 45))]
    a, b = rnd.choice(pal)
    small = Image.new("RGBA", (8, 8))
    px = small.load()
    for y in range(8):
        for x in range(8):
            t = (x + y) / 14
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)
    im = small.resize((w, h), Image.BICUBIC)
    blobs = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blobs)
    for _ in range(3):
        r = rnd.randint(h // 6, h // 2)
        cx, cy = rnd.randint(0, w), rnd.randint(0, h)
        c = rnd.choice([(255, 140, 60), (90, 200, 255), (255, 80, 160), (180, 255, 120)])
        bd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c + (45,))
    im.alpha_composite(blobs.filter(ImageFilter.GaussianBlur(h / 6)))
    d = ImageDraw.Draw(im)
    bar_y = h - 7 * S
    d.rectangle([0, bar_y, w, h], fill=(0, 0, 0, 140))
    d.rectangle([0, bar_y + 2 * S, int(w * rnd.uniform(0.15, 0.9)), h - 2 * S], fill=(255, 255, 255, 90))
    return im


def tile_wall(W, H, tw, th, gap, seed, highlights=(), live=()):
    rnd = random.Random(seed)
    wall = Image.new("RGBA", (W, H), INK)
    d = ImageDraw.Draw(wall)
    cols = W // (tw + gap) + 2
    rows = H // (th + gap) + 2
    ox = -((cols * (tw + gap) - W) // 2)
    oy = -((rows * (th + gap) - H) // 2)
    lab = font("consolab.ttf", 15)
    for r in range(rows):
        for c in range(cols):
            x, y = ox + c * (tw + gap), oy + r * (th + gap)
            wall.alpha_composite(tile(tw, th, rnd), (x, y)) if x >= 0 and y >= 0 else wall.paste(tile(tw, th, rnd), (x, y))
            d.rectangle([x, y, x + tw - 1, y + th - 1], outline=(40, 40, 55, 255), width=S)
            if (r, c) in live:
                d.rounded_rectangle([x + 10 * S, y + 10 * S, x + 66 * S, y + 32 * S], 4 * S, fill=RED)
                d.text((x + 38 * S, y + 22 * S), "LIVE", font=lab, fill=WHITE, anchor="mm")
            if (r, c) in highlights:
                d.rectangle([x - 3 * S, y - 3 * S, x + tw + 2 * S, y + th + 2 * S], outline=LIME, width=4 * S)
    return wall


def marker_swipe(w, h, rot=-2.5, seed=1):
    """Highlighter stroke: slightly ragged ends, a touch of transparency, tilted. Returned with padding h on every side."""
    rnd = random.Random(seed)
    pad = h
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts_top, pts_bot = [], []
    n = 24
    for i in range(n + 1):
        x = pad + w * i / n
        pts_top.append((x, pad + rnd.uniform(-0.015, 0.015) * h))
        pts_bot.append((x, pad + h + rnd.uniform(-0.015, 0.015) * h))
    # rounded-ish chisel ends with a little wobble, like a real marker stroke
    left = [(pad - (0.10 + 0.12 * math.sin(math.pi * k / 8)) * h + rnd.uniform(-0.02, 0.02) * h, pad + h * k / 8) for k in range(9)]
    right = [(pad + w + (0.14 + 0.12 * math.sin(math.pi * k / 8)) * h + rnd.uniform(-0.02, 0.02) * h, pad + h * k / 8) for k in range(9)]
    d.polygon(pts_top + right + pts_bot[::-1] + left[::-1], fill=LIME[:3] + (240,))
    return im.rotate(rot, resample=Image.BICUBIC, expand=False)


def sorted_box(x0, y0, x1, y1):
    return [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]


def corners(d, box, L, wdt, col=WHITE):
    x0, y0, x1, y1 = box
    for (x, y, sx, sy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        d.rectangle(sorted_box(x, y, x + sx * L, y + sy * wdt), fill=col)
        d.rectangle(sorted_box(x, y, x + sx * wdt, y + sy * L), fill=col)


def banner(name, mark, tagline, schedule, path):
    W, H = 2048 * S, 1152 * S
    CX = 1024 * S
    img = tile_wall(W, H, 300 * S, 169 * S, 14 * S, seed=21,
                    highlights={(1, 1), (4, 6), (2, 5)}, live={(0, 2), (3, 0), (4, 3), (1, 6)})
    # darken the wall, most of all behind the type (the always-visible strip, y 407..745)
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    sd.rectangle([0, 0, W, H], fill=85)
    sd.rounded_rectangle([330 * S, 380 * S, 1718 * S, 772 * S], 40 * S, fill=235)
    shade = shade.filter(ImageFilter.GaussianBlur(60 * S))
    dark = Image.new("RGBA", (W, H), INK[:3] + (0,))
    dark.putalpha(shade)
    img.alpha_composite(dark)
    d = ImageDraw.Draw(img)

    # title on one line; the marked word sits on a highlighter swipe in dark ink
    words = name.split(" ")
    size = 150
    tf = font("Anton-Regular.ttf", size)
    while size > 80 and tracked_len(d, name, tf, 3) > 1120 * S:
        size -= 2
        tf = font("Anton-Regular.ttf", size)
    total = tracked_len(d, name, tf, 3)
    x = CX - total / 2
    base = 610 * S
    for i, w in enumerate(words):
        txt = w + (" " if i < len(words) - 1 else "")
        wl = tracked_len(d, w, tf, 3)
        if w == mark:
            hh = int(size * 0.94 * S)
            sw = marker_swipe(int(wl + 24 * S), hh, seed=4)
            img.alpha_composite(sw, (int(x - 12 * S - hh), int(base - size * 0.87 * S - hh)))
            d = ImageDraw.Draw(img)
            tracked(d, (x, base), txt, tf, INK, 3)
        else:
            sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            tracked(ImageDraw.Draw(sh), (x + 5 * S, base + 5 * S), txt, tf, (0, 0, 0, 200), 3)
            img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(2 * S)))
            d = ImageDraw.Draw(img)
            tracked(d, (x, base), txt, tf, WHITE, 3)
        x += tracked_len(d, txt, tf, 3)
    left, right = CX - total / 2, CX + total / 2

    # REC chip above, left-aligned with the title; timecode right-aligned
    cf = font("consolab.ttf", 26)
    d.ellipse([left, 436 * S, left + 20 * S, 456 * S], fill=RED)
    tracked(d, (left + 32 * S, 455 * S), "REC  LIVE STREAM CLIPS", cf, WHITE, 2)
    tc = "00:00:45:12"
    tracked(d, (right - tracked_len(d, tc, cf, 2), 455 * S), tc, cf, GREY, 2)

    # tagline + schedule, centered
    bf = font("BebasNeue-Regular.ttf", 50)
    tl = tracked_len(d, tagline, bf, 5)
    tracked(d, (CX - tl / 2, 672 * S), tagline, bf, WHITE, 5)
    sf = font("consolab.ttf", 24)
    sl = tracked_len(d, schedule, sf, 2)
    tracked(d, (CX - sl / 2, 716 * S), schedule, sf, LIME, 2)

    # viewfinder corners framing the block (inside the mobile-safe strip)
    corners(d, (left - 40 * S, 418 * S, right + 40 * S, 736 * S), 46 * S, 5 * S)
    img.resize((2048, 1152), Image.LANCZOS).convert("RGB").save(path, optimize=True)


def profile(path, wm_path):
    D = 800 * S
    img = Image.new("RGBA", (D, D), INK)
    wall = tile_wall(D, D, 230 * S, 130 * S, 12 * S, seed=5, highlights={(2, 0)}, live=set())
    wall.alpha_composite(Image.new("RGBA", (D, D), INK[:3] + (205,)))
    img.alpha_composite(wall)
    # lime highlighter swipe across the middle
    hh = int(200 * S)
    sw = marker_swipe(int(400 * S), hh, rot=-6, seed=9)
    img.alpha_composite(sw, (int(D / 2 - 200 * S - hh), int(D / 2 - 100 * S - hh)))
    d = ImageDraw.Draw(img)
    # dark play triangle on the swipe, rounded with a thick round-joined line
    cx, cy, R = D / 2 + 18 * S, D / 2, 100 * S
    tri = [(cx - R * 0.62, cy - R * 0.95), (cx + R, cy), (cx - R * 0.62, cy + R * 0.95)]
    d.polygon(tri, fill=INK)
    d.line(tri + [tri[0]], fill=INK, width=int(30 * S), joint="curve")
    for x, y in tri:
        d.ellipse([x - 15 * S, y - 15 * S, x + 15 * S, y + 15 * S], fill=INK)
    # viewfinder corners + REC dot
    m = 175 * S
    corners(d, (m, m, D - m, D - m), 70 * S, 14 * S)
    d.ellipse([D - m - 44 * S, m + 30 * S, D - m - 14 * S, m + 60 * S], fill=RED)
    out = img.resize((800, 800), Image.LANCZOS).convert("RGB")
    out.save(path, optimize=True)
    out.resize((150, 150), Image.LANCZOS).save(wm_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="STREAM HIGHLIGHTS HUB")
    ap.add_argument("--mark", default="HIGHLIGHTS", help="the word that gets the highlighter swipe")
    ap.add_argument("--tagline", default="THE BEST MOMENTS FROM THE BIGGEST STREAMERS")
    ap.add_argument("--schedule", default="GTA 6  /  GAMING  /  IRL  /  NEW CLIPS DAILY")
    ap.add_argument("--only", choices=["banner", "profile"])
    a = ap.parse_args()
    if a.only != "profile":
        banner(a.name, a.mark, a.tagline, a.schedule, HERE / "banner.png")
    if a.only != "banner":
        profile(HERE / "profile_picture.png", HERE / "watermark_150.png")
    print("done")
