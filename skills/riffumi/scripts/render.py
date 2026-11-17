"""Render a video from a JSON edit spec (see references/spec-format.md).

    python3 render.py spec.json                      # the video, full canvas size -> spec.output
    python3 render.py spec.json --scale 0.5          # quick half-size draft -> <output>_draft.mp4 (not for delivery)
    python3 render.py spec.json --stills 0,3.2,7.5   # full-size JPEGs at those seconds
    python3 render.py spec.json --sheet 12           # one contact sheet of 12 frames
    python3 render.py spec.json --only 4             # re-render scene 4 (and reuse the rest)
    python3 render.py spec.json --audio-only         # rebuild only the sound mix

Needs Python 3.8+, numpy, Pillow and ffmpeg. Scenes are encoded one file each
(transitions live inside the incoming scene's file), joined without re-encoding,
then the mixed and loudness-levelled audio is muxed on.
"""
import argparse
import json
import math
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vdlib import (Clock, clamp, color, cover_box, die, ease, from_np, hsv, is_image,  # noqa: E402
                   lerp, load_font, need_ffmpeg, probe)
import blocks as blocklib  # noqa: E402

# =========================================================================== context


class Ctx:
    def __init__(self, spec, spec_path, scale=1.0):
        self.spec = spec
        self.base = os.path.dirname(os.path.abspath(spec_path))
        cv = spec.get("canvas", {})
        self.DW, self.DH = int(cv.get("width", 1080)), int(cv.get("height", 1920))
        self.S = scale
        self.W = int(round(self.DW * scale / 2) * 2)
        self.H = int(round(self.DH * scale / 2) * 2)
        self.fps = int(cv.get("fps", 30))
        bt = spec.get("beat") or {}
        self.clock = Clock(self.fps, bt.get("bpm"), bt.get("offset", 0.0))
        self.bg = color(cv.get("background", "#000000"))
        self.seed = int(spec.get("seed", 7))

    def path(self, p):
        if p is None:
            return None
        p = os.path.expanduser(str(p))
        return p if os.path.isabs(p) else os.path.join(self.base, p)

    def px(self, v):
        """Design pixels -> render pixels."""
        return float(v) * self.S

    def beat_phase(self, t_global):
        b = self.clock.beat
        if not b:
            return None
        return ((t_global - 0.0) / b) % 1.0


# =========================================================================== sources

class ClipReader:
    """Streams frames of a video clip at render size, following a time map."""

    def __init__(self, ctx, sc, times):
        self.ctx = ctx
        self.src = ctx.path(sc["src"])
        if not os.path.isfile(self.src):
            die(f"clip not found: {self.src}")
        info = probe(self.src)
        self.info = info
        self.fit = sc.get("fit", "cover")
        fx, fy = (sc.get("focus") or [0.5, 0.5])
        W, H = ctx.W, ctx.H
        self.rate = min(60.0, max(24.0, info["fps"] or 30.0))
        self.times = times
        lo = max(0.0, min(times))
        hi = max(times) + 2.0 / self.rate
        self.t0 = lo
        if self.fit == "cover":
            sw, sh = info["width"], info["height"]
            s = max(W / sw, H / sh)
            nw, nh = int(math.ceil(sw * s / 2) * 2), int(math.ceil(sh * s / 2) * 2)
            nw, nh = max(nw, W), max(nh, H)
            cx = int(clamp(fx * nw - W / 2, 0, nw - W))
            cy = int(clamp(fy * nh - H / 2, 0, nh - H))
            vf = f"scale={nw}:{nh}:flags=bicubic,crop={W}:{H}:{cx}:{cy}"
            self.fw, self.fh = W, H
        else:
            vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=bicubic"
            sw, sh = info["width"], info["height"]
            s = min(W / sw, H / sh)
            self.fw, self.fh = int(sw * s) // 2 * 2 or 2, int(sh * s) // 2 * 2 or 2
            vf = f"scale={self.fw}:{self.fh}:flags=bicubic"
        vf = f"fps={self.rate}," + vf
        self.cmd = ["ffmpeg", "-v", "error", "-ss", f"{lo:.4f}", "-t", f"{hi - lo:.4f}", "-i", self.src,
                    "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.idx = [int(round((t - lo) * self.rate)) for t in times]
        self.monotonic = all(b >= a for a, b in zip(self.idx, self.idx[1:]))
        self.fsize = self.fw * self.fh * 3
        self.proc = None
        self.cache = None
        self.last = None
        self.pos = -1

    def _open(self):
        self.proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, bufsize=self.fsize * 4)

    def _read(self):
        b = self.proc.stdout.read(self.fsize)
        if len(b) < self.fsize:
            return None
        return np.frombuffer(b, np.uint8).reshape(self.fh, self.fw, 3)

    def frame(self, k):
        """Frame for the k-th entry of the time map."""
        want = self.idx[k]
        if not self.monotonic:
            if self.cache is None:
                self._open()
                frames = []
                while True:
                    f = self._read()
                    if f is None:
                        break
                    frames.append(f)
                self.proc.wait()
                if not frames:
                    die(f"could not decode {self.src}")
                self.cache = frames
            return self.cache[int(clamp(want, 0, len(self.cache) - 1))]
        if self.proc is None:
            self._open()
        while self.pos < want:
            f = self._read()
            if f is None:
                break
            self.last = f
            self.pos += 1
        if self.last is None:
            die(f"could not decode {self.src} at {self.times[k]:.2f}s")
        return self.last

    def close(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()


def time_map(sc, clock, n_frames, dur):
    """Source time (s) for each local output frame of a clip scene."""
    fps = clock.fps
    t_in = clock.sec(sc.get("in", 0)) or 0.0
    sp0 = float(sc.get("speed", 1.0))
    sp1 = float(sc.get("speed_to", sp0))
    times = []
    src = t_in
    freeze = sc.get("freeze")  # {"at": local seconds, "hold": seconds}
    f_at = clock.sec(freeze["at"]) if freeze else None
    f_hold = clock.sec(freeze.get("hold", 0.5)) if freeze else 0
    for f in range(n_frames):
        t = f / fps
        if freeze and f_at <= t < f_at + f_hold:
            times.append(times[-1] if times else src)
            continue
        times.append(src)
        p = clamp(t / max(dur, 1e-6))
        sp = lerp(sp0, sp1, ease("inout", p))
        src += sp / fps
    if sc.get("reverse"):
        times = list(reversed(times))
    return times


class Picture:
    """A still image with optional crop, cached at full source resolution."""
    _cache = {}

    def __init__(self, ctx, src, crop=None):
        key = (src, tuple(crop) if crop else None)
        if key in Picture._cache:
            self.__dict__ = Picture._cache[key].__dict__
            return
        p = ctx.path(src)
        if not os.path.isfile(p):
            die(f"image not found: {p}")
        im = Image.open(p)
        im.load()
        self.has_alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
        im = im.convert("RGBA")
        if crop:
            x0, y0, x1, y1 = crop
            if max(crop) <= 1.0:
                x0, x1 = x0 * im.width, x1 * im.width
                y0, y1 = y0 * im.height, y1 * im.height
            im = im.crop((int(x0), int(y0), int(x1), int(y1)))
        self.rgba = im
        self.rgb = im.convert("RGB")
        self._matte = None
        Picture._cache[key] = self

    def matte(self, method="auto"):
        if self._matte is None:
            if self.has_alpha and self.rgba.getchannel("A").getextrema()[0] < 250:
                self._matte = self.rgba.getchannel("A")
            else:
                from matte import make_matte
                m, rep = make_matte(self.rgb, method)
                for w in rep.get("warnings", []):
                    print(f"matte warning: {w}", file=sys.stderr)
                self._matte = m
        return self._matte


# =========================================================================== camera

def camera(sc, p, t, ctx, dur=None):
    """(zoom, fx, fy, rot_deg) for a scene at progress p (may exceed 1)."""
    mv = sc.get("camera", "none") or "none"
    a = float(sc.get("camera_amount", 0.08))
    if isinstance(mv, list):  # keyframed path [{t, zoom, x, y, rot, ease}]
        def kt(k):
            return ctx.clock.sec(k.get("t", 0), dur)
        kf = sorted(mv, key=kt)
        prev = kf[0]
        for k in kf:
            if kt(k) <= t:
                prev = k
        nxt = next((k for k in kf if kt(k) > t), prev)
        t0, t1 = kt(prev), kt(nxt)
        q = ease(nxt.get("ease", "inout"), (t - t0) / (t1 - t0)) if t1 > t0 else 1.0

        def g(key, d):
            return lerp(float(prev.get(key, d)), float(nxt.get(key, d)), q)
        return g("zoom", 1.0), g("x", 0.5), g("y", 0.5), g("rot", 0.0)
    z, fx, fy, rot = 1.0, 0.5, 0.5, 0.0
    if mv == "push-in":
        z = 1 + a * ease("inout", p) if p <= 1 else 1 + a + a * (p - 1)
    elif mv == "pull-out":
        z = 1 + a * (1 - min(1, p))
    elif mv in ("pan-left", "pan-right", "pan-up", "pan-down"):
        z = 1 + a * 1.5
        q = ease("inout", min(p, 1.0)) if p <= 1 else 1.0
        if mv == "pan-left":
            fx = 1 - q
        elif mv == "pan-right":
            fx = q
        elif mv == "pan-up":
            fy = 1 - q
        else:
            fy = q
    elif mv == "punch-in":
        k = clamp(t / 0.22)
        z = 1 + a * 1.8 * (1 - ease("out", k)) + a * 0.4 * p
    elif mv == "pulse":
        per = (ctx.clock.beat or 0.5) * 2
        z = 1 + a * 0.5 * (0.5 - 0.5 * math.cos(2 * math.pi * t / per))
    elif mv == "drift":
        z = 1 + a * 1.2
        fx, fy = 0.3 + 0.4 * p, 0.35 + 0.3 * p
    elif mv == "handheld":
        z = 1.06 + a * 0.3
        s = ctx.seed
        fx = 0.5 + 0.18 * (math.sin(t * 1.3 + s) * 0.6 + math.sin(t * 2.9 + s * 2) * 0.4)
        fy = 0.5 + 0.18 * (math.sin(t * 1.1 + s * 3) * 0.6 + math.sin(t * 3.7 + s) * 0.4)
        rot = 0.35 * math.sin(t * 1.7 + s)
    elif mv in ("rotate-cw", "rotate-ccw"):
        rot = (-1 if mv == "rotate-cw" else 1) * 3.0 * p
        z = 1.1 + a * 0.5 * p
    elif mv == "tilt":
        rot = 1.6 * math.sin(t * 1.2)
        z = 1.08
        fx = 0.5 + 0.15 * math.sin(t * 0.9)
    return z, fx, fy, rot


def apply_camera_to_frame(img, z, fx, fy, rot):
    """Zoom/pan/rotate an already frame-sized PIL image."""
    W, H = img.size
    if rot:
        need = abs(math.cos(math.radians(rot))) + abs(math.sin(math.radians(rot))) * max(W / H, H / W)
        z = max(z, need)
    if z > 1.0005:
        w, h = W / z, H / z
        x0, y0 = (W - w) * clamp(fx), (H - h) * clamp(fy)
        img = img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h))
    if rot:
        img = img.rotate(rot, Image.BILINEAR)
    return img


def picture_frame(pic, W, H, z, fx, fy, rot, focus=(0.5, 0.5), source=None):
    """Render a Picture covering W x H with a camera move, sampling the full-res source."""
    src = source or pic.rgb
    sw, sh = src.size
    x0, y0, x1, y1 = cover_box(sw, sh, W, H, *focus)
    if rot:
        need = abs(math.cos(math.radians(rot))) + abs(math.sin(math.radians(rot))) * max(W / H, H / W)
        z = max(z, need)
    cw, ch = (x1 - x0) / z, (y1 - y0) / z
    bx0 = x0 + ((x1 - x0) - cw) * clamp(fx)
    by0 = y0 + ((y1 - y0) - ch) * clamp(fy)
    img = src.resize((W, H), Image.BICUBIC if z > 1.3 else Image.BILINEAR, box=(bx0, by0, bx0 + cw, by0 + ch))
    if rot:
        img = img.rotate(rot, Image.BILINEAR)
    return img


def blurred_cover(img, W, H, dim=0.45, radius=None):
    small = img.copy()
    small.thumbnail((max(16, W // 8), max(16, H // 8)))
    sw, sh = small.size
    box = cover_box(sw, sh, W, H)
    small = small.resize((max(8, W // 8), max(8, H // 8)), Image.BILINEAR, box=box)
    small = small.filter(ImageFilter.GaussianBlur(radius or 6))
    big = small.resize((W, H), Image.BILINEAR)
    if dim < 1:
        big = Image.eval(big, lambda v: int(v * dim))
    return big


# =========================================================================== grades & effects

def _lum(a):
    return a[..., 0:1] * 0.299 + a[..., 1:2] * 0.587 + a[..., 2:3] * 0.114


def _sat(a, s):
    L = _lum(a)
    return L + (a - L) * s


def grade(a, name):
    if not name or name == "none":
        return a
    if name == "warm":
        a = a * np.array([1.07, 1.0, 0.9], np.float32)
        return _sat(a, 1.05)
    if name == "cool":
        return a * np.array([0.92, 1.0, 1.08], np.float32)
    if name == "vivid":
        return (_sat(a, 1.35) - 128) * 1.08 + 128
    if name == "muted":
        return (_sat(a, 0.68) - 128) * 0.9 + 128 + 8
    if name == "mono":
        return np.repeat(_lum(a), 3, axis=2)
    if name == "noir":
        return (np.repeat(_lum(a), 3, axis=2) - 128) * 1.35 + 128
    if name == "teal-orange":
        t = _lum(a) / 255.0
        a = a + (1 - t) * np.array([-14, 6, 16], np.float32) + t * np.array([18, 4, -16], np.float32)
        return _sat(a, 1.1)
    if name == "retro":
        a = (_sat(a, 0.78) - 128) * 0.86 + 128
        return a * np.array([1.0, 0.98, 0.9], np.float32) + np.array([16, 10, 4], np.float32)
    if name == "candy":
        t = _lum(a) / 255.0
        return _sat(a, 1.45) + t * np.array([12, -6, 14], np.float32)
    if name == "sunset":
        H = a.shape[0]
        g = np.linspace(1, 0, H, dtype=np.float32)[:, None, None]
        a = a * np.array([1.08, 0.97, 0.88], np.float32) + g * np.array([26, 6, 18], np.float32)
        return _sat(a, 1.12)
    if name == "bright":
        return a * 1.12 + 6
    if name == "dark":
        return a * 0.78
    print(f"unknown grade '{name}', ignored", file=sys.stderr)
    return a


_vig_cache = {}
# Effects that act on the finished frame (text included). All others treat only the
# picture under the layers, so type stays crisp. Override per effect with "on".
FRAME_EFFECTS = {"beat-flash", "flash-in", "glitch-in", "shake"}


def effect(a, name, amt, ctx, t_global, t_local, sc):
    H, W = a.shape[:2]
    if name == "vignette":
        key = (W, H)
        if key not in _vig_cache:
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            d = ((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2) * 2.2
            _vig_cache[key] = np.clip(d, 0, 1)[..., None]
        return a * (1 - 0.55 * amt * _vig_cache[key])
    if name == "grain":
        rng = np.random.default_rng(int(t_global * 1000) + ctx.seed)
        n = rng.normal(0, 9 * amt, (H // 2 + 1, W // 2 + 1)).astype(np.float32)
        n = np.kron(n, np.ones((2, 2), np.float32))[:H, :W, None]
        return a + n
    if name == "chromatic":
        px = int(max(1, ctx.px(10) * amt))
        b = a.copy()
        b[..., 0] = np.roll(a[..., 0], -px, axis=1)
        b[..., 2] = np.roll(a[..., 2], px, axis=1)
        return b
    if name == "scanlines":
        m = np.ones((H, 1, 1), np.float32)
        step = max(2, int(ctx.px(4)))
        m[::step] = 1 - 0.28 * amt
        return a * m
    if name == "pixelate":
        bs = max(2, int(ctx.px(18) * amt))
        im = from_np(a).resize((max(1, W // bs), max(1, H // bs)), Image.BILINEAR).resize((W, H), Image.NEAREST)
        return np.asarray(im, np.float32)
    if name == "posterize":
        lv = max(2, int(6 / max(amt, 0.2)))
        return np.round(a / 255 * lv) / lv * 255
    if name in ("soft-focus", "glow", "bloom"):
        im = from_np(a)
        small = im.resize((W // 4, H // 4), Image.BILINEAR)
        if name == "soft-focus":
            bl = np.asarray(small.filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BILINEAR), np.float32)
            return a * (1 - 0.4 * amt) + bl * 0.4 * amt
        hi = np.clip(np.asarray(small, np.float32) - 170, 0, 255) * 1.6
        hi = from_np(hi).filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR)
        return a + np.asarray(hi, np.float32) * 0.6 * amt
    if name == "beat-flash":
        ph = ctx.beat_phase(t_global)
        if ph is None:
            return a
        return a * (1 + 0.32 * amt * math.exp(-ph * 9))
    if name == "glitch-in":
        k = int(t_local * ctx.fps)
        if k < 4:
            px = int(ctx.px([24, 14, 7, 3][k]) * amt)
            b = a.copy()
            b[..., 0] = np.roll(a[..., 0], -px, axis=1)
            b[..., 2] = np.roll(a[..., 2], px, axis=1)
            return b
        return a
    if name == "flash-in":
        k = int(t_local * ctx.fps)
        if k < 3:
            w = [0.85, 0.5, 0.2][k] * amt
            return a + (255 - a) * w
        return a
    if name == "letterbox":
        b = a.copy()
        bar = int(H * 0.11 * amt)
        b[:bar] = 0
        b[H - bar:] = 0
        return b
    if name == "shake":
        k = t_local
        dx = int(ctx.px(14) * amt * math.sin(k * 55) * math.exp(-k * 6))
        dy = int(ctx.px(10) * amt * math.cos(k * 47) * math.exp(-k * 6))
        return np.roll(np.roll(a, dx, axis=1), dy, axis=0)
    print(f"unknown effect '{name}', ignored", file=sys.stderr)
    return a


# =========================================================================== overlays

_DIAG = {}


def _screen(a, layer):
    return 255 - (255 - a) * (255 - layer) / 255.0


def overlay(a, ov, ctx, t, dur, scene_index):
    kind = ov.get("type")
    amt = float(ov.get("amount", 0.6))
    H, W = a.shape[:2]
    rng = random.Random(ctx.seed * 131 + scene_index * 17 + hash(kind) % 997)
    tint = color(ov.get("tint")) if ov.get("tint") else None
    if kind == "light-leak":
        sm = Image.new("RGB", (max(8, W // 8), max(8, H // 8)), (0, 0, 0))
        d = ImageDraw.Draw(sm)
        cols = [tint or (255, 140, 40, 255), (255, 60, 120, 255), (255, 210, 120, 255)]
        for i in range(3):
            ph = rng.random() * 6.28
            cx = (0.5 + 0.55 * math.sin(t * 0.5 + ph)) * sm.width
            cy = (0.5 + 0.55 * math.cos(t * 0.37 + ph * 1.3)) * sm.height
            r = sm.width * (0.35 + 0.1 * i)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=cols[i][:3])
        sm = sm.filter(ImageFilter.GaussianBlur(sm.width * 0.12))
        layer = np.asarray(sm.resize((W, H), Image.BILINEAR), np.float32) * amt
        return _screen(a, layer)
    if kind == "light-sweep":
        p = clamp(t / max(dur, 0.01))
        sm = Image.new("L", (max(8, W // 6), max(8, H // 6)), 0)
        d = ImageDraw.Draw(sm)
        x = lerp(-0.6, 1.6, ease("inout", p)) * sm.width
        band = sm.width * 0.18
        d.polygon([(x - band, 0), (x + band, 0), (x + band - sm.height * 0.5, sm.height),
                   (x - band - sm.height * 0.5, sm.height)], fill=255)
        sm = sm.filter(ImageFilter.GaussianBlur(sm.width * 0.06))
        m = np.asarray(sm.resize((W, H), Image.BILINEAR), np.float32)[..., None] / 255.0
        col = np.array((tint or (255, 255, 255, 255))[:3], np.float32)
        return _screen(a, m * col * amt)
    if kind == "speed-lines":
        layer = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(layer)
        frame = int(t * ctx.fps)
        r2 = random.Random(frame // 2 + ctx.seed)
        n = int(60 * float(ov.get("density", 1)))
        cx, cy = W / 2, H / 2
        R = math.hypot(W, H)
        for _ in range(n):
            ang = r2.random() * 6.283
            r0 = R * (0.32 + 0.2 * r2.random())
            wdt = max(1, int(ctx.px(3 + 6 * r2.random())))
            d.line((cx + math.cos(ang) * r0, cy + math.sin(ang) * r0, cx + math.cos(ang) * R,
                    cy + math.sin(ang) * R), fill=int(200 * amt), width=wdt)
        m = np.asarray(layer, np.float32)[..., None] / 255.0
        col = np.array((tint or (255, 255, 255, 255))[:3], np.float32)
        return a * (1 - m) + col * m
    if kind == "shimmer":
        # one travelling highlight that brightens only the artwork in the picture (light type, warm or
        # cool print) and leaves the rest alone: a sheen on a label, a logo, a title card
        p = t / max(dur, 0.01)
        start = float(ov.get("start", 0.15))
        span = max(float(ov.get("span", 0.6)), 0.05)
        u = (p - start) / span
        if u < -0.25 or u > 1.25:
            return a
        f = a / 255.0
        r, g, b = f[..., 0], f[..., 1], f[..., 2]
        which = str(ov.get("mask", "bright-warm"))
        thr = float(ov.get("threshold", 0.42))
        m = np.zeros(r.shape, np.float32)
        if "bright" in which:
            m = np.maximum(m, np.clip((0.299 * r + 0.587 * g + 0.114 * b - thr) / 0.18, 0, 1))
        if "warm" in which:
            m = np.maximum(m, np.clip(((r - g) - 0.12) / 0.15, 0, 1))
        if "cool" in which:
            m = np.maximum(m, np.clip(((b - r) - 0.12) / 0.15, 0, 1))
        mi = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(1.0, ctx.px(1.2))))
        m = np.asarray(mi, np.float32) / 255.0
        key = (W, H)
        if key not in _DIAG:
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            _DIAG[key] = (xx / W) * 0.75 + (yy / H) * 0.25
        pos = -0.25 + u * 1.5
        width = float(ov.get("width", 0.07))
        band = np.exp(-((_DIAG[key] - pos) / width) ** 2) * clamp(1 - abs(u - 0.5) * 0.6)
        col = np.array((tint or (255, 247, 230, 255))[:3], np.float32) / 255.0
        gain = (band * m * amt)[..., None]
        return a + (255.0 - a) * gain * col
    # particle families
    n = int({"bokeh": 26, "confetti": 70, "dust": 90, "snow": 120, "rain": 140, "sparkles": 40,
             "embers": 60}.get(kind, 50) * float(ov.get("density", 1)))
    if kind not in ("bokeh", "confetti", "dust", "snow", "rain", "sparkles", "embers"):
        print(f"unknown overlay '{kind}', ignored", file=sys.stderr)
        return a
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    sp = float(ov.get("speed", 1))
    palette = [color(c) for c in ov.get("colors", [])] or \
        [(255, 43, 214, 255), (34, 228, 255, 255), (255, 229, 59, 255), (182, 255, 59, 255), (255, 255, 255, 255)]
    for i in range(n):
        x0, y0, s0, ph = rng.random(), rng.random(), rng.random(), rng.random() * 6.28
        if kind == "bokeh":
            r = ctx.px(30 + 90 * s0)
            x = (x0 + 0.02 * math.sin(t * 0.6 + ph)) * W
            y = ((y0 - t * 0.03 * sp * (0.5 + s0)) % 1.2 - 0.1) * H
            c = tint or palette[i % len(palette)]
            al = int(70 * amt * (0.6 + 0.4 * math.sin(t * 1.5 + ph)))
            d.ellipse((x - r, y - r, x + r, y + r), fill=c[:3] + (al,))
        elif kind == "confetti":
            x = (x0 + 0.04 * math.sin(t * 2 + ph)) * W
            y = ((y0 + t * 0.35 * sp * (0.6 + s0)) % 1.1 - 0.05) * H
            sz = ctx.px(10 + 14 * s0)
            ang = t * 6 * (s0 - 0.5) + ph
            sq = abs(math.cos(t * 5 + ph))
            pts = []
            for dx, dy in ((-1, -0.5), (1, -0.5), (1, 0.5), (-1, 0.5)):
                dx2, dy2 = dx * sz * sq, dy * sz
                pts.append((x + dx2 * math.cos(ang) - dy2 * math.sin(ang),
                            y + dx2 * math.sin(ang) + dy2 * math.cos(ang)))
            c = palette[i % len(palette)]
            d.polygon(pts, fill=c[:3] + (int(255 * amt),))
        elif kind in ("dust", "embers", "sparkles"):
            up = -1 if kind == "embers" else 1
            x = (x0 + 0.03 * math.sin(t * 0.8 + ph)) * W
            y = ((y0 + up * t * 0.02 * sp * (0.3 + s0)) % 1.0) * H
            r = ctx.px(1.5 + 3 * s0) * (2.2 if kind == "sparkles" else 1)
            tw = 0.5 + 0.5 * math.sin(t * (3 + 4 * s0) + ph)
            c = tint or ((255, 150, 60, 255) if kind == "embers" else (255, 255, 255, 255))
            al = int(255 * amt * (tw if kind != "dust" else 0.6))
            if kind == "sparkles":
                rr = r * (1 + 2 * tw)
                d.polygon([(x, y - rr), (x + rr * 0.25, y), (x, y + rr), (x - rr * 0.25, y)], fill=c[:3] + (al,))
                d.polygon([(x - rr, y), (x, y - rr * 0.25), (x + rr, y), (x, y + rr * 0.25)], fill=c[:3] + (al,))
            else:
                d.ellipse((x - r, y - r, x + r, y + r), fill=c[:3] + (al,))
        elif kind == "snow":
            x = (x0 + 0.03 * math.sin(t * 1.2 + ph)) * W
            y = ((y0 + t * 0.09 * sp * (0.5 + s0)) % 1.05) * H
            r = ctx.px(2 + 5 * s0)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(220 * amt)))
        elif kind == "rain":
            x = (x0 + t * 0.15 * sp) % 1.0 * W
            y = ((y0 + t * 1.6 * sp * (0.7 + s0)) % 1.1 - 0.05) * H
            ln = ctx.px(40 + 50 * s0)
            c = tint or (200, 220, 255, 255)
            d.line((x, y, x - ln * 0.15, y - ln), fill=c[:3] + (int(150 * amt),), width=max(1, int(ctx.px(2))))
    if kind == "bokeh":
        layer = layer.filter(ImageFilter.GaussianBlur(ctx.px(6)))
        arr = np.asarray(layer, np.float32)
        m = arr[..., 3:4] / 255.0
        return _screen(a, arr[..., :3] * m)
    arr = np.asarray(layer, np.float32)
    m = arr[..., 3:4] / 255.0
    return a * (1 - m) + arr[..., :3] * m


# =========================================================================== text

class TextLayer:
    def __init__(self, ctx, L):
        self.ctx = ctx
        self.L = L
        S = ctx.S
        txt = str(L.get("text", ""))
        case = L.get("case")
        if case == "upper" or L.get("upper"):
            txt = txt.upper()
        elif case == "lower":
            txt = txt.lower()
        self.text = txt
        self.size = float(L.get("size", 96)) * S
        self.font = load_font(L.get("font"), self.size)
        self.fill = color(L.get("color", "#ffffff"))
        self.grad = [color(c) for c in L["gradient"]] if L.get("gradient") else None
        self.stroke = int(round(float(L.get("stroke", 0)) * S))
        self.stroke_col = color(L.get("stroke_color", "#000000"))
        self.glow = color(L["glow"]) if L.get("glow") else None
        self.glow_r = float(L.get("glow_radius", 18)) * S
        sh = L.get("shadow")
        self.shadow = None
        if sh:
            if sh is True:
                sh = [0, 6, 10, "#000000aa"]
            self.shadow = (sh[0] * S, sh[1] * S, sh[2] * S, color(sh[3] if len(sh) > 3 else "#000000aa"))
        self.panel = L.get("panel")  # {color, opacity, radius, pad}
        self.tracking = float(L.get("tracking", 0)) * S
        self.line_h = float(L.get("line_height", 1.08))
        self.align = L.get("align", "center")
        self.maxw = float(L.get("max_width", 0.88)) * ctx.W
        anim = (L.get("in") or {}).get("anim", "none") if isinstance(L.get("in"), dict) else (L.get("in") or "none")
        self.anim_in = anim
        self.unit_kind = "char" if anim in ("typewriter", "letters", "tracking") else \
            "word" if anim in ("stagger",) else "block"
        self._layout()
        self._render_units()

    # -- layout
    def _adv(self, s):
        return self.font.getlength(s) + self.tracking * max(0, len(s) - 1)

    def _layout(self):
        # auto-shrink so the longest single word fits
        words_all = self.text.split()
        while words_all and max(self._adv(w) for w in words_all) > self.maxw and self.size > 10:
            self.size *= 0.92
            self.font = load_font(self.L.get("font"), self.size)
        lines = []
        for para in self.text.split("\n"):
            cur = []
            for w in para.split(" "):
                trial = " ".join(cur + [w])
                if cur and self._adv(trial) > self.maxw:
                    lines.append(cur)
                    cur = [w]
                else:
                    cur.append(w)
            lines.append(cur)
        asc, desc = self.font.getmetrics()
        lh = (asc + desc) * self.line_h
        units = []  # (text, x, y) relative to block top-left (glyph box origin)
        widths = [self._adv(" ".join(l)) for l in lines]
        bw = max(widths) if widths else 0
        y = 0.0
        for li, l in enumerate(lines):
            lw = widths[li]
            x0 = {"left": 0, "right": bw - lw}.get(self.align, (bw - lw) / 2)
            if self.unit_kind == "block":
                units.append((" ".join(l), x0, y, li))
            elif self.unit_kind == "word":
                x = x0
                for w in l:
                    units.append((w, x, y, li))
                    x += self._adv(w + " ")
            else:
                x = x0
                s = " ".join(l)
                for i, ch in enumerate(s):
                    if ch != " ":
                        units.append((ch, x, y, li))
                    x += self.font.getlength(s[:i + 1]) - self.font.getlength(s[:i]) + self.tracking
            y += lh
        self.lines = lines
        self.block_w, self.block_h = bw, y - (lh - (asc + desc))
        self.units = units

    # -- rasterise
    def _draw_text(self, s):
        pad = int(self.stroke + (self.glow_r * 2 if self.glow else 0) +
                  (abs(self.shadow[0]) + abs(self.shadow[1]) + self.shadow[2] * 2 if self.shadow else 0) + 4)
        l, t, r, b = self.font.getbbox(s, stroke_width=self.stroke)
        asc, desc = self.font.getmetrics()
        w = int(max(r, self._adv(s)) + pad * 2 + 2)
        h = int(max(b, asc + desc) + pad * 2 + 2)
        mask = Image.new("L", (w, h), 0)
        md = ImageDraw.Draw(mask)
        fill_mask = Image.new("L", (w, h), 0)
        fd = ImageDraw.Draw(fill_mask)
        if self.tracking and len(s) > 1:
            x = pad
            for i, ch in enumerate(s):
                md.text((x, pad), ch, font=self.font, fill=255, stroke_width=self.stroke, stroke_fill=255)
                fd.text((x, pad), ch, font=self.font, fill=255)
                x += self.font.getlength(s[:i + 1]) - self.font.getlength(s[:i]) + self.tracking
        else:
            md.text((pad, pad), s, font=self.font, fill=255, stroke_width=self.stroke, stroke_fill=255)
            fd.text((pad, pad), s, font=self.font, fill=255)
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if self.glow:
            g = mask.filter(ImageFilter.GaussianBlur(self.glow_r))
            g = g.point(lambda v: min(255, int(v * 1.7)))
            gl = Image.new("RGBA", (w, h), self.glow[:3] + (0,))
            gl.putalpha(g)
            out.alpha_composite(gl)
        if self.shadow:
            sx, sy, sb, sc = self.shadow
            sm = mask.filter(ImageFilter.GaussianBlur(sb)) if sb > 0 else mask
            sm = sm.point(lambda v: int(v * sc[3] / 255))
            sl = Image.new("RGBA", (w, h), sc[:3] + (0,))
            sl.putalpha(sm)
            out.alpha_composite(sl, (int(sx), int(sy)))
        if self.stroke:
            st = Image.new("RGBA", (w, h), self.stroke_col[:3] + (0,))
            st.putalpha(mask.point(lambda v: int(v * self.stroke_col[3] / 255)))
            out.alpha_composite(st)
        if self.grad:
            ys = np.linspace(0, 1, h, dtype=np.float32)[:, None]
            stops = len(self.grad) - 1
            arr = np.zeros((h, w, 4), np.float32)
            for i in range(stops):
                lo, hi = i / stops, (i + 1) / stops
                m = ((ys >= lo) & (ys <= hi)).astype(np.float32)
                q = np.clip((ys - lo) / (hi - lo), 0, 1)
                c0, c1 = np.array(self.grad[i], np.float32), np.array(self.grad[i + 1], np.float32)
                arr += m[..., None] * (c0 + (c1 - c0) * q[..., None])
            fill = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        else:
            fill = Image.new("RGBA", (w, h), self.fill)
        fill.putalpha(ImageChops.multiply(fill.getchannel("A"), fill_mask))
        out.alpha_composite(fill)
        return out, pad

    def _render_units(self):
        self.tiles = []
        for (s, x, y, li) in self.units:
            tile, pad = self._draw_text(s)
            self.tiles.append((tile, x - pad, y - pad, li))
        P = self.panel
        self.panel_img = None
        if P:
            pad = float(P.get("pad", 26)) * self.ctx.S
            pw, ph = int(self.block_w + pad * 2), int(self.block_h + pad * 2)
            pc = color(P.get("color", "#000000"), P.get("opacity", 0.6))
            im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
            ImageDraw.Draw(im).rounded_rectangle((0, 0, pw - 1, ph - 1), int(float(P.get("radius", 18)) * self.ctx.S),
                                                 fill=pc)
            self.panel_img = (im, -pad, -pad)


def anim_state(name, p, i, n, unit_h, S, t_abs=0.0):
    """Transform for one unit at entrance progress p (0..1). Returns dict."""
    st = {"dx": 0.0, "dy": 0.0, "sx": 1.0, "sy": 1.0, "rot": 0.0, "a": 1.0, "blur": 0.0,
          "clip_x": 1.0, "clip_y": 1.0, "pivot": "c"}
    if p >= 1 or name in (None, "none", "cut"):
        return st
    e = ease("out", p)
    if name == "fade":
        st["a"] = e
    elif name == "pop":
        s = 0.55 + 0.45 * ease("back", p)
        st.update(sx=s, sy=s, a=min(1, p * 3))
    elif name == "zoom-out":
        s = 1 + 0.7 * (1 - e)
        st.update(sx=s, sy=s, a=min(1, p * 2.5))
    elif name == "elastic":
        s = max(0.01, ease("elastic", p))
        st.update(sx=s, sy=s, a=min(1, p * 4))
    elif name == "bounce":
        st.update(dy=(1 - ease("back", p)) * 70 * S, a=min(1, p * 3))
    elif name == "drop":
        st.update(dy=-(1 - ease("bounce", p)) * 420 * S, a=min(1, p * 5))
    elif name.startswith("slide"):
        dirn = name.split("-")[1] if "-" in name else "up"
        d = (1 - e) * 110 * S
        st["dx"], st["dy"] = {"up": (0, d), "down": (0, -d), "left": (d, 0), "right": (-d, 0)}[dirn]
        st["a"] = e
    elif name == "shake":
        k = (1 - p)
        st.update(dx=math.sin(p * 46) * 34 * S * k, rot=math.sin(p * 31) * 4 * k,
                  sx=1 + 0.25 * k * k, sy=1 + 0.25 * k * k, a=min(1, p * 6))
    elif name == "wiggle":
        st.update(rot=14 * math.sin(p * 20) * (1 - p), a=min(1, p * 4), sx=0.8 + 0.2 * e, sy=0.8 + 0.2 * e)
    elif name == "swing":
        st.update(rot=48 * (1 - p) * math.cos(p * 9), a=min(1, p * 4), pivot="n")
    elif name == "spin":
        st.update(rot=200 * (1 - e), sx=0.2 + 0.8 * e, sy=0.2 + 0.8 * e, a=min(1, p * 3))
    elif name == "flip":
        st.update(sx=max(0.02, abs(math.sin(e * math.pi / 2))), a=min(1, p * 3))
    elif name == "unfold":
        st.update(clip_y=e, pivot="n")
    elif name == "reveal":
        st.update(clip_x=e)
    elif name == "blur":
        st.update(blur=22 * S * (1 - e), a=e, sx=1.05 - 0.05 * e, sy=1.05 - 0.05 * e)
    elif name == "rubber":
        k = math.sin(p * math.pi * 3) * (1 - p)
        st.update(sx=1 + 0.38 * k, sy=1 - 0.38 * k, a=min(1, p * 5))
    elif name == "flicker":
        pattern = [0, 1, 0, 0, 1, 0.3, 1, 0, 1, 1, 0.6, 1]
        st["a"] = pattern[min(len(pattern) - 1, int(p * len(pattern)))]
    elif name in ("typewriter",):
        st["a"] = 1.0 if p * n > i else 0.0
    elif name == "letters":
        st.update(dy=(1 - e) * unit_h * 0.6, a=e)
    elif name == "stagger":
        st.update(dy=(1 - e) * unit_h * 0.5, a=e)
    elif name == "tracking":
        st.update(a=e)
    else:
        st["a"] = e
    return st


def exit_state(name, q, S):
    st = {"dx": 0.0, "dy": 0.0, "sx": 1.0, "sy": 1.0, "rot": 0.0, "a": 1.0, "blur": 0.0}
    if q <= 0 or name in (None, "none"):
        return st
    e = ease("in", q)
    if name == "fade":
        st["a"] = 1 - e
    elif name == "pop":
        st.update(sx=1 - 0.5 * e, sy=1 - 0.5 * e, a=1 - e)
    elif name == "blur":
        st.update(blur=20 * S * e, a=1 - e)
    elif name.startswith("slide"):
        dirn = name.split("-")[1] if "-" in name else "down"
        d = e * 120 * S
        st["dx"], st["dy"] = {"up": (0, -d), "down": (0, d), "left": (-d, 0), "right": (d, 0)}[dirn]
        st["a"] = 1 - e
    else:
        st["a"] = 1 - e
    return st


def place_tile(canvas, tile, cx, cy, st, ext=None):
    """Composite a tile centred at (cx, cy) after the transform in st (and ext)."""
    sx, sy = st["sx"] * (ext["sx"] if ext else 1), st["sy"] * (ext["sy"] if ext else 1)
    rot = st["rot"] + (ext["rot"] if ext else 0)
    a = st["a"] * (ext["a"] if ext else 1)
    blur = st["blur"] + (ext["blur"] if ext else 0)
    if a <= 0.003:
        return
    t = tile
    if st.get("clip_x", 1) < 1 or st.get("clip_y", 1) < 1:
        cw = max(1, int(t.width * st.get("clip_x", 1)))
        ch = max(1, int(t.height * st.get("clip_y", 1)))
        m = Image.new("L", t.size, 0)
        ImageDraw.Draw(m).rectangle((0, 0, cw, ch), fill=255)
        t = t.copy()
        t.putalpha(ImageChops.multiply(t.getchannel("A"), m))
    if abs(sx - 1) > 1e-3 or abs(sy - 1) > 1e-3:
        nw, nh = max(1, int(t.width * abs(sx))), max(1, int(t.height * abs(sy)))
        t = t.resize((nw, nh), Image.BICUBIC)
        if sx < 0:
            t = t.transpose(Image.FLIP_LEFT_RIGHT)
    pivot_dy = 0
    if abs(rot) > 0.05:
        if st.get("pivot") == "n":
            pivot_dy = -t.height / 2
        t = t.rotate(rot, Image.BICUBIC, expand=True)
        if pivot_dy:
            # keep the top edge centre fixed
            r = math.radians(rot)
            cy += -pivot_dy - (-pivot_dy) * math.cos(r)
            cx += (-pivot_dy) * math.sin(r)
    if blur > 0.5:
        t = t.filter(ImageFilter.GaussianBlur(blur))
    if a < 0.999:
        t = t.copy()
        t.putalpha(t.getchannel("A").point(lambda v: int(v * a)))
    x = int(round(cx + st["dx"] + (ext["dx"] if ext else 0) - t.width / 2))
    y = int(round(cy + st["dy"] + (ext["dy"] if ext else 0) - t.height / 2))
    if x >= canvas.width or y >= canvas.height or x + t.width <= 0 or y + t.height <= 0:
        return
    canvas.alpha_composite(t, (max(0, x), max(0, y)), (max(0, -x), max(0, -y)))


ANCHORS = {"c": (0.5, 0.5), "center": (0.5, 0.5), "n": (0.5, 0), "s": (0.5, 1), "w": (0, 0.5), "e": (1, 0.5),
           "nw": (0, 0), "ne": (1, 0), "sw": (0, 1), "se": (1, 1)}


def layer_window(ctx, L, scene_dur):
    start = ctx.clock.sec(L.get("start", 0), scene_dur) or 0.0
    end = L.get("end")
    end = ctx.clock.sec(end, scene_dur) if end is not None else None
    if L.get("dur") is not None:
        end = start + ctx.clock.sec(L["dur"], scene_dur)
    return start, end


def anim_params(ctx, spec_in, default_dur):
    if isinstance(spec_in, str):
        return spec_in, default_dur, None
    if not spec_in:
        return "none", default_dur, 0.0
    return (spec_in.get("anim", "fade"), ctx.clock.sec(spec_in.get("dur", default_dur)),
            ctx.clock.sec(spec_in.get("stagger", 0)) if spec_in.get("stagger") is not None else None)


def keyframe_values(ctx, kfs, t):
    """Interpolate x, y, scale, rot, opacity keyframes (t relative to layer start)."""
    out = {}
    if not kfs:
        return out
    kfs = sorted(kfs, key=lambda k: ctx.clock.sec(k.get("t", 0)))
    for key in ("x", "y", "scale", "rot", "opacity"):
        pts = [(ctx.clock.sec(k.get("t", 0)), k[key], k.get("ease", "inout")) for k in kfs if key in k]
        if not pts:
            continue
        if t <= pts[0][0]:
            out[key] = pts[0][1]
        elif t >= pts[-1][0]:
            out[key] = pts[-1][1]
        else:
            for (t0, v0, _), (t1, v1, e1) in zip(pts, pts[1:]):
                if t0 <= t <= t1:
                    out[key] = lerp(v0, v1, ease(e1, (t - t0) / (t1 - t0) if t1 > t0 else 1))
                    break
    return out


def draw_text_layer(canvas, ctx, TL, t_local, scene_dur, t_global):
    L = TL.L
    start, end = layer_window(ctx, L, scene_dur)
    if t_local < start or (end is not None and t_local >= end):
        return
    tl = t_local - start
    name, din, stagger = anim_params(ctx, L.get("in"), 0.3)
    oname, dout, _ = anim_params(ctx, L.get("out"), 0.25)
    n = len(TL.tiles)
    if stagger is None:
        stagger = {"typewriter": 0.045, "letters": 0.035, "stagger": 0.09}.get(name, 0.0)
    if name == "typewriter":
        din_total = max(din, stagger * n)
    kf = keyframe_values(ctx, L.get("keyframes"), tl)
    ax, ay = ANCHORS.get(L.get("anchor", "c"), (0.5, 0.5))
    X = kf.get("x", L.get("x", 0.5)) * ctx.W
    Y = kf.get("y", L.get("y", 0.5)) * ctx.H
    bx = X - TL.block_w * ax
    by = Y - TL.block_h * ay
    ext = {"dx": 0.0, "dy": 0.0, "sx": 1.0, "sy": 1.0, "rot": kf.get("rot", float(L.get("rotate", 0))),
           "a": kf.get("opacity", float(L.get("opacity", 1))), "blur": 0.0}
    sc = kf.get("scale", 1.0)
    bb = float(L.get("beat_bounce", 0))
    if bb and ctx.clock.beat:
        sc *= 1 + bb * math.exp(-ctx.beat_phase(t_global) * 6)
    ext["sx"] = ext["sy"] = sc
    if end is not None and oname != "none":
        q = clamp((tl - (end - start - dout)) / max(dout, 1e-3))
        es = exit_state(oname, q, ctx.S)
        for k in ("dx", "dy", "blur"):
            ext[k] += es[k]
        ext["sx"] *= es["sx"]
        ext["sy"] *= es["sy"]
        ext["a"] *= es["a"]
    # panel
    if TL.panel_img:
        im, ox, oy = TL.panel_img
        pst = anim_state(name if TL.unit_kind == "block" else "fade", clamp(tl / max(din, 1e-3)), 0, 1,
                         TL.size, ctx.S)
        place_tile(canvas, im, bx + ox + im.width / 2, by + oy + im.height / 2, pst, ext)
    asc, desc = TL.font.getmetrics()
    track_spread = 0.0
    if name == "tracking":
        track_spread = (1 - ease("out", clamp(tl / max(din, 1e-3)))) * TL.size * 0.5
    mid = (n - 1) / 2
    for i, (tile, x, y, li) in enumerate(TL.tiles):
        if TL.unit_kind == "block":
            p = clamp(tl / max(din, 1e-3))
        elif name == "typewriter":
            p = clamp(tl / max(din_total, 1e-3))
        else:
            p = clamp((tl - i * stagger) / max(din, 1e-3))
        st = anim_state(name, p, i, n, asc + desc, ctx.S)
        if track_spread:
            st["dx"] += (i - mid) * track_spread / max(1, n) * 2
        # scale/rotate the whole block about its centre
        cx = bx + x + tile.width / 2
        cy = by + y + tile.height / 2
        if abs(ext["sx"] - 1) > 1e-3 or abs(ext["rot"]) > 0.05:
            ox, oy = cx - X, cy - Y
            r = math.radians(-ext["rot"])
            ox, oy = ox * ext["sx"], oy * ext["sy"]
            ox, oy = ox * math.cos(r) - oy * math.sin(r), ox * math.sin(r) + oy * math.cos(r)
            cx, cy = X + ox, Y + oy
        place_tile(canvas, tile, cx, cy, st, ext)


# =========================================================================== image / block / shape / caption layers

class ImageLayer:
    def __init__(self, ctx, L):
        self.ctx = ctx
        self.L = L
        pic = Picture(ctx, L["src"], L.get("crop"))
        im = pic.rgba
        if L.get("cutout"):
            m = pic.matte(L.get("cutout") if L.get("cutout") in ("flat", "rembg") else "auto")
            im = pic.rgb.convert("RGBA")
            im.putalpha(m)
            bb = m.point(lambda v: 255 if v > 20 else 0).getbbox()
            if bb:
                im = im.crop(bb)
        w = L.get("w")
        h = L.get("h")
        if w:
            tw = float(w) * ctx.W
            th = tw * im.height / im.width
            if h and th > float(h) * ctx.H:
                th = float(h) * ctx.H
                tw = th * im.width / im.height
        elif h:
            th = float(h) * ctx.H
            tw = th * im.width / im.height
        else:
            tw, th = im.width * ctx.S, im.height * ctx.S
        im = im.resize((max(1, int(tw)), max(1, int(th))), Image.LANCZOS)
        if L.get("radius"):
            m = Image.new("L", im.size, 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), int(float(L["radius"]) * ctx.S),
                                                fill=255)
            im.putalpha(ImageChops.multiply(im.getchannel("A"), m))
        ol = L.get("outline")
        if ol or L.get("drop_shadow"):
            from matte import stickerize
            im = stickerize(im, (int(float(ol[0]) * ctx.S), ol[1]) if ol else None, bool(L.get("drop_shadow")))
        self.tile = im
        self.glow = L.get("glow")  # colour, "cycle" or None
        if self.glow:
            gm = Image.new("L", (im.width + int(ctx.px(160)), im.height + int(ctx.px(160))), 0)
            off = int(ctx.px(80))
            gm.paste(im.getchannel("A").point(lambda v: 255 if v > 30 else 0), (off, off))
            self.glow_mask = gm.filter(ImageFilter.GaussianBlur(ctx.px(30)))


def draw_image_layer(canvas, ctx, IL, t_local, scene_dur, t_global):
    L = IL.L
    start, end = layer_window(ctx, L, scene_dur)
    if t_local < start or (end is not None and t_local >= end):
        return
    tl = t_local - start
    name, din, _ = anim_params(ctx, L.get("in"), 0.35)
    oname, dout, _ = anim_params(ctx, L.get("out"), 0.25)
    kf = keyframe_values(ctx, L.get("keyframes"), tl)
    ax, ay = ANCHORS.get(L.get("anchor", "c"), (0.5, 0.5))
    X = kf.get("x", L.get("x", 0.5)) * ctx.W
    Y = kf.get("y", L.get("y", 0.5)) * ctx.H
    fl = L.get("float")
    if fl:
        amp = float(fl if not isinstance(fl, dict) else fl.get("amp", 14)) * ctx.S
        per = float(1.8 if not isinstance(fl, dict) else fl.get("period", 1.8))
        Y += amp * math.sin(2 * math.pi * tl / per)
    drift = float(L.get("grow", 0))
    sc = kf.get("scale", 1.0) * (1 + drift * clamp(tl / max(scene_dur, 0.01)))
    bb = float(L.get("beat_bounce", 0))
    if bb and ctx.clock.beat:
        sc *= 1 + bb * math.exp(-ctx.beat_phase(t_global) * 6)
    ext = {"dx": 0.0, "dy": 0.0, "sx": sc, "sy": sc, "rot": kf.get("rot", float(L.get("rotate", 0))),
           "a": kf.get("opacity", float(L.get("opacity", 1))), "blur": 0.0}
    if end is not None and oname != "none":
        q = clamp((tl - (end - start - dout)) / max(dout, 1e-3))
        es = exit_state(oname, q, ctx.S)
        for k in ("dx", "dy", "blur"):
            ext[k] += es[k]
        ext["sx"] *= es["sx"]
        ext["sy"] *= es["sy"]
        ext["a"] *= es["a"]
    st = anim_state(name, clamp(tl / max(din, 1e-3)), 0, 1, IL.tile.height, ctx.S)
    cx = X + IL.tile.width * (0.5 - ax)
    cy = Y + IL.tile.height * (0.5 - ay)
    if IL.glow:
        gcol = hsv(t_global * 0.35) if IL.glow == "cycle" else color(IL.glow)
        gl = Image.new("RGBA", IL.glow_mask.size, gcol[:3] + (0,))
        k = 1.0
        if ctx.clock.beat and L.get("glow_pulse", True):
            k = 0.75 + 0.5 * math.exp(-ctx.beat_phase(t_global) * 5)
        gl.putalpha(IL.glow_mask.point(lambda v: min(255, int(v * 1.6 * k))))
        place_tile(canvas, gl, cx, cy, st, ext)
    place_tile(canvas, IL.tile, cx, cy, st, ext)


def draw_block_layer(canvas, ctx, L, t_local, scene_dur, t_global):
    start, end = layer_window(ctx, L, scene_dur)
    if t_local < start or (end is not None and t_local >= end):
        return
    tl = t_local - start
    w = float(L.get("w", 0.7)) * ctx.W
    tile = blocklib.draw_block(L.get("block"), L.get("props", {}), w, tl, ctx.S)
    ax, ay = ANCHORS.get(L.get("anchor", "c"), (0.5, 0.5))
    X, Y = L.get("x", 0.5) * ctx.W, L.get("y", 0.5) * ctx.H
    name, din, _ = anim_params(ctx, L.get("in"), 0.3)
    oname, dout, _ = anim_params(ctx, L.get("out"), 0.25)
    st = anim_state(name, clamp(tl / max(din, 1e-3)), 0, 1, tile.height, ctx.S)
    ext = None
    if end is not None and oname != "none":
        q = clamp((tl - (end - start - dout)) / max(dout, 1e-3))
        ext = exit_state(oname, q, ctx.S)
    place_tile(canvas, tile, X + tile.width * (0.5 - ax), Y + tile.height * (0.5 - ay), st, ext)


def draw_shape_layer(canvas, ctx, L, t_local, scene_dur, t_global):
    start, end = layer_window(ctx, L, scene_dur)
    if t_local < start or (end is not None and t_local >= end):
        return
    tl = t_local - start
    shape = L.get("shape", "rect")
    W, H = ctx.W, ctx.H
    x, y = L.get("x", 0.5) * W, L.get("y", 0.5) * H
    w, h = L.get("w", 0.5) * W, L.get("h", 0.1) * H
    fill = color(L.get("color", "#ffffff"), L.get("opacity"))
    name, din, _ = anim_params(ctx, L.get("in"), 0.35)
    p = ease("out", clamp(tl / max(din, 1e-3)))
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if name == "draw":  # grow along width
        w = w * p
    elif name != "none":
        fill = fill[:3] + (int(fill[3] * p),)
    if shape == "rect":
        d.rounded_rectangle((x - w / 2, y - h / 2, x + w / 2, y + h / 2), int(float(L.get("radius", 0)) * ctx.S),
                            fill=fill)
    elif shape == "circle":
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=fill)
    elif shape == "ring":
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), outline=fill,
                  width=max(1, int(float(L.get("thickness", 8)) * ctx.S)))
    elif shape == "line":
        d.line((x - w / 2, y, x + w / 2, y), fill=fill, width=max(1, int(float(L.get("thickness", 8)) * ctx.S)))
    canvas.alpha_composite(layer)


class CaptionLayer:
    """Word-timed captions: shows chunks of words, highlights the spoken one."""

    def __init__(self, ctx, L):
        self.ctx = ctx
        self.L = L
        words = L.get("words")
        if isinstance(words, str):
            with open(ctx.path(words)) as f:
                words = json.load(f)
            if isinstance(words, dict):
                words = words.get("words", [])
        self.words = [{"w": w.get("w") or w.get("word") or w.get("text"), "s": float(w.get("s", w.get("start"))),
                       "e": float(w.get("e", w.get("end")))} for w in words]
        n = int(L.get("chunk", 3))
        chunks, cur = [], []
        for w in self.words:
            cur.append(w)
            if len(cur) >= n or w["w"].rstrip().endswith((".", "?", "!", ",")):
                chunks.append(cur)
                cur = []
        if cur:
            chunks.append(cur)
        self.chunks = chunks
        self.cache = {}

    def draw(self, canvas, t_global):
        off = float(self.L.get("offset", 0))
        t = t_global - off
        ch = next((c for c in self.chunks if c[0]["s"] - 0.05 <= t < c[-1]["e"] + 0.15), None)
        if not ch:
            return
        hi = next((i for i, w in enumerate(ch) if w["s"] <= t < w["e"] + 0.05), None)
        key = (id(ch), hi)
        if key not in self.cache:
            base = dict(self.L)
            base.pop("words", None)
            txt = " ".join(w["w"] for w in ch)
            TL = TextLayer(self.ctx, dict(base, text=txt, **{"in": "none"}))
            if hi is not None and self.L.get("highlight"):
                hl = dict(base, text=txt, color=self.L["highlight"], **{"in": "none"})
                TH = TextLayer(self.ctx, hl)
                self.cache[key] = (TL, TH, hi)
            else:
                self.cache[key] = (TL, None, None)
        TL, TH, hi = self.cache[key]
        X, Y = self.L.get("x", 0.5) * self.ctx.W, self.L.get("y", 0.72) * self.ctx.H
        k = clamp((t - ch[0]["s"] + 0.05) / 0.12)
        st = {"dx": 0, "dy": (1 - ease("out", k)) * 20 * self.ctx.S, "sx": 0.92 + 0.08 * ease("back", k),
              "sy": 0.92 + 0.08 * ease("back", k), "rot": 0, "a": k, "blur": 0}
        for tile, x, y, li in TL.tiles:
            place_tile(canvas, tile, X - TL.block_w / 2 + x + tile.width / 2,
                       Y - TL.block_h / 2 + y + tile.height / 2, st)
        if TH is not None:
            # highlight: re-draw the spoken word in the highlight colour on top
            line_words = [l for l in TL.lines]
            flat = [(li, wi) for li, l in enumerate(line_words) for wi in range(len(l))]
            if hi < len(flat):
                li, wi = flat[hi]
                pre = " ".join(line_words[li][:wi]) + (" " if wi else "")
                word = line_words[li][wi]
                lw = TL._adv(" ".join(line_words[li]))
                x0 = {"left": 0, "right": TL.block_w - lw}.get(TL.align, (TL.block_w - lw) / 2)
                asc, desc = TL.font.getmetrics()
                tile, pad = TH._draw_text(word)
                x = x0 + TL._adv(pre) - pad
                y = li * (asc + desc) * TL.line_h - pad
                place_tile(canvas, tile, X - TL.block_w / 2 + x + tile.width / 2,
                           Y - TL.block_h / 2 + y + tile.height / 2, st)


# =========================================================================== transitions

def transition(A, B, kind, p, ctx):
    """Blend outgoing frame A into incoming B; p goes 0 -> 1."""
    H, W = B.shape[:2]
    e = ease("inout", p)
    if kind == "dissolve":
        return A * (1 - e) + B * e
    if kind in ("fade-black", "dip"):
        return A * clamp(1 - p * 2) if p < 0.5 else B * clamp(p * 2 - 1)
    if kind == "flash":
        if p < 0.35:
            return A + (255 - A) * (p / 0.35)
        return B + (255 - B) * (1 - ease("out", (p - 0.35) / 0.65))
    if kind == "grays":
        g = clamp(1 - abs(p - 0.5) * 2)
        X = A if p < 0.5 else B
        L = _lum(X)
        return X * (1 - g) + L * g
    if kind.startswith("wipe-"):
        d = kind.split("-")[1]
        out = A.copy()
        if d == "left":
            c = int(W * (1 - e))
            out[:, c:] = B[:, c:]
        elif d == "right":
            c = int(W * e)
            out[:, :c] = B[:, :c]
        elif d == "up":
            c = int(H * (1 - e))
            out[c:] = B[c:]
        else:
            c = int(H * e)
            out[:c] = B[:c]
        return out
    if kind.startswith("slide-") or kind.startswith("push-") or kind.startswith("whip-"):
        d = kind.split("-")[1]
        ee = ease("inout" if not kind.startswith("whip") else "in", p) if kind.startswith("slide") else \
            ease("inout", p)
        out = np.empty_like(B)
        if d in ("left", "right"):
            off = int(W * ee)
            if d == "left":
                out[:, :W - off] = A[:, off:]
                out[:, W - off:] = B[:, :off]
            else:
                out[:, off:] = A[:, :W - off]
                out[:, :off] = B[:, W - off:]
        else:
            off = int(H * ee)
            if d == "up":
                out[:H - off] = A[off:]
                out[H - off:] = B[:off]
            else:
                out[off:] = A[:H - off]
                out[:off] = B[H - off:]
        if kind.startswith("whip"):
            k = 1 - abs(p - 0.5) * 2
            if k > 0.05:
                im = from_np(out)
                rad = ctx.px(40) * k
                if d in ("left", "right"):
                    im = im.resize((max(1, int(W / (1 + rad / 4))), H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
                else:
                    im = im.resize((W, max(1, int(H / (1 + rad / 4)))), Image.BILINEAR).resize((W, H), Image.BILINEAR)
                out = np.asarray(im, np.float32)
        return out
    if kind == "zoom":
        if p < 0.5:
            z = 1 + ease("in", p * 2) * 0.6
            im = apply_camera_to_frame(from_np(A), z, 0.5, 0.5, 0)
            X = np.asarray(im, np.float32)
            return X + (255 - X) * (p * 2) * 0.25
        z = 1 + (1 - ease("out", (p - 0.5) * 2)) * 0.6
        im = apply_camera_to_frame(from_np(B), z, 0.5, 0.5, 0)
        return np.asarray(im, np.float32)
    if kind == "glitch":
        X = A if p < 0.5 else B
        k = 1 - abs(p - 0.5) * 2
        px = int(ctx.px(36) * k)
        out = X.copy()
        out[..., 0] = np.roll(X[..., 0], -px, axis=1)
        out[..., 2] = np.roll(X[..., 2], px, axis=1)
        rng = random.Random(int(p * 1000))
        for _ in range(int(8 * k)):
            y0 = rng.randrange(0, H)
            hh = rng.randrange(4, max(5, H // 12))
            out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], rng.randrange(-W // 6, W // 6), axis=1)
        return out
    if kind in ("circle-open", "iris-close", "radial", "diagonal", "slice", "bars-open"):
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        R = math.hypot(W, H) / 2
        if kind == "circle-open":
            r = R * e
            d.ellipse((W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r), fill=255)
        elif kind == "iris-close":
            r = R * (1 - e)
            d.rectangle((0, 0, W, H), fill=255)
            d.ellipse((W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r), fill=0)
        elif kind == "radial":
            d.pieslice((W / 2 - R * 1.5, H / 2 - R * 1.5, W / 2 + R * 1.5, H / 2 + R * 1.5), -90, -90 + 360 * e,
                       fill=255)
        elif kind == "diagonal":
            x = (W + H) * e
            d.polygon([(0, 0), (x, 0), (x - H, H), (0, H)], fill=255)
        elif kind == "slice":
            n = 8
            for i in range(n):
                q = ease("out", clamp(p * 1.6 - i / n * 0.6))
                y0, y1 = H * i / n, H * (i + 1) / n
                if i % 2:
                    d.rectangle((W * (1 - q), y0, W, y1), fill=255)
                else:
                    d.rectangle((0, y0, W * q, y1), fill=255)
        elif kind == "bars-open":
            hh = H / 2 * e
            d.rectangle((0, H / 2 - hh, W, H / 2 + hh), fill=255)
        mk = np.asarray(m.filter(ImageFilter.GaussianBlur(ctx.px(3))), np.float32)[..., None] / 255
        return A * (1 - mk) + B * mk
    if kind == "blur":
        k = 1 - abs(p - 0.5) * 2
        X = A * (1 - e) + B * e
        if k > 0.05:
            im = from_np(X)
            sm = im.resize((max(1, int(W / (1 + 12 * k))), H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
            X = np.asarray(sm, np.float32)
        return X
    if kind == "pixelize":
        k = 1 - abs(p - 0.5) * 2
        X = A if p < 0.5 else B
        bs = max(1, int(ctx.px(60) * k))
        if bs > 1:
            im = from_np(X).resize((max(1, W // bs), max(1, H // bs)), Image.BILINEAR).resize((W, H), Image.NEAREST)
            X = np.asarray(im, np.float32)
        return X
    if kind == "squeeze":
        out = np.zeros_like(B)
        wa = max(1, int(W * (1 - e)))
        wb = max(1, W - wa)
        out[:, :wa] = np.asarray(from_np(A).resize((wa, H), Image.BILINEAR), np.float32)
        out[:, wa:] = np.asarray(from_np(B).resize((wb, H), Image.BILINEAR), np.float32)
        return out
    if kind == "light-leak":
        X = A * (1 - e) + B * e
        k = 1 - abs(p - 0.5) * 2
        ov = {"type": "light-leak", "amount": 0.9 * k}
        return overlay(X, ov, ctx, p * 2, 1, 99)
    print(f"unknown transition '{kind}', using a cut", file=sys.stderr)
    return B


# =========================================================================== scenes

class Scene:
    def __init__(self, ctx, sc, index, start):
        self.ctx = ctx
        self.sc = sc
        self.i = index
        self.start = start
        clk = ctx.clock
        if "beats" in sc:
            if not clk.beat:
                die(f"scene {index} uses 'beats' but the spec has no beat.bpm")
            self.dur = float(sc["beats"]) * clk.beat
        else:
            self.dur = clk.sec(sc.get("dur", 2.0))
        self.type = sc.get("type", "clip" if sc.get("src") and not is_image(str(sc.get("src"))) else
                           "image" if sc.get("src") else "color")
        tr = sc.get("transition") or "cut"
        if isinstance(tr, str):
            tr = {"type": tr}
        self.trans = tr.get("type", "cut")
        self.trans_dur = clk.sec(tr.get("dur", 0.3)) if self.trans != "cut" else 0.0
        self.layers = []
        for L in sc.get("layers", []):
            k = L.get("type", "text")
            if k == "text":
                self.layers.append(("text", TextLayer(ctx, L)))
            elif k == "image":
                self.layers.append(("image", ImageLayer(ctx, L)))
            elif k == "block":
                self.layers.append(("block", L))
            elif k == "shape":
                self.layers.append(("shape", L))
            elif k == "captions":
                self.layers.append(("captions", CaptionLayer(ctx, L)))
            else:
                die(f"unknown layer type '{k}' in scene {index}")
        self.pic = None
        if self.type in ("image", "card"):
            self.pic = Picture(ctx, sc["src"], sc.get("crop"))
            if self.type == "card":
                self._prep_card()
        if self.type == "gradient":
            self._prep_gradient()
        self.reader = None

    # ---- frame counts
    def n_frames(self, clock):
        return int(round((self.start + self.dur) * clock.fps)) - int(round(self.start * clock.fps))

    # ---- card
    def _prep_card(self):
        ctx, sc = self.ctx, self.sc
        c = sc.get("card", {})
        pic = self.pic
        im = pic.rgba if pic.has_alpha else pic.rgb.convert("RGBA")
        if c.get("cutout"):
            m = pic.matte("auto")
            im = pic.rgb.convert("RGBA")
            im.putalpha(m)
            bb = m.point(lambda v: 255 if v > 20 else 0).getbbox()
            if bb:
                im = im.crop(bb)
        mw, mh = float(c.get("w", 0.84)) * ctx.W, float(c.get("h", 0.52)) * ctx.H
        s = min(mw / im.width, mh / im.height)
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
        if not c.get("cutout"):
            m = Image.new("L", im.size, 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1),
                                                int(float(c.get("radius", 40)) * ctx.S), fill=255)
            im.putalpha(ImageChops.multiply(im.getchannel("A"), m))
        if c.get("outline") or c.get("drop_shadow", bool(c.get("cutout"))):
            from matte import stickerize
            ol = c.get("outline")
            im = stickerize(im, (int(float(ol[0]) * ctx.S), ol[1]) if ol else None, bool(c.get("drop_shadow", True)))
        self.card_img = im
        g = c.get("glow", "cycle")
        self.card_glow = g
        if g:
            off = int(ctx.px(130))
            gm = Image.new("L", (im.width + off * 2, im.height + off * 2), 0)
            gm.paste(im.getchannel("A").point(lambda v: 255 if v > 30 else 0), (off, off))
            self.card_glow_mask = gm.filter(ImageFilter.GaussianBlur(ctx.px(36)))
        bg = c.get("bg", "blur")
        if bg == "blur":
            self.card_bg = blurred_cover(pic.rgb, ctx.W, ctx.H, float(c.get("bg_dim", 0.42)))
        elif isinstance(bg, list):
            self.card_bg = None
            self.sc = dict(sc, colors=bg)
            self._prep_gradient()
        else:
            self.card_bg = Image.new("RGB", (ctx.W, ctx.H), color(bg)[:3])

    def _prep_gradient(self):
        ctx = self.ctx
        cols = [np.array(color(c)[:3], np.float32) for c in self.sc.get("colors", ["#14002e", "#3a0ca3"])]
        yy, xx = np.mgrid[0:ctx.H, 0:ctx.W].astype(np.float32)
        self.g_xx, self.g_yy = xx / ctx.W - 0.5, yy / ctx.H - 0.5
        self.g_cols = cols

    def _gradient(self, t):
        ang = math.radians(float(self.sc.get("angle", 90)) + float(self.sc.get("spin", 0)) * t)
        proj = self.g_xx * math.cos(ang) + self.g_yy * math.sin(ang)
        proj = np.clip(proj / 0.75 + 0.5, 0, 1)
        n = len(self.g_cols) - 1
        out = np.zeros(proj.shape + (3,), np.float32)
        if n == 0:
            out[:] = self.g_cols[0]
        for i in range(n):
            lo, hi = i / n, (i + 1) / n
            q = np.clip((proj - lo) / (hi - lo), 0, 1)[..., None]
            m = ((proj >= lo) & (proj <= hi))[..., None]
            out = np.where(m, self.g_cols[i] + (self.g_cols[i + 1] - self.g_cols[i]) * q, out)
        hs = float(self.sc.get("hue_shift", 0))
        if hs:
            out = np.roll(out, 1, axis=2) * (0.5 + 0.5 * math.sin(t * hs)) + out * (0.5 - 0.5 * math.sin(t * hs))
        return out

    # ---- base frame
    def open(self, f_from, f_to):
        """Prepare to produce local frames f_from..f_to-1 (may run past the scene end)."""
        clk = self.ctx.clock
        if self.type == "clip":
            n_total = f_to
            times_all = time_map(self.sc, clk, n_total, self.dur)
            self.times_from = f_from
            self.reader = ClipReader(self.ctx, self.sc, times_all[f_from:f_to])

    def close(self):
        if self.reader:
            self.reader.close()
            self.reader = None

    def base(self, f, t):
        ctx, sc = self.ctx, self.sc
        W, H = ctx.W, ctx.H
        p = t / max(self.dur, 1e-6)
        z, fx, fy, rot = camera(sc, p, t, ctx, self.dur)
        if self.type == "clip":
            arr = self.reader.frame(f - self.times_from)
            im = Image.fromarray(arr)
            if im.size != (W, H):
                bg = blurred_cover(im, W, H, float(sc.get("bg_dim", 0.5))) if sc.get("fit", "cover") == "blur" \
                    else Image.new("RGB", (W, H), ctx.bg[:3])
                bg.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
                im = bg
            return apply_camera_to_frame(im, z, fx, fy, rot), None
        if self.type == "image":
            fit = sc.get("fit", "cover")
            focus = tuple(sc.get("focus") or (0.5, 0.5))
            if fit == "cover":
                im = picture_frame(self.pic, W, H, z, fx, fy, rot, focus)
                mt = None
                if any(getattr(Lo, "L", {}).get("behind_subject") for k, Lo in self.layers if k == "text"):
                    mt = picture_frame(self.pic, W, H, z, fx, fy, rot, focus, source=self.pic.matte())
                return im, mt
            bg = blurred_cover(self.pic.rgb, W, H, float(sc.get("bg_dim", 0.5))) if fit == "blur" else \
                Image.new("RGB", (W, H), color(sc.get("bg", "#000000"))[:3])
            fg = self.pic.rgb.copy()
            s = min(W / fg.width, H / fg.height)
            fg = fg.resize((int(fg.width * s), int(fg.height * s)), Image.LANCZOS)
            bg.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
            return apply_camera_to_frame(bg, z, fx, fy, rot), None
        if self.type == "card":
            c = sc.get("card", {})
            if self.card_bg is not None:
                bgim = apply_camera_to_frame(self.card_bg, 1 + 0.05 * p, 0.5, 0.5, 0)
            else:
                bgim = from_np(self._gradient(t))
            canvas = bgim.convert("RGBA")
            ent = c.get("enter", "pop")
            st = anim_state(ent, clamp(t / 0.3), 0, 1, self.card_img.height, ctx.S)
            grow = 1 + float(c.get("grow", 0.04)) * clamp(p)
            ext = {"dx": 0, "dy": 0, "sx": grow, "sy": grow, "rot": float(c.get("rotate", 0)), "a": 1, "blur": 0}
            fl = c.get("float")
            if fl:
                ext["dy"] = float(fl) * ctx.S * math.sin(2 * math.pi * t / 1.8)
            cx, cy = float(c.get("x", 0.5)) * W, float(c.get("y", 0.55)) * H
            if self.card_glow:
                gcol = hsv(self.start * 0.35 + t * 0.35) if self.card_glow == "cycle" else color(self.card_glow)
                k = 1.0
                if ctx.clock.beat:
                    k = 0.75 + 0.5 * math.exp(-ctx.beat_phase(self.start + t) * 5)
                gl = Image.new("RGBA", self.card_glow_mask.size, gcol[:3] + (0,))
                gl.putalpha(self.card_glow_mask.point(lambda v: min(255, int(v * 1.7 * k))))
                place_tile(canvas, gl, cx, cy, st, ext)
            place_tile(canvas, self.card_img, cx, cy, st, ext)
            return canvas.convert("RGB"), None
        if self.type == "gradient":
            return from_np(self._gradient(t)), None
        return Image.new("RGB", (W, H), color(sc.get("color", "#000000"))[:3]), None

    # ---- full composite
    def frame(self, f):
        """Composite local frame f -> float32 HxWx3."""
        ctx, sc = self.ctx, self.sc
        t = f / ctx.fps
        tg = self.start + t
        im, mt = self.base(f, t)
        a = np.asarray(im, np.float32)
        g = sc.get("grade")
        if sc.get("grade_to"):
            p = clamp(t / max(self.dur, 1e-6))
            a = grade(a.copy(), g) * (1 - p) + grade(a.copy(), sc["grade_to"]) * p
        elif g:
            a = grade(a, g)
        amt_g = float(sc.get("grade_amount", 1))
        if amt_g < 1 and g:
            a = np.asarray(im, np.float32) * (1 - amt_g) + a * amt_g
        effs = [(e.get("type"), float(e.get("amount", 1)), e.get("on")) if isinstance(e, dict) else (e, 1.0, None)
                for e in (sc.get("effects") or [])]
        for name, amt, on in effs:
            if (on or ("frame" if name in FRAME_EFFECTS else "picture")) == "picture":
                a = effect(a, name, amt, ctx, tg, t, sc)
        ovs = sc.get("overlay")
        if ovs:
            for ov in (ovs if isinstance(ovs, list) else [ovs]):
                a = overlay(a, ov, ctx, t, self.dur, self.i)
        a = np.clip(a, 0, 255)
        canvas = from_np(a).convert("RGBA")
        behind = [(k, Lo) for k, Lo in self.layers if k == "text" and Lo.L.get("behind_subject")]
        if behind and mt is not None:
            for k, Lo in behind:
                draw_text_layer(canvas, ctx, Lo, t, self.dur, tg)
            subj = from_np(a).convert("RGBA")
            subj.putalpha(mt)
            canvas.alpha_composite(subj)
        elif behind and mt is None:
            pass
        for k, Lo in self.layers:
            if k == "text":
                if Lo.L.get("behind_subject") and mt is not None:
                    continue
                draw_text_layer(canvas, ctx, Lo, t, self.dur, tg)
            elif k == "image":
                draw_image_layer(canvas, ctx, Lo, t, self.dur, tg)
            elif k == "block":
                draw_block_layer(canvas, ctx, Lo, t, self.dur, tg)
            elif k == "shape":
                draw_shape_layer(canvas, ctx, Lo, t, self.dur, tg)
            elif k == "captions":
                Lo.draw(canvas, tg)
        a = np.asarray(canvas.convert("RGB"), np.float32)
        for name, amt, on in effs:
            if (on or ("frame" if name in FRAME_EFFECTS else "picture")) == "frame":
                a = effect(a, name, amt, ctx, tg, t, sc)
        return a


# =========================================================================== build

def load_spec(path):
    with open(path) as f:
        spec = json.load(f)
    if not spec.get("scenes"):
        die("spec has no scenes")
    return spec


def build_scenes(ctx):
    scenes, t = [], 0.0
    for i, sc in enumerate(ctx.spec["scenes"]):
        S = Scene(ctx, sc, i, t)
        scenes.append(S)
        t += S.dur
    return scenes, t


def scene_frame_ranges(scenes, clock):
    out = []
    for S in scenes:
        f0 = int(round(S.start * clock.fps))
        f1 = int(round((S.start + S.dur) * clock.fps))
        out.append((f0, f1))
    return out


def global_fade(a, gf, total_frames, ctx):
    fd = ctx.spec.get("fade") or {}
    fi = ctx.clock.frames(ctx.clock.sec(fd.get("in", 0)))
    fo = ctx.clock.frames(ctx.clock.sec(fd.get("out", 0)))
    if fi and gf < fi:
        a = a * (gf / fi)
    if fo and gf >= total_frames - fo:
        a = a * ((total_frames - 1 - gf) / fo)
    return a


def render_scene_frames(ctx, scenes, i, ranges, total_frames, sink, frame_filter=None):
    """Produce frames for scene i (with its incoming transition) into sink(gf, uint8)."""
    S = scenes[i]
    f0, f1 = ranges[i]
    n = f1 - f0
    tr_n = min(n, ctx.clock.frames(S.trans_dur)) if S.trans != "cut" and i > 0 else 0
    wanted = range(n) if frame_filter is None else [k for k in range(n) if (f0 + k) in frame_filter]
    if not wanted:
        return
    tails = {}
    if tr_n and any(k < tr_n for k in wanted):
        P = scenes[i - 1]
        pf0, pf1 = ranges[i - 1]
        pn = pf1 - pf0
        P.open(pn, pn + tr_n)
        for k in range(tr_n):
            if k in wanted:
                tails[k] = P.frame(pn + k)
            else:
                if P.type == "clip":
                    P.reader.frame(k)  # keep the stream in step
        P.close()
    S.open(0, n)
    for k in range(n):
        if frame_filter is not None and k not in wanted:
            if S.type == "clip" and k < max(wanted):
                S.reader.frame(k)
            continue
        a = S.frame(k)
        if k in tails:
            a = transition(tails[k], a, S.trans, (k + 1) / (tr_n + 1), ctx)
        a = global_fade(a, f0 + k, total_frames, ctx)
        sink(f0 + k, np.clip(a, 0, 255).astype(np.uint8))
        if frame_filter is not None and k >= max(wanted):
            break
    S.close()


def encoder_args(draft):
    if draft:
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]


def encode_scene(ctx, scenes, i, ranges, total_frames, out_path, draft):
    tmp = out_path[:-4] + ".part.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ctx.W}x{ctx.H}",
           "-r", str(ctx.fps), "-i", "-"] + encoder_args(draft) + ["-r", str(ctx.fps), "-an", tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        render_scene_frames(ctx, scenes, i, ranges, total_frames, lambda gf, fr: p.stdin.write(fr.tobytes()))
    finally:
        p.stdin.close()
    if p.wait() != 0:
        die(f"ffmpeg failed encoding scene {i}")
    os.replace(tmp, out_path)


# =========================================================================== audio

def build_audio(ctx, scenes, total, out_audio):
    spec = ctx.spec
    inputs, chains, labels = [], [], []
    idx = 0

    def add(path, ss=None):
        nonlocal idx
        p = ctx.path(path)
        if not os.path.isfile(p):
            die(f"audio file not found: {p}")
        if ss:
            inputs.extend(["-ss", f"{ss:.4f}"])
        inputs.extend(["-i", p])
        idx += 1
        return idx - 1

    mus = spec.get("music")
    music_label = None
    if mus:
        mus = mus if isinstance(mus, dict) else {"src": mus}
        k = add(mus["src"], ctx.clock.sec(mus.get("start", 0)) or None)
        fin = ctx.clock.sec(mus.get("fade_in", 0.05))
        fout = ctx.clock.sec(mus.get("fade_out", 1.5))
        gain = float(mus.get("gain_db", 0))
        at = ctx.clock.sec(mus.get("at", 0)) or 0
        ch = (f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{total + 1:.3f},"
              f"asetpts=PTS-STARTPTS,volume={gain}dB,afade=t=in:d={max(0.01, fin):.3f},"
              f"afade=t=out:st={max(0, total - at - fout):.3f}:d={max(0.01, fout):.3f}")
        if at:
            ch += f",adelay={int(at * 1000)}|{int(at * 1000)}"
        music_label = "mus"
        chains.append(ch + f"[{music_label}]")
    vo_labels = []
    for j, vo in enumerate(spec.get("voiceover", []) or []):
        vo = vo if isinstance(vo, dict) else {"src": vo}
        k = add(vo["src"])
        at = ctx.clock.sec(vo.get("at", 0)) or 0
        lab = f"vo{j}"
        chains.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={float(vo.get('gain_db', 0))}dB,"
                      f"adelay={int(at * 1000)}|{int(at * 1000)}[{lab}]")
        vo_labels.append(lab)
    for j, fx in enumerate(spec.get("sfx", []) or []):
        k = add(fx["src"])
        at = ctx.clock.sec(fx.get("at", 0)) or 0
        lab = f"sfx{j}"
        chains.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={float(fx.get('gain_db', -4))}dB,"
                      f"adelay={int(at * 1000)}|{int(at * 1000)}[{lab}]")
        labels.append(lab)
    for S in scenes:
        sa = S.sc.get("audio")
        if isinstance(sa, dict) and sa.get("src"):
            # sound from another file under this scene (talking-head cutaways: b-roll picture,
            # the speaker's audio continues)
            k = add(sa["src"], ctx.clock.sec(sa.get("in", 0)) or None)
            g = float(sa.get("gain_db", 0))
            lab = f"nat{S.i}"
            at = S.start
            chains.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{S.dur:.3f},"
                          f"asetpts=PTS-STARTPTS,volume={g}dB,afade=t=in:d=0.02,"
                          f"afade=t=out:st={max(0, S.dur - 0.03):.3f}:d=0.03,"
                          f"adelay={int(at * 1000)}|{int(at * 1000)}[{lab}]")
            labels.append(lab)
            continue
        if S.type == "clip" and sa:
            sp = float(S.sc.get("speed", 1))
            if S.sc.get("reverse") or S.sc.get("freeze") or S.sc.get("speed_to") or not (0.5 <= sp <= 2):
                print(f"scene {S.i}: natural sound skipped (reverse/freeze/ramp/extreme speed)", file=sys.stderr)
                continue
            info = probe(ctx.path(S.sc["src"]))
            if not info["has_audio"]:
                continue
            k = add(S.sc["src"], ctx.clock.sec(S.sc.get("in", 0)) or None)
            g = float(sa.get("gain_db", 0)) if isinstance(sa, dict) else 0.0
            lab = f"nat{S.i}"
            at = S.start
            tempo = f",atempo={sp}" if abs(sp - 1) > 1e-3 else ""
            chains.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{S.dur * sp:.3f},"
                          f"asetpts=PTS-STARTPTS{tempo},volume={g}dB,afade=t=in:d=0.04,"
                          f"afade=t=out:st={max(0, S.dur - 0.06):.3f}:d=0.06,"
                          f"adelay={int(at * 1000)}|{int(at * 1000)}[{lab}]")
            labels.append(lab)
    if not chains:
        return False
    mix_inputs = list(labels)
    if vo_labels:
        if len(vo_labels) > 1:
            chains.append("".join(f"[{v}]" for v in vo_labels) + f"amix=inputs={len(vo_labels)}:normalize=0[vomix]")
        else:
            chains.append(f"[{vo_labels[0]}]anull[vomix]")
        if music_label and (mus or {}).get("duck", True):
            chains.append("[vomix]asplit=2[vomain][vokey]")
            chains.append(f"[{music_label}][vokey]sidechaincompress=threshold=0.04:ratio=8:attack=30:release=350[mducked]")
            mix_inputs += ["mducked", "vomain"]
        else:
            mix_inputs += [music_label, "vomix"] if music_label else ["vomix"]
    elif music_label:
        mix_inputs.append(music_label)
    lufs = spec.get("loudness", -14)
    tail = f"atrim=0:{total:.3f},apad=whole_dur={total:.3f}"
    if lufs is not None:
        tail += f",loudnorm=I={float(lufs)}:TP=-1.5:LRA=11"
    chains.append("".join(f"[{m}]" for m in mix_inputs) +
                  f"amix=inputs={len(mix_inputs)}:normalize=0:dropout_transition=0,{tail},"
                  f"aresample=48000[aout]")
    cmd = ["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(chains), "-map", "[aout]",
                                                     "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", out_audio]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        die("audio mix failed (see ffmpeg message above)")
    return True


# =========================================================================== main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--preview", action="store_true",
                    help="accepted for older instructions; renders the full-size video like a plain run")
    ap.add_argument("--scale", type=float,
                    help="quick draft at a fraction of the canvas (0.5 = half size); written as "
                         "<output>_draft.mp4 and not for delivery")
    ap.add_argument("--stills", help="comma-separated seconds to render as JPEG")
    ap.add_argument("--sheet", type=int, help="contact sheet with N evenly spaced frames")
    ap.add_argument("--only", help="comma-separated scene indexes to re-render")
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--out", help="override output path")
    ap.add_argument("--workdir", help="folder for scene files (default: <output>_parts)")
    a = ap.parse_args()
    need_ffmpeg()
    spec = load_spec(a.spec)
    # Every MP4 is rendered at the full canvas size (1080p by default): there is no separate
    # preview file to mistake for the finished video. --scale below 1 is a quick draft for
    # checking a long cut; it is written as <output>_draft.mp4 and is not for delivery.
    if a.scale is not None and not 0 < a.scale <= 1:
        die("--scale must be above 0 and at most 1")
    if a.preview:
        print("note: --preview now renders the full-size video, the same as a plain run", file=sys.stderr)
    scale = a.scale or 1.0
    if (a.stills or a.sheet) and not a.scale:
        scale = 1.0 if a.stills else 0.5
    draft = scale != 1.0 and not (a.stills or a.sheet)
    ctx = Ctx(spec, a.spec, scale)
    scenes, total = build_scenes(ctx)
    ranges = scene_frame_ranges(scenes, ctx.clock)
    total_frames = ranges[-1][1]
    out = ctx.path(a.out or spec.get("output", "video.mp4"))
    if draft and not a.out:
        out = out[:-4] + "_draft.mp4"
    note = f" (draft at {scale:g}x, not for delivery)" if draft else ""
    print(f"{len(scenes)} scenes, {total:.2f}s, {ctx.W}x{ctx.H} @ {ctx.fps}fps{note}", file=sys.stderr)

    if a.stills or a.sheet:
        if a.stills:
            secs = [float(x) for x in a.stills.split(",") if x.strip()]
        else:
            secs = [total * (k + 0.5) / a.sheet for k in range(a.sheet)]
        want = {min(total_frames - 1, int(round(s * ctx.fps))): s for s in secs}
        got = {}
        for i in range(len(scenes)):
            f0, f1 = ranges[i]
            sel = {gf for gf in want if f0 <= gf < f1}
            if sel:
                render_scene_frames(ctx, scenes, i, ranges, total_frames,
                                    lambda gf, fr: got.__setitem__(gf, fr), frame_filter=sel)
        stem = os.path.splitext(out)[0]
        if a.stills:
            paths = []
            for gf in sorted(got):
                p = f"{stem}_still_{gf / ctx.fps:07.3f}s.jpg"
                Image.fromarray(got[gf]).save(p, quality=92)
                paths.append(p)
            print("\n".join(paths))
        else:
            cols = min(6, a.sheet)
            rows = math.ceil(a.sheet / cols)
            tw = 360 if ctx.W <= ctx.H else 480
            th = int(tw * ctx.H / ctx.W)
            sheet = Image.new("RGB", (cols * tw, rows * (th + 26)), (16, 16, 16))
            d = ImageDraw.Draw(sheet)
            f = load_font("sans", 18)
            for n, gf in enumerate(sorted(got)):
                x, y = (n % cols) * tw, (n // cols) * (th + 26)
                sheet.paste(Image.fromarray(got[gf]).resize((tw, th), Image.BILINEAR), (x, y + 26))
                si = next(i for i, (f0, f1) in enumerate(ranges) if f0 <= gf < f1)
                d.text((x + 6, y + 4), f"{gf / ctx.fps:.2f}s  scene {si}", fill=(255, 220, 80), font=f)
            p = f"{stem}_sheet.jpg"
            sheet.save(p, quality=88)
            print(p)
        return

    work = ctx.path(a.workdir) if a.workdir else os.path.splitext(out)[0] + "_parts"
    os.makedirs(work, exist_ok=True)
    tag = "d" if draft else "f"
    files = [os.path.join(work, f"{tag}{i:03d}.mp4") for i in range(len(scenes))]
    if not a.audio_only:
        only = None
        if a.only:
            only = {int(x) for x in a.only.split(",")}
            # a changed scene also changes the transition into the next one
            only |= {i + 1 for i in only if i + 1 < len(scenes) and scenes[i + 1].trans != "cut"}
        for i in range(len(scenes)):
            if only is not None and i not in only and os.path.isfile(files[i]):
                continue
            print(f"scene {i + 1}/{len(scenes)} ({scenes[i].type}, {scenes[i].dur:.2f}s)", file=sys.stderr)
            encode_scene(ctx, scenes, i, ranges, total_frames, files[i], draft)
    lst = os.path.join(work, "concat.txt")
    with open(lst, "w") as f:
        for p in files:
            if not os.path.isfile(p):
                die(f"missing scene file {p}; render without --only first")
            f.write(f"file '{os.path.abspath(p)}'\n")
    video_only = os.path.join(work, "video_only.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    video_only], check=True)
    audio = os.path.join(work, "mix.m4a")
    has_audio = build_audio(ctx, scenes, total_frames / ctx.fps, audio)
    tmp = out[:-4] + ".part.mp4"
    if has_audio:
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", video_only, "-i", audio, "-map", "0:v", "-map", "1:a",
               "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", tmp]
    else:
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", video_only, "-c", "copy", "-movflags", "+faststart", tmp]
    subprocess.run(cmd, check=True)
    os.replace(tmp, out)
    info = probe(out)
    print(json.dumps({"output": out, "seconds": round(info["duration"], 3), "width": info["width"],
                      "height": info["height"], "audio": info["has_audio"], "draft": draft}))


if __name__ == "__main__":
    main()
