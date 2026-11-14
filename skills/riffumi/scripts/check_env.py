#!/usr/bin/env python3
"""Report what this machine can do for video work, so the agent picks the right route.

    python3 check_env.py            # human summary
    python3 check_env.py --json

Checks: ffmpeg/ffprobe (and key filters), Python libs (numpy, Pillow required;
OpenCV, rembg, faster-whisper optional), installed fonts, the skill's fonts/
folder, CPU count, and whether common asset hosts answer (stock video, music,
fonts). Network checks are quick HEAD requests and never download anything.

The result is also written to ENV_FILE (.riffumi_env.json in the working
directory) so preflight.py knows whether this host is offline and can relax
the font and b-roll requirements instead of failing every bold cut.
"""
import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request

ENV_FILE = ".riffumi_env.json"

HOSTS = {
    # The public download link of one clip: a 302 to its MP4 for any client (a plain GET of the
    # site root is bot-checked and says nothing about whether the route works).
    "pexels_download": "https://www.pexels.com/download/video/3209828/",
    "mixkit": "https://mixkit.co/",
    "mixkit_assets": "https://assets.mixkit.co/",
    "archive_org": "https://archive.org/",
    "google_fonts_css": "https://fonts.googleapis.com/css2?family=Anton",
    "github_raw": "https://raw.githubusercontent.com/",
    "pypi": "https://pypi.org/simple/",
}


def ping(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-net", action="store_true")
    a = ap.parse_args()
    r = {"python": sys.version.split()[0], "cpus": os.cpu_count()}
    r["ffmpeg"] = bool(shutil.which("ffmpeg")) and bool(shutil.which("ffprobe"))
    if r["ffmpeg"]:
        v = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
        r["ffmpeg_version"] = v
        f = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        r["ffmpeg_filters"] = {k: (f" {k} " in f) for k in ("loudnorm", "sidechaincompress", "vidstabdetect",
                                                           "deshake", "xfade", "subtitles", "drawtext")}
        enc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
        r["encoders"] = {k: (k in enc) for k in ("libx264", "libx265", "libvpx-vp9", "aac", "libmp3lame")}
    libs = {}
    for m in ("numpy", "PIL", "cv2", "scipy", "rembg", "onnxruntime", "faster_whisper", "whisper"):
        try:
            importlib.import_module(m)
            libs[m] = True
        except Exception:
            libs[m] = False
    r["python_libs"] = libs
    fonts = []
    if shutil.which("fc-list"):
        out = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
        fonts = sorted({x.split(",")[0].strip() for x in out.splitlines() if x.strip()})
    r["system_font_families"] = len(fonts)
    r["system_fonts_sample"] = fonts[:40]
    fd = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
    r["skill_fonts"] = sorted(f for f in os.listdir(fd) if f.lower().endswith((".ttf", ".otf"))) if os.path.isdir(fd) else []
    if not a.no_net:
        r["network"] = {k: ping(u) for k, u in HOSTS.items()}
    # Stock b-roll needs no key: stock_search.py builds pexels.com search pages for
    # the agent's own web tools and downloads picks through the public download link.
    r["stock_route"] = "pexels.com public (no key): stock_search.py --plan ... then --get"
    ready = r["ffmpeg"] and libs["numpy"] and libs["PIL"]
    r["can_render"] = bool(ready)
    net = r.get("network", {})
    # Offline = no asset host answered at all (sandboxes with no egress).
    # Fonts and stock b-roll are then out of reach; preflight relaxes them.
    r["online"] = any(v is not None for v in net.values()) if net else None
    r["fonts_reachable"] = net.get("google_fonts_css") == 200 if net else None
    r["stock_reachable"] = bool(net) and net.get("pexels_download") in (200, 301, 302)
    missing = [m for m in ("numpy", "PIL") if not libs[m]]
    if ready:
        r["route"] = "code: render locally with scripts/render.py"
    elif r["ffmpeg"] and missing:
        r["route"] = ("almost: run python3 scripts/setup.py to install " + " and ".join(missing) +
                      ", then render locally with scripts/render.py")
    else:
        r["route"] = ("no local render: install ffmpeg + numpy + Pillow (python3 scripts/setup.py prints "
                      "the commands), or use a connected video tool / generation model, or the hosted "
                      "Riffumi connector at riffumi.com")
    try:
        with open(ENV_FILE, "w") as fh:
            json.dump(r, fh, indent=1)
    except OSError:
        pass
    if a.json:
        print(json.dumps(r, indent=1))
        return
    print(f"Python {r['python']}  CPUs {r['cpus']}")
    print(f"ffmpeg: {'yes' if r['ffmpeg'] else 'NO'}  {r.get('ffmpeg_version', '')}")
    if r["ffmpeg"]:
        print("  filters: " + ", ".join(f"{k}={'y' if v else 'n'}" for k, v in r["ffmpeg_filters"].items()))
    print("libs: " + ", ".join(f"{k}={'y' if v else 'n'}" for k, v in libs.items()))
    print(f"fonts: {r['system_font_families']} system families, {len(r['skill_fonts'])} in skill fonts/")
    if "network" in r:
        print("network: " + ", ".join(f"{k}={v}" for k, v in r["network"].items()))
    print("stock b-roll: " + r["stock_route"])
    if r.get("online") is False:
        print("offline: no asset host answers from here. Fonts and stock b-roll cannot be fetched; preflight "
              "treats those two rows as warnings. Use the user's own files, system fonts and generated shots.")
    elif r.get("stock_reachable") is False:
        print("  -> pexels.com does not answer from this host; read its pages with your own web tool, or ask "
              "the user to paste clip links, then stock_search.py --get downloads them")
    print("route: " + r["route"])
    print(f"(saved to {ENV_FILE} for preflight.py)")


if __name__ == "__main__":
    main()
