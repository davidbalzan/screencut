"""Presentation exports (keynote): each scene alone, ready to drop one per slide into Keynote or
PowerPoint. Called by build.py after the full video when `exports.slides` is on (keynote's
default).

    <work>/slides/NN-<clip>.mp4   the scene's footage in its window frame, zoom, spotlight and
                                  callout included, title and chapter bar left out (the slide
                                  has its own); fades in from the ground and out to it, so it
                                  loops cleanly; no audio; H.264 high, faststart
    <work>/slides/NN-<clip>.png   a poster frame at the scene's settled zoom
    <work>/slides/index.md        the list, with titles and callouts

`exports.aspect`: "16:9" (1920x1080, default) or "4:3" (1440x1080).
"""
import json, os, shutil

SIZES = {"16:9": (1920, 1080), "4:3": (1440, 1080)}
MARGIN, BAR, CALLOUT = 56, 38, 66   # around the window; its top bar; the callout band under it
FADE = 0.4
ENC = ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-level:v", "4.1",
       "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an"]


def plain(title):
    return title if isinstance(title, str) else "".join(s for s, _ in title)


def _fit(aspect, x, y, w, h):
    fw, fh = (w, w / aspect) if w / h < aspect else (h * aspect, h)
    fw, fh = int(fw) // 2 * 2, int(fh) // 2 * 2
    return [x + (w - fw) // 2, y + (h - fh) // 2, fw, fh]


def shifted(sc, dt):
    """The scene with every time moved by -dt (frames stay put: they are indexed from start)."""
    s = dict(sc)
    for k in ("start", "fstart", "end"):
        s[k] = round(sc[k] - dt, 3)
    s["view"] = [[round(v[0] - dt, 3), *v[1:]] for v in sc.get("view", [])]
    s["spots"] = [[round(a - dt, 3), round(b - dt, 3), *r] for a, b, *r in sc.get("spots", [])]
    s["ff"] = [[round(a - dt, 3), round(b - dt, 3), v] for a, b, v in sc.get("ff", [])]
    return s


def export(tl, work, dest, aspect, run, here):
    W, H = SIZES[aspect]
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)
    rows = []
    for sc in tl["scenes"]:
        s = shifted(sc, sc["fstart"])
        cw, ch = sc["fsize"]
        box_h = H - 2 * MARGIN - BAR - CALLOUT
        s["rect"] = _fit(cw / ch, MARGIN, MARGIN + BAR, W - 2 * MARGIN, box_h)
        s["rect"][1] = (H - s["rect"][3] - BAR - CALLOUT) // 2 + BAR  # window (bar + footage) and the callout band, centred
        total = round(s["end"], 3)
        stl = {**tl, "total": total, "size": [W, H], "slide": {"fade": FADE}, "scenes": [s], "cuts": [], "voice": [],
               "captions": [], "intro": {**tl["intro"], "len": 0}, "end": {**tl["end"], "len": 0}}
        name = f"{sc['n']:02d}-{sc['clip']}"
        tmp = os.path.join(work, "slide-frames", name)
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp)
        tlf = os.path.join(tmp, "timeline.json")
        json.dump(stl, open(tlf, "w"))
        run(["node", os.path.join(here, "render.mjs"), tlf, tmp, str(tl["fps"])])
        mp4 = os.path.join(dest, name + ".mp4")
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-framerate", str(tl["fps"]), "-i", os.path.join(tmp, "%05d.jpg"), *ENC, mp4])
        spot = s["spots"][0] if s["spots"] else None
        at = (spot[0] + spot[1]) / 2 if spot else total * 0.6
        pdir = os.path.join(tmp, "poster")
        run(["node", os.path.join(here, "render.mjs"), tlf, pdir, str(tl["fps"]), "--frames", str(int(at * tl["fps"])), "--png"])
        png = os.path.join(dest, name + ".png")
        shutil.move(os.path.join(pdir, os.listdir(pdir)[0]), png)
        rows.append((name, plain(sc["title"]), sc.get("callout", ""), total))
    with open(os.path.join(dest, "index.md"), "w") as f:
        f.write(f"# Slides\n\nOne clip per slide ({aspect}, {W}x{H}, no audio, loops cleanly), each with a poster frame.\n\n")
        f.write("| # | Title | Callout | Clip | Poster | Length |\n|---|---|---|---|---|---|\n")
        for i, (name, title, callout, d) in enumerate(rows, 1):
            f.write(f"| {i} | {title} | {callout} | [{name}.mp4]({name}.mp4) | [{name}.png]({name}.png) | {d:.1f} s |\n")
    shutil.rmtree(os.path.join(work, "slide-frames"), ignore_errors=True)
    print(f"slides: {len(rows)} clips + posters in {dest} (index.md lists them)")
