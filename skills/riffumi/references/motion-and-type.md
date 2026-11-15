# Motion, type, colour and information graphics

What each tool is for. The spec names in `code` are what `render.py` understands.

## Text entrances - match the mood

| Entrance | Feel | Use for |
|---|---|---|
| `none` | instant | frame-0 hook (the thumbnail must be fully composed) |
| `fade`, `blur` | calm, premium | editorial, memory, luxury |
| `pop`, `elastic`, `rubber`, `bounce` | playful, energetic | social, kids, food, deals |
| `drop`, `shake` | impact | numbers, prices, "SALE", beat drops |
| `slide-*`, `reveal`, `unfold` | orderly, informative | features, steps, B2B |
| `letters`, `typewriter`, `tracking` | crafted titles | names, places, taglines, tech |
| `stagger` | spoken rhythm | sentences, quotes, captions |
| `flicker` | neon, night, retro | signage looks, nightlife, gaming |
| `spin`, `flip`, `swing`, `wiggle` | quirky | stickers, one-word jokes - sparingly |

Vary entrances across the piece; repeat one only when it is the signature.

## Typography

- 2 families maximum: a **headline** with character and a **support** face that disappears.
- Size on a 1080 px wide vertical canvas: hook 120-220, benefit 80-130, small print 40-56.
  On 1920x1080 landscape: hook 110-180, benefit 64-100.
- Contrast: thick stroke (6-12) or a soft shadow on busy footage; a panel when the footage is
  very busy; never thin light type on bright video.
- Upper case for short punches; sentence case for anything over ~5 words.
- Keep lines short (`max_width` 0.8-0.88), break on meaning, not width.
- Pairings that work (all open-licence): Anton + Inter, Bebas Neue + DM Sans, Playfair Display +
  Inter, Fraunces + Space Grotesk, Archivo Black + IBM Plex Mono, Caveat + Poppins,
  Cormorant Garamond + Montserrat, Bungee + Nunito Sans, Abril Fatface + Work Sans,
  League Gothic + Sora, Righteous + Outfit, Cinzel + Lato.
- Style ideas: neon (glow in the accent colour), comic (yellow fill, thick ink stroke, hard red
  shadow), sticker (bright fill, white stroke 10+, drop shadow), editorial (cream serif, warm hard
  shadow), highlighter (dark text on a lime panel), terminal (green mono on black panel),
  sale tag (white slab on red panel), quiet lowercase (light sans, wide tracking, soft shadow),
  gradient (two-stop vertical gradient fill).

## Camera moves

| Move | Use |
|---|---|
| `push-in` | attention, intimacy, the default for stills |
| `pull-out` | reveal context, endings |
| `pan-*` | scanning a scene, landscape photos on vertical canvases |
| `punch-in` | beat hits, surprises |
| `pulse` | breathing on the beat for music pieces |
| `drift` | dreamy, editorial |
| `handheld` | POV, UGC realism |
| `rotate-*`, `tilt` | energy on stills, products on a turntable feel |
| keyframed path | precise moves: detail -> whole, follow a line, two-point pan |

Neighbouring scenes should not share a move. Clips that already move rarely need one.

## Transitions

Mostly **hard cuts** (on the beat when there is music). Accent transitions mark structure:

- `flash`, `zoom`, `glitch`, `whip-*` - energy, drops, social (not on premium/memory pieces).
- `dissolve`, `fade-black`, `grays`, `blur` - time passing, calm, premium, memory.
- `wipe-*`, `slide-*`, `diagonal`, `slice`, `bars-open` - lists, before/after, organised info.
- `circle-open`, `iris-close`, `radial` - playful, retro, object portals.
- `light-leak` - warm, nostalgic, story endings.
- `pixelize`, `squeeze` - retro/gaming accents only.

Typical lengths: 0.15-0.25 s energetic, 0.35-0.6 s calm.

## Colour

- Grades: `vivid` (products, food, social), `warm` (home, people, food), `cool` (tech, clean,
  "before"), `muted` (editorial, documentary), `mono`/`noir` (drama, "before", archive),
  `teal-orange` (cinematic, outdoor), `retro` (nostalgia), `candy` (playful, beauty),
  `sunset` (travel, golden hour).
- Pull the accent from the product or the footage; check text contrast on the busiest frame.
- Keep one grade per piece unless the grade change is the device.

## Effects and overlays

- `vignette` focuses; `grain` adds film warmth and hides compression; `chromatic` and `glitch-in`
  are energy accents; `scanlines`/`pixelate`/`posterize` are retro/gaming looks; `soft-focus`
  is dreamy; `glow` blooms highlights; `letterbox` reads cinematic.
- `beat-flash` makes footage pulse on every beat - great on music-sync stretches, tiring beyond ~6 s.
- Overlays: `light-leak` (warm, nostalgic), `light-sweep` (one shiny pass on a hero frame),
  `shimmer` (the sheen stays on the artwork: label type, logo, title card; the background keeps still),
  `bokeh` (dreamy, festive), `confetti` (celebration, launches, sales), `dust`/`embers`/`sparkles`
  (atmosphere), `snow`/`rain` (season, mood), `speed-lines` (comic impact, energy).
  One overlay family per piece unless it is the device.

## Information blocks

Use when they carry a real fact better than words: rating (`stars`), price (`price`),
key number (`counter`), progress or share (`progress`), what is included (`checklist`),
who is speaking (`lower-third`), steps (`step`), naming a part (`callout`), a real review
(`review`), a real quote (`quote`), a real deadline (`countdown`), a conversation (`messages`),
an event (`notification`), social proof from a real comment (`comment`), and the ask (`cta`).

One block on screen at a time, on the empty side of the frame, never over a face or the product.
Size them generously on phones (width 0.6-0.9 of a vertical canvas).

## Layout on vertical canvases

- Hook and headline in the upper third (y 0.12-0.35 on TikTok/Reels), benefits mid-frame,
  CTA around y 0.75-0.8 (above the caption area). Nothing important in the bottom 20-35%
  or the right 13% on TikTok.
- On product cards leave 120+ px between headline and card.
- On landscape (16:9) keep text within 5% margins; lower thirds at y 0.78-0.85.
