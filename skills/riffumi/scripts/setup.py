"""Install what the Riffumi skill needs to render on this machine.

    python3 scripts/setup.py          # install numpy + Pillow for this Python, report ffmpeg
    python3 scripts/setup.py --extras # also scipy, rembg + onnxruntime, faster-whisper
    python3 scripts/setup.py --dry    # only print what it would run

Uses the same interpreter you run the scripts with (sys.executable), so the
packages land where render.py will find them. ffmpeg is a system package;
the script prints the install command for this platform instead of running it.
"""
import argparse
import importlib
import platform
import shutil
import subprocess
import sys

REQUIRED = [("numpy", "numpy"), ("PIL", "pillow")]
EXTRAS = [("scipy", "scipy"), ("rembg", "rembg"), ("onnxruntime", "onnxruntime"),
          ("faster_whisper", "faster-whisper")]

FFMPEG_HINTS = {
    "Darwin": "brew install ffmpeg",
    "Linux": "sudo apt-get install -y ffmpeg   (or: sudo dnf install ffmpeg)",
    "Windows": "winget install Gyan.FFmpeg   (or: choco install ffmpeg)",
}


def have(mod):
    try:
        importlib.import_module(mod)
        return True
    except Exception:
        return False


def pip_install(pkgs, dry):
    cmd = [sys.executable, "-m", "pip", "install", "--quiet"] + pkgs
    print("run: " + " ".join(cmd))
    if dry:
        return 0
    r = subprocess.run(cmd)
    if r.returncode and "--user" not in cmd:
        print("retrying with --user")
        r = subprocess.run(cmd + ["--user"])
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extras", action="store_true", help="also install the optional packages")
    ap.add_argument("--dry", action="store_true", help="print the commands, change nothing")
    a = ap.parse_args()
    print(f"python: {sys.executable} ({platform.python_version()})")
    want = [pkg for mod, pkg in REQUIRED if not have(mod)]
    if a.extras:
        want += [pkg for mod, pkg in EXTRAS if not have(mod)]
    if want:
        rc = pip_install(want, a.dry)
        if rc:
            print("pip failed. Create a virtual environment and try again:\n"
                  "  python3 -m venv .venv && .venv/bin/pip install numpy pillow\n"
                  "then run the scripts with .venv/bin/python.")
            sys.exit(rc)
    else:
        print("python packages: already installed")
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        print("ffmpeg: found")
    else:
        hint = FFMPEG_HINTS.get(platform.system(), "install ffmpeg from ffmpeg.org/download.html")
        print("ffmpeg: MISSING. Install it with:\n  " + hint)
    print("done. Run python3 scripts/check_env.py to confirm, then "
          "python3 scripts/render.py examples/smoke-test.json --preview")


if __name__ == "__main__":
    main()
