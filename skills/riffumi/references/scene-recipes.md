# Scene recipes - proven building blocks

Copy, then change the words, files, colours and timing to fit the concept. Every recipe below
comes from a finished video that cleared the production bar. Positions are for **16:9
(1920x1080)**; for **9:16** keep x near 0.5, move text into the upper third (y 0.15-0.35) and
keep the bottom 25-35% clear of anything important.

Combine recipes into a structure (`creative-system.md`); never run them in a fixed order. A
strong 30-60 s piece usually uses 6-9 different recipes, one of them as the signature device.

Timing: with music, use `"beats"` for scene length and `"Nb"` for layer starts (beats from the
scene start), so everything lands on the music.

---

## 1. Hook slam (frame 0 = thumbnail)
Moving b-roll, one huge line already on screen at frame 0, a second line arriving on the beat.
```json
{"src": "broll/world.mp4", "in": 1.0, "beats": 8, "camera": "push-in", "camera_amount": 0.06,
 "grade": "teal-orange", "effects": ["vignette", {"type": "grain", "amount": 0.7}],
 "layers": [
  {"text": "ONE ASIN.", "font": "Bungee", "size": 230, "y": 0.4, "color": "#ffffff", "glow": "#ff2bd6", "glow_radius": 26, "in": "none", "beat_bounce": 0.03},
  {"text": "one produced video", "font": "SpaceGrotesk-700", "size": 84, "y": 0.6, "color": "#22e4ff", "case": "upper", "tracking": 6, "start": "4b", "in": {"anim": "letters", "dur": 0.5}}]}
```

## 2. The ask (a conversation as the story engine)
Someone types; a chat thread answers. Great for tools, services, "you ask, we deliver".
```json
{"src": "broll/typing.mp4", "in": 2.0, "beats": 8, "camera": "drift", "transition": {"type": "glitch", "dur": 0.2},
 "layers": [
  {"text": "Just ask.", "font": "Bungee", "size": 150, "x": 0.24, "y": 0.44, "stroke": 6, "stroke_color": "#0d0221", "in": {"anim": "pop", "dur": 0.35}},
  {"type": "block", "block": "messages", "x": 0.74, "y": 0.5, "w": 0.44, "start": "1b",
   "props": {"accent": "#ff2bd6", "gap": 2.2, "messages": [{"from": "me", "text": "<the request>"}, {"from": "them", "text": "On it."}]}}]}
```

## 3. Product hero with proof
The real product cut out as a sticker, glowing, floating; proof blocks land beat by beat.
```json
{"type": "card", "src": "assets/pack.jpg", "beats": 8, "transition": {"type": "circle-open", "dur": 0.35},
 "card": {"cutout": true, "outline": [10, "#ffffff"], "w": 0.4, "h": 0.74, "x": 0.7, "y": 0.52,
          "bg": ["#0d0221", "#3a0ca3", "#7209b7"], "glow": "cycle", "float": 10, "rotate": -3, "enter": "elastic"},
 "overlay": {"type": "bokeh", "amount": 0.45},
 "layers": [
  {"type": "block", "block": "stars", "x": 0.06, "y": 0.42, "anchor": "w", "w": 0.46, "start": "2b", "props": {"value": 4.4, "count": "42,000+", "label": "ratings"}},
  {"type": "block", "block": "callout", "x": 0.06, "y": 0.68, "anchor": "w", "w": 0.36, "start": "4b", "props": {"text": "<real benefit>", "pointer": "right", "accent": "#ffe53b"}}]}
```

## 4. Countdown into the drop
Four beats, one number per beat, the drop lands on the next scene's flash.
```json
{"src": "broll/abstract_light.mp4", "in": 2, "beats": 4, "effects": ["beat-flash", "vignette"],
 "layers": [
  {"text": "3", "font": "Bungee", "size": 420, "color": "#22e4ff", "glow": "#22e4ff", "end": "1b", "in": {"anim": "drop", "dur": 0.25}, "flash_ok": true},
  {"text": "2", "font": "Bungee", "size": 420, "color": "#ff2bd6", "glow": "#ff2bd6", "start": "1b", "end": "2b", "in": {"anim": "drop", "dur": 0.25}, "flash_ok": true},
  {"text": "1", "font": "Bungee", "size": 420, "color": "#ffe53b", "glow": "#ffe53b", "start": "2b", "end": "3b", "in": {"anim": "drop", "dur": 0.25}, "flash_ok": true},
  {"text": "GO", "font": "Bungee", "size": 300, "glow": "#ff2bd6", "start": "3b", "in": {"anim": "shake", "dur": 0.3}, "flash_ok": true}]}
```
Put the countdown so its last beat is one beat before the music's drop (`beats.py` reports it).

## 5. Kinetic word stack
Three short lines stack on alternating beats, each with a different entrance, over energetic footage.
```json
{"src": "broll/energy.mp4", "beats": 8, "transition": {"type": "flash", "dur": 0.15}, "camera": "pulse",
 "grade": "vivid", "effects": ["beat-flash", "glitch-in"],
 "layers": [
  {"text": "PARTY MODE", "font": "Bungee", "size": 150, "y": 0.38, "stroke": 9, "stroke_color": "#0d0221", "start": "1b", "in": {"anim": "shake", "dur": 0.3}},
  {"text": "16M COLORS", "font": "Bungee", "size": 150, "y": 0.58, "color": "#ffe53b", "stroke": 9, "stroke_color": "#0d0221", "start": "3b", "in": {"anim": "drop", "dur": 0.35}},
  {"text": "YOUR ROOM CALLED", "font": "Bungee", "size": 130, "y": 0.78, "color": "#22e4ff", "stroke": 9, "stroke_color": "#0d0221", "start": "5b", "in": {"anim": "elastic", "dur": 0.4}}]}
```

## 6. Words on the beat
One word per beat across the frame. Pure rhythm; perfect right after a drop.
```json
{"src": "broll/hands_or_gear.mp4", "beats": 8, "transition": {"type": "zoom", "dur": 0.25}, "camera": "pulse", "effects": ["beat-flash"],
 "layers": [
  {"text": "ON", "font": "Bungee", "size": 200, "x": 0.2, "y": 0.58, "glow": "#22e4ff", "start": "2b", "in": {"anim": "shake", "dur": 0.25}},
  {"text": "THE", "font": "Bungee", "size": 200, "x": 0.46, "y": 0.58, "glow": "#ff2bd6", "start": "3b", "in": {"anim": "shake", "dur": 0.25}},
  {"text": "BEAT.", "font": "Bungee", "size": 200, "x": 0.78, "y": 0.58, "color": "#ffe53b", "start": "4b", "in": {"anim": "shake", "dur": 0.25}, "beat_bounce": 0.05}]}
```

## 7. Split-screen b-roll
Three portrait clips side by side make one landscape beat; or two landscape clips stacked for 9:16.
```bash
python3 scripts/compose.py split --out assets/split.mp4 --size 1920x1080 --dur 3.6 broll/a.mp4@2 broll/b.mp4@2.6 broll/c.mp4@3
python3 scripts/compose.py split --out assets/split_v.mp4 --size 1080x1920 --stack --dur 3 broll/x.mp4@1 broll/y.mp4@1
```
```json
{"src": "assets/split.mp4", "beats": 8, "transition": {"type": "whip-left", "dur": 0.25},
 "layers": [{"text": "B-ROLL BY DEFAULT", "font": "Bungee", "size": 120, "y": 0.62, "panel": {"color": "#0d0221", "opacity": 0.78, "radius": 16, "pad": 26}, "start": "2b", "in": {"anim": "reveal", "dur": 0.35}}]}
```

## 8. Step label over footage
For how-to, features and processes: a numbered label top-left, footage carrying the action.
```json
{"type": "block", "block": "step", "x": 0.04, "y": 0.13, "anchor": "w", "w": 0.44,
 "props": {"number": 3, "label": "Hunts the b-roll", "accent": "#ff2bd6", "card": true}}
```

## 9. Graphics showcase over darkened footage
Footage graded `dark`, then a sticker slam, a counting number and a pulsing button on successive beats.
```json
{"src": "broll/screen_or_workspace.mp4", "beats": 8, "transition": {"type": "slide-up", "dur": 0.25}, "camera": "drift", "grade": "dark", "effects": ["vignette"],
 "layers": [
  {"type": "image", "src": "assets/pack.jpg", "cutout": "flat", "outline": [12, "#ffffff"], "drop_shadow": true, "h": 0.6, "x": 0.27, "y": 0.6, "rotate": -7, "start": "1b", "in": {"anim": "elastic", "dur": 0.45}, "float": 8},
  {"type": "block", "block": "counter", "x": 0.72, "y": 0.42, "w": 0.34, "start": "3b", "props": {"value": 16, "suffix": "M", "label": "colors", "color": "#22e4ff"}},
  {"type": "block", "block": "cta", "x": 0.72, "y": 0.75, "w": 0.32, "start": "5b", "in": "pop", "props": {"label": "Shop now", "accent": "#ffe53b"}}]}
```

## 10. Text behind the product
Product cut onto a flat colour field; a giant word sits behind it. Reads as print-ad craft.
```bash
python3 scripts/compose.py field assets/pack.jpg --color "#1a0b3d" --size 1920x1080 --h 0.6 --out assets/hero.png
```
```json
{"type": "image", "src": "assets/hero.png", "beats": 8, "transition": {"type": "diagonal", "dur": 0.3}, "camera": "push-in", "camera_amount": 0.07,
 "overlay": {"type": "sparkles", "amount": 0.8},
 "layers": [{"text": "GLOW", "font": "Bungee", "size": 480, "y": 0.3, "color": "#ffe53b", "behind_subject": true, "in": {"anim": "zoom-out", "dur": 0.4}}]}
```
Keep the word's lower half behind the product and its top half clear, so it still reads.

## 11. Proof checklist
Items tick in on the beat beside footage of the work being done.
```json
{"type": "block", "block": "checklist", "x": 0.7, "y": 0.56, "w": 0.4, "start": "1b",
 "props": {"title": "<what is checked>", "items": ["<real item>", "<real item>", "<real item>"], "every": 0.43, "theme": "dark", "accent": "#b6ff3b"}}
```

## 12. Phone reveal (the payoff)
The result plays inside a phone over blurred abstract footage; the words build on the left.
```bash
python3 scripts/compose.py phone --screen out/result.mp4@0 --bg broll/abstract.mp4 --size 1920x1080 --x 0.68 --dur 8.7 --out assets/phone.mp4
```
```json
{"src": "assets/phone.mp4", "beats": 20, "transition": {"type": "light-leak", "dur": 0.5}, "overlay": {"type": "light-sweep", "amount": 0.35},
 "layers": [
  {"text": "you typed", "font": "JetBrainsMono-800", "size": 50, "x": 0.31, "y": 0.27, "color": "#b6ff3b", "case": "upper", "in": "fade"},
  {"text": "B09V366BDY", "font": "Bungee", "size": 118, "x": 0.31, "y": 0.39, "glow": "#ff2bd6", "start": "1b", "in": {"anim": "typewriter"}},
  {"text": "it made this.", "font": "Bungee", "size": 104, "x": 0.31, "y": 0.6, "color": "#ffe53b", "start": "7b", "in": {"anim": "elastic", "dur": 0.45}}]}
```
Place it on the music's breakdown or its biggest hit.

## 13. Speed-ramp reveal / freeze label
```json
{"src": "broll/action.mp4", "in": 3, "speed": 2.5, "speed_to": 0.4, "beats": 4, "transition": {"type": "flash", "dur": 0.15},
 "freeze": {"at": "3b", "hold": "1b"},
 "layers": [{"type": "block", "block": "callout", "x": 0.62, "y": 0.4, "w": 0.34, "start": "3b", "props": {"text": "<what you see>", "pointer": "left"}}]}
```

## 14. Problem flash
Three 2-beat cuts of the frustration, desaturated, one word each, then a hard stop.
```json
{"src": "broll/problem1.mp4", "beats": 2, "grade": "mono", "effects": ["shake"],
 "layers": [{"text": "TANGLED.", "font": "Anton", "size": 220, "in": {"anim": "shake", "dur": 0.2}}]}
```
Repeat with two more clips and words, then cut to the product in full colour (`flash` transition).

## 15. Brand end card
Brand colours, the real logo file, one line, a real call to action, held 4+ seconds.
```json
{"type": "color", "color": "#111111", "beats": 12, "transition": {"type": "flash", "dur": 0.2},
 "overlay": [{"type": "sparkles", "amount": 0.7, "density": 0.8, "tint": "#FBB825"}, {"type": "light-sweep", "amount": 0.15}],
 "effects": ["vignette"],
 "layers": [
  {"type": "image", "src": "brand/logo.png", "h": 0.4, "y": 0.25, "glow": "#FBB825", "in": {"anim": "elastic", "dur": 0.5}},
  {"text": "<PRODUCT OR LINE>", "font": "Poppins-800", "size": 108, "y": 0.535, "tracking": 10, "start": "1b", "in": {"anim": "tracking", "dur": 0.5}},
  {"type": "shape", "shape": "rect", "y": 0.6, "w": 0.07, "h": 0.006, "radius": 3, "color": "#FBB825", "start": "2b", "in": {"anim": "draw", "dur": 0.4}},
  {"text": "<one-line promise>", "font": "Poppins-600", "size": 52, "y": 0.665, "color": "#FFFFFFCC", "start": "2b", "in": {"anim": "stagger"}},
  {"text": "<CTA>", "font": "Poppins-800", "size": 44, "y": 0.8, "panel": {"color": "#FF0000", "opacity": 1, "radius": 14, "pad": 28}, "start": "4b", "in": {"anim": "pop", "dur": 0.3}, "beat_bounce": 0.03}]}
```

## 16. Label close-up with a shimmer
A tight crop of the real pack, a slow camera move, and one highlight that travels across the
print only: the type and the logo catch the light, the pack itself stays still. Three of these
read the product's own label as the story; no words needed on top.
```json
{"type": "image", "src": "assets/pack.jpg", "crop": [0.28, 0.40, 0.70, 0.76], "beats": 3, "transition": {"type": "zoom", "dur": 0.25},
 "grade": "warm", "camera": "push-in", "camera_amount": 0.08,
 "overlay": {"type": "shimmer", "amount": 0.6, "start": 0.15, "span": 0.6},
 "effects": ["vignette", {"type": "grain", "amount": 0.4}]}
```
Use `"mask": "bright-cool"` for blue or silver print, `"threshold"` lower for dim type.

---

## Before / after: the same brief, plain vs produced

**Plain (what to avoid):** 5 product photos, each 3 s, centered caption fading in, one
dissolve between each, music bed under it. No footage, no beat grid, one entrance, nothing
surprising. Preflight score ~10.

**Produced:** hook slam on moving b-roll (1) -> the problem in three flashes (14) -> countdown
into the drop (4) -> product hero with proof (3) -> kinetic word stack over energetic b-roll
(5) -> split-screen of real-life use (7) -> text behind the product (10) -> phone or
end-result reveal on the breakdown (12) -> end card on the last hit (15). Same facts, same
product photos, plus 8-10 stock clips and a beat grid. Preflight score 85+.
