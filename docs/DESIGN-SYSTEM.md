# Archive 88: brand and design system (2026 identity)

Archive 88 sells **curated pieces, made in limited runs** (est. 1988). This document covers the identity that came
out of the 2026 rebrand and the shop built on it. The identity was drawn from the original Figma logo (slab
ARCHIVE, a pine and mountain roundel, 88) and lives in the same Figma file on the page **Rebrand 2026**: nine
boards, six logo components, colour variables and text styles with the same names as the tokens below.

Design read: an online shop for an outdoor heritage label, in a catalogue-like "archive" language. Layout variance 7,
motion 7, density 4. Native CSS and JavaScript only, no frameworks or animation libraries.

---

## 1. Brand

Brand assets live in one place each: logo files in `assets/brand/` and the inline logo parts in
`src/brand-defs.html` (both written by `tools/make_brand.py`), fonts in `assets/fonts/`, the share image and app
icons from `tools/make_icons.js`, social links and business details in `data/store.json`.

| | |
| --- | --- |
| Positioning | A small collection of outdoor clothing, chosen piece by piece and made in limited runs. |
| Tagline | Curated pieces, made in limited runs. Est. 1988. (the two lines from the original logo) |
| Voice | Plain, specific, unhurried. Say what it is made of and how it fits. No filler words. |
| Signature elements | The roundel (it turns once when you hover the logo, and sits in the turning seal on the hero), slab headlines, style numbers in mono (`No. 042`), the graded forest film, one blaze accent, the full-width logo that closes every page |

### Logo

| Mark | File | Use |
| --- | --- | --- |
| Lockup | `assets/brand/lockup.svg` | Primary. ARCHIVE, the roundel, 88 on one line. 120px wide or more. |
| Wordmark | `wordmark.svg` | Letters only, for sizes under 120px. |
| Stacked | `stacked.svg` | Roundel over name over descriptor. Labels, swing tags, packaging. |
| Seal | `seal.svg`, `seal-ring.svg` | Roundel in a ring of type. Stickers, embossing; the ring turns on the homepage hero. |
| Roundel | `emblem.svg` | Favicon, app icon, 404, footer. Holds at 16px. |
| Monogram | `monogram.svg` | A88. Embroidery, zip pulls, small woven tabs. |

Construction: letters are Rokkitt Black with 1.2% tracking. The roundel is 1.18 times the cap height (round shapes
overshoot), with a gap of 0.3 cap heights either side. Clear space is half a roundel on every side. The roundel is one
shape: a solid disc with the ridge and pine knocked out, colours swapped where they cross. All files use
`currentColor`, so they take the colour of the text around them. To change the drawing, edit `tools/make_brand.py`
and run it; never edit the SVGs by hand.

### Colour

| Token | Hex | Use |
| --- | --- | --- |
| Spruce | `#17271F` | The brand's black: text, primary buttons, announcement bar, footer, gift card |
| Night | `#0E1813` | Dark theme background |
| Pine | `#2F4A3C` | Hover on spruce, *in stock* and *added* states |
| Moss | `#7A8870` | Quiet detail on dark (print and labels) |
| Bone | `#EFEBE1` | The ground of the original logo: newsletter band, type on dark |
| Chalk | `#F7F5EF` | Page background |
| Stone | `#E2DDD0` | Behind every product image |
| Blaze | `#E5541B` | **The one accent, signals only**: bag count, *Selling fast*, low-stock dots, delivery meter, focus ring |
| Ember | `#B4410F` | Blaze for small text on light (sale price, errors): 5.2:1 on chalk |

Primary actions are solid spruce; blaze is kept for signals so it always means *look here*. Light and dark themes
are both designed: the site follows the device and the footer has a switch (Auto, Light, Dark). The hero, footer,
announcement bar and gift card stay dark in both themes.

### Typography

| Role | Face | Where |
| --- | --- | --- |
| Display | **Rokkitt** 800 / 900 (the slab from the logo) | Headlines, page, section and product titles, index rows, menu |
| Text + UI | **Geist** 400 / 500 | Navigation, buttons, cards, prices, forms, body copy |
| Facts | **Geist Mono** 400 / 500, uppercase with wide tracking for labels | Style numbers, counts, sizes, badges, field labels, breadcrumbs |

The serif is deliberate: it is the logo's own letterform. Sentence case for everything set in the slab or Geist.
Self-hosted variable fonts with tuned fallbacks, so text barely moves when they load.

### Shape

Square corners on every control, card and image. Round is reserved for the roundel, colour swatches and status dots.

### Product card
Image on the stone ground (strict 4:5) with one small badge at most (*Selling fast*, *New*, *Bestseller* or *Sold out*),
then name and price on one line, the colour name and the style number, and swatches. Desktop hover swaps the photo to
the alternate angle instantly and reveals quick-add sizes along the bottom of the image. The whole card is one link target; swatches and
quick add sit above it.

---

## 2. Token architecture (`assets/css/tokens.css`)

1. **Primitive**: the palette, fonts, type scale, motion speeds. These never change with the theme.
2. **Semantic**: what a value is for: `--ink` (text and solid fills), `--paper` (type on ink), `--color-bg`, `--color-primary`, `--color-signal` (as text), `--color-signal-fill`, `--color-success`, `--color-media`, `--surface-dark`, `--on-dark`, `--color-focus`. These flip between light and dark.
3. **Component**: values a component owns: `--media-ratio: 4 / 5`, `--bar-h`, `--nav-h`, `--sidebar-w`, `--drawer-w`, `--radius: 0`, `--tap: 44px`, `--section`.

Components read layers 2 and 3 only. To restyle, change a semantic token; no component CSS changes.

Motion: `--t-press` 80ms, `--t-fast` 200ms (hovers), `--t-base` 350ms (drawers, menus), `--t-slow` 800ms (section
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
| Colour / size selectors | `colour_selector()`, `size_selector()` | `.option`, `.size-opt` | `pdp.js` | Real radios. Sold-out sizes disabled and struck; low stock gets an orange dot. |
| Variant matrix | `variant_matrix()` | `.matrix` | – | Full size × colour availability table (PDP, *Availability*). |
| Add to bag | inline in `pdp()` | `.buy-btn` | `pdp.js` | Full-width spruce button. |
| Sticky Add to bag | `sticky_atc()` | `.sticky-atc` | `pdp.js` | Bar pinned to the bottom, phones/tablets only. |
| Accordion | `accordion()` | `.accordion` | – | Native `<details>`. |
| Promises, sign-up, footer | `promises()`, `signup()`, `footer()` | `.promises`, `.signup`, `.footer` | `store.js` | Service bar, newsletter (inline validation; hook `window.A88S.subscribe(email)` to your email provider), four link columns, legal row, A88 mark. |
| Form field | `field()` | `.field` | `gift.js` | Visible label, hint, error under the field. |

### Scaling the catalogue
- Data shape: one style per entry; `stock[colour][size]` **is** the variant matrix. SKUs are derived
  (`A88-012-OLIVE-M`). Add styles, colours or sizes without touching code.
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

## 4b. Header, homepage and motion

**Inverting header (site-wide).** Any section marked `data-nav="dark"` flips the header while the header sits over
it. Sections that also carry `data-nav-clear` (the film hero, the banner) make it see-through and lightly frosted
with light type, so the imagery runs behind it; other dark sections (the footer) give a solid spruce bar. Everywhere
else it is a solid light bar. Opening the mega-menu always brings the solid light bar back.

**Homepage, top to bottom.** Every word and picture comes from the `home` block in `data/store.json`. Each section
uses a different layout so the page never repeats itself.

| Section | Pattern |
| --- | --- |
| Film hero | Forest film full-bleed under the header. Two-line slab headline, one line of copy, two buttons, bottom left. The seal turns slowly bottom right. Muted, pauses off screen, Pause/Play button, poster only with reduced motion. |
| Name band | The three phrases from the logo in outlined slab, moving slowly. The only marquee on the site; pauses on hover; static with reduced motion. |
| New in | Product rail, *See all* link. |
| Statement | One large paragraph. Words ink in as it crosses the screen. |
| Archive index | Six category names as large rows with counts; on desktop a sticky frame shows the lead style of the row under the pointer. |
| Stories | Two pictures set off the grid, title and a line of copy underneath. Pictures drift slightly as you scroll. |
| Most wanted | One large product and four beside it (top-ranked styles that aren't new). |
| Banner | Full-bleed picture that settles as it arrives, statement, link to About. |
| Promises, sign-up, footer | Shared by every page. The full-width logo rises into place at the very end. |

**Motion.** Each movement has a job: the headline rising line by line sets hierarchy; sections arriving once give
sequence; the statement inking in and the pictures drifting tie content to scroll; hovers give feedback (the roundel
turns, arrows nudge, cards zoom slightly); page changes cross-fade and a product picture carries over from its card
to its page. Scroll-linked effects are CSS scroll-driven animations (they simply don't run in browsers without
support); reveals use IntersectionObserver in `motion.js`. With reduced motion nothing moves and everything is
visible; without JavaScript everything is visible.

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
- [x] `prefers-reduced-motion` respected (film, reveals, announcement rotation)
- [x] Responsive at 375 / 768 / 1024 / 1440, no horizontal scroll (checked at 390px)
- [x] Media space reserved (aspect-ratio), font fallbacks metric-matched (no CLS)
