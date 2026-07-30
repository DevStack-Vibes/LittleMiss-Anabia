"""
Optional helper to seed a few sample categories and products so the store
isn't empty on first run. Safe to run multiple times (skips if data exists).

Usage:
    python seed.py
"""
from app import app
from extensions import db
from models import Category, Product, ProductVariant
from utils import unique_slug


SAMPLE_CATEGORIES = [
    {"name": "Party Frocks", "description": "Twirl-worthy dresses for celebrations."},
    {"name": "Rompers", "description": "Comfy everyday rompers for little ones."},
    {"name": "Ethnic Wear", "description": "Traditional outfits for festive occasions."},
    {"name": "Accessories", "description": "Bows, headbands and finishing touches."},
]

SAMPLE_PRODUCTS = [
    {
        "name": "Pink Ruffle Layer Party Frock",
        "category": "Party Frocks",
        "price": 3200,
        "sale_price": 2699,
        "description": "A dreamy pink and mint layered tulle frock with a satin bow belt — "
                        "perfect for birthdays and family gatherings.",
        "featured": True,
        "sizes": ["1-2 Years", "2-3 Years", "3-4 Years", "4-5 Years"],
    },
    {
        "name": "Mint Polka Puff Sleeve Romper",
        "category": "Rompers",
        "price": 1899,
        "sale_price": None,
        "description": "Soft cotton romper with puff sleeves and a cute bow belt, "
                        "designed for all-day comfort.",
        "featured": True,
        "sizes": ["0-6 Months", "6-12 Months", "1-2 Years"],
    },
    {
        "name": "Yellow Heart Print Sundress",
        "category": "Party Frocks",
        "price": 2100,
        "sale_price": None,
        "description": "Lightweight cotton sundress with heart prints and lace trim hem.",
        "featured": False,
        "sizes": ["2-3 Years", "3-4 Years", "4-5 Years", "5-6 Years"],
    },
    {
        "name": "Pastel Bow Hair Clip Set (3pc)",
        "category": "Accessories",
        "price": 650,
        "sale_price": None,
        "description": "A set of three matching pastel bow hair clips — pink, mint and gold.",
        "featured": False,
        "sizes": [],
    },
]


def run():
    with app.app_context():
        cat_map = {}
        for i, c in enumerate(SAMPLE_CATEGORIES):
            existing = Category.query.filter_by(name=c["name"]).first()
            if existing:
                cat_map[c["name"]] = existing
                continue
            cat = Category(
                name=c["name"], description=c["description"], sort_order=i,
                slug=unique_slug(Category, c["name"]),
            )
            db.session.add(cat)
            db.session.flush()
            cat_map[c["name"]] = cat

        for p in SAMPLE_PRODUCTS:
            if Product.query.filter_by(name=p["name"]).first():
                continue
            product = Product(
                name=p["name"],
                slug=unique_slug(Product, p["name"]),
                description=p["description"],
                category_id=cat_map[p["category"]].id,
                price=p["price"],
                sale_price=p["sale_price"],
                is_featured=p["featured"],
                is_active=True,
            )
            db.session.add(product)
            db.session.flush()
            for size in p["sizes"]:
                db.session.add(ProductVariant(product_id=product.id, size=size, stock_qty=15))

        db.session.commit()
        print("Sample categories & products seeded (no images attached — add photos from the admin panel).")


if __name__ == "__main__":
    run()
