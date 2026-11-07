# heist-cam

**Product tutorials and trailers cut from your real web UI, in a CCTV / heist style. Fully scripted, with no video editor.**

heist-cam is a [Claude Code](https://claude.com/claude-code) skill. Ask Claude for "a demo video of the new dashboard" and it:
1. agrees the story with you;
2. drives your actual app in Chrome and records one short clip per step;
3. lays a surveillance HUD over the footage: a blinking REC light, a running timestamp, `CAM 01 // PLACE` labels, brackets that lock onto the footage, titles that decode from random glyphs, typed subtitles, a glitch at every cut, grain and scanlines;
4. cuts on the beat of your music, adds a sound hit on each cut, and adds an optional voice-over;
5. measures the result before you share it.

![Contact sheet: intro, three scenes, end card](docs/contact-sheet.png)
<sub>The contact sheet from a build of the test fixture (test patterns in place of a real UI). Every build writes one to `out/contact.png`.</sub>

## How it works

```
 record.mjs (Playwright)        video.json                    music / voice
 real clicks, real typing  ─┐   brand, scenes, titles,  ─┐    beat grid, sfx, TTS
 one clip per step          │   crops, end card          │          │
                            ▼                            ▼          ▼
                     ┌──────────────── build.py ─────────────────────────┐
                     │ trim each clip to its action · speed up · crop     │
                     │ snap cuts to the beat · glitch + grain at cuts     │
                     │ hud.html rendered frame by frame (pure fn of t)    │
                     │ overlay · mix audio · H.264 high@4.1, faststart    │
                     └───────────────────────┬───────────────────────────┘
                                             ▼
                          check.py → PASS / WARN / FAIL + contact sheet
```

- **All on-screen text is HTML.** `hud.html` defines `window.render(t)` as a pure function of time. A headless Chrome screenshots it frame by frame as transparent PNGs, and ffmpeg lays them over the footage. Every run comes out the same, and no ffmpeg text filter is needed (some ffmpeg builds don't have `drawtext`).
- **Real footage only.** It never uses mockups. The recording waits for real responses. The video doubles as QA: if a frame shows a UI bug, report the bug rather than editing around it.
- **Everything specific to a video lives in one `video.json`:** brand, texts, logos, music and voices. Nothing is tied to a particular machine or repo.

## Install

```bash
git clone git@github.com:davidbalzan/heist-cam.git ~/.claude/skills/heist-cam
cd ~/.claude/skills/heist-cam/scripts && npm install
python3 ~/.claude/skills/heist-cam/scripts/doctor.py
```

`doctor.py` checks everything the skill needs and prints the exact fix for anything missing:

| Required | Why |
|---|---|
| Python 3.8+ with numpy | the build, beat detection and checks |
| ffmpeg + ffprobe with libx264 | assembly; the doctor also checks for the filters the build uses |
| Node 20+ | recording and the HUD render |
| Google Chrome | recording uses the installed Chrome through [patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright), a Playwright fork that real sites challenge less |
| `npm install` in `scripts/` | installs patchright |

Voice is optional. See [Voice](#voice).

## Use it

In Claude Code, run `/heist-cam` or just ask for a demo video, walkthrough or trailer. Claude runs the doctor, helps you fix anything missing, then works through the steps below. To do it by hand:

```bash
mkdir my-video && cp ~/.claude/skills/heist-cam/examples/* my-video/ && cd my-video
# 1. edit record.mjs (your steps), then record the real UI
node record.mjs                                   # → clips/<name>/*.webm + clips/clips.json
#    logged-in site? a PERSON logs in first; the agent never handles credentials:
node ~/.claude/skills/heist-cam/scripts/login.mjs https://app.example.com ~/.cache/heist-cam/profile
# 2. edit video.json, validate it
python3 ~/.claude/skills/heist-cam/scripts/config.py video.json
# 3. HUD-only contact sheet, then the full build (checks run at the end)
python3 ~/.claude/skills/heist-cam/scripts/build.py video.json --sheet
python3 ~/.claude/skills/heist-cam/scripts/build.py video.json
```

Look at `out/contact.png` and watch the video before sharing it. The checks don't replace looking.

## `video.json`

See [`examples/video.example.json`](examples/video.example.json). The build rejects unknown keys (with a "did you mean"), wrong types and missing files before it does any work.

| Key | What |
|---|---|
| `mode` | `tutorial` (default; keeps 2–3 s holds so results can be read) or `trailer` (fast, ≤1.5 s holds) |
| `speed` | playback speed of the footage (default 1.5) |
| `brand` | `accent` / `alert` / `glow` (6-digit hex), `site` label, `date`, starting `clock` |
| `intro` | `len`, `alert` line, `title`, `sub` |
| `scenes[]` | `clip`, `kind` (`desk` / `wide` / `phone`), optional `crop` `[x,y,w,h]` to zoom, `cam`, `title` as `[["TEXT ", ""], ["ACCENT", "a"]]`, `sub` |
| `end` | `logo[]` (SVG, or PNG/WebP/JPEG with a transparent background), `logoHeights`, `line`, `url` |
| `music` | `file`, `sync` (`beat` / `bar`), `bpm` / `offset` / `barOffset` overrides, `fadeIn`, `fadeOut`, `volume` |
| `sfx` | `cut` (`"auto"` or a file) plays on every cut, plus `events[]` `{at, file}` |
| `voice[]` | `{file, start, text}`, as written by `voice.mjs` |
| `checks` | override `maxHold`, `maxStill`, `minEndHold`, `minVoiceMatch`; `stt` provider; `transcribe: false` |

### Beat sync
With `"sync": "beat"` (or `"bar"`), `beats.py` finds the track's beat grid using only numpy and ffmpeg. Each cut then moves **later** to the next beat or bar, never earlier, so a tutorial keeps its holds; the clip's last frame is held to fill the gap. It assumes a steady tempo, which is fine for the usual music beds. The grid is written to `out/beats.json`. On a test loop it put cuts within 12 ms of the true beat.

## Checks

`check.py` runs after every build and writes `out/check.json`. Any FAIL makes the build exit non-zero.

| Check | FAIL / WARN when |
|---|---|
| length | the file doesn't match the timeline |
| phone playback | not H.264 yuv420p, or above level 4.1/4.2 (older phones and TVs refuse it) |
| faststart | the `moov` box comes after `mdat`, so web players must download the whole file first |
| blank footage | a scene's recording is empty, or the crop misses it |
| holds | a frozen stretch is too long, too much of a scene is still, or the result isn't held long enough to read (limits depend on the mode) |
| loudness | outside -18..-10 LUFS integrated; true peak above -1 dBTP |
| voice | each line, heard back **from the final mix** at its slot, matches less than 80% of its text (buried under the music or cut off) |

## Voice

`node scripts/voice.mjs lines.json out/vo [--provider elevenlabs|google]` generates each line, transcribes it back and regenerates it (up to 3 tries) until it matches and fits its slot.

| Provider | Auth (environment only) | Voices |
|---|---|---|
| ElevenLabs | `ELEVENLABS_API_KEY` | voice IDs; the playbook lists the ones that worked |
| Google Cloud TTS | `GOOGLE_API_KEY` (restrict it to Text-to-Speech + Speech-to-Text), **or** `gcloud auth login` + `GOOGLE_CLOUD_PROJECT` | e.g. `en-US-Chirp3-HD-Charon` (default), `en-GB-Chirp3-HD-Algenib` |

Keys go in the environment, never in an argument or a file. If you use the gcloud login, set `GOOGLE_CLOUD_PROJECT`. Otherwise Google bills your gcloud default project, which may be a production one. The doctor warns about this.

## Layout

```
SKILL.md               what Claude reads: setup step, workflow, rules
reference/PLAYBOOK.md  the look, what worked and what was rejected, voices, traps
examples/              record.example.mjs, video.example.json
scripts/
  doctor.py            setup check with fixes
  rig.mjs, login.mjs   recording helpers; a person logs in
  config.py            video.json validation
  beats.py             beat grid (numpy + ffmpeg)
  build.py             the assembly
  hud.html, render.mjs the HUD and its frame renderer
  check.py             post-build checks
  speech.mjs, voice.mjs  TTS/STT providers and voice-over generation
```

## Credits

The beat-grid cutting and the automated render checks are inspired by Scenario's [Kinetic Film](https://www.scenario.com/explorations/kinetic-film/). Validating the config strictly comes from [OpenKatana](https://github.com/rk0neki/OpenKatana).
