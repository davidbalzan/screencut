#!/usr/bin/env python3
"""Measure a built video against its timeline; build.py runs this after every export.

    python3 check.py <video.json>       # prints PASS/WARN/FAIL per check, writes <work>/check.json; exit 1 on any FAIL

FAIL = the file itself is wrong (length, codec, faststart, blank footage).
WARN = pacing or loudness worth a look. Thresholds follow `mode` (tutorial | trailer) and can be
overridden in video.json under "checks". Holds are measured on the footage before grain and HUD
(out/base_raw.mp4), since the HUD's running clock means the final frames never sit still.
This does not replace looking at out/contact.png and watching the video.
"""
import json, os, re, subprocess, sys

DEFAULTS = {
    # maxHold: longest frozen stretch inside a scene; maxStill: share of a scene that is frozen;
    # minEndHold: frozen time at the end of each scene, so the result can be read.
    "tutorial": {"maxHold": 6.0, "maxStill": 0.85, "minEndHold": 1.0},
    "trailer": {"maxHold": 1.5, "maxStill": 0.6, "minEndHold": 0.0},
}
STILL_NOISE = 0.003  # freezedetect noise: below this a frame counts as unchanged (build.py's fast-forward uses it too)
LUFS = (-18.0, -10.0)
TRUE_PEAK = -1.0


def ff(args):
    return subprocess.run(args, capture_output=True, text=True)


def moov_before_mdat(path):
    with open(path, "rb") as f:
        pos, size = 0, os.path.getsize(path)
        while pos < size:
            f.seek(pos)
            hdr = f.read(16)
            if len(hdr) < 8:
                return False
            n, kind = int.from_bytes(hdr[:4], "big"), hdr[4:8]
            if n == 1:
                n = int.from_bytes(hdr[8:16], "big")
            if kind == b"moov":
                return True
            if kind == b"mdat" or n < 8:
                return False
            pos += n
    return False


def intervals(stderr, start_key, end_key):
    out, cur = [], None
    for line in stderr.splitlines():
        if m := re.search(start_key + r":\s*([\d.]+)", line):
            cur = float(m.group(1))
        elif (m := re.search(end_key + r":\s*([\d.]+)", line)) and cur is not None:
            out.append((cur, float(m.group(1))))
            cur = None
    return out, cur


def norm_words(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w ]", " ", s.lower())).strip().split()


def similar(a, b):  # same measure as speech.mjs
    A, Bw = set(norm_words(a)), norm_words(b)
    return sum(w in A for w in Bw) / max(len(A), len(Bw), 1)


def voice_checks(cfg, tl, th, final, work, p, add):
    """Hear each voice line back from the FINAL mix (music, sfx and all) at its slot: catches a line
    buried under the music or cut off by the next one. One short paid STT call per line."""
    lines = [v for v in tl.get("voice", cfg.get("voice", [])) if v.get("text")]  # starts resolved by build.py
    if not lines or th.get("transcribe") is False:
        return
    provider = th.get("stt") or ("elevenlabs" if os.environ.get("ELEVENLABS_API_KEY") else "google" if os.environ.get("GOOGLE_API_KEY") else None)
    if not provider:
        add("WARN", "voice", "not checked: set ELEVENLABS_API_KEY or GOOGLE_API_KEY, or checks.stt = \"google\" to use the gcloud login (run doctor.py)")
        return
    speech = os.path.join(os.path.dirname(os.path.abspath(__file__)), "speech.mjs")
    for i, v in enumerate(lines, 1):
        d = float(ff(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p(v["file"])]).stdout.strip())
        s = max(0.0, float(v["start"]) - 0.2)
        seg = os.path.join(work, f"voicecheck{i:02d}.wav")
        ff(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{s}", "-t", f"{d + 0.6}", "-i", final, "-vn", "-ac", "1", "-ar", "16000", seg])
        r = ff(["node", speech, "stt", seg, provider, v.get("languageCode", "en-US")])
        if r.returncode:
            add("WARN", f"voice {i}", f"transcription failed ({provider}): {r.stderr.strip()[-200:]}")
            continue
        score = similar(v["text"], r.stdout)
        ok = score >= th.get("minVoiceMatch", 0.8)
        add("PASS" if ok else "WARN", f"voice {i}", f"{score:.0%} match at {v['start']} s — heard \"{r.stdout.strip()}\"" + ("" if ok else " (buried under the music or clipped? lower music volume or move the line)"))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cfg_path = os.path.abspath(sys.argv[1])
    base = os.path.dirname(cfg_path)
    p = lambda x: x if os.path.isabs(x) else os.path.join(base, x)
    cfg = json.load(open(cfg_path))
    work = p(cfg.get("work", "out"))
    tl = json.load(open(os.path.join(work, "timeline.json")))
    final = p(cfg.get("out", "video.mp4"))
    mode = cfg.get("mode", "tutorial")
    th = {**DEFAULTS.get(mode, DEFAULTS["tutorial"]), **cfg.get("checks", {})}
    res = []
    add = lambda status, name, detail: res.append({"status": status, "check": name, "detail": detail})

    # ---- the file
    info = json.loads(ff(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", final]).stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    add("PASS" if abs(dur - tl["total"]) <= 0.15 else "FAIL", "length", f"{dur:.2f} s (timeline {tl['total']:.2f} s)")
    # level 4.2 at most up to 1080p in either orientation (1080x1920@30 fits 4.1: 8160 macroblocks a frame)
    ok = v["codec_name"] == "h264" and v.get("pix_fmt") == "yuv420p" and v.get("profile") in ("High", "Main", "Constrained Baseline") and int(v.get("level", 99)) <= (51 if v["width"] * v["height"] > 1920 * 1088 else 42)
    add("PASS" if ok else "FAIL", "phone playback", f"{v['codec_name']} {v.get('profile')} L{v.get('level')} {v.get('pix_fmt')} {v['width']}x{v['height']}")
    add("PASS" if moov_before_mdat(final) else "FAIL", "faststart", "moov before mdat" if moov_before_mdat(final) else "moov after mdat: web players must download the whole file first")
    mb, rate = os.path.getsize(final) / 1e6, float(info["format"].get("bit_rate", 0)) / 1e6
    add("PASS" if rate <= 12 else "WARN", "size", f"{mb:.1f} MB, {rate:.1f} Mbit/s")

    # ---- footage: blank or frozen stretches per scene
    raw = os.path.join(work, "base_raw.mp4")
    r = ff(["ffmpeg", "-nostdin", "-hide_banner", "-i", raw, "-vf", f"freezedetect=n={STILL_NOISE}:d=0.4,blackdetect=d=0.3:pic_th=0.985", "-an", "-f", "null", "-"])
    freezes, open_start = intervals(r.stderr, "freeze_start", "freeze_end")
    if open_start is not None:
        freezes.append((open_start, tl["total"]))
    blacks = [(float(s), float(e)) for s, e in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)]
    ov = lambda iv, s, e: sum(max(0.0, min(b, e) - max(a_, s)) for a_, b in iv)
    for s in tl["scenes"]:
        # from where the footage starts: a style's lead-in (kinetic title slam) holds the first frame on purpose
        S, E = s.get("fstart", s["start"]), s["end"]
        L = E - S
        name = f"scene {s['n']:02d} ({s['clip']})"
        if ov(blacks, S, E) > 0.5 * L:
            add("FAIL", name, f"footage blank for {ov(blacks, S, E):.1f} of {L:.1f} s: the recording is empty or the crop misses it")
            continue
        holds = [min(b, E) - max(a_, S) for a_, b in freezes if b > S and a_ < E]
        longest, still = max(holds, default=0.0), ov(freezes, S, E) / L
        end_hold = next((E - max(a_, S) for a_, b in freezes if b >= E - 0.1 and a_ < E), 0.0)
        issues = []
        if longest > th["maxHold"]:
            issues.append(f"holds {longest:.1f} s (max {th['maxHold']})")
        if still > th["maxStill"]:
            issues.append(f"{still:.0%} still (max {th['maxStill']:.0%})")
        if end_hold < th["minEndHold"]:
            issues.append(f"result held {end_hold:.1f} s at the end (min {th['minEndHold']}): may be unreadable")
        add("WARN" if issues else "PASS", name, "; ".join(issues) or f"{L:.1f} s, longest hold {longest:.1f} s, {still:.0%} still, end hold {end_hold:.1f} s")
    body = tl["total"] - tl["intro"]["len"] - tl["end"]["len"]
    add("PASS", "pace", f"{len(tl['scenes'])} scenes, {10 * (len(tl['scenes']) - 1) / max(body, 0.1):.1f} cuts per 10 s of footage, mode {mode}")

    # ---- audio
    if a:
        r = ff(["ffmpeg", "-nostdin", "-hide_banner", "-i", final, "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"])
        summ = r.stderr[r.stderr.rfind("Summary:"):]
        I = float(re.search(r"I:\s*(-?[\d.]+|-inf) LUFS", summ).group(1).replace("-inf", "-99"))
        tp = float(re.search(r"Peak:\s*(-?[\d.]+|-inf) dBFS", summ).group(1).replace("-inf", "-99"))
        add("PASS" if LUFS[0] <= I <= LUFS[1] else "WARN", "loudness", f"{I:.1f} LUFS integrated (aim {LUFS[0]:.0f}..{LUFS[1]:.0f}; web/social ≈ -14)")
        add("PASS" if tp <= TRUE_PEAK else "WARN", "true peak", f"{tp:.1f} dBTP (max {TRUE_PEAK}): {'ok' if tp <= TRUE_PEAK else 'may clip after re-encoding; lower music/sfx volume'}")
    else:
        add("WARN", "audio", "no audio stream")
    voice_checks(cfg, tl, th, final, work, p, add)

    w = max(len(x["check"]) for x in res)
    for x in res:
        print(f"  {x['status']:<4}  {x['check']:<{w}}  {x['detail']}")
    json.dump(res, open(os.path.join(work, "check.json"), "w"), indent=1)
    fails = sum(x["status"] == "FAIL" for x in res)
    warns = sum(x["status"] == "WARN" for x in res)
    print(f"checks: {fails} fail, {warns} warn — {os.path.join(work, 'check.json')}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
