#!/usr/bin/env python3
"""Archive 88: build the logo files in assets/brand/ from the identity's geometry.

The marks are drawn once here and written as outlined SVG (no font needed to display them), so the site,
the favicon and the Figma identity page all use exactly the same shapes.

Only needed when the logo itself changes. Requires:  pip install fonttools brotli
Run:  python3 tools/make_brand.py
"""
import math
import os
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "assets", "fonts")
OUT = os.path.join(ROOT, "assets", "brand")


def face(file, wght):
    f = TTFont(os.path.join(FONTS, file))
    return instancer.instantiateVariableFont(f, {"wght": wght})


class Type:
    """Outlines text from one static instance of a font."""

    def __init__(self, font):
        self.font = font
        self.glyphs = font.getGlyphSet()
        self.cmap = font.getBestCmap()
        self.upm = font["head"].unitsPerEm
        self.cap = getattr(font["OS/2"], "sCapHeight", 0) or self.upm * 0.7

    def advance(self, ch):
        return self.font["hmtx"][self.cmap[ord(ch)]][0]

    def width(self, text, size, track=0.0):
        s = size / self.upm
        return sum(self.advance(c) * s + track * size for c in text) - track * size

    def line(self, text, size, x=0.0, y=0.0, track=0.0):
        """Path data for `text` with its baseline starting at (x, y). Returns (d, width)."""
        s = size / self.upm
        pen = SVGPathPen(self.glyphs, lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        cx = x
        for c in text:
            g = self.cmap[ord(c)]
            self.glyphs[g].draw(TransformPen(pen, (s, 0, 0, -s, cx, y)))
            cx += self.advance(c) * s + track * size
        return pen.getCommands(), cx - x - track * size

    def ring(self, text, size, cx, cy, r, track=0.0, start=-90.0):
        """Text set clockwise around a circle of radius r (baseline on the circle), centred on `start` degrees."""
        s = size / self.upm
        total = sum(self.advance(c) * s + track * size for c in text)
        pen = SVGPathPen(self.glyphs, lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        a = math.radians(start) - (total / r) / 2
        for c in text:
            adv = self.advance(c) * s + track * size
            mid = a + (adv - track * size) / (2 * r)          # angle at the glyph's centre
            rot = mid + math.pi / 2
            cos, sin = math.cos(rot), math.sin(rot)
            half = (adv - track * size) / 2
            # glyph space -> scale, flip y, shift so the glyph centre sits at the origin, rotate, move to the circle
            px, py = cx + r * math.cos(mid), cy + r * math.sin(mid)
            t = (s * cos, s * sin, s * sin, -s * cos, px - half * cos, py - half * sin)
            self.glyphs[self.cmap[ord(c)]].draw(TransformPen(pen, t))
            a += adv / r
        return pen.getCommands()


def n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def scene(cx=50.0, cy=50.0, k=1.0):
    """The roundel's picture: a ridge and a pine, counterchanged (one even-odd path).
    Drawn on a 100 x 100 field, then scaled by k about (cx, cy)."""
    R = 41.0

    def p(x, y):
        return f"{n(cx + (x - 50) * k)} {n(cy + (y - 50) * k)}"

    yl, yr = 47.0, 51.0
    xl = 50 - math.sqrt(R * R - (yl - 50) ** 2)
    xr = 50 + math.sqrt(R * R - (yr - 50) ** 2)
    ridge = [(xl, yl), (52, 47), (65.5, 23), (71.5, 32.5), (76.5, 27), (xr, yr)]
    mountain = "M" + "L".join(p(x, y) for x, y in ridge) + f"A{n(R * k)} {n(R * k)} 0 0 1 {p(xl, yl)}Z"
    pine_pts = [(38, 13), (47, 31), (43.5, 31), (52, 47), (47.5, 47), (57.5, 65),
                (40.5, 65), (40.5, 77), (35.5, 77), (35.5, 65),
                (18.5, 65), (28.5, 47), (24, 47), (32.5, 31), (29, 31)]
    pine = "M" + "L".join(p(x, y) for x, y in pine_pts) + "Z"
    return mountain + pine


def roundel(cx, cy, d):
    """Solid disc with the scene knocked out of it: one path, even-odd."""
    r = d / 2
    disc = f"M{n(cx - r)} {n(cy)}a{n(r)} {n(r)} 0 1 0 {n(d)} 0a{n(r)} {n(r)} 0 1 0 {n(-d)} 0Z"
    return disc + scene(cx, cy, d / 100)


def lozenge(cx, cy, w, h):
    return f"M{n(cx - w / 2)} {n(cy)}L{n(cx)} {n(cy - h / 2)}L{n(cx + w / 2)} {n(cy)}L{n(cx)} {n(cy + h / 2)}Z"


def svg(name, w, h, body, title):
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n(w)} {n(h)}" fill="currentColor" '
           f'role="img" aria-label="{title}"><title>{title}</title>{body}</svg>\n')
    with open(os.path.join(OUT, name), "w") as fh:
        fh.write(doc)
    return doc


def main():
    os.makedirs(OUT, exist_ok=True)
    slab = Type(face("rokkitt-latin.woff2", 900))
    mono = Type(face("geist-mono-latin.woff2", 500))
    parts = {}

    # ── Emblem: the roundel on its own ────────────────────────────────────────
    parts["emblem"] = svg("emblem.svg", 100, 100,
                          f'<path fill-rule="evenodd" d="{roundel(50, 50, 100)}"/>', "Archive 88")

    # ── Primary lockup: ARCHIVE (roundel) 88 on one line ──────────────────────
    size = 100.0
    cap = slab.cap / slab.upm * size
    track = 0.012
    d1, w1 = slab.line("ARCHIVE", size, 0, cap, track)
    dia = cap * 1.18                                     # the roundel overshoots the cap height, as round letters do
    gap = cap * 0.30
    ex = w1 + gap + dia / 2
    d2, w2 = slab.line("88", size, ex + dia / 2 + gap, cap, track)
    W = ex + dia / 2 + gap + w2
    pad = (dia - cap) / 2
    body = (f'<g transform="translate(0 {n(pad)})"><path d="{d1}"/><path d="{d2}"/></g>'
            f'<path fill-rule="evenodd" d="{roundel(ex, pad + cap / 2, dia)}"/>')
    parts["lockup"] = svg("lockup.svg", W, dia, body, "Archive 88")
    parts["lockup_size"] = (W, dia)

    # ── Wordmark: letters only, for small sizes where the roundel would fill in ─
    dw, ww = slab.line("ARCHIVE 88", size, 0, cap, track)
    parts["wordmark"] = svg("wordmark.svg", ww, cap, f'<path d="{dw}"/>', "Archive 88")
    parts["wordmark_size"] = (ww, cap)

    # ── Stacked lockup: roundel, name, descriptor ─────────────────────────────
    sw = ww
    rd = 92.0
    ty = rd + 30
    ms = 11.5
    desc = ["CURATED PIECES", "EST. 1988"]
    mt = 0.24
    wa, wb = mono.width(desc[0], ms, mt), mono.width(desc[1], ms, mt)
    lz = 16
    total = wa + lz * 2 + 6 + wb
    x0 = (sw - total) / 2
    by = ty + cap + 30
    da, _ = mono.line(desc[0], ms, x0, by, mt)
    db, _ = mono.line(desc[1], ms, x0 + wa + lz * 2 + 6, by, mt)
    mcap = mono.cap / mono.upm * ms
    body = (f'<path fill-rule="evenodd" d="{roundel(sw / 2, rd / 2, rd)}"/>'
            f'<g transform="translate(0 {n(ty)})"><path d="{dw}"/></g>'
            f'<path d="{da}"/><path d="{db}"/><path d="{lozenge(x0 + wa + lz + 3, by - mcap / 2, 7, 7)}"/>')
    parts["stacked"] = svg("stacked.svg", sw, by + 2, body, "Archive 88. Curated pieces, est. 1988")
    parts["stacked_size"] = (sw, by + 2)

    # ── Seal: roundel inside a ring of type ───────────────────────────────────
    C, ro = 120.0, 118.0
    ring = (f"M{n(C - ro)} {n(C)}a{n(ro)} {n(ro)} 0 1 0 {n(ro * 2)} 0a{n(ro)} {n(ro)} 0 1 0 {n(-ro * 2)} 0Z"
            f"M{n(C - ro + 2.5)} {n(C)}a{n(ro - 2.5)} {n(ro - 2.5)} 0 1 1 {n((ro - 2.5) * 2)} 0"
            f"a{n(ro - 2.5)} {n(ro - 2.5)} 0 1 1 {n(-(ro - 2.5) * 2)} 0Z")
    ts = 15.0
    rt = 88.0
    top = slab.ring("ARCHIVE 88", 27, C, C, rt - 3, 0.07, -90)
    # bottom line reads left to right along the lower arc: set anticlockwise by mirroring the angle walk
    bot = ring_bottom(mono, "CURATED PIECES  EST. 1988", ts * 0.72, C, C, rt + 8.5, 0.2)
    loz = lozenge(C - rt - 3, C, 8, 8) + lozenge(C + rt + 3, C, 8, 8)
    body = (f'<path fill-rule="evenodd" d="{ring}"/><path d="{top}"/><path d="{bot}"/><path d="{loz}"/>'
            f'<path fill-rule="evenodd" d="{roundel(C, C, 124)}"/>')
    parts["seal"] = svg("seal.svg", 240, 240, body, "Archive 88 seal")

    # ── Monogram: A88 ─────────────────────────────────────────────────────────
    dm, wm = slab.line("A88", size, 0, cap, -0.005)
    parts["monogram"] = svg("monogram.svg", wm, cap, f'<path d="{dm}"/>', "A88")
    parts["monogram_size"] = (wm, cap)

    # ── Favicon: the roundel, switching colour with the browser theme ─────────
    fav = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><style>path{fill:#17271f}'
           '@media(prefers-color-scheme:dark){path{fill:#efebe1}}</style>'
           f'<path fill-rule="evenodd" d="{roundel(50, 50, 100)}"/></svg>\n')
    with open(os.path.join(ROOT, "assets", "img", "favicon.svg"), "w") as fh:
        fh.write(fav)

    # ── Rotating ring for the seal on the homepage: one line of type all the way round ──
    ring_d = ring_full(mono, "ARCHIVE 88 * CURATED PIECES * EST. 1988 * ", 13.0, 120, 120, 101.0)

    with open(os.path.join(OUT, "seal-ring.svg"), "w") as fh:
        fh.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" fill="#efebe1"><path d="{ring_d}"/></svg>\n')

    # ── src/brand-defs.html: the logo as reusable inline SVG parts, plus the social icons ──
    defs_path = os.path.join(ROOT, "src", "brand-defs.html")
    icons = [ln for ln in open(defs_path).read().splitlines() if 'id="ico-' in ln]
    defs = f"""  <!-- GENERATED by tools/make_brand.py: the Archive 88 logo as inline SVG parts, so pages can colour and animate it.
       lg-name + lg-roundel + lg-88 share the lockup's viewBox (0 0 {n(W)} {n(dia)}); lg-emblem is 100 x 100; lg-word is the letters-only wordmark.
       Social icons: Instagram/Facebook from Phosphor Icons (MIT). -->
  <svg width="0" height="0" style="position:absolute" aria-hidden="true">
    <defs>
      <g id="lg-name" transform="translate(0 {n(pad)})"><path d="{d1}"/></g>
      <g id="lg-88" transform="translate(0 {n(pad)})"><path d="{d2}"/></g>
      <path id="lg-roundel" fill-rule="evenodd" d="{roundel(ex, pad + cap / 2, dia)}"/>
      <path id="lg-emblem" fill-rule="evenodd" d="{roundel(50, 50, 100)}"/>
      <g id="lg-word"><path d="{dw}"/></g>
{chr(10).join(icons)}
    </defs>
  </svg>
"""
    with open(defs_path, "w") as fh:
        fh.write(defs)
    print("lockup viewBox", n(W), n(dia), "roundel centre", n(ex), n(pad + cap / 2), "wordmark", n(ww), n(cap))

    for k, v in parts.items():
        if k.endswith("_size"):
            print(k, [round(x, 2) for x in v])
    print("wrote", sorted(os.listdir(OUT)))


def ring_bottom(t, text, size, cx, cy, r, track):
    """Text along the lower arc, reading left to right (tops of the letters point to the centre)."""
    s = size / t.upm
    total = sum(t.advance(c) * s + track * size for c in text)
    pen = SVGPathPen(t.glyphs, lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    a = math.radians(90) + (total / r) / 2
    for c in text:
        adv = t.advance(c) * s + track * size
        w = adv - track * size
        mid = a - w / (2 * r)
        rot = mid - math.pi / 2
        cos, sin = math.cos(rot), math.sin(rot)
        px, py = cx + r * math.cos(mid), cy + r * math.sin(mid)
        tr = (s * cos, s * sin, s * sin, -s * cos, px - (w / 2) * cos, py - (w / 2) * sin)
        if c != " ":
            t.glyphs[t.cmap[ord(c)]].draw(TransformPen(pen, tr))
        a -= adv / r
    return pen.getCommands()


def ring_full(t, text, size, cx, cy, r):
    """One line of type clockwise round the whole circle; `*` becomes a lozenge. Spacing is stretched to close the loop."""
    s = size / t.upm
    adv = [(size * 0.9 if c == "*" else t.advance(c) * s) for c in text]
    track = (2 * math.pi * r - sum(adv)) / len(text)
    pen = SVGPathPen(t.glyphs, lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    extra = ""
    a = -math.pi / 2
    capm = t.cap / t.upm * size
    for c, w in zip(text, adv):
        mid = a + w / (2 * r)
        if c == "*":
            rc, h = r + capm / 2, capm * 0.42
            ux, uy = math.cos(mid), math.sin(mid)
            pts = [(cx + (rc + h) * ux, cy + (rc + h) * uy), (cx + rc * ux - h * uy, cy + rc * uy + h * ux),
                   (cx + (rc - h) * ux, cy + (rc - h) * uy), (cx + rc * ux + h * uy, cy + rc * uy - h * ux)]
            extra += "M" + "L".join(f"{n(x)} {n(y)}" for x, y in pts) + "Z"
        elif c != " ":
            rot = mid + math.pi / 2
            cos, sin = math.cos(rot), math.sin(rot)
            px, py = cx + r * math.cos(mid), cy + r * math.sin(mid)
            t.glyphs[t.cmap[ord(c)]].draw(TransformPen(pen, (s * cos, s * sin, s * sin, -s * cos, px - (w / 2) * cos, py - (w / 2) * sin)))
        a += (w + track) / r
    return pen.getCommands() + extra


if __name__ == "__main__":
    sys.exit(main())
