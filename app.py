import os

from flask import Flask

from config import Config
from extensions import db, login_manager
from models import AdminUser
from utils import cart_count


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from routes.storefront import shop_bp
    from routes.admin import admin_bp

    app.register_blueprint(shop_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @login_manager.user_loader
    def load_user(user_id):
        return AdminUser.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        from models import Category
        return {
            "STORE_NAME": app.config["STORE_NAME"],
            "STORE_TAGLINE": app.config["STORE_TAGLINE"],
            "STORE_PHONE": app.config["STORE_PHONE"],
            "STORE_EMAIL": app.config["STORE_EMAIL"],
            "STORE_WHATSAPP": app.config["STORE_WHATSAPP"],
            "STORE_INSTAGRAM": app.config["STORE_INSTAGRAM"],
            "STORE_FACEBOOK": app.config["STORE_FACEBOOK"],
            "CURRENCY": app.config["CURRENCY_SYMBOL"],
            "nav_categories": Category.query.filter_by(is_active=True).order_by(Category.sort_order).all(),
            "cart_item_count": cart_count(),
        }

    with app.app_context():
        db.create_all()
        _ensure_admin_seed()

    return app


def _ensure_admin_seed():
    """Create a default admin login on first run so the panel is never locked out."""
    if AdminUser.query.count() == 0:
        admin = AdminUser(username="admin", is_super=True)
        admin.set_password("LittleMiss@2026")
        db.session.add(admin)
        db.session.commit()
        print("=" * 60)
        print(" Created default admin login:")
        print("   username: admin")
        print("   password: LittleMiss@2026")
        print(" Please change this password after logging in!")
        print("=" * 60)


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
