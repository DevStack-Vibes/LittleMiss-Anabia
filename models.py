import random
import string
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


def _gen_order_number():
    stamp = datetime.utcnow().strftime("%y%m%d")
    rand = "".join(random.choices(string.digits, k=4))
    return f"LMA-{stamp}-{rand}"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(90), unique=True, nullable=False)
    description = db.Column(db.String(255))
    image = db.Column(db.String(255))  # filename in uploads/products
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    products = db.relationship("Product", backref="category", lazy=True)

    def __repr__(self):
        return f"<Category {self.name}>"


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(170), unique=True, nullable=False)
    description = db.Column(db.Text)
    sku = db.Column(db.String(50))
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    price = db.Column(db.Float, nullable=False)
    sale_price = db.Column(db.Float, nullable=True)  # if set and < price, shows as discounted

    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = db.relationship(
        "ProductImage", backref="product", lazy=True, cascade="all, delete-orphan",
        order_by="ProductImage.sort_order"
    )
    variants = db.relationship(
        "ProductVariant", backref="product", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def display_price(self):
        if self.sale_price and self.sale_price < self.price:
            return self.sale_price
        return self.price

    @property
    def is_on_sale(self):
        return bool(self.sale_price and self.sale_price < self.price)

    @property
    def discount_percent(self):
        if self.is_on_sale:
            return round((1 - (self.sale_price / self.price)) * 100)
        return 0

    @property
    def total_stock(self):
        if self.variants:
            return sum(v.stock_qty for v in self.variants)
        return 0

    @property
    def in_stock(self):
        return self.total_stock > 0

    @property
    def primary_image(self):
        return self.images[0].filename if self.images else None

    def __repr__(self):
        return f"<Product {self.name}>"


class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    sort_order = db.Column(db.Integer, default=0)


class ProductVariant(db.Model):
    __tablename__ = "product_variants"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    size = db.Column(db.String(30), nullable=False, default="Standard")
    color = db.Column(db.String(40), nullable=True)
    stock_qty = db.Column(db.Integer, default=0)

    @property
    def label(self):
        parts = [p for p in [self.size, self.color] if p]
        return " / ".join(parts) if parts else "Standard"


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(30), unique=True, default=_gen_order_number)

    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    notes = db.Column(db.String(255))

    payment_method = db.Column(db.String(30), default="COD")
    status = db.Column(db.String(30), default="Pending")
    # Pending -> Confirmed -> Packed -> Shipped -> Delivered  (or Cancelled at any point)

    subtotal = db.Column(db.Float, nullable=False, default=0)
    shipping_fee = db.Column(db.Float, nullable=False, default=0)
    total = db.Column(db.Float, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")

    STATUS_FLOW = ["Pending", "Confirmed", "Packed", "Shipped", "Delivered"]
    STATUS_BADGE = {
        "Pending": "badge-pending",
        "Confirmed": "badge-confirmed",
        "Packed": "badge-packed",
        "Shipped": "badge-shipped",
        "Delivered": "badge-delivered",
        "Cancelled": "badge-cancelled",
    }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)

    product_name = db.Column(db.String(150), nullable=False)
    variant_label = db.Column(db.String(80))
    image = db.Column(db.String(255))
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class AdminUser(UserMixin, db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_super = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class SiteSetting(db.Model):
    """Simple key/value store for editable homepage content (hero text, banner, etc)."""
    __tablename__ = "site_settings"

    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text)

    @staticmethod
    def get(key, default=""):
        row = SiteSetting.query.get(key)
        return row.value if row else default

    @staticmethod
    def set(key, value):
        row = SiteSetting.query.get(key)
        if row:
            row.value = value
        else:
            row = SiteSetting(key=key, value=value)
            db.session.add(row)
