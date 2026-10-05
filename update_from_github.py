"""
Download the latest scripts from GitHub into this folder.

Made for Pyto on iPhone, which has no git. Run it whenever you have pushed
changes from the Mac. Your rapidapi_key.txt is never touched.
"""
import base64
import json
import urllib.request
from pathlib import Path

REPO = "dfeldkamp12/Check-eBay-UPs"
BRANCH = "main"
FILES = ["Quick_Scan.py", "Scan_Inventory.py", "update_from_github.py"]

HERE = Path(__file__).parent


def download(name):
    # The contents API is always current; raw.githubusercontent.com can serve
    # a cached copy for several minutes after a push
    url = f"https://api.github.com/repos/{REPO}/contents/{name}?ref={BRANCH}"
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    return base64.b64decode(data["content"])


def main():
    print(f"Updating from github.com/{REPO}\n")
    for name in FILES:
        try:
            content = download(name)
        except Exception as e:
            print(f"❌ {name}: {e}")
            continue
        path = HERE / name
        status = "unchanged" if path.exists() and path.read_bytes() == content else "updated"
        path.write_bytes(content)
        print(f"✔ {name}: {status}")
    print("\nDone.")


if __name__ == "__main__":
    main()
