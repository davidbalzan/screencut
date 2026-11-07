"""Validate a video.json before anything is built: unknown keys (typos), wrong types, bad
values and missing files are all reported at once, so a misspelt "sycn" can't silently do nothing.

    python3 config.py <video.json>      # prints the problems; exit 1 if any
"""
import difflib, json, os, re, sys

STYLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "styles")


def styles():
    """Every style is a folder styles/<name>/ holding hud.html and style.json."""
    return sorted(d for d in os.listdir(STYLES_DIR) if os.path.exists(os.path.join(STYLES_DIR, d, "style.json")))


def load_style(name):
    return {"name": name, **json.load(open(os.path.join(STYLES_DIR, name, "style.json")))}

NUM, INT, STR, BOOL, HEX, FILE, TITLE = "number", "integer", "string", "boolean", "hex", "file", "title"


def enum(*vals):
    return ("enum", vals)


def arr(item, n=None):
    return ("list", item, n)


def obj(fields, required=()):
    return ("obj", fields, set(required))


TITLE_SPEC = TITLE  # "TEXT" or [["TEXT ", ""], ["ACCENT", "a"]]
SCENE = obj({"clip": STR, "kind": enum("desk", "wide", "phone", "full", "type"), "rect": arr(NUM, 4), "crop": arr(NUM, 4), "cam": STR,
             "title": TITLE_SPEC, "sub": STR, "titleSize": NUM, "speed": NUM, "fastForward": BOOL,
             "ramps": arr(obj({"from": NUM, "to": NUM, "speed": NUM}, ["from", "to", "speed"])),
             "fit": enum("full", "content"), "layout": STR,
             "focus": arr(NUM, 4), "zoom": NUM, "callout": STR, "chapter": STR}, ["clip", "title"])
# A type scene: no footage, type only (manifesto and vision beats). Length from `len` seconds or
# `beats` on the beat grid, else from what it shows; a voice line anchored to it stretches it.
NO_CLIP = ("refuse", 'a type scene has no footage: drop "clip", or drop "kind": "type" to show the clip')
TYPE_SCENE = obj({"kind": enum("type"), "clip": NO_CLIP, "title": TITLE_SPEC, "sub": STR, "len": NUM, "beats": INT,
                  "lines": arr(STR), "strike": BOOL, "then": TITLE_SPEC, "chips": arr(STR), "chapter": STR}, ["kind"])
SPEC = obj({
    "out": STR, "clips": FILE, "work": STR, "speed": NUM, "mode": enum("tutorial", "trailer"), "style": ("style",), "fastForward": BOOL,
    "fit": enum("full", "content"), "layout": STR, "zoom": NUM,
    "exports": obj({"slides": enum(True, False, "all"), "aspect": enum("16:9", "4:3")}),  # "all": type scenes too
    "brand": obj({"accent": HEX, "alert": HEX, "glow": HEX, "site": STR, "date": STR, "clock": STR,
                  "ground": HEX, "palette": arr(HEX)}),
    "intro": obj({"len": NUM, "alert": STR, "title": TITLE_SPEC, "sub": STR, "size": NUM}),
    "scenes": arr(("scene",)),
    "end": obj({"len": NUM, "logo": arr(FILE), "logoHeights": arr(NUM), "line": STR, "url": STR, "blink": BOOL}),
    "music": ("music",),
    "sfx": obj({"cut": ("cut",), "volume": NUM,
                "events": arr(obj({"at": NUM, "file": FILE, "volume": NUM}, ["at", "file"]))}),
    "voice": arr(obj({"file": FILE, "start": NUM, "scene": ("anchor",), "volume": NUM, "text": STR, "languageCode": STR}, ["file", "start"])),
    "checks": obj({"maxHold": NUM, "maxStill": NUM, "minEndHold": NUM, "transcribe": BOOL, "minVoiceMatch": NUM,
                   "stt": enum("elevenlabs", "google")}),
}, ["scenes"])
MUSIC = obj({"file": FILE, "sync": enum(True, "beat", "bar"), "bpm": NUM, "offset": NUM, "barOffset": INT,
             "fadeIn": NUM, "fadeOut": NUM, "volume": NUM}, ["file"])


def validate(cfg, p):
    """p resolves a path relative to the video.json. Returns a list of problems."""
    errs = []

    def check(v, spec, at):
        kind = spec if isinstance(spec, str) else spec[0]
        isnum = isinstance(v, (int, float)) and not isinstance(v, bool)
        if kind == NUM and not isnum:
            errs.append(f"{at}: expected a number, got {v!r}")
        elif kind == INT and not (isnum and float(v).is_integer()):
            errs.append(f"{at}: expected a whole number, got {v!r}")
        elif kind in (STR, FILE) and not isinstance(v, str):
            errs.append(f"{at}: expected a string, got {v!r}")
        elif kind == BOOL and not isinstance(v, bool):
            errs.append(f"{at}: expected true/false, got {v!r}")
        elif kind == HEX and not (isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v)):
            errs.append(f"{at}: expected a 6-digit hex colour like #4ade80, got {v!r}")
        elif kind == FILE and not os.path.exists(p(v)):
            errs.append(f"{at}: file not found: {p(v)}")
        elif kind == TITLE:
            ok = isinstance(v, str) or (isinstance(v, list) and all(
                isinstance(x, list) and len(x) == 2 and isinstance(x[0], str) and x[1] in ("", "a") for x in v))
            if not ok:
                errs.append(f'{at}: expected "TEXT" or [["TEXT ", ""], ["ACCENT", "a"]], got {json.dumps(v)}')
        elif kind == "enum" and v not in spec[1]:
            errs.append(f"{at}: must be one of {', '.join(map(repr, spec[1]))}, got {v!r}")
        elif kind == "list":
            if not isinstance(v, list):
                errs.append(f"{at}: expected a list, got {v!r}")
            elif spec[2] and len(v) != spec[2]:
                errs.append(f"{at}: expected {spec[2]} values, got {len(v)}")
            else:
                for i, x in enumerate(v):
                    check(x, spec[1], f"{at}[{i}]")
        elif kind == "obj":
            if not isinstance(v, dict):
                errs.append(f"{at}: expected an object, got {v!r}")
                return
            fields, req = spec[1], spec[2]
            for k in v:
                if k not in fields:
                    near = difflib.get_close_matches(k, fields, 1)
                    errs.append(f"{at}.{k}: unknown key" + (f" (did you mean {near[0]!r}?)" if near else f"; allowed: {', '.join(fields)}"))
                else:
                    check(v[k], fields[k], f"{at}.{k}")
            for k in sorted(req - v.keys()):
                errs.append(f"{at}.{k}: required")
        elif kind == "scene":  # a footage scene, or a type scene ("kind": "type")
            if isinstance(v, dict) and v.get("kind") == "type":
                return check(v, TYPE_SCENE, at)
            only_type = [k for k in v if k in TYPE_SCENE[1] and k not in SCENE[1]] if isinstance(v, dict) else []
            for k in only_type:
                errs.append(f'{at}.{k}: only type scenes have {k} (add "kind": "type" and drop "clip")')
            check({k: x for k, x in v.items() if k not in only_type} if only_type else v, SCENE, at)
        elif kind == "refuse":
            errs.append(f"{at}: {spec[1]}")
        elif kind == "music":
            check({"file": v} if isinstance(v, str) else v, MUSIC, at)
        elif kind == "cut":
            if v != "auto":
                check(v, FILE, at)
        elif kind == "style":
            if v not in styles():
                near = difflib.get_close_matches(str(v), styles(), 1)
                errs.append(f"{at}: unknown style {v!r}" + (f" (did you mean {near[0]!r}?)" if near else "") + f"; styles: {', '.join(styles())}")
        elif kind == "anchor":  # voice start relative to a scene's cut: 0 = intro, 1..n = scene, "end" = end card
            n = len(cfg.get("scenes", [])) if isinstance(cfg.get("scenes"), list) else 0
            if not (v == "end" or (isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= n)):
                errs.append(f'{at}: expected 0 (intro), 1..{n} (a scene) or "end", got {v!r}')

    check(cfg, SPEC, "video")
    if isinstance(cfg.get("scenes"), list) and not cfg["scenes"]:
        errs.append("video.scenes: needs at least one scene")
    for at, z in [("video.zoom", cfg.get("zoom"))] + [(f"video.scenes[{i}].zoom", s.get("zoom")) for i, s in enumerate(cfg.get("scenes") or []) if isinstance(s, dict)]:
        if isinstance(z, (int, float)) and not 1 <= z <= 4:
            errs.append(f"{at}: the closest zoom, 1 (no zoom) to 4, got {z}")
    if isinstance(cfg.get("speed"), (int, float)) and cfg["speed"] <= 0:
        errs.append("video.speed: must be above 0")
    for i, s in enumerate(cfg.get("scenes") if isinstance(cfg.get("scenes"), list) else []):
        if not isinstance(s, dict):
            continue
        if isinstance(s.get("speed"), (int, float)) and s["speed"] <= 0:
            errs.append(f"video.scenes[{i}].speed: must be above 0")
        if s.get("kind") == "type":
            if not any(s.get(k) for k in ("title", "lines", "chips", "then")):
                errs.append(f"video.scenes[{i}]: a type scene shows something: give it a title, lines, chips or then")
            if "len" in s and "beats" in s:
                errs.append(f"video.scenes[{i}]: len (seconds) or beats (on the beat grid), not both")
            if isinstance(s.get("len"), (int, float)) and s["len"] <= 0:
                errs.append(f"video.scenes[{i}].len: must be above 0")
            if isinstance(s.get("beats"), int) and s["beats"] < 1:
                errs.append(f"video.scenes[{i}].beats: at least 1")
            for k in ("strike", "then"):
                if s.get(k) and not s.get("lines"):
                    errs.append(f"video.scenes[{i}].{k}: works on lines; add \"lines\": [...]")
        for j, r in enumerate(s.get("ramps") if isinstance(s.get("ramps"), list) else []):
            if isinstance(r, dict) and all(isinstance(r.get(k), (int, float)) for k in ("from", "to", "speed")):
                if not (0 <= r["from"] < r["to"]) or r["speed"] <= 0:
                    errs.append(f"video.scenes[{i}].ramps[{j}]: needs 0 <= from < to (seconds into the clip's action) and speed > 0")
    clock = cfg.get("brand", {}).get("clock") if isinstance(cfg.get("brand"), dict) else None
    if isinstance(clock, str) and not re.fullmatch(r"\d\d:\d\d:\d\d", clock):
        errs.append(f"video.brand.clock: expected HH:MM:SS, got {clock!r}")
    if cfg.get("style", "heist") in styles() and isinstance(cfg.get("scenes"), list):
        st = load_style(cfg.get("style", "heist"))
        for i, s in enumerate(cfg["scenes"]):  # hud styles (kinetic, keynote, social) place footage by layout, not kind
            k = s.get("kind") if isinstance(s, dict) else None
            if k in SCENE[1]["kind"][1] and k != "type" and st["footage"] == "canvas" and k not in st["rects"]:
                errs.append(f"video.scenes[{i}].kind: style {st['name']!r} has no {k!r}; kinds: {', '.join(st['rects'])}")
        lays = st.get("layouts", {})
        for at, v in [("video.layout", cfg.get("layout"))] + [(f"video.scenes[{i}].layout", s.get("layout")) for i, s in enumerate(cfg["scenes"]) if isinstance(s, dict)]:
            if isinstance(v, str) and v not in lays:
                errs.append(f"{at}: style {st['name']!r} has " + (f"no layout {v!r}; layouts: {', '.join(lays)}" if lays else "no layouts"))
        for i, s in enumerate(cfg["scenes"]):
            if isinstance(s, dict) and (s.get("focus") or s.get("callout")) and not st.get("camera"):
                errs.append(f"video.scenes[{i}]: focus and callout need a style with a camera (keynote, social); {st['name']!r} has none")
        exp = cfg.get("exports") if isinstance(cfg.get("exports"), dict) else {}
        if exp.get("slides") and st["footage"] != "hud":
            errs.append(f"video.exports.slides: style {st['name']!r} can't export slides (keynote can)")
    clips_path = p(cfg.get("clips", "clips/clips.json")) if isinstance(cfg.get("clips", ""), str) else None
    if clips_path and os.path.exists(clips_path) and isinstance(cfg.get("scenes"), list):
        names = {c.get("name") for c in json.load(open(clips_path))}
        for i, s in enumerate(cfg["scenes"]):
            if isinstance(s, dict) and s.get("kind") != "type" and isinstance(s.get("clip"), str) and s["clip"] not in names:
                near = difflib.get_close_matches(s["clip"], [n for n in names if n], 1)
                errs.append(f"video.scenes[{i}].clip: no clip {s['clip']!r} in {clips_path}" + (f" (did you mean {near[0]!r}?)" if near else ""))
    elif clips_path and not os.path.exists(clips_path):
        errs.append(f"video.clips: {clips_path} not found (record first: it is written by rig.done())")
    return errs


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = os.path.abspath(sys.argv[1])
    base = os.path.dirname(path)
    errs = validate(json.load(open(path)), lambda x: x if os.path.isabs(x) else os.path.join(base, x))
    print("\n".join(errs) or "video.json ok")
    sys.exit(1 if errs else 0)
