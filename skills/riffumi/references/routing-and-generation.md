# Routing: code, generation models, connected tools - or a production package

This skill runs in any agent. Capabilities differ, so decide the route from what is actually
available, tell the user in one line, and keep the same creative standard on every route.

## 1. Detect

- **Can you run shell commands?** Run `python3 scripts/check_env.py`. `can_render: true` means the
  local renderer works (ffmpeg + numpy + Pillow). If ffmpeg is missing and you may install
  software, install it (`apt-get install ffmpeg`, `brew install ffmpeg`, `pip install numpy pillow`).
- **Image generation?** (a built-in image tool, an image MCP, an API the user connected)
- **Video generation?** (text/image-to-video models, avatar or lip-sync tools)
- **Voice?** (text-to-speech, a voice the user owns)
- **Connected editing/design tools?** (a video editor with an API or MCP, a design tool with
  video export, the user's own cloud renderer)
- **Browser or fetch tools?** for product pages and stock libraries.
- **What the user said**: a tool they want used or avoided is a hard instruction.

## 2. Choose

| Situation | Route |
|---|---|
| Code available | Plan here, render with `render.py`. B-roll from `stock_search.py` (pexels.com, no key) first, generation for beats stock cannot cover, composites with `compose.py`. |
| No code, video generation available | Generate shots per beat, then assemble in the generator's editor or a connected tool; if neither can cut, deliver the shots plus an edit list. |
| No code, a connected editor available | Build in that tool following its own guide; carry over concept, beat sheet, text, music and checks. |
| Image generation only | Generate stills per beat and deliver them with the edit spec (or a slideshow the tool can export). |
| Nothing | Deliver the production package (below). |

Never claim a capability you have not verified, never invent a tool's options - read its own
documentation or schema first.

## 3. Prompting generation models

Per shot, one prompt with: **subject** (exact, from the real product photo when relevant),
**action**, **setting**, **camera** (shot size, angle, move: "slow push-in", "handheld",
"top-down"), **lens/look** ("35 mm, shallow depth of field"), **light** ("warm practical lamps,
dusk"), **mood**, **style** (photoreal, film stock, 3D, illustration), **duration** (3-8 s works
best for most video models), **aspect** (match the canvas).

Consistency across shots: repeat a fixed style block in every prompt; use the same reference
image or seed when supported; generate the hero frame first, then image-to-video from it.

Product fidelity: use the real product photo as the reference (image-to-image or
image-to-video); ask for the product to stay unchanged; reject outputs that alter its shape,
colour, branding, size or contents. Text inside generated images is unreliable - add text in
the edit instead.

B-roll is the main job for a video model in this skill: when stock has no clip for a beat, generate
it rather than falling back to a still. Typical generated beats: an establishing scene, a lifestyle moment, a problem scene, an abstract
background for type, a transition shot. Typical non-generated beats: the product doing its job,
real results, real people speaking.

Costs: generation often spends the user's credits. Say roughly how many generations you plan,
start with the hero shot, and do not retry blindly.

## 4. Connected tools

- Read the tool's guide/schema; map this skill's beat sheet onto its project model
  (scenes/clips, layers/titles, transitions, audio tracks).
- Keep: the concept, the device, true facts, music licence rules, safe zones, preflight checks.
- If the tool's catalogue lacks something (an effect, a block), approximate with what it has,
  or render that one element locally (e.g. a transparent PNG or a short clip) and import it.

## 5. The production package (no rendering available)

Deliver, in one document:
1. Concept: idea, structure, device, level, platform, aspect, length.
2. Beat sheet table: time in/out, shot (file + timestamp or stock link or generation prompt),
   on-screen text, motion, transition, sound cue.
3. Text sheet: every on-screen line with its source fact.
4. Kit: fonts (with download links), colours (hex), grade, overlays.
5. Music: track, link, licence, BPM, where cuts land.
6. An edit spec JSON for `render.py`, so anyone with Python can render it.
7. Asset list with links and licences.
