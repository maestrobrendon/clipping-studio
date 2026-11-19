"""Channel art, concept "chat pop": electric blue, halftone, heavy outlined type with hard shadows,
stream-chat bubbles flying around. Bright, loud, the opposite of the dark control-room version.

  python make_channel_art_pop.py      writes banner.png, profile_picture.png, watermark_150.png into v5_chat_pop/

Fonts: Anton (OFL), Bebas Neue (OFL), Consolas (Windows). Original artwork, no platform logos or emotes.
"""
import math, os, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "v5_chat_pop"
FONTS = [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts", Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts"]
S = 2

BLUE = (43, 46, 255, 255)
BLUE_D = (24, 22, 190, 255)
YEL = (255, 222, 0, 255)
BLK = (12, 12, 18, 255)
WHT = (255, 255, 255, 255)
RED = (255, 52, 70, 255)
NAMECOLS = [(255, 90, 160, 255), (0, 190, 120, 255), (255, 140, 0, 255), (120, 80, 255, 255), (0, 150, 255, 255)]


def font(name, px):
    for d in FONTS:
        if (d / name).exists():
            return ImageFont.truetype(str(d / name), int(px * S))
    raise SystemExit(f"font {name} not found")


def background(W, H):
    small = Image.new("RGBA", (2, 2))
    small.putdata([BLUE, BLUE, BLUE_D, BLUE_D])
    img = small.resize((W, H), Image.BICUBIC)
    # halftone: dot size grows toward the bottom-right corner
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(dots)
    step = 26 * S
    for y in range(0, H + step, step):
        for x in range(0, W + step, step):
            t = min(1, max(0, (x / W) * 0.5 + (y / H) * 0.6 - 0.15))
            r = 1.5 * S + t * 7 * S
            ox = (step // 2) if (y // step) % 2 else 0
            d.ellipse([x + ox - r, y - r, x + ox + r, y + r], fill=(255, 255, 255, 34))
    img.alpha_composite(dots)
    return img


def outlined(img, xy, text, fnt, fill, stroke=6, shadow=12, anchor="ls", rot=0):
    """Text with thick black outline and a hard (unblurred) black offset shadow."""
    W, H = img.size
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    x, y = xy
    if shadow:
        d.text((x + shadow * S, y + shadow * S), text, font=fnt, fill=BLK, anchor=anchor, stroke_width=stroke * S, stroke_fill=BLK)
    d.text((x, y), text, font=fnt, fill=fill, anchor=anchor, stroke_width=stroke * S, stroke_fill=BLK)
    if rot:
        L = L.rotate(rot, center=(x, y), resample=Image.BICUBIC)
    img.alpha_composite(L)
    return d.textbbox((x, y), text, font=fnt, anchor=anchor, stroke_width=stroke * S)


def bubble(img, x, y, user, msg, ucol, scale=1.0, rot=0.0, tail="left"):
    """Chat bubble: white card, black outline, hard shadow, username line + message."""
    uf = font("consolab.ttf", 22 * scale)
    mf = font("Anton-Regular.ttf", 46 * scale)
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    w = max(tmp.textlength(user, font=uf), tmp.textlength(msg, font=mf)) + 52 * S * scale
    h = 112 * S * scale
    pad = 60 * S
    L = Image.new("RGBA", (int(w + 2 * pad), int(h + 2 * pad)), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    bx, by = pad, pad
    sh = 9 * S * scale
    lw = int(5 * S * scale)
    tx = bx + 34 * S * scale if tail == "left" else bx + w - 34 * S * scale
    tri = [(tx - 16 * S * scale, by + h - 4), (tx + 16 * S * scale, by + h - 4), (tx - (22 if tail == "left" else -22) * S * scale, by + h + 30 * S * scale)]
    for off, col in ((sh, BLK), (0, None)):
        d.rounded_rectangle([bx + off, by + off, bx + w + off, by + h + off], 22 * S * scale, fill=BLK if col else WHT,
                            outline=BLK, width=lw)
        d.polygon([(px + off, py + off) for px, py in tri], fill=BLK if col else WHT, outline=BLK)
    d.line([tri[0], tri[2], tri[1]], fill=BLK, width=lw)
    d.rectangle([tri[0][0] + lw, tri[0][1] - lw * 2, tri[1][0] - lw, tri[0][1] + lw // 2], fill=WHT)
    d.text((bx + 26 * S * scale, by + 34 * S * scale), user, font=uf, fill=ucol, anchor="ls")
    d.text((bx + 26 * S * scale, by + 92 * S * scale), msg, font=mf, fill=BLK, anchor="ls")
    L = L.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(L, (int(x - L.width / 2), int(y - L.height / 2)))


def pill(img, cx, cy, text, bg, fg, px=34, rot=0):
    f = font("Anton-Regular.ttf", px)
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    w = tmp.textlength(text, font=f) + 44 * S
    h = px * 1.35 * S
    pad = 30 * S
    L = Image.new("RGBA", (int(w + 2 * pad), int(h + 2 * pad)), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    for off, col in ((7 * S, BLK), (0, bg)):
        d.rounded_rectangle([pad + off, pad + off, pad + w + off, pad + h + off], h / 2, fill=col, outline=BLK, width=4 * S)
    d.text((pad + w / 2, pad + h / 2 + 1 * S), text, font=f, fill=fg, anchor="mm")
    L = L.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(L, (int(cx - L.width / 2), int(cy - L.height / 2)))


def banner(path):
    W, H = 2048 * S, 1152 * S
    img = background(W, H)
    # chat flying in from the sides (outside the text block; partly cropped on mobile, that's fine)
    chats = [
        (250, 330, "clipfarmer", "CLIP IT", -8, "left", 1.0),
        (230, 610, "nightowl_22", "NO WAY", 6, "left", 0.95),
        (300, 860, "modsasleep", "REPLAY THAT", -4, "left", 0.9),
        (1810, 300, "vicecityvibes", "LMAOOO", 7, "right", 1.0),
        (1820, 560, "justchatting", "W STREAM", -6, "right", 0.95),
        (1760, 840, "lurker4life", "CHAT IS THIS REAL", 4, "right", 0.85),
        (760, 190, "speedrunz", "HE DID NOT", -3, "left", 0.8),
        (1300, 960, "gg_ez", "GG", 5, "right", 0.85),
    ]
    for i, (x, y, u, m, r, t, sc) in enumerate(chats):
        bubble(img, x * S, y * S, u, m, NAMECOLS[i % len(NAMECOLS)], scale=sc, rot=r, tail=t)
    # type block, centered in the always-visible strip (y 407..745)
    CX = 1024 * S
    pill(img, CX - 330 * S, 442 * S, "LIVE", RED, WHT, px=30, rot=-4)
    outlined(img, (CX - 250 * S, 458 * S), "BEST MOMENTS, DAILY", font("BebasNeue-Regular.ttf", 46), WHT, stroke=0, shadow=3)
    outlined(img, (CX, 596 * S), "STREAM HIGHLIGHTS", font("Anton-Regular.ttf", 150), WHT, stroke=7, shadow=13, anchor="ms", rot=2)
    # HUB on a yellow block, tilted the other way
    hub_f = font("Anton-Regular.ttf", 92)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    bx0, by0, bx1, by1 = CX - 300 * S, 612 * S, CX - 90 * S, 706 * S
    d.rectangle([bx0 + 10 * S, by0 + 10 * S, bx1 + 10 * S, by1 + 10 * S], fill=BLK)
    d.rectangle([bx0, by0, bx1, by1], fill=YEL, outline=BLK, width=6 * S)
    d.text(((bx0 + bx1) / 2, (by0 + by1) / 2 + 2 * S), "HUB", font=hub_f, fill=BLK, anchor="mm")
    img.alpha_composite(L.rotate(-3, center=((bx0 + bx1) / 2, (by0 + by1) / 2), resample=Image.BICUBIC))
    outlined(img, (CX - 60 * S, 656 * S), "GTA 6  ·  GAMING  ·  IRL", font("BebasNeue-Regular.ttf", 50), YEL, stroke=3, shadow=4)
    outlined(img, (CX - 60 * S, 700 * S), "THE BIGGEST STREAMERS, CLIPPED", font("BebasNeue-Regular.ttf", 36), WHT, stroke=2, shadow=3)
    img.resize((2048, 1152), Image.LANCZOS).convert("RGB").save(path, optimize=True)


def profile(path, wm):
    D = 800 * S
    img = background(D, D)
    # one big chat bubble with a play button inside
    L = Image.new("RGBA", (D, D), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    x0, y0, x1, y1 = 150 * S, 175 * S, 650 * S, 560 * S
    tail = [(260 * S, 540 * S), (360 * S, 540 * S), (215 * S, 660 * S)]
    sh = 18 * S
    for off, col in ((sh, BLK), (0, YEL)):
        d.rounded_rectangle([x0 + off, y0 + off, x1 + off, y1 + off], 70 * S, fill=col, outline=BLK, width=14 * S)
        d.polygon([(a + off, b + off) for a, b in tail], fill=col, outline=BLK)
    d.line([tail[0], tail[2], tail[1]], fill=BLK, width=14 * S, joint="curve")
    d.rectangle([tail[0][0] + 10 * S, tail[0][1] - 20 * S, tail[1][0] - 10 * S, tail[0][1] + 4 * S], fill=YEL)
    cx, cy, R = (x0 + x1) / 2 + 20 * S, (y0 + y1) / 2, 120 * S
    tri = [(cx - R * 0.62, cy - R * 0.95), (cx + R, cy), (cx - R * 0.62, cy + R * 0.95)]
    d.polygon(tri, fill=BLK)
    d.line(tri + [tri[0]], fill=BLK, width=28 * S, joint="curve")
    for a, b in tri:
        d.ellipse([a - 14 * S, b - 14 * S, a + 14 * S, b + 14 * S], fill=BLK)
    img.alpha_composite(L.rotate(-5, center=(D / 2, D / 2), resample=Image.BICUBIC))
    pill(img, 600 * S, 200 * S, "LIVE", RED, WHT, px=44, rot=10)
    out = img.resize((800, 800), Image.LANCZOS).convert("RGB")
    out.save(path, optimize=True)
    out.resize((150, 150), Image.LANCZOS).save(wm)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    banner(OUT / "banner.png")
    profile(OUT / "profile_picture.png", OUT / "watermark_150.png")
    print("done")
