from flask import Flask, jsonify, request
import pandas as pd

app = Flask(__name__)

# Load the Excel file
def load_data():
    return pd.read_excel("grocerz excel sheet.xlsx")

@app.route("/")
def home():
    return "Grocerz Backend Running Successfully!"

@app.route("/items", methods=["GET"])
def get_items():
    df = load_data()

    # Read filters from URL
    category = request.args.get("category")      # bakery, dairy, children, pets, etc.
    subcategory = request.args.get("subcategory")              # example: cake, milk, chocolate
    Products = request.args.get("type")       # small, big, packet, premium
    availability = request.args.get("availability")  # in-store, out-of-store

    # Apply filters one by one if they exist
    if category:
        df = df[df["category"].str.lower() == category.lower()]

    if subcategory :
        df = df[df["subcategory"].str.lower() == subcategory.lower()]

    if Products:
        df = df[df["Products"].str.lower() == Products.lower()]

    if availability:
        df = df[df["availability"].str.lower() == availability.lower()]

    # Convert to list of JSON objects
    results = df.to_dict(orient="records")
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
