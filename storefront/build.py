#!/usr/bin/env python3
"""Builds the Archive 88 storefront from data/ into static pages.

    python3 storefront/build.py

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


# Brand assets shared with the main Archive 88 site: wordmark letters + social icons (src/partials/defs.html),
# fonts (assets/fonts/) and social links (data/site.json). One source of truth for the identity.
SITE_ROOT = ROOT.parent
BRAND_DEFS = (SITE_ROOT / "src" / "partials" / "defs.html").read_text()
SITE = json.loads((SITE_ROOT / "data" / "site.json").read_text())
WM = "".join(f'<use href="#wm-{c}" class="wm-l"/>' for c in ["A", "R", "C", "H", "I", "V", "E", "8a", "8b"])


def wordmark(cls: str = "", label: str = "Archive 88") -> str:
    aria = f'role="img" aria-label="{e(label)}"' if label else 'aria-hidden="true" focusable="false"'
    return f'<svg class="wordmark {cls}" viewBox="0 0 640 68" {aria}>{WM}</svg>'


def social(variant: str) -> str:
    items = "".join(
        f'<li><a class="social__btn" href="{e(SITE["social"][k])}" target="_blank" rel="noopener noreferrer" '
        f'aria-label="{label} (opens in a new tab)"><span class="social__base" aria-hidden="true"></span>'
        f'<span class="social__face"><svg aria-hidden="true"><use href="#ico-{k}"/></svg></span></a></li>'
        for k, label in (("instagram", "Instagram"), ("facebook", "Facebook")))
    return f'<ul class="social social--{variant}" aria-label="Archive 88 on social media">{items}</ul>'


def head(title: str, desc: str, root: str, canonical: str, jsonld: list | None = None) -> str:
    ld = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in (jsonld or []))
    return f'''<!doctype html>
<!-- GENERATED by storefront/build.py. Edit data/, components.py or build.py, not this file. -->
<html lang="{store["locale"]}" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
<meta name="theme-color" content="#E6E3DA">
<meta property="og:type" content="website"><meta property="og:site_name" content="{e(store["name"])}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<link rel="icon" href="{root}../assets/img/favicon.svg" type="image/svg+xml">
<link rel="preload" href="{root}../assets/fonts/archivo-narrow-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{root}../assets/fonts/archivo-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{root}../assets/fonts/fonts.css">
<link rel="stylesheet" href="{root}assets/css/tokens.css">
<link rel="stylesheet" href="{root}assets/css/store.css">
<script>document.documentElement.classList.replace("no-js","js")</script>
{ld}
</head>'''


def header(root: str, active: str | None = None) -> str:
    return f'''<a class="skip" href="#main">Skip to content</a>
<header class="nav">
  <button type="button" class="nav__menu" data-drawer-open="menu" aria-controls="menu" aria-expanded="false">
    <span class="nav__burger" aria-hidden="true"><i></i><i></i></span><span class="nav__word">Menu</span>
  </button>
  <a class="nav__logo" href="{root}" aria-label="{e(store["name"])}, home">{wordmark(label="")}</a>
  <div class="nav__right">
    <a class="nav__join" href="{root}../#join">Join the list</a>
    {social("nav")}
    <button type="button" class="nav__cart" data-drawer-open="cart" aria-controls="cart" aria-expanded="false" aria-label="Bag, 0 items" data-bag-btn>
      <span>Bag</span><span class="nav__count" data-bag-count>0</span>
    </button>
  </div>
</header>'''


def footer(root: str) -> str:
    cats = "".join(f'<li><a href="{root}shop/{c["handle"]}/">{e(c["title"])}</a></li>' for c in CATS)
    promises = "".join(f'<li><span class="eyebrow">{e(a)}</span><p>{e(b)}</p></li>' for a, b in store["promises"])
    return f'''<section class="promises" aria-label="Our promises"><ul>{promises}</ul></section>
<footer class="footer">
  <div class="footer__row">
    <p>{e(store["tagline"])}<br>Natural fibres. Est. 1988</p>
    <nav class="footer__nav" aria-label="Footer">
      <ul><li><a href="{root}shop/">Shop all</a></li>{cats}</ul>
      <ul><li><a href="{root}../size-guide/">Size guide</a></li><li><a href="{root}../#returns">Returns</a></li>
        <li><a href="{root}../contact/">Contact</a></li><li><a href="{root}../about/">About</a></li></ul>
      <ul><li><a href="{root}../privacy/">Privacy</a></li><li><a href="{root}../terms/">Terms of sale</a></li></ul>
    </nav>
    <div class="footer__end">{social("footer")}<p>© {date.today().year} {e(store["name"])}</p><p class="footer__small">Sample catalogue: names, prices and stock are placeholders.</p></div>
  </div>
  {wordmark("wordmark--footer")}
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
  <p>Start with the pieces people reach for first.</p>
  <a class="btn btn--secondary" href="__ROOT__shop/">Shop all</a>
</div>'''
    foot = f'''<dl class="cart-total"><dt>Subtotal</dt><dd data-cart-subtotal>{money(0, SYM)}</dd></dl>
<p class="cart-note">Delivery and taxes calculated at checkout.</p>
<button type="button" class="cart__checkout" data-checkout>Checkout</button>
<p class="cart-msg" data-checkout-msg aria-live="polite"></p>'''
    return C.drawer("cart", "Bag", body, footer=foot, label_extra=' <span class="drawer__count" data-drawer-count></span>')


def menu_drawer(root: str) -> str:
    """Full-screen ink overlay with numbered categories, as on the main site."""
    counts = {c["handle"]: sum(1 for p in catalog if p["category"] == c["handle"]) for c in CATS}
    rows = [("shop/", "Shop all", len(catalog))] + [(f'shop/{c["handle"]}/', c["title"], counts[c["handle"]]) for c in CATS]
    items = "".join(
        f'<li><a href="{root}{u}"><span class="menu__num">{i:02d}</span><span class="menu__name">{e(t)}</span>'
        f'<span class="menu__count">{n}</span><span class="menu__arrow" aria-hidden="true">→</span></a></li>'
        for i, (u, t, n) in enumerate(rows, 1))
    body = (f'<span class="eyebrow menu__eyebrow">Shop by category</span><ul class="menu__cats">{items}</ul>'
            f'<div class="menu__foot"><nav class="menu__links" aria-label="More"><a href="{root}../">The archive</a>'
            f'<a href="{root}../lookbook/">Shop the look</a><a href="{root}../about/">About</a>'
            f'<a href="{root}../size-guide/">Size guide</a><a href="{root}../contact/">Contact</a></nav>{social("menu")}</div>')
    return C.drawer("menu", "Menu", body, side="menu")


def page(*, title, desc, root, path, main, active=None, scripts=(), jsonld=None, extra="", tone="paper",
         vendor=(), pre="") -> str:
    canonical = store["url"] + path
    cfg = {"root": root, "currency": store["currency"], "symbol": SYM, "locale": store["locale"],
           "freeShipping": store["free_shipping_threshold"], "lowStock": LOW, "shopify": store.get("shopify_domain", "")}
    js = "".join(f'<script src="{root}../{v}" defer></script>' for v in vendor)
    js += "".join(f'<script src="{root}assets/js/{s}.js" defer></script>' for s in ("store", *scripts))
    return (head(title, desc, root, canonical, jsonld) +
            f'\n<body data-tone="{tone}">\n{pre}{BRAND_DEFS}\n{SPRITE}\n{header(root, active)}\n<main id="main">\n{main}\n</main>\n{footer(root)}\n'
            f'{cart_drawer().replace("__ROOT__", root)}\n{menu_drawer(root)}\n{extra}\n'
            f'<div class="grain" aria-hidden="true"></div>\n'
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
    counts = {c["handle"]: sum(1 for p in catalog if p["category"] == c["handle"]) for c in CATS}
    families = sorted({c["family"] for p in items for c in p["colours"]})
    title = category["title"] if category else "Shop all"
    intro = category["intro"] if category else store["description"]
    cards = "\n".join(C.product_card(p, root, SYM, eager=i < 4) for i, p in enumerate(items))
    filters = (C.filter_group("Category", C.category_links(CATS, category and category["handle"], counts, len(catalog), root), gid="category")
               + C.filter_group("Size", C.size_chips(size_groups(items)), gid="size")
               + C.filter_group("Colour", C.colour_filters(families), gid="colour"))
    page_size = store["page_size"]
    main = f'''<div class="plp" data-plp data-page-size="{page_size}">
  <header class="plp__head">
    {breadcrumbs([("Home", root), ("Shop", root + "shop/" if category else None)] + ([(title, None)] if category else []))}
    <div class="plp__title-row"><h1 class="display">{e(title)}</h1>
    <p class="plp__intro"><strong>{len(items)}</strong> styles, kept in every size.<br>{e(intro)}</p></div>
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
          <button type="button" class="btn btn--ink" data-drawer-close data-show-results>Show {len(items)} styles</button>
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
        active=category["handle"] if category else "all", scripts=("plp",)))


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
    gallery = (f'<section class="gallery" aria-label="Product images" data-gallery>{"".join(sets)}'
               f'<p class="gallery__pager" aria-hidden="true"><span data-gallery-index>1</span> / <span data-gallery-total>{count}</span></p></section>')

    th = store["free_shipping_threshold"]
    details = (f'<p>{e(p["description"])}</p><ul class="spec"><li><span>Composition</span>{e(p.get("material", ""))}</li>'
               f'<li><span>Care</span>{e(p.get("care", ""))}</li><li><span>Origin</span>{e(p.get("origin", ""))}</li>'
               f'<li><span>Style</span>{e(p["style"])}</li></ul>')
    fit = (f'<p>{e(p.get("fit", ""))}.</p><p>Between sizes? Take your usual size for a close fit, or size up for room to layer.</p>'
           f'<p><a href="{root}../size-guide/">Full size guide</a></p>')
    delivery = (f'<p>Free UK delivery on orders over {money(th, SYM)}; otherwise {money(5, SYM)}. Dispatched within 1 to 2 working days.</p>'
                f'<p>Free returns within 30 days, from your door.</p>')

    number = p["style"].split("-")[-1]
    origin = p.get("origin", "").replace("Made in ", "")
    info = f'''<div class="pdp__info">
  <div class="pdp__sticky">
    <p class="pdp__meta"><span>No. {e(number)}</span><a href="{root}shop/{cat["handle"]}/">{e(cat["title"])}</a></p>
    <h1 class="pdp__title">{e(p["title"])}</h1>
    <div class="pdp__price">{C.price(p, SYM)}</div>
    <dl class="pdp__facts">
      <div><dt>Cloth</dt><dd>{e(p.get("material", "").split(",")[0])}</dd></div>
      <div><dt>Fit</dt><dd>{e(p.get("fit", "").split(",")[0])}</dd></div>
      <div><dt>Made in</dt><dd>{e(origin)}</dd></div>
    </dl>
    <p class="pdp__desc">{e(p["description"])}</p>
    <form class="buy" data-buy novalidate>
      {C.colour_selector(p)}
      {C.size_selector(p, root)}
      <p class="stock-msg" data-stock-msg aria-live="polite"></p>
      <button type="submit" class="buy-btn" data-atc><span class="buy-btn__price">{money(p["price"], SYM)}</span><span class="tag__cta" data-atc-label>Add to bag</span></button>
    </form>
    <p class="pdp__note"><strong>Free UK delivery</strong> over {money(th, SYM)}. <strong>Free returns</strong> within 30 days.</p>
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
    recs = "".join(C.product_card(q, root, SYM, quick_add=False) for q in prepare_for[:4])

    matrix = {
        "handle": p["handle"], "style": p["style"], "title": p["title"], "price": p["price"], "sil": p["silhouette"],
        "url": f'{root}products/{p["handle"]}/', "sizes": p["sizes"], "stock": p["stock"],
        "colours": [{"h": c["handle"], "n": c["name"], "hex": c["hex"],
                     "img": p["media"][c["handle"]][0].get("src")} for c in p["colours"]],
        "ids": p.get("shopify_variant_ids", {}),
    }
    main = f'''<div class="pdp" data-pdp>
  {breadcrumbs([("Shop", root + "shop/"), (cat["title"], root + "shop/" + cat["handle"] + "/"), ("No. " + p["style"].split("-")[-1], None)])}
  <div class="pdp__layout">{gallery}{info}</div>
</div>
<section class="recs" aria-labelledby="recs-title">
  <h2 class="display display--md" id="recs-title">More {e(cat["title"])}</h2>
  <div class="grid grid--4">{recs}</div>
</section>
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


def home():
    root = ""
    prepare(root)
    counts = {c["handle"]: sum(1 for p in catalog if p["category"] == c["handle"]) for c in CATS}
    tiles = []
    for i, c in enumerate(CATS, 1):
        lead = next(p for p in sorted(catalog, key=lambda p: p["rank"]) if p["category"] == c["handle"])
        v = lead["media"][lead["colours"][0]["handle"]][0]
        tiles.append(f'<li><a class="tile" href="shop/{c["handle"]}/">{C.frame(C.media(v, ""), "tile__media")}'
                     f'<span class="tile__meta"><span>{i:02d}</span><span>{counts[c["handle"]]} styles</span></span>'
                     f'<span class="tile__title">{e(c["title"])}</span></a></li>')
    newest = [p for p in sorted(catalog, key=lambda p: p["rank"]) if p.get("new")][:10]
    cards = "".join(C.product_card(p, root, SYM) for p in newest)
    words = ["Natural fibres", "Kept in every size", "Free 30-day returns", "Made to be worn often", f"{len(catalog)} styles"]
    run = "".join(f"<span>{e(w)}</span><i>✦</i>" for w in words)
    loader = f'''<script>try{{if(sessionStorage.getItem("a88-store-intro"))document.documentElement.classList.add("seen-intro")}}catch(e){{}}</script>
<div class="loader" aria-hidden="true">
  <div class="loader__inner">
    {wordmark("wordmark--loader", "")}
    <div class="loader__meta"><span>{e(store["tagline"])}</span><span class="loader__count"><span class="js-count">00</span>/{len(catalog)}</span></div>
  </div>
</div>
'''
    main = f'''<section class="hero">
  <h1 class="hero__mark">{wordmark("wordmark--hero", store["name"] + ": " + store["tagline"])}</h1>
  <div class="hero__foot">
    <div class="js-hero-fade"><p class="hero__line">{e(store["tagline"].capitalize())}. {len(catalog)} styles in natural fibres, kept in every size.</p>
    <p class="hero__signal">Free UK delivery over {money(store["free_shipping_threshold"], SYM)}. Free 30-day returns.</p></div>
    <a class="btn btn--accent btn--lg js-hero-fade" href="shop/">Shop the collection</a>
  </div>
</section>
<section class="archive" aria-labelledby="new-title">
  <div class="archive__pin">
    <div class="archive__head">
      <p class="eyebrow">Just in · {len(newest)} styles</p>
      <h2 class="display display--md" id="new-title">New in</h2>
      <div class="archive__side">
        <a class="link-line" href="shop/?sort=new">View all new <span aria-hidden="true">→</span></a>
        <div class="archive__progress" aria-hidden="true"><span class="js-progress"></span></div>
      </div>
    </div>
    <div class="archive__viewport"><div class="archive__track">{cards}</div></div>
  </div>
</section>
<div class="marquee" aria-hidden="true"><div class="marquee__track">{run}{run}</div></div>
<section class="tiles" aria-labelledby="tiles-title">
  <div class="section-head"><h2 class="display display--md" id="tiles-title">The collection</h2><p class="eyebrow">Shop by category</p></div>
  <ul class="tiles__grid">{"".join(tiles)}</ul>
</section>'''
    write("index.html", page(
        title=f'{store["name"]}: {store["tagline"]}', desc=store["description"], root=root, path="", main=main, tone="bone",
        vendor=("assets/vendor/gsap.min.js", "assets/vendor/ScrollTrigger.min.js", "assets/vendor/lenis.min.js"),
        scripts=("home",), pre=loader))


# ---------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    validate()
    PHOTO_CACHE = {p["handle"]: process_photos(p["handle"]) for p in catalog}
    for d in ("products", "shop"):
        shutil.rmtree(ROOT / d, ignore_errors=True)
    home()
    plp(None)
    for c in CATS:
        plp(c)
    prepare("../../")
    for p in catalog:
        pdp(p)
    variants = sum(len(p["colours"]) * len(p["sizes"]) for p in catalog)
    with_photos = sum(1 for h in PHOTO_CACHE.values() if h)
    print(f"Built {len(catalog)} product pages, {len(CATS) + 1} listing pages, home. "
          f"{variants} variants. {with_photos}/{len(catalog)} styles have photos; the rest show placeholder art.")
    for w in sorted(set(warnings)):
        print("  !", w)
