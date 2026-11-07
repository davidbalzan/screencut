---
name: heist-cam
description: Make a product tutorial or trailer video from the REAL web UI in a CCTV/heist style (REC + timestamp + cam labels, brackets locking onto the footage, titles decoding from glyphs, typed subtitles, glitch at cuts, grain, beat-synced music and sound effects, optional ElevenLabs or Google Cloud TTS voice). Scripted end to end with Playwright + an HTML HUD rendered frame by frame + ffmpeg; no video editor. Use when someone asks for a demo video, walkthrough, tutorial clip, feature trailer or "a video for <person>" of a web app or site.
---

# heist-cam — CCTV-style product videos

**Playwright records the real UI, one short clip per step → an HTML HUD, a pure function of time, is rendered frame by frame to transparent PNGs → ffmpeg stacks footage + HUD + glitch + audio.** Every word on screen is HTML, so it looks the same on every run and needs no ffmpeg text filter.

Everything here is generic: brand, texts, logo, music and voices all come from one `video.json`. Nothing depends on a particular machine, vault or repo. Read [reference/PLAYBOOK.md](reference/PLAYBOOK.md) for the look, what worked, what was rejected, and the traps.

## Step 0 — always: is it set up?
Run `python3 <this skill>/scripts/doctor.py` (add `video.json` once one exists) **before anything else**, and again whenever a script fails with "not set up yet". It lists each requirement as ✓/✗ with the exact fix command.
- **Anything ✗ under "required": guide the user through it before doing anything else.** Go one item at a time: show the `fix:` line, offer to run it (`brew install`, `npm install`), and re-run the doctor until it says Ready. Never skip ahead to recording.
  - Required: Python 3.8+ with numpy, ffmpeg with libx264, Node 20+, Google Chrome, and `npm install` in `scripts/`. `npm install` adds one dependency, `patchright`, a Playwright fork that real sites challenge less; it uses the installed Chrome.
- **Voice is optional.** Ask whether the video needs a voice at all. If it does and no provider shows ✓, help them choose and set one up:
  - **ElevenLabs** (best character voices): `ELEVENLABS_API_KEY`.
  - **Google Cloud TTS** (Chirp 3 HD voices, cheap): either `GOOGLE_API_KEY`, an API key restricted to the Text-to-Speech and Speech-to-Text APIs, or a `gcloud auth login` plus `GOOGLE_CLOUD_PROJECT`.
  - Keys go in the environment, from wherever the team keeps secrets. **The user sets them; never ask them to paste a key into the chat**, never pass one as an argument, never write one to a file.
  - If the doctor says Google would bill the gcloud default project, stop and ask which project to use: it may be a production project.
- **No `video.json` yet:** copy `examples/` into a new folder outside any product repo, then follow the Workflow. `python3 scripts/config.py video.json` checks it at any time; the build refuses unknown keys (with a "did you mean"), bad values and missing files.

## Workflow
Work in a folder of its own (not inside a product repo): `video.json`, `record.mjs`, `clips/`, `out/`, the music file, the logo SVGs.

1. **Agree the story first, in plain words:** who it's for, 3–6 steps, one title + one sentence per step, the length (tutorials ≈ 30–60 s at 1.5×). Ask for the music track and the logo; never generate a music bed (it was rejected as bad).
2. **Record** (`examples/record.example.mjs` → your `record.mjs`):
   - `rig.clip(name, run, setup)`: `setup` (load, dismiss banners, scroll) is cut off; only `run` is kept. Hold 2–3 s on every result so it can be read.
   - Real clicks, real typing (`typeSlow`), real answers: wait for the actual response, never mock it.
   - **Logged-in sites:** `node scripts/login.mjs <url> <profileDir>` opens a headed Chrome and **a person logs in** (SSO, passkey). The agent never types or holds credentials. Pass the same `profileDir` to `openRig`. Keep profiles outside any repo.
   - Use test or demo data; nothing private or customer-identifying on screen. Don't show locations or names someone asked to keep off camera.
3. **Write `video.json`** (`examples/video.example.json`): brand colours (6-digit hex), site label, intro, one entry per scene (`clip`, `kind` desk/wide/phone, optional `crop` [x,y,w,h] in recording pixels to zoom onto the part that matters, `cam`, `title` as `[[text, ""], [text, "a"]]` where `"a"` is the accent colour, `sub`), end card with logos (`end.logo`: SVG, or PNG/WebP/JPEG with a transparent background; `end.logoHeights` in px), `music`, optional `voice`.
4. **Contact sheet before the full export:** `python3 scripts/build.py video.json --sheet` renders the HUD at one frame per scene. Then run the full build and **look at `out/contact.png`** (one frame per scene on real footage). Never share a video whose frames you haven't looked at.
5. **Build:** `python3 scripts/build.py video.json` → the mp4 (H.264 high@4.1, faststart) + `out/contact.png`, then the checks (`scripts/check.py`) run on their own: a non-zero exit means a FAIL (wrong length, codec/level, no faststart, blank footage); WARNs are pacing and loudness worth a look. Thresholds follow `mode` (`tutorial` keeps 2–3 s holds; `trailer` wants ≤1.5 s holds), overridable under `checks`. Fix a FAIL before sharing; the checks never replace looking at the contact sheet and watching it.
   - **Beat sync:** `"music": {..., "sync": "beat" | "bar"}` finds the track's beat grid (`scripts/beats.py`, numpy + ffmpeg) and moves each cut *later* to the next beat or bar, holding the clip's last frame to fill. Assumes a steady tempo; override with `bpm`, `offset` (s), `barOffset` (beats) if the grid is off. Check `out/beats.json`.
   - **Sound effects:** `"sfx": {"cut": "auto" | "<file>", "volume": 0.6, "events": [{"at": 4.2, "file": "whoosh.wav"}]}`. `auto` is a short static burst + thump made with ffmpeg on every cut, under the glitch.
6. **Voice (optional, trailers):** `node scripts/voice.mjs lines.json out/vo [--provider elevenlabs|google]` generates each line, transcribes it back and regenerates until it matches and fits. The provider can also be set per line, and otherwise defaults to whichever key is set. Google voices are named like `en-US-Chirp3-HD-Charon` (the default) or `en-GB-Chirp3-HD-Algenib`, and the language comes from the name. Put the resulting `out/vo/voice.json` entries under `"voice"` in `video.json` and rebuild. The build's checks then hear each line back **from the final mix** at its slot, which catches a line buried under the music or cut off. That costs one short speech-to-text call per line, uses `checks.stt` or the key that is set, and `checks.transcribe: false` turns it off.

## Two ways to put the look in (pick per video)
- **This skill: composited HUD.** The overlay is rendered separately and laid over the footage. Smooth, repeatable, stylised (CCTV). Best for trailers and short tutorials with music.
- **Live in-page overlay** (a teammate's rig): highlights (rings, captions, chapter chips) injected into the page and recorded in-frame while Playwright drives it, then ffmpeg chapters + fades + an ElevenLabs narrator timed to the highlights. Best for narrated walkthroughs of long flows. The recording step (`rig.mjs`) works for both; only the look stage differs.

## Rules
- Real product footage only, never mockups.
- No ffmpeg `drawtext`: some builds lack it, and all text belongs in `hud.html`.
- HUD fps = footage fps (30), or the cards drift.
- The video doubles as QA: if a frame shows a UI bug, report it rather than editing around it.
