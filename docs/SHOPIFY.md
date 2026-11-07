# Moving Archive 88 to Shopify

Everything in this repo is shaped so it can move to Shopify with little rework:
the product data matches Shopify's fields, the build already writes an import CSV, and each page section
maps onto a theme section.

Recommended route: **a custom Shopify theme built from this design** (checkout, stock, product pages,
Instagram/Facebook shop and Google Shopping all come from Shopify).

---

## 1. Create the metafield definitions first

In Shopify admin: **Settings > Custom data > Products > Add definition**. Use namespace `archive`.
The CSV import only fills metafields that already have a definition.

| Name | Namespace and key | Type |
| --- | --- | --- |
| Number | `archive.number` | Single line text |
| Era | `archive.era` | Single line text |
| Size | `archive.size` | Single line text |
| Material | `archive.material` | Single line text |
| Condition | `archive.condition` | Single line text |
| Condition notes | `archive.condition_notes` | Multi-line text |
| Flaws | `archive.flaws` | Multi-line text (one per line) |
| Measurements | `archive.measurements` | JSON |
| Tag colour | `archive.tag_colour` | Single line text (ink, pine or paper) |
| Final sale | `archive.final_sale` | True or false |
| Drop | `archive.drop` | Single line text (e.g. Season one) |

## 2. Import the products

1. Put the real pieces in `data/products.json` and photos in `assets/products/<handle>/`.
2. Make sure the site (with photos) is live at the URL in `data/site.json`. The CSV points Shopify at those image URLs to download them.
3. Run `python3 build.py`.
4. Shopify admin: **Products > Import** and choose `shopify/products.csv`.
5. Check one product: price, inventory (1, or 0 if sold), photos and the metafields above.

What the CSV sets:

| products.json | Shopify |
| --- | --- |
| `handle` | Handle (also the product URL: `/products/<handle>`) |
| `title`, `description` | Title, Description |
| `category` | Product type + a tag |
| `drop` | `archive.drop` metafield + a tag (use it for the drop collection) |
| `price` | Variant price (GBP) |
| `available` | Inventory quantity 1 (available) or 0 (sold); "continue selling when out of stock" is off |
| `number` | SKU `A88-<number>` + metafield |
| everything else | `archive.*` metafields |

After importing, set **Product category** (Shopify's standard taxonomy, e.g. Apparel > Clothing > Outerwear)
in bulk. It helps Google and Meta catalogues.

## 3. Categories, drops and sold pieces

- **Categories:** create one automated collection per category with the condition *Product type is equal to Outerwear* (and so on).
  Use the same handles as `data/site.json` (`outerwear`, `knitwear`...) so links carry over.
- **Drops on set dates:** create a collection per drop (e.g. "Season two") and, on each product, schedule its availability on the
  Online Store sales channel for the drop date and time. Put the same date in the theme setting for the hero's "Next drop" line.
- **Sold pieces stay visible:** keep sold products **active** with 0 stock. The theme shows the Sold stamp when
  `product.available` is false, exactly like the static site does with `"available": false`.

## 4. Turning this design into the theme

| This repo | Shopify theme |
| --- | --- |
| `src/partials/head.html` | `layout/theme.liquid` `<head>` (Shopify adds its own SEO tags; keep the Open Graph `product:*` tags and JSON-LD) |
| `src/partials/header.html` | `sections/header.liquid` (menu from a navigation menu or collections; bag from `cart`) |
| `src/partials/footer.html` | `sections/footer.liquid` |
| `src/partials/home-main.html` | `templates/index.json` made of sections: `hero`, `film`, `story`, `archive-track` (loops over a collection), `label`, `marquee`, `returns`, `newsletter` |
| `src/partials/product-main.html` | `sections/main-product.liquid` + `templates/product.json` |
| the hang tag in `build.py` (`tag_card`) | `snippets/hang-tag.liquid` |
| `src/partials/shop-main.html` + `assets/js/shop.js` | `templates/collection.json` (the "all" collection); filters can stay client-side, or use Shopify's Search & Discovery filters |
| `src/partials/record-main.html` | a page template looping over all products (including sold) grouped by the `archive.drop` metafield |
| `src/pages/*.html` | Shopify pages; Privacy and Terms go in **Settings > Policies** |
| `data/site.json` values | theme settings (`config/settings_schema.json`): drop date, social links, shipping text, returns FAQ blocks |
| `assets/css`, `assets/js`, `assets/fonts`, `assets/vendor` | theme `assets/` (flat folder; update paths with `asset_url`) |

Liquid equivalents of the generated values:

```liquid
{{ product.metafields.archive.number }}            No. 001
{{ product.metafields.archive.measurements.value }}  measurements object, loop over it for the table
{% if product.available %} Add to bag {% else %} Sold {% endif %}
{{ product.price | money }}
{{ product.featured_image | image_url: width: 1600 | image_tag: loading: 'lazy' }}
```

## 5. Wiring the bag, checkout and email

The bag in `assets/js/site.js` (`setupCart`) stores items in the browser. On Shopify, replace its storage with the
Ajax Cart API:

- **Add:** `POST /cart/add.js` with `{ id: <variant id>, quantity: 1 }` (put `data-variant-id` on the Add to bag button in the hang-tag snippet).
- **Read / count:** `GET /cart.js`.
- **Remove:** `POST /cart/change.js` with `{ id: <line key>, quantity: 0 }`.
- **Checkout button:** link to `/checkout`.

The animations (dot arcing to the bag, count pop, drawer) stay the same.

**Email sign-up:** use Shopify's customer form in the newsletter section:

```liquid
{% form 'customer' %}
  <input type="hidden" name="contact[tags]" value="newsletter">
  <label for="email">Email address</label>
  <input id="email" type="email" name="contact[email]" required>
  <button type="submit">Join</button>
{% endform %}
```

Then send drop emails with Shopify Email (or Klaviyo).

## 6. Sales channels

Once products are live: add the **Facebook & Instagram** and **Google & YouTube** channels. They read the
same products, so the Instagram shop and Google Shopping stay in sync with stock automatically.
