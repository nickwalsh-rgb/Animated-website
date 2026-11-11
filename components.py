"""Storefront UI components.

Every piece of markup the site renders comes from a function in this file, so a component is defined once
and reused on every page that needs it (product card on PLP, PDP "pairs well with" and home; media frame in cards,
gallery and bag). Components take plain data (dicts from catalog.json, prepared by build.py) and return HTML strings.

Naming follows the CSS: a function `product_card()` renders `.card`, `media()` renders `.media`, and so on.
See docs/DESIGN-SYSTEM.md for the rules each component enforces.
"""
from __future__ import annotations

import json
from html import escape

# ---------------------------------------------------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------------------------------------------------


def e(value) -> str:
    """Escape text for HTML content and attribute values."""
    return escape(str(value), quote=True)


def money(amount, symbol: str = "£") -> str:
    amount = float(amount)
    return f"{symbol}{amount:,.0f}" if amount.is_integer() else f"{symbol}{amount:,.2f}"


def icon(name: str, label: str | None = None) -> str:
    """Inline SVG icon from the sprite (stroke icons, 24px grid, Lucide-style). Decorative unless labelled."""
    aria = f'role="img" aria-label="{e(label)}"' if label else 'aria-hidden="true" focusable="false"'
    return f'<svg class="icon" {aria}><use href="#i-{name}"/></svg>'


def json_script(element_id: str, data) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/json" id="{element_id}">{payload}</script>'


# ---------------------------------------------------------------------------------------------------------------------
# Media: the strict 4:5 frame. Every product image on the site goes through here.
# ---------------------------------------------------------------------------------------------------------------------

# Viewboxes for placeholder art. All are 4:5 so the frame never distorts.
VIEWBOX = {"front": "0 0 400 500", "back": "0 0 400 500", "detail": "110 60 180 225"}


def media(view: dict, alt: str, *, sizes: str = "(min-width: 1200px) 25vw, (min-width: 700px) 33vw, 50vw",
          eager: bool = False, cls: str = "") -> str:
    """One 4:5 image. `view` comes from build.py: either a photo {kind:'img', ...} or placeholder art
    {kind:'svg', sil, hex, angle}. The frame (.media) owns the ratio; content is cropped to fill it."""
    loading = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    if view["kind"] == "img":
        return (f'<picture class="media__item {cls}">'
                f'<source type="image/webp" srcset="{e(view["webp"])}" sizes="{e(sizes)}">'
                f'<img src="{e(view["src"])}" alt="{e(alt)}" width="1200" height="1500" {loading}></picture>')
    angle = view["angle"]
    if angle == "fabric":
        art = f'<rect width="400" height="500" fill="currentColor"/><rect width="400" height="500" fill="url(#weave)"/>'
        box = "0 0 400 500"
    else:
        sil = view["sil"] + ("-back" if angle == "back" else "")
        art = f'<use href="#s-{sil}" width="400" height="500"/>'
        box = VIEWBOX[angle]
    return (f'<svg class="media__item media__art {cls}" viewBox="{box}" preserveAspectRatio="xMidYMid slice" '
            f'role="img" aria-label="{e(alt)}" style="color:{e(view["hex"])}">{art}</svg>')


def frame(inner: str, cls: str = "") -> str:
    return f'<div class="media {cls}">{inner}</div>'


# ---------------------------------------------------------------------------------------------------------------------
# Price, badges, swatches
# ---------------------------------------------------------------------------------------------------------------------


def price(p: dict, sym: str) -> str:
    if p.get("compare_at") and p["compare_at"] > p["price"]:
        return (f'<p class="price price--sale"><span class="sr-only">Sale price </span>{money(p["price"], sym)} '
                f'<s><span class="sr-only">was </span>{money(p["compare_at"], sym)}</s></p>')
    return f'<p class="price">{money(p["price"], sym)}</p>'


def badge(text: str, tone: str = "neutral") -> str:
    return f'<span class="badge badge--{tone}">{e(text)}</span>'


def swatch_list(p: dict, *, limit: int = 5) -> str:
    """Colour swatches on a product card: buttons that change the card's colour in place (aria-pressed)."""
    items = []
    for i, c in enumerate(p["colours"][:limit]):
        items.append(
            f'<li><button type="button" class="swatch" style="--swatch:{e(c["hex"])}" '
            f'data-colour="{e(c["handle"])}" aria-pressed="{"true" if i == 0 else "false"}" '
            f'aria-label="{e(c["name"])}" title="{e(c["name"])}"></button></li>')
    more = len(p["colours"]) - limit
    extra = f'<li class="swatches__more">+{more}</li>' if more > 0 else ""
    return f'<ul class="swatches" aria-label="Colours">{"".join(items)}{extra}</ul>'


# ---------------------------------------------------------------------------------------------------------------------
# Product card (PLP, home, PDP recommendations)
# ---------------------------------------------------------------------------------------------------------------------


def colour_count(p: dict) -> str:
    n = len(p["colours"])
    return f"{n} colours" if n > 1 else p["colours"][0]["name"]


def product_card(p: dict, root: str, sym: str, *, eager: bool = False, quick_add: bool = True, cls: str = "") -> str:
    """The product card: image on a quiet ground, then name and price, colour and style number. Hover (fine pointers only) swaps the
    photo to the alternate angle instantly; the second image is already loaded in the same frame, so there's no
    flash. Quick add sits along the bottom of the image. Data attributes drive filtering, sorting and quick add."""
    first = p["colours"][0]
    v = p["media"][first["handle"]]
    url = f'{root}products/{p["handle"]}/'
    alt_front = f'{p["title"]} in {first["name"]}, front'
    alt_back = f'{p["title"]} in {first["name"]}, alternate view'
    badges = []
    if p["sold_out"]:
        badges.append(badge("Sold out", "muted"))
    elif p["low_stock"]:
        badges.append(badge("Selling fast", "signal"))
    elif p.get("new"):
        badges.append(badge("New"))
    elif p.get("best"):
        badges.append(badge("Bestseller"))
    filter_data = {
        "data-cat": p["category"],
        "data-price": p["price"],
        "data-rank": p["rank"],
        "data-new": "1" if p.get("new") else "0",
        "data-index": p["index"],
        # "colour:size size|colour:size" in-stock pairs. Lets size + colour filters combine correctly.
        "data-stock": "|".join(f'{c}:{" ".join(s)}' for c, s in p["in_stock"].items()),
        "data-families": " ".join(sorted({c["family"] for c in p["colours"]})),
    }
    attrs = " ".join(f'{k}="{e(val)}"' for k, val in filter_data.items())
    colours_json = e(json.dumps(p["card_colours"], ensure_ascii=False, separators=(",", ":")))
    qa = ""
    if quick_add and not p["sold_out"]:
        qa = (f'<div class="quick-add" data-quick-add>'
              f'<p class="quick-add__label">Quick add <span class="quick-add__colour">{e(first["name"])}</span></p>'
              f'<div class="quick-add__sizes"></div></div>')
    return f'''<article class="card{" is-soldout" if p["sold_out"] else ""}{" " + cls if cls else ""}" data-product="{e(p["handle"])}" data-title="{e(p["title"])}" data-style="{e(p["style"])}" data-sil="{e(p["silhouette"])}" data-url="{e(url)}" data-colours="{colours_json}" {attrs}>
  <div class="card__media">
    <a class="card__link" href="{e(url)}" tabindex="-1" aria-hidden="true">
      {frame(media(v[0], alt_front, eager=eager, cls="media__item--primary") + media(v[1], alt_back, cls="media__item--alt"), "media--hover")}
    </a>
    <div class="card__badges">{"".join(badges)}</div>
    {qa}
  </div>
  <div class="card__body">
    <h3 class="card__title"><a href="{e(url)}">{e(p["title"])}</a></h3>
    {price(p, sym)}
    <p class="card__colour" data-card-colour>{e(first["name"])}</p>
    <p class="card__no">No. {e(p["style"].split("-")[-1])}</p>
    {swatch_list(p)}
  </div>
</article>'''


def rail(rid: str, title: str, cards: str, *, link: tuple[str, str] | None = None, eyebrow: str = "") -> str:
    """A horizontal product rail: native scroll-snap (swipe, trackpad, keyboard) with previous/next buttons on
    fine pointers. Works without JS; store.js wires the buttons and their disabled state."""
    more = f'<a class="link-arrow" href="{e(link[1])}">{e(link[0])} {icon("arrow")}</a>' if link else ""
    eb = f'<p class="eyebrow">{e(eyebrow)}</p>' if eyebrow else ""
    return f'''<section class="rail" aria-labelledby="{rid}-title" data-rail>
  <div class="section-head">
    <div>{eb}<h2 class="section-title" id="{rid}-title">{e(title)}</h2></div>
    <div class="section-head__end">{more}
      <div class="rail__ctrl"><button type="button" class="icon-btn" data-rail-prev aria-label="Previous {e(title)}" disabled>{icon("chevron")}</button>
      <button type="button" class="icon-btn" data-rail-next aria-label="Next {e(title)}">{icon("chevron")}</button></div>
    </div>
  </div>
  <div class="rail__track" data-rail-track tabindex="0" role="region" aria-label="{e(title)}, scroll sideways">{cards}</div>
</section>'''


# ---------------------------------------------------------------------------------------------------------------------
# PLP: filter sidebar
# ---------------------------------------------------------------------------------------------------------------------


def filter_group(title: str, body: str, *, open_: bool = True, gid: str = "") -> str:
    return (f'<details class="filter" {"open" if open_ else ""} data-filter-group="{e(gid)}">'
            f'<summary class="filter__title">{e(title)}<span class="filter__count" data-group-count></span>{icon("chevron")}</summary>'
            f'<div class="filter__body">{body}</div></details>')


def category_links(categories: list, active: str | None, counts: dict, total: int, root: str) -> str:
    cur_all = 'aria-current="page"' if active is None else ""
    rows = [f'<li><a href="{root}shop/" {cur_all}>All clothing '
            f'<span class="count">{total}</span></a></li>']
    for c in categories:
        cur = 'aria-current="page"' if c["handle"] == active else ""
        rows.append(f'<li><a href="{root}shop/{c["handle"]}/" {cur}>{e(c["title"])} '
                    f'<span class="count">{counts.get(c["handle"], 0)}</span></a></li>')
    return f'<ul class="cat-list">{"".join(rows)}</ul>'


def size_chips(groups: list[tuple[str, list[str]]]) -> str:
    out = []
    for label, sizes in groups:
        chips = "".join(
            f'<label class="chip"><input type="checkbox" name="size" value="{e(s)}"><span>{e(s)}</span></label>'
            for s in sizes)
        heading = f'<p class="chip-group__label">{e(label)}</p>' if len(groups) > 1 else ""
        out.append(f'<div class="chip-group">{heading}<div class="chip-grid">{chips}</div></div>')
    return "".join(out)


FAMILY_HEX = {"black": "#1E2421", "blue": "#2E3E5C", "grey": "#7A7C7F", "neutral": "#C8BFAE", "white": "#F6F5F1",
              "brown": "#7A5638", "green": "#55603F", "red": "#8E4527"}


def colour_filters(families: list[str]) -> str:
    rows = "".join(
        f'<label class="colour-opt"><input type="checkbox" name="colour" value="{e(f)}">'
        f'<span class="colour-opt__dot" style="--swatch:{FAMILY_HEX.get(f, "#ccc")}"></span>{e(f.title())}</label>'
        for f in families)
    return f'<div class="colour-grid">{rows}</div>'


# ---------------------------------------------------------------------------------------------------------------------
# PDP: variant selectors, matrix, accordions, sticky add-to-cart
# ---------------------------------------------------------------------------------------------------------------------


def colour_selector(p: dict) -> str:
    opts = "".join(
        f'<label class="swatch-opt" title="{e(c["name"])}"><input type="radio" name="colour" value="{e(c["handle"])}" '
        f'{"checked" if i == 0 else ""}><span class="swatch swatch--lg" style="--swatch:{e(c["hex"])}"></span>'
        f'<span class="sr-only">{e(c["name"])}</span></label>'
        for i, c in enumerate(p["colours"]))
    return (f'<fieldset class="option" data-option="colour"><legend class="option__legend">Colour '
            f'<span class="option__value" data-colour-name>{e(p["colours"][0]["name"])}</span></legend>'
            f'<div class="swatch-row">{opts}</div></fieldset>')


def size_selector(p: dict, root: str) -> str:
    first = p["colours"][0]["handle"]
    opts = []
    for s in p["sizes"]:
        n = p["stock"][first].get(s, 0)
        opts.append(f'<label class="size-opt"><input type="radio" name="size" value="{e(s)}" {"disabled" if n == 0 else ""}>'
                    f'<span>{e(s)}</span></label>')
    unit = "Waist (in)" if p["sizes"][0].isdigit() else "Size"
    return (f'<fieldset class="option" data-option="size" aria-describedby="size-msg"><legend class="option__legend">{unit} '
            f'<span class="option__value" data-size-name></span></legend>'
            f'<a class="option__aside" href="#details-fit">Size &amp; fit</a>'
            f'<div class="size-grid">{"".join(opts)}</div>'
            f'<p class="option__msg" id="size-msg" data-size-msg aria-live="polite"></p></fieldset>')


def variant_matrix(p: dict, low: int) -> str:
    """Full size x colour availability table (inside the Availability accordion)."""
    head = "".join(f'<th scope="col">{e(s)}</th>' for s in p["sizes"])
    rows = []
    for c in p["colours"]:
        cells = []
        for s in p["sizes"]:
            n = p["stock"][c["handle"]].get(s, 0)
            state, text = ("out", "Sold out") if n == 0 else (("low", f"{n} left") if n <= low else ("in", "In stock"))
            cells.append(f'<td class="mx mx--{state}"><span class="mx__dot" aria-hidden="true"></span>'
                         f'<span class="sr-only">{text}</span></td>')
        rows.append(f'<tr><th scope="row"><span class="swatch swatch--sm" style="--swatch:{e(c["hex"])}" aria-hidden="true"></span>'
                    f'{e(c["name"])}</th>{"".join(cells)}</tr>')
    legend = ('<p class="matrix__legend"><span><i class="mx__dot mx--in"></i>In stock</span>'
              '<span><i class="mx__dot mx--low"></i>Few left</span><span><i class="mx__dot mx--out"></i>Sold out</span></p>')
    return (f'<div class="matrix-wrap"><table class="matrix"><caption class="sr-only">Availability by colour and size</caption>'
            f'<thead><tr><td></td>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>{legend}')


def accordion(title: str, body: str, aid: str, open_: bool = False) -> str:
    return (f'<details class="accordion" id="{e(aid)}" {"open" if open_ else ""}><summary>{e(title)}{icon("plus")}</summary>'
            f'<div class="accordion__body">{body}</div></details>')


def sticky_atc(p: dict, sym: str) -> str:
    """Phones/tablets: a bar pinned to the bottom while the main Add to bag button is off screen."""
    return f'''<div class="sticky-atc" data-sticky-atc hidden>
  <div class="sticky-atc__info">
    <p class="sticky-atc__title">{e(p["title"])}</p>
    <p class="sticky-atc__meta"><span data-sticky-variant>{e(p["colours"][0]["name"])}</span> · {money(p["price"], sym)}</p>
  </div>
  <button type="button" class="buy-btn buy-btn--bar" data-sticky-btn><span data-sticky-label>Select size</span></button>
</div>'''


def drawer(did: str, title: str, body: str, *, side: str = "right", footer: str = "", label_extra: str = "") -> str:
    """Generic slide-out panel (bag, menu, mobile filters, size sheet). Behaviour lives in store.js: focus is trapped,
    Esc / scrim / close button dismiss it, and focus returns to the opener."""
    foot = f'<div class="drawer__foot">{footer}</div>' if footer else ""
    return f'''<div class="drawer drawer--{side}" id="{e(did)}" role="dialog" aria-modal="true" aria-labelledby="{e(did)}-title" hidden>
  <div class="drawer__scrim" data-drawer-close></div>
  <div class="drawer__panel" tabindex="-1">
    <header class="drawer__head">
      <h2 class="drawer__title" id="{e(did)}-title">{e(title)}{label_extra}</h2>
      <button type="button" class="drawer__close" data-drawer-close>Close</button>
    </header>
    <div class="drawer__body" data-lenis-prevent>{body}</div>
    {foot}
  </div>
</div>'''


# ---------------------------------------------------------------------------------------------------------------------
# Forms (gift cards; reusable for checkout-style forms)
# ---------------------------------------------------------------------------------------------------------------------


def field(fid: str, label: str, *, type_: str = "text", autocomplete: str = "", required: bool = True,
          hint: str = "", maxlength: int = 0, inputmode: str = "", textarea: bool = False) -> str:
    """Labelled input with hint and an inline error slot. Labels are always visible; the error sits under the field
    and is tied to it with aria-describedby."""
    desc = f"{fid}-hint {fid}-err" if hint else f"{fid}-err"
    attrs = [f'id="{e(fid)}"', f'name="{e(fid)}"', f'aria-describedby="{desc}"']
    if required:
        attrs.append("required")
    if autocomplete:
        attrs.append(f'autocomplete="{e(autocomplete)}"')
    if maxlength:
        attrs.append(f'maxlength="{maxlength}"')
    if inputmode:
        attrs.append(f'inputmode="{e(inputmode)}"')
    opt = "" if required else ' <span class="field__opt">(optional)</span>'
    control = (f'<textarea {" ".join(attrs)} rows="3"></textarea>' if textarea
               else f'<input type="{e(type_)}" {" ".join(attrs)}>')
    hint_html = f'<p class="field__hint" id="{fid}-hint">{e(hint)}</p>' if hint else ""
    return (f'<div class="field"><label class="field__label" for="{e(fid)}">{e(label)}{opt}</label>{control}'
            f'{hint_html}<p class="field__err" id="{fid}-err" aria-live="polite"></p></div>')
