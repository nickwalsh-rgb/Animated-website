# Archive 88 · "The long way round": concept homepage

Concept only. Not linked from the site, not built by `build.py`, not deployed.
Open `concepts/redesign/index.html` straight from disk (it uses the site's own fonts, film, stills, wordmark and garment art via `../../assets/`).

## 0. Brief
A 7-part homepage for **Archive 88**: a permanent collection of clothing in natural fibres, kept in every size.
Visitor: someone tired of seasonal churn who will pay more for something they keep for years.
Mood: **quiet, enduring, outdoors.**
**Signature: the aperture.** The page opens on paper with the ARCHIVE 88 wordmark edge to edge and the forest film held in a
small portrait window (two figures walking toward the sea). Scrolling opens the window to full bleed while the wordmark
letters part and fade, and then the headline rises over the film. It turns the brand film into the way in.
Supporting moves (all quiet): masked line rise, scroll-lit manifesto, cursor-following garment on the collection index,
slow fibre marquee. Fidelity: nothing beyond what is listed here.

## 1. Stack
A single `index.html` with inline CSS and JS. No libraries. Brand SVGs are inlined (wordmark letters and the A88 mark from `src/brand-defs.html`, icons and garment art from `assets/sprite.svg`).

## 2. Fonts (self-hosted, `assets/fonts/fonts.css`)
| Role | Family | Weights | Used on |
|---|---|---|---|
| Display | Archivo Narrow | 500 | H1, H2, manifesto, index titles, stats, marquee |
| Body/UI | Archivo | 400 / 500 | nav, body, buttons, labels |

## 3. Tokens
```
--paper #fbfaf8  (page)       --mist #ecebe6 (product ground)   --ink #1b211d (text, footer)
--pine  #2f3d33  (fibre band)  --muted #646a65 (5.3:1)           --line rgba(27,33,29,.12)
--signal #a3471f: used only on the bag dot, the (0n) section indices and ::selection
```
Square corners everywhere (brand rule). Grain: fixed SVG fractal noise, opacity .05, z 100, no pointer events.

## 4. Hero: the aperture (runway 260vh desktop, 230vh mobile; sticky stage 100dvh)
- **Film** `assets/video/forest.mp4` (≥768px) / `forest-portrait.mp4` (<768px), poster `forest-poster.jpg` / `campaign/hero-1-mobile.jpg`,
  `autoplay muted loop playsinline`, `object-fit:cover; object-position:50% 60%`. The figures sit dead centre, so the narrow window always frames them.
- Window at rest: desktop 28vw × 60vh, mobile 64vw × 50vh, centred, lifted 4vh. Clipped with `clip-path: inset(t r b l)`; the insets
  scale by `(1 − p)`, where `p = easeInOutCubic(smoothstep(0, .58, s))` and `s` = scroll progress through the runway, lerped at .12.
  The film scales 1.18 → 1 with p.
- **Wordmark**: inline SVG `viewBox 0 0 640 68`, nine `<use>` letters, width `calc(100vw − 2·gutter)`, bottom = gutter, ink.
  Load: each letter rises from translateY(105%) in a masked box, .9s, `cubic-bezier(.22,1,.36,1)`, delay `.15 + i·.05s`.
  Scroll: letter i moves `(i − 4)·p·5vw` sideways and `p·40px` down, and the group's opacity is `1 − smoothstep(.05, .4, s)`.
- **Side labels** (desktop only), 11px Archivo 500, uppercase, +.18em, ink 60%, vertically centred beside the window:
  left "The permanent collection / No. 001–100", right "Natural fibres / Every size, all year". Opacity `1 − p·2.2`.
- **Phase 2** (s > .6): a bottom scrim `linear-gradient(0deg, rgba(27,33,29,.62), transparent 60%)` fades in with `smoothstep(.5, .8, s)`.
  - **H1** "Clothes for / the long way round.": Archivo Narrow 500, `clamp(3.25rem, 8.2vw, 9.5rem)`/.9, −.02em, paper. Each line sits in an `overflow:hidden` box and rises 110% → 0 over .95s, stagger .1s.
  - **Sub** (16px, paper 80%, max 30rem): "One collection in natural fibres, kept in every size, all year. No seasons, no sell-outs, nothing made to be replaced."
  - **CTAs**: primary "Shop the collection →" (paper fill, ink text, 50px, 0 28px); secondary "Find your fit" (paper text with an underline that grows from the left).
  - Bottom-right: "Free UK delivery over £150 · Free 30-day returns", 12px, paper 70%.
- **Nav** (fixed, 64px): A88 mark left; Shop · Fabrics · Fits · Journal · Gift cards (13px/500) centred; Search · Account · Bag with an orange dot right.
  Tone is ink over paper and paper over the open film (p > .92). After the hero it turns solid: paper at 92% with a 12px blur and a hairline.
  Mobile: the mark plus Bag and a two-line burger.

## 5. (01) The idea: manifesto
Padding `clamp(96px, 13vw, 176px)` vertical. 12-column grid: label in columns 1–3, text in 4–12.
Text: Archivo Narrow 500 `clamp(2rem, 4.3vw, 4.25rem)`/1.04, −.015em. Words start at 16% ink and light up in order as the
section scrolls through (from its top at 85% of the viewport to its bottom at 55%).
"We don't make seasons. We make one collection, keep every style in every size, and only change a piece when we can make it better. Buy it once. Wear it in. Send it back to be mended."
Stats row (4 columns, hairline on top; 2×2 on mobile): numerals in Archivo Narrow 400 `clamp(3rem, 6vw, 5.5rem)`, counted up over 1.6s:
100 / styles in the collection · 305 / colourways, all kept in stock · 6 / sizes, XS to XXL, every style · 0 / seasonal drops, ever.

## 6. (02) The collection: index
Six rows (Outerwear 14 · from £250, Knitwear 18 · £120, Shirts 18 · £85, Jersey 18 · £50, Trousers 16 · £95, Tailoring 16 · £215).
Each row is `grid: 72px 1fr 160px 120px 32px`, has a hairline on top and 18px vertical padding.
Title: Archivo Narrow 500, uppercase, `clamp(2.6rem, 7vw, 7rem)`/.92.
Hover (pointer: fine): the row title slides +24px over .5s, the other rows dim to 30%, and a 280×350 mist card follows the cursor
(lerp .14, tilt ±8° from x-velocity). The card holds that category's garment in a catalogue colour:
coat Camel #B08A5B, knit Rust #8E4527, shirt Pale Sky #AFBBC6, tee Navy #232B3A, trouser Olive #5E6142, blazer Chocolate #4A3428.
On touch screens each row shows a 40px swatch instead.

## 7. (03) Most worn: product grid
H2 "Kept in every size." with a "Shop bestsellers →" link. Four cards (4 columns; a scroll-snap rail at 80vw per card on mobile).
Each card has a mist 4:5 ground with the garment drawn at 72% in its first colour. On hover the garment lifts 6px and scales 1.03 over .6s.
Clicking a swatch (18px square, 1px ring, ring turns ink when active) changes the garment colour with a .4s `color` transition.
Each card lists title and price, then material and origin.
Products: Single-Breasted Overcoat £250, Fisherman Jumper £235, Chambray Shirt £125, Straight Chino £165 (real catalogue data).

## 8. (04) Fabrics: marquee band
Pine ground, paper text. One row: "Merino ✳ Lambswool ✳ Cashmere ✳ Linen ✳ Moleskin ✳ Selvedge denim ✳ Waxed cotton ✳",
in Archivo Narrow 500 uppercase `clamp(4rem, 11vw, 10rem)`, scrolling linearly over 60s. The ✳ glyphs are paper at 35%.
Below it: the label on the left, and on the right 18px copy at paper 80% with a "Shop by fabric →" link.

## 9. (05) Made to be mended
Two columns, 5/7. Left: still `menu-2.jpg` at 4:5, with an inner parallax from scale 1.12 that moves ±6% over the section.
Right: H2 "Wear it in. / Send it back. / We'll mend it.", then body copy, then three promise rows (truck, return and leaf icons from the sprite), then "Read our story →".

## 10. Footer
Ink ground. "Letters from the archive." H2 with a one-line sub, and an email field with an underline and a "Subscribe →" button.
Three link columns at 13px, paper 60%. Last comes the full-width wordmark in paper, whose letters rise in when it enters view, and the © line.

## 11. Motion rules
Entrances use `cubic-bezier(.22,1,.36,1)`. Reveals are in-view once, at a .18 threshold: y 28px → 0 and opacity 0 → 1 over .9s, staggered .08s.
Nothing loops except the film and the marquee. Under `prefers-reduced-motion`, scroll mappings stay without smoothing, there is no marquee or cursor card, the film does not autoplay, and all reveals show their final state.
If the JS fails, the rest state is fully visible, because hidden states only apply under `.js`.
