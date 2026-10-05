import getpass
import os
import re
import statistics
import requests
from pathlib import Path

KEY_FILE = Path(__file__).parent / "rapidapi_key.txt"


def load_api_key():
    # RAPIDAPI_KEY env var wins; otherwise read the git-ignored rapidapi_key.txt
    key = os.environ.get("RAPIDAPI_KEY")
    if key:
        return key.strip()
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    # First run on a new device (e.g. Pyto): ask once and save it next to the script
    key = getpass.getpass("RapidAPI key (saved for next time): ").strip()
    if not key:
        raise SystemExit(f"No RapidAPI key found. Put it in {KEY_FILE} or set RAPIDAPI_KEY.")
    KEY_FILE.write_text(key + "\n")
    return key

# ---------------------------------------------------------
# 1. UPC -> product name via UPCitemdb (free: 100 lookups/day)
# ---------------------------------------------------------
class LookupLimitReached(Exception):
    pass


def clean_product_name(title, max_words=6):
    # "Animal Crossing: New Horizons  Nintendo Switch  [Physical] - U.S. Version"
    # -> "Animal Crossing New Horizons Nintendo Switch"
    # Long, punctuated names match very few eBay listings, so keep it short
    title = re.sub(r"\[.*?\]|\(.*?\)", " ", title)
    title = re.sub(r"\s-\s.*$", " ", title)
    title = re.sub(r"[^\w\s&'-]", " ", title)
    return " ".join(title.split()[:max_words])


def lookup_product_name(upc):
    """Return a short product name for the UPC, or None if it isn't in UPCitemdb."""
    response = requests.get(
        "https://api.upcitemdb.com/prod/trial/lookup",
        params={"upc": upc},
        timeout=20,
    )
    if response.status_code == 429:
        raise LookupLimitReached("UPCitemdb daily limit (100 lookups) reached")
    items = response.json().get("items") or []
    if not items or not items[0].get("title"):
        return None
    return clean_product_name(items[0]["title"])


# ---------------------------------------------------------
# 2. eBay sold prices for a product name via RapidAPI
# ---------------------------------------------------------
def get_price_data_from_api(query, api_key):
    """
    Search eBay sold listings by product name (a bare UPC finds almost
    nothing, because sellers rarely put it in titles).
    Returns dict with median_price, lowest_price, sold_count and title,
    or None if nothing sold.
    """
    url = "https://ebay-average-selling-price.p.rapidapi.com/findCompletedItems"

    payload = {
        "keywords": query,
        "max_search_results": "120",
        "remove_outliers": "true",
        "site_id": "0"
    }

    headers = {
        "content-type": "application/json",
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "ebay-average-selling-price.p.rapidapi.com"
    }

    response = requests.post(url, json=payload, headers=headers, timeout=60)
    data = response.json()

    products = data.get("products") if isinstance(data.get("products"), list) else []
    prices = [item["sale_price"] for item in products if item.get("sale_price")]

    median_price = data.get("median_price") or (statistics.median(prices) if prices else None)
    if median_price is None:
        return None

    return {
        "median_price": median_price,
        "lowest_price": data.get("min_price") or (min(prices) if prices else None),
        "sold_count": data.get("total_results"),
        "title": products[0].get("title") if products else None,
    }


# ---------------------------------------------------------
# 3. Purchase price advisor (using MEDIAN sold price)
# ---------------------------------------------------------
def suggest_purchase_price(
    median_sold_price,
    shipping_cost=7.0,
    fee_rate=0.16,
    min_profit=3.0
):
    # The median is the typical sale; the lowest sale is usually a broken,
    # parts-only or case-only listing and gives a misleading number
    fees = median_sold_price * fee_rate
    max_purchase_price = median_sold_price - fees - shipping_cost - min_profit
    return round(max_purchase_price, 2)


# ---------------------------------------------------------
# 4. Main program (continuous mode)
# ---------------------------------------------------------
def main():
    api_key = load_api_key()

    print("Scan a UPC or type a product name (press Enter on a blank line to exit)\n")

    while True:
        entry = input("UPC or name: ").strip()

        if entry == "":
            print("\nExiting. Goodbye.")
            break

        query = entry
        if entry.isdigit():
            try:
                query = lookup_product_name(entry)
            except LookupLimitReached as e:
                print(f"⚠️ {e}.")
                query = None
            except Exception as e:
                print(f"⚠️ Barcode lookup failed: {e}")
                query = None

            if not query:
                query = input("Barcode not found. Type the product name (Enter to skip): ").strip()
                if not query:
                    print()
                    continue

        print(f"Searching eBay sold listings for: {query}")
        try:
            result = get_price_data_from_api(query, api_key)
        except Exception as e:
            print(f"❌ eBay price lookup failed: {e}\n")
            continue

        if result is None:
            print("❌ No eBay sales found. Try a shorter or different name.\n")
            continue

        max_price = suggest_purchase_price(result["median_price"])

        print("\n--- RESULTS ---")
        print(f"Searched For: {query}")
        print(f"Example Sold Listing: {result['title']}")
        print(f"Median Sold Price: ${round(result['median_price'], 2)}")
        if result["lowest_price"] is not None:
            print(f"Lowest Sold Price: ${round(result['lowest_price'], 2)}")
        print(f"Shipping Default: $7.00")
        print(f"Sold Count (last 90 days): {result['sold_count']}")
        print(f"Suggested Max Purchase Price: ${max_price}")
        print("Do not pay more than this.\n")


# ---------------------------------------------------------
# 5. Run
# ---------------------------------------------------------
if __name__ == "__main__":
    # On the phone, fetch the latest version from GitHub first (see update_from_github.py)
    try:
        import importlib
        import update_from_github
        importlib.reload(update_from_github)  # Pyto can keep an old copy loaded between runs
    except ImportError:
        update_from_github = None
    if update_from_github and hasattr(update_from_github, "run_latest"):
        update_from_github.run_latest(__file__, main, globals())
    else:
        main()
