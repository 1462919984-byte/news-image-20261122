#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make.fun news-image entry: one newspaper front page summing up world news
for Sunday 22 November 2026, drawn entirely with the Python PIL library.

The program is fully deterministic.  It never reads the clock, never touches
the network and never uses random numbers: every pixel is computed from the
fixed story data below, so running it twice always produces byte-identical
output.  It uses only PIL's built-in default font at several sizes (never a
font file) and only PIL's basic shapes for every illustration.
"""

import os
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Page geometry: the whole page is a square 1024 by 1024 pixels.
# ---------------------------------------------------------------------------
W = 1024            # page width in pixels
H = 1024            # page height in pixels
MARGIN = 28         # outer margin so ink never touches the page edge
CW = W - 2 * MARGIN  # usable content width inside the two side margins

# ---------------------------------------------------------------------------
# Palette: a pale paper ground, dark ink, a deep red accent, and a few
# supporting tints used by the small drawings and the world map.
# ---------------------------------------------------------------------------
PAPER = (246, 241, 227)     # warm pale paper, the page background
INK = (28, 26, 22)          # near-black ink for body text and rules
RED = (166, 28, 34)         # the single deep red accent colour
MID = (88, 82, 72)          # softer grey-ink for secondary lines
RULE = (72, 66, 56)         # colour of the heavy double rules
SEA = (219, 230, 236)       # pale blue for the map ocean
LAND = (210, 217, 192)      # pale green for map continents
CARD = (243, 238, 222)      # slightly lighter paper for panels and boxes
GRID = (204, 211, 218)      # faint grid lines on the map

# ---------------------------------------------------------------------------
# A tiny font cache so every size of the built-in default font is created
# exactly once and reused.  This also keeps the drawing fast and consistent.
# ---------------------------------------------------------------------------
_FONT_CACHE = {}


def F(size):
    """Return PIL's built-in default font at the requested pixel size."""
    if size not in _FONT_CACHE:
        _FONT_CACHE[size] = ImageFont.load_default(size=size)
    return _FONT_CACHE[size]


# ---------------------------------------------------------------------------
# Text measuring helpers.  The brief demands that no line of text ever spills
# over a panel edge, so every string is measured before it is placed.
# ---------------------------------------------------------------------------
def text_wh(txt, size):
    """Return (width, height, top, bottom) for a string at a font size.

    'top' and 'bottom' come from the glyph bounding box and let us place the
    visible top of the text exactly, instead of guessing a baseline.
    """
    f = F(size)
    b = f.getbbox(txt)
    return (b[2] - b[0], b[3] - b[1], b[1], b[3])


def tw(txt, size):
    """Return just the rendered width of a string at a font size."""
    return F(size).getlength(txt)


def wrap(txt, size, maxw):
    """Greedily wrap words so no rendered line is wider than maxw."""
    f = F(size)
    words = txt.split()
    lines = []
    cur = ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if cur == "" or f.getlength(trial) <= maxw:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def fit_lines(txt, size, maxw, maxlines):
    """Wrap text to at most maxlines lines, shrinking the font until it fits."""
    s = size
    while s >= 6:
        lines = wrap(txt, s, maxw)
        if len(lines) <= maxlines:
            return lines, s
        s -= 1
    return wrap(txt, s, maxw), s


def fit_one(txt, size, maxw):
    """Shrink a single line of text until it fits within maxw pixels."""
    s = size
    while s >= 6 and tw(txt, s) > maxw:
        s -= 1
    return s


def fit_one_tiny(txt, size, maxw):
    """Like fit_one but may shrink as far as 4px for the dense briefs."""
    s = size
    while s >= 4 and tw(txt, s) > maxw:
        s -= 1
    return s


# ---------------------------------------------------------------------------
# Small drawing helpers shared by every section of the page.
# ---------------------------------------------------------------------------
# Text is positioned by its visible top edge here, not by a guessed baseline.
def draw_centered(dr, cx, ytop, txt, size, fill):
    """Draw text so its visible top sits at ytop and it is centred on cx."""
    w, h, top, _ = text_wh(txt, size)
    dr.text((int(cx - w / 2), int(ytop - top)), txt, font=F(size), fill=fill)


def draw_left(dr, x, ytop, txt, size, fill):
    """Draw text with its visible top at ytop, anchored to the left edge x."""
    _, _, top, _ = text_wh(txt, size)
    dr.text((int(x), int(ytop - top)), txt, font=F(size), fill=fill)


def draw_right(dr, xr, ytop, txt, size, fill):
    """Draw text right-aligned so its right edge ends at xr."""
    w, _, top, _ = text_wh(txt, size)
    dr.text((int(xr - w), int(ytop - top)), txt, font=F(size), fill=fill)


def draw_italic_center(dr, img, cx, ytop, txt, size, fill):
    """Draw a sheared (fake italic) line centred on cx at visual top ytop.

    The built-in default font has no true italic face, so we render the text
    to a small transparent canvas, shear that canvas, and paste it back.  The
    shear amount is a fixed constant, so the result stays deterministic.
    """
    f = F(size)
    w = f.getlength(txt)
    b = f.getbbox(txt)
    asc = -b[1]
    # Give the temporary canvas a little breathing room for the shear.
    pad = int(size * 0.35) + 4
    tmp = Image.new("RGBA", (int(w) + pad * 2, int(size) + pad * 2), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    td.text((pad, pad + asc), txt, font=f, fill=(fill[0], fill[1], fill[2], 255))
    # Shear the canvas slightly to the right to fake an italic slant.
    sheared = tmp.transform(
        tmp.size, Image.Transform.AFFINE, (1, 0, -0.26, 0, 1, 0),
        resample=Image.Resampling.BICUBIC)
    sw, sh = sheared.size
    # The shear moves pixels left, so compensate a touch before pasting.
    img.paste(sheared, (int(cx - sw / 2) + int(size * 0.13), int(ytop)), sheared)


# One shared rule keeps every divider on the page at the same weight and colour.
def hrule(dr, y, x0=MARGIN, x1=W - MARGIN, thick=3, fill=RULE):
    """Draw one horizontal rule between x0 and x1 at height y."""
    dr.rectangle([x0, y, x1, y + thick], fill=fill)


def red_banner(dr, x, y, w, h, txt, size=11):
    """Draw the bold red subject banner that tops each feature drawing."""
    dr.rectangle([x, y, x + w, y + h], fill=RED)
    draw_centered(dr, x + w / 2, y + h / 2 - (size * 0.55), txt, size, (255, 255, 255))


# ---------------------------------------------------------------------------
# The fourteen feature-story drawings.  Each is built only from rectangles,
# ellipses, lines, arcs and polygons so it is an original, code-only picture.
# ---------------------------------------------------------------------------

def drw_cop31(dr, x, y, w, h):
    """COP31: a globe with a blank, crossed-out treaty page beside it."""
    cx, cy = x + w * 0.40, y + h * 0.55
    r = int(h * 0.34)
    # A pale globe with a green-blue ocean and ink meridian lines.
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=INK, width=2, fill=(196, 214, 208))
    dr.ellipse([cx - r * 0.45, cy - r, cx - r * 0.45, cy + r], outline=INK, width=1)
    dr.ellipse([cx + r * 0.45, cy - r, cx + r * 0.45, cy + r], outline=INK, width=1)
    dr.line([cx - r, cy, cx + r, cy], fill=INK, width=1)
    dr.line([cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7], fill=INK, width=1)
    # A small sun in the corner suggests the warm climate summit city.
    dr.ellipse([x + w * 0.04, y + h * 0.04, x + w * 0.16, y + h * 0.2], fill=(238, 190, 70), outline=INK, width=1)
    # A torn treaty page beside the globe, crossed out to mean 'no deal'.
    px = x + w * 0.70
    dr.rectangle([px - w * 0.15, y + h * 0.26, px + w * 0.15, y + h * 0.76], fill=(252, 248, 234), outline=INK, width=2)
    dr.line([px - w * 0.11, y + h * 0.38, px + w * 0.11, y + h * 0.38], fill=INK, width=1)
    dr.line([px - w * 0.11, y + h * 0.50, px + w * 0.11, y + h * 0.50], fill=INK, width=1)
    # A jagged tear on the page edge makes the empty deal feel broken.
    dr.polygon([(px + w * 0.15, y + h * 0.28), (px + w * 0.23, y + h * 0.32),
                (px + w * 0.15, y + h * 0.36)], fill=PAPER, outline=INK, width=1)
    # Two red slashes over the page mark the rejected draft.
    dr.line([px - w * 0.13, y + h * 0.32, px + w * 0.13, y + h * 0.66], fill=RED, width=4)
    dr.line([px - w * 0.13, y + h * 0.66, px + w * 0.13, y + h * 0.32], fill=RED, width=4)


def drw_bahrain(dr, x, y, w, h):
    """Bahrain: a struck oil tank with a rising plume of smoke and flame."""
    ground = y + h * 0.82
    dr.line([x + w * 0.05, ground, x + w * 0.95, ground], fill=INK, width=2)
    # Two storage tanks sit on the low ground line.
    dr.rectangle([x + w * 0.07, y + h * 0.52, x + w * 0.37, y + h * 0.82], fill=(182, 168, 146), outline=INK, width=2)
    dr.ellipse([x + w * 0.07, y + h * 0.46, x + w * 0.37, y + h * 0.58], fill=(158, 146, 126), outline=INK, width=2)
    dr.rectangle([x + w * 0.52, y + h * 0.58, x + w * 0.82, y + h * 0.82], fill=(182, 168, 146), outline=INK, width=2)
    dr.ellipse([x + w * 0.52, y + h * 0.52, x + w * 0.82, y + h * 0.64], fill=(158, 146, 126), outline=INK, width=2)
    # A bright flame licks up from the first tank.
    dr.polygon([(x + w * 0.22, y + h * 0.46), (x + w * 0.29, y + h * 0.22),
                (x + w * 0.35, y + h * 0.34), (x + w * 0.31, y + h * 0.16),
                (x + w * 0.21, y + h * 0.46)], fill=(232, 118, 40))
    dr.polygon([(x + w * 0.23, y + h * 0.44), (x + w * 0.28, y + h * 0.28),
                (x + w * 0.30, y + h * 0.44)], fill=(255, 190, 60))
    # Smoke puffs float upward and to the right of the fire.
    dr.ellipse([x + w * 0.26, y + h * 0.10, x + w * 0.36, y + h * 0.22], fill=(120, 118, 112))
    dr.ellipse([x + w * 0.40, y + h * 0.08, x + w * 0.52, y + h * 0.20], fill=(104, 102, 98))
    dr.ellipse([x + w * 0.54, y + h * 0.14, x + w * 0.66, y + h * 0.26], fill=(88, 86, 82))


def drw_kyiv(dr, x, y, w, h):
    """Kyiv: a five-storey apartment block with a drone and a broken side."""
    bx, by = x + w * 0.08, y + h * 0.40
    bw, bh = w * 0.84, h * 0.46
    # The intact part of the block is a pale wall with rows of windows.
    dr.rectangle([bx, by, bx + bw, by + bh], fill=(206, 186, 160), outline=INK, width=2)
    for rrow in range(4):
        for col in range(5):
            wx = bx + bw * 0.06 + col * (bw / 5)
            wy = by + bh * 0.10 + rrow * (bh / 4)
            dr.rectangle([wx, wy, wx + bw * 0.09, wy + bh * 0.13], fill=(90, 80, 68))
    # The right-hand side of the block collapses into a ragged rubble slope.
    dr.polygon([(bx + bw * 0.78, by), (bx + bw, by), (bx + bw, by + bh),
                (bx + bw * 0.78, by + bh * 0.55), (bx + bw * 0.70, by + bh * 0.40),
                (bx + bw * 0.62, by + bh), (bx + bw * 0.78, by + bh)],
               fill=(150, 132, 108), outline=INK, width=2)
    # Loose rubble chunks spill out at the base of the wall.
    dr.ellipse([x + w * 0.5, y + h * 0.82, x + w * 0.95, y + h * 0.95], fill=(128, 112, 92), outline=INK, width=1)
    # A small quadcopter drone hovers above the roof.
    dx, dy = x + w * 0.40, y + h * 0.18
    dr.ellipse([dx - w * 0.09, dy - h * 0.04, dx + w * 0.09, dy + h * 0.05], fill=(70, 70, 66), outline=INK, width=1)
    dr.line([dx - w * 0.16, dy, dx - w * 0.05, dy], fill=INK, width=1)
    dr.line([dx + w * 0.05, dy, dx + w * 0.16, dy], fill=INK, width=1)
    dr.line([dx, dy - h * 0.11, dx, dy - h * 0.02], fill=INK, width=1)
    # A red explosion flash at the broken corner ties the drone to the damage.
    dr.polygon([(bx + bw * 0.60, by + bh * 0.28), (bx + bw * 0.76, by + bh * 0.08),
                (bx + bw * 0.93, by + bh * 0.33), (bx + bw * 0.76, by + bh * 0.52)],
               fill=RED)


def drw_sparta(dr, x, y, w, h):
    """Baltic Sea: a cargo ship on waves with a fire on its deck."""
    sea = y + h * 0.72
    # Rolling waves under the hull.
    for i in range(3):
        dr.arc([x + w * 0.04 + i * w * 0.30, sea - h * 0.12,
                x + w * 0.34 + i * w * 0.30, sea + h * 0.12], 180, 360, fill=INK, width=2)
    # The hull is a long dark polygon with a red waterline stripe.
    dr.polygon([(x + w * 0.08, sea), (x + w * 0.20, sea - h * 0.36),
                (x + w * 0.76, sea - h * 0.36), (x + w * 0.92, sea),
                (x + w * 0.82, sea + h * 0.02), (x + w * 0.18, sea + h * 0.02)],
               fill=(84, 80, 72), outline=INK, width=2)
    dr.line([x + w * 0.20, sea - h * 0.26, x + w * 0.76, sea - h * 0.26], fill=RED, width=4)
    # A small superstructure and funnel sit near the stern.
    dr.rectangle([x + w * 0.56, sea - h * 0.52, x + w * 0.70, sea - h * 0.36], fill=(120, 116, 106), outline=INK, width=2)
    dr.rectangle([x + w * 0.60, sea - h * 0.58, x + w * 0.66, sea - h * 0.52], fill=(70, 70, 66), outline=INK, width=1)
    # Flames rise from the deck amidships.
    dr.polygon([(x + w * 0.34, sea - h * 0.36), (x + w * 0.42, sea - h * 0.64),
                (x + w * 0.48, sea - h * 0.48), (x + w * 0.44, sea - h * 0.36)],
               fill=(232, 118, 40))
    dr.polygon([(x + w * 0.36, sea - h * 0.36), (x + w * 0.40, sea - h * 0.52),
                (x + w * 0.44, sea - h * 0.36)], fill=(255, 190, 60))
    # A second smaller flame at the stern joins the first.
    dr.polygon([(x + w * 0.62, sea - h * 0.52), (x + w * 0.66, sea - h * 0.70),
                (x + w * 0.70, sea - h * 0.52)], fill=(232, 118, 40))


def drw_bear(dr, x, y, w, h):
    """Bear market: a falling price line and a big red down arrow."""
    # A small grid suggests a trading chart behind the line.
    for i in range(4):
        dr.line([x + w * 0.06, y + h * (0.20 + i * 0.18), x + w * 0.68, y + h * (0.20 + i * 0.18)], fill=GRID, width=1)
    # Candle sticks; several are red to show a slide.
    candles = [(0.16, 0.28, 0.50, 0.42, False), (0.30, 0.30, 0.60, 0.50, True),
               (0.44, 0.42, 0.72, 0.60, True), (0.58, 0.54, 0.80, 0.74, True)]
    for cx, top, bot, hi, down in candles:
        dr.line([x + w * cx, y + h * top, x + w * cx, y + h * bot], fill=INK, width=1)
        col = RED if down else (120, 160, 120)
        dr.rectangle([x + w * (cx - 0.045), y + h * top, x + w * (cx + 0.045), y + h * hi],
                     fill=col, outline=INK, width=1)
    # The steep falling trend line across the chart.
    dr.line([x + w * 0.10, y + h * 0.24, x + w * 0.66, y + h * 0.76], fill=INK, width=3)
    # A heavy red arrow (shaft plus triangle head) emphasises the drop.
    dr.rectangle([x + w * 0.74, y + h * 0.30, x + w * 0.82, y + h * 0.78], fill=RED)
    dr.polygon([(x + w * 0.70, y + h * 0.20), (x + w * 0.86, y + h * 0.20),
                (x + w * 0.78, y + h * 0.42)], fill=RED)
    dr.polygon([(x + w * 0.70, y + h * 0.90), (x + w * 0.86, y + h * 0.90),
                (x + w * 0.78, y + h * 0.70)], fill=RED)


def drw_sinaloa(dr, x, y, w, h):
    """Sinaloa: a wanted poster behind bars, now closed with handcuffs."""
    # The poster card sits on the left of the picture.
    dr.rectangle([x + w * 0.10, y + h * 0.10, x + w * 0.58, y + h * 0.90], fill=(250, 246, 232), outline=INK, width=2)
    # A simple face silhouette on the poster.
    dr.ellipse([x + w * 0.24, y + h * 0.20, x + w * 0.44, y + h * 0.42], fill=(150, 132, 108), outline=INK, width=1)
    dr.polygon([(x + w * 0.24, y + h * 0.52), (x + w * 0.44, y + h * 0.52),
                (x + w * 0.44, y + h * 0.72), (x + w * 0.24, y + h * 0.72)], fill=(150, 132, 108))
    # 'WANTED' in red across the poster top.
    draw_centered(dr, x + w * 0.34, y + h * 0.12, "WANTED", 8, RED)
    # Prison bars stand in front of the poster to show the capture.
    for i in range(4):
        dr.line([x + w * (0.58 + i * 0.09), y + h * 0.10, x + w * (0.58 + i * 0.09), y + h * 0.90], fill=INK, width=3)
    # Closed handcuffs to the right of the bars.
    cxx = x + w * 0.80
    dr.ellipse([cxx - w * 0.10, y + h * 0.40, cxx + w * 0.10, y + h * 0.60], outline=INK, width=3)
    dr.ellipse([cxx - w * 0.04, y + h * 0.50, cxx + w * 0.16, y + h * 0.70], outline=INK, width=3)
    dr.line([cxx, y + h * 0.40, cxx + w * 0.03, y + h * 0.50], fill=INK, width=3)


def drw_cikande(dr, x, y, w, h):
    """Cikande: a factory whose roof pours out flame and a thick smoke cloud."""
    # Factory shed with a saw-tooth roof.
    dr.rectangle([x + w * 0.05, y + h * 0.62, x + w * 0.95, y + h * 0.90], fill=(176, 158, 134), outline=INK, width=2)
    for i in range(3):
        sx = x + w * (0.07 + i * 0.28)
        dr.polygon([(sx, y + h * 0.62), (sx + w * 0.14, y + h * 0.46),
                    (sx + w * 0.28, y + h * 0.62)], fill=(150, 132, 108), outline=INK, width=1)
    # Flames leap from the roof ridge.
    dr.polygon([(x + w * 0.38, y + h * 0.44), (x + w * 0.48, y + h * 0.18),
                (x + w * 0.54, y + h * 0.30), (x + w * 0.58, y + h * 0.14),
                (x + w * 0.46, y + h * 0.46)], fill=(232, 118, 40))
    # A layered smoke plume builds into a rising cloud over the roof.
    dr.ellipse([x + w * 0.40, y + h * 0.08, x + w * 0.58, y + h * 0.26], fill=(110, 108, 104))
    dr.ellipse([x + w * 0.54, y + h * 0.02, x + w * 0.72, y + h * 0.20], fill=(94, 92, 88))
    dr.ellipse([x + w * 0.66, y + h * 0.12, x + w * 0.86, y + h * 0.30], fill=(120, 118, 112))


def drw_trade(dr, x, y, w, h):
    """Trade deal: EU and Indonesian flags joined by a signed document."""
    import math
    # EU flag: blue with a ring of small gold stars.
    dr.rectangle([x + w * 0.04, y + h * 0.24, x + w * 0.29, y + h * 0.64], fill=(48, 74, 150), outline=INK, width=2)
    ex, ey = x + w * 0.165, y + h * 0.44
    for a in range(12):
        ang = math.radians(a * 30)
        dr.ellipse([ex + math.cos(ang) * w * 0.06 - w * 0.012, ey + math.sin(ang) * h * 0.08 - w * 0.012,
                    ex + math.cos(ang) * w * 0.06 + w * 0.012, ey + math.sin(ang) * h * 0.08 + w * 0.012],
                   fill=(245, 200, 60))
    # Indonesian flag: red over white.
    dr.rectangle([x + w * 0.73, y + h * 0.24, x + w * 0.98, y + h * 0.64], fill=(235, 235, 235), outline=INK, width=2)
    dr.rectangle([x + w * 0.73, y + h * 0.24, x + w * 0.98, y + h * 0.44], fill=(205, 60, 52))
    # A signed treaty scroll bridges the two flags in the middle.
    dr.rectangle([x + w * 0.36, y + h * 0.30, x + w * 0.66, y + h * 0.58], fill=(252, 248, 234), outline=INK, width=2)
    dr.line([x + w * 0.40, y + h * 0.40, x + w * 0.62, y + h * 0.40], fill=INK, width=1)
    dr.line([x + w * 0.40, y + h * 0.48, x + w * 0.62, y + h * 0.48], fill=INK, width=1)
    # A red seal stamp marks the deal as signed.
    dr.ellipse([x + w * 0.55, y + h * 0.52, x + w * 0.66, y + h * 0.66], fill=RED)


def drw_delta(dr, x, y, w, h):
    """Delta: a jet silhouette beside a clock face showing a delay."""
    # A simple jet drawn from polygons, nose to the left.
    dr.polygon([(x + w * 0.06, y + h * 0.50), (x + w * 0.32, y + h * 0.46),
                (x + w * 0.40, y + h * 0.34), (x + w * 0.48, y + h * 0.44),
                (x + w * 0.60, y + h * 0.42), (x + w * 0.68, y + h * 0.34),
                (x + w * 0.64, y + h * 0.50), (x + w * 0.68, y + h * 0.66),
                (x + w * 0.60, y + h * 0.58), (x + w * 0.48, y + h * 0.56),
                (x + w * 0.40, y + h * 0.66), (x + w * 0.32, y + h * 0.54)],
               fill=(96, 96, 92), outline=INK, width=2)
    # Two wing engines beneath the fuselage.
    dr.ellipse([x + w * 0.42, y + h * 0.60, x + w * 0.48, y + h * 0.70], fill=(70, 70, 66), outline=INK, width=1)
    dr.ellipse([x + w * 0.52, y + h * 0.58, x + w * 0.58, y + h * 0.68], fill=(70, 70, 66), outline=INK, width=1)
    # A clock face on the right, hands pointing to a late hour.
    cxx, cyy = x + w * 0.84, y + h * 0.50
    dr.ellipse([cxx - w * 0.13, cyy - h * 0.20, cxx + w * 0.13, cyy + h * 0.20], fill=(250, 246, 232), outline=INK, width=2)
    dr.line([cxx, cyy, cxx + w * 0.06, cyy - h * 0.12], fill=INK, width=2)
    dr.line([cxx, cyy, cxx - w * 0.05, cyy + h * 0.08], fill=RED, width=2)
    dr.ellipse([cxx - w * 0.015, cyy - h * 0.02, cxx + w * 0.015, cyy + h * 0.02], fill=INK)


def drw_cricket(dr, x, y, w, h):
    """Cricket: bat, ball and stumps for India's record 720 for 9."""
    # Three stumps with bails at the top.
    for i in range(3):
        dr.line([x + w * (0.18 + i * 0.08), y + h * 0.34, x + w * (0.18 + i * 0.08), y + h * 0.70], fill=INK, width=4)
    dr.line([x + w * 0.14, y + h * 0.34, x + w * 0.38, y + h * 0.34], fill=INK, width=3)
    # A cricket bat leans against the stumps.
    dr.polygon([(x + w * 0.42, y + h * 0.22), (x + w * 0.52, y + h * 0.22),
                (x + w * 0.60, y + h * 0.84), (x + w * 0.48, y + h * 0.88)],
               fill=(196, 148, 86), outline=INK, width=2)
    dr.line([x + w * 0.46, y + h * 0.22, x + w * 0.53, y + h * 0.84], fill=INK, width=2)
    # A red cricket ball with a white seam.
    ballx, bally = x + w * 0.76, y + h * 0.54
    dr.ellipse([ballx - w * 0.09, bally - h * 0.12, ballx + w * 0.09, bally + h * 0.12], fill=RED, outline=INK, width=2)
    dr.line([ballx - w * 0.06, bally - h * 0.06, ballx + w * 0.06, bally + h * 0.06], fill=(255, 255, 255), width=2)


def drw_leeds(dr, x, y, w, h):
    """Leeds: a goal net and a football for the 4-1 win in London."""
    # Green pitch rectangle as the backdrop.
    dr.rectangle([x + w * 0.04, y + h * 0.18, x + w * 0.96, y + h * 0.90], fill=(116, 156, 104), outline=INK, width=2)
    # Goal frame and a cross-hatched net.
    dr.rectangle([x + w * 0.58, y + h * 0.26, x + w * 0.92, y + h * 0.58], outline=(240, 240, 240), width=3)
    for i in range(1, 4):
        dr.line([x + w * (0.58 + i * 0.085), y + h * 0.26, x + w * (0.58 + i * 0.085), y + h * 0.58], fill=(240, 240, 240), width=1)
        dr.line([x + w * 0.58, y + h * (0.26 + i * 0.08), x + w * 0.92, y + h * (0.26 + i * 0.08)], fill=(240, 240, 240), width=1)
    # A football flying toward the net.
    ballx, bally = x + w * 0.30, y + h * 0.50
    dr.ellipse([ballx - w * 0.11, bally - h * 0.16, ballx + w * 0.11, bally + h * 0.16], fill=(240, 240, 240), outline=INK, width=2)
    dr.polygon([(ballx, bally - h * 0.16), (ballx + w * 0.04, bally - h * 0.04),
                (ballx, bally), (ballx - w * 0.04, bally - h * 0.04)], fill=INK)
    # A red '4-1' score badge in the corner of the pitch.
    draw_centered(dr, x + w * 0.20, y + h * 0.26, "4-1", 14, RED)


def drw_miami(dr, x, y, w, h):
    """Miami: a knocked-out scoreboard with a red card shown to the side."""
    # A dark scoreboard frame.
    dr.rectangle([x + w * 0.04, y + h * 0.22, x + w * 0.66, y + h * 0.64], fill=(40, 40, 38), outline=INK, width=2)
    draw_centered(dr, x + w * 0.35, y + h * 0.28, "MIA 0", 11, (255, 255, 255))
    draw_centered(dr, x + w * 0.35, y + h * 0.46, "CLB 1", 11, (255, 255, 255))
    # A football between the two score lines.
    dr.ellipse([x + w * 0.27, y + h * 0.36, x + w * 0.44, y + h * 0.54], fill=(240, 240, 240), outline=INK, width=1)
    # A red card stands upright to the right, meaning a sending off.
    dr.rectangle([x + w * 0.76, y + h * 0.22, x + w * 0.90, y + h * 0.64], fill=RED, outline=INK, width=2)
    # A small down arrow underlines the 'out' of the banner.
    dr.polygon([(x + w * 0.78, y + h * 0.72), (x + w * 0.88, y + h * 0.72),
                (x + w * 0.83, y + h * 0.82)], fill=INK)


def drw_peru(dr, x, y, w, h):
    """Peru: shaking mountains with a jagged seismic crack between them."""
    # Three Andes peaks of rising height.
    dr.polygon([(x + w * 0.04, y + h * 0.82), (x + w * 0.28, y + h * 0.32),
                (x + w * 0.52, y + h * 0.82)], fill=(176, 158, 134), outline=INK, width=2)
    dr.polygon([(x + w * 0.24, y + h * 0.82), (x + w * 0.50, y + h * 0.20),
                (x + w * 0.76, y + h * 0.82)], fill=(156, 138, 116), outline=INK, width=2)
    # Snow caps on the two tallest peaks.
    dr.polygon([(x + w * 0.24, y + h * 0.48), (x + w * 0.28, y + h * 0.32),
                (x + w * 0.34, y + h * 0.48)], fill=(240, 240, 240), outline=INK, width=1)
    dr.polygon([(x + w * 0.46, y + h * 0.38), (x + w * 0.50, y + h * 0.20),
                (x + w * 0.56, y + h * 0.38)], fill=(240, 240, 240), outline=INK, width=1)
    # A zig-zag crack runs down between the peaks to show the quake.
    dr.line([x + w * 0.50, y + h * 0.36, x + w * 0.42, y + h * 0.44,
             x + w * 0.50, y + h * 0.52, x + w * 0.44, y + h * 0.60,
             x + w * 0.50, y + h * 0.68], fill=RED, width=4)
    # Shaking arcs radiate from the ground on both sides.
    for s in (0.30, 0.60):
        dr.arc([x + w * (0.02 + s), y + h * 0.74, x + w * (0.20 + s), y + h * 0.94], 90, 270, fill=RED, width=3)
    # Two tiny houses at the foot of the mountains show the damage.
    dr.rectangle([x + w * 0.12, y + h * 0.74, x + w * 0.2, y + h * 0.84], fill=(198, 178, 150), outline=INK, width=1)
    dr.polygon([(x + w * 0.11, y + h * 0.74), (x + w * 0.16, y + h * 0.68), (x + w * 0.21, y + h * 0.74)], fill=(150, 90, 70))


def drw_storm(dr, x, y, w, h):
    """Brazil storm: a house losing its roof to a whirling gust."""
    # A small house with a triangle roof.
    dr.rectangle([x + w * 0.18, y + h * 0.40, x + w * 0.58, y + h * 0.78], fill=(198, 178, 150), outline=INK, width=2)
    dr.polygon([(x + w * 0.14, y + h * 0.40), (x + w * 0.38, y + h * 0.22),
                (x + w * 0.62, y + h * 0.40)], fill=(150, 90, 70), outline=INK, width=2)
    # A door and window on the wall.
    dr.rectangle([x + w * 0.34, y + h * 0.54, x + w * 0.42, y + h * 0.78], fill=(90, 80, 68), outline=INK, width=1)
    dr.rectangle([x + w * 0.22, y + h * 0.46, x + w * 0.28, y + h * 0.54], fill=(170, 190, 214), outline=INK, width=1)
    # A swirl of wind arcs sweeping across the scene.
    for r in (0.12, 0.18, 0.24):
        dr.arc([x + w * 0.60, y + h * 0.14, x + w * 0.98, y + h * 0.58], 180, 360, fill=INK, width=2)
    # Small flying debris lines above the roof.
    dr.line([x + w * 0.66, y + h * 0.20, x + w * 0.72, y + h * 0.16], fill=INK, width=2)
    dr.line([x + w * 0.80, y + h * 0.16, x + w * 0.86, y + h * 0.12], fill=INK, width=2)
    dr.line([x + w * 0.74, y + h * 0.12, x + w * 0.80, y + h * 0.08], fill=INK, width=2)


# The number keys into this lookup so story data and artwork stay decoupled.
# A table mapping story number to its drawing routine.
DRAWINGS = {
    1: drw_cop31, 2: drw_bahrain, 3: drw_kyiv, 4: drw_sparta,
    5: drw_bear, 6: drw_sinaloa, 7: drw_cikande, 8: drw_trade,
    9: drw_delta, 10: drw_cricket, 11: drw_leeds, 12: drw_miami,
    13: drw_peru, 14: drw_storm,
}

# ---------------------------------------------------------------------------
# The 14 feature stories.  Each entry carries the number, place, topic,
# headline, two-or-three-line summary (source named in brackets at the end)
# and the short wording for the red banner across the drawing.
# ---------------------------------------------------------------------------
STORIES = [
    (1, "ANTALYA, TURKIYE", "CLIMATE", "COP31 ends with no deal",
     "The EU, island nations and Panama reject a final draft that never names fossil fuels; nearly 200 countries leave Antalya without a deal. (AP, Reuters)",
     "COP31"),
    (2, "BAHRAIN", "GULF", "Iranian attack hits Bahrain facility",
     "Bahrain says an Iranian attack struck a civilian industrial site and wounded two people; Tehran shows off a new dual-missile launcher. (Reuters, AFP)",
     "BAHRAIN"),
    (3, "KYIV REGION, UKRAINE", "WAR", "Drone strike collapses Kyiv-region flats",
     "At least 14 are missing after a Russian drone hits a five-storey block; 186 drones were fired and 161 downed, and a Kryvyi Rih missile kills a boy and a woman. (AP)",
     "KYIV"),
    (4, "BALTIC SEA", "WAR", "Russian cargo ship ablaze after drone strike",
     "The Sparta II catches fire in the Gulf of Finland after a suspected Ukrainian drone strike, and the crew abandons ship. (Reuters)",
     "SPARTA II"),
    (5, "NEW YORK", "MARKETS", "AI sell-off puts Nasdaq in a bear market",
     "The S&P 500 falls 3.7 percent on Friday in its worst week since Covid; about 4 trillion dollars come off AI stocks and Nvidia faces an accounting inquiry. (AP, Reuters)",
     "BEAR MARKET"),
    (6, "SINALOA, MEXICO", "CARTELS", "El Chapo Isidro captured",
     "Mexican special forces seize the FBI's most-wanted cartel boss; 11 people die in the raid, four of them soldiers. (AP)",
     "SINALOA"),
    (7, "CIKANDE, INDONESIA", "DISASTER", "Factory fire leaves 36 missing",
     "A candy factory fire kills three workers and rescuers search the ruins for 36 still missing. (AP, Reuters)",
     "CIKANDE FIRE"),
    (8, "BRUSSELS", "TRADE", "EU and Indonesia sign landmark trade deal",
     "After nearly ten years of talks, tariffs are scrapped on up to 98.5 percent of goods. (Reuters)",
     "TRADE DEAL"),
    (9, "ATLANTA, USA", "TRAVEL", "Delta glitch delays 1,010 flights",
     "A weight-and-balance automation failure snarls Thanksgiving-week travel, and the FAA orders a ground stop, then a delay. (AP, Gizmodo)",
     "DELTA"),
    (10, "WELLINGTON", "CRICKET", "Pant powers India to 720 for 9",
     "A blistering century takes India to its highest Test total on New Zealand soil and breaks the Test six-hitting record. (Cricinfo)",
     "720 FOR 9"),
    (11, "LONDON", "FOOTBALL", "Leeds stun Chelsea 4-1",
     "Noah Okafor scores twice at Stamford Bridge; Newcastle hold Arsenal 2-2 and Manchester City draw 1-1. (BBC)",
     "LEEDS 4-1"),
    (12, "MIAMI, USA", "FOOTBALL", "Messi's Miami fall to Columbus",
     "Inter Miami lose their playoff opener to the Columbus Crew, and Messi escapes a red card. (AP)",
     "MIAMI OUT"),
    (13, "JUNIN, PERU", "QUAKE", "Magnitude 6.7 quake hits central Peru",
     "The Andean tremor injures people and damages homes as officials assess remote villages. (Reuters)",
     "PERU QUAKE"),
    (14, "TUPANCIRETA, BRAZIL", "STORM", "Storm kills three in southern Brazil",
     "Wind gusts of 114 km/h damage thousands of buildings in Rio Grande do Sul. (AP)",
     "BRAZIL STORM"),
]

# ---------------------------------------------------------------------------
# The 22 one-line briefs numbered 15 to 36, each beginning with number+place.
# ---------------------------------------------------------------------------
BRIEFS = [
    "15. GAZA. Israel names three Palestinians killed in a Gaza City drone strike on a vehicle on Saturday. (Al Jazeera)",
    "16. WEST BANK. Settler arson attacks on Palestinian homes condemned by Eisenkot as Jewish terrorism. (AFP)",
    "17. BENGHAZI. Suspected Ukrainian sea drones strike Russian corvette Merkury at a Libyan naval base. (Libyan officials)",
    "18. CARACAS. US and Venezuela sign a deal to re-establish military ties as Hegseth visits. (AP)",
    "19. WASHINGTON. Trump vows a permanent nuclear deal with Iran and warns Tehran over an alleged dirty-bomb plot that is not independently confirmed. (Anadolu)",
    "20. BRUSSELS. EU proposes a Big Tech tax and 200 billion euros of budget cuts. (Reuters)",
    "21. PARIS. French protesters rally for a sixth weekend over living costs and public services. (AP)",
    "22. COPENHAGEN. Denmark expels a Russian defence attache and curbs visas. (Reuters)",
    "23. TOKYO. Japan and Taiwan track Russian military aircraft near their coasts. (Reuters)",
    "24. BRASILIA. Bolsonaro in intensive care after an abdominal obstruction. (AP)",
    "25. MADRID. Spain heads for an early election on 29 November. (Reuters)",
    "26. JOHANNESBURG. ANC struggles to form local coalitions; Phumzile Mlambo-Ngcuka dies at 71. (AP)",
    "27. KHARTOUM. UN counts about 1630 civilian deaths from drone strikes in Sudan, January to October. (UN)",
    "28. KINSHASA. Ebola responders in DR Congo face attacks fuelled by misinformation. (WHO)",
    "29. MANIPUR. 11 dead and more than 180 in hospital after illicit alcohol. (Reuters)",
    "30. PORT-AU-PRINCE. Haiti signs a prison-building deal with El Salvador. (AP)",
    "31. LAHORE. Pakistan beat Sri Lanka 1-0 in their Test series, winning by eight wickets. (ICC)",
    "32. SEOUL. Education minister quits after an AI cheating scandal in the Suneung exam. (SBS)",
    "33. BAYELSA. 24 dead as a funeral boat capsizes in southern Nigeria. (NEMA)",
    "34. MELBOURNE. Australia edge England by three wickets in the first T20. (ICC)",
    "35. SYDNEY. Hobart Hurricanes and Sydney Sixers win in the Women's Big Bash. (Cricinfo)",
    "36. UNITED NATIONS. The race to succeed Guterres as secretary-general stalls. (AP)",
]

# ---------------------------------------------------------------------------
# The six big statistics and their short labels.
# ---------------------------------------------------------------------------
STATS = [
    ("14", "MISSING AFTER KYIV-REGION DRONE STRIKE"),
    ("186", "DRONES IN ONE OVERNIGHT RUSSIAN ATTACK"),
    ("1010+", "DELTA FLIGHTS DELAYED"),
    ("720-9", "INDIA'S TEST TOTAL IN WELLINGTON"),
    ("24", "DEAD IN NIGERIA BOAT CAPSIZE"),
    ("NO DEAL", "COP31 ENDS WITH NO DEAL"),
]

# ---------------------------------------------------------------------------
# The seven region tabs; the counts must total 36.
# ---------------------------------------------------------------------------
REGIONS = [
    ("EUROPE", 9, (70, 92, 140)),
    ("AMERICAS", 8, (176, 72, 58)),
    ("ASIA-PACIFIC", 5, (56, 128, 100)),
    ("MIDDLE EAST", 4, (176, 122, 46)),
    ("AFRICA", 5, (134, 92, 148)),
    ("OCEANIA", 3, (56, 128, 158)),
    ("WORLD", 2, (92, 90, 88)),
]

# ---------------------------------------------------------------------------
# The DATE CHECK list: events from earlier days, never 22 November news.
# ---------------------------------------------------------------------------
DATE_CHECK = ("the Trump, Xi and Putin meeting in Shenzhen", "the International Court of Justice verdict on "
              "Myanmar and the Rohingya", "Anthropic's record share sale and first days of trading",
              "the Russian missile barrage on Kyiv's bridges", "Cyclone Akvan reaching India",
              "the UK and European Union reset agreement", "the BepiColombo probe reaching Mercury",
              "the Houthi missile interceptions over Riyadh", "the tanker strikes near the Strait of Hormuz",
              "the GTA VI launch")

# ---------------------------------------------------------------------------
# Map data: an approximate location for every feature story so a numbered pin
# can be dropped onto the stylised world map.
# ---------------------------------------------------------------------------
PINS = [
    (1, 30.7, 36.9), (2, 50.5, 26.0), (3, 30.5, 50.4), (4, 22.0, 59.0),
    (5, -74.0, 40.7), (6, -107.5, 25.0), (7, 106.4, -6.3), (8, 4.35, 50.85),
    (9, -84.4, 33.7), (10, 174.8, -41.3), (11, -0.13, 51.5), (12, -80.2, 25.8),
    (13, -75.2, -11.2), (14, -53.6, -29.0),
]

# ---------------------------------------------------------------------------
# Coarse continent outlines in longitude/latitude, drawn as filled polygons.
# ---------------------------------------------------------------------------
CONTINENTS = [
    [(-165, 62), (-150, 66), (-135, 58), (-124, 49), (-117, 33), (-105, 20),
     (-96, 16), (-88, 22), (-81, 31), (-68, 45), (-60, 55), (-75, 62),
     (-90, 65), (-110, 68), (-140, 70), (-165, 70)],
    [(-80, 10), (-75, 2), (-60, 0), (-50, -3), (-40, -7), (-35, -15),
     (-38, -25), (-48, -28), (-55, -33), (-65, -40), (-72, -50), (-72, -40),
     (-75, -25), (-78, -10), (-80, 0), (-83, 8)],
    [(-17, 35), (-8, 36), (10, 37), (32, 31), (42, 11), (48, -2), (40, -15),
     (35, -30), (20, -35), (12, -18), (9, -5), (5, 5), (-8, 4), (-16, 10), (-17, 25)],
    [(-10, 36), (-8, 43), (2, 47), (10, 55), (20, 60), (30, 60), (40, 50),
     (28, 45), (22, 40), (12, 38), (2, 36)],
    [(30, 60), (45, 60), (60, 65), (90, 72), (120, 72), (140, 60), (160, 60),
     (170, 55), (175, 50), (160, 45), (140, 35), (120, 30), (105, 22), (95, 15),
     (85, 10), (70, 20), (60, 28), (50, 30), (40, 40), (35, 45), (30, 55)],
    [(172.8, -34.4), (174.6, -36.8), (176, -37.9), (177.6, -39.3),
     (176.6, -41.1), (174.8, -41.3), (174.5, -40.0), (173, -38.5),
     (172.8, -36.5)],
    [(166.5, -45.5), (168, -46.7), (170.5, -46.5), (172.5, -45.5),
     (174, -41.5), (172, -40.5), (170, -41.8), (167, -44.5)],
    [(95, 5), (102, 2), (106, -6), (111, -7), (118, -8), (122, -6),
     (116, -3), (109, -2), (103, 1)],
    [(35, 30), (46, 30), (56, 26), (60, 22), (52, 15), (43, 12), (38, 20)],
    [(-55, 60), (-45, 60), (-35, 66), (-40, 75), (-55, 80), (-70, 75), (-65, 66)],
]


# Project a real longitude/latitude pair into pixel space inside the map box.
def lonlat(lon, lat, mx, my, mw, mh):
    """Project longitude/latitude onto the rectangular map area."""
    x = mx + (lon + 180.0) / 360.0 * mw
    y = my + (90.0 - lat) / 180.0 * mh
    return x, y


# Layers are painted back-to-front so the pins always land on top of the map.
def draw_world_map(dr, mx, my, mw, mh):
    """Draw the simple, shape-built world map with its 14 numbered pins."""
    # Ocean background plus a subtle graticule grid.
    dr.rectangle([mx, my, mx + mw, my + mh], fill=SEA)
    for lon in range(-180, 181, 30):
        gx, _ = lonlat(lon, 0, mx, my, mw, mh)
        dr.line([gx, my, gx, my + mh], fill=GRID, width=1)
    for lat in range(-60, 91, 30):
        _, gy = lonlat(0, lat, mx, my, mw, mh)
        dr.line([mx, gy, mx + mw, gy], fill=GRID, width=1)
    # A thin frame around the map.
    dr.rectangle([mx, my, mx + mw, my + mh], outline=INK, width=2)
    # Fill each continent and trace its outline.
    for pts in CONTINENTS:
        xy = [lonlat(lon, lat, mx, my, mw, mh) for lon, lat in pts]
        dr.polygon(xy, fill=LAND, outline=INK)
    # Drop one numbered red pin for each of the 14 feature stories.  Each pin
    # is clamped a little inside the map border so the two places that sit near
    # an edge (New Zealand to the east, Hawaii to the west) never spill out.
    for num, lon, lat in PINS:
        px, py = lonlat(lon, lat, mx, my, mw, mh)
        r = 5
        px = max(mx + 8, min(mx + mw - 8, px))
        py = max(my + 8, min(my + mh - 8, py))
        dr.ellipse([px - r, py - r, px + r, py + r], fill=RED, outline=(255, 255, 255), width=1)
        draw_centered(dr, px, py + r - 1, str(num), 7, (255, 255, 255))


# ---------------------------------------------------------------------------
# Feature panel rendering.  A panel stacks, top to bottom: the subject
# drawing with its red banner, a kicker, a two-line headline and a short
# summary.  Text is measured and wrapped so nothing escapes the panel.
# ---------------------------------------------------------------------------
# Each card measures and wraps its text first, so nothing spills past a panel edge.
def draw_feature_panel(dr, x, y, w, h, story, large):
    num, place, topic, headline, summary, banner = story
    # Decide how tall the picture area is depending on panel size.
    pic_h = int(h * 0.42) if large else int(h * 0.38)
    # A light card behind the whole panel makes each story read as a unit.
    dr.rectangle([x, y, x + w, y + h], fill=CARD, outline=INK, width=2)
    # Draw the subject picture, then lay the red banner over its top edge.
    DRAWINGS[num](dr, x + 3, y + 3, w - 6, pic_h - 3)
    red_banner(dr, x + 3, y + 3, w - 6, 16, banner, 10 if large else 9)
    # Kicker line: number, place and topic in small caps.
    kick = "%d · %s · %s" % (num, place, topic)
    draw_left(dr, x + 7, y + pic_h + 4, kick, 9, RED)
    # Headline: wrap to two lines, shrinking only if a word would overflow.
    hl_lines, hl_size = fit_lines(headline, 13 if large else 11, w - 12, 2)
    ty = y + pic_h + 14
    for ln in hl_lines:
        draw_left(dr, x + 7, ty, ln, hl_size, INK)
        ty += hl_size + 2
    # Summary: up to three lines so nothing is ever cut off.
    sm_lines, sm_size = fit_lines(summary, 9 if large else 8, w - 12, 3)
    for ln in sm_lines:
        draw_left(dr, x + 7, ty, ln, sm_size, MID)
        ty += sm_size + 1


# ---------------------------------------------------------------------------
# Section builders, drawn strictly top to bottom to match the brief.
# ---------------------------------------------------------------------------
# Every section builder returns the next free y to hand off vertical space.
def build_header(dr, img, y):
    """Top bar, masthead, sub-headline and the double rule."""
    # Top bar: the page name on the left, the story/region count on the right.
    draw_left(dr, MARGIN, y + 2, "THE WORLD IN ONE DAY", 22, INK)
    draw_right(dr, W - MARGIN, y + 4, "36 STORIES · 7 REGIONS", 20, RED)
    dr.line([MARGIN, y + 30, W - MARGIN, y + 30], fill=RULE, width=2)
    y += 36
    # The large, centred masthead naming the day.
    draw_centered(dr, W // 2, y, "Sunday 22 November 2026", 64, INK)
    y += 68
    # The italic sub-headline naming the four lead stories.
    draw_italic_center(dr, img, W // 2, y,
                       "COP31 ends with no deal, Iran strikes Bahrain, 186 drones over Ukraine, Nasdaq in a bear market.",
                       13, INK)
    y += 18
    # A double horizontal rule separates the header from the body.
    hrule(dr, y, thick=4)
    hrule(dr, y + 8, thick=2)
    return y + 12


# The six figures sit in equal columns, the last one in red for the 'no deal' result.
def build_stats(dr, y):
    """The strip of six big numbers, each with a short label beneath."""
    colw = CW / 6.0
    for i, (num, label) in enumerate(STATS):
        cx = MARGIN + colw * i + colw / 2
        # The big number shrinks to fit its column if it is too wide.
        nsz = fit_one(num, 40, colw - 12)
        draw_centered(dr, cx, y + 2, num, nsz, RED if i == 5 else INK)
        # The label wraps to at most two short lines beneath the number.
        lab_lines, lab_size = fit_lines(label, 9, colw - 8, 2)
        for j, ln in enumerate(lab_lines):
            draw_centered(dr, cx, y + 40 + j * (lab_size + 1), ln, lab_size, MID)
    return y + 62


# Seven equal colour blocks let the 36-story regional split be seen at a glance.
def build_tabs(dr, y):
    """The row of seven coloured region tabs with their story counts."""
    gap = 5
    tabw = (CW - gap * 6) / 7.0
    for i, (name, count, col) in enumerate(REGIONS):
        x = MARGIN + i * (tabw + gap)
        dr.rectangle([x, y, x + tabw, y + 24], fill=col)
        label = "%s %d" % (name, count)
        draw_centered(dr, x + tabw / 2, y + 12 - 6, label, 11, (255, 255, 255))
    return y + 28


# Four large cards, then two rows of five smaller ones, advancing y row by row.
def build_features(dr, y):
    """The 14 feature panels: one row of four large, then two rows of five."""
    gap = 10
    # Row of four large panels.
    pw = (CW - gap * 3) / 4.0
    ph = 190
    for i in range(4):
        draw_feature_panel(dr, MARGIN + i * (pw + gap), y, pw, ph, STORIES[i], True)
    y += ph + 8
    # Two rows of five smaller panels.
    pw = (CW - gap * 4) / 5.0
    ph = 150
    for row in range(2):
        for i in range(5):
            idx = 4 + row * 5 + i
            draw_feature_panel(dr, MARGIN + i * (pw + gap), y, pw, ph, STORIES[idx], False)
        y += ph + 8
    return y


# The map stays left while the 22 briefs flow into two shrinking-font columns.
def build_map_briefs(dr, y):
    """The world map with pins, beside two columns of one-line briefs."""
    map_w = 180
    map_h = 150
    # Map sits on the left of this band.
    draw_world_map(dr, MARGIN, y, map_w, map_h)
    # Briefs fill the remaining width in two columns of eleven lines each.
    bx = MARGIN + map_w + 18
    colw = (W - MARGIN - bx - 12) / 2.0
    for i, brief in enumerate(BRIEFS):
        col = i // 11
        row = i % 11
        cx = bx + col * (colw + 12)
        cy = y + row * 13 + 2
        # Number and place are drawn in red, the rest in ink.
        parts = brief.split(". ", 2)
        head = parts[0] + ". " + parts[1] + "."
        rest = parts[2]
        # Keep each brief to a single line: shrink the font if it must.
        head_s = fit_one_tiny(head, 5, colw * 0.28)
        rest_s = fit_one_tiny(rest, 5, colw - tw(head, head_s) - 1)
        draw_left(dr, cx, cy, head, head_s, RED)
        draw_left(dr, cx + tw(head, head_s) + 1, cy, rest, rest_s, INK)
    # A thin divider between the two columns of briefs.
    dvx = bx + colw + 6
    dr.line([dvx, y, dvx, y + map_h], fill=GRID, width=1)
    return y + map_h


# A red box keeps earlier-days news apart from the current day's reporting.
def build_datecheck(dr, y):
    """The boxed DATE CHECK strip listing news from earlier days."""
    bh = 50
    bx0, by0 = MARGIN, y
    bx1, by1 = W - MARGIN, y + bh
    dr.rectangle([bx0, by0, bx1, by1], fill=CARD, outline=RED, width=2)
    # Title line: the words DATE CHECK are red and bold-looking, rest ink.
    draw_left(dr, bx0 + 10, by0 + 7, "DATE CHECK", 11, RED)
    draw_left(dr, bx0 + 10 + tw("DATE CHECK", 11) + 8, by0 + 8,
              "— big news from earlier days, never 22 November news:", 9, INK)
    # Join the list into a flowing sentence and wrap it inside the box.
    body = "  ·  ".join(DATE_CHECK) + "."
    lines = wrap(body, 8, (bx1 - bx0) - 20)
    ty = by0 + 23
    for ln in lines[:4]:
        draw_left(dr, bx0 + 10, ty, ln, 8, MID)
        ty += 9
    return y + bh


# A single credit line closes the page with the organisations behind the stories.
def build_footer(dr, y):
    """A single centred footer line naming the sources."""
    src = ("Sources: AP, Reuters, AFP, BBC, Cricinfo, ICC, Al Jazeera, Anadolu, "
           "SBS, NEMA, WHO, UN, Libyan officials, Gizmodo, and others.")
    draw_centered(dr, W // 2, y, src, 8, MID)


def render():
    """Compose every section into the finished 1024 by 1024 page."""
    img = Image.new("RGB", (W, H), PAPER)
    dr = ImageDraw.Draw(img)
    # A thin ink frame around the whole page, like a newspaper border.
    dr.rectangle([6, 6, W - 7, H - 7], outline=INK, width=2)

    y = MARGIN
    y = build_header(dr, img, y)   # returns 28 + 36 + 68 + 18 + 12 = 162
    y = build_stats(dr, y)         # + 62 -> 224
    y = build_tabs(dr, y)          # + 28 -> 252
    y = build_features(dr, y)      # 252 + 198 + 158 + 158 = 766
    y = build_map_briefs(dr, y)    # + 150 -> 916
    y = build_datecheck(dr, y)     # + 50 -> 966
    y += 10
    build_footer(dr, y)            # around 976, safely above the border
    return img


def main():
    """Render the page and write it to MAKEFUN_OUTPUT_DIR or /output."""
    img = render()
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "entry.png")
    img.save(outpath, "PNG")
    print("wrote", outpath, "size", img.size)


if __name__ == "__main__":
    main()
