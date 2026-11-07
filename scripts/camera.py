"""Camera moves for styles whose footage box looks at part of the recording: keynote zooms
(ease in to where the action is, hold, ease out) and social pans (a vertical crop that follows
the action). build.py calls plan() per scene; the HUD interpolates the result.

Where to look, in order: the scene's `focus` [x, y, w, h] (recording pixels), the boxes the
recorder logged for the clip (clips.json `focus: [{t, box}]`, from rig.mjs glide()/focus()),
else the motion finder (focus.py). All boxes here are in pixels of the footage as the video
shows it (the recording, or its crop).

A view is [x, y, w, h] with the footage box's aspect; keyframes are [t, x, y, w, h] in timeline
seconds. Spots (keynote) are [t0, t1, x, y, w, h]: the box the spotlight and callout point at.
"""
import math
import numpy as np
import focus as finder

ZOOM_FILL = (0.8, 0.72)   # keynote: the region fills at most this share of the view (w, h)
PAN_FILL = (0.92, 0.85)   # social: the same for the crop
SAMPLE = 0.1              # social: seconds between keyframes


def _clamp(v, a, b):
    return max(a, min(b, v))


def full_view(W, H, aspect):
    """The largest box of `aspect` in the frame, centred."""
    w = min(W, H * aspect)
    h = w / aspect
    return [(W - w) / 2, (H - h) / 2, w, h]


def view_on(box, W, H, aspect, zmin, zmax, fill, at=None):
    """A view of `aspect` around box: as close as fill allows, zoom (relative to the full view)
    kept within [zmin, zmax], centred on `at` (else the box's centre), inside the frame."""
    fx, fy, fw, fh = full_view(W, H, aspect)
    bx, by, bw, bh = box
    z = _clamp(min(fill[0] * fw / max(bw, 1), fill[1] * fh / max(bh, 1)), zmin, zmax)
    vw, vh = fw / z, fh / z
    cx, cy = at or (bx + bw / 2, by + bh / 2)
    return [_clamp(cx - vw / 2, 0, W - vw), _clamp(cy - vh / 2, 0, H - vh), vw, vh], z


def _inter(a, b, inset=0.04):
    """The spot: box a grown to a readable minimum (a thin cursor trail would cut through what it
    passes), cut to view b and kept a little inside it."""
    a = list(a)
    for i, share in ((0, 0.25), (1, 0.3)):  # at least this share of the view's width / height
        need = b[2 + i] * share
        if a[2 + i] < need:
            a[i] -= (need - a[2 + i]) / 2
            a[2 + i] = need
    x0, y0 = max(a[0], b[0] + b[2] * 0.012), max(a[1], b[1] + b[3] * inset)
    x1, y1 = min(a[0] + a[2], b[0] + b[2] * 0.988), min(a[1] + a[3], b[1] + b[3] * (1 - inset))
    return [x0, y0, max(0, x1 - x0), max(0, y1 - y0)]


def _r(v):
    return [round(float(x), 2) for x in v]


def targets(scene, clip, crop, src, segs, fstart, kept_off):
    """Where the action is: ("focus" | "logged" | "motion" | "none", boxes [(t, box)], centroids).
    t is timeline seconds; boxes are in footage pixels (crop offset applied)."""
    ox, oy = (crop[0], crop[1]) if crop else (0, 0)
    to = finder.screen_time(segs)
    if scene.get("focus"):
        x, y, w, h = scene["focus"]
        return "focus", [(fstart, [x - ox, y - oy, w, h])], []
    if clip.get("focus"):
        out = []
        for f in clip["focus"]:
            x, y, w, h = f["box"]
            out.append((fstart + to(max(0.0, f["t"] + kept_off)), [x - ox, y - oy, w, h]))
        return "logged", out, []
    act = finder.activity(src[0], src[1], src[2], crop)
    r, where = finder.region_of(act, segs)
    if not r:
        return "none", [], []
    # a region of what scrolled: the change in place was only the cursor, nothing to follow
    cents = [(fstart + t, m, x, y) for t, m, x, y in finder.centroids(act, segs)] if where == "local" else []
    return "motion", [(fstart, r)], cents


def zoom(kind, boxes, W, H, aspect, fstart, end, zmin, zmax):
    """Keynote: ease into the action, hold, ease out by the cut. Several logged boxes that don't
    fit one view become stops the camera moves between."""
    full = full_view(W, H, aspect)
    L = end - fstart
    din, dout = _clamp(0.22 * L, 0.6, 1.1), _clamp(0.18 * L, 0.5, 0.9)
    in0, out1 = fstart + 0.35, end - 0.1
    out0 = out1 - dout
    if not boxes or zmax <= 1.0 or out0 - (in0 + din) < 0.8:
        return [[round(fstart, 3), *_r(full)]], []
    def arrivals(bs):  # when the camera reaches each stop: after its box is logged, a hold apart
        out, t_ = [], in0
        for i, (t, _) in enumerate(bs):
            out.append(max(t_ + din, t + 0.2 if i else in0 + din))
            t_ = out[-1] + 0.6
        return out
    if len(boxes) > 1:
        xs = [b[0] for _, b in boxes] + [b[0] + b[2] for _, b in boxes]
        ys = [b[1] for _, b in boxes] + [b[1] + b[3] for _, b in boxes]
        union = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
        fx, fy, fw, fh = full
        fits = min(ZOOM_FILL[0] * fw / max(union[2], 1), ZOOM_FILL[1] * fh / max(union[3], 1)) >= zmin
        if fits or arrivals(boxes)[-1] > out0 - 0.6:  # one view holds them all, or no time to visit each
            boxes = [(boxes[0][0], union)]
    keys, spots, prev = [[fstart, *full], [in0, *full]], [], full
    for i, ((t, box), arrive) in enumerate(zip(boxes, arrivals(boxes))):
        v, _ = view_on(box, W, H, aspect, zmin, zmax, ZOOM_FILL)
        if i:
            keys.append([arrive - din, *prev])
            spots[-1][1] = arrive - din
        keys.append([arrive, *v])
        spots.append([arrive + 0.05, out0, *_inter(box, v)])
        prev = v
    keys += [[out0, *prev], [out1, *full]]
    return [[round(k[0], 3), *_r(k[1:])] for k in keys], [[round(s[0], 3), round(s[1], 3), *_r(s[2:])] for s in spots if s[4] > 0 and s[5] > 0]


def _smooth(v, sigma):
    if sigma <= 0 or len(v) < 3:
        return v
    r = int(math.ceil(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(v, r, mode="edge"), k, mode="valid")


def pan(kind, boxes, cents, W, H, aspect, fstart, end, zmin, zmax):
    """Social: a crop of `aspect` that follows the action, gently: targets are smoothed, the crop
    only moves once the action leaves its middle, and never faster than half its width a second."""
    if not boxes:
        return [[round(fstart, 3), *_r(view_on([0, 0, W, H], W, H, aspect, zmin, zmax, PAN_FILL)[0])]]
    xs = [b[0] for _, b in boxes] + [b[0] + b[2] for _, b in boxes]
    ys = [b[1] for _, b in boxes] + [b[1] + b[3] for _, b in boxes]
    big = [0, 0, max(b[2] for _, b in boxes), max(b[3] for _, b in boxes)]  # the crop fits the largest box
    vw, vh = view_on(big, W, H, aspect, zmin, zmax, PAN_FILL)[0][2:]
    ts = np.arange(fstart, end + 1e-6, SAMPLE)
    first = boxes[0][1]
    tx, ty = first[0] + first[2] / 2, first[1] + first[3] / 2
    if kind == "motion" and cents:
        ct = np.array([c[0] for c in cents]); cm = np.array([c[1] for c in cents])
        cx = np.array([c[2] for c in cents]); cy = np.array([c[3] for c in cents])
        # keep the centroids inside the region (strays far off it are noise for a crop)
        x0, y0 = min(xs), min(ys)
        cx, cy = np.clip(cx, x0, max(xs)), np.clip(cy, y0, max(ys))
    # A region wider than the crop is read left to right (lines of text, a form): the crop holds
    # the region's left edge and moves right only when the action passes 90 % of its width.
    rx0, rx1 = min(xs), max(xs)
    wide = rx1 - rx0 > vw
    lead = lambda x: _clamp(max(rx0, x - 0.9 * vw) + vw / 2, rx0 + vw / 2, rx1 - vw / 2) if wide else x
    if wide:
        tx = rx0 + vw / 2
    gx, gy = [], []
    for t in ts:
        if kind == "logged":
            past = [b for bt, b in boxes if bt <= t + 0.3] or [first]
            b = past[-1]
            tx, ty = lead(b[0] + b[2] / 2), b[1] + b[3] / 2
        elif kind == "motion" and cents:
            w = cm * np.exp(-0.5 * ((ct - t) / 0.5) ** 2)
            if w.sum() > 30:
                tx, ty = lead(float((w * cx).sum() / w.sum())), float((w * cy).sum() / w.sum())
        gx.append(tx)
        gy.append(ty)
    gx, gy = _smooth(np.array(gx), 0.6 / SAMPLE), _smooth(np.array(gy), 0.6 / SAMPLE)
    cam = [gx[0], gy[0]]
    px, py = [], []
    step = 0.5 * vw * SAMPLE
    for x, y in zip(gx, gy):
        for i, (g, dz) in enumerate(((x, 0.18 * vw), (y, 0.18 * vh))):
            d = g - cam[i]
            if abs(d) > dz:
                cam[i] += _clamp(d - math.copysign(dz, d), -step, step)
        px.append(cam[0])
        py.append(cam[1])
    px, py = _smooth(np.array(px), 0.3 / SAMPLE), _smooth(np.array(py), 0.3 / SAMPLE)
    keys = []
    for t, x, y in zip(ts, px, py):
        keys.append([round(float(t), 3), *_r([_clamp(x - vw / 2, 0, W - vw), _clamp(y - vh / 2, 0, H - vh), vw, vh])])
    return keys


def plan(style, scene, clip, crop, fsize, rect, src, segs, fstart, end, kept_off, zoom_max=None):
    """The camera of one scene: {view, viewEase, spots, focusFrom}. src = (file, start, length)."""
    W, H = fsize
    # zoom: the box was fit to the footage's aspect (to even pixels), so the footage's own is exact
    aspect = W / H if style["camera"] == "zoom" else rect[2] / rect[3]
    zmin, zmax = style.get("zoomMin", 1.0), float(zoom_max if zoom_max is not None else style.get("zoomMax", 2.0))
    if zmax <= 1.0:
        return {"view": [[round(fstart, 3), *_r(full_view(W, H, aspect))]], "viewEase": True, "spots": [], "focusFrom": "off"}
    kind, boxes, cents = targets(scene, clip, crop, src, segs, fstart, kept_off)
    zmin = min(zmin, zmax)
    if style["camera"] == "pan":
        return {"view": pan(kind, boxes, cents, W, H, aspect, fstart, end, zmin, zmax), "viewEase": False, "spots": [], "focusFrom": kind}
    view, spots = zoom(kind, boxes, W, H, aspect, fstart, end, zmin, zmax)
    return {"view": view, "viewEase": True, "spots": spots, "focusFrom": kind}
