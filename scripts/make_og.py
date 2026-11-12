#!/usr/bin/env python3
"""Fixed 1200x630 text share card -> og.jpg. No post images are used. Run once (or when the wording changes)."""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
W, H = 1200, 630
BG, FG, MUTED, ACCENT = (11, 11, 13), (236, 235, 232), (154, 151, 143), (216, 195, 165)


def font(path, size, idx=2):  # index 2 = SC in the Noto CJK collections
    try:
        return ImageFont.truetype(path, size, index=idx)
    except Exception:
        return ImageFont.truetype(path, size)


def center(d, y, text, f, fill):
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, font=f, fill=fill)


def main():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([36, 36, W - 37, H - 37], outline=(40, 40, 44), width=1)
    center(d, 150, "AI FASHION PORTRAIT · PORTFOLIO", font(SANS, 22), ACCENT)
    center(d, 205, "YLL·Hara", font(SERIF, 112), FG)
    d.line([(W / 2 - 60, 372), (W / 2 + 60, 372)], fill=ACCENT, width=2)
    center(d, 398, "AI 时尚影像 · AI Fashion Portrait", font(SERIF, 40), FG)
    center(d, 470, "@GenRyoma", font(SANS, 30), MUTED)
    center(d, 548, "yanlvlab.github.io", font(SANS, 20), (110, 108, 102))
    im.save(os.path.join(ROOT, "og.jpg"), quality=92)


if __name__ == "__main__":
    main()
