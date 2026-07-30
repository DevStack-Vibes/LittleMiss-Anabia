# Little Miss by Anabia — E-Commerce Store + Admin Panel

A complete Flask e-commerce site for a kids' clothing brand, themed around your
logo's pink / mint / cream palette. Cash on Delivery checkout, full product &
order management from a custom admin panel.

## Features

**Storefront**
- Home page with hero banner, shop-by-category, best sellers, new arrivals, trust badges, FAQ
- Shop-all page with category filter + sort (newest / price)
- Product detail page with photo gallery, size selector, live stock indicator
- Session-based cart (add / update qty / remove)
- Checkout with Cash on Delivery (name, phone, address, city, notes)
- Order confirmation page + "Track My Order" (by order number + phone)
- Fully responsive, mobile-friendly nav

**Admin Panel** (`/admin`)
- Secure login (Flask-Login), change password
- Dashboard: total orders, revenue, pending orders, low-stock alerts, recent orders
- Products: create/edit/delete, multiple photos, categories, price + sale price,
  size/color variants with per-size stock quantities, featured toggle
- Categories: create/edit/delete with image
- Orders: list + filter by status, detail view, update status
  (Pending → Confirmed → Packed → Shipped → Delivered, or Cancelled)
- Homepage hero text editable from Settings

## Tech stack
Flask, Flask-SQLAlchemy (SQLite), Flask-Login, Jinja2, vanilla CSS/JS (no build step).

## 1. Setup

```bash
cd littlemiss
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Run the app

```bash
python app.py
```

The site will be available at **http://localhost:5000**
The database (`instance/littlemiss.db`) and default admin login are created automatically on first run.

**Default admin login** (also printed in the terminal on first run):
```
URL:      http://localhost:5000/admin/login
Username: admin
Password: LittleMiss@2026
```
⚠️ Please log in and change this password immediately from **Admin → Password**.

## 3. (Optional) Add sample products

To preview the store with a few sample categories/products before you upload your real catalog:

```bash
python seed.py
```
This only adds data if it doesn't already exist, and skips images (add real photos from the admin panel).

## 4. Add your real catalog

1. Log in to `/admin`
2. Go to **Categories** → add your categories (Frocks, Rompers, Ethnic Wear, Accessories, etc.) with an image each
3. Go to **Products** → **Add New Product** for each item:
   - Name, category, price (and sale price if discounted)
   - Upload one or more photos
   - Add sizes with stock quantity (e.g. "2-3 Years" → 10 in stock)
4. Orders placed by customers appear instantly under **Orders**

## 5. Store settings

Edit contact info, WhatsApp link, social links, and shipping fee in `config.py`:
```python
STORE_PHONE = "+92 3XX XXXXXXX"
STORE_EMAIL = "hello@littlemiss-anabia.com"
STORE_WHATSAPP = "https://wa.me/923000000000"
STORE_INSTAGRAM = "https://instagram.com/littlemiss.anabia"
STORE_FACEBOOK = "https://facebook.com/littlemiss.anabia"
SHIPPING_FEE = 250
FREE_SHIPPING_THRESHOLD = 4000
```
Homepage hero headline/subtext can be edited live from **Admin → Settings**.

## 6. Deploying to a real server

For production:
1. Set a strong `SECRET_KEY` environment variable
2. Run behind Gunicorn + Nginx (or any WSGI host), e.g.:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 app:app
   ```
3. Point `DATABASE_URL` to a proper database (PostgreSQL/MySQL) if you expect real traffic —
   SQLite is fine for getting started and moderate traffic.
4. Serve `/static/uploads` via your web server or a CDN for speed.

## Project structure

```
littlemiss/
├── app.py                  # Application factory / entry point
├── config.py                # Store settings & config
├── extensions.py             # db, login_manager
├── models.py                 # Category, Product, Variant, Order, AdminUser, SiteSetting
├── utils.py                   # slugs, image upload, cart helpers
├── seed.py                     # optional sample data
├── requirements.txt
├── routes/
│   ├── storefront.py        # customer-facing routes
│   └── admin.py               # admin panel routes
├── templates/
│   ├── base.html, index.html, shop.html, product.html,
│   │   cart.html, checkout.html, order_success.html, track_order.html
│   ├── partials/            # navbar, footer, product card
│   └── admin/                 # admin panel templates
└── static/
    ├── css/style.css (storefront) & admin.css (admin panel)
    ├── js/main.js
    ├── img/logo.jpeg
    └── uploads/products/    # uploaded product & category photos
```

## Notes

- Cart is stored in the browser session (no login required to shop) — this is standard for small COD-based stores.
- Stock is deducted per size variant only when an order is placed at checkout.
- This is a solid production-ready foundation. If you'd like SMS/WhatsApp order notifications,
  a customer accounts/login system, discount codes, or a payment gateway added later, those can be layered on top.
