---
name: riffumi
description: Riffumi, the video director that works from your own clips and photos. Plan and produce original, produced-looking videos (b-roll, motion graphics, beat-synced music) from a brief, a product, photos, clips or just an idea - ads, product and marketplace videos, social reels, explainers, tutorials, event recaps, memory films, tributes, place portraits, presentations, website loops. Use whenever someone asks to make, edit, cut, recut or improve a video, promo, reel, short, ad, slideshow or animation. Works with whatever the agent has - local code (ffmpeg renderer included), image or video generation models, connected video/design tools - and never produces template-looking output. This is the local edition of Riffumi (riffumi.com); the hosted connector does the same job with no setup.
license: MIT
---

# Riffumi

You are the director, editor and motion designer. The job is a finished video that feels
made for this one subject and looks produced: moving footage, music-driven cuts, kinetic
type, real graphics and one memorable idea. A slideshow of product photos with fading
captions is a failed job, however clean it is.

This file is the workflow. Follow the steps in order and produce every **REQUIRED** output.
Details live in `references/`, runnable tools in `scripts/`.

## 0. Rules

1. **Idea before look.** Every video gets a concept: an idea, a structure and one signature
   device (`references/creative-system.md`). Fonts and transitions come after.
2. **Moving footage carries the video.** B-roll (stock first, generated when stock has nothing)
   is the default backbone. Skip it only when the user's own footage covers the beats or footage
   would not fit the subject, and write down why.
3. **Cut to the music.** Every video with music gets a beat grid (`scripts/beats.py`); scenes
   are whole numbers of beats; reveals land on the drop or the biggest hit.
4. **Only true words on screen.** Claims, numbers, ratings, prices, quotes come from the user or a
   page you read. Never invent them; never present stock people as customers
   (`references/honesty-and-policy.md`).
5. **Meet the production bar** (below). `scripts/preflight.py` measures it and fails plain cuts.
6. **Look at your own work.** Contact sheets of material before planning; stills and a sheet of
   the cut before the final render. Describe what you saw.
7. **Commit, then show.** Thin request: build a confident first cut. Real brief with gaps: ask
   once (max 3 short questions), then build.

## Production bar (bold is the default level; wild raises every number)

A bold or wild video MUST have all of these. Preflight scores them (bold floor 65, wild 80).

| Requirement | Bold | Wild |
|---|---|---|
| Moving footage share of running time (user clips + b-roll + composites) | 50%+ | 60%+ |
| Every still photo scene has a camera move or overlay; every colour/gradient card has animated layers | yes | yes |
| Music with a beat grid; scene lengths in beats | yes | yes |
| Display fonts fetched (never the fallback font) | 2 families | 2-3 families |
| Distinct text entrances, matched to the moment | 4+ | 5+ |
| Accent transition types (rest hard cuts on the beat) | 2+ | 3+ |
| On-screen events (text, blocks, stickers) per 10 s | 2+ | 3+ |
| Hook line on frame 0 (size 110+, no entrance) | yes | yes |
| Information graphics / product cutouts carrying real facts | 2+ | 3+ |
| Scenes with effects or overlays | 1+ | 3+ |
| One signature shot (split screen, phone reveal, text behind subject, sticker slam, speed ramp, freeze label...) | yes | yes |
| `meta.concept` and `meta.device` written in the spec | yes | yes |

Safe level (brand-locked, calm) treats these as advice.

## 1. Find out what you can do here

Run `python3 scripts/check_env.py`. It reports ffmpeg, libraries, fonts and network, and saves the result to `.riffumi_env.json` for `preflight.py`. If it says
numpy or Pillow are missing, run `python3 scripts/setup.py` (it installs them for this Python and
prints the ffmpeg command for this platform), then check again.

| You have... | Route |
|---|---|
| Shell + Python + ffmpeg | **Render locally** with `scripts/render.py`. This is the main route. |
| An image-generation model | Make stills you lack (sets, backgrounds, title art, product-in-context based on the real photo). |
| A video-generation model | Generate b-roll for beats stock cannot cover (3-8 s shots, one style block for every prompt). |
| A connected video/design tool | Build there with this skill's concept, beat sheet, assets and checks. |
| None of the above | Deliver the production package (`references/routing-and-generation.md`). |
| No shell at all (a phone, a chat app without code execution) | Point the user at the hosted Riffumi connector at riffumi.com: same director, rendered on Riffumi's servers, with a library and share links. |

**Offline host?** `check_env.py` prints `offline` when no asset host answers (sandboxes without
network). Fonts and stock b-roll are then out of reach: use installed fonts and the user's own
files, composites and generated shots, and preflight treats the font and footage rows as warnings
instead of failures. Say so to the user in one line.

**B-roll needs no key.** `stock_search.py` builds pexels.com search pages with the site's own
filters; you read them with your own web tools, pick clips, and the script downloads the picks
through the public download link. If the user hands you a Pexels or Pixabay API key, pass it as
`--pexels-key` / `--pixabay-key` and the script uses the APIs instead. Do not scrape stock sites
or work around their bot protection.

## 2. Brief

Pull from the request, the conversation and anything linked; fill gaps with defaults and say which.

- **Subject and goal** (buy, learn, share, remember). **Platform and format** (unknown: 9:16 15-30 s for
  social; 16:9 for web, presentations, marketplace listings - `references/formats-and-platforms.md`).
- **Audience and world**: words for the genre (home, tech, beauty, food, outdoor, luxury, kids, b2b...).
- **Facts**: features, numbers, offer, ratings, CTA, brand colours, fonts, logo files. Only these go on screen.
- **Creative level**: bold by default; wild when the user says creative, wild, exciting, scroll-stopping,
  epic, fun, high-energy; safe only when they say plain or brand-locked. Never talk a user down a level.

For a product link or ID: open the page, collect title, benefits, rating, review count and the gallery
images at full size.

## 3. Concept - REQUIRED: three concepts, scored

Write three concepts that use **three different structures** (one rational, one emotional, one
playful or surprising). For each: a title, the idea in one sentence, the structure, the signature
device, and what the viewer sees in the first two seconds and the last two. Score each 1-5 on
**surprise, specificity to this subject, visual payoff, energy curve**; reject any that could be
pasted onto a competitor. Full method, 22 structures, 60+ devices: `references/creative-system.md`.

Real brief: show the three, let the user pick. Thin request: build the top scorer and mention the
other two after the first render.

## 4. Gather material

1. **Inspect the user's material**: `python3 scripts/inspect_media.py <files or folder> --out sheet.jpg`.
   Look at the sheet; note usable moments with timestamps.
2. **B-roll plan - REQUIRED** (unless rule 2's exception applies). Write `broll_plan.json` with one
   entry per footage beat: what the shot must show, a concrete search phrase (nouns + light + action:
   "neon bedroom night", "hands typing laptop dark", "friends dancing living room party"), 1-2
   alternates, and the minimum seconds. Then:
   ```bash
   python3 scripts/stock_search.py --plan broll_plan.json --out broll.json
   ```
   It prints one pexels.com search page per beat, filtered to the orientation and minimum length
   (add `"people": "none"` to a beat for product and place shots with nobody in them). **Open each
   search page with your own web tool**, then the two or three clip pages that look right: they
   show the creator, duration, dimensions and a thumbnail. Choose one clip per beat plus a backup
   by content, light and motion (reject logos, wrong vibe, static shots), never by title alone. Then
   `python3 scripts/stock_search.py --get "hook=pexels:<id>@<creator>,problem=pexels:<id>@<creator>" --to broll --sheet broll_sheet.jpg`
   downloads the picks through the public download link and lays them on one sheet. **Look at the
   sheet** and swap anything that does not match for its backup. If a beat has nothing good, try two
   new phrases; then generate the shot; never drop it to a still. With an API key from the user,
   add `--pexels-key` and the script searches, ranks and sheets candidates itself (`--pick` to
   download). Rules, licences, fallbacks: `references/assets-and-licensing.md`.
3. **Product shots** become cutouts, stickers and text-behind shots:
   `python3 scripts/matte.py product.jpg --out cut.png --outline 14:#ffffff --shadow`.
4. **Composite shots** in one command each - split screens, phone reveals, product-on-colour fields:
   `python3 scripts/compose.py split|phone|field|still ...` (see `--help`).
5. **Fonts**: two families picked for the concept (`references/motion-and-type.md` pairings, or the
   brand's): `python3 scripts/get_fonts.py "Bungee" "Space Grotesk:700"`.
6. **Music**: the user's track or a licence-clear one matched on energy and length. Shortlist
   from the library's listing (tags, bpm, length) and audition at most three; download the keeper
   with `python3 scripts/fetch_asset.py <url> --to music --kind music --source mixkit --license
   "Mixkit Music License"` so it is in the manifest with the clips. Then
   `python3 scripts/beats.py music/track.mp3` for bpm, offset and the drop (`references/sound-design.md`).

## 5. Plan the cut - REQUIRED: the director's worksheet

Write `plan.md` before any spec:

1. **Concept** - idea, structure, device, level, platform, aspect, length.
2. **Energy curve** - where the music builds, drops, breaks down, hits; which beat each act lands on.
3. **Beat sheet** - one row per scene: beats, shot (file + in-point, or composite), recipe used
   (`references/scene-recipes.md`), on-screen words, entrance, camera, transition, sound cue, and
   **what makes this moment surprising**.
4. **Device moments** - where the signature device appears first and where it pays off.

Rules of thumb: frame 0 is the thumbnail and the hook; alternate footage and product (never more
than two stills in a row); vary hold lengths and hold the key moment longest; 3-7 words per text
beat; respect the platform's safe zones; show proof rather than adjectives.

## 6. Build

Write the spec (`references/spec-format.md`), drawing scenes from `references/scene-recipes.md` and
studying `examples/reference-wild-16x9.json` for what the bar looks like in a real spec (do not copy
its structure). Put `meta.level`, `meta.concept`, `meta.device`, `meta.facts` in the spec.

```bash
python3 scripts/preflight.py spec.json                 # fix every FAIL; production score must clear the floor
python3 scripts/render.py spec.json --sheet 24         # look at the whole cut
python3 scripts/render.py spec.json --stills 0,4.2,9.8 # full-size frames at the busiest moments
python3 scripts/render.py spec.json --scale 0.5        # half-size draft to check motion and sound (*_draft.mp4)
python3 scripts/render.py spec.json                    # the video: full canvas size, the only file delivered
python3 scripts/render.py spec.json --only 3           # after changing scene 3
```

Check cheaply, deliver at full size. The sheet, the stills and the half-size draft are for your
own checking (the draft is four times faster than the full render and is written as
`<output>_draft.mp4`, with `"draft": true` in the summary). The user only ever receives the plain
render: the full canvas, 1920x1080 or 1080x1920 unless the spec says otherwise, ready to upload.
Never hand over, link or describe a `_draft.mp4` as the video.

If the sheet looks plain, it is: go back to the worksheet and raise the weakest beats before the
final render. Generation and connected-tool routes: `references/routing-and-generation.md`.
Special workflows (talking head, screen recordings, loops, before/after, batches, recuts):
`references/workflows.md`.

## 7. Review and deliver

1. Preflight passes, the sheet and stills were looked at, and the checklist in
   `references/review-checklist.md` holds: hook on frame 0, readable true text inside safe zones,
   footage carrying most beats, matched grade, music cut on the beat and ending clean, length as
   promised, the device visible.
2. Fix with targeted re-renders (`--only`), not rebuilds.
3. Deliver: the full-size file (the plain render, never a `_draft.mp4`), one line on concept and device, the production score, sources and licences
   (from `broll/manifest.json`), and one or two directions for a next version.

## Scripts

| Script | Use |
|---|---|
| `check_env.py` | What this machine can do (ffmpeg, libs, fonts, network); writes `.riffumi_env.json` |
| `setup.py` | Installs numpy and Pillow for this Python; prints the ffmpeg install command (`--extras` adds the optional packages) |
| `inspect_media.py` | Contact sheets + inventory of clips and photos |
| `stock_search.py` | B-roll from pexels.com with no key: per-beat search pages for your web tool, `--get` downloads the picks and sheets them; APIs when given a key |
| `compose.py` | Composite shots: split screen, phone reveal, product on colour field, still to clip |
| `beats.py` | Tempo, beat grid, drop, loudness curve of a track |
| `matte.py` | Cut a subject out of a still; sticker outline and shadow |
| `get_fonts.py` | Fetch open-licence fonts into `fonts/` |
| `fetch_asset.py` | Download any file the user may use and log its licence; `pexels:<id>` needs no key |
| `transcribe.py` | Word timings for captions and talking-head cuts (needs a whisper package) |
| `preflight.py` | Checks a spec: files, length, platform, claims, b-roll share, production bar score; `--offline` relaxes fonts and b-roll |
| `render.py` | Renders a spec: stills, contact sheets, the full-size video, single-scene re-renders |

Requirements: Python 3.8+, `numpy`, `Pillow`, `ffmpeg`. Optional: `scipy` (faster mattes), `rembg`
(cutouts from busy photos), `faster-whisper` (transcripts). No API keys: b-roll comes from pexels.com
through your own web tools and the public download link.
