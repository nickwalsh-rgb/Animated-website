"""Writes SAMPLE catalogue data to data/catalog.json (100 styles, size x colour variants).

Run once to (re)generate placeholder data:  python3 tools/seed_catalog.py
Replace catalog.json with your real range (or a Shopify export mapped to the same shape) before launch.
Deterministic: the same seed always produces the same file.
"""
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "catalog.json"
rng = random.Random(88)

COLOURS = {
    "ink": ("Ink", "#1E2421", "black"),
    "navy": ("Navy", "#232B3A", "blue"),
    "charcoal": ("Charcoal", "#45474A", "grey"),
    "stone": ("Stone", "#B9B2A4", "neutral"),
    "ecru": ("Ecru", "#E9E3D3", "white"),
    "white": ("Optic White", "#F6F5F1", "white"),
    "oat": ("Oat", "#D3C6AE", "neutral"),
    "camel": ("Camel", "#B08A5B", "brown"),
    "chocolate": ("Chocolate", "#4A3428", "brown"),
    "olive": ("Olive", "#5E6142", "green"),
    "pine": ("Pine", "#2F3D33", "green"),
    "rust": ("Rust", "#8E4527", "red"),
    "sky": ("Pale Sky", "#AFBBC6", "blue"),
}
ALPHA = ["XS", "S", "M", "L", "XL", "XXL"]
WAIST = ["28", "30", "32", "34", "36", "38"]

# category: (silhouette, size run, price range, palette, names, material, fit, origin)
CATS = {
    "outerwear": ("coat", ALPHA, (245, 495), ["ink", "navy", "camel", "olive", "stone", "chocolate"],
        ["Single-Breasted Overcoat", "Waxed Field Jacket", "Wool Car Coat", "Quilted Liner Jacket", "Cotton Trench",
         "Melton Peacoat", "Ripstop Parka", "Wool Chore Coat", "Raglan Mac", "Down Gilet", "Suede Blouson",
         "Herringbone Topcoat", "Waxed Harrington", "Shearling-Collar Jacket"],
        ["Virgin wool, recycled nylon lining", "Waxed British cotton", "Water-repellent cotton gabardine"],
        ["Relaxed through the body, hits mid-thigh", "Regular fit, sits at the hip"], ["Portugal", "Great Britain", "Italy"]),
    "knitwear": ("knit", ALPHA, (110, 260), ["oat", "ecru", "navy", "charcoal", "olive", "camel", "rust", "pine"],
        ["Merino Crew", "Lambswool V-Neck", "Cashmere Roll Neck", "Shetland Crew", "Ribbed Cardigan",
         "Fisherman Jumper", "Merino Polo", "Cotton Half-Zip", "Brushed Mohair Cardigan", "Cable Crew",
         "Cashmere Crew", "Waffle Knit Henley", "Lambswool Shawl Cardigan", "Merino Zip Cardigan",
         "Linen Crew", "Alpaca Crew", "Textured Cotton Crew", "Fine-Gauge Mock Neck"],
        ["Extra-fine merino wool", "Geelong lambswool", "Mongolian cashmere", "Organic cotton"],
        ["Regular fit, ribbed hem and cuffs", "Relaxed fit, dropped shoulder"], ["Scotland", "Italy", "Portugal"]),
    "shirts": ("shirt", ALPHA, (85, 165), ["white", "sky", "ecru", "navy", "olive", "stone", "chocolate"],
        ["Oxford Button-Down", "Poplin Shirt", "Brushed Flannel Shirt", "Linen Camp Collar Shirt", "Denim Western Shirt",
         "Corduroy Overshirt", "Twill Workshirt", "Band Collar Shirt", "Seersucker Shirt", "Chambray Shirt",
         "Wool Overshirt", "Striped Poplin Shirt", "Moleskin Overshirt", "Silk-Cotton Shirt", "Cuban Collar Shirt",
         "Heavy Twill Overshirt", "Garment-Dyed Shirt", "Herringbone Shirt"],
        ["Long-staple cotton", "Washed linen", "Cotton twill"],
        ["Regular fit, straight hem", "Relaxed fit, boxy through the body"], ["Portugal", "Italy", "Japan"]),
    "trousers": ("trouser", WAIST, (95, 195), ["ink", "navy", "stone", "olive", "chocolate", "charcoal", "ecru"],
        ["Pleated Wool Trouser", "Straight Chino", "Rigid Selvedge Jean", "Wide Fatigue Trouser", "Drawstring Linen Trouser",
         "Cord Trouser", "Tapered Chino", "Carpenter Trouser", "Flannel Trouser", "Painter Pant",
         "Relaxed Jean", "Gurkha Trouser", "Cotton Drill Trouser", "Seersucker Trouser", "Twill Easy Pant",
         "Moleskin Trouser"],
        ["Cotton twill", "Japanese selvedge denim", "Wool flannel", "Washed linen"],
        ["Straight leg, mid rise", "Relaxed through the thigh, tapered leg"], ["Japan", "Portugal", "Italy"]),
    "jersey": ("tee", ALPHA, (45, 110), ["white", "ink", "ecru", "navy", "olive", "charcoal", "stone", "rust"],
        ["Heavyweight Tee", "Pocket Tee", "Long-Sleeve Tee", "Loopback Sweatshirt", "Breton Top",
         "Pique Polo", "Mock Neck Tee", "Ringer Tee", "Hooded Sweatshirt", "Raglan Sweatshirt",
         "Slub Tee", "Henley Tee", "Rugby Shirt", "Waffle Long-Sleeve", "Crew Sweatshirt",
         "Merino Tee", "Boxy Tee", "Ribbed Tank"],
        ["Organic cotton jersey", "Loopback cotton fleece", "Merino jersey"],
        ["Regular fit", "Boxy fit, dropped shoulder"], ["Portugal", "Great Britain"]),
    "tailoring": ("blazer", ALPHA, (195, 520), ["navy", "charcoal", "stone", "ink", "chocolate", "olive"],
        ["Unstructured Blazer", "Wool Hopsack Jacket", "Linen Suit Jacket", "Tweed Sport Coat", "Double-Breasted Blazer",
         "Flannel Suit Jacket", "Cotton Travel Blazer", "Seersucker Jacket", "Corduroy Sport Coat", "Wool Gilet",
         "Cashmere Blend Blazer", "Twill Field Blazer", "Mohair Suit Jacket", "Knitted Blazer", "Herringbone Blazer",
         "Wool Bomber Jacket"],
        ["Italian wool", "Wool-cashmere blend", "Irish linen"],
        ["Soft shoulder, half lined", "Natural shoulder, unlined"], ["Italy", "Portugal"]),
}
CARE = {
    "outerwear": "Dry clean only.", "knitwear": "Hand wash cold, dry flat.", "shirts": "Machine wash 30°C.",
    "trousers": "Machine wash 30°C inside out.", "jersey": "Machine wash 30°C.", "tailoring": "Dry clean only.",
}
SHORT = {"XS": "XS", "S": "S", "M": "M", "L": "L", "XL": "XL", "XXL": "XXL"}

# Name keyword -> composition, so a "Cashmere Crew" is never described as cotton.
FIBRES = [
    ("cashmere", "Mongolian cashmere"), ("lambswool", "Geelong lambswool"), ("shetland", "Shetland wool"),
    ("alpaca", "Baby alpaca, merino"), ("mohair", "Brushed mohair, wool"), ("merino", "Extra-fine merino wool"),
    ("linen", "Washed linen"), ("selvedge", "Japanese selvedge denim"), ("jean", "Japanese selvedge denim"),
    ("denim", "Cotton denim"), ("waxed", "Waxed British cotton"), ("wool", "Virgin wool"), ("flannel", "Wool flannel"),
    ("tweed", "Donegal tweed"), ("corduroy", "Cotton corduroy"), ("cord ", "Cotton corduroy"), ("moleskin", "Cotton moleskin"),
    ("seersucker", "Cotton seersucker"), ("suede", "Goat suede"), ("silk", "Silk, cotton"), ("down", "Recycled nylon, responsibly sourced down"),
    ("ripstop", "Cotton-nylon ripstop"), ("oxford", "Cotton oxford"), ("poplin", "Cotton poplin"), ("chambray", "Cotton chambray"),
    ("herringbone", "Wool herringbone"), ("cotton", "Organic cotton"),
]
PROPER = ("Mongolian", "Geelong", "Shetland", "Japanese", "Donegal", "Italian", "Irish")


def fibre_for(name, fallback):
    low = name.lower() + " "
    for key, fibre in FIBRES:
        if key in low:
            return fibre
    return rng.choice(fallback)


def soft(material):
    return material if material.startswith(PROPER) else material[0].lower() + material[1:]


def lead(name):
    return ("An " if name[0].lower() in "aeiou" else "A ") + name.lower()


products = []
n = 0
for cat, (sil, sizes, (lo, hi), palette, names, mats, fits, origins) in CATS.items():
    for name in names:
        n += 1
        handle = name.lower().replace(" ", "-").replace("'", "")
        cols = rng.sample(palette, rng.choice([2, 3, 3, 4]))
        price = round(rng.randint(lo, hi) / 5) * 5
        stock = {}
        for c in cols:
            row = {}
            for s in sizes:
                r = rng.random()
                row[s] = 0 if r < 0.12 else (rng.randint(1, 3) if r < 0.3 else rng.randint(4, 30))
            stock[c] = row
        material = fibre_for(name, mats)
        products.append({
            "handle": handle,
            "style": f"TEL-{n:03d}",
            "title": name,
            "category": cat,
            "silhouette": sil,
            "price": price,
            "compare_at": None,
            "new": n % 7 == 0 or rng.random() < 0.12,
            "rank": rng.randint(1, 1000),
            "description": f"{lead(name)} in {soft(material.split(',')[0])}, made to be worn often. "
                           f"Quiet details, a considered fit and cloth that gets better with every wear.",
            "material": material,
            "fit": rng.choice(fits),
            "care": CARE[cat],
            "origin": f"Made in {rng.choice(origins)}",
            "colours": [{"handle": c, "name": COLOURS[c][0], "hex": COLOURS[c][1], "family": COLOURS[c][2]} for c in cols],
            "sizes": sizes,
            "stock": stock,
            "shopify_variant_ids": {},
        })

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({
    "_readme": [
        "SAMPLE DATA: 100 styles generated by tools/seed_catalog.py. Replace with the real range.",
        "One entry per style. stock is the size x colour variant matrix: stock[colour_handle][size] = units on hand.",
        "SKU per variant = <style>-<COLOUR>-<SIZE> (built automatically).",
        "shopify_variant_ids (optional): {\"<colour>/<size>\": 1234567890} enables real checkout links.",
        "Photos: assets/products/<handle>/<colour>-1.jpg (front), -2 (alternate angle), -3, -4. Cropped to 4:5 by the build.",
    ],
    "products": products,
}, indent=1, ensure_ascii=False) + "\n")
variants = sum(len(p["colours"]) * len(p["sizes"]) for p in products)
print(f"Wrote {len(products)} styles, {variants} variants -> {OUT}")
