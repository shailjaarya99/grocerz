from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import os
import io
import base64
import hmac
import hashlib
import time
import qrcode

app = Flask(__name__)
app.secret_key = "dev-secret"  # change later

# Path to Excel inventory file
DATA_PATH = os.path.join("data", "inventory.xlsx")

# Secret key for signing QR payloads
QR_SECRET = b"change-this-secret"

# ----------------------
# LOAD PRODUCTS FUNCTION
# ----------------------


def load_products():
    df = pd.read_excel(DATA_PATH, engine="openpyxl")

    for col in ["sku", "name", "brand", "size", "color", "ingredient_tags", "aisle"]:
        df[col] = df[col].astype(str).fillna("").str.strip()
    df["price"] = df["price"].astype(float)
    df["stock_qty"] = df["stock_qty"].astype(int)
    return df


def stock_badge(qty):
    if qty <= 0:
        return "Out"
    elif qty < 10:
        return "Low"
    else:
        return "In stock"

# ----------------------
# QR HELPER FUNCTIONS
# ----------------------


def sign_payload(order_id, amount):
    paise = int(round(amount * 100))
    msg = f"order:{order_id}:{paise}".encode()
    sig = hmac.new(QR_SECRET, msg, hashlib.sha256).hexdigest()
    return f"{msg.decode()}:{sig}"


def qr_base64(payload):
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

# ----------------------
# ROUTES
# ----------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/products")
def products():
    q = request.args.get("q", "").lower().strip()
    brand = request.args.get("brand", "").lower().strip()
    df = load_products()

    if q:
        mask = df["name"].str.lower().str.contains(
            q) | df["sku"].str.lower().str.contains(q)
        df = df[mask]

    if brand:
        df = df[df["brand"].str.lower().str.contains(brand)]

    df["availability"] = df["stock_qty"].apply(stock_badge)
    return render_template("products.html", products=df.to_dict(orient="records"), q=q, brand=brand)

# ✅ Excel upload route (fixes 'upload' error)


@app.route("/admin/upload", methods=["POST"])
def upload():
    file = request.files.get("excel")
    if not file:
        flash("Please select an Excel file.")
        return redirect(url_for("index"))

    os.makedirs("data", exist_ok=True)
    file.save(DATA_PATH)
    flash("Inventory updated successfully!")
    return redirect(url_for("products"))

# ✅ Buy product and show receipt with QR code


@app.route("/buy", methods=["POST"])
def buy():
    sku = request.form.get("sku", "").strip()
    qty = int(request.form.get("qty", "1"))

    df = load_products()
    row = df[df["sku"] == sku]
    if row.empty:
        flash("Product not found.")
        return redirect(url_for("products"))

    product = row.iloc[0].to_dict()
    if product["stock_qty"] < qty:
        flash("Not enough stock.")
        return redirect(url_for("products"))

    total = product["price"] * qty
    order_id = int(time.time())

    payload = sign_payload(order_id, total)
    qr_data_url = qr_base64(payload)

    receipt = {
        "order_id": order_id,
        "items": [{
            "sku": product["sku"],
            "name": product["name"],
            "qty": qty,
            "price_each": product["price"],
            "line_total": total
        }],
        "total": total,
        "qr_payload": payload,
        "qr_data_url": qr_data_url
    }

    return render_template("receipt.html", receipt=receipt)


# ----------------------
# RUN SERVER
# ----------------------
if __name__ == "__main__":
    print("✨ Grocerz is running at http://127.0.0.1:5000 ✨")
    app.run(debug=True)
