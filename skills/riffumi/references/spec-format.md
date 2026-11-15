# Edit spec format (scripts/render.py)

A spec is one JSON file. Paths are relative to the spec file. Sizes are in **design pixels**
of the canvas (they scale for previews). Positions are **fractions** of the canvas (0-1).

## Time values

Anywhere a time is asked for you can write:

| Form | Meaning |
|---|---|
| `1.5` or `"1.5s"` | seconds |
| `"12f"` | frames |
| `"4b"` | beats (needs `beat.bpm`) |
| `"50%"` | share of the scene (layer start/end/dur only) |

## Top level

```json
{
  "canvas": {"width": 1080, "height": 1920, "fps": 30, "background": "#000000"},
  "output": "out/final.mp4",
  "seed": 7,
  "beat": {"bpm": 128, "offset": 0},
  "music": {"src": "audio/track.mp3", "start": 0.42, "gain_db": 0, "fade_in": 0.05, "fade_out": 1.5, "duck": true},
  "voiceover": [{"src": "audio/vo.wav", "at": 0.3, "gain_db": 0}],
  "sfx": [{"src": "audio/whoosh.wav", "at": "8b", "gain_db": -6}],
  "loudness": -14,
  "fade": {"in": 0, "out": 0.4},
  "meta": {"platform": "tiktok", "target_seconds": 20, "goal": "sell", "level": "bold",
           "concept": "Your room called.", "device": "the room changes colour on every beat",
           "facts": ["100 ft", "4.4 stars from 42,000+ ratings"], "music": true},
  "scenes": [ ... ]
}
```

- `beat.offset` stays 0 when you trim the track with `music.start` = the offset `beats.py` reports;
  then beat 0 is frame 0 and `"beats": N` scenes cut on the grid.
- `music.duck` lowers music under voiceover (sidechain). `loudness` null skips levelling.
- `meta` is read by `preflight.py` only (platform checks, length promise, claim check, CTA check,
  b-roll share, and the production bar for `level` bold/wild, which also wants `concept` and `device`).

## Scene

```json
{"type": "clip", "src": "broll/city.mp4", "in": 3.2, "dur": 1.8,
 "beats": 4, "speed": 1.0, "speed_to": 0.4, "reverse": false, "freeze": {"at": "2b", "hold": "1b"},
 "fit": "cover", "focus": [0.5, 0.4], "audio": {"gain_db": -4},
 "camera": "push-in", "camera_amount": 0.08,
 "grade": "vivid", "grade_to": "warm", "grade_amount": 1,
 "effects": ["vignette", {"type": "chromatic", "amount": 0.5}, "beat-flash"],
 "overlay": {"type": "confetti", "amount": 0.8, "density": 1, "speed": 1, "tint": "#ffd166"},
 "transition": {"type": "whip-left", "dur": 0.25},
 "layers": [ ... ]}
```

Length: `dur` (time value) or `beats` (count). Scene starts are cumulative; a transition
plays at the **start** of the incoming scene (the outgoing scene runs on underneath), so
cuts stay on the beat and the total length is the sum of scene lengths.

### Scene types

| type | Fields |
|---|---|
| `clip` | `src` video, `in`, `speed`, `speed_to` (eased ramp across the scene), `reverse`, `freeze {at, hold}`, `fit` cover/contain/blur, `focus [x,y]`, `audio` true or `{gain_db}` (natural sound; skipped on reverse/freeze/ramps and speeds outside 0.5-2), or `{src, in, gain_db}` to play sound from another file under this scene (any scene type - b-roll cutaways while a speaker keeps talking) |
| `image` | `src` still, `crop [x0,y0,x1,y1]` (fractions or pixels), `fit` cover/contain/blur, `focus`, `bg` (contain colour). Text layers with `behind_subject` go behind the photo's subject (auto matte) |
| `card` | `src` still shown as a card: `card {w, h, x, y, radius, glow ("cycle"/colour/null), bg ("blur"/colour/[gradient colours]), bg_dim, enter (pop/slide-up/drop/fade/none), grow, float, rotate, cutout (true = product cut from its background), outline [px, colour], drop_shadow}` |
| `gradient` | `colors` [2+], `angle` deg, `spin` deg/s, `hue_shift` |
| `color` | `color` |

Type is inferred when omitted: video `src` -> clip, image `src` -> image, no src -> color.

### Camera

`none, push-in, pull-out, pan-left, pan-right, pan-up, pan-down, punch-in, pulse` (breathes on the beat),
`drift, handheld, rotate-cw, rotate-ccw, tilt`; `camera_amount` ~0.04 subtle to 0.15 strong.
Or a keyframed path: `"camera": [{"t": 0, "zoom": 1.0, "x": 0.5, "y": 0.5}, {"t": "100%"... }]`
uses `t` time values, `zoom`, `x`/`y` (0-1 where the crop window sits), `rot`, `ease`.

### Grades

`warm, cool, vivid, muted, mono, noir, teal-orange, retro, candy, sunset, bright, dark`.
`grade_to` makes a colour journey across the hold (cool to warm for memories, mono to colour
for before/after).

### Effects

Picture effects (under the text): `vignette, grain, chromatic, scanlines, pixelate, posterize,
soft-focus, glow, letterbox`.
Frame effects (over everything): `beat-flash` (pulse on every beat), `flash-in` (white hit on the
cut), `glitch-in` (RGB split on the cut), `shake` (impact shudder at scene start).
Each takes `amount` and can be forced with `"on": "picture" | "frame"`.

### Overlays

`light-leak, light-sweep, bokeh, confetti, dust, sparkles, embers, snow, rain, speed-lines, shimmer`
with `amount` (opacity), `density`, `speed`, `tint`, `colors` (confetti/bokeh palette).
`shimmer` is different: it brightens only the artwork already in the picture (light type, warm or cool
print) with one travelling highlight and leaves the background alone, so a label, a logo or a title
card catches the light: `{"type": "shimmer", "amount": 0.6, "start": 0.15, "span": 0.6, "mask":
"bright-warm", "threshold": 0.42, "width": 0.07, "tint": "#fff7e6"}` (`start` and `span` are shares of
the scene; `mask` is any mix of `bright`, `warm`, `cool`). It runs on the picture, under text layers.
Several at once: `"overlay": [{...}, {...}]`.

### Transitions (incoming)

`cut, dissolve, fade-black, flash, grays, wipe-left|right|up|down, slide-left|right|up|down,
whip-left|right|up|down, zoom, glitch, circle-open, iris-close, radial, diagonal, slice,
bars-open, blur, pixelize, squeeze, light-leak`. `dur` 0.15-0.5 s typical.

## Layers

Drawn in list order (first = back). Common fields: `start`, `end` or `dur` (time values,
relative to the scene), `in` (entrance), `out` (exit), `x`, `y`, `anchor`
(`c, n, s, w, e, nw, ne, sw, se`), `opacity`, `rotate`, `keyframes`, `beat_bounce`.

`in` / `out`: a name or `{"anim": name, "dur": 0.3, "stagger": 0.05}`.

Entrances: `none, fade, pop, zoom-out, elastic, bounce, drop, slide-up|down|left|right, shake,
wiggle, swing, spin, flip, unfold, reveal, blur, rubber, flicker` (whole layer) and
`typewriter, letters, tracking` (per character), `stagger` (per word).
Exits: `none, fade, pop, blur, slide-up|down|left|right`.

`keyframes`: `[{"t": 0, "x": 0.5, "y": 1.2, "scale": 1, "rot": 0, "opacity": 1, "ease": "out"}, ...]`
(`t` in seconds, frames or beats from the layer start - not percentages; eases `linear, in, out, inout,
back, elastic, bounce, hold`). `x`/`y` may leave the canvas, so things can fly in from off screen.

### text

```json
{"type": "text", "text": "Built to last", "font": "Anton", "size": 160, "color": "#ffffff",
 "gradient": ["#ffd166", "#ef476f"], "stroke": 8, "stroke_color": "#000000",
 "glow": "#ff2bd6", "glow_radius": 18, "shadow": [0, 8, 0, "#000000cc"],
 "panel": {"color": "#000000", "opacity": 0.55, "radius": 20, "pad": 26},
 "case": "upper", "tracking": 2, "line_height": 1.05, "align": "center", "max_width": 0.86,
 "x": 0.5, "y": 0.3, "in": {"anim": "letters", "dur": 0.35}, "beat_bounce": 0.04,
 "behind_subject": false}
```

- `font`: a file path, a file in the skill's `fonts/` (`"Inter-900"`), or an installed family
  (`"DejaVu Sans:Bold"`). Fetch fonts with `get_fonts.py`.
- Lines wrap at `max_width` (fraction of canvas width); a word that cannot fit shrinks the size.
- `shadow`: `[x, y, blur, colour]` or `true`. `panel` puts a rounded plate behind the text.
- `behind_subject` (image scenes only): the words sit between the photo's subject and its background.

### image

```json
{"type": "image", "src": "pack.jpg", "cutout": "auto", "outline": [14, "#ffffff"], "drop_shadow": true,
 "w": 0.7, "h": 0.5, "x": 0.5, "y": 0.55, "radius": 30, "glow": "cycle", "float": 14, "grow": 0.04,
 "in": {"anim": "elastic", "dur": 0.5}}
```

`cutout` (`auto`, `flat`, `rembg`) removes the background (product on white works offline),
`outline` + `drop_shadow` make a sticker, `float` bobs it (px or `{amp, period}`), `glow` adds a
coloured halo (`"cycle"` walks the hue), `grow` is a slow scale over the scene.
Also takes a logo, a screenshot, a generated still, a transparent PNG.

### block

```json
{"type": "block", "block": "stars", "w": 0.8, "x": 0.5, "y": 0.82, "start": "2b",
 "props": {"value": 4.4, "count": "42,000+", "label": "ratings", "accent": "#ffb400", "theme": "light"}}
```

| block | props |
|---|---|
| `cta` | label, arrow, accent, label_color, pulse_period |
| `stars` | value, count, label, accent, card, fill_time |
| `price` | price, was, label, accent |
| `counter` | value, prefix, suffix, decimals, label, color, card, count_time |
| `progress` | label, value (0-100), suffix, accent, card |
| `checklist` | title, items[], every (s between ticks), accent, theme |
| `lower-third` | name, title, accent, theme |
| `step` | number, label, accent, card |
| `callout` | text, pointer (left/right/up/down), accent |
| `review` | stars, title, text, name, verified, theme |
| `quote` | quote, name, role, accent |
| `countdown` | seconds, label, accent |
| `messages` | messages [{from: me/them, text}], gap, accent |
| `notification` | app, title, text, time, icon, accent |
| `comment` | name, text, likes, initial, accent |

All take `theme` (`light`/`dark`), `font`, `accent`. Blocks show only real data: a rating, review,
price or quote the user gave or that you read on their page.

### shape

`{"type": "shape", "shape": "rect|circle|ring|line", "x", "y", "w", "h", "color", "opacity",
"radius", "thickness", "in": {"anim": "draw"}}` - `draw` grows a line or bar from the centre.

### captions

```json
{"type": "captions", "words": "take_words.json", "chunk": 3, "font": "Inter-900", "size": 92,
 "y": 0.68, "stroke": 8, "highlight": "#ffe53b", "case": "upper", "offset": 0}
```

`words` is a list of `{w, s, e}` (global seconds) or a path to `transcribe.py` output.
Shows a few words at a time and recolours the spoken one. `offset` shifts all timings.

## Command line

```
render.py spec.json [--preview] [--scale 0.5] [--stills 0,3.2] [--sheet 12]
                    [--only 2,5] [--audio-only] [--out file.mp4] [--workdir dir]
```

Scene files go in `<output>_parts/` (prefix `p` for previews, `f` for finals), so `--only`
re-renders just what changed (and the scene after it when a transition depends on it).
