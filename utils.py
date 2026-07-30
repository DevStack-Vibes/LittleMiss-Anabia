import os
import re
import uuid

from flask import current_app, session
from werkzeug.utils import secure_filename

from extensions import db
from models import Product, ProductVariant


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or uuid.uuid4().hex[:8]


def unique_slug(model, name, existing_id=None):
    base = slugify(name)
    slug = base
    i = 2
    query = model.query.filter_by(slug=slug)
    if existing_id:
        query = query.filter(model.id != existing_id)
    while query.first() is not None:
        slug = f"{base}-{i}"
        i += 1
        query = model.query.filter_by(slug=slug)
        if existing_id:
            query = query.filter(model.id != existing_id)
    return slug


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def save_product_image(file_storage):
    """Save an uploaded image and return its stored filename, or None."""
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, filename))
    return filename


# ---------- Cart helpers (session based) ----------
# Cart stored in session as: {"<product_id>:<variant_id>": {"qty": int}}

def _cart():
    return session.setdefault("cart", {})


def cart_key(product_id, variant_id):
    return f"{product_id}:{variant_id or 0}"


def add_to_cart(product_id, variant_id, qty=1):
    cart = _cart()
    key = cart_key(product_id, variant_id)
    if key in cart:
        cart[key]["qty"] += qty
    else:
        cart[key] = {"qty": qty}
    session.modified = True


def update_cart_qty(key, qty):
    cart = _cart()
    if key in cart:
        if qty <= 0:
            cart.pop(key)
        else:
            cart[key]["qty"] = qty
    session.modified = True


def remove_from_cart(key):
    cart = _cart()
    cart.pop(key, None)
    session.modified = True


def clear_cart():
    session["cart"] = {}
    session.modified = True


def get_cart_details():
    """Resolve the session cart into a list of rich line-item dicts, skipping stale entries."""
    cart = _cart()
    items = []
    subtotal = 0.0
    stale_keys = []

    for key, data in cart.items():
        try:
            product_id_str, variant_id_str = key.split(":")
            product_id = int(product_id_str)
            variant_id = int(variant_id_str)
        except ValueError:
            stale_keys.append(key)
            continue

        product = Product.query.get(product_id)
        if not product or not product.is_active:
            stale_keys.append(key)
            continue

        variant = ProductVariant.query.get(variant_id) if variant_id else None
        qty = max(1, int(data.get("qty", 1)))
        unit_price = product.display_price
        line_total = unit_price * qty

        items.append({
            "key": key,
            "product": product,
            "variant": variant,
            "qty": qty,
            "unit_price": unit_price,
            "line_total": line_total,
        })
        subtotal += line_total

    if stale_keys:
        for k in stale_keys:
            cart.pop(k, None)
        session.modified = True

    return items, subtotal


def cart_count():
    cart = _cart()
    return sum(int(v.get("qty", 1)) for v in cart.values())
