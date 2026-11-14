"""Build the two archives (no caches, no fetched fonts, no system files):

  dist/riffumi-skill.zip    the skill folder alone (unzips to riffumi/); served from riffumi.com/skill
  dist/riffumi-plugin.zip   the whole plugin (manifests + skills/ + README + LICENSE + assets),
                            the archive the OpenAI plugin portal takes

    python3 build.py
"""
import os
import shutil
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {"__pycache__"}
SKIP_FILES = {".DS_Store", ".riffumi_env.json"}
SKIP_FONTS = (".ttf", ".otf")


def walk(top):
    for d, dirs, files in os.walk(top):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            if f in SKIP_FILES or (f.lower().endswith(SKIP_FONTS) and os.path.basename(d) == "fonts"):
                continue
            yield os.path.join(d, f)


def build(out, roots, base):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for r in roots:
            full = os.path.join(ROOT, r)
            for f in ([full] if os.path.isfile(full) else walk(full)):
                z.write(f, os.path.relpath(f, base))
    print(f"{out}  {os.path.getsize(out)} bytes")


def main():
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    for d, dirs, _ in os.walk(os.path.join(ROOT, "skills")):
        for x in dirs:
            if x == "__pycache__":
                shutil.rmtree(os.path.join(d, x))
    build(os.path.join(ROOT, "dist", "riffumi-skill.zip"), ["skills/riffumi"], os.path.join(ROOT, "skills"))
    build(os.path.join(ROOT, "dist", "riffumi-plugin.zip"),
          [".claude-plugin", "plugin.json", "skills", "README.md", "LICENSE", "assets"], ROOT)


if __name__ == "__main__":
    main()
