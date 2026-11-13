# Special workflows

## Photos only (no clips from the user)

B-roll is the first answer: product photos alone make a slideshow, so the photos carry the
product beats and stock or generated b-roll carries the world, the problem and the payoff (see
SKILL.md step 4). For the product beats, a still becomes motion through camera moves (push, pull, pan,
keyframed paths), crops into details (detail trio), cutouts that move (sticker slam, floating
product), text behind the subject, grade journeys, overlays (light leak, dust, bokeh), cards on
moving gradients and info blocks. Say plainly what stills can do (camera, light, depth, type)
and what they cannot (show the product working). For proof beats with no footage, use a
demonstration the user can film on a phone, a generated clip clearly based on the real product,
or a different structure (three reasons, manifesto, tease and reveal).

Landscape photos on a vertical canvas: `fit: "blur"` (sharp photo over a blurred copy) or a
`pan-left/right` across a cover crop; never a blind centre crop that cuts the subject.

## Talking head / founder / testimonial

1. Transcribe: `transcribe.py take.mp4 --out words.json --srt take.srt`.
2. Build a cut list from `segments`: keep the strongest lines, drop false starts, repeats, long
   pauses and filler; show the list as a table (kept/dropped with reasons) and take edits in words.
3. Strongest line first (the hook), then context, value, proof, CTA.
4. One clip scene per kept line (`in`, `dur` from the segment times), hard cuts, a punch-in on
   every second cut to hide jumps (`camera: punch-in` with a small amount).
5. B-roll cutaways (stock, generated or the user's) over every 2nd-3rd line, keyed to what is
   being said, while the voice continues: the cutaway scene shows the b-roll clip and takes its
   sound from the take with `"audio": {"src": "take.mp4", "in": <line start>}`. Return to the
   speaker for emphasis.
6. Captions over everything (`captions` layer with the words, offset to the new timeline -
   re-time words to the cut, or transcribe the rendered cut again).
7. Product image on the empty side of the frame when the product is named; lower third
   with name and role (only what the user gives).

## Screen recordings, app and SaaS demos, process videos

- Find the moments where something changes (look at a contact sheet with `--per-clip 12`).
- Each moment at 1-2x; each wait as one fast scene (`speed` 4-20) or a ramp into the next moment.
- Use camera keyframes to zoom into the part of the screen that matters; a 16:9 recording on a
  9:16 canvas can sit at `fit: contain` with a zoomed path.
- Callout blocks name UI elements; step numbers carry the sequence; the result is shown first.
- Natural sound mutes on fast or ramped scenes - put music under them.

## Speed, freeze, rewind, reverse

- `speed` 2-20 for time-lapse feel; `speed_to` for an eased ramp (fast into the moment, slow
  through it).
- `freeze {at, hold}` holds a frame (camera moves keep running) - pair with a label.
- `reverse: true` plays the scene backwards (rewind gags, "undo the mess").
- Kickflip-style hero: speed 1 -> 0.5 into the peak, freeze at the peak 0.5 s, then a reverse
  scene of the last 0.4 s, then play on.

## Before and after

Match framing exactly (same crop, same camera move). Before: `mono`/`muted`/`cool`, slower,
quieter. After: full colour, energy, music lift. Swipe or wipe between them on a beat. Only real
before/after material, never simulated results.

## Loops (website heroes, bumpers, store backgrounds)

Start and end on the same frame and motion: either a clip section that loops naturally, a
camera move that returns to its start (keyframed path), or a crossfade from the end back into
the start (render the last scene with `transition: dissolve` from a copy of the first). No text
for website backgrounds; muted; 6-20 s; small files (encode the final with a higher CRF if needed).

## Batches and variations

- A/B hooks: same body, 3 different first 2 seconds (question open, number counter, problem flash).
- Platform set: one master cut, then recuts per aspect - re-frame each scene (`focus`, crops,
  text positions for the new safe zone), never just letterbox. Change lengths per platform
  (6 s bumper, 15 s ad, 30 s organic).
- Several products: give each video its own structure, device and kit; keep a list of what was
  used and exclude it on the next one.
- Name files clearly: `<subject>_<platform>_<aspect>_<length>s_<version>.mp4`.

## Story pieces (memories, trips, events, pets, tributes, places)

These are the main exception to b-roll by default: build them from the user's own photos and clips.
Stock would put strangers into someone's memories. Generic atmosphere (sky, sea, city lights) is fine
only for transitions or title cards, and only if the user agrees.

- Titles serve the moment: a name, a place, a date, a feeling - not marketing.
- Music first; varied holds with the climax held longest; camera moves never repeat on
  neighbours; a grade that travels; sound palette cinematic or none; no UI pops or sales blocks.
- Chapters for long spans of time; a dedication line at the end when it fits.
- People's photos: keep faces out of the crop edges and out from under text; ask before
  publishing anything with other people in it.

## Recutting an existing video

Inspect it (`inspect_media.py --per-clip 12`), transcribe if it has speech, list its beats and
what works, then rebuild it as a spec with the user's video as the clip source: new hook,
tighter holds, captions, new aspect, music re-levelled.
