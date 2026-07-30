from flask import (
    Blueprint, render_template, redirect, url_for, request, flash,
    current_app, abort, session
)

from extensions import db
from models import Product, Category, ProductVariant, Order, OrderItem, SiteSetting
from utils import (
    add_to_cart, update_cart_qty, remove_from_cart, clear_cart,
    get_cart_details, cart_key
)

shop_bp = Blueprint("shop", __name__)


@shop_bp.route("/")
def index():
    featured = (
        Product.query.filter_by(is_active=True, is_featured=True)
        .order_by(Product.created_at.desc())
        .limit(8)
        .all()
    )
    new_arrivals = (
        Product.query.filter_by(is_active=True)
        .order_by(Product.created_at.desc())
        .limit(8)
        .all()
    )
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).limit(6).all()
    hero_headline = SiteSetting.get("hero_headline", "Little Miss by Anabia")
    hero_sub = SiteSetting.get(
        "hero_sub",
        "Twirl-worthy dresses, rompers &amp; ethnic wear for your little princess — handpicked with love."
    )
    return render_template(
        "index.html",
        featured=featured,
        new_arrivals=new_arrivals,
        categories=categories,
        hero_headline=hero_headline,
        hero_sub=hero_sub,
    )


@shop_bp.route("/shop")
def shop_all():
    category_slug = request.args.get("category")
    sort = request.args.get("sort", "new")
    query = Product.query.filter_by(is_active=True)

    active_category = None
    if category_slug:
        active_category = Category.query.filter_by(slug=category_slug).first_or_404()
        query = query.filter_by(category_id=active_category.id)

    if sort == "price_low":
        query = query.order_by(Product.price.asc())
    elif sort == "price_high":
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    products = query.all()
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
    return render_template(
        "shop.html",
        products=products,
        categories=categories,
        active_category=active_category,
        sort=sort,
    )


@shop_bp.route("/product/<slug>")
def product_detail(slug):
    product = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
    related = (
        Product.query.filter(
            Product.category_id == product.category_id,
            Product.id != product.id,
            Product.is_active.is_(True),
        )
        .limit(4)
        .all()
    )
    return render_template("product.html", product=product, related=related)


@shop_bp.route("/cart/add", methods=["POST"])
def cart_add():
    product_id = request.form.get("product_id", type=int)
    variant_id = request.form.get("variant_id", type=int)
    qty = max(1, request.form.get("qty", 1, type=int))

    product = Product.query.get_or_404(product_id)

    if product.variants:
        variant = ProductVariant.query.get(variant_id) if variant_id else None
        if not variant or variant.product_id != product.id:
            flash("Please select a size before adding to cart.", "warning")
            return redirect(url_for("shop.product_detail", slug=product.slug))
        if variant.stock_qty < qty:
            flash(f"Only {variant.stock_qty} left in that size. Please adjust the quantity.", "warning")
            return redirect(url_for("shop.product_detail", slug=product.slug))

    add_to_cart(product_id, variant_id, qty)
    flash(f'"{product.name}" added to your cart 💕', "success")
    return redirect(request.referrer or url_for("shop.product_detail", slug=product.slug))


@shop_bp.route("/cart")
def cart_view():
    items, subtotal = get_cart_details()
    shipping_fee = 0 if (subtotal >= current_app.config["FREE_SHIPPING_THRESHOLD"] or subtotal == 0) else current_app.config["SHIPPING_FEE"]
    total = subtotal + shipping_fee
    return render_template("cart.html", items=items, subtotal=subtotal, shipping_fee=shipping_fee, total=total)


@shop_bp.route("/cart/update", methods=["POST"])
def cart_update():
    key = request.form.get("key")
    qty = request.form.get("qty", 1, type=int)
    update_cart_qty(key, qty)
    return redirect(url_for("shop.cart_view"))


@shop_bp.route("/cart/remove/<path:key>")
def cart_remove(key):
    remove_from_cart(key)
    flash("Item removed from cart.", "info")
    return redirect(url_for("shop.cart_view"))


@shop_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, subtotal = get_cart_details()
    if not items:
        flash("Your cart is empty — add something pretty first!", "warning")
        return redirect(url_for("shop.shop_all"))

    shipping_fee = 0 if subtotal >= current_app.config["FREE_SHIPPING_THRESHOLD"] else current_app.config["SHIPPING_FEE"]
    total = subtotal + shipping_fee

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        notes = request.form.get("notes", "").strip()

        if not name or not phone or not address or not city:
            flash("Please fill in your name, phone, address and city.", "warning")
            return render_template(
                "checkout.html", items=items, subtotal=subtotal,
                shipping_fee=shipping_fee, total=total, form=request.form
            )

        # Re-validate stock at the moment of order placement
        for item in items:
            if item["variant"] and item["variant"].stock_qty < item["qty"]:
                flash(
                    f'Sorry, "{item["product"].name}" ({item["variant"].label}) only has '
                    f'{item["variant"].stock_qty} left in stock.', "danger"
                )
                return redirect(url_for("shop.cart_view"))

        order = Order(
            customer_name=name, phone=phone, email=email, address=address,
            city=city, notes=notes, subtotal=subtotal, shipping_fee=shipping_fee,
            total=total, payment_method="COD", status="Pending",
        )
        db.session.add(order)
        db.session.flush()  # get order.id before commit

        for item in items:
            product = item["product"]
            variant = item["variant"]
            oi = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                variant_label=variant.label if variant else None,
                image=product.primary_image,
                unit_price=item["unit_price"],
                quantity=item["qty"],
            )
            db.session.add(oi)
            if variant:
                variant.stock_qty = max(0, variant.stock_qty - item["qty"])

        db.session.commit()
        clear_cart()

        return redirect(url_for("shop.order_success", order_number=order.order_number))

    return render_template("checkout.html", items=items, subtotal=subtotal, shipping_fee=shipping_fee, total=total, form={})


@shop_bp.route("/order/success/<order_number>")
def order_success(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template("order_success.html", order=order)


@shop_bp.route("/track-order", methods=["GET", "POST"])
def track_order():
    order = None
    searched = False
    if request.method == "POST":
        searched = True
        order_number = request.form.get("order_number", "").strip()
        phone = request.form.get("phone", "").strip()
        order = Order.query.filter_by(order_number=order_number, phone=phone).first()
        if not order:
            flash("We couldn't find an order with that number and phone combination.", "warning")
    return render_template("track_order.html", order=order, searched=searched)
