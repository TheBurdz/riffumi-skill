#!/usr/bin/env python3
"""Find b-roll on pexels.com without any key, or through the stock APIs when the user hands you one.

Default route (no key): the script builds the pexels.com search page for each beat, with the
site's own filters (orientation, minimum seconds, people count), and you open those pages with
your own web tools, the way you would read any web page. A clip page (/video/<slug>-<id>/) shows
the creator, duration, dimensions and a thumbnail. Pick one clip per beat plus a backup, then let
the script download the picks through the public "Free download" link and lay them out on one
contact sheet so you can check them before they go in the cut.

    # one beat: print the search URL
    python3 stock_search.py "hands pouring coffee" --orientation portrait --min-seconds 3

    # a whole video: one URL per beat, written to a JSON you fill in
    python3 stock_search.py --plan broll_plan.json --out broll.json

    # download the picks (beat=pexels:<id>[@Creator Name]) and build the check sheet
    python3 stock_search.py --get "hook=pexels:3209828@Pressmaster,payoff=pexels:857195" --to broll --sheet broll_sheet.jpg

broll_plan.json:
    {"orientation": "portrait", "beats": [
       {"beat": "hook",    "query": "neon bedroom night",       "alt": ["led lights dark room"], "min_seconds": 3},
       {"beat": "problem", "query": "messy cables desk close up", "people": "none"},
       {"beat": "payoff",  "query": "friends dancing living room party", "min_seconds": 4}]}

The download link https://www.pexels.com/download/video/<id>/ is the same one the site's button
uses; it answers for any client with the clip's largest rendition. --max-res 1080 (the default)
tries the 1080p rendition first to keep files small, and falls back to the original.

Keyed route (optional): pass --pexels-key or --pixabay-key and the script searches the official
APIs instead, ranks 15 results per phrase, draws the candidates on a sheet, and --pick downloads
your choices. Keys are only ever taken from those flags: the script never reads the environment
or a config file for them, and never prints them. Users who want this every time can edit the
script; the default build stays keyless on purpose.

Either way: do not scrape stock sites or work around their bot protection. Everything downloaded
is logged in <to>/manifest.json with source, licence and creator.
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

UA = "riffumi-skill/1.0 (+stock_search)"


# --------------------------------------------------------------------------- keys

def get_keys(args):
    """Keys come from the command line only (see the module docstring)."""
    keys = {}
    if getattr(args, "pexels_key", None):
        keys["pexels"] = args.pexels_key
    if getattr(args, "pixabay_key", None):
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
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from vdlib import load_font
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

def _siblings():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fetch_asset
    import inspect_media
    return fetch_asset, inspect_media


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
    fetch_asset, _ = _siblings()
    out = []
    for beat, c in picks:
        name = re.sub(r"[^a-z0-9]+", "_", beat.lower()).strip("_") + f"_{c['provider']}{c['id']}.mp4"
        try:
            e = fetch_asset.download(c["download"], args.to, name, c["provider"], c["license"],
                                     c.get("creator", ""), "broll", c.get("page") or "")
            out.append({"beat": beat, "file": e["saved"], "ok": True, "error": None})
        except RuntimeError as exc:
            out.append({"beat": beat, "file": None, "ok": False, "error": str(exc)[:300]})
    print(json.dumps(out, indent=1))


# --------------------------------------------------------------------------- keyless route (pexels.com)

PEXELS_SITE = "https://www.pexels.com"
PEXELS_PEOPLE = {"none": "0", "one": "1", "two": "2", "group": "3_plus"}
PEXELS_LICENSE = "Pexels License (free for commercial use, no attribution required)"


def pexels_search_url(query, orientation=None, min_seconds=None, max_seconds=None, people=None,
                      resolution=None, page=None):
    """The pexels.com video search page with the filters the site itself uses (checked 2026-11-11):
    orientation, min_duration/max_duration in seconds, people_count (0 = nobody in frame, the
    product-shot filter), resolution_name (1080p or 4K)."""
    q = " ".join((query or "").split())
    params = []
    if orientation in ("portrait", "landscape", "square"):
        params.append(("orientation", orientation))
    if min_seconds:
        params.append(("min_duration", str(int(float(min_seconds)))))
    if max_seconds:
        params.append(("max_duration", str(int(float(max_seconds)))))
    if people in PEXELS_PEOPLE:
        params.append(("people_count", PEXELS_PEOPLE[people]))
    if resolution and str(resolution).lower() in ("1080p", "4k"):
        params.append(("resolution_name", "4K" if str(resolution).lower() == "4k" else "1080p"))
    if page and int(page) > 1:
        params.append(("page", str(int(page))))
    url = f"{PEXELS_SITE}/search/videos/{urllib.parse.quote(q, safe='')}/"
    return url + ("?" + urllib.parse.urlencode(params) if params else "")


def pexels_id(text):
    """The clip id from a pexels.com clip page, a download link, a bare id or pexels:<id>."""
    t = (text or "").strip()
    m = (re.search(r"pexels\.com/(?:video/(?:[a-z0-9-]*-)?|download/video/)(\d+)", t, re.I)
         or re.fullmatch(r"(?:pexels:)?(\d+)", t, re.I))
    return m.group(1) if m else None


def site_route(beats, orientation, args):
    """One search URL per beat, plus what to do with it."""
    results = []
    for b in beats:
        min_s = float(b.get("min_seconds", args.min_seconds))
        urls = [pexels_search_url(q, orientation, min_s, b.get("max_seconds"), b.get("people"),
                                  b.get("resolution"))
                for q in [b["query"]] + list(b.get("alt", []))]
        results.append({"beat": b.get("beat", "beat"), "query": b["query"], "min_seconds": min_s,
                        "search": urls[0], "alt_search": urls[1:], "pick": None, "backup": None})
    return {
        "route": "pexels.com (no key)",
        "orientation": orientation,
        "results": results,
        "how": [
            "Open each 'search' page with your own web tool (page fetch, web search or a browser tool).",
            "Open the two or three clip pages that look right (/video/<slug>-<id>/): they show the creator, "
            "duration, dimensions and a thumbnail. Judge the thumbnail and the description against the beat; "
            "never pick by title alone.",
            "Write the pick as pexels:<id>@<creator> into 'pick' (and one 'backup'), then run: "
            "stock_search.py --get \"hook=pexels:<id>@<creator>,...\" --to broll --sheet broll_sheet.jpg",
            "Filters you can add to a search URL: people_count=0 for product and place shots with nobody in "
            "them, min_duration/max_duration in seconds, resolution_name=1080p, page=2 for more. Keep the "
            "query to plain nouns; two or three words beat a sentence.",
            "If pexels.com does not answer from this host: ask the user to open the search in their browser "
            "and paste clip links, then --get works the same; or use the user's own footage, composites and "
            "generated shots. Never scrape or work around bot protection.",
        ],
    }


def parse_get(spec):
    """'hook=pexels:123@Jane Doe,payoff=https://www.pexels.com/video/x-456/' -> [(beat, id, creator)]."""
    out = []
    for item in [i for i in spec.split(",") if i.strip()]:
        beat, _, ref = item.strip().partition("=")
        if not ref:
            beat, ref = "beat%d" % (len(out) + 1), beat
        ref, _, creator = ref.partition("@")
        pid = pexels_id(ref)
        if not pid:
            sys.exit(f"--get: cannot read a Pexels clip id from '{ref}' (want pexels:<id> or a pexels.com link)")
        out.append((re.sub(r"[^a-z0-9]+", "_", beat.lower()).strip("_") or "beat", pid, creator.strip()))
    return out


def do_get(args):
    """Download picked Pexels clips through the public download link; sheet them for the eye check."""
    fetch_asset, inspect_media = _siblings()
    out = []
    for beat, pid, creator in parse_get(args.get):
        name = f"{beat}_pexels{pid}.mp4"
        try:
            e = fetch_asset.download(f"pexels:{pid}", args.to, name, creator=creator, kind="broll",
                                     max_res=args.max_res)
            out.append({"beat": beat, "ref": f"pexels:{pid}", "file": e["saved"], "ok": True, "error": None})
        except RuntimeError as exc:
            out.append({"beat": beat, "ref": f"pexels:{pid}", "file": None, "ok": False, "error": str(exc)[:300]})
    files = [o["file"] for o in out if o["ok"]]
    result = {"downloaded": out}
    if args.sheet and files:
        try:
            inspect_media.main([*files, "--out", args.sheet])
            result["sheet"] = args.sheet
            result["next"] = ("Look at the sheet: one row per clip. Keep what matches the beat by content, light "
                              "and motion; swap anything static, off-vibe or branded for the backup.")
        except SystemExit as exc:
            result["sheet"] = None
            result["sheet_error"] = str(exc)[:300]
    print(json.dumps(result, indent=1))
    if not files:
        sys.exit(2)


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="?")
    ap.add_argument("--plan", help="JSON file with one search per beat")
    ap.add_argument("--orientation", default="portrait", choices=["portrait", "landscape", "square", "any"])
    ap.add_argument("--min-seconds", type=float, default=3.0)
    ap.add_argument("--people", choices=sorted(PEXELS_PEOPLE), help="people in frame (none = product shots)")
    ap.add_argument("--out", help="write the search JSON (keyless) or the candidates JSON (keyed) here")
    ap.add_argument("--get", help="keyless download: beat=pexels:<id>[@creator],... (ids you found on the site)")
    ap.add_argument("--to", default="broll")
    ap.add_argument("--sheet", help="contact sheet: of the downloads (--get) or of the API candidates (keyed)")
    ap.add_argument("--max-res", type=int, default=1080, help="prefer the 1080p rendition when downloading (0 = original)")
    # Keyed route only:
    ap.add_argument("--pexels-key", help="use the Pexels API instead of the site (optional)")
    ap.add_argument("--pixabay-key", help="use the Pixabay API as well (optional)")
    ap.add_argument("--per-query", type=int, default=15, help="keyed: results requested per search (one API call)")
    ap.add_argument("--keep", type=int, default=6, help="keyed: best candidates kept per beat")
    ap.add_argument("--target", type=int, default=1920, help="keyed: long side wanted for the download file")
    ap.add_argument("--provider", help="keyed: pexels,pixabay (default: every provider with a key)")
    ap.add_argument("--pick", help="keyed: candidates JSON from an earlier run")
    ap.add_argument("--choose", help="keyed: beat:number pairs, e.g. hook:2,payoff:1")
    a = ap.parse_args()
    if a.get:
        return do_get(a)
    if a.pick:
        if not a.choose:
            sys.exit("--pick needs --choose beat:number,...")
        return do_pick(a)
    if a.plan:
        with open(a.plan) as f:
            plan = json.load(f)
        orientation = plan.get("orientation", a.orientation)
        beats = plan["beats"]
    elif a.query:
        orientation = a.orientation
        beats = [{"beat": "beat", "query": a.query, "people": a.people}]
    else:
        sys.exit("give a query, --plan, or --get")
    keys = get_keys(a)
    if not keys:
        data = site_route(beats, orientation, a)
        s = json.dumps(data, indent=1)
        if a.out:
            with open(a.out, "w") as f:
                f.write(s)
            print(json.dumps({"out": a.out, "route": data["route"],
                              "searches": [{"beat": r["beat"], "search": r["search"]} for r in data["results"]],
                              "how": data["how"]}, indent=1))
        else:
            print(s)
        return
    results = [run_beat(b, keys, a, orientation, a.target) for b in beats]
    data = {"orientation": orientation, "providers": sorted(keys), "results": results,
            "next": "Look at the sheet. Pick one clip per beat (plus a backup) by content, light and motion, "
                    "then: stock_search.py --pick <this json> --choose beat:#,beat:# (same keys)"}
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
