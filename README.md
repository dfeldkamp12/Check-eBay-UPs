# Check eBay UPCs

Scripts for deciding what to buy for eBay resale. You scan barcodes, the scripts look up recent eBay sold prices, and you get the most you should pay for each item.

| Script | What it does |
|---|---|
| `Scan_Inventory.py` | Logs scanned barcodes into an Excel file |
| `Quick_Scan.py` | Looks up one barcode at a time and shows its price info |
| `batch_processor.py` | Prices every barcode in a folder of Excel files and sorts them by best seller |

## How the suggested price works

Each lookup uses the **lowest recent eBay sold price** for the barcode (UPC) and works backward:

```
Max purchase price = lowest sold price − 16% eBay fees − $7.00 shipping − $3.00 minimum profit
```

Change these defaults in `suggest_purchase_price()` in `Quick_Scan.py`.

## Before the first run

You need:

- Python with the packages in `requirements.txt`:

  ```zsh
  pip install -r requirements.txt
  ```

- A RapidAPI key subscribed to the **eBay Average Selling Price** API. Put it in a file called `rapidapi_key.txt` in this folder:

  ```zsh
  echo "YOUR_KEY_HERE" > rapidapi_key.txt
  ```

  Or set it as the `RAPIDAPI_KEY` environment variable. `rapidapi_key.txt` is listed in `.gitignore`, so it is never uploaded to GitHub.

`Scan_Inventory.py` does not need the key.

## Scan_Inventory.py: scan barcodes into Excel

```zsh
python Scan_Inventory.py
```

1. Enter a location name, for example `Goodwill`.
2. Scan barcodes. Each one is saved right away with a timestamp.
3. Press Ctrl+C to stop.

The file is named after the location and date, for example `Goodwill_100526.xlsx`. Column A holds the timestamp and column B holds the barcode. Scanning the same location on the same day adds to the existing file.

On a Mac the file is saved in the folder you run the script from. On iPhone (Pyto app) it is saved in Pyto's Documents folder.

## Quick_Scan.py: check one item

```zsh
python Quick_Scan.py
```

Scan or type a UPC to see:

- Item title
- Lowest sold price
- Number sold in the last 90 days
- Suggested max purchase price

Press Enter on a blank line to exit.

## batch_processor.py: price a whole spreadsheet

```zsh
python batch_processor.py
```

1. Put Excel files from `Scan_Inventory.py` in iCloud Drive → `eBay Scans`.
2. Run the script. For each file it:
   - Reads the barcodes in column B and skips anything that is not a valid 8, 12, 13 or 14-digit UPC.
   - Adds title, lowest sold price, sold count and suggested max purchase price.
   - Sorts rows by **lowest sold price × sold count**, so the best sellers come first.
   - Saves the result to `eBay Scans/Results/` as `<name>_Results.xlsx`.
   - Moves the original file to `eBay Scans/Archive/`.

If a file name already exists, `_a`, `_b` and so on are added instead of overwriting.

## Using the scripts on iPhone (Pyto)

Pyto has no git, so `update_from_github.py` downloads the latest `Quick_Scan.py`, `Scan_Inventory.py` and itself from this repo into Pyto's folder.

After changing a script on the Mac, push to GitHub, then run `update_from_github.py` in Pyto.

While the repo is public, no GitHub login is needed. If the repo is made private, `update_from_github.py` asks once for a GitHub fine-grained token with read-only **Contents** access to this repo, and saves it in `github_token.txt`.

The first time `Quick_Scan.py` runs on the phone, it asks for the RapidAPI key and saves it in `rapidapi_key.txt` next to the script. Both files are listed in `.gitignore`, and the update script never overwrites them.

## Notes

- Each lookup uses one RapidAPI request. Check your RapidAPI plan limits before processing large files.
- Barcodes the API cannot find are left blank in the results.
