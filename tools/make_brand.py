#!/usr/bin/env python3
"""Archive 88: build the logo files in assets/brand/ from the identity's geometry.

The idea of the mark: the 88 is four rings, two by two. Where the four rings meet they leave a four-pointed
star, the lozenge from the original logo, now a north star. The pine is drawn from the same arcs.

Everything is written as outlined SVG (no font needed to display it), so the site, the favicon and the Figma
identity page all use exactly the same shapes.

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
BLAZE = "#e5541b"

# ── The mark, on its own grid ─────────────────────────────────────────────────
R = 50.0            # ring radius
HOLE = 16.0         # counter radius
DROP = 88.0         # distance between the two ring centres of one eight (they overlap by 12)
MW, MH = 4 * R, 2 * R + DROP                      # 200 x 188
TIP = R - math.sqrt(R * R - (DROP / 2) ** 2)      # half-width of the star at its waist (26.25)


def n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def circle(cx, cy, r, cw=True):
    s = 1 if cw else 0
    return f"M{n(cx - r)} {n(cy)}a{n(r)} {n(r)} 0 1 {s} {n(2 * r)} 0a{n(r)} {n(r)} 0 1 {s} {n(-2 * r)} 0Z"


def mark(x=0.0, y=0.0, h=MH, hole=HOLE):
    """Returns (rings, star) path data for the mark with its top-left at (x, y) and height h."""
    k = h / MH
    P = lambda px, py: (x + px * k, y + py * k)
    rings = ""
    for cx in (R, 3 * R):
        for cy in (R, R + DROP):
            a, b = P(cx, cy)
            rings += circle(a, b, R * k) + circle(a, b, hole * k, cw=False)
    r = n(R * k)
    t, rt, bt, lt = P(2 * R, R), P(2 * R + TIP, R + DROP / 2), P(2 * R, R + DROP), P(2 * R - TIP, R + DROP / 2)
    star = (f"M{n(t[0])} {n(t[1])}A{r} {r} 0 0 0 {n(rt[0])} {n(rt[1])}A{r} {r} 0 0 0 {n(bt[0])} {n(bt[1])}"
            f"A{r} {r} 0 0 0 {n(lt[0])} {n(lt[1])}A{r} {r} 0 0 0 {n(t[0])} {n(t[1])}Z")
    return rings, star


def pine(cx, top, h):
    """The pine: three tiers cut from the same arcs as the star, and a trunk. Height h, centred on cx."""
    unit = h / 150.0
    d = ""
    for s, y0 in ((0.86, 0.0), (1.12, 30.0), (1.4, 66.0)):
        r = R * s * unit
        ax, ay = cx, top + y0 * unit
        hw, hh = TIP * s * unit, (DROP / 2) * s * unit
        d += (f"M{n(ax)} {n(ay)}A{n(r)} {n(r)} 0 0 0 {n(ax + hw)} {n(ay + hh)}L{n(ax - hw)} {n(ay + hh)}"
              f"A{n(r)} {n(r)} 0 0 0 {n(ax)} {n(ay)}Z")
    tw = 9 * unit
    d += f"M{n(cx - tw / 2)} {n(top + 126 * unit)}h{n(tw)}v{n(24 * unit)}h{n(-tw)}Z"
    return d


def lozenge(cx, cy, w, h):
    """The small star used as a separator: the mark's star at reading size."""
    k = h / DROP
    r = n(R * k)
    hw = TIP * k
    return (f"M{n(cx)} {n(cy - h / 2)}A{r} {r} 0 0 0 {n(cx + hw)} {n(cy)}A{r} {r} 0 0 0 {n(cx)} {n(cy + h / 2)}"
            f"A{r} {r} 0 0 0 {n(cx - hw)} {n(cy)}A{r} {r} 0 0 0 {n(cx)} {n(cy - h / 2)}Z")


# ── Type ──────────────────────────────────────────────────────────────────────
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
        pen = SVGPathPen(self.glyphs, n)
        cx = x
        for c in text:
            self.glyphs[self.cmap[ord(c)]].draw(TransformPen(pen, (s, 0, 0, -s, cx, y)))
            cx += self.advance(c) * s + track * size
        return pen.getCommands(), cx - x - track * size

    def ring(self, text, size, cx, cy, r, track=0.0, start=-90.0, inside=False):
        """Text centred on `start` degrees round a circle. inside=True reads left to right along the lower arc."""
        s = size / self.upm
        adv = [self.advance(c) * s for c in text]
        total = sum(adv) + track * size * (len(text) - 1)
        pen = SVGPathPen(self.glyphs, n)
        sign = -1 if inside else 1
        a = math.radians(start) - sign * (total / r) / 2
        for c, w in zip(text, adv):
            mid = a + sign * w / (2 * r)
            rot = mid + sign * math.pi / 2
            cos, sin = math.cos(rot), math.sin(rot)
            px, py = cx + r * math.cos(mid), cy + r * math.sin(mid)
            if c != " ":
                self.glyphs[self.cmap[ord(c)]].draw(TransformPen(pen, (s * cos, s * sin, s * sin, -s * cos, px - (w / 2) * cos, py - (w / 2) * sin)))
            a += sign * (w + track * size) / r
        return pen.getCommands()

    def loop(self, text, size, cx, cy, r):
        """One line of type clockwise round the whole circle; `*` becomes a star. Spacing is stretched to close the loop."""
        s = size / self.upm
        capm = self.cap / self.upm * size
        adv = [(size * 0.9 if c == "*" else self.advance(c) * s) for c in text]
        track = (2 * math.pi * r - sum(adv)) / len(text)
        pen = SVGPathPen(self.glyphs, n)
        extra = ""
        a = -math.pi / 2
        for c, w in zip(text, adv):
            mid = a + w / (2 * r)
            if c == "*":
                rc = r + capm / 2
                extra += lozenge(cx + rc * math.cos(mid), cy + rc * math.sin(mid), 0, capm * 1.25)
            elif c != " ":
                rot = mid + math.pi / 2
                cos, sin = math.cos(rot), math.sin(rot)
                px, py = cx + r * math.cos(mid), cy + r * math.sin(mid)
                self.glyphs[self.cmap[ord(c)]].draw(TransformPen(pen, (s * cos, s * sin, s * sin, -s * cos, px - (w / 2) * cos, py - (w / 2) * sin)))
            a += (w + track) / r
        return pen.getCommands() + extra


def svg(name, w, h, body, title):
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n(w)} {n(h)}" fill="currentColor" '
           f'role="img" aria-label="{title}"><title>{title}</title>{body}</svg>\n')
    with open(os.path.join(OUT, name), "w") as fh:
        fh.write(doc)


def two(rings, star):
    """The mark in its two-colour form: rings take the text colour, the star is blaze."""
    # The star sits under the rings with a hairline of its own colour, so no background shows through the joins.
    return f'<path fill="{BLAZE}" stroke="{BLAZE}" stroke-width="0.6" d="{star}"/><path d="{rings}"/>'


def main():
    os.makedirs(OUT, exist_ok=True)
    slab = Type(face("rokkitt-latin.woff2", 900))
    mono = Type(face("geist-mono-latin.woff2", 500))
    size = 100.0
    cap = slab.cap / slab.upm * size
    track = 0.012

    # ── Mark ──────────────────────────────────────────────────────────────────
    rings, star = mark()
    svg("mark.svg", MW, MH, two(rings, star), "Archive 88")
    svg("mark-one-colour.svg", MW, MH, f'<path d="{rings}"/>', "Archive 88")
    svg("star.svg", 2 * TIP, DROP, f'<path d="{lozenge(TIP, DROP / 2, 0, DROP)}"/>', "Archive 88 star")
    svg("pine.svg", 80, 150, f'<path d="{pine(40, 0, 150)}"/>', "Archive 88 pine")

    # ── Lockup: ARCHIVE and the eights on one line. The eights overshoot the cap height by 5% top and bottom. ──
    dn, wn = slab.line("ARCHIVE", size, 0, cap, track)
    mh = cap * 1.1
    pad = (mh - cap) / 2
    mx = wn + cap * 0.3
    lr, ls = mark(mx, 0, mh)
    W = mx + MW * mh / MH
    name = f'<g transform="translate(0 {n(pad)})"><path d="{dn}"/></g>'
    svg("lockup.svg", W, mh, name + two(lr, ls), "Archive 88")
    svg("wordmark.svg", wn, cap, f'<path d="{dn}"/>', "Archive")

    # ── Stacked: the mark, the name, the descriptor ───────────────────────────
    sh = 150.0
    sr, ss = mark((wn - MW * sh / MH) / 2, 0, sh)
    ty = sh + 34
    ms, mt = 12.5, 0.24
    a, b = "CURATED PIECES", "EST. 1988"
    wa, wb = mono.width(a, ms, mt), mono.width(b, ms, mt)
    gap = 22
    x0 = (wn - (wa + gap * 2 + wb)) / 2
    by = ty + cap + 34
    mcap = mono.cap / mono.upm * ms
    da, _ = mono.line(a, ms, x0, by, mt)
    db, _ = mono.line(b, ms, x0 + wa + gap * 2, by, mt)
    svg("stacked.svg", wn, by + 2,
        two(sr, ss) + f'<g transform="translate(0 {n(ty)})"><path d="{dn}"/></g><path d="{da}"/><path d="{db}"/>'
        f'<path fill="{BLAZE}" d="{lozenge(x0 + wa + gap, by - mcap / 2, 0, mcap * 1.5)}"/>',
        "Archive 88. Curated pieces, est. 1988")

    # ── Seal: the mark inside a ring of type ──────────────────────────────────
    C, ro = 150.0, 148.0
    band = circle(C, C, ro) + circle(C, C, ro - 4, cw=False)
    top = slab.ring("ARCHIVE", 34, C, C, 108, 0.1, -90)
    bot = mono.ring("CURATED PIECES  EST. 1988", 12.5, C, C, 124, 0.2, 90, inside=True)
    qr, qs = mark(C - MW * 128 / MH / 2, C - 64, 128)
    stars = lozenge(C - 119, C, 0, 15) + lozenge(C + 119, C, 0, 15)
    svg("seal.svg", 300, 300, f'<path d="{band}"/><path d="{top}"/><path d="{bot}"/><path fill="{BLAZE}" d="{stars}"/>' + two(qr, qs),
        "Archive 88 seal")
    ring_d = mono.loop("ARCHIVE 88 * CURATED PIECES * EST. 1988 * ", 13.0, 120, 120, 101.0)
    with open(os.path.join(OUT, "seal-ring.svg"), "w") as fh:
        fh.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" fill="#efebe1"><path d="{ring_d}"/></svg>\n')

    # ── Monogram: A and the eights ────────────────────────────────────────────
    dA, wA = slab.line("A", size, 0, cap, 0)
    gr, gs = mark(wA + cap * 0.12, 0, mh)
    svg("monogram.svg", wA + cap * 0.12 + MW * mh / MH, mh,
        f'<g transform="translate(0 {n(pad)})"><path d="{dA}"/></g>' + two(gr, gs), "A88")

    # ── Favicon: the mark on a spruce tile ────────────────────────────────────
    fr, fs = mark(15, 17.1, 65.8)
    fav = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#17271f"/>'
           f'<path fill="{BLAZE}" stroke="{BLAZE}" stroke-width="0.6" d="{fs}"/><path fill="#efebe1" d="{fr}"/></svg>\n')
    with open(os.path.join(ROOT, "assets", "img", "favicon.svg"), "w") as fh:
        fh.write(fav)

    # ── src/brand-defs.html: the logo as reusable inline SVG parts, plus the social icons ──
    defs_path = os.path.join(ROOT, "src", "brand-defs.html")
    icons = [ln for ln in open(defs_path).read().splitlines() if 'id="ico-' in ln]
    er, es = mark(0, 0, MH)
    sx, sy = mx + (2 * R) * mh / MH, (R + DROP / 2) * mh / MH
    defs = f"""  <!-- GENERATED by tools/make_brand.py: the Archive 88 logo as inline SVG parts, so pages can colour and animate it.
       Lockup viewBox: 0 0 {n(W)} {n(mh)} (lg-name, lg-88, lg-star; the star's centre is {n(sx)} {n(sy)}).
       lg-mark and lg-mark-star: the eights on their own, {n(MW)} x {n(MH)}. lg-pine: 80 x 150. lg-loz: the star alone, 52.5 x 88.
       Social icons: Instagram/Facebook from Phosphor Icons (MIT). -->
  <svg width="0" height="0" style="position:absolute" aria-hidden="true">
    <defs>
      <g id="lg-name" transform="translate(0 {n(pad)})"><path d="{dn}"/></g>
      <path id="lg-88" d="{lr}"/>
      <path id="lg-star" d="{ls}"/>
      <path id="lg-mark" d="{er}"/>
      <path id="lg-mark-star" d="{es}"/>
      <path id="lg-pine" d="{pine(40, 0, 150)}"/>
      <path id="lg-loz" d="{lozenge(TIP, DROP / 2, 0, DROP)}"/>
{chr(10).join(icons)}
    </defs>
  </svg>
"""
    with open(defs_path, "w") as fh:
        fh.write(defs)
    print("lockup", n(W), n(mh), "star centre", n(sx), n(sy), "| mark", n(MW), n(MH), "| wordmark", n(wn), n(cap))
    print("wrote", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    sys.exit(main())
