# Product photos

One folder per style, named after its `handle` in `storefront/data/catalog.json`:

```
assets/products/merino-crew/
  oat-1.jpg      front           (shown first; the card's main image)
  oat-2.jpg      alternate angle (shown on card hover)
  oat-3.jpg      detail
  oat-4.jpg      on body / back
  navy-1.jpg ...
```

- File names: `<colour handle>-<n>.jpg|png|webp`. The colour handle must match the style's colour in catalog.json.
- **4:5 portrait, 1600 x 2000 px ideal.** Anything else is centre-cropped to exactly 4:5 by the build, so frame the
  garment with room around it.
- Shoot every style the same way (same background, light and crop) so the grid reads as one calm surface.
- Run `python3 storefront/build.py`. With Pillow installed it writes `web/` copies (WebP 480/960/1600 + JPEG 1200).
  Colours without photos keep showing the placeholder art.
