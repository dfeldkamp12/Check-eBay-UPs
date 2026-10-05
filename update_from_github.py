"""
Download the latest scripts from GitHub into this folder.

Made for Pyto on iPhone, which has no git. Quick_Scan.py calls this
automatically at startup; run it by hand to update the other scripts or
if the automatic check fails. Your rapidapi_key.txt is never touched.

A public repo needs no login. If the repo is private, it asks once for a
GitHub token (read-only access to this repo) and saves it in
github_token.txt next to this script.
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


class TokenNeeded(Exception):
    pass


def is_git_checkout():
    # On the Mac the folder is a git repo; downloading would overwrite
    # uncommitted edits there, so updates are for the phone only
    return (HERE / ".git").exists()


def saved_token():
    return TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else None


def ask_for_token():
    token = getpass.getpass("Repo is private. GitHub token (saved for next time): ").strip()
    if not token:
        raise SystemExit("A GitHub token is needed to read the private repo.")
    TOKEN_FILE.write_text(token + "\n")
    return token


def download(name, token, timeout):
    # The contents API is always current; raw.githubusercontent.com can serve
    # a cached copy for several minutes after a push
    url = f"https://api.github.com/repos/{REPO}/contents/{name}?ref={BRANCH}"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.load(response)
    return base64.b64decode(data["content"])


def update_all(timeout=20, ask_token=True, verbose=True):
    """Download every file in FILES. Returns the names of files that changed."""
    token = saved_token()
    changed = []
    for name in FILES:
        try:
            try:
                content = download(name, token, timeout)
            except urllib.error.HTTPError as e:
                # Private repos answer 404 (not 401) to requests without a token
                if e.code not in (401, 404):
                    raise
                if token:
                    raise SystemExit(f"GitHub refused the token ({e.code}). Delete {TOKEN_FILE.name} and run again with a new one.")
                if not ask_token:
                    raise TokenNeeded("repo is private; run update_from_github.py to enter a token")
                token = ask_for_token()
                content = download(name, token, timeout)
        except TokenNeeded:
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            # No signal / GitHub unreachable: the other files will fail too,
            # so stop now instead of waiting out a timeout for each one
            if not verbose:
                raise
            print(f"❌ Can't reach GitHub: {getattr(e, 'reason', e)}")
            break
        except Exception as e:
            if verbose:
                print(f"❌ {name}: {e}")
            continue
        path = HERE / name
        if path.exists() and path.read_bytes() == content:
            status = "unchanged"
        else:
            path.write_bytes(content)
            changed.append(name)
            status = "updated"
        if verbose:
            print(f"✔ {name}: {status}")
    return changed


def main():
    if is_git_checkout():
        raise SystemExit("This folder is the git repo on the Mac. Use git pull here instead.")
    print(f"Updating from github.com/{REPO}\n")
    update_all()
    print("\nDone.")


if __name__ == "__main__":
    main()
