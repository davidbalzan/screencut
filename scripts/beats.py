#!/usr/bin/env python3
"""Find the beat grid of a music file (numpy + ffmpeg only, no librosa).

    python3 beats.py <music file> [--bpm 120]        # prints JSON: bpm, beats[], bars[]

Assumes a steady tempo (fine for the music beds these videos use). Onset strength is the
spectral flux of the track; the tempo is the strongest autocorrelation lag between 60 and
200 BPM (with a mild pull towards 120), refined to ±3 %; the phase is the grid offset that
lands on the most onsets. Bars are every 4th beat starting at the strongest of the four
phases — a guess, so `music.barOffset` in video.json can shift it by whole beats.
"""
import json, subprocess, sys
import numpy as np

SR, HOP, WIN = 22050, 256, 1024


def onset_envelope(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    if len(x) < WIN * 4:
        sys.exit(f"{path}: too short to find a beat")
    n = 1 + (len(x) - WIN) // HOP
    frames = np.lib.stride_tricks.as_strided(x, shape=(n, WIN), strides=(x.strides[0] * HOP, x.strides[0]))
    spec = np.abs(np.fft.rfft(frames * np.hanning(WIN), axis=1))
    # Coarse log-spaced bands: a kick sweeping down in pitch stays inside one band instead of
    # lighting up new bins through its tail (which drags the onset ~150 ms late).
    edges = np.unique(np.geomspace(2, spec.shape[1] - 1, 25).astype(int))
    bands = np.log1p(100 * np.add.reduceat(spec, edges, axis=1)[:, :-1])
    flux = np.maximum(np.diff(bands, axis=0), 0).sum(axis=1)
    flux = np.concatenate([[0], flux])
    lag = WIN / 2 / HOP  # the window sees an onset this many frames before its centre reaches it
    flux -= np.convolve(flux, np.ones(16) / 16, mode="same")  # remove the slow loudness trend
    return np.roll(np.maximum(flux, 0), int(round(lag))), len(x) / SR


def phase_score(env, period, phase):
    idx = np.round(np.arange(phase, len(env), period)).astype(int)
    return env[idx[idx < len(env)]].mean()


def best_phase(env, period):
    phases = np.arange(0, period, 0.5)
    scores = [phase_score(env, period, ph) for ph in phases]
    return phases[int(np.argmax(scores))], max(scores)


def analyse(path, bpm=None):
    env, dur = onset_envelope(path)
    fps = SR / HOP
    if bpm:
        period = 60 * fps / bpm
    else:
        ac = np.correlate(env, env, mode="full")[len(env) - 1:]
        lags = np.arange(int(60 * fps / 200), int(60 * fps / 60) + 1)
        prior = np.exp(-0.5 * (np.log2((60 * fps / lags) / 120) / 0.9) ** 2)
        period = lags[int(np.argmax(ac[lags] * prior))]
        cands = period * np.linspace(0.97, 1.03, 61)
        period = cands[int(np.argmax([best_phase(env, c)[1] for c in cands]))]
    phase, _ = best_phase(env, period)
    beats = [round(float(t), 3) for t in np.arange(phase, len(env), period) / fps if t < dur]
    bar_strength = [np.mean([env[int(round(b * fps))] for b in beats[j::4]]) for j in range(min(4, len(beats)))]
    first_bar = int(np.argmax(bar_strength)) if bar_strength else 0
    return {"bpm": round(60 * fps / period, 2), "beats": beats, "barPhase": first_bar, "duration": round(dur, 3)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    bpm = float(sys.argv[sys.argv.index("--bpm") + 1]) if "--bpm" in sys.argv else None
    r = analyse(sys.argv[1], bpm)
    r["bars"] = r["beats"][r["barPhase"]::4]
    print(json.dumps(r))
