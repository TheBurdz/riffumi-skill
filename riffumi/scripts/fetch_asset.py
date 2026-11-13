#!/usr/bin/env python3
"""Download a stock clip, photo, music track or sound and record where it came from.

    python3 fetch_asset.py URL --to assets/ [--name city_night.mp4]
        --source pexels --license "Pexels License" --creator "Jane Doe"
        --kind broll|music|sfx|photo|font [--page https://www.pexels.com/video/...]

Writes the file and appends an entry to assets/manifest.json:
  {file, url, page, source, license, creator, kind, bytes, downloaded}
The manifest is how credits, licence checks and re-use work later: keep it.

Only download what the user may use: their own files, or free-for-commercial-use
libraries (see references/assets-and-licensing.md). This script does not bypass
logins, paywalls or bot checks; if a site refuses, use another source or ask the
user to download the file and hand it over.
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--to", default="assets")
    ap.add_argument("--name")
    ap.add_argument("--source", default="")
    ap.add_argument("--license", default="")
    ap.add_argument("--creator", default="")
    ap.add_argument("--kind", default="")
    ap.add_argument("--page", default="")
    a = ap.parse_args()
    os.makedirs(a.to, exist_ok=True)
    name = a.name or os.path.basename(urllib.parse.urlparse(a.url).path) or "asset"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    dest = os.path.join(a.to, name)
    req = urllib.request.Request(a.url, headers={"User-Agent": "Mozilla/5.0 (riffumi-skill)"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(dest + ".part", "wb") as f:
            ctype = r.headers.get("Content-Type", "")
            if "text/html" in ctype:
                sys.exit(f"refused: {a.url} returned a web page, not a file. Use the direct file link.")
            n = 0
            while True:
                b = r.read(1 << 16)
                if not b:
                    break
                f.write(b)
                n += len(b)
    except urllib.error.HTTPError as e:
        sys.exit(f"download failed: HTTP {e.code} from {a.url}. The host may block scripts; try another "
                 f"source or ask the user for the file.")
    except Exception as e:
        sys.exit(f"download failed: {e}")
    os.replace(dest + ".part", dest)
    man = os.path.join(a.to, "manifest.json")
    data = []
    if os.path.isfile(man):
        with open(man) as f:
            data = json.load(f)
    data.append({"file": name, "url": a.url, "page": a.page, "source": a.source, "license": a.license,
                 "creator": a.creator, "kind": a.kind, "bytes": n,
                 "downloaded": datetime.datetime.now().isoformat(timespec="seconds")})
    with open(man, "w") as f:
        json.dump(data, f, indent=1)
    print(json.dumps({"saved": dest, "bytes": n}))


if __name__ == "__main__":
    main()
