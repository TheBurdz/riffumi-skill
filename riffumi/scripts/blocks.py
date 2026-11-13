"""Animated information blocks drawn with Pillow.

Every block is a function (props, width_px, t, scale) -> RGBA image, where t is
seconds since the layer started. Heights follow from the width. Blocks only
show what the user supplied: real ratings, real prices, real quotes.
"""
import math

from PIL import Image, ImageDraw, ImageFilter

from vdlib import clamp, color, ease, load_font


def _theme(props):
    dark = str(props.get("theme", "light")).lower() == "dark"
    bg = color(props.get("bg") or ("#15171c" if dark else "#ffffff"))
    fg = color(props.get("fg") or ("#ffffff" if dark else "#14161a"))
    sub = color(props.get("sub") or ("#a3a9b5" if dark else "#646b78"))
    acc = color(props.get("accent", "#2f6bff"))
    return bg, fg, sub, acc


def _font(props, size, bold=True):
    return load_font(props.get("font") or ("sans:bold" if bold else "sans"), size)


def _card(w, h, bg, radius, shadow=True):
    pad = int(h * 0.12) if shadow else 0
    im = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("L", im.size, 0)
        ImageDraw.Draw(sh).rounded_rectangle((pad, pad + pad // 3, pad + w, pad + h + pad // 3),
                                             radius, fill=110)
        sh = sh.filter(ImageFilter.GaussianBlur(max(2, pad // 2)))
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        layer.putalpha(sh)
        im.alpha_composite(layer)
    ImageDraw.Draw(im).rounded_rectangle((pad, pad, pad + w, pad + h), radius, fill=bg)
    return im, pad


def _wrap(draw, text, font, maxw):
    words, lines, cur = str(text).split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if draw.textlength(trial, font=font) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def _stars_row(im, x, y, r, n_full, accent, gap=1.15):
    """Draw 5 stars filling up to n_full (float)."""
    d = ImageDraw.Draw(im)
    for k in range(5):
        cx = x + r + k * r * 2 * gap
        pts = []
        for j in range(10):
            ang = -math.pi / 2 + j * math.pi / 5
            rr = r if j % 2 == 0 else r * 0.45
            pts.append((cx + rr * math.cos(ang), y + rr * math.sin(ang)))
        d.polygon(pts, fill=(200, 200, 200, 120))
        f = clamp(n_full - k)
        if f > 0:
            mask = Image.new("L", im.size, 0)
            ImageDraw.Draw(mask).polygon(pts, fill=255)
            clip = Image.new("L", im.size, 0)
            ImageDraw.Draw(clip).rectangle((cx - r, y - r, cx - r + 2 * r * f, y + r), fill=255)
            from PIL import ImageChops
            mask = ImageChops.multiply(mask, clip)
            fill = Image.new("RGBA", im.size, accent)
            fill.putalpha(mask)
            im.alpha_composite(fill)

# ---------------------------------------------------------------- blocks

def cta(p, w, t, S):
    bg, fg, sub, acc = _theme(p)
    h = int(w * 0.22)
    pulse = 1 + 0.045 * (0.5 + 0.5 * math.sin(t * math.pi * 2 / float(p.get("pulse_period", 0.9))))
    ww, hh = int(w * pulse), int(h * pulse)
    pad = int(h * 0.5)
    im = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    glow = Image.new("L", im.size, 0)
    x0, y0 = (im.width - ww) // 2, (im.height - hh) // 2
    ImageDraw.Draw(glow).rounded_rectangle((x0, y0, x0 + ww, y0 + hh), hh // 2, fill=160)
    glow = glow.filter(ImageFilter.GaussianBlur(pad // 2))
    g = Image.new("RGBA", im.size, acc[:3] + (0,))
    g.putalpha(glow)
    im.alpha_composite(g)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x0, y0, x0 + ww, y0 + hh), hh // 2, fill=acc)
    lab = p.get("label", "Shop now")
    f = _font(p, int(hh * 0.42))
    lc = color(p["label_color"]) if p.get("label_color") else (
        (20, 20, 25, 255) if sum(acc[:3]) > 450 else (255, 255, 255, 255))
    arrow = bool(p.get("arrow", True))
    # The arrow is drawn, not typed: fallback fonts often lack the glyph and
    # render a box instead (seen on the smoke test, 2026-11-12).
    tw = d.textlength(lab, font=f)
    ah = hh * 0.30                     # arrow height
    gap = hh * 0.22
    total = tw + (gap + ah * 1.1 if arrow else 0)
    x = im.width / 2 - total / 2
    cy = im.height / 2
    d.text((x, cy), lab, font=f, fill=lc, anchor="lm")
    if arrow:
        x0 = x + tw + gap
        lw = max(2, int(hh * 0.07))
        d.line([(x0, cy), (x0 + ah, cy)], fill=lc, width=lw)
        d.line([(x0 + ah * 0.55, cy - ah * 0.45), (x0 + ah, cy), (x0 + ah * 0.55, cy + ah * 0.45)],
               fill=lc, width=lw, joint="curve")
    return im


def stars(p, w, t, S):
    bg, fg, sub, acc = _theme(dict(p, accent=p.get("accent", "#ffb400")))
    h = int(w * 0.24)
    val = float(p.get("value", p.get("stars", 5)))
    r = h * 0.22
    f = _font(p, int(h * 0.36))
    f2 = _font(p, int(h * 0.2), bold=False)
    lab = " ".join(str(x) for x in (p.get("count", ""), p.get("label", "")) if x)
    tmp = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    need = h * 0.25 + 5 * r * 2 * 1.15 + h * 0.18 + tmp.textlength(f"{val:g}", font=f) + \
        (h * 0.12 + tmp.textlength(lab, font=f2) if lab else 0) + h * 0.25
    cw = int(max(w, need))
    im, pad = _card(cw, h, bg, h // 4, p.get("card", True))
    k = ease("out", clamp(t / float(p.get("fill_time", 0.9))))
    x0 = pad + (cw - need) / 2 + h * 0.25
    _stars_row(im, x0, pad + h * 0.5, r, val * k, acc)
    d = ImageDraw.Draw(im)
    xt = x0 + 5 * r * 2 * 1.15 + h * 0.18
    d.text((xt, pad + h * 0.5), f"{val:g}", font=f, fill=fg, anchor="lm")
    if lab:
        d.text((xt + d.textlength(f"{val:g}", font=f) + h * 0.12, pad + h * 0.52), lab, font=f2, fill=sub,
               anchor="lm")
    if cw > w:
        s = w / cw
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    return im


def price(p, w, t, S):
    bg, fg, sub, acc = _theme(p)
    h = int(w * 0.42)
    k = ease("back", clamp(t / 0.35))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), int(h * 0.18), fill=acc)
    fc = (20, 20, 25, 255) if sum(acc[:3]) > 450 else (255, 255, 255, 255)
    if p.get("label"):
        d.text((w / 2, h * 0.2), str(p["label"]).upper(), font=_font(p, int(h * 0.14)),
               fill=fc, anchor="mm")
    d.text((w / 2, h * 0.55), str(p.get("price", "")), font=_font(p, int(h * 0.42)), fill=fc,
           anchor="mm")
    if p.get("was"):
        f = _font(p, int(h * 0.15), bold=False)
        txt = str(p["was"])
        tw = d.textlength(txt, font=f)
        y = h * 0.86
        d.text((w / 2, y), txt, font=f, fill=fc[:3] + (190,), anchor="mm")
        d.line((w / 2 - tw / 2 - 4, y, w / 2 + tw / 2 + 4, y), fill=fc, width=max(2, int(h * 0.02)))
    s = max(0.05, k)
    return im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.BICUBIC)


def counter(p, w, t, S):
    bg, fg, sub, acc = _theme(p)
    h = int(w * 0.5)
    k = ease("out", clamp(t / float(p.get("count_time", 1.2))))
    val = float(p.get("value", 0)) * k
    dec = int(p.get("decimals", 0))
    txt = f"{p.get('prefix', '')}{val:,.{dec}f}{p.get('suffix', '')}"
    if p.get("card"):
        im, pad = _card(w, h, bg, h // 6)
    else:
        im, pad = Image.new("RGBA", (w, h), (0, 0, 0, 0)), 0
    d = ImageDraw.Draw(im)
    numc = color(p.get("color")) if p.get("color") else (acc if p.get("card") else (255, 255, 255, 255))
    f = _font(p, int(h * 0.5))
    while d.textlength(txt, font=f) > w * 0.92 and f.size > 10:
        f = _font(p, f.size - 4)
    stroke = 0 if p.get("card") else max(2, int(h * 0.03))
    d.text((pad + w / 2, pad + h * 0.42), txt, font=f, fill=numc, anchor="mm",
           stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    if p.get("label"):
        d.text((pad + w / 2, pad + h * 0.82), str(p["label"]), font=_font(p, int(h * 0.15)),
               fill=sub if p.get("card") else (255, 255, 255, 255), anchor="mm",
               stroke_width=0 if p.get("card") else max(1, stroke // 2), stroke_fill=(0, 0, 0, 255))
    return im


def progress(p, w, t, S):
    bg, fg, sub, acc = _theme(p)
    h = int(w * 0.2)
    im, pad = _card(w, h, bg, h // 4, p.get("card", True))
    d = ImageDraw.Draw(im)
    k = ease("out", clamp(t / float(p.get("fill_time", 1.0))))
    v = clamp(float(p.get("value", 50)) / 100.0) * k
    bx0, by0, bx1, by1 = pad + h * 0.15, pad + h * 0.58, pad + w - h * 0.15, pad + h * 0.8
    d.rounded_rectangle((bx0, by0, bx1, by1), int((by1 - by0) / 2), fill=sub[:3] + (70,))
    if v > 0:
        d.rounded_rectangle((bx0, by0, bx0 + (bx1 - bx0) * v, by1), int((by1 - by0) / 2), fill=acc)
    f = _font(p, int(h * 0.24))
    d.text((bx0, pad + h * 0.3), str(p.get("label", "")), font=f, fill=fg, anchor="lm")
    d.text((bx1, pad + h * 0.3), f"{float(p.get('value', 0)) * k:.0f}{p.get('suffix', '%')}",
           font=f, fill=fg, anchor="rm")
    return im


def checklist(p, w, t, S):
    bg, fg, sub, acc = _theme(p)
    items = list(p.get("items", []))[:6]
    title = p.get("title")
    row = int(w * 0.13)
    h = int(row * (len(items) + (1 if title else 0)) + row * 0.6)
    im, pad = _card(w, h, bg, row // 3, p.get("card", True))
    d = ImageDraw.Draw(im)
    f = _font(p, int(row * 0.42))
    y = pad + row * 0.55
    if title:
        d.text((pad + row * 0.4, y), str(title), font=_font(p, int(row * 0.48)), fill=fg, anchor="lm")
        y += row
    every = float(p.get("every", 0.35))
    for i, it in enumerate(items):
        k = clamp((t - i * every) / 0.25)
        if k <= 0:
            break
        cx = pad + row * 0.65
        r = row * 0.28
        d.ellipse((cx - r, y - r, cx + r, y + r), fill=acc)
        kk = ease("out", k)
        pts = [(cx - r * 0.5, y), (cx - r * 0.1, y + r * 0.4), (cx + r * 0.55, y - r * 0.4)]
        if kk < 0.5:
            q = kk / 0.5
            pts = [pts[0], (lerp_pt(pts[0], pts[1], q))]
        else:
            q = (kk - 0.5) / 0.5
            pts = [pts[0], pts[1], lerp_pt(pts[1], pts[2], q)]
        d.line(pts, fill=(255, 255, 255, 255), width=max(2, int(row * 0.07)), joint="curve")
        col = fg[:3] + (int(255 * k),)
        d.text((cx + row * 0.55, y), str(it), font=f, fill=col, anchor="lm")
        y += row
    return im


def lerp_pt(a, b, q):
    return (a[0] + (b[0] - a[0]) * q, a[1] + (b[1] - a[1]) * q)


def lower_third(p, w, t, S):
    bg, fg, sub, acc = _theme(dict(p, theme=p.get("theme", "dark")))
    h = int(w * 0.2)
    k = ease("out", clamp(t / 0.45))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ww = int(w * k)
    if ww < 2:
        return im
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, ww, h), fill=bg[:3] + (225,))
    d.rectangle((0, 0, int(h * 0.07), h), fill=acc)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rectangle((0, 0, ww, h), fill=255)
    txt = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt)
    td.text((h * 0.25, h * 0.36), str(p.get("name", "")), font=_font(p, int(h * 0.36)), fill=fg, anchor="lm")
    td.text((h * 0.25, h * 0.74), str(p.get("title", "")), font=_font(p, int(h * 0.22), False), fill=sub, anchor="lm")
    from PIL import ImageChops
    txt.putalpha(ImageChops.multiply(txt.getchannel("A"), mask))
    im.alpha_composite(txt)
    return im


def step(p, w, t, S):
    bg, fg, sub, acc = _theme(p)
    h = int(w * 0.3)
    f_lab = _font(p, int(h * 0.3))
    lab = str(p.get("label", ""))
    tmp = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    need = int(h * 1.05 + tmp.textlength(lab, font=f_lab) + h * 0.35)
    cw = max(w, need)  # widen for long labels, then scale the whole block back to w
    if p.get("card"):
        im, pad = _card(cw, h, bg, h // 5)
    else:
        im, pad = Image.new("RGBA", (cw, h), (0, 0, 0, 0)), 0
    d = ImageDraw.Draw(im)
    k = ease("back", clamp(t / 0.35))
    r = h * 0.38 * max(0.01, k)
    cx, cy = pad + h * 0.5, pad + h * 0.5
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=acc)
    nc = (20, 20, 25, 255) if sum(acc[:3]) > 450 else (255, 255, 255, 255)
    if k > 0.3:
        d.text((cx, cy), str(p.get("number", 1)), font=_font(p, int(h * 0.42)), fill=nc, anchor="mm")
    k2 = clamp((t - 0.15) / 0.3)
    labc = fg if p.get("card") else (255, 255, 255, 255)
    d.text((pad + h * 1.05 + (1 - ease("out", k2)) * 30 * S, cy), lab,
           font=f_lab, fill=labc[:3] + (int(255 * k2),), anchor="lm",
           stroke_width=0 if p.get("card") else max(2, int(h * 0.03)), stroke_fill=(0, 0, 0, int(255 * k2)))
    if cw > w:
        s = w / cw
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    return im


def callout(p, w, t, S):
    bg, fg, sub, acc = _theme(p)
    h = int(w * 0.28)
    k = ease("back", clamp(t / 0.3))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ptr = p.get("pointer", "left")
    tip = h * 0.28
    x0, x1, y0, y1 = (tip if ptr == "left" else 0), (w - tip if ptr == "right" else w), 0, h
    if ptr == "down":
        y1 = h - tip
    if ptr == "up":
        y0 = tip
    d.rounded_rectangle((x0, y0, x1 - 1, y1 - 1), int((y1 - y0) / 2), fill=acc)
    cy, cx = (y0 + y1) / 2, w / 2
    tri = {"left": [(0, cy), (x0 + 2, cy - tip * 0.6), (x0 + 2, cy + tip * 0.6)],
           "right": [(w, cy), (x1 - 2, cy - tip * 0.6), (x1 - 2, cy + tip * 0.6)],
           "down": [(cx, h), (cx - tip * 0.6, y1 - 2), (cx + tip * 0.6, y1 - 2)],
           "up": [(cx, 0), (cx - tip * 0.6, y0 + 2), (cx + tip * 0.6, y0 + 2)]}[ptr]
    d.polygon(tri, fill=acc)
    fc = (20, 20, 25, 255) if sum(acc[:3]) > 450 else (255, 255, 255, 255)
    f = _font(p, int((y1 - y0) * 0.42))
    txt = str(p.get("text", ""))
    while d.textlength(txt, font=f) > (x1 - x0) * 0.86 and f.size > 8:
        f = _font(p, f.size - 2)
    d.text(((x0 + x1) / 2, cy), txt, font=f, fill=fc, anchor="mm")
    s = max(0.05, k)
    return im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.BICUBIC)


def review(p, w, t, S):
    bg, fg, sub, acc = _theme(dict(p, accent=p.get("accent", "#ffb400")))
    pad_in = int(w * 0.06)
    f_t = _font(p, int(w * 0.055))
    f_b = _font(p, int(w * 0.045), False)
    f_n = _font(p, int(w * 0.04))
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    body = _wrap(tmp, p.get("text", ""), f_b, w - pad_in * 2)[:6]
    h = int(pad_in * 2 + w * 0.09 + (w * 0.075 if p.get("title") else 0) + len(body) * w * 0.062 + w * 0.07)
    im, pad = _card(w, h, bg, int(w * 0.04))
    d = ImageDraw.Draw(im)
    y = pad + pad_in + w * 0.035
    k = ease("out", clamp(t / 0.9))
    _stars_row(im, pad + pad_in, y, w * 0.035, float(p.get("stars", 5)) * k, acc)
    if p.get("verified"):
        d.text((pad + pad_in + w * 0.42, y), "✓ Verified", font=f_n, fill=color("#16a34a"), anchor="lm")
    y += w * 0.07
    if p.get("title"):
        d.text((pad + pad_in, y), str(p["title"]), font=f_t, fill=fg, anchor="lt")
        y += w * 0.075
    for ln in body:
        d.text((pad + pad_in, y), ln, font=f_b, fill=fg, anchor="lt")
        y += w * 0.062
    d.text((pad + pad_in, y + w * 0.015), "— " + str(p.get("name", "")), font=f_n, fill=sub, anchor="lt")
    return im


def quote(p, w, t, S):
    bg, fg, sub, acc = _theme(p)
    pad_in = int(w * 0.08)
    f_q = _font(p, int(w * 0.06))
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lines = _wrap(tmp, p.get("quote", ""), f_q, w - pad_in * 2)[:6]
    h = int(pad_in * 2 + w * 0.12 + len(lines) * w * 0.08 + w * 0.08)
    im, pad = _card(w, h, bg, int(w * 0.04))
    d = ImageDraw.Draw(im)
    d.text((pad + pad_in, pad + pad_in * 0.5), "“", font=_font(p, int(w * 0.2)), fill=acc, anchor="lt")
    y = pad + pad_in + w * 0.1
    n = len(lines)
    for i, ln in enumerate(lines):
        k = clamp((t - i * 0.12) / 0.3)
        d.text((pad + pad_in, y), ln, font=f_q, fill=fg[:3] + (int(255 * k),), anchor="lt")
        y += w * 0.08
    k = clamp((t - n * 0.12) / 0.3)
    who = str(p.get("name", "")) + (", " + str(p["role"]) if p.get("role") else "")
    d.text((pad + pad_in, y + w * 0.02), "— " + who, font=_font(p, int(w * 0.045)),
           fill=sub[:3] + (int(255 * k),), anchor="lt")
    return im


def countdown(p, w, t, S):
    bg, fg, sub, acc = _theme(dict(p, theme=p.get("theme", "dark")))
    h = int(w * 0.36)
    im, pad = _card(w, h, bg, h // 4)
    d = ImageDraw.Draw(im)
    left = max(0, int(p.get("seconds", 10)) - int(t))
    mm, ss = divmod(left, 60)
    d.text((pad + w / 2, pad + h * 0.3), str(p.get("label", "Ends in")).upper(), font=_font(p, int(h * 0.16)),
           fill=sub, anchor="mm")
    d.text((pad + w / 2, pad + h * 0.66), f"{mm:02d}:{ss:02d}", font=_font(p, int(h * 0.42)), fill=acc, anchor="mm")
    return im


def messages(p, w, t, S):
    bg, fg, sub, acc = _theme(p)
    msgs = list(p.get("messages", []))[:6]
    gap = float(p.get("gap", 0.9))
    f = _font(p, int(w * 0.05), False)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    rows = []
    for m in msgs:
        lines = _wrap(tmp, m.get("text", ""), f, w * 0.62)
        rows.append((m.get("from", "them"), lines))
    lh = w * 0.065
    total = sum(len(ls) * lh + w * 0.07 for _, ls in rows) + w * 0.04
    im = Image.new("RGBA", (w, int(total)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = 0
    for i, (who, lines) in enumerate(rows):
        start = i * gap
        if t < start:
            if t > start - 0.5 and who != "me":
                bx, by = w * 0.02, y
                d.rounded_rectangle((bx, by, bx + w * 0.18, by + w * 0.08), int(w * 0.04), fill=color("#e5e7eb"))
                for j in range(3):
                    a = 120 + int(120 * (0.5 + 0.5 * math.sin(t * 9 - j)))
                    cx = bx + w * 0.05 + j * w * 0.04
                    d.ellipse((cx - w * 0.01, by + w * 0.03, cx + w * 0.01, by + w * 0.05), fill=(90, 90, 90, a))
            break
        bw = max(d.textlength(ln, font=f) for ln in lines) + w * 0.08
        bh = len(lines) * lh + w * 0.04
        me = who == "me"
        bx = w - bw - w * 0.02 if me else w * 0.02
        k = ease("back", clamp((t - start) / 0.3))
        col = acc if me else color("#e5e7eb")
        tc = (255, 255, 255, 255) if me else (20, 20, 25, 255)
        bub = Image.new("RGBA", (int(bw) + 2, int(bh) + 2), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bub)
        bd.rounded_rectangle((0, 0, bw, bh), int(w * 0.04), fill=col)
        yy = w * 0.02
        for ln in lines:
            bd.text((w * 0.04, yy), ln, font=f, fill=tc, anchor="lt")
            yy += lh
        s = max(0.05, k)
        bub = bub.resize((max(1, int(bub.width * s)), max(1, int(bub.height * s))), Image.BICUBIC)
        im.alpha_composite(bub, (int(bx + (bw - bub.width) * (1 if me else 0)), int(y)))
        y += bh + w * 0.03
    return im


def notification(p, w, t, S):
    bg, fg, sub, acc = _theme(p)
    h = int(w * 0.24)
    im, pad = _card(w, h, bg[:3] + (240,), int(h * 0.28))
    d = ImageDraw.Draw(im)
    ic = h * 0.5
    x0, y0 = pad + h * 0.2, pad + h * 0.25
    d.rounded_rectangle((x0, y0, x0 + ic, y0 + ic), int(ic * 0.25), fill=acc)
    d.text((x0 + ic / 2, y0 + ic / 2), str(p.get("icon", "✓")), font=_font(p, int(ic * 0.55)),
           fill=(255, 255, 255, 255), anchor="mm")
    tx = x0 + ic + h * 0.18
    d.text((tx, pad + h * 0.3), str(p.get("app", "")).upper(), font=_font(p, int(h * 0.13), False), fill=sub, anchor="lm")
    d.text((pad + w - h * 0.2, pad + h * 0.3), str(p.get("time", "now")), font=_font(p, int(h * 0.13), False),
           fill=sub, anchor="rm")
    d.text((tx, pad + h * 0.52), str(p.get("title", "")), font=_font(p, int(h * 0.17)), fill=fg, anchor="lm")
    d.text((tx, pad + h * 0.74), str(p.get("text", "")), font=_font(p, int(h * 0.15), False), fill=fg, anchor="lm")
    k = ease("out", clamp(t / 0.4))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(im, (0, int(-(1 - k) * im.height)))
    return out


def comment(p, w, t, S):
    bg, fg, sub, acc = _theme(p)
    f_n = _font(p, int(w * 0.045))
    f_b = _font(p, int(w * 0.05), False)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lines = _wrap(tmp, p.get("text", ""), f_b, w * 0.72)[:4]
    h = int(w * 0.12 + len(lines) * w * 0.068 + w * 0.08)
    im, pad = _card(w, h, bg, int(w * 0.05))
    d = ImageDraw.Draw(im)
    r = w * 0.055
    cx, cy = pad + w * 0.08, pad + w * 0.09
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=acc)
    d.text((cx, cy), str(p.get("initial", str(p.get("name", "?"))[:1])).upper(), font=_font(p, int(r)),
           fill=(255, 255, 255, 255), anchor="mm")
    x = pad + w * 0.17
    d.text((x, pad + w * 0.05), str(p.get("name", "")), font=f_n, fill=sub, anchor="lt")
    y = pad + w * 0.11
    for ln in lines:
        d.text((x, y), ln, font=f_b, fill=fg, anchor="lt")
        y += w * 0.068
    if p.get("likes") is not None:
        k = ease("back", clamp((t - 0.4) / 0.3))
        lk = f"♥ {p['likes']:,}" if isinstance(p["likes"], int) else "♥ " + str(p["likes"])
        if k > 0:
            d.text((pad + w * 0.93, y + w * 0.01), lk, font=f_n, fill=color("#ff3b5c"), anchor="rt")
    return im


BLOCKS = {
    "cta": cta, "button": cta, "stars": stars, "star-rating": stars, "price": price,
    "price-badge": price, "counter": counter, "progress": progress, "progress-bar": progress,
    "checklist": checklist, "lower-third": lower_third, "step": step, "step-number": step,
    "callout": callout, "review": review, "review-card": review, "quote": quote, "quote-card": quote,
    "countdown": countdown, "messages": messages, "text-message": messages,
    "notification": notification, "comment": comment,
}


def draw_block(kind, props, w, t, S):
    fn = BLOCKS.get(kind)
    if not fn:
        raise ValueError(f"unknown block '{kind}'. Known: {', '.join(sorted(BLOCKS))}")
    return fn(props or {}, max(40, int(w)), max(0.0, t), S)
