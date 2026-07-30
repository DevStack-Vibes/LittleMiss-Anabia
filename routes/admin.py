import os
from datetime import datetime, timedelta

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, current_app
)
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import Product, Category, ProductImage, ProductVariant, Order, AdminUser, SiteSetting
from utils import unique_slug, save_product_image

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


# ---------------------------------------------------------------- auth ----
@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = AdminUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(request.args.get("next") or url_for("admin.dashboard"))
        flash("Invalid username or password.", "danger")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for("admin.login"))


@admin_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        confirm_pw = request.form.get("confirm_password", "")

        if not current_user.check_password(current_pw):
            flash("Current password is incorrect.", "danger")
        elif len(new_pw) < 6:
            flash("New password must be at least 6 characters.", "warning")
        elif new_pw != confirm_pw:
            flash("New password and confirmation don't match.", "warning")
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            flash("Password updated successfully.", "success")
            return redirect(url_for("admin.dashboard"))

    return render_template("admin/change_password.html")


# ----------------------------------------------------------- dashboard ----
@admin_bp.route("/")
@login_required
def dashboard():
    total_products = Product.query.count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status="Pending").count()
    revenue = db.session.query(db.func.coalesce(db.func.sum(Order.total), 0.0)).filter(
        Order.status != "Cancelled"
    ).scalar()

    low_stock = (
        ProductVariant.query.filter(ProductVariant.stock_qty <= 3, ProductVariant.stock_qty > 0)
        .join(Product)
        .filter(Product.is_active.is_(True))
        .limit(8)
        .all()
    )
    out_of_stock_variants = ProductVariant.query.filter(ProductVariant.stock_qty <= 0).count()

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()

    week_ago = datetime.utcnow() - timedelta(days=7)
    orders_this_week = Order.query.filter(Order.created_at >= week_ago).count()

    return render_template(
        "admin/dashboard.html",
        total_products=total_products,
        total_orders=total_orders,
        pending_orders=pending_orders,
        revenue=revenue,
        low_stock=low_stock,
        out_of_stock_variants=out_of_stock_variants,
        recent_orders=recent_orders,
        orders_this_week=orders_this_week,
    )


# ------------------------------------------------------------ products ----
@admin_bp.route("/products")
@login_required
def products():
    q = request.args.get("q", "").strip()
    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    items = query.order_by(Product.created_at.desc()).all()
    return render_template("admin/products.html", products=items, q=q)


@admin_bp.route("/products/new", methods=["GET", "POST"])
@login_required
def product_new():
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        product = Product(
            name=request.form.get("name", "").strip(),
            description=request.form.get("description", "").strip(),
            sku=request.form.get("sku", "").strip(),
            category_id=request.form.get("category_id", type=int) or None,
            price=request.form.get("price", type=float) or 0,
            sale_price=request.form.get("sale_price", type=float) or None,
            is_featured=bool(request.form.get("is_featured")),
            is_active=bool(request.form.get("is_active", "on")),
        )
        product.slug = unique_slug(Product, product.name)
        db.session.add(product)
        db.session.flush()

        _save_variants_from_form(product)
        _save_images_from_form(product)

        db.session.commit()
        flash(f'Product "{product.name}" created.', "success")
        return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", product=None, categories=categories)


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        new_name = request.form.get("name", "").strip()
        if new_name != product.name:
            product.slug = unique_slug(Product, new_name, existing_id=product.id)
        product.name = new_name
        product.description = request.form.get("description", "").strip()
        product.sku = request.form.get("sku", "").strip()
        product.category_id = request.form.get("category_id", type=int) or None
        product.price = request.form.get("price", type=float) or 0
        product.sale_price = request.form.get("sale_price", type=float) or None
        product.is_featured = bool(request.form.get("is_featured"))
        product.is_active = bool(request.form.get("is_active"))

        # remove selected images
        remove_ids = request.form.getlist("remove_image")
        if remove_ids:
            for img in ProductImage.query.filter(ProductImage.id.in_(remove_ids)).all():
                path = os.path.join(current_app.config["UPLOAD_FOLDER"], img.filename)
                if os.path.exists(path):
                    os.remove(path)
                db.session.delete(img)

        # remove selected variants
        remove_variant_ids = request.form.getlist("remove_variant")
        if remove_variant_ids:
            ProductVariant.query.filter(ProductVariant.id.in_(remove_variant_ids)).delete(
                synchronize_session=False
            )

        _update_existing_variants_from_form(request.form)
        _save_variants_from_form(product, prefix="new_")
        _save_images_from_form(product)

        db.session.commit()
        flash(f'Product "{product.name}" updated.', "success")
        return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", product=product, categories=categories)


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@login_required
def product_delete(product_id):
    product = Product.query.get_or_404(product_id)
    for img in product.images:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], img.filename)
        if os.path.exists(path):
            os.remove(path)
    name = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{name}" deleted.', "info")
    return redirect(url_for("admin.products"))


def _save_variants_from_form(product, prefix=""):
    sizes = request.form.getlist(f"{prefix}variant_size")
    colors = request.form.getlist(f"{prefix}variant_color")
    stocks = request.form.getlist(f"{prefix}variant_stock")
    for size, color, stock in zip(sizes, colors, stocks):
        if not size and not color:
            continue
        variant = ProductVariant(
            product_id=product.id,
            size=size or "Standard",
            color=color or None,
            stock_qty=int(stock) if str(stock).strip().isdigit() else 0,
        )
        db.session.add(variant)


def _update_existing_variants_from_form(form):
    ids = form.getlist("variant_id")
    sizes = form.getlist("variant_size_existing")
    colors = form.getlist("variant_color_existing")
    stocks = form.getlist("variant_stock_existing")
    for vid, size, color, stock in zip(ids, sizes, colors, stocks):
        variant = ProductVariant.query.get(int(vid))
        if variant:
            variant.size = size or "Standard"
            variant.color = color or None
            variant.stock_qty = int(stock) if str(stock).strip().isdigit() else 0


def _save_images_from_form(product):
    files = request.files.getlist("images")
    next_order = len(product.images)
    for f in files:
        filename = save_product_image(f)
        if filename:
            db.session.add(ProductImage(product_id=product.id, filename=filename, sort_order=next_order))
            next_order += 1


# ----------------------------------------------------------- categories ----
@admin_bp.route("/categories")
@login_required
def categories():
    items = Category.query.order_by(Category.sort_order).all()
    return render_template("admin/categories.html", categories=items)


@admin_bp.route("/categories/new", methods=["GET", "POST"])
@login_required
def category_new():
    if request.method == "POST":
        cat = Category(
            name=request.form.get("name", "").strip(),
            description=request.form.get("description", "").strip(),
            sort_order=request.form.get("sort_order", type=int) or 0,
            is_active=bool(request.form.get("is_active", "on")),
        )
        cat.slug = unique_slug(Category, cat.name)
        image = save_product_image(request.files.get("image"))
        if image:
            cat.image = image
        db.session.add(cat)
        db.session.commit()
        flash(f'Category "{cat.name}" created.', "success")
        return redirect(url_for("admin.categories"))
    return render_template("admin/category_form.html", category=None)


@admin_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@login_required
def category_edit(category_id):
    cat = Category.query.get_or_404(category_id)
    if request.method == "POST":
        new_name = request.form.get("name", "").strip()
        if new_name != cat.name:
            cat.slug = unique_slug(Category, new_name, existing_id=cat.id)
        cat.name = new_name
        cat.description = request.form.get("description", "").strip()
        cat.sort_order = request.form.get("sort_order", type=int) or 0
        cat.is_active = bool(request.form.get("is_active"))
        image = save_product_image(request.files.get("image"))
        if image:
            cat.image = image
        db.session.commit()
        flash(f'Category "{cat.name}" updated.', "success")
        return redirect(url_for("admin.categories"))
    return render_template("admin/category_form.html", category=cat)


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@login_required
def category_delete(category_id):
    cat = Category.query.get_or_404(category_id)
    if cat.products:
        flash("Can't delete a category that still has products. Move or delete those products first.", "warning")
        return redirect(url_for("admin.categories"))
    db.session.delete(cat)
    db.session.commit()
    flash("Category deleted.", "info")
    return redirect(url_for("admin.categories"))


# ---------------------------------------------------------------- orders ----
@admin_bp.route("/orders")
@login_required
def orders():
    status = request.args.get("status", "")
    query = Order.query
    if status:
        query = query.filter_by(status=status)
    items = query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=items, status=status)


@admin_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("admin/order_detail.html", order=order)


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@login_required
def order_update_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status")
    valid = Order.STATUS_FLOW + ["Cancelled"]
    if new_status in valid:
        order.status = new_status
        db.session.commit()
        flash(f"Order {order.order_number} marked as {new_status}.", "success")
    return redirect(url_for("admin.order_detail", order_id=order.id))


# -------------------------------------------------------------- settings ----
@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        SiteSetting.set("hero_headline", request.form.get("hero_headline", "").strip())
        SiteSetting.set("hero_sub", request.form.get("hero_sub", "").strip())
        db.session.commit()
        flash("Homepage settings updated.", "success")
        return redirect(url_for("admin.settings"))

    hero_headline = SiteSetting.get("hero_headline", "Little Miss by Anabia")
    hero_sub = SiteSetting.get(
        "hero_sub",
        "Twirl-worthy dresses, rompers &amp; ethnic wear for your little princess — handpicked with love."
    )
    return render_template("admin/settings.html", hero_headline=hero_headline, hero_sub=hero_sub)
