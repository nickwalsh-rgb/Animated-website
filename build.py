#!/usr/bin/env python3
"""Archive 88 site build.

Reads data/site.json + data/products.json, the templates in src/partials/ and the
info pages in src/pages/, then writes:
  index.html                       homepage (current drop)
  shop/index.html                  every available piece, filterable
  record/index.html                every piece ever released, by drop
  products/<handle>/index.html     one page per piece
  <slug>/index.html                about, contact, size guide, privacy, terms
  shopify/products.csv             Shopify product import (same data)
  sitemap.xml, robots.txt

Photos: drop files into assets/products/<handle>/ (01.jpg, 02.jpg ...) and rebuild.
If Pillow is installed (pip install pillow) web-sized copies are made in
assets/products/<handle>/web/. Without it, the originals are used as they are.

Usage:  python3 build.py
"""
from __future__ import annotations

import csv
import datetime as dt
import html
import json
import re
import shutil
import struct
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from PIL import Image, ImageOps
except ImportError:  # photos are then served at original size
    Image = None

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src" / "partials"
PAGES = ROOT / "src" / "pages"
UK = ZoneInfo("Europe/London")
NOW = dt.datetime.now(UK)
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
TAGS = {"ink", "pine", "paper"}
WEB_WIDTHS = (480, 960, 1600)
# Info page slugs become top-level folders that the build deletes and regenerates,
# so they must never collide with real folders.
RESERVED = {"assets", "data", "src", "docs", "shopify", "products", "shop", "record", "github", "node_modules"}
WM = "".join(f'<use href="#wm-{c}" class="wm-l"/>' for c in ["A", "R", "C", "H", "I", "V", "E", "8a", "8b"])
SCRIPTS = ["assets/vendor/gsap.min.js", "assets/vendor/ScrollTrigger.min.js", "assets/vendor/lenis.min.js",
           "assets/js/site.js"]

warnings: list[str] = []


def e(s) -> str:
    """HTML-escape text for element content and attributes."""
    return html.escape(str(s), quote=True)


def partial(name: str) -> str:
    return (SRC / f"{name}.html").read_text()


def fill(tpl: str, ctx: dict) -> str:
    """Replace {{key}} placeholders. Unknown keys are left visible so they get noticed."""
    def sub(m):
        key = m.group(1)
        if key.startswith("social:"):
            return social(key.split(":", 1)[1], ctx["_site"])
        if key.startswith("biz:"):
            return biz(ctx["_site"], key.split(":", 1)[1])
        if key in ctx:
            return str(ctx[key])
        warnings.append(f"unfilled placeholder {{{{{key}}}}}")
        return m.group(0)
    return re.sub(r"\{\{([\w:]+)\}\}", sub, tpl)


def social(variant: str, site: dict) -> str:
    links = [("instagram", "Instagram"), ("facebook", "Facebook")]
    items = "".join(
        f'<li><a class="social__btn" href="{e(site["social"][k])}" target="_blank" rel="noopener noreferrer" '
        f'aria-label="{label} (opens in a new tab)"><span class="social__base" aria-hidden="true"></span>'
        f'<span class="social__face"><svg aria-hidden="true"><use href="#ico-{k}"/></svg></span></a></li>'
        for k, label in links
    )
    return f'<ul class="social social--{variant}" aria-label="Archive 88 on social media">{items}</ul>'


def biz(site, key) -> str:
    """Business detail for info pages; missing values are visibly marked."""
    v = (site.get("business") or {}).get(key, "")
    if not v:
        return '<span class="tbc">To be confirmed</span>'
    if key == "email":
        return f'<a href="mailto:{e(v)}">{e(v)}</a>'
    if key == "phone":
        return f'<a href="tel:{e(re.sub(r"[^0-9+]", "", v))}">{e(v)}</a>'
    return e(v).replace("\n", "<br />")


def money(n, site) -> str:
    return site["currency_symbol"] + (f"{n:,.0f}" if float(n).is_integer() else f"{n:,.2f}")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ---------------------------------------------------------------- photos

def photo_sources(handle: str) -> list[Path]:
    folder = ROOT / "assets" / "products" / handle
    if not folder.is_dir():
        return []
    return [p for p in sorted(folder.iterdir())
            if p.is_file() and p.suffix.lower() in IMG_EXT and not p.name.startswith(".")]


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def make_web_copies(src: Path):
    """WebP at several widths + one 1200px JPEG (share previews, bag, fallback). Skips up-to-date files."""
    web = src.parent / "web"
    web.mkdir(exist_ok=True)
    stem = src.stem
    targets = {w: web / f"{stem}-{w}.webp" for w in WEB_WIDTHS}
    jpg = web / f"{stem}-1200.jpg"
    if all(t.exists() and t.stat().st_mtime >= src.stat().st_mtime for t in [*targets.values(), jpg]):
        return targets, jpg
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        for w, out in targets.items():
            copy = im.copy()
            if copy.width > w:
                copy = copy.resize((w, round(copy.height * w / copy.width)), Image.LANCZOS)
            copy.save(out, "WEBP", quality=80, method=6)
        copy = im.copy()
        if copy.width > 1200:
            copy = copy.resize((1200, round(copy.height * 1200 / copy.width)), Image.LANCZOS)
        copy.save(jpg, "JPEG", quality=82, optimize=True, progressive=True)
    return targets, jpg


def photos_for(handle: str) -> list[dict]:
    """[{orig, src, srcset}] per photo. src is the light JPEG when available."""
    out = []
    sources = photo_sources(handle)
    if sources and Image is None:
        warnings.append("Pillow not installed: product photos are served at full size (pip install pillow)")
    keep = set()
    for s in sources:
        if Image is not None:
            targets, jpg = make_web_copies(s)
            keep.update([*targets.values(), jpg])
            srcset = ", ".join(f"{rel(t)} {w}w" for w, t in targets.items())
            out.append({"orig": rel(s), "src": rel(jpg), "srcset": srcset})
        else:
            out.append({"orig": rel(s), "src": rel(s), "srcset": ""})
    web = ROOT / "assets" / "products" / handle / "web"
    if Image is not None and web.is_dir():  # remove copies of photos that were deleted
        for f in web.iterdir():
            if f not in keep:
                f.unlink()
    return out


def img_tag(photo, root, alt, sizes, lazy=True, cls=""):
    srcset = ", ".join(f"{root}{part}" for part in photo["srcset"].split(", ")) if photo["srcset"] else ""
    return (f'<img{f" class={chr(34)}{cls}{chr(34)}" if cls else ""} src="{root}{photo["src"]}"'
            + (f' srcset="{srcset}" sizes="{sizes}"' if srcset else "")
            + f' alt="{e(alt)}"{" loading=" + chr(34) + "lazy" + chr(34) if lazy else ""} decoding="async" />')


def image_size(path: Path):
    """Width/height for JPEG and PNG without third-party libraries (for og:image)."""
    try:
        data = path.read_bytes()
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", data[16:24])
        if data[:2] == b"\xff\xd8":
            i = 2
            while i < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    except Exception:
        pass
    return None


def mime(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")


# ---------------------------------------------------------------- drops

def drop_label(when: dt.datetime) -> str:
    hour = when.strftime("%I").lstrip("0")
    mins = "" if when.minute == 0 else when.strftime(":%M")
    return f"{when.strftime('%A')} {when.day} {when.strftime('%B')}, {hour}{mins}{when.strftime('%p').lower()}"


def load_drops(site):
    drops = []
    for d in site["drops"]["list"]:
        when = dt.datetime.fromisoformat(d["date"]).astimezone(UK)
        drops.append({**d, "when": when, "iso": when.isoformat(), "label": drop_label(when),
                      "year": when.year, "month": when.strftime("%B %Y")})
    drops.sort(key=lambda d: d["when"])
    past = [d for d in drops if d["when"] <= NOW]
    future = [d for d in drops if d["when"] > NOW]
    current = past[-1] if past else (drops[0] if drops else None)
    nxt = future[0] if future else None
    if not past:
        warnings.append("no drop date has passed yet; showing the first drop on the homepage")
    return drops, current, nxt


# ---------------------------------------------------------------- validation

def validate(site, products):
    cats = {c["handle"] for c in site["categories"]}
    drops = {d["handle"] for d in site["drops"]["list"]}
    seen_h, seen_n = set(), set()
    required = ["handle", "number", "title", "category", "drop", "price", "available", "tag",
                "era", "size", "material", "condition", "measurements_cm", "description"]
    for p in products:
        for k in required:
            if k not in p or p[k] in ("", None):
                sys.exit(f"products.json: '{p.get('handle', '?')}' is missing '{k}'")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", p["handle"]):
            sys.exit(f"products.json: handle '{p['handle']}' must be lowercase-with-dashes")
        if p["handle"] in seen_h or p["number"] in seen_n:
            sys.exit(f"products.json: duplicate handle or number at '{p['handle']}'")
        seen_h.add(p["handle"]); seen_n.add(p["number"])
        if p["category"] not in cats:
            sys.exit(f"products.json: '{p['handle']}' has unknown category '{p['category']}'")
        if p["drop"] not in drops:
            sys.exit(f"products.json: '{p['handle']}' has unknown drop '{p['drop']}' (see drops.list in site.json)")
        if p["tag"] not in TAGS:
            sys.exit(f"products.json: '{p['handle']}' tag must be one of {sorted(TAGS)}")
        if not photo_sources(p["handle"]):
            warnings.append(f"no photos yet for {p['handle']} (assets/products/{p['handle']}/)")
    missing = [k for k in ("legal_name", "address", "email") if not (site.get("business") or {}).get(k)]
    if missing:
        warnings.append(f"business details still to add in site.json: {', '.join(missing)}")


# ---------------------------------------------------------------- shared markup

def cat_title(site, handle):
    return next(c["title"] for c in site["categories"] if c["handle"] == handle)


def tag_card(p, site, root, extra_class="", photos=None):
    """The hang tag: archive track, shop grid and 'More from the archive'."""
    url = f"{root}products/{p['handle']}/"
    photos = photos if photos is not None else PHOTOS[p["handle"]]
    sold = not p["available"]
    if photos:
        photo = img_tag(photos[0], root, f'{p["title"]}, front', "(max-width: 720px) 70vw, 320px")
        photo_cls = "has-photo"
    else:
        photo = '<svg class="tag__mono" viewBox="0 0 146 68" aria-hidden="true"><use href="#mono"/></svg>'
        photo_cls = "is-empty"
    action = '<span class="tag__sold">Sold</span>' if sold else add_button(p, site, "tag__add", photos)
    data = (f'data-cat="{p["category"]}" data-size="{e(slug(p["size"]))}" data-sold="{"1" if sold else "0"}" '
            f'data-price="{p["price"]}" data-no="{e(p["number"])}"')
    return f'''          <article class="tag tag--{p["tag"]}{" is-sold" if sold else ""}{extra_class}" {data}>
            <span class="tag__hole"></span>
            <div class="tag__top"><span>No. {e(p["number"])}</span><span>{e(p["size"])}</span></div>
            <a class="tag__photo {photo_cls}" href="{url}" tabindex="-1" aria-hidden="true">{photo}{'<span class="tag__stamp">Sold</span>' if sold else ''}</a>
            <div class="tag__body">
              <h3><a class="tag__link" href="{url}">{e(p["title"])}</a></h3>
              <dl><dt>Category</dt><dd>{e(cat_title(site, p["category"]))}</dd><dt>Era</dt><dd>{e(p["era"])}</dd></dl>
              {action}
            </div>
          </article>'''


def add_button(p, site, cls, photos, block=False):
    img = photos[0]["src"] if photos else ""
    return (f'<button class="{cls}{" btn--block" if block else ""} js-add" type="button" data-id="{e(p["number"])}" '
            f'data-name="{e(p["title"])}" data-cat="{e(cat_title(site, p["category"]))}" data-price="{p["price"]}" '
            f'data-theme="tag--{p["tag"]}" data-img="{e(img)}" data-url="products/{p["handle"]}/">'
            f'<span class="tag__price">{money(p["price"], site)}</span><span class="tag__cta">Add to bag</span></button>')


def menu_cats(site, products, root):
    avail = [p for p in products if p["available"]]
    rows = [("all", "All pieces", 1, "Everything available now. One of each, numbered.", len(avail))]
    rows += [(c["handle"], c["title"], c["image"], c["description"],
              sum(1 for p in avail if p["category"] == c["handle"])) for c in site["categories"]]
    out = []
    for i, (h, title, img, desc, n) in enumerate(rows):
        href = f"{root}shop/" + ("" if h == "all" else f"?cat={h}")
        out.append(
            f'          <li><a href="{href}" data-cat="{h}" data-img="{img}" data-desc="{e(desc)}">'
            f'<span class="menu__num">{i:02d}</span><span class="menu__name"><span>{e(title)}</span></span>'
            f'<span class="menu__count">{n:02d}</span><span class="menu__arrow" aria-hidden="true">→</span></a></li>')
    return "\n".join(out), rows[0][3]


def accordion(items, prefix, open_first=False):
    out = []
    for i, (q, a_html) in enumerate(items, 1):
        is_open = open_first and i == 1
        out.append(f'''          <div class="acc js-acc">
            <button class="acc__q" type="button" aria-expanded="{"true" if is_open else "false"}" aria-controls="{prefix}-{i}" id="{prefix}-q{i}"><span>{e(q)}</span><i aria-hidden="true"></i></button>
            <div class="acc__a" id="{prefix}-{i}" role="region" aria-labelledby="{prefix}-q{i}"{"" if is_open else " hidden"}><div class="acc__body">{a_html}</div></div>
          </div>''')
    return "\n".join(out)


def countdown(nxt, cls=""):
    """Live countdown markup (filled in by site.js). Hidden by the script once the date passes."""
    if not nxt:
        return ""
    unit = lambda k, label: (f'<span class="cd__unit"><span class="cd__num js-cd-{k}">00</span>'
                             f'<span class="cd__label">{label}</span></span>')
    return (f'<div class="countdown js-countdown js-drop {cls}" data-drop="{nxt["iso"]}" role="timer" '
            f'aria-label="Time until {e(nxt["name"])}: {e(nxt["label"])}">'
            f'<p class="countdown__title">{e(nxt["name"])} drops {e(nxt["label"])}</p>'
            f'<div class="countdown__units" aria-hidden="true">{unit("d", "Days")}{unit("h", "Hours")}'
            f'{unit("m", "Minutes")}{unit("s", "Seconds")}</div></div>')


def base_ctx(site, products, root, page_id):
    cats_html, first_desc = menu_cats(site, products, root)
    return {"_site": site, "root": root, "home": root, "page": page_id, "wm": WM, "year": NOW.year,
            "locale": site["locale"], "menu_cats": cats_html, "menu_first_desc": e(first_desc),
            "og_type": "website", "og_image": site["url"] + "assets/img/og-image.jpg",
            "og_image_type": "image/jpeg", "og_image_w": 1200, "og_image_h": 630,
            "og_image_alt": "The Archive 88 wordmark over a sunlit pine forest path, two people walking toward the sea.",
            "extra_meta": ""}


def page(ctx, body_attrs, body_html, scripts):
    head = fill(partial("head"), ctx)
    tail = "\n".join(f'  <script src="{ctx["root"]}{s}"></script>' for s in [*SCRIPTS, *scripts])
    return (f"{head}<body {body_attrs}>\n  <div class=\"grain\" aria-hidden=\"true\"></div>\n\n{partial('defs')}\n"
            f"{body_html}\n{tail}\n</body>\n</html>\n")


def write(path: str, content: str):
    out = ROOT / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content)


def org_ld(site):
    b = site.get("business") or {}
    org = {"@type": "Organization", "@id": site["url"] + "#org", "name": site["name"], "url": site["url"],
           "logo": site["url"] + "assets/img/icon-512.png", "image": site["url"] + "assets/img/og-image.jpg",
           "description": site["description"], "foundingDate": "1988",
           "sameAs": [site["social"]["instagram"], site["social"]["facebook"]]}
    if b.get("legal_name"):
        org["legalName"] = b["legal_name"]
    if b.get("email"):
        org["email"] = b["email"]
    return org


def product_ld(p, site):
    url = f'{site["url"]}products/{p["handle"]}/'
    photos = PHOTOS[p["handle"]]
    return {
        "@type": "Product", "@id": url + "#product", "name": p["title"], "sku": f'A88-{p["number"]}',
        "url": url, "description": p["description"], "category": cat_title(site, p["category"]),
        "brand": {"@id": site["url"] + "#org"}, "material": p["material"], "size": p["size"],
        "image": [site["url"] + ph["src"] for ph in photos] or [site["url"] + "assets/img/og-image.jpg"],
        "offers": {
            "@type": "Offer", "url": url, "price": f'{p["price"]:.2f}', "priceCurrency": site["currency"],
            "availability": "https://schema.org/" + ("InStock" if p["available"] else "SoldOut"),
            "itemCondition": "https://schema.org/UsedCondition", "seller": {"@id": site["url"] + "#org"},
        },
    }


def ld_json(graph) -> str:
    text = json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=2, ensure_ascii=False)
    return "\n".join("  " + line for line in text.replace("</", "<\\/").splitlines())


def breadcrumbs_ld(site, items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(items, 1)]}


# ---------------------------------------------------------------- pages

def build_home(site, products, current, nxt):
    root = ""
    ctx = base_ctx(site, products, root, "home")
    faq = accordion([(f["q"], f'<p>{e(f["a"])}</p>') for f in site["returns_faq"]], "acc")
    in_drop = [p for p in products if current and p["drop"] == current["handle"]]
    drop_attr = f' data-drop="{nxt["iso"]}"' if nxt else ""
    ctx.update({
        "title": e(site["title"]), "description": e(site["description"]), "canonical": site["url"],
        "jsonld": ld_json([org_ld(site),
                           {"@type": "WebSite", "@id": site["url"] + "#website", "url": site["url"],
                            "name": site["name"], "publisher": {"@id": site["url"] + "#org"}, "inLanguage": "en-GB"},
                           {"@type": "ItemList", "name": current["name"] if current else "The archive",
                            "itemListElement": [
                                {"@type": "ListItem", "position": i, "url": f'{site["url"]}products/{p["handle"]}/'}
                                for i, p in enumerate(in_drop, 1)]}]),
        "drop_name": e(current["name"]) if current else "The archive",
        "archive_tags": "\n".join(tag_card(p, site, root) for p in in_drop),
        "returns_faq": faq,
        "next_drop_hero": (f' <span class="hero__drop js-drop"{drop_attr}>Next drop: {e(nxt["label"])}.</span>'
                           if nxt else ""),
        "countdown": countdown(nxt, "js-reveal"),
    })
    body = "\n".join(fill(partial(n), ctx) for n in ["loader", "header", "home-main", "footer"])
    write("index.html", page(ctx, 'class="is-loading" data-nav="bone"', body, ["assets/js/home.js"]))


def build_product(site, products, p, nxt):
    root = "../../"
    url = f'{site["url"]}products/{p["handle"]}/'
    photos = PHOTOS[p["handle"]]
    title = p["title"]
    cat = cat_title(site, p["category"])

    if photos:
        slides = [f'          <figure class="pdp__slide">'
                  + img_tag(ph, root, f"{title}, photo {i}", "(max-width: 900px) 86vw, 55vw", lazy=i > 1)
                  + "</figure>" for i, ph in enumerate(photos, 1)]
    else:
        slides = [f'          <figure class="pdp__slide is-empty tag--{p["tag"]}"><svg viewBox="0 0 146 68" aria-hidden="true">'
                  f'<use href="#mono"/></svg><figcaption>{e(shot)}<small>Photo to come</small></figcaption></figure>'
                  for shot in site["shot_list"]]
    pager = "".join(f'<i{" class=\"is-on\"" if i == 0 else ""}></i>' for i in range(len(slides)))

    if p["available"]:
        buy = "          " + add_button(p, site, "buy-btn", photos, block=True)
        if p.get("final_sale"):
            buy += ('\n          <p class="pdp__note"><strong>Final sale.</strong> Excluded from 30-day returns. '
                    'Your 14-day legal right to cancel still applies.</p>')
    else:
        buy = ('          <p class="pdp__sold">Sold</p>\n'
               '          <p class="pdp__note">This piece has found a home. '
               + (f'{e(nxt["name"])} drops {e(nxt["label"])}. ' if nxt else "")
               + f'Join the list to see it first.</p>\n          <a class="btn btn--ink btn--block" href="{root}#join">Join the list</a>')

    rows = "".join(f"<tr><th scope=\"row\">{e(k)}</th><td>{e(v)} cm</td></tr>" for k, v in p["measurements_cm"].items())
    flaws = ("<ul class=\"pdp__flaws\">" + "".join(f"<li>{e(f)}</li>" for f in p.get("flaws", [])) + "</ul>"
             if p.get("flaws") else "<p>Nothing to note beyond normal wear for its age.</p>")
    details = accordion([
        ("Measurements", f'<table class="pdp__measure"><caption>Measured flat, in centimetres. Labelled size: {e(p["size"])}. '
                         f'<a href="{root}size-guide/">How we measure</a>.</caption><tbody>{rows}</tbody></table>'),
        ("Condition", f'<p><strong>{e(p["condition"])}.</strong> {e(p.get("condition_notes", ""))}</p>{flaws}'),
        ("Material", f'<p>{e(p["material"])}</p>'),
        ("Shipping", f'<p>{e(site["shipping"]["text"])}</p>'),
        ("Returns", f'<p>30 days from delivery for a full refund. <a href="{root}#returns">How returns work</a>.</p>'),
    ], "pd", open_first=True)

    others = sorted((o for o in products if o["handle"] != p["handle"]),
                    key=lambda o: (not o["available"], o["category"] != p["category"]))[:3]
    more = "\n".join(tag_card(o, site, root, " tag--grid js-reveal") for o in others)

    desc = f'{p["description"]} Size {p["size"]}, {p["era"]}. One of one, {money(p["price"], site)}.'
    ctx = base_ctx(site, products, root, "product")
    if photos and image_size(ROOT / photos[0]["src"]):
        w, h = image_size(ROOT / photos[0]["src"])
        ctx.update({"og_image": site["url"] + photos[0]["src"], "og_image_type": mime(photos[0]["src"]),
                    "og_image_w": w, "og_image_h": h, "og_image_alt": f"{title} from Archive 88"})
    ctx.update({
        "og_type": "product",
        "extra_meta": "\n".join([
            f'  <meta property="product:price:amount" content="{p["price"]:.2f}" />',
            f'  <meta property="product:price:currency" content="{site["currency"]}" />',
            f'  <meta property="product:availability" content="{"in stock" if p["available"] else "out of stock"}" />',
            '  <meta property="product:condition" content="used" />',
            f'  <meta property="product:retailer_item_id" content="A88-{p["number"]}" />']),
        "title": e(f"{title} No. {p['number']} - Archive 88"), "description": e(desc), "canonical": url,
        "jsonld": ld_json([org_ld(site), product_ld(p, site), breadcrumbs_ld(site, [
            ("Shop", site["url"] + "shop/"), (cat, f'{site["url"]}shop/?cat={p["category"]}'), (title, url)])]),
        "handle": p["handle"], "number": e(p["number"]), "category": p["category"], "category_title": e(cat),
        "name": e(title), "title_lower": e(title.lower()), "price_fmt": money(p["price"], site),
        "size": e(p["size"]), "era": e(p["era"]), "condition": e(p["condition"]),
        "description": e(p["description"]), "gallery": "\n".join(slides), "pager": pager,
        "buy": buy, "details": details, "more": more,
    })
    body = "\n".join(fill(partial(n), ctx) for n in ["header", "product-main", "footer"])
    write(f"products/{p['handle']}/index.html",
          page(ctx, f'data-nav="paper" class="{"is-sold" if not p["available"] else ""}"', body, ["assets/js/product.js"]))


def build_shop(site, products, nxt):
    root = "../"
    ctx = base_ctx(site, products, root, "shop")
    avail = [p for p in products if p["available"]]
    chip = lambda group, val, label, n=None, on=False: (
        f'<button class="chip{" is-on" if on else ""}" type="button" data-{group}="{e(val)}" aria-pressed="{"true" if on else "false"}">'
        f'{e(label)}{f"<span>{n}</span>" if n is not None else ""}</button>')
    cat_chips = [chip("cat", "all", "All", len(avail), True)] + [
        chip("cat", c["handle"], c["title"], sum(1 for p in avail if p["category"] == c["handle"]))
        for c in site["categories"]]
    sizes = list(dict.fromkeys(p["size"] for p in products))
    size_chips = [chip("size", "all", "Any", None, True)] + [chip("size", slug(s), s) for s in sizes]
    # Available pieces first (newest numbers first), then sold ones (hidden until "Include sold").
    ordered = sorted(products, key=lambda p: (not p["available"], -int(re.sub(r"\D", "", p["number"]) or 0)))
    ctx.update({
        "title": "Shop all - Archive 88",
        "description": e("Every piece available in the Archive 88 archive. Filter by category and size. One of each."),
        "canonical": site["url"] + "shop/",
        "jsonld": ld_json([org_ld(site), {"@type": "CollectionPage", "name": "Shop all", "url": site["url"] + "shop/",
                                          "isPartOf": {"@id": site["url"] + "#website"}}]),
        "cat_chips": "\n".join("            " + c for c in cat_chips),
        "size_chips": "\n".join("            " + c for c in size_chips),
        "grid": "\n".join(tag_card(p, site, root, " tag--grid") for p in ordered),
        "count": len(avail),
        "join_note": (f"{e(nxt['name'])} drops {e(nxt['label'])}." if nxt else "New pieces arrive with every drop."),
    })
    body = "\n".join(fill(partial(n), ctx) for n in ["header", "shop-main", "footer"])
    write("shop/index.html", page(ctx, 'data-nav="paper"', body, ["assets/vendor/Flip.min.js", "assets/js/shop.js"]))


def build_record(site, products, drops):
    root = "../"
    ctx = base_ctx(site, products, root, "record")
    groups = []
    for d in reversed([d for d in drops if any(p["drop"] == d["handle"] for p in products)]):
        pieces = sorted((p for p in products if p["drop"] == d["handle"]), key=lambda p: p["number"])
        sold = sum(1 for p in pieces if not p["available"])
        rows = "\n".join(
            f'''              <tr class="{"is-sold" if not p["available"] else ""}">
                <td class="rec__no">No. {e(p["number"])}</td>
                <th scope="row" class="rec__name"><a href="{root}products/{p["handle"]}/">{e(p["title"])}</a></th>
                <td>{e(cat_title(site, p["category"]))}</td><td>{e(p["size"])}</td><td>{e(p["era"])}</td>
                <td class="rec__status">{"Sold" if not p["available"] else "Available"}</td>
              </tr>''' for p in pieces)
        groups.append(f'''        <section class="rec js-reveal" aria-labelledby="drop-{d["handle"]}">
          <header class="rec__head">
            <h2 id="drop-{d["handle"]}">{e(d["name"])}</h2>
            <p>Released {e(d["month"])}. {len(pieces)} pieces, {sold} sold.</p>
          </header>
          <table class="rec__table">
            <thead><tr><th scope="col">No.</th><th scope="col">Piece</th><th scope="col">Category</th><th scope="col">Size</th><th scope="col">Era</th><th scope="col">Status</th></tr></thead>
            <tbody>
{rows}
            </tbody>
          </table>
        </section>''')
    total = len(products)
    ctx.update({
        "title": "The record - Archive 88",
        "description": e("Every piece Archive 88 has released, kept on record by drop. Sold pieces stay listed."),
        "canonical": site["url"] + "record/",
        "jsonld": ld_json([org_ld(site), {"@type": "CollectionPage", "name": "The record", "url": site["url"] + "record/"}]),
        "groups": "\n".join(groups), "total": total,
        "sold_total": sum(1 for p in products if not p["available"]),
    })
    body = "\n".join(fill(partial(n), ctx) for n in ["header", "record-main", "footer"])
    write("record/index.html", page(ctx, 'data-nav="paper"', body, []))


def build_info_pages(site, products):
    """src/pages/<slug>.html: first line is a JSON comment with title/description/lede."""
    built = []
    for f in sorted(PAGES.glob("*.html")):
        text = f.read_text()
        m = re.match(r"\s*<!--\s*(\{.*?\})\s*-->\s*", text, re.S)
        if not m:
            sys.exit(f"{f}: must start with <!-- {{\"title\": ..., \"description\": ...}} -->")
        meta = json.loads(m.group(1))
        slug_ = f.stem
        root = "../"
        ctx = base_ctx(site, products, root, slug_)
        is_legal = meta.get("legal", False)
        ctx.update({
            "title": e(f'{meta["title"]} - Archive 88'), "description": e(meta["description"]),
            "canonical": f'{site["url"]}{slug_}/',
            "jsonld": ld_json([org_ld(site), {"@type": "WebPage", "name": meta["title"], "url": f'{site["url"]}{slug_}/'}]),
            "page_title": e(meta["title"]), "lede": meta.get("lede", ""),
            "updated": f"{NOW.day} {NOW.strftime('%B %Y')}",
            "shipping_text": e(site["shipping"]["text"]),
            "_ig": e(site["social"]["instagram"]),
            "legal_note": ('<p class="legal-note"><strong>Draft.</strong> This is a starting template, not legal advice. '
                           'Have it checked before the shop opens.</p>' if is_legal and not site.get("legal_reviewed") else ""),
        })
        ctx["content"] = fill(text[m.end():], ctx)
        body = "\n".join(fill(partial(n), ctx) for n in ["header", "page-main", "footer"])
        write(f"{slug_}/index.html", page(ctx, 'data-nav="paper"', body, []))
        built.append(slug_)
    return built


# ---------------------------------------------------------------- Shopify CSV

def build_shopify_csv(site, products, drops):
    drop_names = {d["handle"]: d["name"] for d in drops}
    meta = {
        "Number (product.metafields.archive.number)": lambda p: p["number"],
        "Era (product.metafields.archive.era)": lambda p: p["era"],
        "Size (product.metafields.archive.size)": lambda p: p["size"],
        "Material (product.metafields.archive.material)": lambda p: p["material"],
        "Condition (product.metafields.archive.condition)": lambda p: p["condition"],
        "Condition notes (product.metafields.archive.condition_notes)": lambda p: p.get("condition_notes", ""),
        "Flaws (product.metafields.archive.flaws)": lambda p: "\n".join(p.get("flaws", [])),
        "Measurements (product.metafields.archive.measurements)": lambda p: json.dumps(p["measurements_cm"]),
        "Tag colour (product.metafields.archive.tag_colour)": lambda p: p["tag"],
        "Final sale (product.metafields.archive.final_sale)": lambda p: "TRUE" if p.get("final_sale") else "FALSE",
        "Drop (product.metafields.archive.drop)": lambda p: drop_names[p["drop"]],
    }
    cols = ["Handle", "Title", "Body (HTML)", "Vendor", "Product Category", "Type", "Tags", "Published",
            "Option1 Name", "Option1 Value", "Variant SKU", "Variant Grams", "Variant Inventory Tracker",
            "Variant Inventory Qty", "Variant Inventory Policy", "Variant Fulfillment Service", "Variant Price",
            "Variant Compare At Price", "Variant Requires Shipping", "Variant Taxable", "Image Src",
            "Image Position", "Image Alt Text", "Gift Card", "SEO Title", "SEO Description", "Status", *meta]
    (ROOT / "shopify").mkdir(exist_ok=True)
    with open(ROOT / "shopify" / "products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for p in products:
            photos = PHOTOS[p["handle"]]
            row = {c: "" for c in cols}
            row.update({
                "Handle": p["handle"], "Title": p["title"], "Body (HTML)": f'<p>{e(p["description"])}</p>',
                "Vendor": site["name"], "Type": cat_title(site, p["category"]),
                "Tags": ", ".join([cat_title(site, p["category"]), drop_names[p["drop"]], p["era"], f'size {p["size"]}']),
                "Published": "TRUE", "Option1 Name": "Title", "Option1 Value": "Default Title",
                "Variant SKU": f'A88-{p["number"]}', "Variant Inventory Tracker": "shopify",
                "Variant Inventory Qty": 1 if p["available"] else 0, "Variant Inventory Policy": "deny",
                "Variant Fulfillment Service": "manual", "Variant Price": f'{p["price"]:.2f}',
                "Variant Requires Shipping": "TRUE", "Variant Taxable": "TRUE", "Gift Card": "FALSE",
                "SEO Title": f'{p["title"]} No. {p["number"]} - Archive 88',
                "SEO Description": p["description"], "Status": "active",
                **{k: fn(p) for k, fn in meta.items()},
            })
            # Shopify downloads and resizes the originals itself.
            for i, ph in enumerate(photos, 1):
                img = {"Image Src": site["url"] + ph["orig"], "Image Position": i, "Image Alt Text": f'{p["title"]}, photo {i}'}
                if i == 1:
                    row.update(img)
                    w.writerow(row)
                else:
                    w.writerow({**{c: "" for c in cols}, "Handle": p["handle"], **img})
            if not photos:
                w.writerow(row)


# ---------------------------------------------------------------- main

PHOTOS: dict[str, list[dict]] = {}


def main():
    site = json.loads((ROOT / "data" / "site.json").read_text())
    products = json.loads((ROOT / "data" / "products.json").read_text())["products"]
    validate(site, products)
    drops, current, nxt = load_drops(site)
    for p in products:
        PHOTOS[p["handle"]] = photos_for(p["handle"])

    # Scheduled drops: pieces from a drop whose date hasn't arrived stay off the site
    # (they are still in the Shopify CSV). The hourly GitHub rebuild publishes them.
    released_drops = {d["handle"] for d in drops if d["when"] <= NOW} or ({current["handle"]} if current else set())
    all_products = products
    products = [p for p in all_products if p["drop"] in released_drops]
    waiting = len(all_products) - len(products)

    # Generated folders are rebuilt from scratch so removed pieces and pages don't linger.
    shutil.rmtree(ROOT / "products", ignore_errors=True)
    for f in PAGES.glob("*.html"):
        if f.stem.lower() in RESERVED or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", f.stem):
            sys.exit(f"src/pages/{f.name}: '{f.stem}' can't be used as a page name")
        shutil.rmtree(ROOT / f.stem, ignore_errors=True)

    build_home(site, products, current, nxt)
    for p in products:
        build_product(site, products, p, nxt)
    build_shop(site, products, nxt)
    build_record(site, products, drops)
    info = build_info_pages(site, products)
    build_shopify_csv(site, all_products, drops)

    urls = ([site["url"], site["url"] + "shop/", site["url"] + "record/"]
            + [f'{site["url"]}{s}/' for s in info]
            + [f'{site["url"]}products/{p["handle"]}/' for p in products])
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {site['url']}sitemap.xml\n")

    print(f"Built home, shop, record, {len(info)} info pages and {len(products)} product pages"
          f"{'' if Image else ' (Pillow not installed: no photo resizing)'}.")
    if current:
        print(f"  homepage drop: {current['name']}" + (f"; next: {nxt['name']} on {nxt['label']}" if nxt else ""))
    if waiting:
        print(f"  {waiting} piece(s) waiting for a future drop (not on the site yet)")
    for w in dict.fromkeys(warnings):
        print("  note:", w)


if __name__ == "__main__":
    main()
