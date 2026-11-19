"""Channel art: Vice-City-style night banner + matching profile picture. Original artwork, no Rockstar assets.

  python make_channel_art.py                       writes banner.png and profile_picture.png beside this file
  python make_channel_art.py --name "STREAM HIGHLIGHTS HUB" --tagline "..." --schedule "..." --logo play|five

Drawn at 2x and scaled down for smooth edges. Fonts: Anton + Bebas Neue (SIL Open Font License).
"""
import argparse, math, os, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = Path(__file__).resolve().parent
FONTS = [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts", Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts"]
S = 2  # supersample
MAX_W = 1080  # widest the title may be on the banner (px)


def font(name, px):
    for d in FONTS:
        if (d / name).exists():
            return ImageFont.truetype(str(d / name), int(px * S))
    raise SystemExit(f"font {name} not found")


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def hexc(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def vgrad(w, h, stops):
    """Vertical gradient; stops = [(y_fraction, '#hex'), ...]"""
    img = Image.new("RGBA", (w, h))
    px = img.load()
    cols = [(f, hexc(c)) for f, c in stops]
    for y in range(h):
        f = y / (h - 1)
        for i in range(len(cols) - 1):
            if cols[i][0] <= f <= cols[i + 1][0]:
                t = (f - cols[i][0]) / max(1e-6, cols[i + 1][0] - cols[i][0])
                c = lerp(cols[i][1], cols[i + 1][1], t)
                break
        else:
            c = cols[-1][1] if f > cols[-1][0] else cols[0][1]
        for x in range(w):
            px[x, y] = c
    return img


def star_pts(cx, cy, r, inner=0.45, rot=-90):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * inner
        a = math.radians(rot + i * 36)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def striped_sun(size, top="#ffe45c", bottom="#ff3d7f", stripes=10):
    """Retro sun: gradient disc, lower half cut by horizontal gaps that widen toward the bottom."""
    d = size
    sun = vgrad(d, d, [(0, top), (0.55, "#ff9a3c"), (1, bottom)])
    mask = Image.new("L", (d, d), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([0, 0, d - 1, d - 1], fill=255)
    for i in range(stripes):
        t = i / stripes
        y = d * (0.27 + 0.73 * t)
        gap = d * (0.006 + 0.028 * t)
        md.rectangle([0, y, d, y + gap], fill=0)
    sun.putalpha(mask)
    return sun


def palm(draw, base, top, lean, fronds=7, scale=1.0, color=(8, 3, 14, 255), seed=1):
    """Palm silhouette: tapered curved trunk + drooping serrated fronds."""
    rnd = random.Random(seed)
    (bx, by), (tx, ty) = base, top
    cx, cy = (bx + tx) / 2 + lean, (by + ty) / 2
    pts_l, pts_r = [], []
    N = 60
    for i in range(N + 1):
        t = i / N
        x = (1 - t) ** 2 * bx + 2 * (1 - t) * t * cx + t * t * tx
        y = (1 - t) ** 2 * by + 2 * (1 - t) * t * cy + t * t * ty
        dx = 2 * (1 - t) * (cx - bx) + 2 * t * (tx - cx)
        dy = 2 * (1 - t) * (cy - by) + 2 * t * (ty - cy)
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        w = (26 - 14 * t) * scale * S * (1.06 if i % 6 < 3 else 1.0)   # ring bumps
        pts_l.append((x + nx * w, y + ny * w))
        pts_r.append((x - nx * w, y - ny * w))
    draw.polygon(pts_l + pts_r[::-1], fill=color)
    # crown
    draw.ellipse([tx - 20 * scale * S, ty - 14 * scale * S, tx + 20 * scale * S, ty + 14 * scale * S], fill=color)
    for k in range(fronds):
        ang = math.radians(-198 + k * (216 / (fronds - 1)) + rnd.uniform(-8, 8))
        if -105 < math.degrees(ang) < -75:
            ang += math.radians(28 if rnd.random() < 0.5 else -28)
        length = rnd.uniform(270, 360) * scale * S
        droop = rnd.uniform(0.45, 0.8)
        ex = tx + math.cos(ang) * length
        ey = ty + math.sin(ang) * length * 0.55 + length * droop
        mx = tx + math.cos(ang) * length * 0.55
        my = ty + math.sin(ang) * length * 0.55 - length * 0.12
        top_side, bot_side = [], []
        M = 38
        for i in range(M + 1):
            t = i / M
            x = (1 - t) ** 2 * tx + 2 * (1 - t) * t * mx + t * t * ex
            y = (1 - t) ** 2 * ty + 2 * (1 - t) * t * my + t * t * ey
            dx = 2 * (1 - t) * (mx - tx) + 2 * t * (ex - mx)
            dy = 2 * (1 - t) * (my - ty) + 2 * t * (ey - my)
            L = math.hypot(dx, dy) or 1
            nx, ny = -dy / L, dx / L
            w = math.sin(math.pi * min(1, t * 1.1)) * 26 * scale * S + 2
            jag = 1.0 if i % 2 == 0 else 0.7           # leaflets
            top_side.append((x + nx * w * jag, y + ny * w * jag))
            bot_side.append((x - nx * w * 0.55 * jag, y - ny * w * 0.55 * jag))
        draw.polygon(top_side + bot_side[::-1], fill=color)


def skyline(draw, W, horizon, rnd, low_zone=None, color=(12, 5, 22, 255), tall=190, low=55):
    x = 0
    while x < W:
        bw = rnd.randint(28, 90) * S
        hmax = tall
        if low_zone and low_zone[0] * S < x < low_zone[1] * S:
            hmax = low
        bh = rnd.randint(20, hmax) * S
        draw.rectangle([x, horizon - bh, x + bw, horizon], fill=color)
        if rnd.random() < 0.25 and bh > 80 * S:                    # antenna
            draw.rectangle([x + bw // 2 - S, horizon - bh - 30 * S, x + bw // 2 + S, horizon - bh], fill=color)
        for wy in range(int(horizon - bh + 10 * S), int(horizon - 6 * S), 14 * S):   # a few lit windows
            for wx in range(int(x + 6 * S), int(x + bw - 6 * S), 12 * S):
                if rnd.random() < 0.07:
                    c = rnd.choice([(255, 120, 170, 200), (255, 210, 120, 200), (90, 230, 255, 180)])
                    draw.rectangle([wx, wy, wx + 4 * S, wy + 5 * S], fill=c)
        x += bw + rnd.randint(0, 6) * S


def text_with_effects(base, xy, text, fnt, fill, shadow=(26, 6, 38, 255), off=(7, 7), glow=None, shear=0.0, anchor="ls", tracking=0):
    W, H = base.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if tracking:
        x, y = xy
        for ch in text:
            d.text((x, y), ch, font=fnt, fill=fill, anchor=anchor)
            x += d.textlength(ch, font=fnt) + tracking * S
    else:
        d.text(xy, text, font=fnt, fill=fill, anchor=anchor)
    if shear:
        cy = xy[1]
        layer = layer.transform(layer.size, Image.AFFINE, (1, shear, -shear * cy, 0, 1, 0), resample=Image.BICUBIC)
    alpha = layer.getchannel("A")
    if glow:
        g = Image.new("RGBA", (W, H), glow[:3] + (0,))
        g.putalpha(alpha.filter(ImageFilter.GaussianBlur(glow[3] * S)).point(lambda v: int(v * 0.85)))
        base.alpha_composite(g)
    if shadow:
        sh = Image.new("RGBA", (W, H), shadow[:3] + (0,))
        sh.putalpha(alpha)
        base.alpha_composite(sh, (off[0] * S, off[1] * S))
    base.alpha_composite(layer)
    return alpha.getbbox()


def hud_stars(draw, x, y, r, n=5, gap=12):
    """Wanted-level row: white stars, black outline."""
    for i in range(n):
        cx = x + r + i * (2 * r + gap * S)
        pts = star_pts(cx, y, r)
        draw.polygon(pts, fill=(0, 0, 0, 255))
        draw.polygon(star_pts(cx, y, r - 4.5 * S), fill=(255, 255, 255, 255))


def grain(img, amount=10, seed=3):
    noise = Image.effect_noise(img.size, amount).convert("L")
    n = Image.merge("RGBA", (noise, noise, noise, Image.new("L", img.size, 14)))
    out = img.copy()
    out = ImageChops.overlay(out.convert("RGB"), Image.merge("RGB", (noise, noise, noise))).convert("RGBA")
    return Image.blend(img, out, 0.06)


def banner(name, tagline, schedule, path):
    W, H = 2048 * S, 1152 * S
    HZ = 742 * S                                   # horizon: bottom edge of the always-visible strip
    img = vgrad(W // 8, H // 8, [(0, "#05040f"), (0.28, "#140a33"), (0.40, "#3a1258"), (0.50, "#8e2268"),
                                  (0.58, "#e8435f"), (0.635, "#ff8a55"), (0.66, "#ffc070"), (0.661, "#120818"), (1, "#05030a")])
    img = img.resize((W, H), Image.BICUBIC)
    d = ImageDraw.Draw(img)
    rnd = random.Random(7)
    for _ in range(140):                           # faint sky stars
        x, y = rnd.randint(0, W), rnd.randint(0, int(H * 0.45))
        r = rnd.choice([1, 1, 1, 2]) * S
        a = rnd.randint(60, 180)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a))
    # sun + glow, right of the title
    sx, sr = 1520 * S, 215 * S
    SY = HZ - 30 * S
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([sx - sr * 1.7, SY - sr * 1.7, sx + sr * 1.7, SY + sr * 1.7], fill=(255, 70, 130, 120))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(70 * S)))
    sun = striped_sun(2 * sr)
    img.alpha_composite(sun, (int(sx - sr), int(SY - sr)))
    # water below the horizon: cover the lower half of the sun, add reflection streaks
    d = ImageDraw.Draw(img)
    water = vgrad(W // 8, (H - HZ) // 8 + 1, [(0, "#1a0a26"), (1, "#05030a")]).resize((W, H - HZ), Image.BICUBIC)
    img.alpha_composite(water, (0, HZ))
    d = ImageDraw.Draw(img)
    for i in range(14):
        y = HZ + (8 + i * i * 2.2) * S
        half = (150 - i * 9) * S
        a = max(30, 200 - i * 13)
        d.rectangle([sx - half, y, sx + half, y + (2 + i * 0.3) * S], fill=(255, 120, 120, a))
    skyline(d, W, HZ, random.Random(11), low_zone=(430, 1720))
    d.rectangle([0, HZ, W, HZ + 2 * S], fill=(255, 120, 150, 120))           # thin neon horizon line
    # palms (frame the strip, crowns inside it on desktop)
    p = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(p)
    palm(pd, (230 * S, H + 40 * S), (300 * S, 455 * S), lean=-60 * S, scale=1.0, seed=2)
    palm(pd, (60 * S, H + 40 * S), (20 * S, 560 * S), lean=40 * S, scale=0.8, seed=5)
    palm(pd, (1930 * S, H + 40 * S), (1840 * S, 470 * S), lean=70 * S, scale=0.9, seed=3)
    palm(pd, (2010 * S, H + 40 * S), (2040 * S, 585 * S), lean=-30 * S, scale=0.75, seed=9)
    img.alpha_composite(p)
    # wanted-level HUD stars + type, left block
    tx = 440 * S
    d = ImageDraw.Draw(img)
    hud_stars(d, tx, 448 * S, 22 * S)
    # title: shrink to fit MAX_W; the last word is drawn in the accent yellow
    size = 132
    while size > 70 and (font("Anton-Regular.ttf", size).getlength(name) / S + 4 * len(name)) > MAX_W:
        size -= 2
    title_f = font("Anton-Regular.ttf", size)
    words = name.split(" ")
    head, last = (" ".join(words[:-1]) + " ", words[-1]) if len(words) > 1 else ("", name)
    if head:
        text_with_effects(img, (tx, 600 * S), head, title_f, (255, 255, 255, 255), off=(6, 6),
                          glow=(255, 60, 140, 255, 26), shear=-0.14, tracking=4)
    hx = tx + title_f.getlength(head) + 4 * S * len(head)
    text_with_effects(img, (hx, 600 * S), last, title_f, (255, 214, 110, 255), off=(6, 6),
                      glow=(255, 60, 140, 255, 26), shear=-0.14, tracking=4)
    text_with_effects(img, (tx + 4 * S, 655 * S), tagline, font("BebasNeue-Regular.ttf", 54), (255, 222, 234, 255),
                      shadow=(20, 4, 30, 255), off=(3, 3), tracking=6)
    text_with_effects(img, (tx + 4 * S, 703 * S), schedule, font("BebasNeue-Regular.ttf", 38), (255, 255, 255, 230),
                      shadow=(20, 4, 30, 255), off=(2, 2), tracking=7)
    img = grain(img)
    img.resize((2048, 1152), Image.LANCZOS).convert("RGB").save(path, optimize=True)


def profile(path, logo="play"):
    D = 800 * S
    img = vgrad(D // 4, D // 4, [(0, "#0a0720"), (0.35, "#3a1056"), (0.58, "#b02a6c"), (0.68, "#ff7a5a"), (0.681, "#140a1e"), (1, "#05030a")]).resize((D, D), Image.BICUBIC)
    HZ = int(D * 0.68)
    sr = int(D * 0.27)
    sun = striped_sun(2 * sr, stripes=6)
    img.alpha_composite(sun, (D // 2 - sr, HZ - sr))
    water = vgrad(10, (D - HZ) // 4 + 1, [(0, "#1a0a26"), (1, "#05030a")]).resize((D, D - HZ), Image.BICUBIC)
    img.alpha_composite(water, (0, HZ))
    d = ImageDraw.Draw(img)
    for i in range(8):
        y = HZ + (6 + i * i * 3) * S
        half = (190 - i * 18) * S
        d.rectangle([D // 2 - half, y, D // 2 + half, y + (3 + i * 0.4) * S], fill=(255, 120, 120, max(40, 200 - i * 20)))
    skyline(d, D, HZ, random.Random(4), low_zone=(170, 640), tall=120, low=40)
    p = Image.new("RGBA", (D, D), (0, 0, 0, 0))
    palm(ImageDraw.Draw(p), (60 * S, D + 30 * S), (95 * S, 380 * S), lean=-30 * S, scale=0.6, seed=2)
    palm(ImageDraw.Draw(p), (750 * S, D + 30 * S), (715 * S, 410 * S), lean=30 * S, scale=0.55, seed=3)
    img.alpha_composite(p)
    if logo == "five":
        text_with_effects(img, (D // 2 - 8 * S, 585 * S), "5", font("Anton-Regular.ttf", 400), (255, 255, 255, 255),
                          off=(10, 10), glow=(255, 60, 140, 255, 30), shear=-0.12, anchor="ms")
        d = ImageDraw.Draw(img)
        r, gap = 28 * S, 10
        hud_stars(d, D // 2 - (5 * 2 * r + 4 * gap * S) // 2, 190 * S, r, n=5, gap=gap)
    else:
        # play button: rounded white triangle with a dark offset shadow and pink glow, "HUB" under it
        cx, cy, R = D // 2 + 22 * S, 340 * S, 170 * S
        tri = [(cx - R * 0.62, cy - R * 0.95), (cx + R * 1.0, cy), (cx - R * 0.62, cy + R * 0.95)]
        def tri_layer(col, dx=0, dy=0):
            L = Image.new("RGBA", (D, D), (0, 0, 0, 0))
            ImageDraw.Draw(L).polygon([(x + dx, y + dy) for x, y in tri], fill=col)
            return L.filter(ImageFilter.GaussianBlur(9 * S)).point(lambda v: v) if False else L
        g = Image.new("RGBA", (D, D), (255, 60, 140, 0))
        m = Image.new("L", (D, D), 0); ImageDraw.Draw(m).polygon(tri, fill=255)
        g.putalpha(m.filter(ImageFilter.GaussianBlur(34 * S)).point(lambda v: int(v * 0.9)))
        img.alpha_composite(g)
        img.alpha_composite(tri_layer((26, 6, 38, 255), 12 * S, 12 * S))
        # rounded corners: draw the triangle with a thick round-joined outline in the same white
        L = Image.new("RGBA", (D, D), (0, 0, 0, 0)); ld = ImageDraw.Draw(L)
        ld.polygon(tri, fill=(255, 255, 255, 255))
        ld.line(tri + [tri[0]], fill=(255, 255, 255, 255), width=int(34 * S), joint="curve")
        for x, y in tri:
            ld.ellipse([x - 17 * S, y - 17 * S, x + 17 * S, y + 17 * S], fill=(255, 255, 255, 255))
        img.alpha_composite(L)
        text_with_effects(img, (D // 2, 720 * S), "HUB", font("Anton-Regular.ttf", 165), (255, 214, 110, 255),
                          off=(7, 7), glow=(255, 60, 140, 255, 22), shear=-0.12, anchor="ms", tracking=0)
    img = grain(img)
    img.resize((800, 800), Image.LANCZOS).convert("RGB").save(path, optimize=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="STREAM HIGHLIGHTS HUB")
    ap.add_argument("--tagline", default="GTA 6 STREAMER MOMENTS, ALL IN ONE PLACE")
    ap.add_argument("--schedule", default="NEW CLIPS EVERY DAY  ·  BEST-OF COMPILATIONS")
    ap.add_argument("--logo", choices=["play", "five"], default="play", help="profile picture: play button + HUB, or the old big 5")
    ap.add_argument("--only", choices=["banner", "profile"])
    a = ap.parse_args()
    if a.only != "profile":
        banner(a.name, a.tagline, a.schedule, HERE / "banner.png")
    if a.only != "banner":
        profile(HERE / "profile_picture.png", a.logo)
    print("done")
