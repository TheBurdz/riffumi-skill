#!/usr/bin/env python3
"""Find b-roll through the official stock APIs, rank it, and show candidates as one contact sheet.

    # one beat
    python3 stock_search.py "hands pouring coffee" --orientation portrait --min-seconds 3 --sheet c.jpg

    # a whole video: one search per beat, one sheet, one JSON
    python3 stock_search.py --plan broll_plan.json --sheet broll_candidates.jpg --out broll_candidates.json

    # download the picks (logs licence + creator to <to>/manifest.json)
    python3 stock_search.py --pick broll_candidates.json --choose hook:2,problem:1,payoff:4 --to broll

broll_plan.json:
    {"orientation": "portrait", "beats": [
       {"beat": "hook",    "query": "neon bedroom night",       "alt": ["led lights dark room"], "min_seconds": 3},
       {"beat": "problem", "query": "messy cables desk close up"},
       {"beat": "payoff",  "query": "friends dancing living room party", "min_seconds": 4}]}

Providers (official APIs, free keys, no scraping, no bot checks involved):
  pexels   PEXELS_API_KEY   https://www.pexels.com/api/   (200 requests/hour, 20,000/month)
  pixabay  PIXABAY_API_KEY  https://pixabay.com/api/docs/
Keys are read from the environment, or from ~/.config/riffumi/keys.json
({"pexels": "...", "pixabay": "..."}), or --pexels-key / --pixabay-key. Keys are never printed.

Each search asks for up to --per-query results (default 15, one request), ranks them
(orientation, length vs the beat, resolution, frame rate, not too long), and keeps the
best --keep (default 6) per beat for the sheet. Look at the sheet, pick one clip per beat
plus a backup, then --pick. Fifteen fetched / six shown beats "five fetched / best three":
one request either way, and the visual check is where quality is decided.

Without any key: the script says so and exits 3. Then either ask the user for a free
Pexels key (two minutes at pexels.com/api), or have the user open the clip page in their
own browser and paste its "Free download" link, and download it with fetch_asset.py.
Do not scrape stock sites or work around their bot protection.
"""
import argparse
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vdlib import load_font  # noqa: E402

UA = "riffumi-skill/1.0 (+stock_search)"


# --------------------------------------------------------------------------- keys

def get_keys(args):
    keys = {}
    p = os.path.expanduser("~/.config/riffumi/keys.json")
    if os.path.isfile(p):
        try:
            with open(p) as f:
                keys.update({k.lower(): v for k, v in json.load(f).items() if v})
        except Exception:
            print(f"note: could not read {p}", file=sys.stderr)
    for prov in ("pexels", "pixabay"):
        env = os.environ.get(prov.upper() + "_API_KEY")
        if env:
            keys[prov] = env
    if args.pexels_key:
        keys["pexels"] = args.pexels_key
    if args.pixabay_key:
        keys["pixabay"] = args.pixabay_key
    return keys


def http_json(url, headers=None):
    req = urllib.request.Request(url, headers=dict({"User-Agent": UA}, **(headers or {})))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise RuntimeError(f"API refused the key (HTTP {e.code}) - check it is valid")
        if e.code == 429:
            raise RuntimeError("API rate limit reached (HTTP 429) - wait, or use the other provider")
        raise RuntimeError(f"HTTP {e.code} from {urllib.parse.urlparse(url).netloc}")


# --------------------------------------------------------------------------- providers

def search_pexels(key, query, orientation, per_page):
    q = {"query": query, "per_page": per_page, "size": "medium"}
    if orientation in ("portrait", "landscape", "square"):
        q["orientation"] = orientation
    data = http_json("https://api.pexels.com/videos/search?" + urllib.parse.urlencode(q), {"Authorization": key})
    out = []
    for v in data.get("videos", []):
        files = [f for f in v.get("video_files", []) if (f.get("file_type") or "").endswith("mp4") and f.get("link")]
        if not files:
            continue
        pics = [p.get("picture") for p in v.get("video_pictures", []) if p.get("picture")]
        out.append({
            "provider": "pexels", "id": v.get("id"), "page": v.get("url"),
            "creator": (v.get("user") or {}).get("name", ""), "creator_url": (v.get("user") or {}).get("url", ""),
            "width": v.get("width", 0), "height": v.get("height", 0), "seconds": v.get("duration", 0),
            "thumbs": ([v.get("image")] if v.get("image") else []) + pics[1:4:1],
            "files": [{"w": f.get("width") or 0, "h": f.get("height") or 0, "fps": f.get("fps") or 0,
                       "url": f["link"]} for f in files],
            "tags": [], "license": "Pexels License (free for commercial use, no attribution required)",
        })
    return out


def search_pixabay(key, query, orientation, per_page):
    q = {"key": key, "q": query, "per_page": max(3, min(200, per_page)), "safesearch": "true"}
    data = http_json("https://pixabay.com/api/videos/?" + urllib.parse.urlencode(q))
    out = []
    for h in data.get("hits", []):
        vids = h.get("videos") or {}
        files = [{"w": v.get("width") or 0, "h": v.get("height") or 0, "fps": 0, "url": v.get("url")}
                 for v in vids.values() if v.get("url")]
        if not files:
            continue
        big = max(files, key=lambda f: f["w"] * f["h"])
        thumb = (vids.get("medium") or vids.get("small") or {}).get("thumbnail")
        out.append({
            "provider": "pixabay", "id": h.get("id"), "page": h.get("pageURL"),
            "creator": h.get("user", ""), "creator_url": "",
            "width": big["w"], "height": big["h"], "seconds": h.get("duration", 0),
            "thumbs": [thumb] if thumb else [], "files": files,
            "tags": [t.strip() for t in (h.get("tags") or "").split(",") if t.strip()],
            "license": "Pixabay Content License (free for commercial use, no attribution required)",
        })
    if orientation in ("portrait", "landscape", "square"):
        def ok(c):
            r = c["width"] / max(1, c["height"])
            return {"portrait": r < 0.9, "landscape": r > 1.1, "square": 0.9 <= r <= 1.1}[orientation]
        out = [c for c in out if ok(c)] or out
    return out


PROVIDERS = {"pexels": search_pexels, "pixabay": search_pixabay}


# --------------------------------------------------------------------------- ranking

def best_file(c, target_long):
    """Smallest file whose long side >= target, else the largest."""
    fs = sorted(c["files"], key=lambda f: max(f["w"], f["h"]))
    for f in fs:
        if max(f["w"], f["h"]) >= target_long:
            return f
    return fs[-1]


def score(c, orientation, min_s, ideal_s, target_long):
    s = 0.0
    w, h = c["width"] or 1, c["height"] or 1
    r = w / h
    want = {"portrait": r < 0.9, "landscape": r > 1.1, "square": 0.9 <= r <= 1.1}.get(orientation, True)
    s += 3 if want else -2
    d = c["seconds"] or 0
    if d < min_s:
        s -= 4
    else:
        s += 2 - min(2, abs(d - ideal_s) / max(ideal_s, 1) * 0.6)
    long_side = max(w, h)
    s += 2 if long_side >= target_long else (1 if long_side >= target_long * 0.66 else -2)
    fps = max((f["fps"] for f in c["files"]), default=0)
    if fps >= 50:
        s += 0.5  # room for slow motion
    if d > 60:
        s -= 1
    return round(s, 2)


def run_beat(beat, keys, args, orientation, target_long):
    queries = [beat["query"]] + list(beat.get("alt", []))
    min_s = float(beat.get("min_seconds", args.min_seconds))
    ideal = max(min_s * 2.5, 6.0)
    seen, cands, errors = set(), [], []
    provs = [p for p in (args.provider.split(",") if args.provider else ["pexels", "pixabay"]) if p in keys]
    for q in queries:
        for prov in provs:
            try:
                for c in PROVIDERS[prov](keys[prov], q, orientation, args.per_query):
                    k = (c["provider"], c["id"])
                    if k in seen:
                        continue
                    seen.add(k)
                    c["query"] = q
                    c["score"] = score(c, orientation, min_s, ideal, target_long)
                    f = best_file(c, target_long)
                    c["download"] = f["url"]
                    c["download_size"] = f"{f['w']}x{f['h']}"
                    cands.append(c)
            except RuntimeError as e:
                errors.append(f"{prov}: {e}")
        if len([c for c in cands if c["score"] >= 5]) >= args.keep:
            break  # enough strong candidates; skip alt queries
    cands.sort(key=lambda c: -c["score"])
    keep = cands[:args.keep]
    for i, c in enumerate(keep, 1):
        c["pick"] = i
        c.pop("files", None)
    return {"beat": beat.get("beat", "beat"), "query": beat["query"], "min_seconds": min_s,
            "found": len(cands), "candidates": keep, "errors": errors}


# --------------------------------------------------------------------------- sheet

def fetch_image(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            from PIL import Image
            return Image.open(io.BytesIO(r.read())).convert("RGB")
    except Exception:
        return None


def make_sheet(results, path, orientation):
    from PIL import Image, ImageDraw
    tw = 220 if orientation == "portrait" else 300
    th = int(tw * (16 / 9 if orientation == "portrait" else 9 / 16 if orientation == "landscape" else 1))
    cols = max((len(r["candidates"]) for r in results), default=1)
    rowh = th + 44
    sheet = Image.new("RGB", (max(1, cols) * tw, max(1, len(results)) * rowh), (16, 16, 18))
    d = ImageDraw.Draw(sheet)
    f1, f2 = load_font("sans:bold", 16), load_font("sans", 13)
    for ri, r in enumerate(results):
        y = ri * rowh
        d.text((6, y + 4), f"{r['beat']}:  \"{r['query']}\"  ({r['found']} found)", fill=(255, 220, 80), font=f1)
        for ci, c in enumerate(r["candidates"]):
            x = ci * tw
            im = fetch_image(c["thumbs"][0]) if c.get("thumbs") else None
            if im:
                s = max(tw / im.width, th / im.height)
                im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))))
                l, t = (im.width - tw) // 2, (im.height - th) // 2
                sheet.paste(im.crop((l, t, l + tw, t + th)), (x, y + 24))
            else:
                d.rectangle((x + 2, y + 26, x + tw - 2, y + 24 + th - 2), outline=(80, 80, 80))
                d.text((x + 10, y + 40), "no preview", fill=(160, 160, 160), font=f2)
            lab = f"#{c['pick']} {c['provider']} {c['seconds']}s {c['width']}x{c['height']} s{c['score']}"
            d.rectangle((x, y + 24 + th - 20, x + tw, y + 24 + th), fill=(0, 0, 0))
            d.text((x + 4, y + 24 + th - 18), lab, fill=(255, 255, 255), font=f2)
    sheet.save(path, quality=88)
    return path


# --------------------------------------------------------------------------- pick / download

def do_pick(args):
    with open(args.pick) as f:
        data = json.load(f)
    by_beat = {r["beat"]: r for r in data["results"]}
    picks = []
    for item in args.choose.split(","):
        beat, _, n = item.strip().partition(":")
        r = by_beat.get(beat)
        if not r:
            sys.exit(f"no beat '{beat}' in {args.pick}")
        c = next((c for c in r["candidates"] if str(c["pick"]) == n), None)
        if not c:
            sys.exit(f"beat '{beat}' has no candidate #{n}")
        picks.append((beat, c))
    fa = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fetch_asset.py")
    import subprocess
    out = []
    for beat, c in picks:
        name = re.sub(r"[^a-z0-9]+", "_", beat.lower()).strip("_") + f"_{c['provider']}{c['id']}.mp4"
        cmd = [sys.executable, fa, c["download"], "--to", args.to, "--name", name, "--source", c["provider"],
               "--license", c["license"], "--creator", c.get("creator", ""), "--page", c.get("page") or "",
               "--kind", "broll"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        ok = r.returncode == 0
        out.append({"beat": beat, "file": os.path.join(args.to, name) if ok else None, "ok": ok,
                    "error": None if ok else (r.stderr or r.stdout).strip()[:300]})
    print(json.dumps(out, indent=1))


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="?")
    ap.add_argument("--plan", help="JSON file with one search per beat")
    ap.add_argument("--orientation", default="portrait", choices=["portrait", "landscape", "square", "any"])
    ap.add_argument("--min-seconds", type=float, default=3.0)
    ap.add_argument("--per-query", type=int, default=15, help="results requested per search (one API call)")
    ap.add_argument("--keep", type=int, default=6, help="best candidates kept per beat")
    ap.add_argument("--target", type=int, default=1920, help="long side wanted for the download file")
    ap.add_argument("--provider", help="pexels,pixabay (default: every provider with a key)")
    ap.add_argument("--sheet", help="write a contact sheet of the candidates")
    ap.add_argument("--out", help="write the candidates JSON here")
    ap.add_argument("--pick", help="candidates JSON from an earlier run")
    ap.add_argument("--choose", help="beat:number pairs, e.g. hook:2,payoff:1")
    ap.add_argument("--to", default="broll")
    ap.add_argument("--pexels-key")
    ap.add_argument("--pixabay-key")
    a = ap.parse_args()
    if a.pick:
        if not a.choose:
            sys.exit("--pick needs --choose beat:number,...")
        return do_pick(a)
    keys = get_keys(a)
    if not keys:
        print(json.dumps({"error": "no_api_key", "fix": [
            "Ask the user for a free Pexels API key (pexels.com/api) and set PEXELS_API_KEY, or a Pixabay key "
            "(pixabay.com/api/docs) as PIXABAY_API_KEY.",
            "Or ask the user to open the clip pages in their own browser and paste the 'Free download' links; "
            "download each with fetch_asset.py.",
            "Do not scrape stock sites or work around their bot protection."]}, indent=1))
        sys.exit(3)
    if a.plan:
        with open(a.plan) as f:
            plan = json.load(f)
        orientation = plan.get("orientation", a.orientation)
        beats = plan["beats"]
    elif a.query:
        orientation = a.orientation
        beats = [{"beat": "beat", "query": a.query}]
    else:
        sys.exit("give a query or --plan")
    results = [run_beat(b, keys, a, orientation, a.target) for b in beats]
    data = {"orientation": orientation, "providers": sorted(keys), "results": results,
            "next": "Look at the sheet. Pick one clip per beat (plus a backup) by content, light and motion, "
                    "then: stock_search.py --pick <this json> --choose beat:#,beat:#"}
    if a.sheet:
        data["sheet"] = make_sheet(results, a.sheet, orientation)
    s = json.dumps(data, indent=1)
    if a.out:
        with open(a.out, "w") as f:
            f.write(s)
    print(s if not a.out else json.dumps({"out": a.out, "sheet": data.get("sheet"),
                                          "beats": [{"beat": r["beat"], "found": r["found"],
                                                     "kept": len(r["candidates"]), "errors": r["errors"]}
                                                    for r in results]}, indent=1))


if __name__ == "__main__":
    main()
