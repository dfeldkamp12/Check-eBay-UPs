"""
Download the latest scripts from GitHub into this folder.

Made for Pyto on iPhone, which has no git. Run it whenever you have pushed
changes from the Mac. Your rapidapi_key.txt is never touched.

The repo is private, so the first run asks for a GitHub token (read-only
access to this repo) and saves it in github_token.txt next to this script.
"""
import base64
import getpass
import json
import urllib.error
import urllib.request
from pathlib import Path

REPO = "dfeldkamp12/Check-eBay-UPs"
BRANCH = "main"
FILES = ["Quick_Scan.py", "Scan_Inventory.py", "update_from_github.py"]

HERE = Path(__file__).parent
TOKEN_FILE = HERE / "github_token.txt"


def load_token():
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    token = getpass.getpass("GitHub token (saved for next time): ").strip()
    if not token:
        raise SystemExit("A GitHub token is needed to read the private repo.")
    TOKEN_FILE.write_text(token + "\n")
    return token


def download(name, token):
    # The contents API is always current; raw.githubusercontent.com can serve
    # a cached copy for several minutes after a push
    url = f"https://api.github.com/repos/{REPO}/contents/{name}?ref={BRANCH}"
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}"}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    return base64.b64decode(data["content"])


def main():
    token = load_token()
    print(f"Updating from github.com/{REPO}\n")
    for name in FILES:
        try:
            content = download(name, token)
        except urllib.error.HTTPError as e:
            if e.code in (401, 404):
                raise SystemExit(f"GitHub refused the token ({e.code}). Delete {TOKEN_FILE.name} and run again with a new one.")
            print(f"❌ {name}: {e}")
            continue
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
