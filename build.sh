#!/bin/sh
# Build the two archives (no caches, no fetched fonts):
#   dist/riffumi-skill.zip    the skill folder alone (unzips to riffumi/); served from riffumi.com/skill
#   dist/riffumi-plugin.zip   the whole plugin (manifests + skills/ + README + LICENSE + assets);
#                             the archive the OpenAI plugin portal takes for a skills-only upload
set -e
cd "$(dirname "$0")"
mkdir -p dist
rm -f dist/riffumi-skill.zip dist/riffumi-plugin.zip
find skills -name '__pycache__' -type d -prune -exec rm -rf {} +
rm -f skills/riffumi/.riffumi_env.json
(cd skills && zip -q -r ../dist/riffumi-skill.zip riffumi \
  -x 'riffumi/fonts/*.ttf' 'riffumi/fonts/*.otf' '*/.DS_Store' '*/__pycache__/*')
zip -q -r dist/riffumi-plugin.zip .claude-plugin plugin.json skills README.md LICENSE assets \
  -x 'skills/riffumi/fonts/*.ttf' 'skills/riffumi/fonts/*.otf' '*/.DS_Store' '*/__pycache__/*'
ls -la dist/
