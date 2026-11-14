#!/usr/bin/env python3
"""Find the tempo and beat grid of a music track so cuts can land on the beat.

    python3 beats.py track.mp3 [--min-bpm 70 --max-bpm 180] [--fps 30] [--json out.json]

Prints JSON: bpm, offset (time of the first beat, s), beat seconds, frames per
beat at --fps, confidence, the loudness curve per second, and `drop` (the
biggest rise in energy, a natural place for the reveal). Paste bpm and offset
into the spec's "beat" block, and trim the track with music.start = offset so
beat 0 lands on frame 0.

Half/double tempo is ambiguous by nature: 70 and 140 fit the same kick. Pick
the one that matches the energy you hear, or pin --min-bpm/--max-bpm.
"""
import argparse
import json
import subprocess
import sys

import numpy as np


def decode(path, sr, seconds):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr)]
    if seconds:
        cmd += ["-t", str(seconds)]
    cmd += ["-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        sys.exit("cannot decode audio: " + r.stderr.decode()[:300])
    return np.frombuffer(r.stdout, np.float32)


def onset_env(a, sr, hop=256, n=1024, band=None):
    if len(a) < n * 2:
        return np.zeros(1), sr / hop
    fr = np.lib.stride_tricks.sliding_window_view(a, n)[::hop] * np.hanning(n)
    S = np.abs(np.fft.rfft(fr, axis=1))
    if band:
        S = S[:, :band]
    flux = np.maximum(np.diff(np.log1p(S * 10), axis=0), 0).sum(1)
    return flux, sr / hop


def grid_score(flux, fps_env, bpm, phase, span):
    B = 60.0 / bpm
    ts = np.arange(phase, span, B)
    idx = np.round(ts * fps_env).astype(int)
    idx = idx[(idx >= 0) & (idx < len(flux))]
    return float(flux[idx].mean()) if len(idx) else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("--min-bpm", type=float, default=70)
    ap.add_argument("--max-bpm", type=float, default=180)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--seconds", type=float, default=60, help="analyse this much of the track")
    ap.add_argument("--json", help="also write the result here")
    a = ap.parse_args()
    sr = 22050
    x = decode(a.audio, sr, a.seconds)
    full = decode(a.audio, 8000, None)
    flux_all, fe = onset_env(x, sr)
    flux_low, _ = onset_env(x, sr, band=60)  # kick / bass region
    flux = flux_low / (flux_low.mean() + 1e-9) + 0.5 * flux_all / (flux_all.mean() + 1e-9)
    span = len(x) / sr - 0.5
    # coarse autocorrelation for candidates
    f0 = flux - flux.mean()
    ac = np.correlate(f0, f0, "full")[len(f0) - 1:]
    cands = []
    for bpm in np.arange(a.min_bpm, a.max_bpm + 0.01, 0.5):
        lag = 60.0 / bpm
        k = int(round(lag * fe))
        if 0 < k < len(ac):
            cands.append((ac[k], bpm))
    cands.sort(reverse=True)
    best = (0.0, None, 0.0)
    scores = []
    for _, c in cands[:6]:
        for bpm in np.arange(c - 1.0, c + 1.0001, 0.02):
            B = 60.0 / bpm
            for ph in np.arange(0, B, 0.005):
                s = grid_score(flux, fe, bpm, ph, span)
                if s > best[0]:
                    best = (s, float(bpm), float(ph))
        scores.append((best[0], best[1]))
    score, bpm, phase = best
    base = float(flux.mean())
    conf = max(0.0, min(1.0, (score / (base + 1e-9) - 1.0) / 2.0))
    # alternatives at half and double tempo
    alts = []
    for m in (0.5, 2.0, 2 / 3, 1.5):
        b2 = bpm * m
        if a.min_bpm * 0.5 <= b2 <= a.max_bpm * 2:
            best2 = max(grid_score(flux, fe, b2, ph, span) for ph in np.arange(0, 60 / b2, 0.01))
            alts.append({"bpm": round(b2, 2), "fit": round(best2 / (score + 1e-9), 3)})
    B = 60.0 / bpm
    # loudness per second (whole track) and the biggest rise
    sec = 8000
    rms = [float(np.sqrt(np.mean(full[i * sec:(i + 1) * sec] ** 2) + 1e-12)) for i in range(len(full) // sec)]
    db = [round(20 * np.log10(r + 1e-9), 1) for r in rms]
    drop = None
    if len(db) > 4:
        sm = np.convolve(db, np.ones(2) / 2, "same")
        jumps = [(sm[i + 1] - sm[max(0, i - 2)], i + 1) for i in range(2, len(sm) - 1)]
        j, i = max(jumps)
        if j > 3:
            drop = {"second": i, "rise_db": round(float(j), 1)}
    # downbeat guess: which beat of four carries most low-end energy
    acc = []
    for k in range(4):
        acc.append(grid_score(flux_low, fe, bpm / 4, phase + k * B, span))
    bar_phase = int(np.argmax(acc))
    out = {
        "bpm": round(bpm, 2), "offset": round(phase, 3), "beat_seconds": round(B, 5),
        "frames_per_beat": round(B * a.fps, 3), "confidence": round(conf, 2),
        "downbeat_offset": round(phase + bar_phase * B, 3),
        "downbeat_confidence": round(float((max(acc) - np.mean(acc)) / (np.mean(acc) + 1e-9)), 2),
        "alternatives": alts, "duration": round(len(full) / 8000, 2), "loudness_db_per_second": db,
        "drop": drop,
        "how_to_use": "spec.beat = {bpm, offset: 0}; spec.music.start = offset (or downbeat_offset to start on a bar); "
                      "give scenes whole-beat lengths with \"beats\": N.",
    }
    s = json.dumps(out, indent=1)
    print(s)
    if a.json:
        with open(a.json, "w") as f:
            f.write(s)


if __name__ == "__main__":
    main()
