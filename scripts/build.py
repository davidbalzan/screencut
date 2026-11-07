#!/usr/bin/env python3
"""Assemble a CCTV-style video from a video.json (see examples/video.example.json).

    python3 build.py <video.json> [--sheet]      # --sheet: contact sheet only (one frame per scene), no full export

Steps: base footage (each clip trimmed to its action, sped up, cropped into its rect on a
near-black canvas) -> glitch at the cuts + fine grain -> the HUD rendered frame by frame
(render.mjs) and overlaid -> music and/or voice lines -> H.264 mp4.
No ffmpeg text filters anywhere: every word on screen is HTML in the HUD.
"""
import base64, json, math, os, subprocess, sys, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import beats, config, doctor
FPS = 30
BG = "0x03060b"
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an"]
# Final export: high@4.1 so older phones/TVs play it (x264 picks 5.0 on its own with -preset slow).
FINAL = ["-c:v", "libx264", "-preset", "slow", "-crf", "22", "-profile:v", "high", "-level:v", "4.1",
         "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p"]
RECTS = {"desk": [90, 60, 1074, 960], "wide": [90, 150, 1280, 800], "phone": [420, 60, 444, 960]}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"failed: {' '.join(cmd[:6])} …\n{r.stderr[-2000:]}")
    return r.stdout


def probe_dur(f):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).strip())


def probe_size(f):
    w, h = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", f]).strip().split(",")
    return int(w), int(h)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cfg_path = os.path.abspath(sys.argv[1])
    sheet_only = "--sheet" in sys.argv
    base = os.path.dirname(cfg_path)
    p = lambda x: x if os.path.isabs(x) else os.path.join(base, x)
    cfg = json.load(open(cfg_path))
    if errs := config.validate(cfg, p):
        sys.exit(f"{cfg_path}: {len(errs)} problem(s), nothing built:\n  " + "\n  ".join(errs))
    if missing := [f"{name}: {detail}\n    fix: {fix}" for ok, name, detail, fix in doctor.required() if not ok]:
        sys.exit("not set up yet:\n  " + "\n  ".join(missing) + f"\n(full report: python3 {os.path.join(HERE, 'doctor.py')})")

    speed = float(cfg.get("speed", 1.5))
    brand = {"accent": "#4ade80", "alert": "#f87171", "glow": "#0b2416", "site": "", "date": "", "clock": "04:21:07", **cfg.get("brand", {})}
    for k in ("accent", "alert"):
        if not (brand[k].startswith("#") and len(brand[k]) == 7):
            sys.exit(f"brand.{k} must be a 6-digit hex colour like #4ade80")
    intro = {"len": 3.0, "alert": "● ALERT // NEW FEATURE", "title": "", "sub": "", **cfg.get("intro", {})}
    end = {"len": 3.4, "line": "", "url": "", **cfg.get("end", {})}
    if end.get("logo"):
        def logo_html(f, h):
            if f.lower().endswith(".svg"):
                return open(p(f)).read().replace("<svg", f'<svg style="height:{h}px;width:auto"', 1)
            mime = {"png": "image/png", "webp": "image/webp", "jpg": "image/jpeg", "jpeg": "image/jpeg"}[f.rsplit(".", 1)[-1].lower()]
            data = base64.b64encode(open(p(f), "rb").read()).decode()
            return f'<img src="data:{mime};base64,{data}" style="height:{h}px;width:auto">'
        sizes = end.get("logoHeights", [110, 70, 70, 70])
        end["logoHtml"] = "".join(logo_html(f, h) for f, h in zip(end["logo"], sizes))
    out = p(cfg.get("work", "out"))
    os.makedirs(out, exist_ok=True)
    clips_json = p(cfg.get("clips", "clips/clips.json"))
    clips = {c["name"]: c for c in json.load(open(clips_json))}
    clip_file = lambda c: c["file"] if os.path.isabs(c["file"]) else os.path.join(os.path.dirname(clips_json), c["file"])

    # ---- beat grid: with music.sync, every cut moves LATER to the next beat/bar (never earlier,
    # so the holds a tutorial needs are kept; the last frame of the clip is held to fill)
    music = cfg.get("music")
    m = (music if isinstance(music, dict) else {"file": music}) if music else {}
    grid = None
    if m.get("sync"):
        if m["sync"] not in ("beat", "bar"):
            sys.exit('music.sync must be "beat" or "bar"')
        r = beats.analyse(p(m["file"]), m.get("bpm"))
        b = [x + m.get("offset", 0.0) for x in r["beats"]]
        grid = b[(r["barPhase"] + int(m.get("barOffset", 0))) % 4::4] if m["sync"] == "bar" else b
        json.dump(r, open(os.path.join(out, "beats.json"), "w"))
        print(f"music: {r['bpm']} BPM, {len(r['beats'])} beats, syncing cuts to the {m['sync']}")

    def snap(t):
        if not grid:
            return round(t, 3)
        nxt = [g for g in grid if g >= t - 0.12]
        if not nxt:
            print(f"warning: cut at {t:.2f} s is past the last {m['sync']} of the music; left unsynced")
            return round(t, 3)
        return round(nxt[0], 3)

    # ---- timeline (already sped up)
    intro["len"] = snap(intro["len"])
    t, scenes = intro["len"], []
    for i, s in enumerate(cfg["scenes"], 1):
        c = clips.get(s["clip"])
        if not c:
            sys.exit(f"scene {i}: no clip named {s['clip']!r} in clips.json")
        L = round(snap(t + (c["dur"] + 0.5) / speed) - t, 3)
        rect = s.get("rect") or RECTS[s.get("kind", "desk")]
        scenes.append(dict(n=i, clip=s["clip"], start=round(t, 3), end=round(t + L, 3), len=L, rect=rect,
                           title=s["title"], sub=s.get("sub", ""), cam=s.get("cam", f"CAM {i:02d}"),
                           crop=s.get("crop"), titleSize=s.get("titleSize")))
        t += L
    total = round(t + end["len"], 3)
    tl = dict(total=total, intro=intro, end=end, scenes=scenes, brand=brand, mode=cfg.get("mode", "tutorial"),
              cuts=[intro["len"]] + [s["end"] for s in scenes])
    json.dump(tl, open(os.path.join(out, "timeline.json"), "w"))
    print(f"timeline: {len(scenes)} scenes, {total:.1f} s")

    if sheet_only:
        frames = [int((intro["len"] * 0.8) * FPS)] + [int((s["start"] + min(s["len"] - 0.2, 2.2)) * FPS) for s in scenes] + [int((total - 0.5) * FPS)]
        sheet = os.path.join(out, "sheet")
        shutil.rmtree(sheet, ignore_errors=True)
        run(["node", os.path.join(HERE, "render.mjs"), os.path.join(out, "timeline.json"), sheet, str(FPS), "--frames", ",".join(map(str, frames))])
        print(f"contact sheet HUD frames in {sheet} (overlay only; run a full build to see them on footage)")
        return

    # ---- base footage
    lst = os.path.join(out, "list.txt")
    with open(lst, "w") as L_:
        def blank(name, d):
            f = os.path.join(out, f"{name}.mp4")
            run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={BG}:s=1920x1080:r={FPS}:d={d}", *ENC, f])
            L_.write(f"file '{f}'\n")
        blank("intro", intro["len"])
        for s in scenes:
            c = clips[s["clip"]]
            f = clip_file(c)
            total_src = probe_dur(f)
            start = max(0, total_src - c["dur"] - 0.3)
            raw = c["dur"] + 0.5
            x, y, w, h = s["rect"]
            if s["crop"]:
                cx, cy, cw, ch = s["crop"]
            else:  # centre crop of the recording to the rect's aspect
                sw, sh = probe_size(f)
                if sw / sh > w / h:
                    ch, cw = sh, int(sh * w / h)
                else:
                    cw, ch = sw, int(sw * h / w)
                cx, cy = (sw - cw) // 2, (sh - ch) // 2
            V = f"crop={cw}:{ch}:{cx}:{cy},scale={w}:{h}"
            o = os.path.join(out, f"scene{s['n']:02d}.mp4")
            run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{start}", "-t", f"{raw}", "-i", f,
                 "-f", "lavfi", "-i", f"color=c={BG}:s=1920x1080:r={FPS}:d={s['len']}", "-filter_complex",
                 f"[0:v]setpts=PTS/{speed},fps={FPS},tpad=stop_mode=clone:stop_duration={math.ceil(s['len']) + 1},{V},setsar=1,eq=contrast=1.06:saturation=0.92[v];[1:v][v]overlay={x}:{y}:shortest=1",
                 *ENC, "-t", f"{s['len']}", o])
            L_.write(f"file '{o}'\n")
        blank("endcard", end["len"])
    base_raw = os.path.join(out, "base_raw.mp4")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", base_raw])
    cuts = "+".join(f"between(t,{c - 0.1:.3f},{c + 0.16:.3f})" for c in [intro["len"]] + [s["end"] for s in scenes])
    base_v = os.path.join(out, "base.mp4")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", base_raw, "-vf",
         f"rgbashift=rh=-16:bh=16:gv=6:enable='{cuts}',noise=alls=55:allf=t:enable='{cuts}',noise=alls=6:allf=t", *ENC, base_v])

    # ---- HUD
    hud = os.path.join(out, "hud")
    shutil.rmtree(hud, ignore_errors=True)
    run(["node", os.path.join(HERE, "render.mjs"), os.path.join(out, "timeline.json"), hud, str(FPS)])
    video = os.path.join(out, "video.mp4")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", base_v, "-framerate", str(FPS), "-i", os.path.join(hud, "%05d.png"),
         "-filter_complex", "[0:v][1:v]overlay=0:0:shortest=1", *ENC, video])

    # ---- audio: music bed, sound effects and/or voice lines placed at times
    inputs, chains, mix = [], [], []
    if music:
        fi, fo = m.get("fadeIn", 0.3), m.get("fadeOut", 2.2)
        inputs += ["-i", p(m["file"])]
        vol = m.get("volume", 1.0)
        chains.append(f"[{len(mix)}:a]atrim=0:{total},afade=t=in:st=0:d={fi},afade=t=out:st={total - fo}:d={fo},volume={vol}[a{len(mix)}]")
        mix.append(f"[a{len(mix)}]")
    for v in sfx_events(cfg.get("sfx"), tl["cuts"], out, p) + cfg.get("voice", []):
        inputs += ["-i", p(v["file"])]
        ms = int(float(v["start"]) * 1000)
        chains.append(f"[{len(mix)}:a]adelay={ms}|{ms},volume={v.get('volume', 1.0)}[a{len(mix)}]")
        mix.append(f"[a{len(mix)}]")
    final = p(cfg.get("out", "video.mp4"))
    if mix:
        audio = os.path.join(out, "audio.wav")
        graph = ";".join(chains) + f";{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{total}[out]"
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]", "-ac", "2", "-ar", "48000", "-t", f"{total}", audio])
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", video, "-i", audio, *FINAL, "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final])
    else:
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", video, *FINAL, "-movflags", "+faststart", final])
    print(f"done: {final} ({probe_dur(final):.1f} s)")
    sheet = os.path.join(out, "contact.png")
    times = [intro["len"] * 0.8] + [s["start"] + min(s["len"] - 0.2, 2.2) for s in scenes] + [total - 0.5]
    sel = "+".join(f"eq(n\\,{int(x * FPS)})" for x in times)
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", final, "-vf", f"select='{sel}',scale=640:-1,tile={min(4, len(times))}x{-(-len(times) // 4)}", "-frames:v", "1", "-fps_mode", "passthrough", sheet])
    print(f"contact sheet: {sheet} — look at it before sharing")
    sys.exit(subprocess.run([sys.executable, os.path.join(HERE, "check.py"), cfg_path]).returncode)


def sfx_events(sfx, cuts, out, p):
    """sfx = {"cut": "auto" | "<file>", "volume": 0.6, "events": [{"at": s, "file": f, "volume": v}]}
    "auto" makes a short static burst + low thump with ffmpeg (always length-capped: an
    uncapped generator once wrote a 95 GB wav). Cut hits land on the cut, under the glitch."""
    if not sfx:
        return []
    ev = []
    hit = sfx.get("cut")
    if hit == "auto":
        hit = os.path.join(out, "sfx_cut.wav")
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=d=0.3:c=white:a=0.6",
             "-f", "lavfi", "-i", "sine=f=52:d=0.24", "-filter_complex",
             "[0]highpass=f=1400,lowpass=f=9000,acrusher=bits=6:mix=0.5,afade=t=out:st=0.04:d=0.26[n];"
             "[1]afade=t=out:st=0:d=0.24,volume=1.4[k];[n][k]amix=inputs=2:normalize=0",
             "-t", "0.3", "-ar", "48000", hit])
    if hit:
        ev += [{"file": hit, "start": max(0.0, c - 0.03), "volume": sfx.get("volume", 0.6)} for c in cuts]
    ev += [{"file": e["file"], "start": e["at"], "volume": e.get("volume", sfx.get("volume", 0.6))} for e in sfx.get("events", [])]
    return ev


if __name__ == "__main__":
    main()
