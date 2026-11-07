# Session handoff: Archive 88 website

Written 7 November 2026, at the end of a long build session. It records what exists, why it is built the way it is, and what comes next.
The README describes the site's features in full; this file covers the state of the work and decisions not to undo by accident.

- Repo: `nickwalsh-rgb/Animated-website`
- Live site: https://nickwalsh-rgb.github.io/Animated-website/ (GitHub Pages, served from `main`)
- Working branch: `ccr-27144a79-23zebb`. Each round of work was merged into `main` by pull request; the last was **PR #12** (merged, deployed).

---

## 1. What was completed

### Earlier rounds (PRs #1 to #11)
- **The site itself:** built from the Archive 88 Figma logo file and the supplied forest video, in an earthy colour palette. It has:
  - a loader on first visit, a hero, the film and the Story section
  - a pinned sideways archive row of hang tags, then the Label section and the marquee
  - Shop the Look, Returns and Join the list.
- **Menu and bag:** a category menu with motion, and a bag drawer saved in the browser.
- **Social icons:** raised Instagram and Facebook keys in the header and footer.
- **Search and sharing:** full meta tags, Open Graph tags and structured data.
- **Pages:**
  - Product pages generated from data.
  - Shop all, with category and size filters kept in the address.
  - The record (every piece ever released, grouped by drop).
  - About, Contact, Size guide, Privacy and Terms.
  - The lookbook, with clickable markers on each photo.
- **Drops:** drops happen on set dates, and the homepage shows a countdown to the next one.
- **Shopify readiness:** Shopify isn't set up yet, but the build exports `shopify/products.csv` and `docs/SHOPIFY.md` explains the setup.
- **Press motion:** every button sinks when pressed and springs back; primary buttons also ripple from the point pressed.
- **Accent colour:** burnt orange `#A3471F`. It marks signals (bag count, drop dates, markers and similar) plus one primary action per page. Errors use ink, never orange.
- **Placeholders:** placeholder business details and a draft About story, both waiting for the owner's real content.
- **Skills:** 30 skills in `.claude/skills/`, including the 7 UI/UX Pro Max skills.

### This session (PR #12): the UI/UX Pro Max pass
**Tier 1: the basics**
- **Accessibility:**
  - a skip link
  - links marked with `aria-current` for the page you're on
  - tap targets of at least 44px
  - phone text of at least 15px
  - the bag's changes announced to screen readers through a hidden status message.
- **Back button:** Back returns you to your scroll position.
- **Fonts:** size-matched fallback fonts, so text doesn't jump when the real fonts load.
- **Motion timing:** shared tokens in CSS (`--t-press/--t-fast/--t-base/--t-slow`) and JS (`A88.T`).

**Tier 2: the experience**
- **Page transitions:** cross-document View Transitions. A hang tag's photo morphs into the product's first photo.
- **Homepage chapter rail:** built from `[data-chapter]` sections. On phones it becomes a progress line at the top.
- **Product page:**
  - an Add to bag bar pinned to the bottom on phones, with a Join the list version for sold pieces
  - a photo zoom viewer, which appears only when real photos exist
  - "Check the fit", which remembers your measurements on the device in `localStorage` under `a88-fit:<measurement>`.
- **Lookbook:** an "Add the whole look" button.
- **Bag:**
  - an Undo message after removing a piece
  - a haptic tap on add, through `navigator.vibrate`
  - suggestions of available pieces when the bag is empty.
- **Email sign-up:**
  - The address is checked when you leave the field.
  - It shows Joining, Joined and error states, with Joining held for at least 600ms so it doesn't flash.
  - It calls a `window.A88.subscribe(email)` hook, which should return a promise.
- **Fixes:**
  - "Join the list" was showing in the phone header, a regression from the tap-target work.
  - Lookbook markers on the homepage could end up invisible after their animation.
- **README:** updated to describe all of the above.

---

## 2. Architecture and decisions to keep

- **Static site from a Python build:**
  - `build.py` uses only the Python standard library, plus Pillow for photo resizing when it is installed.
  - It reads `data/*.json` and `src/partials/*.html` (the shared page pieces) plus `src/pages/` (the info page bodies).
  - It writes every page.
- **Never hand-edit generated files:**
  - `index.html`, `shop/`, `record/`, `lookbook/`, `products/*/` and the info page folders
  - `sitemap.xml`, `robots.txt` and `shopify/products.csv`.
  - Edit the data, partials or `build.py`, then run `python3 build.py`.
- **Content lives in data files:**
  - `data/products.json`: the pieces (sample data).
  - `data/site.json`: business details, drops, categories, shipping and the returns FAQ.
  - `data/lookbook.json`: the looks (placeholders).
- **Photos:** go in `assets/products/<handle>/01.jpg…` and `assets/lookbook/<look>.jpg`. The build makes resized web versions in a `web/` folder beside the originals.
- **JavaScript:**
  - `assets/js/site.js` is shared by every page. It exposes `window.A88 = { $, $$, ROOT, site, motion, reduced, D, T, splitLines, splitWords, onCategory, restoreScroll }`.
  - Each page type has its own script: `home.js`, `product.js`, `shop.js` and `lookbook.js`.
- **Libraries:** GSAP 3.12.7 (with ScrollTrigger and Flip) and Lenis 1.1.20 are kept in the repo under `assets/vendor/`. There is no CDN and no npm build.
- **Press motion:** uses the Web Animations API on the separate CSS `scale` property, so it never fights GSAP or hover transforms.
- **Reduced motion:** `prefers-reduced-motion` turns all motion off. Revealed content fades with opacity only, never `visibility`.
  - Anything that must receive focus while it fades in must also use opacity, not GSAP's `autoAlpha`. Using `autoAlpha` there caused two focus bugs this session.
- **Accent colour rule:** the accent is used only on light sections (paper and bone). Each page has one accent action; every other button is ink.
- **Automatic rebuilds:**
  - `.github/workflows/build.yml` rebuilds the site on every push and hourly, so the countdown and drop state stay current.
  - It commits the generated files, then asks GitHub Pages to rebuild.
  - `.nojekyll` must stay: Jekyll fails on the Liquid code example in `docs/SHOPIFY.md`.
- **Cart storage:** the bag is saved in the browser's `localStorage`. Shopify checkout is a TODO in `site.js` (the `checkout` click handler).

---

## 3. Current state

- `main` = `5d26edd` (merge of PR #12). The deploy succeeded ("Build site" and "pages build and deployment" both passed).
- The working tree is clean. No test photos are left in `assets/products/`.
- All product, lookbook and business data is **sample or placeholder** content.
- **Last test run (Chromium, desktop and iPhone 13):**
  - axe accessibility checker: no violations on any page.
  - These all passed: lookbook, press motion, shop filters, buy bar, zoom, fit check, undo, whole look and email states.
  - Console errors: none.
- **Tests are not in the repo:** the test scripts lived in this session's scratchpad (`uxaudit.js`, `t5.js`, `look.js`, `press.js`, `pdp.js`, `bag.js`). They are lost when the session ends.

---

## 4. Remaining tasks

### Waiting on the owner (they said they aren't ready yet; keep the placeholders until they are)
- [ ] Real business details in `data/site.json`. The current ones are placeholders.
- [ ] Legal review of Privacy and Terms, then set `"legal_reviewed": true`.
- [ ] The real About story, replacing the draft in `src/pages/about.html`.
- [ ] Real pieces, photos, drop dates, lookbook photos with marker positions, social links and shipping wording.
- [ ] Shopify setup (follow `docs/SHOPIFY.md`):
  - Connect checkout (the TODO in `site.js`).
  - Connect email sign-up by setting `window.A88.subscribe`. Until then the form says "Joined" but stores nothing.

### Tier 3 (proposed, not yet requested)
- [ ] Sorting on Shop all (newest, price).
- [ ] Search on the record page.
- [ ] Swiping between looks on the lookbook on phones.
- Dark mode was considered and **not recommended**: it doesn't fit the brand's light/dark section rhythm.

---

## 5. Known issues and loose ends

- **Audit script false positives:** the `uxaudit.js` audit reported:
  - `bagLive: false`, because it looks for an old selector. The live status element is `.js-bag-status`, which works.
  - A wrong scroll value after Back, because Playwright's click scrolls the page itself. Scroll restore was verified separately: 1200 → 1200.
- **Focus partly hidden:** the audit found 1 of 34 focused elements partly hidden behind the fixed nav. It wasn't investigated; the likely fix is a `scroll-padding-top` or `scroll-margin` adjustment.
- **Zoom and real photos:** photo zoom and photo thumbnails have only been tested with a temporary stand-in photo. Re-check them once real product photos are added.
- **Haptics:** the vibration on add only works on Android. iOS Safari doesn't support `navigator.vibrate`.
- **Page transitions:** they need a browser that supports cross-document View Transitions (Chromium-based browsers). Other browsers fall back to normal navigation.
- **Live site not checked directly:** this cloud container's network blocks `*.github.io`, so the live site was confirmed through the Actions runs, not by loading it.
- **Branch hygiene:** `ccr-27144a79-23zebb` has been merged. Start new work from the latest `main`.

---

## 6. Next steps

1. Load the live site and do a quick visual check on desktop and phone:
   - the page transition from a tag to its product page
   - the chapter rail
   - the buy bar on phones
   - Undo in the bag.
2. Recreate the regression tests inside the repo, for example in `tests/` with Playwright and axe-core, so they outlive sessions.
3. Fix the partly hidden focused element (section 5).
4. Ask the owner whether to start Tier 3, or move on to Shopify setup once their store exists.
