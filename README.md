# Archive 88 — animated site

A single-page, scroll-animated brand site for **Archive 88**, built from the Figma brand file
("05 Quiet Caps" wordmark, A88 monogram, woven/neck label).

No build step: plain HTML, CSS and JS. GSAP, ScrollTrigger and Lenis are vendored in `assets/vendor/`.

## Run it

```bash
python3 -m http.server 8080
# open http://localhost:8080
```

Or turn on GitHub Pages for the branch (Settings → Pages → deploy from branch, root).

## What moves

| Section | Motion |
| --- | --- |
| Loader | Wordmark letters rise one by one while a counter runs 00 → 88, then the panel lifts away |
| Hero | Wordmark letters rise in, then drift apart at different speeds as you scroll |
| Field film | A small window opens into the full-screen forest film as you scroll, then the line "Made for the long way round" rises in |
| Story | The manifesto lights up word by word as you read |
| Archive | Pinned horizontal track of hang tags that swing with scroll speed |
| Label | Woven label flips up and tilts toward the cursor; monogram scales behind it |
| Marquee | Drifts constantly, speeds up and reverses with scroll direction |
| Footer | Giant wordmark rises letter by letter |
| Menu | Ink panel wipes down, category names rise in; hovering dims the others and wipes in a new film still + description. Clicking a category scrolls the archive track to that piece |
| Bag | Drawer slides in from the right; "Add to bag" sends a dot arcing up to the bag count, which pops. Removing an item slides and collapses it |
| Returns | Accordion answers open with measured height + fade |

The nav changes colour to suit each section, gets a background once you scroll past the hero, and hides when you scroll down.
`prefers-reduced-motion` skips the loader and all scroll animation.
A light film grain sits over the whole page for texture.

## Film

`assets/video/forest.mp4` is the supplied forest-to-ocean clip, edited for the web:
warm, lower-saturation grade with lifted blacks, light denoise, a 1.5s crossfade so it loops
without a jump (6.5s), no audio, 1280×720, ~2.8 MB. `assets/img/forest-poster.jpg` is the first frame,
shown while the video loads. The film only plays while it's on screen.

## Brand tokens (from Figma)

| Token | Hex |
| --- | --- |
| Ink | `#1B211D` |
| Bone | `#E6E3DA` |
| Pine | `#2F3D33` |
| Paper | `#F5F4F0` |

Type: **Archivo Narrow** Medium (wordmark / display), **Archivo** (body). Both are loaded from Google Fonts.
The wordmark is the exact vector from Figma, split into one SVG symbol per letter (top of `index.html`).

## Shop features

- **Menu** (top left): categories are read from the `data-cat` on each tag, so the counts stay correct as you add pieces.
  Preview stills are `assets/img/menu-1…5.jpg` (frames from the film). Esc closes; focus stays inside while open.
- **Bag** (top right): each piece is 1 of 1, so it can only be added once. The bag is saved in the browser (`localStorage`).
- **Returns**: steps + FAQ accordion, linked from the menu and footer.

## To do before launch

- **Copy and pieces are placeholders.** The six hang tags (names, eras, categories) and the story text
  should be replaced with the real drop.
- **Mailing list:** `setupForm()` in `assets/js/main.js` only validates the email and shows a thank-you message.
  Connect it to your provider (Klaviyo, Mailchimp, Shopify, etc.) where the `TODO` comment is.
- **Prices are placeholders** (`data-price` on each `.js-add` button).
- **Checkout isn't connected.** The Checkout button only shows a message; hand the bag to Shopify/Stripe where the `TODO` is in `setupCart()`.
- **Returns policy wording is a starting draft** (30 days, unworn, no exchanges, final-sale note). Check it against your actual policy and local consumer law before publishing.
- Add product photography to the tags if you want images; each tag is an `<article class="tag">` in `index.html`.

## Files

```
index.html            page + inline wordmark/monogram symbols
assets/css/style.css  layout, tokens, responsive rules
assets/js/main.js     all animation
assets/img/           wordmark.svg, monogram.svg, favicon.svg, forest-poster.jpg
assets/video/         forest.mp4
assets/vendor/        gsap, ScrollTrigger, lenis
.claude/skills/       design/animation skills for Claude Code
```
