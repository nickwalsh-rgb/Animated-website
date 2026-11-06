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
| Story | The manifesto lights up word by word as you read |
| Archive | Pinned horizontal track of hang tags that swing with scroll speed |
| Label | Woven label flips up and tilts toward the cursor; monogram scales behind it |
| Marquee | Drifts constantly, speeds up and reverses with scroll direction |
| Footer | Giant wordmark rises letter by letter |

The nav changes colour to suit each section, gets a background once you scroll past the hero, and hides when you scroll down.
`prefers-reduced-motion` skips the loader and all scroll animation.

## Brand tokens (from Figma)

| Token | Hex |
| --- | --- |
| Ink | `#1B211D` |
| Bone | `#E6E3DA` |
| Pine | `#2F3D33` |
| Paper | `#F5F4F0` |

Type: **Archivo Narrow** Medium (wordmark / display), **Archivo** (body). Both are loaded from Google Fonts.
The wordmark is the exact vector from Figma, split into one SVG symbol per letter (top of `index.html`).

## To do before launch

- **Copy and pieces are placeholders.** The six hang tags (names, eras, categories) and the story text
  should be replaced with the real drop.
- **Mailing list:** `setupForm()` in `assets/js/main.js` only validates the email and shows a thank-you message.
  Connect it to your provider (Klaviyo, Mailchimp, Shopify, etc.) where the `TODO` comment is.
- Add product photography to the tags if you want images; each tag is an `<article class="tag">` in `index.html`.

## Files

```
index.html            page + inline wordmark/monogram symbols
assets/css/style.css  layout, tokens, responsive rules
assets/js/main.js     all animation
assets/img/           wordmark.svg, monogram.svg, favicon.svg
assets/vendor/        gsap, ScrollTrigger, lenis
.claude/skills/       design/animation skills for Claude Code
```
