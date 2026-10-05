import os
import requests
import json
from pathlib import Path

KEY_FILE = Path(__file__).parent / "rapidapi_key.txt"


def load_api_key():
    # RAPIDAPI_KEY env var wins; otherwise read the git-ignored rapidapi_key.txt
    key = os.environ.get("RAPIDAPI_KEY")
    if key:
        return key.strip()
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    raise SystemExit(f"No RapidAPI key found. Put it in {KEY_FILE} or set RAPIDAPI_KEY.")

# ---------------------------------------------------------
# 1. RapidAPI lookup (returns lowest price, sold count, and title)
# ---------------------------------------------------------
def get_price_data_from_api(upc, api_key):
    url = "https://ebay-average-selling-price.p.rapidapi.com/findCompletedItems"

    payload = {
        "keywords": upc,
        "max_search_results": "120",
        "remove_outliers": "true",
        "site_id": "0"
    }

    headers = {
        "content-type": "application/json",
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "ebay-average-selling-price.p.rapidapi.com"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        # -----------------------------
        # Extract lowest sold price
        # -----------------------------
        lowest_price = None

        # Preferred: API-provided min_price
        if "min_price" in data and data["min_price"]:
            lowest_price = data["min_price"]

        # Fallback: compute from products[]
        elif "products" in data and isinstance(data["products"], list):
            prices = [
                item.get("sale_price")
                for item in data["products"]
                if item.get("sale_price")
            ]
            if prices:
                lowest_price = min(prices)

        # -----------------------------
        # Extract sold count
        # -----------------------------
        sold_count = data.get("total_results", None)

        # -----------------------------
        # Extract Title (product description)
        # -----------------------------
        title = None

        # Preferred: products[]
        if "products" in data and isinstance(data["products"], list) and len(data["products"]) > 0:
            title = data["products"][0].get("title")

        # Fallback: sold_items[]
        elif "sold_items" in data and isinstance(data["sold_items"], list) and len(data["sold_items"]) > 0:
            title = data["sold_items"][0].get("title")

        return lowest_price, sold_count, title

    except Exception:
        return None, None, None


# ---------------------------------------------------------
# 2. Purchase price advisor (using LOWEST sold price)
# ---------------------------------------------------------
def suggest_purchase_price(
    lowest_sold_price,
    shipping_cost=7.0,
    fee_rate=0.16,
    min_profit=3.0
):
    fees = lowest_sold_price * fee_rate
    max_purchase_price = lowest_sold_price - fees - shipping_cost - min_profit
    return round(max_purchase_price, 2)


# ---------------------------------------------------------
# 3. Main program (continuous mode)
# ---------------------------------------------------------
def main():
    api_key = load_api_key()

    print("Scan UPCs (press Enter on a blank line to exit)\n")

    while True:
        sku = input("UPC: ").strip()

        if sku == "":
            print("\nExiting. Goodbye.")
            break

        lowest_price, sold_count, title = get_price_data_from_api(sku, api_key)

        if lowest_price is None:
            print("❌ Could not retrieve sold price.\n")
            continue

        max_price = suggest_purchase_price(lowest_price)

        print("\n--- RESULTS ---")
        print(f"Title: {title}")
        print(f"Lowest Sold Price: ${round(lowest_price, 2)}")
        print(f"Shipping Default: $7.00")   # <-- ADDED ROW
        print(f"Sold Count (last 90 days): {sold_count}")
        print(f"Suggested Max Purchase Price: ${max_price}")
        print("Do not pay more than this.\n")


# ---------------------------------------------------------
# 4. Run
# ---------------------------------------------------------
if __name__ == "__main__":
    main()