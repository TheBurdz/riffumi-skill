# Riffumi skill

The local edition of [Riffumi](https://riffumi.com): a video director your AI agent follows,
with a working ffmpeg renderer, keyless stock b-roll, beat sync, cutouts, composites and a
production bar it measures before delivering. The agent turns the user's own clips and photos
into finished videos: product showcases, social posts, stories, ads, how-tos, highlight reels.
MIT licensed. Nothing is sent to Riffumi.

This repository is a plugin with one skill. The skill lives in
[`skills/riffumi/`](skills/riffumi/): start with its [README](skills/riffumi/README.md) and
[SKILL.md](skills/riffumi/SKILL.md). The same folder is what the zip on
[riffumi.com/skill](https://riffumi.com/skill) contains.

Prefer nothing to install? The hosted connector at [riffumi.com](https://riffumi.com) renders on
Riffumi's servers and works from any AI app that takes MCP connectors, phones included.
[Which one is for you](https://riffumi.com/skill).

## Install

- **As a plugin**, from the Claude or ChatGPT plugin directory once listed, or straight from this
  repository. In Claude Code:

  ```
  /plugin marketplace add TheBurdz/riffumi-skill
  /plugin install riffumi-skill@riffumi
  ```

  In Codex (and the ChatGPT desktop app, where the marketplace then shows as a source in the
  Plugins Directory):

  ```
  codex plugin marketplace add TheBurdz/riffumi-skill
  ```
- **As a bare skill**: download `riffumi-skill.zip` from the
  [releases](https://github.com/TheBurdz/riffumi-skill/releases) or from
  [riffumi.com/skill](https://riffumi.com/skill), unzip it, and add the `riffumi` folder to your
  agent as a skill (or drop it in your project and point the agent at `riffumi/SKILL.md`).

Then, in the skill folder:

```bash
python3 scripts/setup.py                       # installs numpy + Pillow; prints the ffmpeg command
python3 scripts/check_env.py                   # what this machine can do, online or offline
python3 scripts/render.py examples/smoke-test.json --preview
```

## What the skill runs, fetches and sends

Everything the agent runs is in `skills/riffumi/scripts/`, plain Python 3.8+ that calls `ffmpeg`
and `ffprobe`. Nothing is compiled, minified or downloaded as code at run time.

- `setup.py` runs `pip install numpy pillow` for the Python that runs the scripts (and the
  optional `scipy`, `rembg`, `onnxruntime`, `faster-whisper` with `--extras`). It prints, and does
  not run, the ffmpeg install command for the platform.
- `check_env.py` sends a HEAD request to a few public hosts (pexels.com, mixkit.co, archive.org,
  fonts.googleapis.com, raw.githubusercontent.com, pypi.org) to tell online from offline, and
  writes `.riffumi_env.json` in the working folder.
- `get_fonts.py` fetches open-licence font files from Google Fonts (`fonts.googleapis.com`,
  `fonts.gstatic.com`) and the `google/fonts` GitHub repository into the skill's `fonts/` folder.
- `stock_search.py` builds pexels.com search URLs for the agent's own web tools and, with `--get`,
  downloads chosen clips through the clip's public download link (`pexels.com/download/video/<id>/`),
  logging source, licence, page and creator in a manifest. With a key the user passes on the
  command line it can query the Pexels or Pixabay API instead; it never reads keys from the
  environment or a file.
- `fetch_asset.py` downloads a file from a URL the agent gives it and logs the licence.
- `transcribe.py` runs a local whisper model when one is installed; audio never leaves the machine.
- `render.py`, `preflight.py`, `compose.py`, `matte.py`, `beats.py`, `inspect_media.py` and
  `blocks.py` work on local files only.

No telemetry, no account, no calls to riffumi.com.

## Build the archives yourself

```bash
python3 build.py            # dist/riffumi-skill.zip (skill folder) and dist/riffumi-plugin.zip (whole plugin)
```

## Reporting problems

Open an issue here, or email support@riffumi.com.
