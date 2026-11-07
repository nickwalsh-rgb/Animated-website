#!/usr/bin/env python3
"""Archive 88 site build.

Reads data/site.json + data/products.json and the templates in src/partials/,
then writes:
  index.html                       homepage
  products/<handle>/index.html     one page per piece
  shopify/products.csv             Shopify product import (same data)
  sitemap.xml, robots.txt

Photos: drop files into assets/products/<handle>/ (01.jpg, 02.jpg ...) and rebuild.

Usage:  python3 build.py
Only the Python standard library is used.
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

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src" / "partials"
UK = ZoneInfo("Europe/London")
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
TAGS = {"ink", "pine", "paper"}
WM = "".join(f'<use href="#wm-{c}" class="wm-l"/>' for c in ["A", "R", "C", "H", "I", "V", "E", "8a", "8b"])

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


def money(n, site) -> str:
    return site["currency_symbol"] + (f"{n:,.0f}" if float(n).is_integer() else f"{n:,.2f}")


# ---------------------------------------------------------------- images

def photos_for(handle: str) -> list[str]:
    folder = ROOT / "assets" / "products" / handle
    if not folder.is_dir():
        return []
    return [f"assets/products/{handle}/{p.name}" for p in sorted(folder.iterdir())
            if p.suffix.lower() in IMG_EXT and not p.name.startswith(".")]


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


# ---------------------------------------------------------------- drop date

def next_drop(site: dict):
    d = site.get("next_drop") or {}
    if not d.get("date"):
        return None
    when = dt.datetime.fromisoformat(d["date"]).astimezone(UK)
    if when < dt.datetime.now(UK):
        warnings.append(f"next_drop date {d['date']} is in the past; it is hidden")
        return None
    hour = when.strftime("%I").lstrip("0")
    mins = "" if when.minute == 0 else when.strftime(":%M")
    ampm = when.strftime("%p").lower()
    label = f"{when.strftime('%A')} {when.day} {when.strftime('%B')}, {hour}{mins}{ampm}"
    return {"iso": when.isoformat(), "label": label, "name": d.get("name", "")}


# ---------------------------------------------------------------- validation

def validate(site, products):
    cats = {c["handle"] for c in site["categories"]}
    seen_h, seen_n = set(), set()
    required = ["handle", "number", "title", "category", "price", "available", "tag",
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
        if p["tag"] not in TAGS:
            sys.exit(f"products.json: '{p['handle']}' tag must be one of {sorted(TAGS)}")
        if not photos_for(p["handle"]):
            warnings.append(f"no photos yet for {p['handle']} (assets/products/{p['handle']}/)")


# ---------------------------------------------------------------- shared markup

def cat_title(site, handle):
    return next(c["title"] for c in site["categories"] if c["handle"] == handle)


def tag_card(p, site, root, extra_class=""):
    """The hang tag used in the archive track and in 'More from the archive'."""
    url = f"{root}products/{p['handle']}/"
    photos = photos_for(p["handle"])
    sold = not p["available"]
    if photos:
        photo = (f'<img src="{root}{photos[0]}" alt="{e(p["title"])}, front" loading="lazy" decoding="async" />')
        photo_cls = "has-photo"
    else:
        photo = '<svg class="tag__mono" viewBox="0 0 146 68" aria-hidden="true"><use href="#mono"/></svg>'
        photo_cls = "is-empty"
    if sold:
        action = '<span class="tag__sold">Sold</span>'
    else:
        action = add_button(p, site, "tag__add", photos)
    return f'''          <article class="tag tag--{p["tag"]}{" is-sold" if sold else ""}{extra_class}" data-cat="{p["category"]}">
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
    img = photos[0] if photos else ""
    return (f'<button class="{cls}{" btn--block" if block else ""} js-add" type="button" data-id="{e(p["number"])}" '
            f'data-name="{e(p["title"])}" data-cat="{e(cat_title(site, p["category"]))}" data-price="{p["price"]}" '
            f'data-theme="tag--{p["tag"]}" data-img="{e(img)}" data-url="products/{p["handle"]}/">'
            f'<span class="tag__price">{money(p["price"], site)}</span><span class="tag__cta">Add to bag</span></button>')


def menu_cats(site, products, home):
    avail = [p for p in products if p["available"]]
    rows = [("all", "All pieces", 1, "Everything currently in the archive. One of each, numbered.", len(avail))]
    rows += [(c["handle"], c["title"], c["image"], c["description"],
              sum(1 for p in avail if p["category"] == c["handle"])) for c in site["categories"]]
    out = []
    for i, (h, title, img, desc, n) in enumerate(rows):
        out.append(
            f'          <li><a href="{home}#shop-{h}" data-cat="{h}" data-img="{img}" data-desc="{e(desc)}">'
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


def page(site, ctx, body_attrs, body_html, scripts):
    head = fill(partial("head"), ctx)
    defs = partial("defs")
    tail = "\n".join(f'  <script src="{ctx["root"]}{s}"></script>' for s in
                     ["assets/vendor/gsap.min.js", "assets/vendor/ScrollTrigger.min.js", "assets/vendor/lenis.min.js",
                      "assets/js/site.js", *scripts])
    return (f"{head}<body {body_attrs}>\n  <div class=\"grain\" aria-hidden=\"true\"></div>\n\n{defs}\n"
            f"{body_html}\n{tail}\n</body>\n</html>\n")


def org_ld(site):
    return {"@type": "Organization", "@id": site["url"] + "#org", "name": site["name"], "url": site["url"],
            "logo": site["url"] + "assets/img/icon-512.png", "image": site["url"] + "assets/img/og-image.jpg",
            "description": site["description"], "foundingDate": "1988",
            "sameAs": [site["social"]["instagram"], site["social"]["facebook"]]}


def product_ld(p, site):
    url = f'{site["url"]}products/{p["handle"]}/'
    photos = photos_for(p["handle"])
    return {
        "@type": "Product", "@id": url + "#product", "name": p["title"], "sku": f'A88-{p["number"]}',
        "url": url, "description": p["description"], "category": cat_title(site, p["category"]),
        "brand": {"@id": site["url"] + "#org"}, "material": p["material"], "size": p["size"],
        "image": [site["url"] + ph for ph in photos] or [site["url"] + "assets/img/og-image.jpg"],
        "offers": {
            "@type": "Offer", "url": url, "price": f'{p["price"]:.2f}', "priceCurrency": site["currency"],
            "availability": "https://schema.org/" + ("InStock" if p["available"] else "SoldOut"),
            "itemCondition": "https://schema.org/UsedCondition", "seller": {"@id": site["url"] + "#org"},
        },
    }


def ld_json(graph) -> str:
    text = json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=2, ensure_ascii=False)
    return "\n".join("  " + line for line in text.replace("</", "<\\/").splitlines())


# ---------------------------------------------------------------- pages

def build_home(site, products, drop):
    root, home = "", ""
    cats_html, first_desc = menu_cats(site, products, home)
    faq = accordion([(f["q"], f'<p>{e(f["a"])}</p>') for f in site["returns_faq"]], "acc")
    drop_attr = f' data-drop="{drop["iso"]}"' if drop else ""
    ctx = {
        "_site": site, "root": root, "home": home, "page": "home", "wm": WM, "year": dt.date.today().year,
        "title": e(site["title"]), "description": e(site["description"]), "canonical": site["url"],
        "locale": site["locale"], "og_type": "website",
        "og_image": site["url"] + "assets/img/og-image.jpg", "og_image_type": "image/jpeg",
        "og_image_w": 1200, "og_image_h": 630,
        "og_image_alt": "The Archive 88 wordmark over a sunlit pine forest path, two people walking toward the sea.",
        "extra_meta": "",
        "jsonld": ld_json([org_ld(site),
                           {"@type": "WebSite", "@id": site["url"] + "#website", "url": site["url"],
                            "name": site["name"], "publisher": {"@id": site["url"] + "#org"}, "inLanguage": "en-GB"},
                           {"@type": "ItemList", "name": "The archive", "itemListElement": [
                               {"@type": "ListItem", "position": i, "url": f'{site["url"]}products/{p["handle"]}/'}
                               for i, p in enumerate(products, 1)]}]),
        "menu_cats": cats_html, "menu_first_desc": e(first_desc),
        "archive_tags": "\n".join(tag_card(p, site, root) for p in products),
        "returns_faq": faq,
        "next_drop_hero": (f' <span class="hero__drop js-drop"{drop_attr}>Next drop: {e(drop["label"])}.</span>'
                           if drop else ""),
        "next_drop_join": (f'<p class="join__drop js-reveal js-drop"{drop_attr}>Next drop: '
                           f'<time datetime="{drop["iso"]}">{e(drop["label"])}</time></p>' if drop else ""),
    }
    body = "\n".join(fill(partial(n), ctx) for n in ["loader", "header", "home-main", "footer"])
    out = page(site, ctx, 'class="is-loading" data-nav="bone"', body, ["assets/js/home.js"])
    (ROOT / "index.html").write_text(out)


def build_product(site, products, p, drop):
    root = home = "../../"
    url = f'{site["url"]}products/{p["handle"]}/'
    photos = photos_for(p["handle"])
    title = p["title"]
    cat = cat_title(site, p["category"])

    # Gallery: real photos, else one labelled slot per shot in the shot list.
    if photos:
        slides = [f'          <figure class="pdp__slide"><img src="{root}{ph}" alt="{e(title)}, photo {i}" '
                  f'{"" if i == 1 else "loading=\"lazy\" "}decoding="async" /></figure>'
                  for i, ph in enumerate(photos, 1)]
    else:
        slides = [f'          <figure class="pdp__slide is-empty tag--{p["tag"]}"><svg viewBox="0 0 146 68" aria-hidden="true">'
                  f'<use href="#mono"/></svg><figcaption>{e(shot)}<small>Photo to come</small></figcaption></figure>'
                  for shot in site["shot_list"]]
    pager = "".join(f'<i{" class=\"is-on\"" if i == 0 else ""}></i>' for i in range(len(slides)))

    # Buy box
    if p["available"]:
        buy = "          " + add_button(p, site, "buy-btn", photos, block=True)
        if p.get("final_sale"):
            buy += ('\n          <p class="pdp__note"><strong>Final sale.</strong> Excluded from 30-day returns. '
                    'Your 14-day legal right to cancel still applies.</p>')
    else:
        buy = ('          <p class="pdp__sold">Sold</p>\n'
               '          <p class="pdp__note">This piece has found a home. '
               + (f'The next drop is {e(drop["label"])}. ' if drop else "")
               + f'Join the list to see it first.</p>\n          <a class="btn btn--ink btn--block" href="{home}#join">Join the list</a>')

    # Details accordion
    rows = "".join(f"<tr><th scope=\"row\">{e(k)}</th><td>{e(v)} cm</td></tr>" for k, v in p["measurements_cm"].items())
    flaws = ("<ul class=\"pdp__flaws\">" + "".join(f"<li>{e(f)}</li>" for f in p.get("flaws", [])) + "</ul>"
             if p.get("flaws") else "<p>Nothing to note beyond normal wear for its age.</p>")
    details = accordion([
        ("Measurements", f'<table class="pdp__measure"><caption>Measured flat, in centimetres. Labelled size: {e(p["size"])}.</caption>'
                         f'<tbody>{rows}</tbody></table>'),
        ("Condition", f'<p><strong>{e(p["condition"])}.</strong> {e(p.get("condition_notes", ""))}</p>{flaws}'),
        ("Material", f'<p>{e(p["material"])}</p>'),
        ("Shipping", f'<p>{e(site["shipping"]["text"])}</p>'),
        ("Returns", f'<p>30 days from delivery for a full refund. <a href="{home}#returns">How returns work</a>.</p>'),
    ], "pd", open_first=True)

    # More from the archive: same category first, then the rest; available before sold.
    others = sorted((o for o in products if o["handle"] != p["handle"]),
                    key=lambda o: (o["category"] != p["category"], not o["available"]))[:3]
    more = "\n".join(tag_card(o, site, root, " tag--grid js-reveal") for o in others)

    cats_html, first_desc = menu_cats(site, products, home)
    desc = f'{p["description"]} Size {p["size"]}, {p["era"]}. One of one, {money(p["price"], site)}.'
    if photos and image_size(ROOT / photos[0]):
        w, h = image_size(ROOT / photos[0])
        og = {"og_image": site["url"] + photos[0], "og_image_type": mime(photos[0]), "og_image_w": w, "og_image_h": h,
              "og_image_alt": f"{title} from Archive 88"}
    else:
        og = {"og_image": site["url"] + "assets/img/og-image.jpg", "og_image_type": "image/jpeg",
              "og_image_w": 1200, "og_image_h": 630,
              "og_image_alt": "The Archive 88 wordmark over a sunlit pine forest path."}
    extra = "\n".join([
        f'  <meta property="product:price:amount" content="{p["price"]:.2f}" />',
        f'  <meta property="product:price:currency" content="{site["currency"]}" />',
        f'  <meta property="product:availability" content="{"in stock" if p["available"] else "out of stock"}" />',
        '  <meta property="product:condition" content="used" />',
        f'  <meta property="product:retailer_item_id" content="A88-{p["number"]}" />',
    ])
    ctx = {
        "_site": site, "root": root, "home": home, "page": "product", "wm": WM, "year": dt.date.today().year,
        "title": e(f"{title} No. {p['number']} - Archive 88"), "description": e(desc), "canonical": url,
        "locale": site["locale"], "og_type": "product", **og, "extra_meta": extra,
        "jsonld": ld_json([org_ld(site), product_ld(p, site), {
            "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Archive", "item": site["url"] + "#archive"},
                {"@type": "ListItem", "position": 2, "name": cat, "item": f'{site["url"]}#shop-{p["category"]}'},
                {"@type": "ListItem", "position": 3, "name": title, "item": url}]}]),
        "menu_cats": cats_html, "menu_first_desc": e(first_desc),
        "handle": p["handle"], "number": e(p["number"]), "category": p["category"], "category_title": e(cat),
        "name": e(title), "title_lower": e(title.lower()), "price_fmt": money(p["price"], site),
        "size": e(p["size"]), "era": e(p["era"]), "condition": e(p["condition"]),
        "description": e(p["description"]), "gallery": "\n".join(slides), "pager": pager,
        "buy": buy, "details": details, "more": more,
    }
    body = "\n".join(fill(partial(n), ctx) for n in ["header", "product-main", "footer"])
    out = page(site, ctx, f'data-nav="paper" class="{"is-sold" if not p["available"] else ""}"',
               body, ["assets/js/product.js"])
    folder = ROOT / "products" / p["handle"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "index.html").write_text(out)


# ---------------------------------------------------------------- Shopify CSV

def build_shopify_csv(site, products):
    meta = {  # column title -> (namespace.key, value getter)
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
    }
    cols = ["Handle", "Title", "Body (HTML)", "Vendor", "Product Category", "Type", "Tags", "Published",
            "Option1 Name", "Option1 Value", "Variant SKU", "Variant Grams", "Variant Inventory Tracker",
            "Variant Inventory Qty", "Variant Inventory Policy", "Variant Fulfillment Service", "Variant Price",
            "Variant Compare At Price", "Variant Requires Shipping", "Variant Taxable", "Image Src",
            "Image Position", "Image Alt Text", "Gift Card", "SEO Title", "SEO Description", "Status", *meta]
    out = ROOT / "shopify"
    out.mkdir(exist_ok=True)
    with open(out / "products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for p in products:
            photos = photos_for(p["handle"])
            row = {c: "" for c in cols}
            row.update({
                "Handle": p["handle"], "Title": p["title"], "Body (HTML)": f'<p>{e(p["description"])}</p>',
                "Vendor": site["name"], "Type": cat_title(site, p["category"]),
                "Tags": ", ".join([cat_title(site, p["category"]), p["era"], f'size {p["size"]}']),
                "Published": "TRUE", "Option1 Name": "Title", "Option1 Value": "Default Title",
                "Variant SKU": f'A88-{p["number"]}', "Variant Inventory Tracker": "shopify",
                "Variant Inventory Qty": 1 if p["available"] else 0, "Variant Inventory Policy": "deny",
                "Variant Fulfillment Service": "manual", "Variant Price": f'{p["price"]:.2f}',
                "Variant Requires Shipping": "TRUE", "Variant Taxable": "TRUE", "Gift Card": "FALSE",
                "SEO Title": f'{p["title"]} No. {p["number"]} - Archive 88',
                "SEO Description": p["description"], "Status": "active",
                **{k: fn(p) for k, fn in meta.items()},
            })
            if photos:
                row.update({"Image Src": site["url"] + photos[0], "Image Position": 1,
                            "Image Alt Text": f'{p["title"]}, photo 1'})
            w.writerow(row)
            for i, ph in enumerate(photos[1:], 2):  # extra images: handle + image columns only
                extra = {c: "" for c in cols}
                extra.update({"Handle": p["handle"], "Image Src": site["url"] + ph, "Image Position": i,
                              "Image Alt Text": f'{p["title"]}, photo {i}'})
                w.writerow(extra)


# ---------------------------------------------------------------- main

def main():
    site = json.loads((ROOT / "data" / "site.json").read_text())
    products = json.loads((ROOT / "data" / "products.json").read_text())["products"]
    validate(site, products)
    drop = next_drop(site)

    # Rebuild product pages from scratch so removed products don't linger.
    shutil.rmtree(ROOT / "products", ignore_errors=True)
    build_home(site, products, drop)
    for p in products:
        build_product(site, products, p, drop)
    build_shopify_csv(site, products)

    today = dt.date.today().isoformat()
    urls = [site["url"]] + [f'{site["url"]}products/{p["handle"]}/' for p in products]
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site['url']}sitemap.xml\n")

    print(f"Built index.html + {len(products)} product pages, shopify/products.csv, sitemap.xml")
    for w in dict.fromkeys(warnings):
        print("  note:", w)


if __name__ == "__main__":
    main()
