"""Look at your material before planning: one contact sheet per file or for a whole folder.

    python3 inspect_media.py clip.mp4 photo.jpg ... --out sheet.jpg [--per-clip 4]
    python3 inspect_media.py ./assets --out assets_sheet.jpg
    python3 inspect_media.py clip.mp4 --at 2.5,7.0 --out-dir frames/     # exact frames

Each row is one file: the frames sampled at 10/35/60/85% (or --per-clip N
evenly), labelled with the file name, size, fps, duration and the timestamp
of every frame. Also prints a JSON inventory (orientation, length, audio,
brightness, motion score) so you can plan without opening every file.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vdlib import IMAGE_EXT, is_image, load_font, need_ffmpeg, probe  # noqa: E402

VIDEO_EXT = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".gif")


def grab(path, t, w):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                        "-vf", f"scale={w}:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    from io import BytesIO
    return Image.open(BytesIO(r.stdout)).convert("RGB")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", default="contact_sheet.jpg")
    ap.add_argument("--per-clip", type=int, default=4)
    ap.add_argument("--thumb", type=int, default=240, help="thumbnail width")
    ap.add_argument("--at", help="exact seconds to export (single clip)")
    ap.add_argument("--out-dir", default=".")
    a = ap.parse_args(argv)
    need_ffmpeg()
    files = []
    for p in a.paths:
        if os.path.isdir(p):
            for f in sorted(os.listdir(p)):
                if f.lower().endswith(VIDEO_EXT + IMAGE_EXT):
                    files.append(os.path.join(p, f))
        else:
            files.append(p)
    if a.at:
        os.makedirs(a.out_dir, exist_ok=True)
        for t in [float(x) for x in a.at.split(",")]:
            im = grab(files[0], t, 1080)
            if im:
                p = os.path.join(a.out_dir, f"{os.path.splitext(os.path.basename(files[0]))[0]}_{t:.2f}s.jpg")
                im.save(p, quality=92)
                print(p)
        return
    rows, inventory = [], []
    for f in files:
        info = probe(f)
        item = {"file": f, "width": info["width"], "height": info["height"],
                "orientation": "portrait" if info["height"] > info["width"] else
                "landscape" if info["width"] > info["height"] else "square"}
        thumbs = []
        if is_image(f):
            im = Image.open(f).convert("RGB")
            im.thumbnail((a.thumb, a.thumb * 2))
            thumbs = [(im, None)]
            item["type"] = "image"
            item["small"] = max(info["width"], info["height"]) < 900
        else:
            item.update(type="video", fps=round(info["fps"], 2), seconds=round(info["duration"], 2),
                        audio=info["has_audio"])
            n = a.per_clip
            ts = [info["duration"] * (k + 0.5) / n for k in range(n)] if n != 4 else \
                [info["duration"] * q for q in (0.1, 0.35, 0.6, 0.85)]
            prev = None
            motion = []
            for t in ts:
                im = grab(f, t, a.thumb)
                if im is None:
                    continue
                thumbs.append((im, t))
                arr = np.asarray(im.resize((64, 64)), np.float32)
                if prev is not None:
                    motion.append(float(np.abs(arr - prev).mean()))
                prev = arr
            item["motion"] = round(float(np.mean(motion)), 1) if motion else 0.0
        if thumbs:
            item["brightness"] = round(float(np.mean([np.asarray(t[0], np.float32).mean() for t in thumbs])), 1)
        inventory.append(item)
        rows.append((f, item, thumbs))
    tw = a.thumb
    th = max((t[0].height for _, _, ts in rows for t in ts), default=tw)
    cols = max(len(ts) for _, _, ts in rows) if rows else 1
    sheet = Image.new("RGB", (cols * tw, len(rows) * (th + 30)), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    font = load_font("sans", 14)
    for r, (f, item, ts) in enumerate(rows):
        y = r * (th + 30)
        lab = os.path.basename(f) + f"  {item['width']}x{item['height']}"
        if item["type"] == "video":
            lab += f"  {item['seconds']}s  {item['fps']}fps  {'audio' if item['audio'] else 'silent'}"
        d.text((4, y + 6), lab, fill=(255, 220, 80), font=font)
        for c, (im, t) in enumerate(ts):
            sheet.paste(im, (c * tw, y + 30))
            if t is not None:
                d.text((c * tw + 4, y + 32), f"{t:.1f}s", fill=(255, 255, 255), font=font,
                       stroke_width=2, stroke_fill=(0, 0, 0))
    sheet.save(a.out, quality=88)
    print(json.dumps({"sheet": a.out, "files": inventory}, indent=1))


if __name__ == "__main__":
    main()
