#!/usr/bin/env python3
"""Find where the UI actually is in a recording, so the video can crop to it (`fit: "content"`).

    python3 content.py <clip.webm> [start] [length]     # prints {"crop": [x, y, w, h], "bg": "#rrggbb", ...}

Samples ~6 frames of the kept action. A row or column is empty when nearly all its pixels match
its own median colour: that covers the page background, blank space under a short page and
Playwright's grey padding alike. A side rail (a narrow strip at the left or right edge whose colour
differs from the page) is ignored when deciding which rows hold content, so a rail running down
an otherwise empty page doesn't keep that page in the crop; the rail is kept in the crop when the
content starts next to it. Small isolated specks at the edges (the cursor parked in a blank area)
are dropped. The box is padded by 2 % of the frame.
"""
import json, subprocess, sys
import numpy as np

SAMPLES, WIDTH = 6, 480       # frames sampled; analysis width in pixels
DIFF, BUSY = 30, 0.006        # a pixel differs from its line's median by > DIFF (sum of |RGB|);
                              # a line holds content when more than BUSY of its pixels differ
RAIL_MAX = 0.08               # a side rail is at most this share of the width
SPECK, SPECK_GAP = 0.03, 0.06  # drop an edge run shorter than SPECK set apart by more than SPECK_GAP
PAD = 0.02


def frames(path, start, length):
    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                    "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.strip().split(","))
    sh = round(h * WIDTH / w / 2) * 2
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{start}", "-t", f"{length}", "-i", path, "-vf",
                          f"fps={SAMPLES / max(length, 0.1):.5f},scale={WIDTH}:{sh}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, sh, WIDTH, 3).astype(np.int16)
    return a, w, h


def busy_lines(f, axis):
    """axis=1: per row; axis=0: per column. True where the line is not one flat colour."""
    med = np.median(f, axis=axis, keepdims=True)
    return (np.abs(f - med).sum(axis=2) > DIFF).mean(axis=axis) > BUSY


def rail(f):
    """Columns [0, r) (or [r, W)) of a side rail, or None: a narrow edge strip whose colour
    differs from the page's, with a clear change of colour where it ends."""
    W = f.shape[1]
    cols = np.median(f, axis=0)  # median colour per column
    page = np.median(cols[int(W * 0.2):int(W * 0.8)], axis=0)
    out = []
    for side in (1, -1):
        idx = list(range(W)) if side == 1 else list(range(W - 1, -1, -1))
        edge = cols[idx[0]]
        if np.abs(edge - page).sum() < 60:
            out.append(None)
            continue
        end = next((k for k in range(int(W * RAIL_MAX)) if np.abs(cols[idx[k]] - edge).sum() > 60), None)
        out.append(None if end is None else end)
    return out  # [left rail width, right rail width] in analysis pixels


def runs(mask):
    """Contiguous True runs as (start, end) with end exclusive."""
    out, s = [], None
    for i, v in enumerate(list(mask) + [False]):
        if v and s is None:
            s = i
        elif not v and s is not None:
            out.append((s, i))
            s = None
    return out


def span(mask):
    """First and last index of content, dropping small specks set apart at either edge."""
    r = runs(mask)
    n = len(mask)
    while len(r) > 1 and r[0][1] - r[0][0] < SPECK * n and r[1][0] - r[0][1] > SPECK_GAP * n:
        r.pop(0)
    while len(r) > 1 and r[-1][1] - r[-1][0] < SPECK * n and r[-1][0] - r[-2][1] > SPECK_GAP * n:
        r.pop()
    return (r[0][0], r[-1][1]) if r else (0, n)


def widen(lo, size, want, limit):
    """Grow [lo, lo+size) to `want` around its centre, kept inside [0, limit)."""
    want = min(want, limit)
    lo = lo - (want - size) / 2
    return min(max(0, lo), limit - want), want


def content_crop(path, start=0.0, length=None, aspect=None):
    """The crop [x, y, w, h] (recording pixels) around the UI, and the page colour.
    aspect: None keeps the content's own; a number forces it; (lo, hi) clamps it — the box grows
    on its short side, inside the frame (a box the frame can't grow to is letterboxed later)."""
    if length is None:
        length = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                      capture_output=True, text=True, check=True).stdout) - start
    a, W, H = frames(path, start, length)
    n, h, w, _ = a.shape
    left, right = rail(a[n // 2])
    lo_c, hi_c = (left or 0), w - (right or 0)
    rows = np.zeros(h, bool)
    cols = np.zeros(w, bool)
    for f in a:
        rows |= busy_lines(f[:, lo_c:hi_c], 1)
        cols |= busy_lines(f, 0)
    cols[:lo_c] = cols[hi_c:] = False
    y0, y1 = span(rows)
    x0, x1 = span(cols)
    if left and x0 - lo_c < 0.12 * w:  # content starts by the rail: keep the rail in the picture
        x0 = 0
    if right and hi_c - x1 < 0.12 * w:
        x1 = w
    s = W / w
    px, py = PAD * W, PAD * H
    x, y = max(0, x0 * s - px), max(0, y0 * s - py)
    cw, ch = min(W, x1 * s + px) - x, min(H, y1 * s + py) - y
    if aspect is not None:
        lo, hi = aspect if isinstance(aspect, (tuple, list)) else (aspect, aspect)
        if cw / ch < lo:
            x, cw = widen(x, cw, ch * lo, W)
        elif cw / ch > hi:
            y, ch = widen(y, ch, cw / hi, H)
    x, y, cw, ch = (int(round(v)) // 2 * 2 for v in (x, y, cw, ch))
    page = np.median(a[n // 2][:, lo_c:hi_c].reshape(-1, 3), axis=0)
    return {"crop": [x, y, cw, ch], "bg": "#" + "".join(f"{int(v):02x}" for v in page), "size": [W, H],
            "rail": [int((left or 0) * s), int((right or 0) * s)]}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    st = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    ln = float(sys.argv[3]) if len(sys.argv) > 3 else None
    print(json.dumps(content_crop(sys.argv[1], st, ln)))
