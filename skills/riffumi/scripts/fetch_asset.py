"""Download a stock clip, photo, music track or sound and record where it came from.

    python3 fetch_asset.py URL --to assets/ [--name city_night.mp4]
        --source pexels --license "Pexels License" --creator "Jane Doe"
        --kind broll|music|sfx|photo|font [--page https://www.pexels.com/video/...]

    # a Pexels clip you found on the site: the id, the clip page or its download link all work
    python3 fetch_asset.py pexels:3209828 --to broll --creator "Pressmaster" --kind broll
    python3 fetch_asset.py https://www.pexels.com/video/a-woman-pouring-coffee-3209828/ --to broll

A Pexels reference needs no key: the script follows the clip's public "Free download" link
(the one the site's own button uses), fills in source, licence and page, and tries the 1080p
rendition first (--max-res 1080) before falling back to the original, usually 4K.

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
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (riffumi-skill/1.1)"
PEXELS_SITE = "https://www.pexels.com"
PEXELS_LICENSE = "Pexels License (free for commercial use, no attribution required)"


def pexels_id(text):
    t = (text or "").strip()
    m = (re.search(r"pexels\.com/(?:video/(?:[a-z0-9-]*-)?|download/video/)(\d+)", t, re.I)
         or re.fullmatch(r"(?:pexels:)?(\d+)", t, re.I))
    return m.group(1) if m else None


def resolve_pexels(pid, max_res):
    """Follow the public download link to the file URL; prefer the largest rendition whose
    short edge is at most max_res (1080 = 1080p) when Pexels publishes one under the usual naming."""
    req = urllib.request.Request(f"{PEXELS_SITE}/download/video/{int(pid)}/", method="HEAD",
                                 headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            final = r.geturl()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"pexels: HTTP {e.code} for clip {pid}. Check the id on pexels.com, or ask the "
                           f"user to paste the clip's Free download link.")
    except Exception as e:
        raise RuntimeError(f"pexels: could not reach the download link for clip {pid}: {e}")
    if max_res and max_res > 0:
        # Two naming styles on videos.pexels.com: "<id>-uhd_3840_2160_25fps.mp4" (older) and
        # "<fileid>_2160_3840_30fps.mp4" (newer, no quality tag). Both expose the size.
        m = re.search(r"(-(?:uhd|hd|sd))?_(\d+)_(\d+)_(\d+fps)\.mp4$", final)
        if m and min(int(m.group(2)), int(m.group(3))) > max_res:
            w, h = int(m.group(2)), int(m.group(3))
            portrait = h > w
            tagged = bool(m.group(1))
            for tag, long_side in (("hd", 1920), ("hd", 1280), ("sd", 960)):
                short = {1920: 1080, 1280: 720, 960: 540}[long_side]
                if short > max_res:
                    continue
                size = f"{short}_{long_side}" if portrait else f"{long_side}_{short}"
                prefix = f"-{tag}_" if tagged else "_"
                cand = final[:m.start()] + f"{prefix}{size}_{m.group(4)}.mp4"
                try:
                    with urllib.request.urlopen(urllib.request.Request(cand, method="HEAD",
                                                                       headers={"User-Agent": UA}),
                                                timeout=30) as r2:
                        if r2.status == 200:
                            return cand
                except Exception:
                    continue
    return final


def download(url, to="assets", name=None, source="", license="", creator="", kind="", page="",
             max_res=1080):
    """Fetch one file (or a Pexels clip reference) into ``to`` and log it in the manifest.
    Returns the manifest entry plus ``saved``; raises RuntimeError with a plain message."""
    os.makedirs(to, exist_ok=True)
    licence = license
    pid = pexels_id(url) if ("pexels" in url.lower() or re.fullmatch(r"\d+", url.strip())) else None
    if pid:
        url = resolve_pexels(pid, max_res)
        page = page or f"{PEXELS_SITE}/video/{pid}/"
        source, licence = source or "pexels", licence or PEXELS_LICENSE
    name = name or os.path.basename(urllib.parse.urlparse(url).path) or "asset"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    dest = os.path.join(to, name)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=300) as r, open(dest + ".part", "wb") as f:
            ctype = r.headers.get("Content-Type", "")
            if "text/html" in ctype:
                raise RuntimeError(f"refused: {url} returned a web page, not a file. Use the direct file link.")
            n = 0
            while True:
                b = r.read(1 << 16)
                if not b:
                    break
                f.write(b)
                n += len(b)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"download failed: HTTP {e.code} from {url}. The host may block scripts; try "
                           f"another source or ask the user for the file.")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"download failed: {e}")
    os.replace(dest + ".part", dest)
    man = os.path.join(to, "manifest.json")
    data = []
    if os.path.isfile(man):
        with open(man) as f:
            data = json.load(f)
    entry = {"file": name, "url": url, "page": page, "source": source, "license": licence,
             "creator": creator, "kind": kind, "bytes": n,
             "downloaded": datetime.datetime.now().isoformat(timespec="seconds")}
    data.append(entry)
    with open(man, "w") as f:
        json.dump(data, f, indent=1)
    return dict(entry, saved=dest)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="a direct file link, or a Pexels clip (pexels:<id>, clip page or download link)")
    ap.add_argument("--to", default="assets")
    ap.add_argument("--name")
    ap.add_argument("--source", default="")
    ap.add_argument("--license", default="")
    ap.add_argument("--creator", default="")
    ap.add_argument("--kind", default="")
    ap.add_argument("--page", default="")
    ap.add_argument("--max-res", type=int, default=1080,
                    help="Pexels only: prefer the largest rendition up to this height class, 1080 = 1080p (0 = original)")
    a = ap.parse_args(argv)
    try:
        e = download(a.url, a.to, a.name, a.source, a.license, a.creator, a.kind, a.page, a.max_res)
    except RuntimeError as exc:
        sys.exit(str(exc))
    print(json.dumps({"saved": e["saved"], "bytes": e["bytes"], "url": e["url"], "page": e["page"],
                      "license": e["license"]}))


if __name__ == "__main__":
    main()
