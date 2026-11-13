# Riffumi skill

The local edition of [Riffumi](https://riffumi.com): a video director your AI agent follows,
with a working ffmpeg renderer, b-roll search, beat sync, cutouts, composites and a production
bar it measures before delivering. MIT licensed.

- The skill itself is in [`riffumi/`](riffumi/) - start with its [README](riffumi/README.md)
  and [SKILL.md](riffumi/SKILL.md).
- Prefer nothing to install? The hosted connector at [riffumi.com](https://riffumi.com) renders
  on Riffumi's servers and works from any AI app that takes MCP connectors, phones included.
  [Which one is for you](https://riffumi.com/skill).

## Get the zip

Download the latest `riffumi-skill.zip` from the
[releases](https://github.com/TheBurdz/riffumi-skill/releases) or from
[riffumi.com/skill](https://riffumi.com/skill), then add the unzipped `riffumi` folder to your
agent as a skill.

## Build the zip yourself

```bash
./build.sh            # writes dist/riffumi-skill.zip
```

## Quick check

```bash
cd riffumi
python3 scripts/setup.py                       # numpy + Pillow; prints the ffmpeg command
python3 scripts/check_env.py                   # what this machine can do
python3 scripts/render.py examples/smoke-test.json --preview
```

## Reporting problems

Open an issue here, or email support@riffumi.com.
