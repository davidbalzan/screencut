#!/usr/bin/env python3
"""Is this machine (and this video folder) ready? Prints each requirement with how to fix it.

    python3 doctor.py [video.json]          # exit 1 if anything REQUIRED is missing

Required: Python 3.8+ with numpy, ffmpeg/ffprobe (with libx264 and the filters the build uses),
Node 20+, Google Chrome, and `npm install` run in this scripts/ folder. Optional: a voice provider
(ElevenLabs or Google Cloud TTS). With a video.json it also validates it and checks the clips/music.
"""
import json, os, platform, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = platform.system() == "Darwin"
NEEDED_FILTERS = ["rgbashift", "noise", "ebur128", "freezedetect", "blackdetect", "silencedetect", "acrusher", "anoisesrc", "amix", "adelay"]


def out(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def chrome_path():
    cands = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")] if MAC else []
    cands += [shutil.which(n) for n in ("google-chrome", "google-chrome-stable", "chrome")]
    return next((c for c in cands if c and os.path.exists(c)), None)


def required():
    """[(ok, name, detail, fix)] for what the build cannot run without."""
    res = []
    py_ok = sys.version_info >= (3, 8)
    try:
        import numpy  # noqa: F401
        np_ok = True
    except ImportError:
        np_ok = False
    res.append((py_ok and np_ok, "python + numpy", f"python {platform.python_version()}, numpy {'ok' if np_ok else 'missing'}",
                "python3 -m pip install --user numpy" if py_ok else "install Python 3.8+ (brew install python)"))

    ff = shutil.which("ffmpeg") and shutil.which("ffprobe")
    fix_ff = "brew install ffmpeg" if MAC else "sudo apt install ffmpeg  (or your distro's package)"
    if not ff:
        res.append((False, "ffmpeg", "ffmpeg/ffprobe not on PATH", fix_ff))
    else:
        ver = (out(["ffmpeg", "-version"]).splitlines() or ["?"])[0]
        filters, encs = out(["ffmpeg", "-hide_banner", "-filters"]), out(["ffmpeg", "-hide_banner", "-encoders"])
        miss = [f for f in NEEDED_FILTERS if not re.search(rf"\s{f}\s", filters)] + ([] if "libx264" in encs else ["libx264"])
        res.append((not miss, "ffmpeg", ver[:60] + (f"; missing: {', '.join(miss)}" if miss else ""),
                    f"{fix_ff}  (a full build: the minimal/static builds can lack libx264 or filters)"))

    nv = out(["node", "--version"]).strip()
    major = int(nv.lstrip("v").split(".")[0]) if nv else 0
    res.append((major >= 20, "node 20+", nv or "node not on PATH", "brew install node  (or nvm install 22)" if MAC else "nvm install 22"))

    c = chrome_path()
    res.append((bool(c), "google chrome", c or "not found (recording and the HUD render use the installed Chrome)",
                "install Google Chrome from google.com/chrome" + ("  (or: brew install --cask google-chrome)" if MAC else "")))

    pr = os.path.isdir(os.path.join(HERE, "node_modules", "patchright"))
    res.append((pr, "npm install", "patchright installed" if pr else "scripts/node_modules missing", f"cd {HERE} && npm install"))
    return res


def optional():
    res = []
    el = bool(os.environ.get("ELEVENLABS_API_KEY"))
    res.append((el, "voice: elevenlabs", "ELEVENLABS_API_KEY set" if el else "ELEVENLABS_API_KEY not set",
                "export ELEVENLABS_API_KEY=… from your team's secret store (shell profile or a secrets manager; never a repo file)"))
    gk = bool(os.environ.get("GOOGLE_API_KEY"))
    gacct = out(["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"]).strip() if shutil.which("gcloud") else ""
    gproj = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if gk:
        res.append((True, "voice: google", "GOOGLE_API_KEY set", ""))
    elif gacct:
        default = out(["gcloud", "config", "get-value", "project"]).strip()
        res.append((bool(gproj), "voice: google", f"gcloud login {gacct}; " + (f"billing project {gproj}" if gproj else f"GOOGLE_CLOUD_PROJECT unset → bills gcloud default project {default or '?'}"),
                    "export GOOGLE_CLOUD_PROJECT=<a non-production project with Text-to-Speech + Speech-to-Text enabled>"))
    else:
        res.append((False, "voice: google", "no GOOGLE_API_KEY and no gcloud login",
                    "Cloud console → APIs: enable Text-to-Speech + Speech-to-Text → Credentials → API key restricted to those two → export GOOGLE_API_KEY=…  (or: gcloud auth login + export GOOGLE_CLOUD_PROJECT=…)"))
    return res


def project(cfg_path):
    sys.path.insert(0, HERE)
    import config
    base = os.path.dirname(os.path.abspath(cfg_path))
    p = lambda x: x if os.path.isabs(x) else os.path.join(base, x)
    try:
        cfg = json.load(open(cfg_path))
    except (OSError, json.JSONDecodeError) as e:
        return [(False, "video.json", str(e), f"cp {HERE}/../examples/video.example.json {cfg_path}  then edit it")]
    errs = config.validate(cfg, p)
    res = [(not errs, "video.json", "valid" if not errs else f"{len(errs)} problem(s):\n        " + "\n        ".join(errs), "fix the keys above (python3 config.py video.json re-checks)")]
    if cfg.get("voice") and not any(ok for ok, *_ in optional()):
        res.append((False, "voice provider", "video.json has voice lines but no provider is configured", "see the voice lines above"))
    return res


def main():
    rows = [("required", required()), ("optional", optional())]
    if len(sys.argv) > 1:
        rows.append(("this video", project(sys.argv[1])))
    bad_required = False
    for section, items in rows:
        print(f"{section}:")
        for ok, name, detail, fix in items:
            mark = "✓" if ok else ("–" if section == "optional" else "✗")
            print(f"  {mark} {name:<18} {detail}")
            if not ok and fix:
                print(f"      fix: {fix}")
            bad_required |= (not ok and section != "optional")
    if bad_required:
        print("\nNot ready: fix the ✗ lines above, then run doctor.py again.")
    else:
        print("\nReady." + ("" if len(sys.argv) > 1 else f" Start a video: mkdir my-video && cp {os.path.normpath(HERE + '/../examples')}/* my-video/"))
    sys.exit(1 if bad_required else 0)


if __name__ == "__main__":
    main()
