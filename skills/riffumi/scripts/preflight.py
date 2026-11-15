"""Check an edit spec before rendering. Fails stop the render; warnings are judgment calls.

    python3 preflight.py spec.json            # human summary, exit 1 on any FAIL
    python3 preflight.py spec.json --json     # machine-readable

Reads spec.meta when present:
  platform        one of the ids below (sets aspect, length and safe-zone checks)
  target_seconds  the length you promised the user
  facts           list of strings the user supplied (claims, numbers, prices, ratings)
  goal            "sell" | "inform" | "story" | ...  (sell expects a call to action)
  music           false when the user asked for no music
  broll           false only when footage truly does not fit (with broll_reason); otherwise a video
                  with no moving footage FAILS and a low share of footage warns
  level           safe | bold (default) | wild - bold and wild must clear the production bar
  concept, device the idea and the signature device, in words (checked for presence)
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vdlib import Clock, is_image  # noqa: E402

# Safe zones are the share of the frame covered by platform UI (top, bottom, left, right).
# Specs drift: re-check the platform's help pages before an ad buy.
PLATFORMS = {
    "tiktok": {"aspect": [(9, 16)], "len": (3, 600), "safe": (0.07, 0.25, 0.06, 0.13)},
    "instagram-reels": {"aspect": [(9, 16)], "len": (3, 180), "safe": (0.14, 0.35, 0.06, 0.06)},
    "facebook-reels": {"aspect": [(9, 16)], "len": (3, 90), "safe": (0.14, 0.35, 0.06, 0.06)},
    "youtube-shorts": {"aspect": [(9, 16), (1, 1)], "len": (1, 180), "safe": (0.07, 0.21, 0.03, 0.09)},
    "youtube": {"aspect": [(16, 9)], "len": (1, 43200), "safe": (0.0, 0.12, 0.0, 0.0)},
    "linkedin": {"aspect": [(9, 16), (4, 5), (1, 1), (16, 9)], "len": (3, 1800), "safe": (0.06, 0.10, 0.04, 0.04)},
    "pinterest": {"aspect": [(9, 16), (2, 3), (4, 5), (1, 1)], "len": (4, 300), "safe": (0.14, 0.41, 0.06, 0.18)},
    "x": {"aspect": [(9, 16), (1, 1), (16, 9), (4, 5)], "len": (1, 140), "safe": (0.08, 0.20, 0.04, 0.12)},
    "snapchat": {"aspect": [(9, 16)], "len": (3, 180), "safe": (0.08, 0.17, 0.0, 0.0)},
    "instagram-feed": {"aspect": [(4, 5), (1, 1)], "len": (3, 3600), "safe": (0.0, 0.0, 0.0, 0.0)},
    "amazon-listing": {"aspect": [(16, 9), (9, 16)], "len": (5, 720), "safe": (0.0, 0.0, 0.0, 0.0)},
    "amazon-sponsored-brands": {"aspect": [(16, 9), (9, 16)], "len": (6, 45), "safe": (0.0, 0.0, 0.0, 0.0)},
    "amazon-sponsored-display": {"aspect": [(16, 9)], "len": (6, 30), "safe": (0.0, 0.0, 0.0, 0.0)},
    "amazon-streaming-tv": {"aspect": [(16, 9)], "len": (15, 60), "safe": (0.05, 0.05, 0.05, 0.05)},
    "shopify": {"aspect": [(1, 1), (16, 9), (9, 16), (4, 5)], "len": (1, 600), "safe": (0, 0, 0, 0)},
    "etsy": {"aspect": [(1, 1), (2, 1), (1, 2), (4, 3)], "len": (5, 15), "safe": (0, 0, 0, 0)},
    "website-hero": {"aspect": [(16, 9), (21, 9)], "len": (4, 60), "safe": (0, 0, 0, 0)},
    "presentation": {"aspect": [(16, 9)], "len": (1, 3600), "safe": (0.05, 0.05, 0.05, 0.05)},
}
CTA_WORDS = ("shop", "buy", "order", "get yours", "link", "try", "visit", "learn more", "sign up", "join",
             "book", "download", "subscribe", "call", "save", "follow", "available", "search", "start")


BLOCK_TEXT_KEYS = ("text", "label", "title", "name", "quote", "role", "price", "was", "value", "count", "stars",
                   "prefix", "suffix", "items", "messages", "seconds")


def text_of(L):
    if L.get("type", "text") == "text":
        return str(L.get("text", ""))
    if L.get("type") == "block":
        pr = L.get("props", {})
        bits = []
        for k in BLOCK_TEXT_KEYS:
            v = pr.get(k)
            if v is None:
                continue
            if isinstance(v, list):
                bits += [m.get("text", "") if isinstance(m, dict) else str(m) for m in v]
            else:
                bits.append(str(v))
        return " ".join(bits)
    return ""


def numbers(s):
    return [re.sub(r"[^\d.]", "", n).rstrip(".") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", s)]


PICTURE_TYPES = ("image", "card", "gradient", "color")
GENERIC_FONTS = ("sans", "sans:bold", "serif", "dejavu", "arial", "helvetica", "")


def _anim(L):
    a = L.get("in")
    if isinstance(a, dict):
        return a.get("anim", "fade")
    return a or "none"


def production_report(spec, scenes, durs, total, clk, level, base, offline=False):
    """Measurable floor for bold/wild work. Returns fails, warns and a 0-100 score.

    offline=True (no asset host reachable, see check_env.py): display fonts
    cannot be fetched, so the fallback-font row warns instead of failing.
    """
    fails, warns = [], []
    pts, maxp = 0, 0

    def check(ok, weight, fail_msg=None, warn_msg=None):
        nonlocal pts, maxp
        maxp += weight
        if ok:
            pts += weight
        elif fail_msg:
            fails.append(fail_msg)
        elif warn_msg:
            warns.append(warn_msg)

    meta = spec.get("meta", {})
    texts = [L for sc in scenes for L in sc.get("layers", []) if L.get("type", "text") == "text"]
    graphic_layers = [L for sc in scenes for L in sc.get("layers", []) if L.get("type") in ("block", "image", "shape")]
    # 1. concept recorded
    check(bool(meta.get("concept")) and bool(meta.get("device")), 10,
          warn_msg="meta.concept and meta.device are empty: write the idea and the signature device into the spec")
    # 2. every scene is alive: motion in the picture plus at least one event
    dead = []
    for i, sc in enumerate(scenes):
        t = sc.get("type") or ("clip" if sc.get("src") and not is_image(sc["src"]) else "image" if sc.get("src") else "color")
        cam = sc.get("camera") not in (None, "none") or bool(sc.get("overlay"))
        animated = [L for L in sc.get("layers", []) if L.get("type") == "block" or _anim(L) != "none" or L.get("keyframes")]
        if t == "image" and not cam:
            dead.append(i)          # a still photo that does not move reads as a slideshow
        elif t in ("color", "gradient") and not animated and not cam:
            dead.append(i)
    check(not dead, 15, fail_msg=f"dead scenes {dead}: a photo with no camera move or overlay, or a colour card with nothing "
                                 f"animating. Give photos a camera move (push-in, pan, punch-in, keyframed path) and "
                                 f"cards an animated layer")
    # 3. beat grid when there is music
    if spec.get("music"):
        on_grid = bool((spec.get("beat") or {}).get("bpm")) and sum(1 for sc in scenes if "beats" in sc) >= len(scenes) * 0.7
        check(on_grid, 10, warn_msg="music without a beat grid: run beats.py, set beat.bpm and give scenes \"beats\" "
                                    "so cuts land on the music")
    # 4. type has character
    fonts = {str(L.get("font", "")).lower() for L in texts}
    font_ok = bool(texts) and not all(f in GENERIC_FONTS for f in fonts)
    if offline:
        check(font_ok, 10, warn_msg="all text uses the fallback font and this host is offline: use an installed "
                                    "display face (fc-list) or the user's own font files; fetch fonts when online")
    else:
        check(font_ok, 10, fail_msg="all text uses the fallback font: fetch display fonts with get_fonts.py (see "
                                    "motion-and-type.md pairings)")
    # 5. entrance variety
    ents = [_anim(L) for L in texts] + [_anim(L) for L in graphic_layers if L.get("in")]
    distinct = {e for e in ents if e not in ("none",)}
    need = 5 if level == "wild" else 4
    plain = sum(1 for e in ents if e in ("none", "fade")) / max(1, len(ents))
    check(len(distinct) >= min(need, max(1, len(ents) - 1)) and plain <= 0.5, 10,
          warn_msg=f"text entrances are samey ({len(distinct)} kinds, {plain:.0%} plain fade/none): use {need}+ kinds "
                   f"matched to the moment (drop/shake for hits, letters/typewriter for titles, stagger for lines)")
    # 6. transition accents
    trs = []
    for sc in scenes[1:]:
        tr = sc.get("transition") or "cut"
        trs.append(tr if isinstance(tr, str) else tr.get("type", "cut"))
    accents = {t for t in trs if t != "cut"}
    need_tr = 3 if level == "wild" else 2
    check(len(accents) >= min(need_tr, max(0, len(scenes) - 1)), 8,
          warn_msg=f"only {len(accents)} accent transition types: mark structure with {need_tr}+ (flash/zoom/whip/"
                   f"glitch for energy, dissolve/light-leak for warmth), hard cuts in between")
    # 7. information density: on-screen events per 10 s
    ev = sum(len(sc.get("layers", [])) for sc in scenes)
    per10 = ev / max(total, 1) * 10
    check(per10 >= (3 if level == "wild" else 2), 8,
          warn_msg=f"{per10:.1f} on-screen events per 10 s: add kinetic type, graphic blocks or callouts (aim 2-4)")
    # 8. hook
    first = scenes[0].get("layers", []) if scenes else []
    hook_ok = any(L.get("type", "text") == "text" and _anim(L) == "none" and float(L.get("size", 0)) >= 110 for L in first)
    check(hook_ok, 8, warn_msg="no big hook line on frame 0 (size >= 110, in: none): the first frame is the thumbnail")
    # 9. texture / effects on bold-wild
    tex = sum(1 for sc in scenes if sc.get("effects") or sc.get("overlay"))
    check(tex >= (3 if level == "wild" else 1), 6,
          warn_msg="no effects or overlays: add grain/vignette for depth and one energy device (beat-flash, glitch-in, "
                   "light-sweep, shimmer, confetti...) where the music peaks")
    # 10. graphic proof
    check(len(graphic_layers) >= 2, 7,
          warn_msg="no information graphics or cutouts: show real facts as blocks (stars, counter, checklist, callout) "
                   "and the product as a cutout/sticker at least once")
    # 11. energy curve: hold lengths vary and something long holds
    if len(durs) >= 5:
        check(max(durs) >= 1.6 * (sum(durs) / len(durs)), 4,
              warn_msg="every hold is about the same length: hold the key moment longest, cut faster before it")
    # 12. a composite / signature shot
    sig = any("split" in str(sc.get("src", "")) or "phone" in str(sc.get("src", "")) for sc in scenes) or \
        any(L.get("behind_subject") or L.get("cutout") for sc in scenes for L in sc.get("layers", [])) or \
        any(sc.get("freeze") or sc.get("speed_to") or sc.get("reverse") for sc in scenes)
    check(sig, 4, warn_msg="no signature shot (split screen, phone reveal, text behind subject, cutout sticker, speed "
                           "ramp, freeze label): add the one your device needs (compose.py builds them)")
    score = int(round(100 * pts / max(1, maxp)))
    floor = 80 if level == "wild" else 65
    if level in ("bold", "wild") and score < floor:
        fails.append(f"production score {score}/100 is under the {level} floor of {floor}: fix the items above")
    return {"fails": fails, "warns": warns, "score": score}


def _cached_offline():
    """True when check_env.py ran in this directory (or a parent) and found no asset host."""
    d = os.getcwd()
    for _ in range(4):
        f = os.path.join(d, ".riffumi_env.json")
        if os.path.isfile(f):
            try:
                return json.load(open(f)).get("online") is False
            except Exception:
                return False
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--offline", action="store_true",
                    help="this host cannot fetch fonts or stock (default: read from .riffumi_env.json "
                         "written by check_env.py, or RIFFUMI_OFFLINE=1)")
    a = ap.parse_args()
    offline = a.offline or os.environ.get("RIFFUMI_OFFLINE") == "1" or _cached_offline()
    with open(a.spec) as f:
        spec = json.load(f)
    base = os.path.dirname(os.path.abspath(a.spec))
    fails, warns, notes = [], [], []
    meta = spec.get("meta", {})
    cv = spec.get("canvas", {})
    W, H, fps = int(cv.get("width", 1080)), int(cv.get("height", 1920)), int(cv.get("fps", 30))
    bt = spec.get("beat") or {}
    clk = Clock(fps, bt.get("bpm"), bt.get("offset", 0))
    scenes = spec.get("scenes", [])
    if not scenes:
        fails.append("no scenes")

    def p(x):
        return x if os.path.isabs(x) else os.path.join(base, x)

    durs, total = [], 0.0
    for i, sc in enumerate(scenes):
        try:
            d = float(sc["beats"]) * clk.beat if "beats" in sc else clk.sec(sc.get("dur", 2.0))
        except Exception as e:
            fails.append(f"scene {i}: bad duration ({e})")
            d = 0
        durs.append(d)
        total += d
        if sc.get("src") and not os.path.isfile(p(sc["src"])):
            fails.append(f"scene {i}: file missing: {sc['src']}")
        for L in sc.get("layers", []):
            if L.get("src") and not os.path.isfile(p(L["src"])):
                fails.append(f"scene {i}: layer file missing: {L['src']}")
        if d < 0.25:
            warns.append(f"scene {i} lasts {d:.2f}s: too short to read anything")
    for key in ("music",):
        m = spec.get(key)
        if m:
            src = m["src"] if isinstance(m, dict) else m
            if not os.path.isfile(p(src)):
                fails.append(f"{key} file missing: {src}")
    for v in spec.get("voiceover", []) or []:
        src = v["src"] if isinstance(v, dict) else v
        if not os.path.isfile(p(src)):
            fails.append(f"voiceover file missing: {src}")

    # length promise
    tgt = meta.get("target_seconds")
    if tgt:
        if total < tgt * 0.85:
            fails.append(f"length {total:.1f}s is well short of the promised {tgt}s")
        elif total > tgt * 1.2:
            warns.append(f"length {total:.1f}s runs past the promised {tgt}s")
    # platform
    plat = PLATFORMS.get(meta.get("platform", ""))
    if meta.get("platform") and not plat:
        notes.append(f"platform '{meta['platform']}' not in the table; aspect/safe-zone checks skipped")
    if plat:
        ok = any(abs(W / H - x / y) < 0.02 for x, y in plat["aspect"])
        if not ok:
            fails.append(f"canvas {W}x{H} is not a {meta['platform']} aspect {plat['aspect']}")
        lo, hi = plat["len"]
        if not lo <= total <= hi:
            fails.append(f"{total:.1f}s is outside {meta['platform']} limits {lo}-{hi}s")
    # music
    if spec.get("music") is None and meta.get("music", True) and not spec.get("voiceover"):
        fails.append("no music and no voiceover: silent videos lose viewers (set meta.music=false if intended)")
    # first frame (thumbnail)
    if scenes:
        first_text = [L for L in scenes[0].get("layers", []) if L.get("type", "text") == "text"]
        if first_text:
            def at_zero(L):
                st = L.get("start", 0)
                anim = L.get("in")
                name = anim if isinstance(anim, str) else (anim or {}).get("anim", "none")
                return (st in (0, "0", None)) and name in ("none", None)
            if not any(at_zero(L) for L in first_text):
                warns.append("frame 0 is the thumbnail: give the hook line in:'none' at start 0 so it is fully "
                             "composed on the first frame")
        elif meta.get("goal") in ("sell", "inform"):
            warns.append("no text on the first scene: the thumbnail frame says nothing")
    # readability, safe zones, claims
    facts = " ".join(meta.get("facts", [])).lower()
    all_text = []
    for i, sc in enumerate(scenes):
        for L in sc.get("layers", []):
            t = text_of(L)
            if not t:
                continue
            all_text.append(t.lower())
            if L.get("type", "text") == "text":
                words = len(t.split())
                start = clk.sec(L.get("start", 0), durs[i]) or 0
                end = clk.sec(L["end"], durs[i]) if L.get("end") is not None else durs[i]
                if L.get("dur") is not None:
                    end = start + clk.sec(L["dur"], durs[i])
                vis = end - start
                # carry-over: same text continues into the next scene counts too
                need = 0.35 + words * 0.22
                if vis < need and not L.get("flash_ok"):
                    warns.append(f"scene {i}: \"{t[:40]}\" is on screen {vis:.2f}s; {words} words need ~{need:.1f}s")
                if plat and plat["safe"] != (0, 0, 0, 0):
                    top, bot, left, right = plat["safe"]
                    y = float(L.get("y", 0.5))
                    x = float(L.get("x", 0.5))
                    if y < top + 0.02 or y > 1 - bot - 0.02:
                        warns.append(f"scene {i}: \"{t[:30]}\" sits at y={y:.2f}, inside the {meta['platform']} UI "
                                     f"zone (keep between {top:.2f} and {1 - bot:.2f})")
                    if x < left or x > 1 - right:
                        warns.append(f"scene {i}: \"{t[:30]}\" sits at x={x:.2f}, under side UI")
            fact_nums = set(numbers(facts))
            for core in numbers(t):
                if core and facts and core not in fact_nums:
                    warns.append(f"scene {i}: number '{core}' in \"{t[:40]}\" is not in meta.facts: verify it")
                elif core and not facts:
                    notes.append(f"scene {i}: number '{core}' on screen; list sources in meta.facts")
    if meta.get("goal") == "sell" and not any(w in " ".join(all_text) for w in CTA_WORDS):
        warns.append("goal is sell but no call to action found on screen")
    # variety
    cams = [sc.get("camera", "none") if isinstance(sc.get("camera", "none"), str) else "path" for sc in scenes
            if sc.get("type", "clip") != "color"]
    if len(cams) >= 4:
        top = max(set(cams), key=cams.count)
        if cams.count(top) / len(cams) > 0.6 and top != "none":
            warns.append(f"camera '{top}' on {cams.count(top)}/{len(cams)} scenes: vary the motion")
        rep = sum(1 for x, y in zip(cams, cams[1:]) if x == y and x not in ("none",))
        if rep >= 3:
            warns.append(f"{rep} neighbouring scenes share a camera move")
    trs = [(sc.get("transition") or "cut") if isinstance(sc.get("transition") or "cut", str)
           else sc["transition"].get("type", "cut") for sc in scenes[1:]]
    if len(trs) >= 5:
        nc = [t for t in trs if t != "cut"]
        if nc and max(nc.count(t) for t in set(nc)) > 0.7 * len(trs):
            warns.append("one transition type dominates: mostly hard cuts plus a few accents reads better")
    if len(durs) >= 5 and not bt.get("bpm"):
        if max(durs) - min(durs) < 0.15:
            warns.append("every scene has the same length: vary the holds (longest on the key moment)")
    if durs and durs[-1] < 1.2:
        warns.append(f"last scene is {durs[-1]:.2f}s: an end card needs ~1.5s+ to be read")
    social = meta.get("platform", "") in ("tiktok", "instagram-reels", "facebook-reels", "youtube-shorts", "snapchat")
    if social:
        for i, d in enumerate(durs):
            if d > 4.5 and scenes[i].get("type") not in ("card",) and not scenes[i].get("layers"):
                warns.append(f"scene {i}: {d:.1f}s with nothing changing is long for {meta['platform']}")
    # moving footage (b-roll by default)
    def is_clip(sc):
        if sc.get("type"):
            return sc["type"] == "clip"
        return bool(sc.get("src")) and not is_image(sc["src"])
    clip_secs = sum(d for sc, d in zip(scenes, durs) if is_clip(sc))
    share = clip_secs / total if total else 0
    res_broll = {"moving_share": round(share, 2)}
    if meta.get("broll") is False:
        if not meta.get("broll_reason"):
            warns.append("meta.broll is false: add meta.broll_reason (why this video has no b-roll)")
        else:
            notes.append(f"no b-roll by choice: {meta['broll_reason']}")
    elif scenes:
        if clip_secs == 0 and offline:
            warns.append("no moving footage and this host is offline (no stock API): use the user's clips, "
                         "generated shots, or animated composites; set meta.broll=false with a reason if none fit")
        elif clip_secs == 0:
            fails.append("no moving footage: plan b-roll (stock or generated) for the non-product beats, or set "
                         "meta.broll=false with meta.broll_reason when footage truly does not fit")
        elif share < 0.4 and meta.get("goal") != "story":
            warns.append(f"only {share:.0%} of the running time is moving footage: add b-roll so it does not read "
                         f"as a slideshow (aim 50-75% for social/promo, 30-50% for explainers)")
        run, worst = 0, 0
        for sc in scenes:
            run = 0 if is_clip(sc) else run + 1
            worst = max(worst, run)
        if worst > 2:
            warns.append(f"{worst} still/card scenes in a row: break them up with footage")
    # ---------------------------------------------------------------- production bar
    level = str(meta.get("level", "bold")).lower()
    prod = production_report(spec, scenes, durs, total, clk, level, base, offline=offline)
    if level in ("bold", "wild"):
        for msg in prod["fails"]:
            fails.append("production: " + msg)
        for msg in prod["warns"]:
            warns.append("production: " + msg)
    else:
        for msg in prod["fails"] + prod["warns"]:
            notes.append("production (safe level, advisory): " + msg)
    res_broll["production_score"] = prod["score"]
    # behind-subject on clips
    for i, sc in enumerate(scenes):
        if any(L.get("behind_subject") for L in sc.get("layers", [])) and sc.get("src") and \
                not is_image(sc["src"]):
            warns.append(f"scene {i}: behind_subject works on still images only; on a clip the text sits on top")
    res = {"seconds": round(total, 2), "scenes": len(scenes), "canvas": f"{W}x{H}@{fps}", "offline": offline, **res_broll, "fails": fails,
           "warnings": warns, "notes": notes, "ok": not fails}
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        print(f"{res['canvas']}  {len(scenes)} scenes  {total:.2f}s  moving footage {res.get('moving_share', 0):.0%}  "
              f"production score {res.get('production_score', '-')}/100 ({level}{', offline host' if offline else ''})")
        for x in fails:
            print("FAIL  " + x)
        for x in warns:
            print("WARN  " + x)
        for x in notes:
            print("note  " + x)
        print("PASS" if not fails else "FIX THE FAILS BEFORE RENDERING")
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
