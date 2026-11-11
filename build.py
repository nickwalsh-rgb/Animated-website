#!/usr/bin/env python3
"""Builds the Archive 88 site from data/ and src/ into static pages.

    python3 build.py

Reads   data/store.json, data/catalog.json, assets/products/<handle>/<colour>-<n>.(jpg|png|webp)
Writes  index.html, shop/index.html, shop/<category>/index.html, products/<handle>/index.html,
        assets/products/<handle>/web/* (4:5 crops at 480/960/1600 px, when Pillow is installed)

Standard library only; Pillow is optional (photo cropping/resizing). Markup comes from components.py.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import components as C  # noqa: E402
from components import e, icon, money  # noqa: E402

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
PHOTOS = ROOT / "assets" / "products"
WIDTHS = (480, 960, 1600)
RATIO = 4 / 5
ANGLES = ("front", "back", "detail", "fabric")
ANGLE_LABEL = {"front": "front", "back": "back", "detail": "detail", "fabric": "fabric close-up"}

try:
    from PIL import Image, ImageOps
except ImportError:  # photos are still used, just not cropped/resized
    Image = None


def fail(msg: str):
    sys.exit(f"\n  Build stopped: {msg}\n")


# ---------------------------------------------------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------------------------------------------------

store = json.loads((DATA / "store.json").read_text())
catalog = json.loads((DATA / "catalog.json").read_text())["products"]
SYM = store["currency_symbol"]
LOW = store["low_stock_threshold"]
CATS = store["categories"]
CAT_BY = {c["handle"]: c for c in CATS}
REQUIRED = ("handle", "style", "title", "category", "silhouette", "price", "colours", "sizes", "stock", "description")


def validate():
    seen, styles = set(), set()
    for i, p in enumerate(catalog):
        for f in REQUIRED:
            if f not in p:
                fail(f"product #{i + 1} ({p.get('handle', '?')}) is missing '{f}'")
        if p["handle"] in seen:
            fail(f"duplicate handle '{p['handle']}'")
        if p["style"] in styles:
            fail(f"duplicate style number '{p['style']}'")
        if not re.fullmatch(r"[a-z0-9-]+", p["handle"]):
            fail(f"handle '{p['handle']}' may only use a-z, 0-9 and -")
        if p["category"] not in CAT_BY:
            fail(f"'{p['handle']}' has unknown category '{p['category']}'")
        for c in p["colours"]:
            if c["handle"] not in p["stock"]:
                fail(f"'{p['handle']}' has no stock row for colour '{c['handle']}'")
            missing = [s for s in p["sizes"] if s not in p["stock"][c["handle"]]]
            if missing:
                fail(f"'{p['handle']}' / {c['handle']} has no stock for sizes {missing}")
        seen.add(p["handle"])
        styles.add(p["style"])


# ---------------------------------------------------------------------------------------------------------------------
# Photos: everything is centre-cropped to exactly 4:5. Fallback is placeholder art in the same frame.
# ---------------------------------------------------------------------------------------------------------------------

PHOTO_RE = re.compile(r"^(?P<colour>[a-z0-9-]+)-(?P<n>\d+)\.(jpe?g|png|webp)$", re.I)
warnings: list[str] = []


def crop_45(im):
    w, h = im.size
    if abs(w / h - RATIO) < 0.005:
        return im
    if w / h > RATIO:  # too wide
        nw = round(h * RATIO)
        left = (w - nw) // 2
        return im.crop((left, 0, left + nw, h))
    nh = round(w / RATIO)
    top = (h - nh) // 2
    return im.crop((0, top, w, top + nh))


def process_photos(handle: str) -> dict[str, list[Path]]:
    """Returns {colour: [web base paths]} for photos found in assets/products/<handle>/."""
    folder = PHOTOS / handle
    found: dict[str, list[tuple[int, Path]]] = {}
    if not folder.is_dir():
        return {}
    for f in sorted(folder.iterdir()):
        m = PHOTO_RE.match(f.name)
        if m:
            found.setdefault(m["colour"].lower(), []).append((int(m["n"]), f))
    out: dict[str, list[Path]] = {}
    web = folder / "web"
    for colour, files in found.items():
        for _, src in sorted(files):
            stem = src.stem.lower()
            if Image is None:
                warnings.append(f"Pillow not installed: {handle}/{src.name} used as-is (CSS still crops it to 4:5)")
                out.setdefault(colour, []).append(src)
                continue
            web.mkdir(exist_ok=True)
            target = web / f"{stem}-1200.jpg"
            if not target.exists() or target.stat().st_mtime < src.stat().st_mtime:
                with Image.open(src) as im:
                    im = crop_45(ImageOps.exif_transpose(im).convert("RGB"))
                    if im.width < 1200:
                        warnings.append(f"{handle}/{src.name} is only {im.width}px wide (1600 x 2000 recommended)")
                    for w in WIDTHS:
                        im.resize((w, round(w / RATIO)), Image.LANCZOS).save(web / f"{stem}-{w}.webp", "WEBP", quality=82)
                    im.resize((1200, 1500), Image.LANCZOS).save(target, "JPEG", quality=84, optimize=True, progressive=True)
            out.setdefault(colour, []).append(web / stem)
    return out


def photo_view(path: Path, root: str) -> dict:
    rel = path.relative_to(ROOT).as_posix()
    if path.suffix:  # unprocessed original
        return {"kind": "img", "src": root + rel, "webp": root + rel}
    return {"kind": "img", "src": f"{root}{rel}-1200.jpg",
            "webp": ", ".join(f"{root}{rel}-{w}.webp {w}w" for w in WIDTHS)}


# ---------------------------------------------------------------------------------------------------------------------
# Derived product data
# ---------------------------------------------------------------------------------------------------------------------


def prepare(root: str):
    """Adds media, availability and card data to every product for pages at depth `root`."""
    for i, p in enumerate(catalog):
        photos = PHOTO_CACHE[p["handle"]]
        p["index"] = i
        p["media"] = {}
        for c in p["colours"]:
            if photos.get(c["handle"]):
                views = [photo_view(x, root) for x in photos[c["handle"]]]
                if len(views) == 1:  # the card needs an alternate angle: fall back to the same photo
                    views.append(views[0])
            else:
                views = [{"kind": "svg", "sil": p["silhouette"], "hex": c["hex"], "angle": a} for a in ANGLES]
            p["media"][c["handle"]] = views
        p["in_stock"] = {c: [s for s in p["sizes"] if row.get(s, 0) > 0] for c, row in p["stock"].items()}
        total = sum(sum(row.values()) for row in p["stock"].values())
        p["sold_out"] = total == 0
        p["low_stock"] = 0 < total <= LOW * 4
        p["card_colours"] = [{
            "h": c["handle"], "n": c["name"], "hex": c["hex"], "f": c["family"],
            "img": [v["webp"] for v in p["media"][c["handle"]][:2]] if p["media"][c["handle"]][0]["kind"] == "img" else None,
            "src": [v["src"] for v in p["media"][c["handle"]][:2]] if p["media"][c["handle"]][0]["kind"] == "img" else None,
            "stock": p["stock"][c["handle"]],
        } for c in p["colours"]]


def size_groups(products) -> list[tuple[str, list[str]]]:
    alpha, waist = [], []
    for p in products:
        for s in p["sizes"]:
            target = waist if s.isdigit() else alpha
            if s not in target:
                target.append(s)
    order = ["XS", "S", "M", "L", "XL", "XXL"]
    alpha.sort(key=lambda s: order.index(s) if s in order else 99)
    waist.sort(key=int)
    groups = []
    if alpha:
        groups.append(("Tops & outerwear", alpha))
    if waist:
        groups.append(("Waist (inches)", waist))
    return groups


# ---------------------------------------------------------------------------------------------------------------------
# Page shell
# ---------------------------------------------------------------------------------------------------------------------

SPRITE = (ROOT / "assets" / "sprite.svg").read_text() if (ROOT / "assets" / "sprite.svg").exists() else ""


# Brand assets: the logo as inline SVG parts and the social icons (src/brand-defs.html, written by
# tools/make_brand.py), logo files (assets/brand/), fonts (assets/fonts/), social links and business details
# (data/store.json). One source of truth for the identity.
BRAND_DEFS = (ROOT / "src" / "brand-defs.html").read_text()


def logo(cls: str = "", label: str = "Archive 88") -> str:
    """The primary lockup: ARCHIVE and the eights. The star between the eights is its own element (blaze), so it
    can turn on hover. Sizes come from tools/make_brand.py."""
    aria = f'role="img" aria-label="{e(label)}"' if label else 'aria-hidden="true" focusable="false"'
    return (f'<svg class="logo {cls}" viewBox="0 0 539.51 64.13" {aria}><use href="#lg-name"/>'
            f'<use href="#lg-star" class="logo__star"/><use href="#lg-88"/></svg>')


def emblem(cls: str = "") -> str:
    """The eights on their own, with the star (decorative)."""
    return (f'<svg class="emblem {cls}" viewBox="0 0 200 188" aria-hidden="true" focusable="false">'
            f'<use href="#lg-mark-star" class="emblem__star"/><use href="#lg-mark"/></svg>')


def pine(cls: str = "") -> str:
    return f'<svg class="pine {cls}" viewBox="0 0 80 150" aria-hidden="true" focusable="false"><use href="#lg-pine"/></svg>'


def social_links(cls: str = "") -> str:
    return "".join(
        f'<li><a class="{cls}" href="{e(store["social"][k])}" target="_blank" rel="noopener noreferrer">'
        f'{label}<span class="sr-only"> (opens in a new tab)</span></a></li>'
        for k, label in (("instagram", "Instagram"), ("facebook", "Facebook")))


def head(title: str, desc: str, root: str, canonical: str, jsonld: list | None = None, preload: str = "") -> str:
    ld = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in (jsonld or []))
    return f'''<!doctype html>
<!-- GENERATED by build.py. Edit data/, components.py or build.py, not this file. -->
<html lang="{store["locale"]}" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#F7F5EF" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0E1813" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website"><meta property="og:site_name" content="{e(store["name"])}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{e(store["url"])}assets/img/og-image.jpg"><meta property="og:url" content="{e(canonical)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{root}assets/img/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{root}assets/img/apple-touch-icon.png">
<link rel="manifest" href="{root}site.webmanifest">
<link rel="preload" href="{root}assets/fonts/rokkitt-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{root}assets/fonts/geist-latin.woff2" as="font" type="font/woff2" crossorigin>
{preload}<link rel="stylesheet" href="{root}assets/fonts/fonts.css">
<link rel="stylesheet" href="{root}assets/css/tokens.css">
<link rel="stylesheet" href="{root}assets/css/store.css">
<script>document.documentElement.classList.replace("no-js","js");try{{var t=localStorage.getItem("a88-theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}}catch(e){{}}</script>
{ld}
</head>'''


def announce_bar(root: str) -> str:
    """Rotating messages above the header. Pauses on hover/focus, has a pause button (WCAG 2.2.2), and stays on the
    first message with reduced motion."""
    items = []
    for i, (msg, text, href) in enumerate(store["announcements"]):
        link = f' <a href="{root}{e(href)}">{e(text)}</a>' if href else ""
        state = ' is-active"' if i == 0 else '" aria-hidden="true"'
        items.append(f'<li class="announce__item{state}>{e(msg)}{link}</li>')
    return f'''<div class="announce" data-announce role="region" aria-label="Offers and services" aria-roledescription="carousel">
  <button type="button" class="announce__btn announce__btn--prev" data-announce-step="-1" aria-label="Previous message">{icon("chevron")}</button>
  <ul class="announce__list" aria-live="off">{"".join(items)}</ul>
  <button type="button" class="announce__btn announce__btn--next" data-announce-step="1" aria-label="Next message">{icon("chevron")}</button>
  <button type="button" class="announce__pause" data-announce-pause aria-pressed="false"><span class="sr-only">Pause messages</span>{icon("pause")}</button>
</div>'''


def counts() -> dict:
    return {c["handle"]: sum(1 for p in catalog if p["category"] == c["handle"]) for c in CATS}


def mega(root: str) -> str:
    """Desktop mega-menu under "Shop": featured links, categories with counts, sizes, and two editorial tiles."""
    n = counts()
    cats = "".join(f'<li><a href="{root}shop/{c["handle"]}/">{e(c["title"])} <span class="count">{n[c["handle"]]}</span></a></li>' for c in CATS)
    alpha = [s for s in ("XS", "S", "M", "L", "XL", "XXL")]
    sizes = "".join(f'<li><a class="size-link" href="{root}shop/?size={s}" aria-label="Shop size {s}">{s}</a></li>' for s in alpha)
    waists = "".join(f'<li><a class="size-link" href="{root}shop/trousers/?size={s}" aria-label="Shop trousers, {s} inch waist">{s}</a></li>' for s in ("28", "30", "32", "34", "36"))
    tiles = "".join(
        f'<li><a class="mega__tile" href="{root}{href}"><span class="mega__img"><img src="{root}assets/img/{img}" alt="" width="720" height="900" loading="lazy" decoding="async"></span>'
        f'<span class="mega__tile-title">{e(t)}</span><span class="mega__tile-cta">Shop now</span></a></li>'
        for img, t, href in (("menu-2.jpg", "Outerwear for weather", "shop/outerwear/"), ("menu-4.jpg", "Knitwear, spun slow", "shop/knitwear/")))
    return f'''<div class="mega" id="mega-shop" data-mega-panel hidden>
  <div class="mega__inner">
    <div class="mega__col"><p class="mega__head">Featured</p><ul class="mega__list">
      <li><a href="{root}shop/?sort=new">New in</a></li><li><a href="{root}shop/">Shop all <span class="count">{len(catalog)}</span></a></li>
      <li><a href="{root}gift-cards/">Gift cards</a></li><li><a href="{root}returns/">Delivery &amp; returns</a></li></ul></div>
    <div class="mega__col"><p class="mega__head">Clothing</p><ul class="mega__list">{cats}</ul></div>
    <div class="mega__col"><p class="mega__head">Shop by size</p><ul class="mega__sizes">{sizes}</ul>
      <p class="mega__head mega__head--sub">Waist (in)</p><ul class="mega__sizes">{waists}</ul>
      <a class="link-arrow mega__guide" href="{root}size-guide/">Size guide {icon("arrow")}</a></div>
    <ul class="mega__tiles">{tiles}</ul>
  </div>
</div>
<div class="mega-scrim" data-mega-scrim hidden></div>'''


def header(root: str, active: str | None = None) -> str:
    def cur(key):
        return ' aria-current="page"' if key == active else ""
    links = [("new", "shop/?sort=new", "New in"), ("outerwear", "shop/outerwear/", "Outerwear"),
             ("knitwear", "shop/knitwear/", "Knitwear"), ("gift", "gift-cards/", "Gift cards")]
    lis = "".join(f'<li><a class="nav__link" href="{root}{u}"{cur(k)}>{t}</a></li>' for k, u, t in links)
    return f'''<a class="skip" href="#main">Skip to content</a>
{announce_bar(root)}
<header class="nav" data-nav-root>
  <div class="nav__bar">
    <a class="nav__logo" href="{root}" aria-label="{e(store["name"])}, home">{logo(label="")}</a>
    <nav class="nav__primary" aria-label="Main">
      <ul>
        <li><button type="button" class="nav__link nav__link--mega" data-mega aria-expanded="false" aria-controls="mega-shop">Shop {icon("chevron")}</button>
          {mega(root)}</li>
        {lis}
      </ul>
    </nav>
    <div class="nav__tools">
      <button type="button" class="nav__tool" data-drawer-open="search" aria-controls="search" aria-expanded="false">{icon("search")}<span class="nav__tool-label">Search</span></button>
      <button type="button" class="nav__tool nav__cart" data-drawer-open="cart" aria-controls="cart" aria-expanded="false" aria-label="Bag, 0 items" data-bag-btn>
        {icon("bag")}<span class="nav__tool-label">Bag</span><span class="nav__count" data-bag-count data-empty>0</span></button>
      <button type="button" class="nav__tool nav__menu" data-drawer-open="menu" aria-controls="menu" aria-expanded="false">{icon("menu")}<span class="sr-only">Menu</span></button>
    </div>
  </div>
</header>'''


def promises() -> str:
    items = "".join(f'<li>{icon(i)}<p><strong>{e(a)}</strong><span>{e(b)}</span></p></li>' for i, a, b in store["promises"])
    return f'<section class="promises" aria-label="Our promises"><ul>{items}</ul></section>'


def signup() -> str:
    return '''<section class="signup" aria-labelledby="signup-title">
  <div class="signup__inner">
    <div><h2 class="section-title" id="signup-title">First to know</h2>
    <p class="signup__lead">One email when a new piece is ready. Nothing else.</p></div>
    <form class="signup__form" data-signup novalidate>
      <div class="field signup__field">
        <label class="field__label" for="signup-email">Email address</label>
        <div class="signup__row"><input type="email" id="signup-email" name="email" autocomplete="email" inputmode="email" required aria-describedby="signup-msg">
        <button type="submit" class="btn btn--primary">Subscribe</button></div>
        <p class="signup__msg" id="signup-msg" data-signup-msg aria-live="polite">You can unsubscribe at any time.</p>
      </div>
    </form>
  </div>
</section>'''


def footer(root: str) -> str:
    cats = "".join(f'<li><a href="{root}shop/{c["handle"]}/">{e(c["title"])}</a></li>' for c in CATS)
    col = lambda title, body: f'<div class="footer__col"><h2 class="footer__head">{title}</h2><ul>{body}</ul></div>'
    return f'''{promises()}
{signup()}
<footer class="footer" data-nav="dark">
  <div class="footer__top">
    <div class="footer__brand">{emblem()}<p>{e(store["tagline"])}.<br>{e(store["established"])}.</p></div>
    <div class="footer__cols">
      {col("Shop", f'<li><a href="{root}shop/?sort=new">New in</a></li><li><a href="{root}shop/">Shop all</a></li>{cats}<li><a href="{root}gift-cards/">Gift cards</a></li>')}
      {col("Help", f'<li><a href="{root}size-guide/">Size guide</a></li><li><a href="{root}returns/">Delivery &amp; returns</a></li><li><a href="{root}contact/">Contact</a></li>')}
      {col("Archive 88", f'<li><a href="{root}about/">About</a></li>')}
      {col("Follow", social_links())}
    </div>
  </div>
  <div class="footer__legal">
    <p>© {date.today().year} {e(store["name"])}</p>
    <ul><li><a href="{root}privacy/">Privacy</a></li><li><a href="{root}terms/">Terms of sale</a></li></ul>
    <p>United Kingdom, £ GBP</p>
    <button type="button" class="theme-switch" data-theme-switch hidden>Theme: <span data-theme-label>Auto</span></button>
  </div>
  <a class="footer__logo" href="{root}" aria-label="{e(store["name"])}, home">{logo(label="")}</a>
</footer>'''


def cart_drawer() -> str:
    th = store["free_shipping_threshold"]
    body = f'''<div class="ship-meter" data-ship-meter data-threshold="{th}">
  <p class="ship-meter__text" data-ship-text>Free UK delivery on orders over {money(th, SYM)}</p>
  <div class="ship-meter__track"><span class="ship-meter__bar" data-ship-bar></span></div>
</div>
<ul class="cart-lines" data-cart-lines aria-label="Items in your bag"></ul>
<div class="cart-empty" data-cart-empty hidden>
  <p class="cart-empty__title">Your bag is empty</p>
  <p>Start with the pieces people ask for most.</p>
  <a class="btn btn--secondary" href="__ROOT__shop/">Shop all</a>
</div>'''
    foot = f'''<dl class="cart-total"><dt>Subtotal</dt><dd data-cart-subtotal>{money(0, SYM)}</dd></dl>
<p class="cart-note">Delivery and taxes calculated at checkout.</p>
<button type="button" class="btn btn--primary btn--block cart__checkout" data-checkout>Checkout</button>
<p class="cart-msg" data-checkout-msg aria-live="polite"></p>'''
    return C.drawer("cart", "Bag", body, footer=foot, label_extra=' <span class="drawer__count" data-drawer-count></span>')


def count_span(k) -> str:
    return f'<span class="count">{k}</span>' if k else ""


def menu_drawer(root: str) -> str:
    """Phones and tablets: the whole navigation in one panel from the left."""
    n = counts()
    rows = [("shop/?sort=new", "New in", None), ("shop/", "Shop all", len(catalog))] + \
           [(f'shop/{c["handle"]}/', c["title"], n[c["handle"]]) for c in CATS] + [("gift-cards/", "Gift cards", None)]
    items = "".join(
        f'<li><a href="{root}{u}"><span>{e(t)}</span>{count_span(k)}{icon("chevron")}</a></li>'
        for u, t, k in rows)
    body = (f'<ul class="menu__list">{items}</ul>'
            f'<ul class="menu__sizes" aria-label="Shop by size">'
            + "".join(f'<li><a class="size-link" href="{root}shop/?size={s}" aria-label="Shop size {s}">{s}</a></li>' for s in ("XS", "S", "M", "L", "XL", "XXL"))
            + f'</ul><ul class="menu__links"><li><a href="{root}size-guide/">Size guide</a></li><li><a href="{root}returns/">Delivery &amp; returns</a></li>'
            f'<li><a href="{root}contact/">Contact</a></li><li><a href="{root}about/">About</a></li></ul>'
            f'<ul class="menu__social">{social_links()}</ul>')
    return C.drawer("menu", "Menu", body, side="left")


def search_drawer(root: str) -> str:
    """Search panel from the top. Results come from search.json (written by the build), loaded on first open."""
    pop = "".join(f'<li><a class="chip-link" href="{root}shop/{c["handle"]}/">{e(c["title"])}</a></li>' for c in CATS)
    body = f'''<form class="search" role="search" data-search action="{root}shop/">
  <label class="sr-only" for="search-q">Search products</label>
  {icon("search")}<input type="search" id="search-q" name="q" placeholder="Search coats, knitwear, colours" autocomplete="off" enterkeyhint="search" aria-describedby="search-count">
  <button type="reset" class="search__clear" data-search-clear hidden>Clear</button>
</form>
<div class="search__suggest" data-search-suggest><p class="search__label">Popular categories</p><ul class="chip-links">{pop}</ul></div>
<p class="search__count" id="search-count" data-search-count aria-live="polite"></p>
<ul class="search__results" data-search-results></ul>'''
    return C.drawer("search", "Search", body, side="top")


def page(*, title, desc, root, path, main, active=None, scripts=(), jsonld=None, extra="", tone="light",
         pre="", preload="") -> str:
    canonical = store["url"] + path
    cfg = {"root": root, "currency": store["currency"], "symbol": SYM, "locale": store["locale"],
           "freeShipping": store["free_shipping_threshold"], "lowStock": LOW, "shopify": store.get("shopify_domain", "")}
    js = "".join(f'<script src="{root}assets/js/{s}.js" defer></script>' for s in ("store", "motion", *scripts))
    return (head(title, desc, root, canonical, jsonld, preload) +
            f'\n<body data-tone="{tone}">\n{pre}{BRAND_DEFS}\n{SPRITE}\n{header(root, active)}\n<main id="main">\n{main}\n</main>\n{footer(root)}\n'
            f'{cart_drawer().replace("__ROOT__", root)}\n{menu_drawer(root)}\n{search_drawer(root)}\n{extra}\n'
            f'<div class="toast" data-toast role="status" aria-live="polite"></div>\n'
            f'{C.json_script("store-config", cfg)}\n{js}\n</body>\n</html>\n')


def write(path: str, html: str):
    out = ROOT / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)


def breadcrumbs(items: list[tuple[str, str | None]]) -> str:
    lis = "".join(f'<li><a href="{e(u)}">{e(t)}</a></li>' if u else f'<li aria-current="page">{e(t)}</li>' for t, u in items)
    return f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{lis}</ol></nav>'


# ---------------------------------------------------------------------------------------------------------------------
# PLP
# ---------------------------------------------------------------------------------------------------------------------


def plp(category: dict | None):
    root = "../" if category is None else "../../"
    prepare(root)
    items = [p for p in catalog if category is None or p["category"] == category["handle"]]
    items.sort(key=lambda p: p["rank"])  # "Featured" order
    counts_ = counts()
    families = sorted({c["family"] for p in items for c in p["colours"]})
    title = category["title"] if category else "Shop all"
    intro = category["intro"] if category else store["description"]
    cards = "\n".join(C.product_card(p, root, SYM, eager=i < 4) for i, p in enumerate(items))
    filters = (C.filter_group("Category", C.category_links(CATS, category and category["handle"], counts_, len(catalog), root), gid="category")
               + C.filter_group("Size", C.size_chips(size_groups(items)), gid="size")
               + C.filter_group("Colour", C.colour_filters(families), gid="colour"))
    page_size = store["page_size"]
    here = category and category["handle"]
    pills = ('<nav class="pills" aria-label="Categories"><ul>'
             + f'<li><a class="pill" href="{root}shop/"{" aria-current=page" if not here else ""}>All</a></li>'
             + "".join(f'<li><a class="pill" href="{root}shop/{c["handle"]}/"{" aria-current=page" if c["handle"] == here else ""}>{e(c["title"])}</a></li>' for c in CATS)
             + '</ul></nav>')
    main = f'''<div class="plp" data-plp data-page-size="{page_size}">
  <header class="plp__head">
    {breadcrumbs([("Home", root), ("Shop", root + "shop/" if category else None)] + ([(title, None)] if category else []))}
    <h1 class="page-title">{e(title)} <span class="page-title__count">{len(items)}</span></h1>
    <p class="plp__intro">{e(intro)}</p>
    {pills}
  </header>
  <div class="plp__toolbar">
    <button type="button" class="btn btn--secondary plp__filter-btn" data-drawer-open="filters" aria-controls="filters">{icon("filter")} Filter <span class="plp__filter-n" data-filter-n></span></button>
    <p class="plp__count" data-result-count aria-live="polite">{len(items)} styles</p>
    <div class="active-filters" data-active-filters></div>
    <label class="sort"><span>Sort</span>
      <select name="sort" data-sort>
        <option value="featured">Featured</option><option value="new">New in</option>
        <option value="price-asc">Price, low to high</option><option value="price-desc">Price, high to low</option>
      </select>{icon("chevron")}</label>
  </div>
  <div class="plp__layout">
    <aside class="plp__filters drawer drawer--left drawer--inline" id="filters" aria-labelledby="filters-title" data-drawer-persistent>
      <div class="drawer__scrim" data-drawer-close></div>
      <form class="drawer__panel" data-filter-form tabindex="-1">
        <header class="drawer__head"><h2 class="drawer__title" id="filters-title">Filter</h2>
          <button type="button" class="drawer__close" data-drawer-close>Close</button></header>
        <div class="drawer__body">{filters}</div>
        <div class="drawer__foot plp__filters-foot">
          <button type="reset" class="btn btn--secondary" data-clear-filters>Clear all</button>
          <button type="button" class="btn btn--primary" data-drawer-close data-show-results>Show {len(items)} styles</button>
        </div>
      </form>
    </aside>
    <section class="plp__results" aria-labelledby="results-title">
      <h2 class="sr-only" id="results-title">Products</h2>
      <div class="grid" data-grid>
{cards}
      </div>
      <div class="plp__empty" data-empty hidden>
        <p class="plp__empty-title">Nothing matches those filters</p>
        <p>Try another size or colour, or clear the filters.</p>
        <button type="button" class="btn btn--secondary" data-clear-filters>Clear filters</button>
      </div>
      <div class="pager" data-pager>
        <p class="pager__text" data-pager-text>Showing {min(page_size, len(items))} of {len(items)}</p>
        <div class="pager__track"><span class="pager__bar" data-pager-bar></span></div>
        <button type="button" class="btn btn--secondary" data-load-more>Load more</button>
      </div>
    </section>
  </div>
</div>'''
    path = "shop/" + (category["handle"] + "/" if category else "")
    write(path + "index.html", page(
        title=f'{title} | {store["name"]}', desc=intro, root=root, path=path, main=main,
        active=category["handle"] if category else None, scripts=("plp",)))


# ---------------------------------------------------------------------------------------------------------------------
# PDP
# ---------------------------------------------------------------------------------------------------------------------


def pdp(p: dict):
    root = "../../"
    cat = CAT_BY[p["category"]]
    sets = []
    for i, c in enumerate(p["colours"]):
        frames = ""
        for n, v in enumerate(p["media"][c["handle"]]):
            alt = f'{p["title"]} in {c["name"]}, {ANGLE_LABEL.get(v.get("angle"), "view " + str(n + 1))}'
            img = C.media(v, alt, sizes="(min-width: 1000px) 30vw, 100vw", eager=(i == 0 and n == 0))
            frames += f'<li class="gallery__slide">{C.frame(img)}</li>'
        sets.append(f'<ul class="gallery__set" data-colour="{e(c["handle"])}" {"hidden" if i else ""} aria-label="{e(c["name"])} images">{frames}</ul>')
    count = len(p["media"][p["colours"][0]["handle"]])
    gallery = (f'<section class="gallery" aria-label="Product images" data-gallery data-vt-target>{"".join(sets)}'
               f'<p class="gallery__pager" aria-hidden="true"><span data-gallery-index>1</span> / <span data-gallery-total>{count}</span></p></section>')

    th = store["free_shipping_threshold"]
    details = (f'<p>{e(p["description"])}</p><ul class="spec"><li><span>Composition</span>{e(p.get("material", ""))}</li>'
               f'<li><span>Care</span>{e(p.get("care", ""))}</li><li><span>Origin</span>{e(p.get("origin", ""))}</li>'
               f'<li><span>Style</span>{e(p["style"])}</li></ul>')
    fit = (f'<p>{e(p.get("fit", ""))}.</p><p>Between sizes? Take your usual size for a close fit, or size up for room to layer.</p>'
           f'<p><a href="{root}size-guide/">Full size guide</a></p>')
    delivery = (f'<p>Free UK delivery on orders over {money(th, SYM)}; otherwise {money(5, SYM)}. Dispatched within 1 to 2 working days.</p>'
                f'<p>Free returns within 30 days, from your door.</p>')

    number = p["style"].split("-")[-1]
    info = f'''<div class="pdp__info">
  <div class="pdp__sticky">
    <p class="pdp__meta"><a href="{root}shop/{cat["handle"]}/">{e(cat["title"])}</a><span>No. {e(number)}</span></p>
    <h1 class="pdp__title">{e(p["title"])}</h1>
    <div class="pdp__price">{C.price(p, SYM)}</div>
    <form class="buy" data-buy novalidate>
      {C.colour_selector(p)}
      {C.size_selector(p, root)}
      <p class="stock-msg" data-stock-msg aria-live="polite"></p>
      <button type="submit" class="buy-btn" data-atc><span data-atc-label>Add to bag</span></button>
    </form>
    <ul class="pdp__note"><li>{icon("truck")}Free UK delivery over {money(th, SYM)}</li><li>{icon("return")}Free returns within 30 days</li></ul>
    <div class="pdp__details">
      {C.accordion("Details & composition", details, "details-info", open_=True)}
      {C.accordion("Size & fit", fit, "details-fit")}
      {C.accordion("Availability", C.variant_matrix(p, LOW), "details-availability")}
      {C.accordion("Delivery & returns", delivery, "details-delivery")}
    </div>
  </div>
</div>'''

    prepare_for = [q for q in catalog if q["category"] == p["category"] and q["handle"] != p["handle"]]
    prepare_for.sort(key=lambda q: abs(q["price"] - p["price"]))
    recs = "".join(C.product_card(q, root, SYM, quick_add=False) for q in prepare_for[:10])

    matrix = {
        "handle": p["handle"], "style": p["style"], "title": p["title"], "price": p["price"], "sil": p["silhouette"],
        "url": f'{root}products/{p["handle"]}/', "sizes": p["sizes"], "stock": p["stock"],
        "colours": [{"h": c["handle"], "n": c["name"], "hex": c["hex"],
                     "img": p["media"][c["handle"]][0].get("src")} for c in p["colours"]],
        "ids": p.get("shopify_variant_ids", {}),
    }
    main = f'''<div class="pdp" data-pdp>
  {breadcrumbs([("Shop", root + "shop/"), (cat["title"], root + "shop/" + cat["handle"] + "/"), (p["title"], None)])}
  <div class="pdp__layout">{gallery}{info}</div>
</div>
{C.rail("recs", "You may also like", recs, link=("Shop " + cat["title"].lower(), root + "shop/" + cat["handle"] + "/"))}
{C.json_script("variant-matrix", matrix)}'''

    size_sheet = C.drawer("size-sheet", "Select a size", '<div class="size-sheet" data-size-sheet></div>', side="bottom")
    offers = [{"@type": "Offer", "sku": f'{p["style"]}-{c["handle"].upper()}-{s}', "price": p["price"],
               "priceCurrency": store["currency"], "itemCondition": "https://schema.org/NewCondition",
               "availability": "https://schema.org/" + ("InStock" if p["stock"][c["handle"]][s] else "OutOfStock")}
              for c in p["colours"] for s in p["sizes"]]
    ld = [{"@context": "https://schema.org", "@type": "Product", "name": p["title"], "sku": p["style"],
           "description": p["description"], "brand": {"@type": "Brand", "name": store["name"]},
           "category": cat["title"], "color": ", ".join(c["name"] for c in p["colours"]), "offers": offers}]
    path = f'products/{p["handle"]}/'
    write(path + "index.html", page(
        title=f'{p["title"]} | {store["name"]}', desc=p["description"], root=root, path=path, main=main,
        active=p["category"], scripts=("pdp",), jsonld=ld, extra=C.sticky_atc(p, SYM) + size_sheet))


# ---------------------------------------------------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------------------------------------------------


def ranked() -> list:
    return sorted(catalog, key=lambda p: p["rank"])


def mark_bestsellers():
    """Bestsellers: the top-ranked styles that aren't new this season."""
    for i, p in enumerate([p for p in ranked() if not p.get("new")]):
        p["best"] = i < 12


def words(text: str) -> str:
    """Wraps each word so the statement can ink in word by word as it crosses the screen (CSS only)."""
    ws = text.split()
    n = max(len(ws) - 1, 1)
    return " ".join(f'<span class="w" style="--p:{i / n:.3f}">{e(w)}</span>' for i, w in enumerate(ws))


def home():
    """Homepage. All of its words and pictures come from the "home" block in data/store.json."""
    root = ""
    prepare(root)
    n = counts()
    order = ranked()
    h = store["home"]
    newest = [p for p in order if p.get("new")][:12]
    best = [p for p in order if p.get("best")][:5]

    rows, frames = [], []
    for i, c in enumerate(CATS):
        lead = next(p for p in order if p["category"] == c["handle"])
        v = lead["media"][lead["colours"][0]["handle"]][0]
        rows.append(f'<li><a class="index__row" href="shop/{c["handle"]}/" data-index-row="{i}"><span class="index__name">{e(c["title"])}</span>'
                    f'<span class="index__meta">{n[c["handle"]]} styles</span>{icon("arrow")}</a></li>')
        frames.append(f'<div class="index__frame{" is-active" if i == 0 else ""}" data-index-frame="{i}">{C.frame(C.media(v, ""))}</div>')

    phrases = "".join(f'<span>{e(t)}</span>{emblem()}' for t in h["band"] * 2)
    band = f'<div class="band__group">{phrases}</div><div class="band__group" aria-hidden="true">{phrases}</div>'

    def visual(s):
        """A story's picture: a photo ("image") or one of the brand illustrations ("art": "eights" or "forest")."""
        if s.get("art") == "eights":
            return f'<span class="story__img story__art story__art--eights" aria-hidden="true">{emblem()}</span>'
        if s.get("art") == "forest":
            return (f'<span class="story__img story__art story__art--forest" aria-hidden="true">'
                    f'<svg class="story__star" viewBox="0 0 52.5 88"><use href="#lg-loz"/></svg>'
                    f'<span class="story__pines">{pine() * 7}</span></span>')
        return (f'<span class="story__img"><img src="{root}assets/img/{e(s["image"])}" alt="{e(s.get("alt", ""))}" '
                f'width="720" height="900" loading="lazy" decoding="async"></span>')

    stories = "".join(
        f'<a class="story__item story__item--{"ab"[i]} reveal" href="{e(s["href"])}">'
        f'{visual(s)}'
        f'<span class="story__title">{e(s["title"])}</span><span class="story__text">{e(s["text"])}</span>'
        f'<span class="link-arrow">{e(s["cta"])} {icon("arrow")}</span></a>'
        for i, s in enumerate(h["stories"][:2]))

    wanted = "".join(C.product_card(p, root, SYM, cls="card--feature reveal" if i == 0 else "reveal") for i, p in enumerate(best))
    lines = "".join(f'<span class="line"><span>{e(t)}</span></span>' for t in h["hero_title"])
    b = h["banner"]

    main = f'''<section class="hero" data-nav="dark" data-nav-clear aria-labelledby="hero-title">
  <div class="hero__film" aria-hidden="true">
    <video class="hero__video" muted loop playsinline preload="metadata" poster="{root}assets/img/forest-poster.jpg">
      <source src="{root}assets/video/forest-portrait.mp4" type="video/mp4" media="(max-width: 720px) and (orientation: portrait)">
      <source src="{root}assets/video/forest.mp4" type="video/mp4">
    </video>
    <div class="hero__shade"></div>
  </div>
  <div class="hero__content">
    <h1 class="hero__title" id="hero-title">{lines}</h1>
    <p class="hero__lead">{e(h["hero_lead"])}</p>
    <div class="hero__cta"><a class="btn btn--light" href="shop/">Shop the archive</a><a class="btn btn--ghost" href="shop/?sort=new">New in</a></div>
  </div>
  <div class="hero__seal" aria-hidden="true"><img src="{root}assets/brand/seal-ring.svg" alt="" width="240" height="240">{emblem()}</div>
  <button type="button" class="hero__toggle" data-film-toggle aria-pressed="false" hidden>
    {icon("pause")}<span class="sr-only" data-film-label>Pause film</span></button>
</section>
<div class="band" aria-label="{e(", ".join(h["band"]))}" role="img"><div class="band__track" aria-hidden="true">{band}</div></div>
{C.rail("new", "New in", "".join(C.product_card(p, root, SYM, eager=i < 2) for i, p in enumerate(newest)), link=("See all", "shop/?sort=new"))}
<section class="manifesto" aria-label="About {e(store["name"])}">
  <p class="manifesto__text">{words(h["statement"])}</p>
  <a class="link-arrow" href="{root}about/">Our story {icon("arrow")}</a>
</section>
<section class="index" aria-labelledby="index-title">
  <div class="section-head"><h2 class="section-title" id="index-title">The archive, by category</h2>
    <a class="link-arrow" href="shop/">All {len(catalog)} styles {icon("arrow")}</a></div>
  <div class="index__layout" data-archive-index>
    <ul class="index__list">{"".join(rows)}</ul>
    <div class="index__stage" aria-hidden="true">{"".join(frames)}</div>
  </div>
</section>
<section class="story" aria-label="From the collection">{stories}</section>
<section class="wanted" aria-labelledby="wanted-title">
  <div class="section-head"><h2 class="section-title" id="wanted-title">Most wanted</h2>
    <a class="link-arrow" href="shop/">Shop all {icon("arrow")}</a></div>
  <div class="wanted__grid">{wanted}</div>
</section>
<section class="banner" data-nav="dark" data-nav-clear aria-labelledby="banner-title">
  <img class="banner__img" src="{root}assets/img/{e(b["image"])}" alt="" width="1280" height="720" loading="lazy" decoding="async">
  <div class="banner__text reveal">
    <h2 class="banner__title" id="banner-title">{e(b["title"])}</h2>
    <p>{e(b["text"])}</p>
    <a class="btn btn--light" href="{root}about/">About Archive 88</a>
  </div>
</section>'''
    ld = [{"@context": "https://schema.org", "@type": "Organization", "name": store["name"], "url": store["url"],
           "logo": store["url"] + "assets/img/icon-512.png", "description": store["description"],
           "sameAs": [store["social"]["instagram"], store["social"]["facebook"]]},
          {"@context": "https://schema.org", "@type": "WebSite", "name": store["name"], "url": store["url"]}]
    write("index.html", page(
        title=f'{store["name"]}: {store["tagline"]}', desc=store["description"], root=root, path="", main=main,
        scripts=("home",), jsonld=ld,
        preload=f'<link rel="preload" href="{root}assets/img/forest-poster.jpg" as="image" fetchpriority="high">\n'))


def search_index():
    """search.json for the header search: one row per style, loaded on first open (about 20 KB)."""
    prepare("")
    rows = []
    for p in ranked():
        c0 = p["colours"][0]
        v = p["media"][c0["handle"]][0]
        rows.append({"t": p["title"], "u": f'products/{p["handle"]}/', "p": p["price"], "c": CAT_BY[p["category"]]["title"],
                     "k": " ".join([p["silhouette"], p.get("material", ""), *(c["name"] for c in p["colours"])]),
                     "n": len(p["colours"]), "h": c0["hex"], "s": p["silhouette"], "i": v.get("src")})
    (ROOT / "search.json").write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")))



# ---------------------------------------------------------------------------------------------------------------------
# Gift cards
# ---------------------------------------------------------------------------------------------------------------------


def gift():
    root = "../"
    g = store["gift_cards"]
    amounts = "".join(
        f'<label class="chip"><input type="radio" name="amount" value="{a}" {"checked" if a == g["default"] else ""}>'
        f'<span>{money(a, SYM)}</span></label>' for a in g["amounts"])
    today = date.today().isoformat()
    email_form = (
        C.field("email-to", "Their name", autocomplete="off", maxlength=40)
        + C.field("email-address", "Their email address", type_="email", autocomplete="off", inputmode="email",
                  hint="We'll send the card here, with your message.")
        + C.field("email-from", "Your name", autocomplete="name", maxlength=40)
        + C.field("email-message", "Message", required=False, maxlength=200, textarea=True, hint="Up to 200 characters.")
        + f'<div class="field"><label class="field__label" for="email-date">Send on</label>'
          f'<input type="date" id="email-date" name="email-date" value="{today}" min="{today}" aria-describedby="email-date-err">'
          f'<p class="field__err" id="email-date-err" aria-live="polite"></p></div>')
    post_form = (
        C.field("post-to", "Their name", autocomplete="off", maxlength=40)
        + C.field("post-line1", "Address line 1", autocomplete="off")
        + C.field("post-line2", "Address line 2", autocomplete="off", required=False)
        + '<div class="field-row">'
        + C.field("post-town", "Town or city", autocomplete="off")
        + C.field("post-postcode", "Postcode", autocomplete="off", maxlength=8)
        + '</div>'
        + C.field("post-from", "Your name", autocomplete="name", maxlength=40)
        + C.field("post-message", "Message", required=False, maxlength=200, textarea=True, hint="Printed inside the card. Up to 200 characters."))

    def buy(method):
        return (f'<button type="submit" class="buy-btn"><span>Add to bag · <span data-gift-price>{money(g["default"], SYM)}</span></span></button>')

    card = f'''<div class="giftcard" data-gift-card data-method="email">
  <div class="giftcard__face">
    <div class="giftcard__top">{logo("giftcard__mark", "")}<span class="giftcard__kind" data-gift-kind>E-gift card</span></div>
    <p class="giftcard__amount" data-gift-amount>{money(g["default"], SYM)}</p>
    <div class="giftcard__foot"><span>For <span data-gift-to>someone good</span></span><span>{e(store["tagline"])}</span></div>
  </div>
</div>'''
    main = f'''<div class="pdp gift" data-gift data-symbol="{e(SYM)}">
  {breadcrumbs([("Shop", root + "shop/"), ("Gift cards", None)])}
  <div class="pdp__layout gift__layout">
    <div class="gift__visual">{card}<p class="gift__caption">Preview. The amount and name update as you go.</p></div>
    <div class="pdp__info"><div class="pdp__sticky">
      <p class="pdp__meta"><span>Gift card</span><span>From {money(min(g["amounts"]), SYM)}</span></p>
      <h1 class="pdp__title">Gift card</h1>
      <p class="pdp__desc">Let them choose. {e(g["terms"])}</p>
      <fieldset class="option gift__amounts"><legend class="option__legend">Amount</legend><div class="chip-grid">{amounts}</div></fieldset>
      <p class="option__legend gift__how" id="gift-how">How should it arrive?</p>
      <div class="gift__methods" role="group" aria-labelledby="gift-how">
        <button type="button" class="gift__method" data-gift-method="email" aria-expanded="false" aria-controls="gift-email">
          <svg class="icon" aria-hidden="true"><use href="#i-mail"/></svg><span><strong>Email a gift card</strong><small>{e(g["email_note"])}</small></span></button>
        <button type="button" class="gift__method" data-gift-method="post" aria-expanded="false" aria-controls="gift-post">
          <svg class="icon" aria-hidden="true"><use href="#i-post"/></svg><span><strong>Post a gift card</strong><small>{e(g["post_note"])}</small></span></button>
      </div>
      <form class="gift__form" id="gift-email" data-gift-form="email" novalidate hidden aria-label="Email a gift card">{email_form}{buy("email")}</form>
      <form class="gift__form" id="gift-post" data-gift-form="post" novalidate hidden aria-label="Post a gift card">{post_form}{buy("post")}</form>
      <div class="pdp__details">
        {C.accordion("How gift cards work", f"<p>{e(g['terms'])}</p><p>The code is entered at checkout. Any balance stays on the card for next time.</p>", "gift-how-it-works", open_=True)}
        {C.accordion("Delivery", f"<p><strong>Email:</strong> {e(g['email_note'])}</p><p><strong>Post:</strong> {e(g['post_note'])}</p>", "gift-delivery")}
      </div>
    </div></div>
  </div>
</div>
{C.json_script("gift-config", {"amounts": g["amounts"], "ids": g.get("shopify_variant_ids", {})})}'''
    write("gift-cards/index.html", page(
        title=f'Gift cards | {store["name"]}', desc=f'{store["name"]} gift cards by email or post. {g["terms"]}',
        root=root, path="gift-cards/", main=main, active="gift", scripts=("gift",)))



# ---------------------------------------------------------------------------------------------------------------------
# Info pages (src/pages/*.html), 404 and sitemap
# ---------------------------------------------------------------------------------------------------------------------

PAGES = ROOT / "src" / "pages"


def fill(text: str, root: str) -> str:
    """{{root}}, {{updated}}, {{shipping_text}}, {{free_threshold}}, {{instagram}} and {{biz:<key>}} from store.json."""
    biz = store["business"]

    def sub(m):
        key = m.group(1)
        if key == "root":
            return root
        if key == "updated":
            return f"{date.today().day} {date.today().strftime('%B %Y')}"
        if key == "shipping_text":
            return e(store["shipping_text"])
        if key == "free_threshold":
            return money(store["free_shipping_threshold"], SYM)
        if key == "instagram":
            return e(store["social"]["instagram"])
        if key.startswith("biz:"):
            name = key[4:]
            if name == "address_inline":
                return e(biz["address"].replace("\n", ", "))
            if name not in biz:
                fail(f"unknown {{{{{key}}}}} in src/pages (not in store.json business)")
            return e(biz[name]).replace("\n", "<br>")
        fail(f"unknown placeholder {{{{{key}}}}} in src/pages")
    return re.sub(r"\{\{([a-z_:]+)\}\}", sub, text)


def info_pages() -> list[str]:
    """Each src/pages/<slug>.html starts with <!-- {"title", "description", "lede", "legal"?} --> and becomes /<slug>/."""
    built = []
    for f in sorted(PAGES.glob("*.html")):
        text = f.read_text()
        m = re.match(r"\s*<!--\s*(\{.*?\})\s*-->\s*", text, re.S)
        if not m:
            fail(f"{f.name} must start with <!-- {{\"title\": ..., \"description\": ...}} -->")
        meta = json.loads(m.group(1))
        slug_, root = f.stem, "../"
        draft = ('<p class="info__note"><strong>Draft.</strong> This is a starting template, not legal advice. '
                 'Have it checked before the shop opens.</p>') if meta.get("legal") and not store.get("legal_reviewed") else ""
        lede = f'<p class="info__lede">{fill(meta["lede"], root)}</p>' if meta.get("lede") else ""
        main = f'''<article class="info">
  {breadcrumbs([("Home", root), (meta["title"], None)])}
  <header class="info__head"><h1 class="page-title">{e(meta["title"])}</h1>{lede}</header>
  {draft}
  <div class="info__body">{fill(text[m.end():], root)}</div>
</article>'''
        shutil.rmtree(ROOT / slug_, ignore_errors=True)
        write(f"{slug_}/index.html", page(title=f'{meta["title"]} | {store["name"]}', desc=fill(meta["description"], root),
                                          root=root, path=f"{slug_}/", main=main, active=slug_))
        built.append(slug_)
    return built


def not_found():
    """404.html. GitHub Pages serves it for any missing path, so links use the site's absolute base path. It also sends
    old addresses on: /storefront/... (before the storefront became the site) and the retired /lookbook/ and /record/."""
    from urllib.parse import urlparse
    base = urlparse(store["url"]).path or "/"
    redirect = f'''<script>(function(){{var b={json.dumps(base)},p=location.pathname,s=b+"storefront/";
if(p.indexOf(s)===0){{location.replace(b+p.slice(s.length)+location.search+location.hash);return;}}
if(/\\/(lookbook|record)(\\/|$)/.test(p.slice(b.length-1))){{location.replace(b+"shop/");}}}})();</script>
'''
    main = f'''<section class="info info--center">
  {emblem()}
  <h1 class="page-title">Page not found</h1>
  <p class="info__lede">That page has moved or doesn't exist. Try the shop, or search for what you were after.</p>
  <p class="info__actions"><a class="btn btn--primary" href="{base}shop/">Shop all</a>
  <button type="button" class="btn btn--secondary" data-drawer-open="search" aria-controls="search">Search</button></p>
</section>'''
    write("404.html", page(title=f'Page not found | {store["name"]}', desc=store["description"], root=base, path="404.html",
                           main=main, pre=redirect).replace('<link rel="canonical"', '<meta name="robots" content="noindex">\n<link rel="canonical"', 1))


def sitemap(info: list[str]):
    urls = ["", "shop/", *(f'shop/{c["handle"]}/' for c in CATS), "gift-cards/", *(f"{s}/" for s in info),
            *(f'products/{p["handle"]}/' for p in ranked())]
    rows = "\n".join(f"  <url><loc>{e(store['url'] + u)}</loc></url>" for u in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}\n</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {store['url']}sitemap.xml\n")
    return len(urls)


# ---------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    validate()
    mark_bestsellers()
    PHOTO_CACHE = {p["handle"]: process_photos(p["handle"]) for p in catalog}
    for d in ("products", "shop", "gift-cards"):
        shutil.rmtree(ROOT / d, ignore_errors=True)
    home()
    search_index()
    gift()
    plp(None)
    for c in CATS:
        plp(c)
    prepare("../../")
    for p in catalog:
        pdp(p)
    prepare("")
    info = info_pages()
    not_found()
    n_urls = sitemap(info)
    variants = sum(len(p["colours"]) * len(p["sizes"]) for p in catalog)
    with_photos = sum(1 for h in PHOTO_CACHE.values() if h)
    print(f"Built {len(catalog)} product pages, {len(CATS) + 1} listing pages, home, gift cards, {len(info)} info pages, 404. "
          f"Sitemap: {n_urls} URLs.")
    print(f"  "
          f"{variants} variants. {with_photos}/{len(catalog)} styles have photos; the rest show placeholder art.")
    for w in sorted(set(warnings)):
        print("  !", w)
