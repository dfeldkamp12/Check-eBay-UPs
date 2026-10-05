import os
import shutil
import pandas as pd
from openpyxl import load_workbook
from pathlib import Path
from time import sleep

# ---------------------------------------------------------
# 1. Import your existing API + pricing logic
# ---------------------------------------------------------
from Quick_Scan import get_price_data_from_api, suggest_purchase_price, load_api_key


# ---------------------------------------------------------
# 2. Folder paths
# ---------------------------------------------------------
BASE_DIR = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "eBay Scans"
ARCHIVE_DIR = BASE_DIR / "Archive"
RESULTS_DIR = BASE_DIR / "Results"

ARCHIVE_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------
# 3. Generate unique filename (adds _a, _b, _c…)
# ---------------------------------------------------------
def unique_filename(base_path):
    if not base_path.exists():
        return base_path

    stem = base_path.stem
    suffix = base_path.suffix

    for letter in "abcdefghijklmnopqrstuvwxyz":
        new_name = base_path.with_name(f"{stem}_{letter}{suffix}")
        if not new_name.exists():
            return new_name

    raise Exception("Too many duplicate filenames.")


# ---------------------------------------------------------
# 4. UPC validation helper
# ---------------------------------------------------------
def is_valid_upc(value: str) -> bool:
    if not value.isdigit():
        return False
    return len(value) in (8, 12, 13, 14)


# ---------------------------------------------------------
# 5. Set Excel column widths
# ---------------------------------------------------------
def set_column_widths(ws, width=40):
    for col in ws.columns:
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = width


# ---------------------------------------------------------
# 6. Process a single Excel file
# ---------------------------------------------------------
def process_excel_file(filepath, api_key):
    print(f"\nProcessing: {filepath.name}")

    df = pd.read_excel(filepath)

    # Ensure Column B exists
    if df.shape[1] < 2:
        print("❌ File does not contain a Column B. Skipping.")
        return

    # Add new columns
    df["Title"] = ""
    df["Lowest Sold Price"] = ""
    df["Shipping Default"] = "$7.00"
    df["Sold Count (last 90 days)"] = ""
    df["Suggested Max Purchase Price"] = ""

    # Iterate through rows
    for idx, row in df.iterrows():
        sku = str(row.iloc[1]).strip()  # Column B

        # Skip blanks, NaN, or invalid UPCs
        if sku == "" or sku.lower() == "nan":
            continue
        if not is_valid_upc(sku):
            continue

        # Build timestamp + filename
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        combined_stamp = f"{timestamp} | {filepath.name}"
        df.at[idx, "Timestamp"] = combined_stamp

        try:
            lowest_price, sold_count, title = get_price_data_from_api(sku, api_key)

            if lowest_price is None:
                continue

            max_price = suggest_purchase_price(lowest_price)

            df.at[idx, "Title"] = title
            df.at[idx, "Lowest Sold Price"] = round(lowest_price, 2)
            df.at[idx, "Sold Count (last 90 days)"] = sold_count
            df.at[idx, "Suggested Max Purchase Price"] = max_price

        except Exception as e:
            print(f"Error processing SKU {sku}: {e}")
            continue

        sleep(0.1)  # Faster rate limiting


    # ---------------------------------------------------------
    #  SORTING LOGIC: Score = Lowest Sold Price × Sold Count
    # ---------------------------------------------------------
    df["Lowest Sold Price"] = pd.to_numeric(df["Lowest Sold Price"], errors="coerce").fillna(0)
    df["Sold Count (last 90 days)"] = pd.to_numeric(df["Sold Count (last 90 days)"], errors="coerce").fillna(0)

    df["Score"] = df["Lowest Sold Price"] * df["Sold Count (last 90 days)"]

    df = df.sort_values(by="Score", ascending=False)


    # ---------------------------------------------------------
    # SAVE RESULTS
    # ---------------------------------------------------------
    result_filename = filepath.stem + "_Results.xlsx"
    result_path = RESULTS_DIR / result_filename
    result_path = unique_filename(result_path)

    df.to_excel(result_path, index=False)

    # Apply column widths
    wb = load_workbook(result_path)
    ws = wb.active
    set_column_widths(ws, width=40)
    wb.save(result_path)

    print(f"✔ Results saved to: {result_path.name}")

    # Move original file to Archive
    archive_path = ARCHIVE_DIR / filepath.name
    archive_path = unique_filename(archive_path)
    shutil.move(str(filepath), str(archive_path))

    print(f"📦 Moved original to Archive: {archive_path.name}")


# ---------------------------------------------------------
# 7. Main batch processor
# ---------------------------------------------------------
def main():
    api_key = load_api_key()

    print("\n📁 Scanning for .xlsx files in eBay Scans...\n")

    files = [
        f for f in BASE_DIR.glob("*.xlsx")
        if "_Results" not in f.name and not f.name.startswith("~$")
    ]

    if not files:
        print("No new Excel files found.")
        return

    for file in files:
        process_excel_file(file, api_key)

    print("\n🎉 All files processed successfully.\n")


# ---------------------------------------------------------
# 8. Run
# ---------------------------------------------------------
if __name__ == "__main__":
    main()
