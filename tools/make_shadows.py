#!/usr/bin/env python3
"""Draws the leaf silhouettes that cast the moving shadows on the homepage wall.

    python3 tools/make_shadows.py

Writes assets/img/shade-frond-a.svg, shade-frond-b.svg, shade-branch-a.svg and shade-branch-b.svg.
Every shape grows from the middle of the left edge towards the right, so the page can pin that point off screen
and sway the shape around it (see .wall in assets/css/store.css). The page blurs and tints them; here they are
plain solid shapes. Seeded, so running it again gives the same files.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "img"
W, H = 1000, 640
FILL = "#30343b"


def n(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def spine(length: float, bend: float, steps: int = 60):
    """Points and headings along a gently arcing stem that starts at the left edge."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = t * length
        y = H / 2 + bend * math.sin(t * math.pi * 0.55) * t
        pts.append((x, y))
    out = []
    for i, (x, y) in enumerate(pts):
        x2, y2 = pts[min(i + 1, steps)]
        x1, y1 = pts[max(i - 1, 0)]
        out.append((x, y, math.atan2(y2 - y1, x2 - x1)))
    return out


def blade(x, y, angle, length, width, droop=0.0) -> str:
    """A leaf: two curves from the base to a point, bowed outwards by `width`, the tip pulled down by `droop`."""
    tx = x + math.cos(angle) * length
    ty = y + math.sin(angle) * length + droop
    mx, my = (x + tx) / 2, (y + ty) / 2
    nx, ny = -math.sin(angle), math.cos(angle)
    return (f"M{n(x)} {n(y)}Q{n(mx + nx * width)} {n(my + ny * width)} {n(tx)} {n(ty)}"
            f"Q{n(mx - nx * width)} {n(my - ny * width)} {n(x)} {n(y)}Z")


def stem(points, thick: float) -> str:
    top = [(x - math.sin(a) * thick * (1 - i / len(points)), y + math.cos(a) * thick * (1 - i / len(points)))
           for i, (x, y, a) in enumerate(points)]
    bot = [(x + math.sin(a) * thick * (1 - i / len(points)), y - math.cos(a) * thick * (1 - i / len(points)))
           for i, (x, y, a) in enumerate(points)]
    return "M" + "L".join(f"{n(x)} {n(y)}" for x, y in top + bot[::-1]) + "Z"


def frond(seed: int, bend: float, pairs: int, reach: float) -> str:
    """A palm frond: a long stem with slender leaflets on both sides, longest in the middle."""
    rnd = random.Random(seed)
    pts = spine(940, bend, pairs + 8)
    d = [stem(pts, 7)]
    for i, (x, y, a) in enumerate(pts[6:-1]):
        t = i / pairs
        size = math.sin(min(1.0, t * 1.05 + 0.08) * math.pi) ** 0.6
        length = reach * size * rnd.uniform(0.86, 1.08)
        splay = math.radians(64 - 34 * t)
        for side in (-1, 1):
            if rnd.random() < 0.06:
                continue  # the odd missing leaflet
            ang = a + side * splay * rnd.uniform(0.92, 1.08)
            d.append(blade(x, y, ang, length, rnd.uniform(5, 9), droop=length * 0.10 * rnd.uniform(0.4, 1.4)))
    return "".join(d)


def branch(seed: int, bend: float, leaves: int) -> str:
    """A leafy branch: broader leaves alternating along a stem, with two side shoots."""
    rnd = random.Random(seed)
    d = []

    def shoot(ox, oy, heading, length, count, scale):
        pts = []
        for i in range(count * 2 + 1):
            t = i / (count * 2)
            pts.append((ox + math.cos(heading + t * 0.25) * length * t, oy + math.sin(heading + t * 0.25) * length * t,
                        heading + t * 0.25))
        d.append(stem(pts, 5 * scale))
        for i, (x, y, a) in enumerate(pts[2:]):
            side = 1 if i % 2 else -1
            size = scale * rnd.uniform(0.8, 1.15) * (1 - 0.35 * i / len(pts))
            d.append(blade(x, y, a + side * math.radians(rnd.uniform(38, 58)), 120 * size, 26 * size,
                           droop=10 * size))
        x, y, a = pts[-1]
        d.append(blade(x, y, a, 120 * scale, 24 * scale))

    main = spine(880, bend, leaves * 2)
    d.append(stem(main, 7))
    for i, (x, y, a) in enumerate(main[3:]):
        side = 1 if i % 2 else -1
        size = rnd.uniform(0.85, 1.2) * (1 - 0.3 * i / len(main))
        d.append(blade(x, y, a + side * math.radians(rnd.uniform(36, 60)), 135 * size, 30 * size, droop=12 * size))
    for at, heading in ((0.28, -0.75), (0.5, 0.7)):
        x, y, a = main[int(len(main) * at)]
        shoot(x, y, a + heading, 330, 4, 0.8)
    x, y, a = main[-1]
    d.append(blade(x, y, a, 140, 28))
    return "".join(d)


def write(name: str, path: str):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -160 {W} {H + 320}" fill="{FILL}">'
           f'<path d="{path}"/></svg>\n')
    (OUT / name).write_text(svg)
    print(f"  {name}: {len(svg) / 1024:.1f} KB")


if __name__ == "__main__":
    write("shade-frond-a.svg", frond(7, 150, 34, 250))
    write("shade-frond-b.svg", frond(21, -110, 30, 215))
    write("shade-branch-a.svg", branch(3, 120, 7))
    write("shade-branch-b.svg", branch(11, -90, 6))
