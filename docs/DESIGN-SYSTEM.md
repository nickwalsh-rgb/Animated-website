# The Easy Life: brand and design system

The Easy Life is a **permanent collection** of 100 styles (1,830 size × colour
variants in the sample data). The identity is quiet and neutral: soft greys and off-whites, charcoal ink, one slate
accent, a relaxed grotesque for display, soft corners, and one idea, **the sunlit wall that keeps your time**. The layout is clean
retail built for range and conversion: announcement bar, mega-menu, search, product rails, plain product cards,
category tiles and a calm footer.

The site is designed to look finished **without photography**: products are drawn art on quiet grounds, and the
homepage scene is made in code. Product photos drop into the same frames when they exist (see section 4).

Design read (`design-taste-frontend` skill): brand overhaul of a premium clothing store for design-conscious
shoppers; variance 6, motion 5, density 3. Structure and UX rules come from the earlier `ui-ux-pro-max` pass.

---

## 1. Brand

The identity was designed in Figma (file **The Easy Life: Identity**,
https://www.figma.com/design/7l0thjO9EW3eoVVXGwTqln) and brought into the site as outlines and images. Brand
assets live in one place each: the wordmark and the leaf mark as symbols in `src/brand-defs.html` (`logo()`,
`emblem()` and `wordmark()` in build.py draw them); standalone files in `assets/img/` (`logo.svg`,
`logo-stacked.svg`, `wordmark.svg`, `mark.svg`, `seal.svg`, `favicon.svg`); the fig shadow layers in
`assets/img/shade-fig-near.webp` and `shade-fig-far.webp`; fonts in `assets/fonts/`; social links and business
details in `data/store.json`.

| | |
| --- | --- |
| Positioning | Easy-wearing clothes in natural fibres, kept in the range season after season. |
| Tagline | Clothes for taking your time |
| Voice | Plain, specific, unhurried. Say what it is made of and how it fits. |
| Signature elements | See below |

### The idea

*Take your time* is taken literally. The homepage is a plaster wall with a window's patch of sun on it, and that
light follows the visitor's own clock: it leans one way in the morning, stands upright at midday, leans the other
way and warms by evening, and dims to a cool trace after dark. Everything distinctive hangs off that:

- **The fig.** The plant on the wall is a fig: its leaf was the first thing anyone wore. The shadow is a real fig
  branch in two layers, a soft far one and a crisp near one, which drift against each other for depth.
- **The mark.** A fig leaf traced from that same shadow, always drawn with the shadow it casts. On the homepage the
  mark's shadow leans with the light (`--mark-x`). It is the favicon and app icon, and sits in the seal.
- **The wordmark.** Newsreader Italic, converted to outlines and altered: the dot has left the "i" and rests on the
  baseline at the end of the name. That resting dot is also the sun on the homepage sundial.
- **The seal.** The mark ringed by the name and the tagline, for the sewn-in label, tissue and stickers.
- **Painted lettering.** The hero line and the story are set under the light, so shadows pass over the letters as
  if they were painted on the wall.
- **The sewn-in label.** The collection's promises are set as a garment label (made of, cut, kept, care) that hangs
  on the wall in the story section.
- **Style numbers.** Every card carries its style number (No. 042), the way a permanent collection would be kept.

### Colour

| Token | Hex | Use |
| --- | --- | --- |
| Ink | `#1C1D1F` | Text, primary buttons (Add to bag, Checkout, Subscribe), announcement bar, footer, selected chips |
| White | `#F8F8F6` | Page background |
| Paper | `#F1F1EE` | Newsletter band, type on ink |
| Mist | `#EAEAE7` | Behind every product image |
| Graphite | `#3A3D42` | Hover on ink, *in stock* and *added* states, the posted gift card |
| Slate | `#41566E` (deep `#33455A`) | **Signals only**: bag count, *Selling fast*, low-stock dots, delivery meter, sale price, focus ring, search highlight |
| Red | `#8F2F2A` | Form errors only |
| Wall | `#FBFBF9` to `#E4E4E0` | The sunlit wall: lit plaster fading to half shade, with a fine grain |
| Tile grounds | `--tile-1` to `--tile-6` | Six close neutral greys behind the category tiles, so the grid has rhythm without colour |

Primary actions are solid ink, as shoppers expect from retail; slate is kept for signals so it always means
*look here*. Text contrast: muted text 5.2:1+ on white and paper, slate 7:1 on white, paper on ink 15:1.

### Typography

| Role | Face | Where |
| --- | --- | --- |
| Logo | **Newsreader Italic**, as outlines | The wordmark only |
| Display | **Bricolage Grotesque** 300 to 400 (variable, with optical sizing), sentence case, tight tracking | The hero line, the story, page, section, tile and product titles |
| UI + body | **Archivo** 400 / 500 | Navigation, buttons, cards, prices, forms, body copy |

Sentence case throughout (no tracked uppercase): quieter, faster to read in a dense grid. Type scale is in tokens
(`--fs-xs` 12 to `--fs-hero`, fluid). Self-hosted with size-matched fallbacks, so text barely shifts when fonts load.
The wordmark is outlines, so it never waits for a font.

### Shape

Soft corners everywhere, by one rule: buttons, chips and badges are pills; inputs and other controls use
`--radius` (10px); image frames and tiles use `--radius-media` (14px).

### Product card
Image on the mist ground (strict 4:5) with one small badge at most (*Selling fast*, *New*, *Bestseller* or *Sold out*),
then name and price on one line, the colour name, and swatches. Desktop hover swaps the photo to the alternate angle
instantly and reveals quick-add sizes along the bottom of the image. The whole card is one link target; swatches and
quick add sit above it.

---

## 2. Token architecture (`assets/css/tokens.css`)

1. **Primitive**: the brand palette, fonts, type scale, motion speeds.
2. **Semantic**: what a value is for: `--color-text`, `--color-primary` (ink), `--color-signal` (slate), `--color-media`, `--color-on-dark`, `--color-error`, `--color-focus`.
3. **Component**: values a component owns: `--media-ratio: 4 / 5`, `--bar-h`, `--nav-h`, `--sidebar-w`, `--drawer-w`, `--radius`, `--radius-media`, `--tap: 44px`.

Components read layers 2 and 3 only. To restyle, change a semantic token; no component CSS changes.

Motion: `--t-press` 80ms, `--t-fast` 200ms (hovers), `--t-base` 350ms (drawers, menus), `--t-slow` 700ms (section
reveals), plus `--t-instant` 0ms for the card angle swap. `prefers-reduced-motion` removes movement but keeps every
state change.

---

## 3. Components

Markup is generated by `components.py` / `build.py` (one function per component); styles live in
`assets/css/store.css` under the same name; behaviour lives in `assets/js/`.

| Component | Python | CSS | JS | Notes |
| --- | --- | --- | --- | --- |
| Announcement bar | `announce_bar()` | `.announce` | `store.js` | Messages from `store.json` → `announcements`. Rotates every 6s; pauses on hover/focus; prev/next and a pause button; starts paused with reduced motion. |
| Header | `header()` | `.nav` | `store.js` | Wordmark, Shop (mega-menu), New in, Outerwear, Knitwear, Gift cards; Search and Bag. Phones: search, bag and menu icons. |
| Mega-menu | `mega()` | `.mega` | `store.js` | Desktop. Featured, categories with counts, shop by size (links pre-filter the grid), two editorial tiles. Click or hover; Esc returns focus to Shop. |
| Search | `search_drawer()`, `search_index()` | `.search`, `.search-hit` | `store.js` | Panel from the top. `search.json` (~20 KB) loads on first open; every word must match name, category, colour or cloth; name matches rank first; Enter opens the top hit. |
| Menu | `menu_drawer()` | `.menu__*` | `store.js` (`Drawer`) | Phones/tablets: every category with counts, sizes, help links. |
| Rail | `rail()` | `.rail` | `store.js` | Sideways product row: native scroll-snap (swipe, trackpad, keyboard) plus previous/next buttons on desktop. New in, Bestsellers, *You may also like*. |
| Media frame | `media()`, `frame()` | `.media` | – | The only way an image is drawn. Strict 4:5. |
| Product card | `product_card()` | `.card` | `store.js` | Used on PLP, rails and search. |
| Swatches | `swatch_list()` | `.swatch` | `store.js` | Recolour the card in place and update the colour name; link keeps `?colour=`. |
| Quick add | inside `product_card()` | `.quick-add` | `store.js` | Fine pointers only. Sizes for the shown colour; sold-out struck through. |
| Badge | `badge()` | `.badge` | – | One per card, in priority order. |
| Category pills | inline in `plp()` | `.pills` | – | Phones/tablets (where the sidebar is a drawer): sideways row of categories. |
| Filter group | `filter_group()` | `.filter` | `plp.js` | `<details>`; shows a count of active choices. |
| Size chips / colour options | `size_chips()`, `colour_filters()` | `.chip`, `.colour-opt` | `plp.js` | Real checkboxes, 44px targets. |
| Drawer | `drawer()` | `.drawer--right/left/top/bottom` | `store.js` (`Drawer`) | One controller for bag, menu, search, mobile filters, size sheet. |
| Colour / size selectors | `colour_selector()`, `size_selector()` | `.option`, `.size-opt` | `pdp.js` | Real radios. Sold-out sizes disabled and struck; low stock gets a slate dot. |
| Variant matrix | `variant_matrix()` | `.matrix` | – | Full size × colour availability table (PDP, *Availability*). |
| Add to bag | inline in `pdp()` | `.buy-btn` | `pdp.js` | Full-width ink pill. |
| Sticky Add to bag | `sticky_atc()` | `.sticky-atc` | `pdp.js` | Bar pinned to the bottom, phones/tablets only. |
| Accordion | `accordion()` | `.accordion` | – | Native `<details>`. |
| Promises, sign-up, footer | `promises()`, `signup()`, `footer()` | `.promises`, `.signup`, `.footer` | `store.js` | Service bar, newsletter (inline validation; hook `window.A88S.subscribe(email)` to your email provider), four link columns, legal row, A88 mark. |
| Form field | `field()` | `.field` | `gift.js` | Visible label, hint, error under the field. |

### Scaling the catalogue
- Data shape: one style per entry; `stock[colour][size]` **is** the variant matrix. SKUs are derived
  (`TEL-012-OLIVE-M`). Add styles, colours or sizes without touching code.
- `build.py` validates every style (required fields, unique handle/style, known category, a stock cell for every
  size × colour) and stops with a clear message if anything is wrong.
- Listing pages are server-rendered (complete without JS, crawlable) and enhanced client-side. Filtering and sorting
  work on in-memory card data, so they are instant; "Load more" pages through 24 at a time (`page_size` in
  `store.json`).
- Past roughly 500 styles per listing, move cards to a JSON index rendered client-side, or paginate listings into
  `/shop/<category>/page/2/` at build time. The card component and filter logic don't change.
- Shopify: add `shopify_domain` in `store.json` and `shopify_variant_ids` (`"colour/size": id`) per style; the
  bag's Checkout button then hands off to `https://<shop>/cart/<id>:<qty>,…`.

---

## 4. UX rules (enforced)

**Strict 4:5 photography.** `.media` owns `aspect-ratio: 4 / 5`; content is `object-fit: cover`. The build also
centre-crops every uploaded photo to exactly 4:5 and writes 480 / 960 / 1600px WebP + a 1200px JPEG, so a wrong
upload can't distort the grid or shift layout. Until photos exist, placeholder art in the same frame is shown.

**Instant alternate angle on hover.** Both angles are in the frame from the start; on hover (or keyboard focus) the
second shows with a 0ms transition. Only on `(hover: hover) and (pointer: fine)`: touch devices never get stuck
hover states, and they reach every angle on the PDP.

**Slide-out bag drawer.** Every add opens the drawer (right side) with the new line highlighted. Focus is trapped,
Esc / scrim / close dismiss it, focus returns to the button that opened it, and the page behind is `inert`.
The drawer shows a free-delivery meter, quantity steppers capped at real stock, remove, subtotal and Checkout.

**PLP sticky sidebar.** From 1000px, the filter column is sticky with its own scroll; the toolbar (count, active
filter chips, sort) is sticky under the header. Below 1000px, the same form becomes a left drawer with a live
*Show N styles* button, and category pills sit under the title. Size and colour filters combine per variant (a style
matches *M + green* only if it has a green colourway in stock in M), and matching cards switch to that colourway.
Filters and sort live in the URL, so the mega-menu's size links open a pre-filtered grid.

**PDP variant matrix.** Choosing a colour updates the gallery, which sizes are available, low-stock dots and the
stock message. If the chosen size is sold out in the new colour, it is cleared with a message saying so. Submitting
without a size shows the error next to the sizes and moves focus there. `?colour=&size=` deep-links a variant.
Desktop: photos in a two-column grid beside a sticky buy column. Phones: a swipeable row with a counter.

**Mobile sticky Add to bag.** Whenever the main button is off screen, a bar pins to the bottom (safe-area aware)
with the product, chosen colour/size and price. With no size chosen it reads *Select size* and opens a bottom sheet
of sizes; picking one adds to the bag. Page padding grows so the bar never covers the footer.

**Accessibility.** AA contrast on every text/background pair; visible focus ring on everything (light on dark
sections); real form controls for every option; 44px minimum targets; live regions announce result counts, search
results, stock and bag changes; skip link; auto-rotating content can be paused; `prefers-reduced-motion` respected.

---

## 4b. Header and homepage

**Header follows the section under it (site-wide).** A section can carry `data-nav="light"` or `data-nav="dark"`,
and `data-nav-clear` to ask for a see-through header. Over the sunlit wall the header is see-through with dark
type, so the wall runs behind it; over a dark section that asks for it the type turns light; over the footer it
is a solid ink bar. Everywhere else it is a solid light bar. `store.js` checks which section is under the middle
of the header as you scroll (measured where the header really is, below the announcement bar at the top). Opening
the mega-menu always brings the solid light bar back.

**The sunlit wall** (`wall()` in build.py, `.wall` in store.css, `home.js`). The section's
background is the wall fully lit, with a fine grain. Two layers sit above it, each the same oversized square wearing
the same six-pane window mask: one puts everything outside the panes in shade, the other holds what happens inside
them (the fig shadow in two layers and a cloud that dims the sun for a few seconds each minute). Each fig layer
hangs from its top right corner and only rotates a degree or so at its own pace, so the browser animates it on the
compositor: no video, no canvas, about 570 KB of images. The shade outside the panes and the leaf shadows are kept
at the same density, as they would be on a real wall. Headlines sit under these layers.

`home.js` reads the visitor's clock once a minute and sets `--sun-skew`, `--sun-shift`, `--sun-len`, `--sun-lit`,
`--sun-shade`, `--sun-leaf` and `--sun-dim` from the `DAY` table (one row per key hour). Add `?light=7.5` to the
homepage address to see any hour from 0 to 24. Without JavaScript the wall shows mid-afternoon. The shadows pause
off screen, have a Pause/Play button, and hold still with reduced motion. To restage the scene: `--fx`/`--fy` on
`.wall` move where the light lands; the values on `.wall__fig--far` and `--near` set each layer's position, size,
sway, speed and strength.

**Homepage, top to bottom.**

| Section | Pattern |
| --- | --- |
| Hero | The sunlit wall under a see-through header. One line across the full width (*Take your time.*), painted under the light. Beneath it one row: a short sentence, two underlined links, and the sundial (the hour, what the light is doing, and the pause button). |
| New in | Product rail, *See all* link. |
| Shop by category | An index: the six categories in display type with their counts, beside one plate that shows the leading styles of whichever name is pointed at or focused. On phones each entry is its own tile. |
| Bestsellers | Product rail (top-ranked styles that aren't new). |
| Story | The wall again, with the promise in three painted lines, a link to About, and the sewn-in label hanging in the light. |
| Brand copy | Two short paragraphs (also useful for search engines). |
| Promises, sign-up, footer | Shared by every page. The footer closes on the wordmark at full width. |

Motion is calm and each piece has a job: the light tells the time, the shadows and the passing cloud make it feel
like weather, the hero rises in once on load, sections fade up 16px once as they arrive, the index plate answers the
pointer. No loader, no pinned or scroll-driven sections, no animation libraries. With reduced motion or without JS
everything is simply visible.

The site is light only. A dark theme is not built; the tokens are layered so one could be added by redefining
the semantic layer.

## 4c. Gift cards

`/gift-cards/` (`gift()` in build.py, `assets/js/gift.js`, settings in `store.json` → `gift_cards`): amount chips,
then two buttons, **Email a gift card** and **Post a gift card**. Each opens its own form (email: name, email, your
name, message, send date; post: name, address, UK postcode, your name, message). A live card preview shows the amount
and recipient. Fields validate when you leave them and on submit, with the error under the field. The card goes in
the bag as a normal line with the recipient details attached, and does not count toward free delivery.
`?send=email|post` deep-links a method.

Before launch: confirm gift card terms (validity, refunds) and set up Shopify gift card products; add their
variant ids to `gift_cards.shopify_variant_ids` (`"email/100": id`). Recipient details travel with the bag line
but a plain cart link can't pass them to Shopify; that needs Shopify's gift card recipient fields or an app.

## 5. Pre-delivery checklist (ui-ux-pro-max)

- [x] No emoji as icons (SVG sprite)
- [x] Pointer cursor and hover feedback on every clickable element
- [x] Hover/press transitions 80–350ms on the motion tokens
- [x] Text contrast ≥ 4.5:1
- [x] Visible focus for keyboard navigation; mega-menu reachable and closable by keyboard
- [x] `prefers-reduced-motion` respected (wall shadows, reveals, announcement rotation)
- [x] Responsive at 375 / 768 / 1024 / 1440, no horizontal scroll (checked at 390px)
- [x] Media space reserved (aspect-ratio), font fallbacks metric-matched (no CLS)
