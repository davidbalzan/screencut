"""Word-by-word captions from the voice lines (social). Each line's speech is found in its file
(silencedetect trims the silence around it) and its words spread over that span by length, with
a pause after commas and full stops. Words are grouped into short pages (2 lines of big type).

    caption_pages(voice) -> [{"t0", "t1", "words": [[text, start], ...]}]   (timeline seconds)

An estimate, not forced alignment: good to a word or so, which reads fine at caption speed.
"""
import re, subprocess

MAX_CHARS, MAX_WORDS = 24, 5    # per page (two lines of big type)
HOLD = 0.5                       # a page stays this long after its last word ends


def speech_span(path):
    """(start, end) of the speech inside an audio file, in seconds."""
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", path, "-af", "silencedetect=n=-35dB:d=0.12", "-f", "null", "-"],
                       capture_output=True, text=True)
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    total = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else 0.0
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    a = ends[0] if starts and starts[0] <= 0.05 and ends else 0.0
    b = starts[-1] if starts and starts[-1] > a and (len(ends) < len(starts) or ends[-1] >= total - 0.05) else total
    return a, max(b, a + 0.2)


def words_timed(text, t0, t1):
    """[[word, start], ...] spread over [t0, t1] by length, pausing after punctuation."""
    ws = text.split()
    weight = [len(w) + 2 + (4 if w[-1] in ",;:" else 6 if w[-1] in ".!?" else 0) for w in ws]
    total, at, out = sum(weight) or 1, t0, []
    for w, k in zip(ws, weight):
        out.append([w, round(at, 3)])
        at += (t1 - t0) * k / total
    return out


def caption_pages(voice):
    """voice: resolved voice entries ({file, start, text}); returns the pages, in time order."""
    pages = []
    for v in voice:
        if not v.get("text"):
            continue
        a, b = speech_span(v["file"])
        end = v["start"] + b
        ws = words_timed(v["text"], v["start"] + a, end)
        line, cur = [], []
        for i, (w, t) in enumerate(ws):
            if cur and (len(" ".join(x[0] for x in cur) + " " + w) > MAX_CHARS or len(cur) >= MAX_WORDS):
                line.append(cur)
                cur = []
            cur.append([w, t])
            if i < len(ws) - 1 and (w[-1] in ".!?" or (w[-1] in ",;:" and len(cur) >= 2)):  # a sentence or clause ends its page
                line.append(cur)
                cur = []
        if cur:
            line.append(cur)
        # a page runs from its first word to the next page's first word (the last: HOLD past the line)
        for k, p in enumerate(line):
            t1 = line[k + 1][0][1] if k + 1 < len(line) else end + HOLD
            pages.append({"t0": round(p[0][1] - 0.05, 3), "t1": round(t1, 3), "end": round(end, 3), "words": p})
    return sorted(pages, key=lambda p: p["t0"])
