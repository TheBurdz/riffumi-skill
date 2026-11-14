"""Cut a subject out of a still image.

    python3 matte.py product.jpg --out product_cutout.png [--mask-out mask.png]
                     [--method auto|flat|rembg] [--tolerance 28] [--feather 2]
                     [--outline 12:#ffffff] [--shadow] [--trim]

Methods
  flat   Background is a near-uniform colour (studio white, a seamless). Uses the
         border colour, a tolerance and a flood fill from the edges, so white
         areas INSIDE the product are kept. Fast, no model, works offline.
  rembg  General photos (people, busy rooms). Needs `pip install rembg onnxruntime`
         and a one-time model download; if that is blocked, this fails clearly.
  auto   flat when the border is uniform, otherwise rembg when installed,
         otherwise flat with a warning.

Prints a JSON report: method used, subject box (fractions), soft share, warnings.
A soft share above ~0.3 or a subject box that fills the frame means the cut is
unreliable: look at the result before building on it.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vdlib import color  # noqa: E402


def border_stats(arr):
    h, w = arr.shape[:2]
    b = max(2, min(h, w) // 100)
    edge = np.concatenate([arr[:b].reshape(-1, 3), arr[-b:].reshape(-1, 3),
                           arr[:, :b].reshape(-1, 3), arr[:, -b:].reshape(-1, 3)])
    med = np.median(edge, axis=0)
    spread = float(np.median(np.abs(edge - med).sum(1)))
    return med, spread


def border_connected(near):
    """Pixels of `near` (bool HxW) connected to the image border.

    Uses scipy when present; otherwise a geodesic dilation on a reduced grid,
    refined at full resolution, so white areas inside the subject stay solid.
    """
    try:
        from scipy import ndimage  # type: ignore
        lab, _ = ndimage.label(near)
        edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        edge = edge[edge > 0]
        return np.isin(lab, edge)
    except Exception:
        pass
    h, w = near.shape
    f = max(1, int(max(h, w) / 420))
    small = near[::f, ::f]
    cur = np.zeros_like(small)
    cur[0], cur[-1], cur[:, 0], cur[:, -1] = small[0], small[-1], small[:, 0], small[:, -1]
    for _ in range(4000):
        g = cur.copy()
        g[1:] |= cur[:-1]
        g[:-1] |= cur[1:]
        g[:, 1:] |= cur[:, :-1]
        g[:, :-1] |= cur[:, 1:]
        g &= small
        if (g == cur).all():
            break
        cur = g
    big = np.repeat(np.repeat(cur, f, 0), f, 1)[:h, :w]
    # grow the coarse result by one cell, then keep only truly near pixels
    m = Image.fromarray(big.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(2 * f + 1))
    return (np.asarray(m) > 0) & near


def flat_matte(img, tolerance=28, feather=2):
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    h, w = rgb.shape[:2]
    med, _ = border_stats(rgb)
    dist = np.abs(rgb - med).sum(2)
    near = dist <= tolerance * 3
    bg = border_connected(near)
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    a = Image.fromarray(alpha, "L")
    # close pin holes, tidy edge, feather
    a = a.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    a = a.filter(ImageFilter.MinFilter(3))  # pull edge in 1px to kill bg fringe
    if feather > 0:
        a = a.filter(ImageFilter.GaussianBlur(feather))
    return a


def rembg_matte(img):
    try:
        from rembg import remove  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("rembg is not installed (pip install rembg onnxruntime)") from e
    out = remove(img.convert("RGB"))
    return out.getchannel("A")


def make_matte(img, method="auto", tolerance=28, feather=2):
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    _, spread = border_stats(rgb)
    warnings = []
    used = method
    if method == "auto":
        if spread < 18:
            used = "flat"
        else:
            try:
                import rembg  # noqa: F401
                used = "rembg"
            except Exception:
                used = "flat"
                warnings.append("background is not uniform and rembg is not installed; "
                                "flat cut may include background")
    if used == "rembg":
        a = rembg_matte(img)
    else:
        a = flat_matte(img, tolerance, feather)
    arr = np.asarray(a, dtype=np.float32) / 255.0
    solid = arr > 0.5
    report = {"method": used, "border_spread": round(spread, 1), "warnings": warnings}
    if solid.any():
        ys, xs = np.where(solid)
        h, w = arr.shape
        report["box"] = [round(float(xs.min() / w), 4), round(float(ys.min() / h), 4),
                         round(float((xs.max() + 1) / w), 4), round(float((ys.max() + 1) / h), 4)]
        inside = arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        report["soft_share"] = round(float(((inside > 0.05) & (inside < 0.95)).mean()), 3)
        report["coverage"] = round(float(solid.mean()), 3)
        if report["coverage"] > 0.97:
            warnings.append("matte covers the whole frame: no background was found")
        if report["soft_share"] > 0.3:
            warnings.append("matte is mostly soft: a hard case (e.g. white on white)")
    else:
        report["box"] = None
        warnings.append("no subject found")
    return a, report


def stickerize(cut, outline=None, shadow=False):
    """Add a sticker outline (px, colour) and/or a soft drop shadow to an RGBA cutout."""
    pad = 0
    if outline:
        pad = max(pad, outline[0] + 2)
    if shadow:
        pad = max(pad, int(max(cut.size) * 0.06))
    if pad:
        big = Image.new("RGBA", (cut.width + pad * 2, cut.height + pad * 2), (0, 0, 0, 0))
        big.alpha_composite(cut, (pad, pad))
        cut = big
    a = cut.getchannel("A")
    out = Image.new("RGBA", cut.size, (0, 0, 0, 0))
    if shadow:
        sh = a.filter(ImageFilter.GaussianBlur(max(2, pad // 3)))
        sh = sh.point(lambda v: int(v * 0.45))
        layer = Image.new("RGBA", cut.size, (0, 0, 0, 0))
        layer.putalpha(sh)
        out.alpha_composite(layer, (0, max(2, pad // 4)))
    if outline:
        w, c = outline
        grown = a.filter(ImageFilter.MaxFilter(w * 2 + 1 if w * 2 + 1 <= 61 else 61))
        if w * 2 + 1 > 61:
            for _ in range((w * 2 + 1) // 61):
                grown = grown.filter(ImageFilter.MaxFilter(61))
        ol = Image.new("RGBA", cut.size, color(c)[:3] + (0,))
        ol.putalpha(grown)
        out.alpha_composite(ol)
    out.alpha_composite(cut)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--out", required=True, help="RGBA PNG cutout")
    ap.add_argument("--mask-out", help="also write the greyscale matte")
    ap.add_argument("--method", default="auto", choices=["auto", "flat", "rembg"])
    ap.add_argument("--tolerance", type=float, default=28)
    ap.add_argument("--feather", type=float, default=2)
    ap.add_argument("--outline", help="width:colour, e.g. 14:#ffffff")
    ap.add_argument("--shadow", action="store_true")
    ap.add_argument("--trim", action="store_true", help="crop to the subject")
    a = ap.parse_args()
    img = Image.open(a.image)
    m, rep = make_matte(img, a.method, a.tolerance, a.feather)
    if a.mask_out:
        m.save(a.mask_out)
    cut = img.convert("RGBA")
    cut.putalpha(m)
    if a.trim and rep.get("box"):
        bb = cut.getchannel("A").getbbox()
        if bb:
            cut = cut.crop(bb)
    ol = None
    if a.outline:
        w, _, c = a.outline.partition(":")
        ol = (int(w), c or "#ffffff")
    if ol or a.shadow:
        cut = stickerize(cut, ol, a.shadow)
    cut.save(a.out)
    rep["out"] = a.out
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
