"""Shared helpers for the Riffumi skill scripts.

Only numpy and Pillow are required. Everything else (OpenCV, rembg, whisper)
is optional and detected at runtime.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
FONT_DIR = os.path.join(SKILL_DIR, "fonts")

# --------------------------------------------------------------------------- misc

def die(msg, code=2):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(code)


def need_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            die(f"{tool} not found on PATH. Install ffmpeg (https://ffmpeg.org) and retry.")


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe(path):
    """Return dict with width, height, fps, duration, has_audio, is_image."""
    need_ffmpeg()
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,width,height,r_frame_rate,nb_frames:format=duration",
         "-of", "json", path], capture_output=True, text=True)
    if out.returncode != 0:
        die(f"cannot read media file: {path}\n{out.stderr.strip()}")
    j = json.loads(out.stdout or "{}")
    info = {"width": 0, "height": 0, "fps": 0.0, "duration": 0.0, "has_audio": False,
            "is_image": False}
    for s in j.get("streams", []):
        if s.get("codec_type") == "video" and not info["width"]:
            info["width"], info["height"] = s.get("width", 0), s.get("height", 0)
            try:
                a, b = s.get("r_frame_rate", "0/1").split("/")
                info["fps"] = float(a) / float(b) if float(b) else 0.0
            except Exception:
                pass
        if s.get("codec_type") == "audio":
            info["has_audio"] = True
    try:
        info["duration"] = float(j.get("format", {}).get("duration", 0) or 0)
    except Exception:
        pass
    ext = os.path.splitext(path)[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff") or info["duration"] == 0:
        info["is_image"] = ext != ".gif"
    return info


IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")


def is_image(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXT

# --------------------------------------------------------------------------- colour

_NAMED = {
    "white": "#ffffff", "black": "#000000", "red": "#ff2a2a", "yellow": "#ffe53b",
    "cyan": "#22e4ff", "magenta": "#ff2bd6", "lime": "#b6ff3b", "orange": "#ff8a1f",
    "blue": "#2f6bff", "green": "#22c55e", "pink": "#ff5fa2", "purple": "#8b5cf6",
    "gray": "#808080", "grey": "#808080", "transparent": "#00000000",
}


def color(c, alpha=None):
    """'#rgb', '#rrggbb', '#rrggbbaa', named, or [r,g,b(,a)] -> (r,g,b,a)."""
    if c is None:
        return None
    if isinstance(c, (list, tuple)):
        t = tuple(int(v) for v in c)
        t = t + (255,) if len(t) == 3 else t
    else:
        s = _NAMED.get(str(c).lower(), str(c)).lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        if len(s) == 6:
            s += "ff"
        if len(s) != 8 or not re.fullmatch(r"[0-9a-fA-F]{8}", s):
            raise ValueError(f"bad colour: {c}")
        t = tuple(int(s[i:i + 2], 16) for i in (0, 2, 4, 6))
    if alpha is not None:
        t = t[:3] + (int(max(0, min(1, alpha)) * 255),)
    return t


def hsv(h, s=0.85, v=1.0):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (int(r * 255), int(g * 255), int(b * 255), 255)

# --------------------------------------------------------------------------- fonts

_font_cache = {}
_FALLBACKS = [
    "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def find_font_file(name):
    """Resolve a font reference to a file path.

    Accepts a path, a file in the skill's fonts/ folder, or a family name
    ("Anton", "Inter:Black", "Playfair Display:Bold Italic") looked up with
    fc-match when available. Falls back to a bold sans.
    """
    if not name:
        name = "sans:bold"
    key = name
    if key in _font_cache:
        return _font_cache[key]
    path = None
    if os.path.isfile(name):
        path = name
    if not path and os.path.isdir(FONT_DIR):
        base = name.lower().replace(" ", "").replace(":", "-")
        for f in sorted(os.listdir(FONT_DIR)):
            stem = os.path.splitext(f)[0].lower().replace(" ", "").replace("_", "-")
            if stem == base or stem.startswith(base):
                path = os.path.join(FONT_DIR, f)
                break
    if not path and shutil.which("fc-match"):
        fam, _, style = name.partition(":")
        q = fam + (":style=" + style if style else "")
        try:
            r = subprocess.run(["fc-match", "-f", "%{file}\n%{family}", q], capture_output=True,
                               text=True, timeout=10)
            lines = r.stdout.splitlines()
            if lines and os.path.isfile(lines[0]):
                got_family = lines[1].lower() if len(lines) > 1 else ""
                if fam.lower() in ("sans", "serif", "mono", "monospace") or \
                        fam.lower().split()[0] in got_family:
                    path = lines[0]
                else:
                    print(f"note: font '{name}' not installed; fc-match offered "
                          f"'{lines[1] if len(lines) > 1 else lines[0]}'. Run get_fonts.py "
                          f"\"{fam}\" to fetch it.", file=sys.stderr)
                    path = lines[0]
        except Exception:
            pass
    if not path:
        for f in _FALLBACKS:
            if os.path.isfile(f):
                path = f
                break
            try:
                ImageFont.truetype(f, 10)
                path = f
                break
            except Exception:
                continue
    _font_cache[key] = path
    return path


def load_font(name, size):
    p = find_font_file(name)
    try:
        return ImageFont.truetype(p, max(4, int(size)))
    except Exception:
        return ImageFont.load_default()

# --------------------------------------------------------------------------- timing

class Clock:
    """Converts spec time values to seconds.

    Numbers are seconds. Strings: "1.5s", "12f" (frames), "4b" (beats, needs
    a beat grid), "50%" (share of the parent duration when one is given).
    """

    def __init__(self, fps=30, bpm=None, offset=0.0):
        self.fps = fps
        self.bpm = bpm
        self.offset = offset or 0.0

    @property
    def beat(self):
        return 60.0 / self.bpm if self.bpm else None

    def sec(self, v, parent=None):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().lower()
        if s.endswith("ms"):
            return float(s[:-2]) / 1000.0
        if s.endswith("s"):
            return float(s[:-1])
        if s.endswith("f"):
            return float(s[:-1]) / self.fps
        if s.endswith("b"):
            if not self.bpm:
                raise ValueError(f"'{v}' uses beats but the spec has no beat grid (beat.bpm)")
            return float(s[:-1]) * self.beat
        if s.endswith("%"):
            if parent is None:
                raise ValueError(f"'{v}' is a percentage without a parent duration")
            return float(s[:-1]) / 100.0 * parent
        return float(s)

    def frames(self, seconds):
        return int(round(seconds * self.fps))

# --------------------------------------------------------------------------- easing

def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease(name, x):
    x = clamp(x)
    if name in (None, "linear"):
        return x
    if name == "in":
        return x * x * x
    if name == "out":
        return 1 - (1 - x) ** 3
    if name in ("inout", "in-out"):
        return 4 * x * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
    if name == "back":
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
    if name == "elastic":
        if x in (0, 1):
            return x
        return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi) / 3) + 1
    if name == "bounce":
        n1, d1 = 7.5625, 2.75
        if x < 1 / d1:
            return n1 * x * x
        if x < 2 / d1:
            x -= 1.5 / d1
            return n1 * x * x + 0.75
        if x < 2.5 / d1:
            x -= 2.25 / d1
            return n1 * x * x + 0.9375
        x -= 2.625 / d1
        return n1 * x * x + 0.984375
    if name == "hold":
        return 0.0 if x < 1 else 1.0
    return x


def lerp(a, b, t):
    return a + (b - a) * t

# --------------------------------------------------------------------------- images

def to_rgba(img):
    return img if img.mode == "RGBA" else img.convert("RGBA")


def cover_box(sw, sh, dw, dh, fx=0.5, fy=0.5):
    """Source crop box (x0,y0,x1,y1) that covers dw x dh, centred on focus."""
    s = max(dw / sw, dh / sh)
    cw, ch = dw / s, dh / s
    x0 = clamp(fx * sw - cw / 2, 0, sw - cw)
    y0 = clamp(fy * sh - ch / 2, 0, sh - ch)
    return (x0, y0, x0 + cw, y0 + ch)


def np_rgb(img):
    return np.asarray(img.convert("RGB"), dtype=np.float32)


def from_np(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
