"""Build the composite shots that make a cut look produced, in one command each.

    # 2-4 clips side by side (or stacked) - turns portrait b-roll into a landscape beat
    python3 compose.py split --out assets/split.mp4 --size 1920x1080 --dur 3.6 \
        broll/a.mp4@2.0 broll/b.mp4@2.6 broll/c.mp4@3.0 [--stack] [--gap 4]

    # a video playing inside a phone over a background clip (or colour) - the "here it is" reveal
    python3 compose.py phone --screen out/promo.mp4@0 --bg broll/neon.mp4@0 --size 1920x1080 \
        --x 0.68 --dur 8.7 --out assets/phone.mp4 [--bg-dim 0.18] [--bg-blur 6]

    # a product cut from its white background onto a flat colour field - for text behind the product
    python3 compose.py field assets/pack.jpg --color "#1a0b3d" --size 1920x1080 --h 0.6 --out assets/hero.png

    # a still turned into a short clip with a slow push (when a composite needs motion)
    python3 compose.py still assets/hero.png --dur 3 --size 1920x1080 --zoom 1.08 --out assets/hero.mp4

clip@seconds sets the in-point. Outputs are 30 fps H.264 and drop straight into a spec as clip scenes.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vdlib import color, die, need_ffmpeg  # noqa: E402


def parse_src(s):
    if "@" in s:
        p, _, t = s.rpartition("@")
        try:
            return p, float(t)
        except ValueError:
            return s, 0.0
    return s, 0.0


def size(s):
    w, _, h = s.lower().partition("x")
    return int(w), int(h)


def enc(out):
    return ["-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-an", out]


def run(cmd):
    r = subprocess.run(cmd)
    if r.returncode != 0:
        die("ffmpeg failed (see message above)")


def split(a):
    W, H = size(a.size)
    n = len(a.clips)
    if not 2 <= n <= 4:
        die("split takes 2-4 clips")
    g = a.gap
    if a.stack:
        cw, ch = W, (H - g * (n - 1)) // n
    else:
        cw, ch = (W - g * (n - 1)) // n, H
    cw, ch = cw // 2 * 2, ch // 2 * 2
    ins, chains = [], []
    for i, c in enumerate(a.clips):
        p, t = parse_src(c)
        if not os.path.isfile(p):
            die(f"missing clip {p}")
        ins += ["-ss", str(t), "-t", str(a.dur + 0.2), "-i", p]
        chains.append(f"[{i}:v]fps=30,scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch},setsar=1[c{i}]")
    pads = []
    for i in range(n):
        x = 0 if a.stack else i * (cw + g)
        y = i * (ch + g) if a.stack else 0
        pads.append((i, x, y))
    gc = color(a.gap_color)
    chains.append(f"color=c=0x{gc[0]:02x}{gc[1]:02x}{gc[2]:02x}:s={W}x{H}:r=30:d={a.dur}[bg]")
    last = "bg"
    for i, x, y in pads:
        chains.append(f"[{last}][c{i}]overlay=x={x}:y={y}:shortest=1[o{i}]")
        last = f"o{i}"
    run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", ";".join(chains), "-map", f"[{last}]",
                                                 "-t", str(a.dur)] + enc(a.out))
    print(a.out)


def phone(a):
    from PIL import Image, ImageDraw
    W, H = size(a.size)
    sh = int(H * a.screen_h) // 2 * 2
    sw = int(sh * 9 / 16) // 2 * 2
    b = max(8, int(sh * 0.025))
    rad = int(sw * 0.095)
    work = os.path.splitext(a.out)[0]
    m = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, sw - 1, sh - 1), rad, fill=255)
    m.save(work + "_mask.png")
    bz = Image.new("RGBA", (sw + 2 * b, sh + 2 * b), (0, 0, 0, 0))
    d = ImageDraw.Draw(bz)
    d.rounded_rectangle((0, 0, sw + 2 * b - 1, sh + 2 * b - 1), rad + b, fill=(14, 14, 20, 255),
                        outline=(90, 90, 110, 255), width=3)
    d.rounded_rectangle((b, b, b + sw - 1, b + sh - 1), rad, fill=(0, 0, 0, 0))
    d.rounded_rectangle(((sw + 2 * b) // 2 - sw // 8, b + 12, (sw + 2 * b) // 2 + sw // 8, b + 12 + sh // 32),
                        sh // 64, fill=(10, 10, 14, 255))
    bz.save(work + "_bezel.png")
    cx, cy = int(W * a.x), int(H * a.y)
    sp, st = parse_src(a.screen)
    if not os.path.isfile(sp):
        die(f"missing screen clip {sp}")
    ins = []
    if a.bg and not a.bg.startswith("#"):
        bp, bt = parse_src(a.bg)
        ins += ["-stream_loop", "-1", "-ss", str(bt), "-i", bp]
        bgc = (f"[0:v]fps=30,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
               f"eq=brightness=-{a.bg_dim}:saturation=1.2,gblur=sigma={a.bg_blur}[bg]")
    else:
        c = color(a.bg or "#111111")
        ins += ["-f", "lavfi", "-i", f"color=c=0x{c[0]:02x}{c[1]:02x}{c[2]:02x}:s={W}x{H}:r=30"]
        bgc = "[0:v]null[bg]"
    ins += ["-ss", str(st), "-t", str(a.dur + 0.2), "-i", sp, "-loop", "1", "-i", work + "_mask.png",
            "-loop", "1", "-i", work + "_bezel.png"]
    fc = (f"{bgc};[1:v]fps=30,scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh},format=rgba[p];"
          f"[2:v]format=gray[m];[p][m]alphamerge[pr];[bg][3:v]overlay=x={cx - sw // 2 - b}:y={cy - sh // 2 - b}[b1];"
          f"[b1][pr]overlay=x={cx - sw // 2}:y={cy - sh // 2}:shortest=1,trim=duration={a.dur}[v]")
    run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", fc, "-map", "[v]", "-t", str(a.dur)] + enc(a.out))
    for f in (work + "_mask.png", work + "_bezel.png"):
        os.remove(f)
    print(a.out)


def field(a):
    from PIL import Image
    from matte import make_matte
    W, H = size(a.size)
    im = Image.open(a.image).convert("RGB")
    m, rep = make_matte(im, a.method)
    for w in rep.get("warnings", []):
        print("matte warning: " + w, file=sys.stderr)
    c = im.convert("RGBA")
    c.putalpha(m)
    bb = m.point(lambda v: 255 if v > 20 else 0).getbbox()
    if bb:
        c = c.crop(bb)
    h = int(H * a.h)
    c = c.resize((max(1, int(c.width * h / c.height)), h), Image.LANCZOS)
    bg = Image.new("RGB", (W, H), color(a.color)[:3])
    x = int(W * a.x - c.width / 2)
    y = H - h - int(H * a.bottom) if a.align == "bottom" else int(H * a.y - h / 2)
    bg.paste(c, (x, y), c)
    bg.save(a.out)
    print(a.out)


def still(a):
    W, H = size(a.size)
    n = int(a.dur * 30)
    z = a.zoom
    vf = (f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
          f"zoompan=z='1+({z}-1)*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps=30")
    run(["ffmpeg", "-v", "error", "-y", "-i", a.image, "-vf", vf, "-frames:v", str(n)] + enc(a.out))
    print(a.out)


def main():
    need_ffmpeg()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split")
    s.add_argument("clips", nargs="+")
    s.add_argument("--out", required=True)
    s.add_argument("--size", default="1920x1080")
    s.add_argument("--dur", type=float, default=3.5)
    s.add_argument("--stack", action="store_true", help="stack vertically instead of side by side")
    s.add_argument("--gap", type=int, default=4)
    s.add_argument("--gap-color", default="#000000")
    p = sub.add_parser("phone")
    p.add_argument("--screen", required=True)
    p.add_argument("--bg", help="clip@in or #colour")
    p.add_argument("--out", required=True)
    p.add_argument("--size", default="1920x1080")
    p.add_argument("--dur", type=float, default=6)
    p.add_argument("--x", type=float, default=0.68)
    p.add_argument("--y", type=float, default=0.5)
    p.add_argument("--screen-h", type=float, default=0.8, help="screen height as a share of the canvas")
    p.add_argument("--bg-dim", type=float, default=0.18)
    p.add_argument("--bg-blur", type=float, default=6)
    f = sub.add_parser("field")
    f.add_argument("image")
    f.add_argument("--out", required=True)
    f.add_argument("--size", default="1920x1080")
    f.add_argument("--color", default="#1a0b3d")
    f.add_argument("--h", type=float, default=0.6)
    f.add_argument("--x", type=float, default=0.5)
    f.add_argument("--y", type=float, default=0.55)
    f.add_argument("--align", default="bottom", choices=["bottom", "center"])
    f.add_argument("--bottom", type=float, default=0.03)
    f.add_argument("--method", default="auto", choices=["auto", "flat", "rembg"])
    t = sub.add_parser("still")
    t.add_argument("image")
    t.add_argument("--out", required=True)
    t.add_argument("--size", default="1920x1080")
    t.add_argument("--dur", type=float, default=3)
    t.add_argument("--zoom", type=float, default=1.08)
    a = ap.parse_args()
    {"split": split, "phone": phone, "field": field, "still": still}[a.cmd](a)


if __name__ == "__main__":
    main()
