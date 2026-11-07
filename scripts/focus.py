#!/usr/bin/env python3
"""Find where the action is in a recording, for the camera of styles that zoom (keynote) or pan
(social). camera.py turns what this finds into camera moves.

    python3 focus.py <clip.webm> [start] [length]     # prints {"region": [x, y, w, h], "size": [W, H], ...}

Frame differencing over the kept action: frames are sampled (gray, 480 px wide) and each pair's
changed pixels form a mask. A pair where the page scrolled (shifting the frame explains the
change) or swapped says nothing about WHERE to look, so it is kept apart. The rest (the cursor
gliding, typing, a card opening, an answer appearing) is summed per stretch of ON-SCREEN time
(a wait the build fast-forwards counts for as long as the viewer sees it), as the union of what
changed in that stretch (a clock ticking in place counts once, not every second), weighted
towards the end of the scene, where the result is held. The region is the box holding the
central 84 % of that heat on each axis, padded and clamped to the frame. A clip that only
scrolls (only the cursor moved besides) gives the box of what scrolled. `centroids` gives the
same signal over time, so a crop can follow it.
"""
import json, subprocess, sys
import numpy as np

WIDTH = 480          # analysis width in pixels
MAX_SAMPLES = 360    # frames sampled at most (long clips are sampled more sparsely)
FPS = 8              # sampling rate for short clips
DIFF = 22            # a pixel changed when its gray level moved by more than this
GLOBAL = 0.18        # a pair where more than this share of pixels changed is a page swap
SHIFT = 60           # scrolls are found by shifting a frame up to this many analysis pixels
BUCKET = 0.25        # on-screen seconds per heat stretch
QUANT = 0.08         # the region drops this much of the heat at each side
PAD = 0.035          # padding around the region, as a share of the frame
MIN_HEAT = 40        # less than this (changed analysis pixels) is specks, not action
CURSOR_ONLY = 0.02   # local heat under this share of the scroll heat: only the cursor moved


def size(path):
    w, h = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                           "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.strip().split(",")
    return int(w), int(h)


def scrolled(a, b):
    """True when frame b is frame a moved up or down (a scroll), even when only a column of the
    page moves: within the columns that changed, shifting a by some dy explains most of it."""
    d = np.abs(a - b) > DIFF
    if d.mean() < 0.004:
        return False
    cols = d.mean(axis=0) > 0.01  # the scrolling part; fixed rails and sidebars stay out
    a, b = a[:, cols], b[:, cols]
    base = d[:, cols].mean()
    best = base
    for dy in range(-SHIFT, SHIFT + 1):
        if dy:
            x, y = (a[dy:], b[:-dy]) if dy > 0 else (a[:dy], b[-dy:])
            best = min(best, (np.abs(x - y) > DIFF).mean())
    return best < 0.35 * base


def activity(path, start=0.0, length=None, crop=None):
    """Per sampled pair: its time (seconds into the kept window), its changed mask, and whether it
    was global (a scroll or a page swap). crop [x, y, w, h]: analyse only that part (the box the
    video shows); coordinates are then relative to it."""
    W, H = size(path)
    if length is None:
        length = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                      capture_output=True, text=True, check=True).stdout) - start
    cx, cy, W, H = crop or (0, 0, W, H)
    rate = min(FPS, MAX_SAMPLES / max(length, 0.1))
    ah = round(H * WIDTH / W / 2) * 2
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{start}", "-t", f"{length}", "-i", path, "-vf",
                          f"crop={W}:{H}:{cx}:{cy},fps={rate:.5f},scale={WIDTH}:{ah}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, check=True).stdout
    g = np.frombuffer(raw, np.uint8).reshape(-1, ah, WIDTH).astype(np.int16)
    masks = np.abs(np.diff(g, axis=0)) > DIFF if len(g) > 1 else np.zeros((0, ah, WIDTH), bool)
    share = masks.reshape(len(masks), -1).mean(axis=1) if len(masks) else np.zeros(0)
    glob = np.array([s > GLOBAL or scrolled(g[i], g[i + 1]) for i, s in enumerate(share)], bool)
    return {"size": (W, H), "scale": W / WIDTH, "times": (np.arange(len(masks)) + 1) / rate, "masks": masks, "global": glob}


def screen_time(segs):
    """Kept-window seconds -> on-screen seconds from the footage's start, for build.py's segs
    [(from, to, speed)]."""
    def f(x):
        o = 0.0
        for a, b, v in segs:
            if x >= b:
                o += (b - a) / v
            else:
                return o + max(0.0, x - a) / v
        return o
    return f


def heat(act, segs=None):
    """(local, scroll) heat maps at the analysis size; either may be None."""
    to = screen_time(segs) if segs else (lambda x: x)
    o = np.array([to(t) for t in act["times"]])
    T = max(o[-1] if len(o) else 0.0, BUCKET)
    bucket = np.floor(o / BUCKET).astype(int)
    out = []
    for sel in (~act["global"], act["global"]):
        if not sel.any():
            out.append(None)
            continue
        h = np.zeros(act["masks"].shape[1:])
        for b in np.unique(bucket[sel]):
            h += act["masks"][sel & (bucket == b)].any(axis=0) * (0.4 + 0.6 * min(1.0, b * BUCKET / T))
        out.append(h if h.sum() >= MIN_HEAT else None)
    return out


def _span(weights, q):
    c = np.cumsum(weights)
    c = c / c[-1]
    return int(np.searchsorted(c, q)), int(np.searchsorted(c, 1 - q)) + 1


def region(act, segs=None):
    """The box [x, y, w, h] (pixels of the analysed frame) where the action is, or None when
    nothing changed."""
    return region_of(act, segs)[0]


def region_of(act, segs=None):
    """(box, "local" | "scroll" | None): the region, and whether it is where things changed in
    place or what scrolled (then the local change was only the cursor)."""
    local, scroll = heat(act, segs)
    kind = "local" if local is not None and (scroll is None or local.sum() >= CURSOR_ONLY * scroll.sum()) else "scroll"
    h = local if kind == "local" else scroll
    if h is None:
        return None, None
    (x0, x1), (y0, y1) = _span(h.sum(axis=0), QUANT), _span(h.sum(axis=1), QUANT)
    W, H = act["size"]
    s = act["scale"]
    x0, x1 = max(0, x0 * s - PAD * W), min(W, x1 * s + PAD * W)
    y0, y1 = max(0, y0 * s - PAD * H), min(H, y1 * s + PAD * H)
    return [int(x0), int(y0), int(x1 - x0), int(y1 - y0)], kind


def centroids(act, segs=None):
    """Per local pair: (on-screen time, mass, cx, cy), centre of what changed, frame pixels."""
    to = screen_time(segs) if segs else (lambda x: x)
    out, s = [], act["scale"]
    for t, m, glob in zip(act["times"], act["masks"], act["global"]):
        n = int(m.sum())
        if not glob and n >= 4:
            ys, xs = np.nonzero(m)
            out.append((to(t), float(n), float(xs.mean() * s), float(ys.mean() * s)))
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    st = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    ln = float(sys.argv[3]) if len(sys.argv) > 3 else None
    a = activity(sys.argv[1], st, ln)
    print(json.dumps({"region": region(a), "size": a["size"], "pairs": len(a["times"]), "scrolls": int(a["global"].sum())}))
