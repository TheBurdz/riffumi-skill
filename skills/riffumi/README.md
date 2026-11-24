# Riffumi skill - the local edition

Riffumi is a video director you talk to. Give it a brief, a product, photos, clips or an idea
and it plans a real concept, gathers material (yours, stock or generated), cuts on the beat,
adds motion graphics and sound, checks its own work and renders an MP4.

This folder is the **skill edition**: plain Markdown instructions (`SKILL.md` + `references/`)
and Python scripts that run wherever your AI agent has a shell, Python and ffmpeg. Nothing is
sent to Riffumi's servers; renders happen on your machine or in your agent's sandbox.

## Two ways to use Riffumi

| | Hosted connector (riffumi.com) | This skill |
|---|---|---|
| Where it renders | Riffumi's servers | your machine or your agent's sandbox |
| Setup | sign in once, nothing to install | copy the folder, install numpy + Pillow + ffmpeg |
| Works from | any AI app that takes MCP connectors, including the phone apps | agents that read skills or can run scripts (Claude Code, Codex, Cursor, Claude apps with code execution and others) |
| Library and share links | yes: uploads, projects and renders kept, every render gets a link that plays in the chat | no: files live where you render them |
| Stock b-roll, fonts, transcription | built in | Pexels through your agent's own web tools, no key; fonts fetched from Google Fonts; whisper optional |
| Cost | 3 free exports, then one plan | free (MIT), you pay nothing to Riffumi |
| Best for | phones, chat apps without code execution, teams, sharing | developers, agent builders, offline work, batch jobs, custom pipelines |

Both follow the same director's playbook: idea before look, footage carries the video, cut to
the music, only true words on screen, and a production bar the agent measures before it
delivers. Details and the hosted sign-up: https://riffumi.com/skill

## What's inside

```
riffumi/
  SKILL.md                      workflow the agent follows
  references/                   loaded on demand
    creative-system.md          concepts, 22 structures, 60+ devices, levels, scoring, anti-template rules
    scene-recipes.md            15 proven scene building blocks as copy-ready spec snippets
    motion-and-type.md          entrances, transitions, camera, colour, overlays, info blocks, layout
    formats-and-platforms.md    canvases, social specs + safe zones, marketplace and other formats
    sound-design.md             music sourcing, beat sync, voiceover, sound effects, loudness
    assets-and-licensing.md     user material, stock libraries, generated assets, fonts, manifest
    routing-and-generation.md   choosing a route, prompting image/video models, connected tools
    workflows.md                photos-only, talking head, screen recordings, loops, batches, stories
    review-checklist.md         what to check before delivering
    honesty-and-policy.md       claims, reviews, IP, AI disclosure, platform policies, privacy
    spec-format.md              the edit spec the renderer reads
  scripts/
    check_env.py                what this machine can do; saves .riffumi_env.json for preflight
    setup.py                    installs numpy + Pillow for this Python, prints the ffmpeg command
    render.py                   JSON edit spec -> MP4 (stills, contact sheets, full-size video)
    stock_search.py             b-roll from pexels.com with no key (search pages + public download); APIs when given a key
    compose.py                  split screens, phone reveals, product-on-colour fields
    preflight.py                checks a spec before rendering (offline-aware)
    inspect_media.py            contact sheets + inventory of your clips and photos
    beats.py                    tempo and beat grid of a music track
    matte.py                    cut a product/subject out of a still, sticker outline and shadow
    get_fonts.py                fetch open-licence fonts
    fetch_asset.py              download stock/music with a licence manifest
    transcribe.py               word timings for captions (optional whisper package)
    blocks.py, vdlib.py         modules used by render.py
  examples/
    smoke-test.json             renders with no assets - an install check
    reference-wild-16x9.json    a real spec that clears the production bar (study it, do not copy it)
```

## Requirements

- Python 3.8+ with `numpy` and `Pillow`: `python3 scripts/setup.py` installs them for the Python
  you run the scripts with (or `pip install -r requirements.txt`)
- `ffmpeg` and `ffprobe` on the PATH (`setup.py` prints the command for your platform)
- No API keys. Stock b-roll comes from pexels.com through the agent's own web tools and the
  public download link; a Pexels or Pixabay key can be passed on the command line if you have one
- Optional: `scipy` (faster cutouts), `rembg` (cutouts from busy photos),
  `faster-whisper` (transcripts for captions): `python3 scripts/setup.py --extras`

Check: `python3 scripts/check_env.py`, then
`python3 scripts/render.py examples/smoke-test.json`.

## Where it runs

| Host | Render | Fonts fetched | Stock b-roll | Transcripts | Status |
|---|---|---|---|---|---|
| Claude Code on a Mac or Linux box | yes | yes | yes, no key (verified 2026-11-14) | with faster-whisper | verified 2026-11-13 (macOS, ffmpeg 9, Python 3.9) |
| Any coding agent with a shell (Codex, Cursor and similar) | yes | yes | yes, no key | optional | expected: same requirements as above |
| Claude apps with code execution | yes when ffmpeg is in the sandbox | depends on sandbox network | depends on sandbox network | no | expected; run check_env.py first |
| ChatGPT with code execution | yes (ffmpeg, numpy and Pillow are preinstalled) | no: the sandbox has no network | no | no | expected; the skill runs offline-aware |
| Agents without code execution | no | no | no | no | the skill still produces the concept, beat sheet and spec; render later, or use the hosted connector |

"Expected" rows follow the vendors' published sandbox facts and have not been run end to end;
`check_env.py` tells you the truth for the host you are on. On an offline host the production
bar relaxes its font and footage rows to warnings and the agent says so.

## Installing in an agent

- **Agents with Agent Skills support** (Claude apps and Claude Code, and other agents that read
  `SKILL.md` folders): add the `riffumi` folder (or the zip) as a skill.
- **Coding agents** (any agent with a shell and file access): put the folder in your project and
  tell the agent "Follow riffumi/SKILL.md for video work", or reference it from your agent's
  instructions file.
- **Chat assistants with file upload and code execution**: upload the zip, ask the assistant to
  unzip it and follow `SKILL.md`.
- **Agents without code execution**: the skill still produces the concept, beat sheet, assets
  list and edit spec; render later on any machine with Python and ffmpeg, or use the hosted
  connector.

## Using it

Just ask, in your own words:

- "Make a 20-second vertical promo for this product: <link or photos>"
- "Turn these 30 photos from our trip into a 45-second film with music"
- "Cut this talking-head take into a 30 s ad with captions"
- "Three different 15 s hooks for this ad, same body"
- "Recut this 16:9 video for Reels and Shorts"

The agent will propose concepts (or just build when the request is thin), show you the video
(always full size, 1080p by default), and refine from your notes.

## Licence

MIT, The Burdz, LLC - see LICENSE. Stock media, music and fonts you download keep their own
licences; the skill records them in `assets/manifest.json`. Stock footage from
[Pexels](https://www.pexels.com). Riffumi is a trademark of
The Burdz, LLC; the hosted service at riffumi.com has its own terms.
