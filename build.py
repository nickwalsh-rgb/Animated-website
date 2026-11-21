#!/usr/bin/env python3
"""Builds the Archive 88 site from data/ and src/ into static pages.

    python3 build.py

Reads   data/store.json, data/catalog.json, src/pages/*.html,
        assets/products/<handle>/<colour>-<n>.(jpg|png|webp)
Writes  index.html, shop/**, products/<handle>/, bag/, search/, gift-cards/, info pages, 404.html,
        search.json, sitemap.xml, robots.txt, and assets/products/<handle>/web/* (2:3 crops, when Pillow is installed)

The layout follows the Carhartt WIP UK audit (docs/DESIGN-SYSTEM.md): two homepage modules with product rails, a
plain product card, colourways as their own cards and URLs, a filter pill instead of a sidebar, a 400px product
information column, a full bag page and a full-screen search page. Every name, image, colour and word is Archive 88's.

Standard library only; Pillow is optional (photo cropping/resizing). Markup comes from components.py.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import components as C  # noqa: E402
from components import e, icon, money, slug  # noqa: E402

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
PHOTOS = ROOT / "assets" / "products"
WIDTHS = (480, 960, 1600)
RATIO = 2 / 3
ANGLES = ("front", "back", "detail", "fabric")

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
NAME = store["name"]
YEAR = date.today().year
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
# Photos: everything is centre-cropped to exactly 2:3. Fallback is placeholder art on the mist ground.
# ---------------------------------------------------------------------------------------------------------------------

PHOTO_RE = re.compile(r"^(?P<colour>[a-z0-9-]+)-(?P<n>\d+)\.(jpe?g|png|webp)$", re.I)
warnings: list[str] = []


def crop_ratio(im):
    w, h = im.size
    if abs(w / h - RATIO) < 0.005:
        return im
    if w / h > RATIO:
        nw = round(h * RATIO)
        left = (w - nw) // 2
        return im.crop((left, 0, left + nw, h))
    nh = round(w / RATIO)
    top = (h - nh) // 2
    return im.crop((0, top, w, top + nh))


def process_photos(handle: str) -> dict[str, list[dict]]:
    """Returns {colour: [views]} for photos in assets/products/<handle>/. Views hold site-root-relative paths."""
    folder = PHOTOS / handle
    if not folder.is_dir():
        return {}
    found: dict[str, list[tuple[int, Path]]] = {}
    for f in sorted(folder.iterdir()):
        m = PHOTO_RE.match(f.name)
        if m:
            found.setdefault(m["colour"].lower(), []).append((int(m["n"]), f))
    out: dict[str, list[dict]] = {}
    web = folder / "web"
    for colour, files in found.items():
        for n, src in sorted(files):
            angle = ANGLES[min(n - 1, len(ANGLES) - 1)]
            rel = src.relative_to(ROOT).as_posix()
            if Image is None:
                warnings.append(f"Pillow not installed: {handle}/{src.name} used as-is (CSS still crops it to 2:3)")
                out.setdefault(colour, []).append({"kind": "img", "src": rel, "webp": [], "angle": angle})
                continue
            web.mkdir(exist_ok=True)
            stem = src.stem.lower()
            target = web / f"{stem}-1200.jpg"
            if not target.exists() or target.stat().st_mtime < src.stat().st_mtime:
                with Image.open(src) as im:
                    im = crop_ratio(ImageOps.exif_transpose(im).convert("RGB"))
                    if im.width < 1200:
                        warnings.append(f"{handle}/{src.name} is only {im.width}px wide (1600 x 2400 recommended)")
                    for w in WIDTHS:
                        im.resize((w, round(w / RATIO)), Image.LANCZOS).save(web / f"{stem}-{w}.webp", "WEBP", quality=82)
                    im.resize((1200, 1800), Image.LANCZOS).save(target, "JPEG", quality=84, optimize=True, progressive=True)
            base = (web / stem).relative_to(ROOT).as_posix()
            out.setdefault(colour, []).append({"kind": "img", "src": f"{base}-1200.jpg", "angle": angle,
                                               "webp": [(f"{base}-{w}.webp", w) for w in WIDTHS]})
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Derived data: fabric, fit and sub-category per style; one colourway per style x colour
# ---------------------------------------------------------------------------------------------------------------------

FABRICS = [  # (name, words in the material line). First match wins; Cotton takes the rest.
    ("Denim", ["denim"]), ("Cashmere", ["cashmere"]), ("Merino", ["merino"]), ("Lambswool", ["lambswool"]),
    ("Alpaca & mohair", ["alpaca", "mohair"]), ("Linen", ["linen"]), ("Corduroy", ["cord"]),
    ("Waxed cotton", ["wax"]), ("Suede", ["suede"]), ("Technical", ["nylon", "ripstop"]),
    ("Jersey", ["jersey", "fleece"]), ("Wool", ["wool", "tweed", "flannel", "herringbone"]), ("Cotton", []),
]
FITS = {"Relaxed": "Relaxed", "Regular": "Regular", "Straight": "Straight", "Boxy": "Boxy",
        "Natural": "Tailored", "Soft": "Tailored"}
FIT_ORDER = ["Regular", "Relaxed", "Straight", "Boxy", "Tailored"]
FAMILY = {  # colour families: filter swatch colour and label
    "black": ("Black", "#1B211D"), "grey": ("Grey", "#8D918C"), "white": ("White", "#F4F2EC"),
    "neutral": ("Neutral", "#CFC6B4"), "brown": ("Brown", "#7A5A40"), "green": ("Green", "#4F6248"),
    "blue": ("Blue", "#2F4A6B"), "red": ("Red", "#9A3B2E"),
}


def fabric_of(p) -> str:
    text = (p.get("material", "") + " " + p["title"]).lower()
    for name, words in FABRICS:
        if not words or any(w in text for w in words):
            return name
    return "Cotton"


def fit_of(p) -> str:
    return FITS.get(p.get("fit", "Regular").split()[0].strip(","), "Regular")


def sub_of(p) -> dict:
    title = p["title"].lower()
    groups = CAT_BY[p["category"]]["subcategories"]
    for g in groups:
        if g["match"] and any(w in title for w in g["match"]):
            return g
    return next(g for g in groups if not g["match"])


def ranked() -> list:
    return sorted(catalog, key=lambda p: p["rank"])


def prepare():
    """Adds media, fabric, fit, sub-category and colourways to every product."""
    best = [p["handle"] for p in ranked() if not p.get("new")][:24]
    for p in catalog:
        photos = PHOTO_CACHE[p["handle"]]
        p["fabric"] = fabric_of(p)
        p["fit_name"] = fit_of(p)
        p["sub"] = sub_of(p)
        p["best"] = p["handle"] in best
        p["media"] = {}
        p["colourways"] = []
        for i, c in enumerate(p["colours"]):
            views = photos.get(c["handle"]) or [{"kind": "svg", "sil": p["silhouette"], "hex": c["hex"], "angle": a} for a in ANGLES]
            if len(views) == 1:
                views = views * 2
            p["media"][c["handle"]] = views
            in_stock = [s for s in p["sizes"] if p["stock"][c["handle"]].get(s, 0) > 0]
            p["colourways"].append({
                "p": p, "c": c, "key": f'{p["handle"]}/{c["handle"]}', "views": views, "in_stock": in_stock,
                "sold_out": not in_stock, "rank": p["rank"] * 10 + i, "fit": p["fit_name"], "fabric": p["fabric"],
                "url": f'products/{p["handle"]}/' + (f'?colour={c["handle"]}' if i else ""),
            })


def colourways(products) -> list:
    """New in first (the default sort, as on the original), then by rank."""
    out = [cw for p in products for cw in p["colourways"]]
    return sorted(out, key=lambda cw: (0 if cw["p"].get("new") else 1, cw["rank"]))


def cw_by_ref(ref: str) -> dict:
    """'handle' or 'handle/colour' to a colourway."""
    handle, _, colour = ref.partition("/")
    p = next((x for x in catalog if x["handle"] == handle), None)
    if not p:
        fail(f"store.json home refers to unknown product '{handle}'")
    if not colour:
        return p["colourways"][0]
    cw = next((x for x in p["colourways"] if x["c"]["handle"] == colour), None)
    if not cw:
        fail(f"store.json home refers to unknown colour '{ref}'")
    return cw


def fabrics_present() -> list[str]:
    have = {p["fabric"] for p in catalog}
    return [n for n, _ in FABRICS if n in have]


def fits_present(products) -> list[str]:
    have = {p["fit_name"] for p in products}
    return [f for f in FIT_ORDER if f in have]


# ---------------------------------------------------------------------------------------------------------------------
# Navigation model: three mega menus (second level only, as on the original) and one straight link
# ---------------------------------------------------------------------------------------------------------------------


def nav_model() -> list[dict]:
    clothing = [("Shop all", "shop/"), ("New arrivals", "shop/new-arrivals/"), ("Bestsellers", "shop/bestsellers/")]
    clothing += [(c["title"], f'shop/{c["handle"]}/') for c in CATS]
    return [
        {"key": "clothing", "title": "Clothing", "href": "shop/", "groups": clothing},
        {"key": "fabrics", "title": "Fabrics", "href": "shop/fabric/",
         "groups": [("All fabrics", "shop/fabric/")] + [(f, f"shop/fabric/{slug(f)}/") for f in fabrics_present()]},
        {"key": "fits", "title": "Fits", "href": "shop/fit/",
         "groups": [("All fits", "shop/fit/")] + [(f"{f} fit", f"shop/fit/{slug(f)}/") for f in fits_present(catalog)]},
        {"key": "gift", "title": "Gift cards", "href": "gift-cards/"},
    ]


# ---------------------------------------------------------------------------------------------------------------------
# Page shell
# ---------------------------------------------------------------------------------------------------------------------

SPRITE = (ROOT / "assets" / "sprite.svg").read_text()
BRAND_DEFS = (ROOT / "src" / "brand-defs.html").read_text()
WM = "".join(f'<use href="#wm-{c}"/>' for c in ["A", "R", "C", "H", "I", "V", "E", "8a", "8b"])


def wordmark(cls: str = "", label: str = NAME) -> str:
    aria = f'role="img" aria-label="{e(label)}"' if label else 'aria-hidden="true" focusable="false"'
    return f'<svg class="wordmark {cls}" viewBox="0 0 640 68" {aria}>{WM}</svg>'


def head(title: str, desc: str, root: str, canonical: str, jsonld: list | None, robots: str, preload: str) -> str:
    ld = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in (jsonld or []))
    return f'''<!doctype html>
<!-- GENERATED by build.py. Edit data/, src/, components.py or build.py, not this file. -->
<html lang="{store["locale"]}" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{e(canonical)}">
<meta name="theme-color" content="#FBFAF8">
<meta property="og:type" content="website"><meta property="og:site_name" content="{e(NAME)}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{e(store["url"])}assets/img/og-image.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{root}assets/img/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{root}assets/img/apple-touch-icon.png">
<link rel="manifest" href="{root}site.webmanifest">
<link rel="preload" href="{root}assets/fonts/archivo-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{root}assets/fonts/archivo-narrow-latin.woff2" as="font" type="font/woff2" crossorigin>
{preload}<link rel="stylesheet" href="{root}assets/fonts/fonts.css">
<link rel="stylesheet" href="{root}assets/css/tokens.css">
<link rel="stylesheet" href="{root}assets/css/store.css">
<script>document.documentElement.classList.replace("no-js","js")</script>
{ld}
</head>'''


def header(root: str, *, overlay: bool, crumbs: list | None) -> str:
    items = []
    for i, n in enumerate(nav_model()):
        if "groups" not in n:
            items.append(f'<li class="hdr__item"><a class="hdr__link" href="{root}{n["href"]}">{e(n["title"])}</a></li>')
            continue
        links = "".join(f'<li><a class="mega__link" href="{root}{h}">{e(t)}</a></li>' for t, h in n["groups"])
        if i == 0 and crumbs:  # product pages: the first link becomes the breadcrumb trail
            label = " ".join(f'<a class="hdr__link" href="{root}{h}">{e(t)}</a>' + ('<span class="hdr__sep" aria-hidden="true">/</span>' if j < len(crumbs) - 1 else "")
                             for j, (t, h) in enumerate(crumbs))
            label = f'<nav class="hdr__crumbs" aria-label="Breadcrumb">{label}</nav>'
        else:
            label = f'<a class="hdr__link" href="{root}{n["href"]}">{e(n["title"])}</a>'
        items.append(f'''<li class="hdr__item" data-mega-item>
        {label}<button type="button" class="hdr__chev" aria-expanded="false" aria-controls="mega-{n["key"]}" aria-label="Show sub categories for {e(n["title"])}">{icon("chevron")}</button>
        <div class="mega" id="mega-{n["key"]}" hidden><ul class="mega__cols">{links}</ul></div>
      </li>''')
    mode = "hdr--overlay" if overlay else ""
    return f'''<a class="skip" href="#main">Skip to content</a>
<header class="hdr {mode}" data-header>
  <div class="hdr__bar">
    <div class="hdr__left">
      <a class="hdr__logo" href="{root}" aria-label="{e(NAME)} home">{wordmark("", "")}</a>
      <nav class="hdr__nav" aria-label="Main"><ul class="hdr__list">{"".join(items)}</ul></nav>
    </div>
    <div class="hdr__right">
      <a class="hdr__link hdr__desk" href="{root}search/">Search</a>
      <button type="button" class="hdr__link hdr__desk" data-dialog-open="login">Login</button>
      <a class="hdr__link" href="{root}bag/" data-bag-link aria-label="Go to bag"><span>Bag</span><span data-bag-count></span></a>
      <a class="hdr__icon hdr__mob" href="{root}search/" aria-label="Search">{icon("search")}</a>
      <button type="button" class="hdr__icon hdr__mob" data-dialog-open="menu" aria-label="Open the main menu">{icon("burger")}</button>
    </div>
  </div>
  <div class="added" data-added hidden role="region" aria-label="Added to bag">
    <p class="added__title" tabindex="-1">Item added to bag</p>
    <div class="added__item" data-added-item></div>
    <div class="added__actions"><a class="btn btn--outline" href="{root}bag/" data-added-bag>Bag</a><a class="btn" href="{root}bag/#checkout">To checkout</a></div>
    <button type="button" class="added__close" data-added-close aria-label="Close">{icon("x")}</button>
  </div>
</header>'''


def menu_dialog(root: str) -> str:
    """Phones and tablets: a full-screen typographic menu. Each level replaces the last, with a back arrow."""
    top, panels = [], []
    for n in nav_model():
        if "groups" not in n:
            top.append(f'<li><a class="menu__big" href="{root}{n["href"]}">{e(n["title"])}</a></li>')
            continue
        top.append(f'<li><button type="button" class="menu__big" data-menu-go="menu-{n["key"]}">{e(n["title"])}</button></li>')
        links = "".join(f'<li><a class="menu__mid" href="{root}{h}">{e(t)}</a></li>' for t, h in n["groups"])
        panels.append(f'<div class="menu__panel" id="menu-{n["key"]}" data-menu-panel hidden><p class="sr-only">{e(n["title"])}</p><ul>{links}</ul></div>')
    return f'''<dialog class="menu" id="menu" aria-label="Main menu" data-menu>
  <div class="menu__bar">
    <a class="menu__ico" href="{root}search/" aria-label="Search" data-menu-search>{icon("search")}</a>
    <button type="button" class="menu__ico" aria-label="Back" data-menu-back hidden>{icon("back")}</button>
    <button type="button" class="menu__ico" aria-label="Close the menu" data-dialog-close>{icon("x")}</button>
  </div>
  <div class="menu__panel" data-menu-panel id="menu-root"><ul>{"".join(top)}</ul>
    <div class="menu__foot"><p class="menu__hello">Welcome to {e(NAME)}</p>
      <div class="menu__btns"><a class="btn" href="#newsletter" data-dialog-close>Sign up</a><button type="button" class="btn btn--outline" data-dialog-open="login">Login</button></div></div>
  </div>
  {"".join(panels)}
</dialog>'''


def login_dialog() -> str:
    return f'''<dialog class="drawer" id="login" aria-labelledby="login-title">
  <div class="drawer__head"><p class="drawer__label">Login</p><button type="button" class="drawer__x" data-dialog-close aria-label="Close">{icon("x")}</button></div>
  <div class="drawer__body">
    <h2 class="drawer__title" id="login-title">Welcome back</h2>
    <p class="drawer__sub">Sign in to see your orders and saved details.</p>
    <form class="login" data-login novalidate>
      {C.field("login-email", "Email", type_="email", autocomplete="email", inputmode="email")}
      <div class="field"><label class="field__label" for="login-password">Password</label>
        <div class="pw"><input type="password" id="login-password" name="login-password" autocomplete="current-password" required aria-describedby="login-password-err">
        <button type="button" class="pw__eye" data-pw-toggle aria-label="Show password" aria-pressed="false">Show</button></div>
        <p class="field__err" id="login-password-err" aria-live="polite"></p></div>
      <p><a class="text-link" href="#" data-login-forgot>Forgot your password?</a></p>
      <button type="submit" class="btn btn--block btn--muted">Login to your account</button>
      <p class="login__msg" data-login-msg aria-live="polite"></p>
    </form>
    <div class="login__new"><p class="drawer__title drawer__title--sm">Not a customer yet?</p>
      <button type="button" class="btn btn--block" data-login-create>Create an account</button></div>
  </div>
</dialog>'''


def footer(root: str) -> str:
    service = [("About", "about/"), ("Size guide", "size-guide/"), ("Delivery & returns", "returns/"),
               ("Contact", "contact/"), ("Gift cards", "gift-cards/")]
    legal = [("Privacy policy", "privacy/"), ("Terms of sale", "terms/")]
    li = lambda items: "".join(f'<li><a href="{root}{h}">{e(t)}</a></li>' for t, h in items)  # noqa: E731
    social = "".join(f'<li><a href="{e(store["social"][k])}" target="_blank" rel="noopener noreferrer">{t}<span class="sr-only"> (opens in a new tab)</span></a></li>'
                     for k, t in (("instagram", "Instagram"), ("facebook", "Facebook")))
    return f'''<footer class="ftr">
  <form class="news" id="newsletter" data-news novalidate>
    <h2 class="news__title">Sign up for the latest news from {e(NAME)}</h2>
    <div class="news__row">
      <label class="sr-only" for="news-email">Email address</label>
      <input class="input" type="email" id="news-email" name="email" placeholder="Email address" autocomplete="email" inputmode="email" required aria-describedby="news-err">
      <button type="submit" class="btn">Subscribe</button>
    </div>
    <p class="news__err" id="news-err" aria-live="polite"></p>
    <fieldset class="news__prefs"><legend class="sr-only">Tell me about</legend>
      <label class="dot"><input type="checkbox" name="interest" value="new-arrivals"><span>New arrivals</span></label>
      <label class="dot"><input type="checkbox" name="interest" value="restocks"><span>Restocks</span></label>
    </fieldset>
    <p class="news__small">We'll email you about new styles and restocks, never more than twice a month. Unsubscribe at any time. See our <a href="{root}privacy/">privacy policy</a>.</p>
  </form>
  <div class="ftr__rows">
    <ul class="ftr__row">{li(service)}</ul>
    <ul class="ftr__row">{social}</ul>
    <ul class="ftr__row ftr__row--muted"><li>United Kingdom</li><li>English</li><li>Prices in GBP</li></ul>
    <ul class="ftr__row ftr__row--muted">{li(legal)}</ul>
  </div>
  <div class="ftr__base"><p>&copy; {YEAR} {e(NAME)}</p><a class="ftr__mark" href="{root}" aria-label="{e(NAME)} home"><svg viewBox="0 0 100 100" aria-hidden="true"><use href="#mono"/></svg></a></div>
</footer>'''


def config(root: str) -> str:
    return C.json_script("store-config", {
        "locale": store["locale"], "currency": store["currency"], "root": root, "free": store["free_shipping_threshold"],
        "delivery": 5, "shopify": store.get("shopify_domain", ""), "low": LOW, "name": NAME})


def page(*, title, desc, root, path, main, overlay=False, crumbs=None, scripts=(), jsonld=None, extra="",
         bare=False, robots="index, follow", preload="", pre="") -> str:
    canonical = store["url"] + path
    chrome_top = "" if bare else header(root, overlay=overlay, crumbs=crumbs)
    chrome_bottom = "" if bare else footer(root)
    dialogs = "" if bare else menu_dialog(root) + login_dialog()
    js = "".join(f'<script src="{root}assets/js/{s}.js" defer></script>' for s in ("store", *scripts))
    cls = "main main--overlay" if overlay else "main"
    return f'''{head(title, desc, root, canonical, jsonld, robots, preload)}
<body>
{SPRITE}{BRAND_DEFS}
{pre}{chrome_top}
<main id="main" class="{cls}" tabindex="-1">
{main}
</main>
{chrome_bottom}
{dialogs}{extra}
<p class="sr-only" aria-live="polite" data-live></p>
{config(root)}
{js}
</body>
</html>
'''


def write(path: str, html: str):
    out = ROOT / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)


def crumbs_ld(items: list[tuple[str, str]]) -> dict:
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": t, "item": store["url"] + h} for i, (t, h) in enumerate(items)]}


def cards(cws, root, *, hl=2, eager=0) -> str:
    return "".join(C.product_card(cw, root, SYM, hl=hl, eager=i < eager) for i, cw in enumerate(cws))


# ---------------------------------------------------------------------------------------------------------------------
# Home: full-width teasers with product rails, then teaser grids (store.json -> home)
# ---------------------------------------------------------------------------------------------------------------------


def home():
    root = ""
    blocks = []
    for pos, m in enumerate(store["home"], 1):
        if m["module"] == "fullWidthTeaser":
            blocks.append(C.full_width_teaser(m, root, first=pos == 1, pos=pos))
            if m.get("rail"):
                r = m["rail"]
                blocks.append(C.products_listing(r["heading"], root + r["seeAll"],
                                                 cards([cw_by_ref(x) for x in r["products"]], root, hl=3)))
        elif m["module"] == "teaserGrid":
            blocks.append(C.teaser_grid(m["teasers"], root, pos))
        else:
            fail(f"unknown home module '{m['module']}' in store.json")
    main = f'<h1 class="sr-only">{e(NAME)}: {e(store["tagline"])}</h1>\n' + "\n".join(blocks)
    ld = [{"@context": "https://schema.org", "@type": "Organization", "name": NAME, "url": store["url"],
           "logo": store["url"] + "assets/img/icon-512.png", "email": store["business"]["email"],
           "telephone": store["business"]["phone"]},
          {"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": store["url"],
           "sameAs": [store["social"]["instagram"], store["social"]["facebook"]]}]
    first = store["home"][0]
    preload = (f'<link rel="preload" as="image" href="{first["imageMobile"]}" media="(max-width: 1023px)">\n'
               f'<link rel="preload" as="image" href="{first["imageDesktop"]}" media="(min-width: 1024px)">\n')
    write("index.html", page(title=f'{NAME} | {store["tagline"]}', desc=store["description"], root=root, path="",
                             main=main, overlay=True, jsonld=ld, preload=preload))


# ---------------------------------------------------------------------------------------------------------------------
# Listing pages: sub-category links, heading, filter pill, product grid, pagination, SEO copy
# ---------------------------------------------------------------------------------------------------------------------

LISTINGS: list[str] = []


def seo_html(paras: list[str], root: str) -> str:
    links = {"size guide": "size-guide/", **{c["title"].lower(): f'shop/{c["handle"]}/' for c in CATS}}

    def sub(m):
        key = m.group(1)
        if key not in links:
            fail(f"unknown link {{{key}}} in store.json seo copy")
        return f'<a href="{root}{links[key]}">{e(key)}</a>'
    return "".join(f"<p>{re.sub(r'\{([a-z &]+)\}', sub, e(p))}</p>" for p in paras)


def listing(path: str, *, title: str, intro: str, products: list, nav: list[tuple[str, str]], crumbs: list,
            seo: list[str], doc_title: str | None = None):
    depth = path.count("/")
    root = "../" * depth
    cws = colourways(products)
    links = [(t, root + h, h == path) for t, h in nav]
    total_pages = max(1, -(-len(cws) // store["page_size"]))
    main = f'''<div class="plp" data-listing data-page-size="{store["page_size"]}">
  <div class="plp__top">{C.subnav(links)}</div>
  <div class="plp__body">
    <div class="plp__pillrow">{C.filter_pill("pill--top")}</div>
    <div class="plp__head"><h1 class="plp__title">{e(title)}</h1><p class="plp__intro">{e(intro)}</p></div>
    <p class="sr-only" data-result-count aria-live="polite">{len(cws)} items</p>
    <div class="grid" data-grid>{cards(cws, root, eager=4)}</div>
    <div class="plp__pillfoot">{C.filter_pill("pill--bottom")}</div>
  </div>
  {C.pagination()}
  <section class="seo"><h2 class="seo__title">{e(NAME)} {e(title.lower() if title != "Shop all" else "collection")}</h2>{seo_html(seo, root)}</section>
</div>
{C.filter_panel()}'''
    ld = [crumbs_ld([("Home", ""), *crumbs])]
    write(path + "index.html", page(
        title=doc_title or f'{title} | {NAME} official store', root=root, path=path, main=main, scripts=("plp",), jsonld=ld,
        desc=f'{intro} Free UK delivery over {money(store["free_shipping_threshold"], SYM)} and free returns within 30 days.'))
    LISTINGS.append(path)
    if total_pages > 1:
        pass  # numbered pages use ?page=N on the same URL (see plp.js); the canonical stays the clean URL


def listings():
    top_nav = [("Shop all", "shop/"), ("New arrivals", "shop/new-arrivals/"), ("Bestsellers", "shop/bestsellers/")]
    top_nav += [(c["title"], f'shop/{c["handle"]}/') for c in CATS]
    generic = lambda t: [f"{t} from the {NAME} permanent collection: considered clothing in natural fibres, kept in the range in every size, season after season.",  # noqa: E731
                         "Not sure of your size? See the {size guide}. Delivery is free over " + money(store["free_shipping_threshold"], SYM) + " and returns are free for 30 days."]
    listing("shop/", title="Shop all", intro="The whole collection: coats, knitwear, shirts, trousers, jersey and tailoring, kept in every size.",
            products=catalog, nav=top_nav, crumbs=[("Shop all", "shop/")], seo=generic("Every style"),
            doc_title=f"Shop all | {NAME} official store")
    listing("shop/new-arrivals/", title="New arrivals", intro="The newest styles to join the permanent collection.",
            products=[p for p in catalog if p.get("new")], nav=top_nav, crumbs=[("New arrivals", "shop/new-arrivals/")], seo=generic("New arrivals"))
    listing("shop/bestsellers/", title="Bestsellers", intro="The styles people come back for, again and again.",
            products=[p for p in catalog if p["best"]], nav=top_nav, crumbs=[("Bestsellers", "shop/bestsellers/")], seo=generic("Bestsellers"))

    for c in CATS:
        prods = [p for p in catalog if p["category"] == c["handle"]]
        base = f'shop/{c["handle"]}/'
        subs = [g for g in c["subcategories"] if any(p["sub"] is g for p in prods)]
        fits = fits_present(prods)
        nav = [("Shop all", base)] + [(g["title"], base + slug(g["title"]) + "/") for g in subs] + [(f"{f} fit", base + slug(f) + "-fit/") for f in fits]
        crumbs = [("Clothing", "shop/"), (c["title"], base)]
        listing(base, title=c["title"], intro=c["intro"], products=prods, nav=nav, crumbs=crumbs, seo=c["seo"],
                doc_title=f'{NAME} {c["title"]} | Official online store')
        for g in subs:
            listing(base + slug(g["title"]) + "/", title=g["title"], intro=f'{g["title"]} from our {c["title"].lower()}. {c["intro"]}',
                    products=[p for p in prods if p["sub"] is g], nav=nav, crumbs=crumbs + [(g["title"], base + slug(g["title"]) + "/")],
                    seo=c["seo"])
        for f in fits:
            listing(base + slug(f) + "-fit/", title=f"{f} fit {c['title'].lower()}", intro=f'{c["title"]} in a {f.lower()} fit. {c["intro"]}',
                    products=[p for p in prods if p["fit_name"] == f], nav=nav, crumbs=crumbs + [(f"{f} fit", base + slug(f) + "-fit/")],
                    seo=c["seo"])

    fab_nav = [("All fabrics", "shop/fabric/")] + [(f, f"shop/fabric/{slug(f)}/") for f in fabrics_present()]
    listing("shop/fabric/", title="Shop by fabric", intro="Wool, cashmere, linen, cotton and denim, from mills that have woven and spun for generations.",
            products=catalog, nav=fab_nav, crumbs=[("Fabrics", "shop/fabric/")], seo=generic("Every fabric"))
    for f in fabrics_present():
        listing(f"shop/fabric/{slug(f)}/", title=f, intro=f"Every {NAME} style made in {f.lower()}.",
                products=[p for p in catalog if p["fabric"] == f], nav=fab_nav,
                crumbs=[("Fabrics", "shop/fabric/"), (f, f"shop/fabric/{slug(f)}/")], seo=generic(f))
    fit_nav = [("All fits", "shop/fit/")] + [(f"{f} fit", f"shop/fit/{slug(f)}/") for f in fits_present(catalog)]
    listing("shop/fit/", title="Shop by fit", intro="Five fits, kept the same season after season, so your size stays your size.",
            products=catalog, nav=fit_nav, crumbs=[("Fits", "shop/fit/")], seo=generic("Every fit"))
    for f in fits_present(catalog):
        listing(f"shop/fit/{slug(f)}/", title=f"{f} fit", intro=f"Everything we make in a {f.lower()} fit.",
                products=[p for p in catalog if p["fit_name"] == f], nav=fit_nav,
                crumbs=[("Fits", "shop/fit/"), (f"{f} fit", f"shop/fit/{slug(f)}/")], seo=generic(f"{f} fit styles"))


# ---------------------------------------------------------------------------------------------------------------------
# Product page
# ---------------------------------------------------------------------------------------------------------------------

TOPS = {  # sample flat measurements for size M, in cm: chest width, back length, sleeve length, shoulder width
    "coat": (60, 96, 66, 48), "blazer": (55, 76, 64, 46), "knit": (56, 68, 64, 49), "shirt": (57, 76, 64, 48),
    "tee": (56, 72, 22, 52), "gift": (0, 0, 0, 0)}
TOP_ROWS = [("Chest width", "Measured flat, from armpit to armpit."),
            ("Back length", "From the highest point of the shoulder to the hem, measured at the back."),
            ("Sleeve length", "From the shoulder seam to the end of the cuff."),
            ("Shoulder width", "From one shoulder seam to the other, across the back.")]
TROUSER_ROWS = [("Waist width", "Measured flat across the top of the waistband."),
                ("Inseam", "From the crotch seam to the bottom hem."),
                ("Front rise", "From the crotch seam to the top of the waistband, at the front."),
                ("Thigh width", "Measured flat, 2 cm below the crotch."),
                ("Leg opening", "Measured flat across the bottom hem.")]
MARKERS = {  # numbered measuring lines on the drawing (400 x 500 art space)
    "top": [((100, 212), (300, 212)), ((372, 76), (372, 410)), ((286, 96), (346, 372)), ((136, 60), (264, 60))],
    "trouser": [((120, 50), (280, 50)), ((214, 184), (232, 450)), ((86, 64), (86, 176)), ((100, 194), (198, 194)), ((100, 474), (184, 474))],
}


def size_data(p) -> dict:
    if p["silhouette"] == "trouser":
        rows = []
        for i, s in enumerate(p["sizes"]):
            w = int(s) if s.isdigit() else 30 + i * 2
            rows.append([round(w * 2.54 / 2, 1), 81, round(26.5 + i * 0.5, 1), round(30 + i, 1), round(19 + i * 0.5, 1)])
        return {"kind": "trouser", "rows": TROUSER_ROWS, "values": dict(zip(p["sizes"], rows))}
    base = TOPS.get(p["silhouette"], TOPS["shirt"])
    mid = p["sizes"].index("M") if "M" in p["sizes"] else len(p["sizes"]) // 2
    vals = {}
    for i, s in enumerate(p["sizes"]):
        d = i - mid
        vals[s] = [base[0] + 3 * d, base[1] + 2 * d, base[2] + d, round(base[3] + 1.5 * d, 1)]
    return {"kind": "top", "rows": TOP_ROWS, "values": vals}


def size_guide_dialog(p) -> str:
    sd = size_data(p)
    kind = sd["kind"]
    sizes = list(sd["values"])
    mid = sizes[min(2, len(sizes) - 1)]
    btns = "".join(f'<button type="button" class="sg__size" data-sg-size="{e(s)}" aria-pressed="{"true" if s == mid else "false"}">{e(s)}</button>' for s in sizes)
    rows = "".join(f'<li class="sg__row" data-sg-row="{i}"><span class="sg__num">{i + 1}</span><span class="sg__name">{e(n)}<small>{e(why)}</small></span>'
                   f'<span class="sg__val" data-sg-val="{i}">{sd["values"][mid][i]} cm</span></li>' for i, (n, why) in enumerate(sd["rows"]))
    lines = ""
    for i, ((x1, y1), (x2, y2)) in enumerate(MARKERS[kind][:len(sd["rows"])]):
        lines += (f'<g class="sg__mark" data-sg-mark="{i}"><line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'
                  f'<circle cx="{(x1 + x2) / 2}" cy="{(y1 + y2) / 2}" r="13"/><text x="{(x1 + x2) / 2}" y="{(y1 + y2) / 2 + 5}">{i + 1}</text></g>')
    sil = p["silhouette"]
    drawing = (f'<svg class="sg__drawing" viewBox="40 30 360 460" aria-hidden="true"><use href="#p-{sil}" class="sg__outline"/>{lines}</svg>')
    head = "".join(f"<th scope=\"col\">{e(n)}</th>" for n, _ in sd["rows"])
    body = "".join(f'<tr><th scope="row">{e(s)}</th>' + "".join(f"<td>{v}</td>" for v in vals) + "</tr>" for s, vals in sd["values"].items())
    return f'''<dialog class="drawer drawer--wide" id="size-guide" aria-labelledby="sg-title">
  <div class="drawer__head"><p class="drawer__label" id="sg-title">Size guide</p><button type="button" class="drawer__x" data-dialog-close aria-label="Close">{icon("x")}</button></div>
  <div class="drawer__body sg" data-sg>
    <div class="tabs" role="tablist" aria-label="Size guide">
      <button type="button" role="tab" id="sg-tab-1" aria-controls="sg-panel-1" aria-selected="true" class="tabs__tab">Product measurements</button>
      <button type="button" role="tab" id="sg-tab-2" aria-controls="sg-panel-2" aria-selected="false" tabindex="-1" class="tabs__tab">Size chart</button>
    </div>
    <div role="tabpanel" id="sg-panel-1" aria-labelledby="sg-tab-1" class="sg__panel">
      <div class="sg__sizes" role="group" aria-label="Show measurements for size">{btns}</div>
      <ol class="sg__list">{rows}</ol>
      {drawing}
      <p class="sg__note">Sample measurements in centimetres, measured flat. Replace with your pattern measurements before launch.</p>
    </div>
    <div role="tabpanel" id="sg-panel-2" aria-labelledby="sg-tab-2" class="sg__panel" hidden>
      <div class="sg__tablewrap" tabindex="0" role="region" aria-label="Size chart, scrolls sideways"><table class="sg__table"><caption class="sr-only">Measurements in centimetres for every size</caption>
        <thead><tr><th scope="col">Size</th>{head}</tr></thead><tbody>{body}</tbody></table></div>
      <p class="sg__note">All measurements in centimetres. <a class="text-link" href="../../size-guide/">How to measure yourself</a></p>
    </div>
  </div>
</dialog>
{C.json_script("size-data", sd)}'''


CUR = ' aria-current="true"'


def pdp(p: dict):
    root = "../../"
    cat = CAT_BY[p["category"]]
    sub = p["sub"]
    sub_href = f'shop/{cat["handle"]}/{slug(sub["title"])}/'
    crumbs = [("Clothing", "shop/"), (cat["title"], f'shop/{cat["handle"]}/'), (sub["title"], sub_href)]
    first = p["colours"][0]

    sets = []
    for i, c in enumerate(p["colours"]):
        frames = "".join(
            f'<li class="gal__slide"><button type="button" class="gal__frame" data-gal-open="{n}" aria-label="Open image {n + 1} of {len(p["media"][c["handle"]])} full screen">'
            f'{C.media(v, C.alt_for(p["title"], c["name"], v.get("angle", "front")), root, sizes="(min-width: 1024px) 30vw, 100vw", eager=(i == 0 and n == 0))}</button></li>'
            for n, v in enumerate(p["media"][c["handle"]]))
        sets.append(f'<ul class="gal__set" data-gal-set="{e(c["handle"])}"{" hidden" if i else ""} aria-label="{e(c["name"])} images">{frames}</ul>')
    count = len(p["media"][first["handle"]])
    gallery = (f'<section class="gal" aria-label="Product images" data-gallery>{"".join(sets)}'
               f'<p class="gal__count" aria-hidden="true"><span data-gal-index>1</span>/<span data-gal-total>{count}</span></p></section>')

    swatches = "".join(
        f'<li><a class="swatch" href="{"./" if i == 0 else "?colour=" + e(c["handle"])}" data-swatch="{e(c["handle"])}"'
        f'{CUR if i == 0 else ""} aria-label="{e(c["name"])}">'
        f'{C.media(p["media"][c["handle"]][0], "", root)}</a></li>'
        for i, c in enumerate(p["colours"]))
    stock0 = p["stock"][first["handle"]]
    sizes = "".join(
        f'<label class="size"><input type="radio" name="size" value="{e(s)}"{" disabled" if stock0[s] <= 0 else ""}>'
        f'<span>{e(s)}</span></label>' for s in p["sizes"])
    th = money(store["free_shipping_threshold"], SYM)
    promises = [f"Free returns within 30 days", f"Free UK delivery on orders over {th}", "UK delivery in 1 to 3 working days",
                "Repairs for life", "Kept in the range, in every size"]
    biz = store["business"]
    details = (f'<p>{e(p["description"])}</p><ul class="bullets"><li>{e(p.get("origin", ""))}</li>'
               f'<li>{e(p["fit_name"])} fit</li><li>Style number {e(p["style"])}</li></ul>')
    material = f'<p><strong>Composition:</strong> {e(p.get("material", ""))}</p><p><strong>Care:</strong> {e(p.get("care", ""))}</p>'
    fit = (f'<p>{e(p.get("fit", ""))}.</p><p>Between sizes? Take your usual size for a close fit, or size up for room to layer.</p>'
           f'<p><button type="button" class="text-link" data-dialog-open="size-guide">Open size guide</button></p>')
    others = [q for q in catalog if q["fabric"] == p["fabric"] and q["handle"] != p["handle"] and q["category"] == p["category"]][:4]
    other_html = ("<ul class=\"bullets\">" + "".join(f'<li><a class="text-link" href="{root}products/{q["handle"]}/">{e(q["title"])}</a>, {e(q.get("material", ""))}</li>' for q in others) + "</ul>") if others else f"<p>This is the only {e(cat['title'].lower())} style we make in {e(p['fabric'].lower())}.</p>"
    info_acc = (f'<p>Product ID: {e(p["style"])}</p><p>Made for {e(biz["trading_name"])} by {e(biz["legal_name"])}, '
                f'{e(biz["address"].replace(chr(10), ", "))}.</p><p><a class="text-link" href="{root}contact/">Contact us</a></p>')

    info = f'''<div class="pdp__info"><div class="pdp__inner">
    <nav class="pdp__crumbs" aria-label="Breadcrumb">{" / ".join(f'<a href="{root}{h}">{e(t)}</a>' for t, h in crumbs)}</nav>
    {'<p class="badge">New</p>' if p.get("new") else ""}
    <h1 class="pdp__title">{e(p["title"])}</h1>
    <p class="pdp__price">{money(p["price"], SYM)}</p>
    <ul class="swatches" aria-label="Colours">{swatches}</ul>
    <p class="pdp__colour"><span class="sr-only">Colour: </span><span data-colour-name>{e(first["name"])}</span></p>
    <form class="buy" data-buy novalidate>
      <fieldset class="sizes"><legend class="sr-only">Size</legend><div class="sizes__grid">{sizes}</div></fieldset>
      <p class="buy__msg" data-buy-msg aria-live="polite"></p>
      <button type="button" class="text-link buy__guide" data-dialog-open="size-guide">Size guide</button>
      <button type="submit" class="btn btn--block buy__btn" data-atc aria-disabled="true"><span data-atc-label>Choose size</span></button>
    </form>
    <button type="button" class="wishlink" data-wish="{e(p["handle"])}/{e(first["handle"])}" aria-pressed="false">{icon("heart")}<span data-wish-label>Add to wishlist</span></button>
    <ul class="promises">{"".join(f"<li>{e(x)}</li>" for x in promises)}</ul>
    <div class="accs">
      {C.accordion("Details", details, open_=True)}
      {C.accordion("Material & care", material)}
      {C.accordion("Size & fit", fit)}
      {C.accordion("Other fabrics", other_html)}
      {C.accordion("Additional information", info_acc)}
    </div>
  </div></div>'''

    # Complete the look: one piece from each other category, close in colour family. You might also like: same category.
    fam = first["family"]
    look = []
    for c in CATS:
        if c["handle"] == p["category"]:
            continue
        pool = [cw for q in ranked() if q["category"] == c["handle"] for cw in q["colourways"] if not cw["sold_out"]]
        pick = next((cw for cw in pool if cw["c"]["family"] in (fam, "neutral", "white")), pool[0] if pool else None)
        if pick:
            look.append(pick)
    similar = [q for q in catalog if q["category"] == p["category"] and q["handle"] != p["handle"]]
    similar.sort(key=lambda q: (q["sub"] is not p["sub"], abs(q["price"] - p["price"])))
    recs = [q["colourways"][0] for q in similar[:10]]

    data = {"handle": p["handle"], "style": p["style"], "title": p["title"], "price": p["price"], "sil": p["silhouette"],
            "url": f'products/{p["handle"]}/', "sizes": p["sizes"], "stock": p["stock"],
            "colours": [{"h": c["handle"], "n": c["name"], "hex": c["hex"],
                         "img": (p["media"][c["handle"]][0]["src"] if p["media"][c["handle"]][0]["kind"] == "img" else None)}
                        for c in p["colours"]], "ids": p.get("shopify_variant_ids", {})}
    main = f'''<div class="pdp" data-pdp>{gallery}{info}</div>
{C.carousel("look", "Complete the look", cards(look, root, hl=3))}
{C.carousel("recs", "You might also like", cards(recs, root, hl=3))}
{C.json_script("product-data", data)}'''
    bar = f'''<div class="pbar" data-pbar aria-hidden="true">
  <div class="pbar__text"><p class="pbar__title">{e(p["title"])}</p><p class="pbar__price">{money(p["price"], SYM)}</p></div>
  <button type="button" class="btn pbar__btn" data-pbar-btn tabindex="-1">Add to bag</button>
</div>'''
    fullscreen = f'''<dialog class="fs" id="fullscreen" aria-label="Product images, full screen" data-fs>
  <ul class="fs__thumbs" data-fs-thumbs aria-label="Thumbnails"></ul>
  <div class="fs__stage" data-fs-stage tabindex="0" aria-roledescription="image viewer"></div>
  <div class="fs__tools"><button type="button" class="round-btn" data-fs-zoom="in" aria-label="Zoom in">{icon("zoom-in")}</button>
    <button type="button" class="round-btn" data-fs-zoom="out" aria-label="Zoom out">{icon("zoom-out")}</button></div>
  <button type="button" class="fs__x" data-dialog-close aria-label="Close full screen">{icon("x")}</button>
  <p class="fs__count" aria-live="polite"><span data-fs-index>1</span>/<span data-fs-total>1</span></p>
  <p class="sr-only">Use the left and right arrow keys to move between images, plus and minus to zoom.</p>
</dialog>'''

    offers = {"@type": "Offer", "price": p["price"], "priceCurrency": store["currency"],
              "itemCondition": "https://schema.org/NewCondition", "url": store["url"] + f'products/{p["handle"]}/',
              "availability": "https://schema.org/" + ("InStock" if any(cw["in_stock"] for cw in p["colourways"]) else "OutOfStock")}
    ld = [{"@context": "https://schema.org", "@type": "Product", "name": p["title"], "sku": p["style"],
           "description": p["description"], "brand": {"@type": "Brand", "name": NAME}, "material": p.get("material", ""),
           "color": ", ".join(c["name"] for c in p["colours"]), "size": p["sizes"], "category": cat["title"],
           "image": [store["url"] + "assets/img/og-image.jpg"], "offers": offers},
          crumbs_ld([("Home", ""), *crumbs, (p["title"], f'products/{p["handle"]}/')])]
    path = f'products/{p["handle"]}/'
    write(path + "index.html", page(
        title=f'{p["title"]} | {NAME}', desc=p["description"], root=root, path=path, main=main, crumbs=crumbs,
        scripts=("pdp",), jsonld=ld, extra=bar + fullscreen + size_guide_dialog(p)))


# ---------------------------------------------------------------------------------------------------------------------
# Bag (a full page, as on the original) and search (full screen, ?query=)
# ---------------------------------------------------------------------------------------------------------------------


def bag():
    root = "../"
    th = money(store["free_shipping_threshold"], SYM)
    best = [p["colourways"][0] for p in ranked() if p["best"]][:10]
    main = f'''<div class="bag" data-bag>
  <div class="bag__main">
    <h1 class="bag__title">Shopping bag</h1>
    <div class="bag__empty" data-bag-empty>
      <p class="bag__empty-msg">Your bag is empty</p>
      <a class="btn" href="{root}shop/">Continue shopping</a>
    </div>
    <div class="bag__full" data-bag-full hidden>
      <ul class="lines" data-bag-lines aria-label="Items in your bag"></ul>
      <details class="promo"><summary class="promo__sum">Add a promo code{icon("plus")}</summary>
        <form class="promo__form" data-promo novalidate><label class="sr-only" for="promo-code">Promo code</label>
          <input class="input" id="promo-code" name="code" autocomplete="off" placeholder="Promo code"><button class="btn" type="submit">Apply</button></form>
        <p class="promo__msg" data-promo-msg aria-live="polite"></p></details>
      <ul class="bag__promises"><li>{icon("check")}Free returns within 30 days</li><li>{icon("check")}Free UK delivery on orders over {th}</li><li>{icon("check")}Repairs for life</li></ul>
      <p class="bag__meter" data-bag-meter aria-live="polite"></p>
      <dl class="totals">
        <div><dt>Subtotal (incl. VAT)</dt><dd data-bag-subtotal></dd></div>
        <div><dt>Standard UK delivery</dt><dd data-bag-delivery></dd></div>
        <div class="totals__total"><dt>Total</dt><dd data-bag-total></dd></div>
      </dl>
    </div>
  </div>
  <aside class="bag__checkout" id="checkout" data-bag-full hidden aria-labelledby="checkout-title" tabindex="-1">
    <h2 class="bag__checkout-title" id="checkout-title">Checkout</h2>
    <button type="button" class="btn btn--block" data-checkout>Proceed as a guest</button>
    <p class="bag__checkout-msg" data-checkout-msg aria-live="polite"></p>
    <p class="bag__legal">By placing an order you accept our <a href="{root}terms/">Terms of sale</a>, including your right to cancel, and our <a href="{root}privacy/">Privacy policy</a>.</p>
    <button type="button" class="arrow-link" data-dialog-open="login">Sign in &amp; checkout{icon("arrow")}</button>
  </aside>
</div>
{C.carousel("bag-recs", "You might also like", cards(best, root, hl=3))}'''
    write("bag/index.html", page(title=f"Shopping bag | {NAME}", desc=f"Your {NAME} shopping bag.", root=root, path="bag/",
                                 main=main, scripts=("bag",), robots="noindex, follow"))


def search_page():
    root = "../"
    trending = "".join(f'<li><button type="button" class="srch__term" data-term="{e(t)}">{e(t)}</button></li>' for t in store["trending"])
    cats = "".join(f'<li><a href="{root}shop/{c["handle"]}/">{e(c["title"])}</a></li>' for c in CATS)
    main = f'''<div class="srch" data-search>
  <header class="srch__bar">
    <a class="srch__logo" href="{root}" aria-label="{e(NAME)} home">{wordmark("", "")}</a>
    <form class="srch__form" role="search" data-search-form action="./">
      <label class="sr-only" for="q">Search for products</label>
      {icon("search")}<input class="srch__input" id="q" type="search" name="query" placeholder="Search for products" autocomplete="off" autofocus enterkeyhint="search">
    </form>
    <a class="srch__close" href="{root}" data-search-close>Close</a>
  </header>
  <div class="srch__body">
    <aside class="srch__side">
      <div data-trending><h2 class="srch__label">Trending searches</h2><ul class="srch__terms">{trending}</ul></div>
      <div data-suggest hidden><h2 class="srch__label">Suggestions</h2><ul class="srch__sugs" data-suggest-list></ul></div>
    </aside>
    <section class="srch__results" aria-labelledby="results-title">
      <div class="srch__head" data-results-head hidden><h2 class="srch__label" id="results-title">Results</h2>{C.filter_pill("pill--inline")}</div>
      <p class="sr-only" data-result-count aria-live="polite"></p>
      <div class="grid grid--search" data-grid></div>
      <div class="plp__pillfoot plp__pillfoot--search" data-results-foot hidden>{C.filter_pill("pill--bottom")}</div>
      <div class="srch__none" data-none hidden><p>No results found. Try different terms or browse our categories.</p><ul>{cats}</ul></div>
    </section>
  </div>
</div>
{C.filter_panel()}'''
    write("search/index.html", page(title=f"Search | {NAME}", desc=f"Search the {NAME} collection.", root=root, path="search/",
                                    main=main, bare=True, scripts=("plp", "search"), robots="noindex, follow"))


def search_index():
    """search.json: one entry per colourway with ready-made card HTML (for pages one folder deep: search, bag),
    plus suggestions (categories, sub-categories, fabrics, fits)."""
    root = "../"
    items = []
    for cw in colourways(catalog):
        p, c = cw["p"], cw["c"]
        text = " ".join([p["title"], c["name"], c["family"], CAT_BY[p["category"]]["title"], p["sub"]["title"],
                         p.get("material", ""), p["fabric"], cw["fit"] + " fit", p["style"]]).lower()
        items.append({"k": cw["key"], "t": p["title"].lower(), "s": text, "h": C.product_card(cw, root, SYM, hl=3)})
    sugs = [{"l": c["title"], "u": f'shop/{c["handle"]}/'} for c in CATS]
    for c in CATS:
        sugs += [{"l": f'{g["title"]}', "u": f'shop/{c["handle"]}/{slug(g["title"])}/'} for g in c["subcategories"]]
    sugs += [{"l": f, "u": f"shop/fabric/{slug(f)}/"} for f in fabrics_present()]
    sugs += [{"l": f"{f} fit", "u": f"shop/fit/{slug(f)}/"} for f in fits_present(catalog)]
    write("search.json", json.dumps({"items": items, "suggest": sugs}, ensure_ascii=False, separators=(",", ":")))


# ---------------------------------------------------------------------------------------------------------------------
# Gift cards: same two-part layout as a product page
# ---------------------------------------------------------------------------------------------------------------------


def gift():
    root = "../"
    g = store["gift_cards"]
    amounts = "".join(f'<label class="size"><input type="radio" name="amount" value="{a}"{" checked" if a == g["default"] else ""}>'
                      f'<span>{money(a, SYM).replace(".00", "")}</span></label>' for a in g["amounts"])
    today = date.today().isoformat()
    email_form = (C.field("email-to", "Their name", autocomplete="off", maxlength=40)
                  + C.field("email-address", "Their email address", type_="email", autocomplete="off", inputmode="email",
                            hint="We'll send the card here, with your message.")
                  + C.field("email-from", "Your name", autocomplete="name", maxlength=40)
                  + C.field("email-message", "Message", required=False, maxlength=200, textarea=True, hint="Up to 200 characters.")
                  + f'<div class="field"><label class="field__label" for="email-date">Send on</label>'
                    f'<input type="date" id="email-date" name="email-date" value="{today}" min="{today}" aria-describedby="email-date-err">'
                    f'<p class="field__err" id="email-date-err" aria-live="polite"></p></div>')
    post_form = (C.field("post-to", "Their name", autocomplete="off", maxlength=40)
                 + C.field("post-line1", "Address line 1", autocomplete="off")
                 + C.field("post-line2", "Address line 2", autocomplete="off", required=False)
                 + C.field("post-town", "Town or city", autocomplete="off")
                 + C.field("post-postcode", "Postcode", autocomplete="off", maxlength=8)
                 + C.field("post-from", "Your name", autocomplete="name", maxlength=40)
                 + C.field("post-message", "Message", required=False, maxlength=200, textarea=True, hint="Printed inside the card. Up to 200 characters."))
    btn = f'<button type="submit" class="btn btn--block">Add to bag</button>'
    main = f'''<div class="pdp gift" data-gift>
  <section class="gal gift__visual" aria-label="Gift card preview">
    <div class="giftcard" data-gift-card data-method="email">
      <div class="giftcard__top">{wordmark("giftcard__mark", "")}<span data-gift-kind>E-gift card</span></div>
      <p class="giftcard__amount" data-gift-amount>{money(g["default"], SYM).replace(".00", "")}</p>
      <div class="giftcard__foot"><span>For <span data-gift-to>someone good</span></span><span>{e(store["tagline"])}</span></div>
    </div>
    <p class="gift__caption">Preview. The amount and name update as you go.</p>
  </section>
  <div class="pdp__info"><div class="pdp__inner">
    <nav class="pdp__crumbs" aria-label="Breadcrumb"><a href="{root}">Home</a> / <a href="{root}gift-cards/" aria-current="page">Gift cards</a></nav>
    <h1 class="pdp__title">Gift card</h1>
    <p class="pdp__price">From {money(min(g["amounts"]), SYM)}</p>
    <p class="gift__lede">Let them choose. {e(g["terms"])}</p>
    <fieldset class="sizes"><legend class="gift__legend">Amount</legend><div class="sizes__grid">{amounts}</div></fieldset>
    <p class="gift__legend" id="gift-how">How should it arrive?</p>
    <div class="gift__methods" role="group" aria-labelledby="gift-how">
      <button type="button" class="gift__method" data-gift-method="email" aria-expanded="false" aria-controls="gift-email">{icon("mail")}<span><strong>By email</strong><small>{e(g["email_note"])}</small></span></button>
      <button type="button" class="gift__method" data-gift-method="post" aria-expanded="false" aria-controls="gift-post">{icon("post")}<span><strong>By post</strong><small>{e(g["post_note"])}</small></span></button>
    </div>
    <form class="gift__form" id="gift-email" data-gift-form="email" novalidate hidden aria-label="Email a gift card">{email_form}{btn}</form>
    <form class="gift__form" id="gift-post" data-gift-form="post" novalidate hidden aria-label="Post a gift card">{post_form}{btn}</form>
    <div class="accs">
      {C.accordion("How gift cards work", f"<p>{e(g['terms'])}</p><p>The code is entered at checkout. Any balance stays on the card for next time.</p>", open_=True)}
      {C.accordion("Delivery", f"<p><strong>Email:</strong> {e(g['email_note'])}</p><p><strong>Post:</strong> {e(g['post_note'])}</p>")}
    </div>
  </div></div>
</div>
{C.json_script("gift-config", {"amounts": g["amounts"], "ids": g.get("shopify_variant_ids", {})})}'''
    write("gift-cards/index.html", page(title=f"Gift cards | {NAME}", desc=f'{NAME} gift cards by email or post. {g["terms"]}',
                                        root=root, path="gift-cards/", main=main, scripts=("gift",)))


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
            return money(store["free_shipping_threshold"], SYM).replace(".00", "")
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
  <header class="info__head"><h1 class="info__title">{e(meta["title"])}</h1>{lede}</header>
  {draft}
  <div class="info__body">{fill(text[m.end():], root)}</div>
</article>'''
        shutil.rmtree(ROOT / slug_, ignore_errors=True)
        write(f"{slug_}/index.html", page(title=f'{meta["title"]} | {NAME}', desc=fill(meta["description"], root),
                                          root=root, path=f"{slug_}/", main=main))
        built.append(slug_)
    return built


def not_found():
    """404.html. GitHub Pages serves it for any missing path, so links use the site's absolute base path. It also
    forwards old addresses: /storefront/... and the retired /lookbook/ and /record/."""
    base = urlparse(store["url"]).path or "/"
    redirect = f'''<script>(function(){{var b={json.dumps(base)},p=location.pathname,s=b+"storefront/";
if(p.indexOf(s)===0){{location.replace(b+p.slice(s.length)+location.search+location.hash);return;}}
if(/\\/(lookbook|record)(\\/|$)/.test(p.slice(b.length-1))){{location.replace(b+"shop/");}}}})();</script>
'''
    main = f'''<section class="info info--center">
  <h1 class="info__title">Page not found</h1>
  <p class="info__lede">That page has moved or doesn't exist. Try the shop, or search for what you were after.</p>
  <p class="info__actions"><a class="btn" href="{base}shop/">Shop all</a> <a class="btn btn--outline" href="{base}search/">Search</a></p>
</section>'''
    write("404.html", page(title=f"Page not found | {NAME}", desc=store["description"], root=base, path="404.html",
                           main=main, pre=redirect, robots="noindex"))


def sitemap(info: list[str]):
    urls = ["", *LISTINGS, "gift-cards/", *(f"{s}/" for s in info), *(f'products/{p["handle"]}/' for p in ranked())]
    rows = "\n".join(f"  <url><loc>{e(store['url'] + u)}</loc></url>" for u in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}\n</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\nDisallow: /search/\nDisallow: /bag/\n\nSitemap: {store['url']}sitemap.xml\n")
    return len(urls)


# ---------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    validate()
    PHOTO_CACHE = {p["handle"]: process_photos(p["handle"]) for p in catalog}
    prepare()
    for d in ("products", "shop", "gift-cards", "bag", "search", "cart"):
        shutil.rmtree(ROOT / d, ignore_errors=True)
    home()
    listings()
    for p in catalog:
        pdp(p)
    bag()
    search_page()
    search_index()
    gift()
    info = info_pages()
    not_found()
    n_urls = sitemap(info)
    n_cw = sum(len(p["colourways"]) for p in catalog)
    with_photos = sum(1 for h in PHOTO_CACHE.values() if h)
    print(f"Built {len(catalog)} product pages ({n_cw} colourways), {len(LISTINGS)} listing pages, home, bag, search, "
          f"gift cards, {len(info)} info pages, 404. Sitemap: {n_urls} URLs.")
    print(f"  {with_photos}/{len(catalog)} styles have photos; the rest show placeholder art.")
    for w in sorted(set(warnings)):
        print("  !", w)
