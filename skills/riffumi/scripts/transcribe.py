#!/usr/bin/env python3
"""Word-timed transcript for captions and talking-head cut lists.

    python3 transcribe.py take.mp4 --out take_words.json [--srt take.srt] [--model small]

Uses faster-whisper if installed (pip install faster-whisper), else openai-whisper
(pip install openai-whisper). Both download a model on first use; if that is
blocked, say so and offer the user to supply a transcript or an .srt instead.
Output: {"words": [{"w", "s", "e"}], "segments": [{"text", "s", "e"}]} - feed
"words" to a captions layer, and read "segments" to plan the cut list.
"""
import argparse
import json
import sys


def fmt(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("media")
    ap.add_argument("--out", required=True)
    ap.add_argument("--srt")
    ap.add_argument("--model", default="small")
    ap.add_argument("--language")
    a = ap.parse_args()
    words, segs = [], []
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel(a.model, compute_type="int8")
        it, _ = model.transcribe(a.media, word_timestamps=True, language=a.language)
        for s in it:
            segs.append({"text": s.text.strip(), "s": round(s.start, 3), "e": round(s.end, 3)})
            for w in s.words or []:
                words.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)})
    except ImportError:
        try:
            import whisper  # type: ignore
        except ImportError:
            sys.exit("No speech model installed. pip install faster-whisper (or openai-whisper), "
                     "or ask the user for a transcript/.srt.")
        model = whisper.load_model(a.model)
        res = model.transcribe(a.media, word_timestamps=True, language=a.language)
        for s in res["segments"]:
            segs.append({"text": s["text"].strip(), "s": round(s["start"], 3), "e": round(s["end"], 3)})
            for w in s.get("words", []):
                words.append({"w": w["word"].strip(), "s": round(w["start"], 3), "e": round(w["end"], 3)})
    with open(a.out, "w") as f:
        json.dump({"words": words, "segments": segs}, f, indent=1)
    if a.srt:
        with open(a.srt, "w") as f:
            for i, s in enumerate(segs, 1):
                f.write(f"{i}\n{fmt(s['s'])} --> {fmt(s['e'])}\n{s['text']}\n\n")
    print(json.dumps({"words": len(words), "segments": len(segs), "out": a.out}))


if __name__ == "__main__":
    main()
