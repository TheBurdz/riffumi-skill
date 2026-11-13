#!/bin/sh
# Build dist/riffumi-skill.zip from the riffumi/ folder (no caches, no fetched fonts).
set -e
cd "$(dirname "$0")"
mkdir -p dist
rm -f dist/riffumi-skill.zip
find riffumi -name '__pycache__' -type d -prune -exec rm -rf {} +
rm -f riffumi/.riffumi_env.json
zip -q -r dist/riffumi-skill.zip riffumi \
  -x 'riffumi/fonts/*.ttf' 'riffumi/fonts/*.otf' '*/.DS_Store' '*/__pycache__/*'
ls -la dist/riffumi-skill.zip
