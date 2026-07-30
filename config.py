import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "littlemiss-anabia-dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'littlemiss.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "products")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
    MAX_CONTENT_LENGTH = 12 * 1024 * 1024  # 12 MB max upload

    # Store info shown across the site / used on invoices
    STORE_NAME = "Little Miss by Anabia"
    STORE_TAGLINE = "Twirl-worthy fashion for little princesses"
    STORE_PHONE = "+92 3XX XXXXXXX"
    STORE_EMAIL = "hello@littlemiss-anabia.com"
    STORE_WHATSAPP = "https://wa.me/923000000000"
    STORE_INSTAGRAM = "https://instagram.com/littlemiss.anabia"
    STORE_FACEBOOK = "https://facebook.com/littlemiss.anabia"
    STORE_ADDRESS = "Sialkot, Punjab, Pakistan"
    CURRENCY_SYMBOL = "Rs."
    SHIPPING_FEE = 250  # flat COD shipping fee within Pakistan, in currency units
    FREE_SHIPPING_THRESHOLD = 4000
