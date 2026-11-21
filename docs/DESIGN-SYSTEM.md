# Archive 88: brand and design system

The storefront rebuilds the **Carhartt WIP UK** store layout, module for module, from the audit of 21 November 2026
(header, mega menu, full-width teasers with product rails, teaser grids, plain product card, category page with a
filter pill, 400px product information column, full bag page, full-screen search, footer). Only the structure,
spacing system and interaction patterns are borrowed. Every name, logo, colour, typeface, image and word is
**Archive 88's own**: the wordmark and A88 mark traced from the Figma "Archive 88 / Wordmark" component, the
Archive 88 palette, Archivo and Archivo Narrow, and the forest film.

## 1. Brand

| | |
| --- | --- |
| Positioning | Considered clothing in natural fibres, kept in the range season after season |
| Tagline | The permanent collection |
| Voice | Plain, specific, unhurried. Sentence case. Say what it is made of and how it fits |
| Assets | Wordmark letters, A88 mark and social icons in `src/brand-defs.html`; fonts in `assets/fonts/`; campaign stills from the forest film in `assets/img/campaign/` |

### Colour: the original's roles, Archive 88's values

| Token | Hex | Original role and value | Use |
| --- | --- | --- | --- |
| `--black` | `#1B211D` (ink) | black `#000` | Text, primary buttons, logo on the solid header |
| `--white` | `#FBFAF8` | white `#FFF` | Page background, type over images |
| `--darkGrey` | `#4A514C` | darkGrey `#555` | SEO copy, text on dark grounds |
| `--midGrey` | `#646A65` | midGrey `#737373` | Colour and price lines, link hover, input ring (5.3:1 on white) |
| `--subtleGrey` | `#DAD7CE` | subtleGrey `#DDD` | Filter pill ring, panel border |
| `--lightGrey` | `#F1EFEA` | lightGrey `#F3F3F3` | Size tiles, checkbox dots, teaser placeholder, disabled button |
| `--imageGrey` | `#ECEBE6` (mist) | imageGrey `#EFEFEF` | Product image ground |
| `--signal` | `#A3471F` (burnt orange) | green `#00A442` | "New" badge, low-stock dots and messages |
| `--error` | `#8A3A18` | red `#DE141F` | Form errors |
| `--pine` | `#2F3D33` | – | Button hover, success messages, the posted gift card |

### Typography

| Role | Face | Where |
| --- | --- | --- |
| Display | **Archivo Narrow** 600 (variable 400–700) | Hero and tile titles, page titles (h1), mobile menu |
| UI and body | **Archivo** (variable 100–900): 600 for UI, 400 for prose | Navigation, cards, buttons, prices, forms, footer; prose in 400 |

Scale (tokens `--t0` to `--t7`, as on the original): 11, 14, 16, 20, 32, 48, 80, 120px. The original sets almost all
UI in Bold; Archive 88 uses a firm 600. Body prose (SEO copy, accordions, info pages, promises) is 400.

### Spacing, shape, motion
- Custom scale `--s1` … `--s64`: 2, 5, 10, 15, 20, 30, 40, 50, 60, 80, 100, 120, 160px. Working rhythm: 20px gutters,
  40px desktop margins, 60px hero padding and desktop section spacing.
- Square corners everywhere except the round filter pill, checkbox dots and round buttons. No shadows: depth comes
  from photography and two 16-stop eased ink gradients (`--overlay-65` on images, `--overlay-50` behind the
  see-through header).
- 200ms for links, header, overlays and drawers. Hover effects only under `(hover: hover) and (pointer: fine)`.
  `prefers-reduced-motion` removes movement and skips the hero film.
- One breakpoint, 1024px: below it every multi-column band is a swipe row with a peek of the next item.

## 2. Pages

| Page | What's on it |
| --- | --- |
| Home `/` | Page builder from `store.json → home`: full-width teaser (film) + rail, full-width teaser + rail, three 3:4 tiles, two 3:4 tiles |
| Listings `/shop/…` | Sub-category links (4-column block indented 200px; two-row scroll on phones), h1 and intro, Filter pill (sticky top right on desktop, bottom centre on phones), 4/2-column grid, 48 per page with `?page=`, SEO copy |
| Product `/products/<handle>/?colour=` | Two-column gallery (swipe with 1/4 counter on phones), 400px information column: New, title, price, photographic swatches, sizes in three columns, size guide, Choose size → Add to bag, wishlist, five promises, five accordions; sticky purchase bar; Complete the look; You might also like; Product JSON-LD |
| Bag `/bag/` | Line items, quantity, Remove (on hover on desktop, always on phones), promo code, promises, free-delivery message, totals, Checkout column (first on phones) |
| Search `/search/?query=` | Full screen, own header (logo, boxed field, Close), trending searches, suggestions, live results, Filter pill |
| Gift cards, About, Size guide, Delivery & returns, Contact, Privacy, Terms, 404 | Same shell |

Listing tree: `shop/` (Shop all), `shop/new-arrivals/`, `shop/bestsellers/`, `shop/<category>/`, sub-categories
`shop/<category>/<group>/` and fits `shop/<category>/<fit>-fit/` (from `store.json → categories[].subcategories`),
`shop/fabric/<fabric>/` and `shop/fit/<fit>/` (derived from each style's material and fit lines in `build.py`).

## 3. Components

| Component | Python | CSS | JS |
| --- | --- | --- | --- |
| Header (see-through over the hero, solid after 10px of scroll or when a menu opens) | `header()` | `.hdr` | `store.js` |
| Mega menu (second level only, columns of three, hover or chevron button) | inside `header()` | `.mega` | `store.js` |
| Breadcrumb in the header (product pages) | `header(crumbs=…)` | `.hdr__crumbs` | – |
| Mobile menu (full screen, drill-down, back arrow) | `menu_dialog()` | `.menu` | `store.js` |
| Login drawer | `login_dialog()` | `.drawer` | `store.js` |
| Added-to-bag pop-up | inside `header()` | `.added` | `store.js` |
| Full-width teaser | `full_width_teaser()` | `.teaser--full` | `store.js` (film) |
| Product rail | `products_listing()` | `.rail` | – |
| Teaser grid | `teaser_grid()` | `.tgrid`, `.teaser--tile` | – |
| Product card (one per colourway) | `product_card()` | `.card`, `.wish` | `store.js` (wishlist) |
| Carousel with round arrows | `carousel()` | `.carousel` | `store.js` |
| Sub-category links | `subnav()` | `.subnav` | – |
| Filter pill and panel | `filter_pill()`, `filter_panel()` | `.pill`, `.fpanel`, `.facet` | `plp.js` |
| Pagination | `pagination()` | `.pager` | `plp.js` |
| Gallery and full-screen viewer | in `pdp()` | `.gal`, `.fs` | `pdp.js` |
| Size selector, add to bag, sticky bar | in `pdp()` | `.size`, `.buy`, `.pbar` | `pdp.js` |
| Size guide (two tabs, numbered drawing) | `size_guide_dialog()` | `.sg`, `.tabs` | `pdp.js` |
| Accordion | `accordion()` | `.acc` | – (native `<details>`) |
| Bag page | `bag()` | `.bag`, `.line`, `.totals` | `bag.js` |
| Search page | `search_page()`, `search_index()` | `.srch` | `search.js` + `plp.js` |
| Footer and newsletter | `footer()` | `.ftr`, `.news`, `.dot` | `store.js` |

## 4. Accessibility and SEO
- Skip link, visually hidden h1 on the home page, module titles as h2, card titles h2 on listings and h3 in rails.
- Screen-reader labels for visual-only values ("Colour:", "Price:"), the bag count ("Go to bag, 2 items"), icon
  buttons ("Show sub categories for Clothing", "Open the main menu", "Add to wishlist: …"), 44px targets.
- Full-tile anchors on teasers use `tabindex="-1"`, so keyboard users meet each link once.
- Native `<dialog>` for every overlay (focus trap, Escape, focus return). `scrollbar-gutter: stable`.
- The hero film can be paused and is not loaded with reduced motion.
- Canonical URLs, Open Graph, Organization + WebSite JSON-LD on home, BreadcrumbList on listings and products,
  Product JSON-LD on products. Search and bag are `noindex, follow`.
- Hooks: `window.A88.subscribe(email, interests)` for the newsletter; if `window.dataLayer` exists, teasers send GA4
  `view_promotion` and `select_promotion`.

## 5. Not built (and why)
- Cookie banner: the site sets no cookies and loads no third-party scripts; add one with your consent tool when you add analytics.
- Accounts: the Login drawer is in place and says accounts open soon.
- Country switcher, apps, store finder, Apple Pay: Archive 88 has no equivalent yet.
