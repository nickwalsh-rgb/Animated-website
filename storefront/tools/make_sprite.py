"""Writes assets/sprite.svg: UI icons + placeholder garment art (front/back, 4:5 viewBox 400x500).

The garment art stands in for photography until real photos are added (see assets/products/README.md).
Colour comes from CSS `color` on the <svg> that uses it, so one shape serves every colourway.
"""
from pathlib import Path

ICONS = {
    "bag": '<path d="M6 7h12l1 13H5L6 7Z"/><path d="M9 7V6a3 3 0 0 1 6 0v1"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "chevron": '<path d="m6 9 6 6 6-6"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "filter": '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "truck": '<path d="M3 6h11v10H3zM14 10h4l3 3v3h-7"/><circle cx="7" cy="17.5" r="1.5"/><circle cx="17" cy="17.5" r="1.5"/>',
    "return": '<path d="M4 9h11a5 5 0 0 1 0 10H8"/><path d="m8 5-4 4 4 4"/>',
    "leaf": '<path d="M5 19c0-8 5-13 14-14 0 9-5 14-13 14"/><path d="M5 19 13 11"/>',
    "check": '<path d="m5 12 4.5 4.5L19 7"/>',
    "trash": '<path d="M5 7h14M10 7V5h4v2M7 7l1 12h8l1-12"/>',
}

SHAPES = {
    "coat": ("M168 70 L232 70 L268 82 L316 100 Q334 108 337 130 L352 382 Q340 390 324 386 L310 214 L306 446 L94 446 L90 214 L76 386 Q60 390 48 382 L63 130 Q66 108 84 100 L132 82 Z",
             "M168 70 L200 168 L232 70 M168 70 L150 120 L176 140 M232 70 L250 120 L224 140 M200 168 L200 446 M118 330 L168 326 M232 326 L282 330 M56 362 L80 366 M320 366 L344 362",
             [(200, 200), (200, 262), (200, 324)],
             "M168 70 Q200 90 232 70 M200 90 L200 446 M100 128 Q200 146 300 128 M56 362 L80 366 M320 366 L344 362"),
    "knit": ("M166 76 Q200 92 234 76 L282 88 L322 108 Q338 116 340 136 L350 372 L322 376 L306 206 L304 408 L96 408 L94 206 L78 376 L50 372 L60 136 Q62 116 78 108 L118 88 Z",
             "M166 76 Q200 112 234 76 M172 82 Q200 102 228 82 M96 386 L304 386 M52 352 L80 356 M320 356 L348 352 M150 130 L150 380 M250 130 L250 380 M200 120 L200 380",
             [],
             "M166 76 Q200 90 234 76 M96 386 L304 386 M52 352 L80 356 M320 356 L348 352"),
    "shirt": ("M170 72 L230 72 L270 84 L318 104 Q334 112 336 132 L348 370 L322 374 L306 206 L304 404 Q250 426 200 418 Q150 426 96 404 L94 206 L78 374 L52 370 L64 132 Q66 112 82 104 L130 84 Z",
              "M170 72 L184 106 L200 90 L216 106 L230 72 M206 96 L206 418 M226 150 L262 150 L262 192 L226 192 Z M54 348 L80 352 M320 352 L346 348",
              [(200, 130), (200, 180), (200, 230), (200, 280), (200, 330), (200, 380)],
              "M170 72 Q200 84 230 72 M90 120 Q200 134 310 120 M200 126 L200 146 M54 348 L80 352 M320 352 L346 348"),
    "tee": ("M168 82 Q200 98 232 82 L276 94 L342 134 L318 196 L294 182 L296 408 L104 408 L106 182 L82 196 L58 134 L124 94 Z",
            "M168 82 Q200 116 232 82 M68 130 L92 190 M332 130 L308 190 M104 392 L296 392",
            [],
            "M168 82 Q200 92 232 82 M68 130 L92 190 M332 130 L308 190 M104 392 L296 392"),
    "trouser": ("M120 64 L280 64 L300 452 L216 452 L202 176 L198 176 L184 452 L100 452 Z",
                "M120 86 L280 86 M140 64 L140 86 M200 64 L200 86 M260 64 L260 86 M206 86 L206 156 Q204 168 198 176 M126 92 Q150 104 158 146 M274 92 Q250 104 242 146 M150 170 L142 450 M250 170 L258 450 M101 436 L185 436 M215 436 L299 436",
                [(206, 76)],
                "M120 86 L280 86 M140 64 L140 86 M200 64 L200 86 M260 64 L260 86 M200 86 L200 176 M134 118 L182 116 L180 162 L136 164 Z M218 116 L266 118 L264 164 L220 162 Z M101 436 L185 436 M215 436 L299 436"),
    "blazer": ("M168 70 L232 70 L268 82 L316 100 Q334 108 337 130 L350 372 L324 376 L310 214 L306 400 Q260 418 212 412 L200 300 L188 412 Q140 418 94 400 L90 214 L76 376 L50 372 L63 130 Q66 108 84 100 L132 82 Z",
               "M168 70 L150 128 L178 150 L200 250 M232 70 L250 128 L222 150 L200 250 M112 320 L168 316 M232 316 L288 320 M236 172 L272 170 M54 352 L78 356 M322 356 L346 352",
               [(200, 274)],
               "M168 70 Q200 88 232 70 M200 88 L200 412 M54 352 L78 356 M322 356 L346 352"),
}


def symbol(name, path_id, details, buttons):
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="4.5" fill="rgba(0,0,0,.28)"/>' for x, y in buttons)
    return (f'<symbol id="s-{name}" viewBox="0 0 400 500">'
            f'<use href="#{path_id}" fill="currentColor" stroke="rgba(0,0,0,.16)" stroke-width="1.5"/>'
            f'<use href="#{path_id}" fill="url(#shade)"/>'
            f'<path d="{details}" fill="none" stroke="rgba(0,0,0,.2)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
            f'{dots}</symbol>')


parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>',
         '<linearGradient id="shade" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".12"/>'
         '<stop offset=".55" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".16"/></linearGradient>',
         '<pattern id="weave" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M0 2.5h10M0 7.5h10" stroke="rgba(0,0,0,.09)" stroke-width="2"/>'
         '<path d="M2.5 0v10M7.5 0v10" stroke="rgba(255,255,255,.07)" stroke-width="2"/></pattern>']
for name, (outline, front, buttons, back) in SHAPES.items():
    parts.append(f'<path id="p-{name}" d="{outline}"/>')
parts.append("</defs>")
for name, body in ICONS.items():
    parts.append(f'<symbol id="i-{name}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
                 f'stroke-linecap="round" stroke-linejoin="round">{body}</symbol>')
for name, (outline, front, buttons, back) in SHAPES.items():
    parts.append(symbol(name, f"p-{name}", front, buttons))
    parts.append(symbol(name + "-back", f"p-{name}", back, []))
parts.append("</svg>")
out = Path(__file__).resolve().parent.parent / "assets" / "sprite.svg"
out.write_text("".join(parts) + "\n")
print("Wrote", out, out.stat().st_size, "bytes")
