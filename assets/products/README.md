# Product photos

One folder per piece, named after its `handle` in `data/products.json`:

```
assets/products/chore-jacket/01.jpg   <- first photo: used on the hang tag, bag, share preview and Shopify
assets/products/chore-jacket/02.jpg
...
```

- **Order** is by file name, so number them `01`, `02`, `03`...
- **Shape:** portrait 4:5. 1600 × 2000 px is ideal; JPG at ~80% quality keeps them light.
- **Suggested shot list** (shown as empty slots until photos exist): Front, Back, Label, Detail, Flaws.
- Then run `python3 build.py`. No other changes needed.
