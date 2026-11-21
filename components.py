"""Archive 88 storefront components.

Every piece of markup comes from a function here, so a component is defined once and reused on every page
(product card on listings, rails, search and the bag; media in cards, gallery and the bag). Components take plain
data prepared by build.py and return HTML strings. CSS class names match the function names (product_card() renders
.card, full_width_teaser() renders .teaser--full, and so on). See docs/DESIGN-SYSTEM.md.
"""
from __future__ import annotations

import json
import re
from html import escape

# ---------------------------------------------------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------------------------------------------------


def e(value) -> str:
    """Escape text for HTML content and attribute values."""
    return escape(str(value), quote=True)


def money(amount, symbol: str = "£") -> str:
    """Prices always show pence, as the original does: £110.00."""
    return f"{symbol}{float(amount):,.2f}"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().replace("&", "and")).strip("-")


def icon(name: str, label: str | None = None, cls: str = "") -> str:
    """Inline SVG icon from the sprite (1.5px stroke, 24px grid). Decorative unless labelled."""
    aria = f'role="img" aria-label="{e(label)}"' if label else 'aria-hidden="true" focusable="false"'
    return f'<svg class="icon {cls}" {aria}><use href="#i-{name}"/></svg>'


def json_script(element_id: str, data) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/json" id="{element_id}">{payload}</script>'


def arrow_link(label: str, href: str, cls: str = "") -> str:
    return f'<a class="arrow-link {cls}" href="{e(href)}">{e(label)}{icon("arrow")}</a>'


# ---------------------------------------------------------------------------------------------------------------------
# Media. Product frames are 2:3 portrait on the mist ground; campaign tiles are 3:4; heroes are 16:9 / 2:3.
# ---------------------------------------------------------------------------------------------------------------------

VIEWBOX = {"front": "0 0 400 500", "back": "0 0 400 500", "detail": "110 60 180 270"}
ANGLE_LABEL = {"front": "front", "back": "back", "detail": "detail", "fabric": "fabric close-up"}


def media(view: dict, alt: str, root: str, *, sizes: str = "(min-width: 1024px) 25vw, 50vw", eager: bool = False) -> str:
    """One product image. `view` is a photo {kind:'img', src, webp:[(path, width)]} or placeholder art
    {kind:'svg', sil, hex, angle}. The frame owns the ratio; content fills it."""
    loading = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    if view["kind"] == "img":
        srcset = ", ".join(f"{root}{p} {w}w" for p, w in view["webp"])
        source = f'<source type="image/webp" srcset="{e(srcset)}" sizes="{e(sizes)}">' if srcset else ""
        return (f'<picture class="art">{source}<img src="{e(root + view["src"])}" alt="{e(alt)}" '
                f'width="1200" height="1800" {loading}></picture>')
    angle = view["angle"]
    if angle == "fabric":
        inner = '<rect width="400" height="600" fill="currentColor"/><rect width="400" height="600" fill="url(#weave)"/>'
        box, fit = "0 0 400 600", "slice"
    else:
        sil = view["sil"] + ("-back" if angle == "back" else "")
        inner = f'<use href="#s-{sil}" width="400" height="500"/>'
        box, fit = VIEWBOX[angle], ("slice" if angle == "detail" else "meet")
    return (f'<svg class="art art--svg" viewBox="{box}" preserveAspectRatio="xMidYMid {fit}" role="img" '
            f'aria-label="{e(alt)}" style="color:{e(view["hex"])}">{inner}</svg>')


def alt_for(title: str, colour: str, angle: str) -> str:
    return f"{title} in {colour}, {ANGLE_LABEL.get(angle, 'view')}"


# ---------------------------------------------------------------------------------------------------------------------
# Product card: image on mist, then three lines of text. No borders, shadows or add-to-bag button.
# ---------------------------------------------------------------------------------------------------------------------


def product_card(cw: dict, root: str, sym: str, *, hl: int = 2, eager: bool = False) -> str:
    """cw is one colourway (a style in one colour) from build.py. Each colourway is its own card and its own URL,
    as on the original. Desktop: hover or focus swaps to the second image. Touch: swipe between the two."""
    p, c = cw["p"], cw["c"]
    views = cw["views"][:2]
    frames = "".join(
        f'<div class="card__frame">{media(v, alt_for(p["title"], c["name"], v.get("angle", "front")), root, eager=eager and i == 0)}</div>'
        for i, v in enumerate(views))
    if cw["sold_out"]:
        badge = '<span class="badge badge--muted">Sold out</span>'
    elif p.get("new"):
        badge = '<span class="badge">New</span>'
    else:
        badge = ""
    data = (f'data-card data-key="{e(cw["key"])}" data-new="{1 if p.get("new") else 0}" data-rank="{cw["rank"]}" '
            f'data-price="{p["price"]}" data-colour="{e(c["family"])}" data-sizes="{e(",".join(cw["in_stock"]))}" '
            f'data-fit="{e(cw["fit"])}" data-fabric="{e(cw["fabric"])}" data-cat="{e(p["category"])}"')
    return f'''<article class="card" {data}>
  <a class="card__link" href="{root}{e(cw["url"])}">
    <div class="card__media">{frames}</div>
    <div class="card__text">
      <div class="card__head"><h{hl} class="card__title">{e(p["title"])}</h{hl}>{badge}</div>
      <p class="card__meta"><span class="sr-only">Colour: </span>{e(c["name"])}</p>
      <p class="card__meta"><span class="sr-only">Price: </span>{money(p["price"], sym)}</p>
    </div>
  </a>
  <button type="button" class="wish" data-wish="{e(cw["key"])}" aria-pressed="false" aria-label="Add to wishlist: {e(p["title"])}, {e(c["name"])}">{icon("heart")}</button>
</article>'''


# ---------------------------------------------------------------------------------------------------------------------
# Homepage modules (the page builder): fullWidthTeaser, productsListing, teaserGrid
# ---------------------------------------------------------------------------------------------------------------------


def teaser_links(links: list, root: str) -> str:
    items = "".join(f'<a class="arrow-link arrow-link--light" href="{root}{e(href)}">{e(label)}{icon("arrow")}</a>'
                    for label, href in links)
    return f'<div class="teaser__links">{items}</div>'


def full_width_teaser(m: dict, root: str, *, first: bool, pos: int) -> str:
    """Hero: two art-directed sources (16:9 desktop, 2:3 mobile), eased gradient, title and links bottom-centre.
    The whole tile is clickable through an invisible anchor that keyboard users skip (tabindex=-1)."""
    href = root + m["links"][0][1]
    prio = 'fetchpriority="high"' if first else 'loading="lazy" decoding="async"'
    if m.get("video"):
        v = m["video"]
        visual = f'''<video class="teaser__media" autoplay muted loop playsinline preload="metadata" aria-hidden="true"
      poster="{root}{e(m["imageDesktop"])}" data-hero-video data-src-desktop="{root}{e(v["desktop"])}" data-src-mobile="{root}{e(v["mobile"])}"
      data-poster-mobile="{root}{e(m["imageMobile"])}"></video>
    <picture class="teaser__poster"><source media="(min-width: 1024px)" srcset="{root}{e(m["imageDesktop"])}">
      <img src="{root}{e(m["imageMobile"])}" alt="{e(m["alt"])}" {prio}></picture>
    <button type="button" class="playpause" data-playpause aria-label="Pause the film">{icon("pause", cls="pp-pause")}{icon("play", cls="pp-play")}</button>'''
    else:
        visual = f'''<picture class="teaser__poster"><source media="(min-width: 1024px)" srcset="{root}{e(m["imageDesktop"])}">
      <img src="{root}{e(m["imageMobile"])}" alt="{e(m["alt"])}" {prio}></picture>'''
    return f'''<article class="teaser teaser--full" data-promo='{e(json.dumps({"promotionName": m["title"], "modulePosition": pos}))}'>
  {visual}
  <a class="teaser__cover" href="{e(href)}" tabindex="-1" aria-hidden="true"></a>
  <div class="teaser__text">
    <h2 class="teaser__title">{e(m["title"])}</h2>
    {teaser_links(m["links"], root)}
  </div>
</article>'''


def products_listing(heading: str, see_all: str, cards: str) -> str:
    """Product rail: 20px label and See all, then a 4-column grid (1024px+) or a swipe row with a peeking card."""
    return f'''<section class="rail" aria-label="{e(heading)}">
  <div class="rail__head"><h2 class="rail__title">{e(heading)}</h2>{arrow_link("See all", see_all)}</div>
  <div class="rail__track">{cards}</div>
</section>'''


def teaser_grid(teasers: list, root: str, pos: int) -> str:
    tiles = []
    for t in teasers:
        tiles.append(f'''<article class="teaser teaser--tile" data-promo='{e(json.dumps({"promotionName": t["title"], "modulePosition": pos}))}'>
    <img class="teaser__media" src="{root}{e(t["image"])}" alt="{e(t["alt"])}" loading="lazy" decoding="async" width="720" height="900">
    <a class="teaser__cover" href="{root}{e(t["links"][0][1])}" tabindex="-1" aria-hidden="true"></a>
    <div class="teaser__text"><h2 class="teaser__title">{e(t["title"])}</h2>{teaser_links(t["links"], root)}</div>
  </article>''')
    return f'<section class="tgrid tgrid--{len(teasers)}" aria-label="Featured">{"".join(tiles)}</section>'


def carousel(cid: str, heading: str, cards: str) -> str:
    """Full-width carousel with round arrow buttons (PDP recommendations, bag)."""
    return f'''<section class="carousel" aria-labelledby="{cid}-h" data-carousel>
  <h2 class="carousel__title" id="{cid}-h">{e(heading)}</h2>
  <div class="carousel__viewport">
    <button type="button" class="round-btn carousel__prev" data-carousel-prev aria-label="Previous products">{icon("chev-l")}</button>
    <div class="carousel__track" data-carousel-track>{cards}</div>
    <button type="button" class="round-btn carousel__next" data-carousel-next aria-label="Next products">{icon("chev-r")}</button>
  </div>
</section>'''


# ---------------------------------------------------------------------------------------------------------------------
# Listing pieces
# ---------------------------------------------------------------------------------------------------------------------


def subnav(links: list[tuple[str, str, bool]]) -> str:
    cur_attr = ' aria-current="page"'
    items = "".join(f'<li><a href="{e(h)}"{cur_attr if cur else ""}>{e(t)}</a></li>' for t, h, cur in links)
    return f'<nav class="subnav" aria-label="Categories"><ul>{items}</ul></nav>'


def filter_pill(cls: str) -> str:
    return (f'<button type="button" class="pill {cls}" data-filter-open aria-haspopup="dialog" aria-controls="filters">'
            f'{icon("filter")}<span data-filter-label>Filter</span></button>')


def filter_panel() -> str:
    sorts = (("new", "New in"), ("relevance", "Relevance"), ("price-asc", "Price (lowest)"), ("price-desc", "Price (highest)"))
    radios = "".join(f'<label class="sortopt"><input type="radio" name="sort" value="{v}"><span>{t}</span></label>' for v, t in sorts)
    return f'''<dialog class="fpanel" id="filters" aria-labelledby="filters-title" data-filter-panel>
  <h2 class="sr-only" id="filters-title">Filter and sort products</h2>
  <div class="fpanel__body">
    <fieldset class="fpanel__sort"><legend class="fpanel__label">Sort by</legend>{radios}</fieldset>
    <div data-facets></div>
    <button type="button" class="text-btn fpanel__clear" data-filter-clear>Clear all</button>
  </div>
  <div class="fpanel__foot">
    <button type="button" class="btn btn--outline" data-filter-cancel>Cancel</button>
    <button type="button" class="btn" data-filter-apply><span>Show <span data-filter-total>0</span> items</span></button>
  </div>
</dialog>'''


def pagination() -> str:
    return '''<nav class="pager" aria-label="Pages" data-pager hidden>
  <a class="pager__link" data-pager-prev href="?page=1">Previous</a>
  <p class="pager__count"><span data-pager-current>1</span> of <span data-pager-total>1</span> pages</p>
  <a class="pager__link" data-pager-next href="?page=2">Next</a>
</nav>'''


# ---------------------------------------------------------------------------------------------------------------------
# PDP pieces
# ---------------------------------------------------------------------------------------------------------------------


def accordion(title: str, body: str, open_: bool = False) -> str:
    return (f'<details class="acc"{" open" if open_ else ""}><summary class="acc__sum">{e(title)}'
            f'{icon("plus", cls="acc__plus")}{icon("minus", cls="acc__minus")}</summary><div class="acc__body">{body}</div></details>')


def field(fid: str, label: str, *, type_: str = "text", autocomplete: str = "", required: bool = True,
          hint: str = "", maxlength: int | None = None, textarea: bool = False, inputmode: str = "") -> str:
    req = " required" if required else ""
    hint_html = f'<p class="field__hint" id="{fid}-hint">{e(hint)}</p>' if hint else ""
    describedby = f'{fid}-err' + (f" {fid}-hint" if hint else "")
    attrs = f'id="{fid}" name="{fid}" aria-describedby="{describedby}"{req}'
    if autocomplete:
        attrs += f' autocomplete="{autocomplete}"'
    if maxlength:
        attrs += f' maxlength="{maxlength}"'
    if inputmode:
        attrs += f' inputmode="{inputmode}"'
    control = f'<textarea {attrs} rows="3"></textarea>' if textarea else f'<input type="{type_}" {attrs}>'
    opt = "" if required else ' <span class="field__opt">(optional)</span>'
    return (f'<div class="field"><label class="field__label" for="{fid}">{e(label)}{opt}</label>{control}{hint_html}'
            f'<p class="field__err" id="{fid}-err" aria-live="polite"></p></div>')
