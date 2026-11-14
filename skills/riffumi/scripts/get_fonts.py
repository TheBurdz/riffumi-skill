"""Fetch open-licence (SIL OFL) font families into the skill's fonts/ folder.

    python3 get_fonts.py "Anton" "Playfair Display:700" "Inter:900" "Caveat"

Tries the Google Fonts CSS API (asks for TrueType), then the google/fonts
GitHub repository. Files land in ../fonts as Family-Weight.ttf and can then be
used in a spec as "font": "Anton" or "font": "Inter-900". Every family on Google
Fonts is free for commercial use; keep the licence note in fonts/LICENSES.txt.
"""
import os
import re
import sys
import urllib.parse
import urllib.request

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
UA_TTF = "Wget/1.21"  # a non-browser UA makes the CSS API serve TrueType


def get(url, ua="Mozilla/5.0"):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def via_css(family, weight):
    q = urllib.parse.quote(family) + (f":wght@{weight}" if weight else "")
    css = get(f"https://fonts.googleapis.com/css2?family={q}", UA_TTF).decode()
    urls = re.findall(r"url\((https://[^)]+)\)", css)
    if not urls:
        raise RuntimeError("no font file in CSS response")
    u = urls[-1]
    ext = os.path.splitext(urllib.parse.urlparse(u).path)[1] or ".ttf"
    return get(u), ext


def via_github(family, weight):
    slug = family.lower().replace(" ", "")
    names = [family.replace(" ", "") + "-Regular.ttf", family.replace(" ", "") + "[wght].ttf"]
    for lic in ("ofl", "apache", "ufl"):
        for n in names:
            url = f"https://raw.githubusercontent.com/google/fonts/main/{lic}/{slug}/{urllib.parse.quote(n)}"
            try:
                return get(url), ".ttf"
            except Exception:
                continue
    raise RuntimeError("not found on GitHub")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    os.makedirs(FONT_DIR, exist_ok=True)
    for arg in sys.argv[1:]:
        fam, _, w = arg.partition(":")
        fname = fam.replace(" ", "") + (f"-{w}" if w else "")
        try:
            data, ext = via_css(fam, w)
        except Exception as e1:
            try:
                data, ext = via_github(fam, w)
                if w:
                    print(f"note: {fam} came as the default/variable file; weight {w} may not be applied")
            except Exception as e2:
                print(f"FAILED {arg}: {e1}; {e2}")
                continue
        p = os.path.join(FONT_DIR, fname + ext)
        with open(p, "wb") as f:
            f.write(data)
        print(f"saved {p}")
    lic = os.path.join(FONT_DIR, "LICENSES.txt")
    if not os.path.isfile(lic):
        with open(lic, "w") as f:
            f.write("Fonts fetched from Google Fonts are licensed under the SIL Open Font License 1.1 or Apache 2.0; "
                "see https://fonts.google.com/ for each family's licence.\n")


if __name__ == "__main__":
    main()
