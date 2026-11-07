---
name: screencut
description: Make a product video cut from the REAL web UI, in a chosen style — kinetic (huge beat-locked words, colour-flip grounds, the screen beside the type), keynote (calm and premium for presentations: titles gliding in above a browser-window frame, smart zoom with a spotlight and callouts, a chapter bar, per-scene slide clips), social (vertical 9:16 for LinkedIn/Shorts: a crop that pans after the action, big word-by-word captions) or heist (CCTV HUD, glitch cuts) — with beat-synced cuts, sound effects, loads fast-forwarded and an optional ElevenLabs or Google Cloud TTS voice. Scripted end to end with Playwright + an HTML HUD rendered frame by frame + ffmpeg; no video editor. Use when someone asks for a demo video, walkthrough, explainer, tutorial clip, feature trailer, slide clips or "a video for <person>" of a web app or site.
---

# screencut — product videos cut from the real UI, in a style

**Playwright records the real UI, one short clip per step → the style's HTML HUD, a pure function of time, is rendered frame by frame → ffmpeg stacks footage + HUD + cut effects + audio.** Every word on screen is HTML, so it looks the same on every run and needs no ffmpeg text filter.

Everything here is generic: brand, texts, logo, music and voices all come from one `video.json`. Read [reference/PLAYBOOK.md](reference/PLAYBOOK.md) for each style's look, what worked and what was rejected, the lessons from past videos, and the traps.

## Step 0 — always: is it set up?
Run `python3 <this skill>/scripts/doctor.py` (add `video.json` once one exists) **before anything else**, and again whenever a script fails with "not set up yet". It lists each requirement as ✓/✗ with the exact fix command.
- **Anything ✗ under "required": guide the user through it before doing anything else**, one item at a time: show the `fix:` line, offer to run it, re-run the doctor until it says Ready. Required: Python 3.8+ with numpy, ffmpeg with libx264, Node 20+, Google Chrome, `npm install` in `scripts/` (adds `patchright`, a Playwright fork real sites challenge less).
- **Voice is optional.** Ask whether the video needs one. Providers: **ElevenLabs** (`ELEVENLABS_API_KEY`; TTS works on the free plan, music needs a paid one; the key needs the Speech to Text permission for the hear-back check and Voices read to list voices) or **Google Cloud TTS** (`GOOGLE_API_KEY` restricted to Text-to-Speech + Speech-to-Text, or `gcloud auth login` + `GOOGLE_CLOUD_PROJECT`).
  - Keys live in the environment (e.g. a 0600 file the shell profile sources). **The user sets them; never ask them to paste a key into the chat**, never pass one as an argument, never write one to a file.
  - If the doctor says Google would bill the gcloud default project, stop and ask which project to use: it may be a production project.

## Workflow
Work in a folder of its own, outside any product repo: `video.json`, `record.mjs`, `clips/`, `out/`, the music file, the logo SVGs.

1. **Ask the style first** (`"style"`; each is a folder under `styles/`), since it decides the recording and the words:
   - **kinetic**: big beat-locked type slams in, colour-flip grounds, the whole screen beside the type (`layout` `split`/`cards`/`window`). Wants a track with a clear beat.
   - **keynote**: calm, premium, for presentations. Titles glide in above (`above`) or beside (`beside`) a still browser-window frame; per scene the camera eases into where the action is, a spotlight dims the rest and a short `callout` names it; a chapter bar. Also writes `out/slides/` (one looping clip + poster per scene, `index.md`) unless `exports.slides: false`; `exports.aspect: "4:3"` for older decks.
   - **social**: vertical 1080×1920. A hook title in the first second, the footage in a window whose crop pans after the action, big word-by-word captions from the voice lines in their own band, hard cuts on the beat, 2× speed.
   - **heist**: a CCTV HUD (REC, timestamp, cam labels, brackets, glitch cuts, grain). Rejected for a product explainer once; offer it for trailers.

   Then agree the story in plain words: who it's for, 3–6 steps, one title + one sentence per step (keynote: 2–4-word callouts too), the length. Ask for the music track and the logo; never generate a music bed.
2. **Voice samples before lines:** generate ONE line in 4–5 voices and let the person pick (a famous stock voice reads as "overused"). Then `node scripts/voice.mjs lines.json out/vo [--provider elevenlabs|google]`: each line is transcribed back and regenerated until it matches and fits. Write numbers as they sound; set `spoken` to what the transcript will say ("dot com" comes back as ".com").
3. **Record** (`examples/record.example.mjs` → your `record.mjs`; import `rig.mjs` by the skill's absolute path):
   - Wide 16:9 at 2× density: `viewport: {width: 2400, height: 1350}`, `deviceScaleFactor: 2` (reads as the page zoomed out to ~80 %, crisp; heist's desk rect suits the 1280×800 default).
   - `rig.clip(name, run, setup)`: `setup` is cut off. In it, wait until the page has REALLY loaded: no "Loading…", no sample-data banner, network idle. Wait on visible elements (`.filter({ visible: true })`). Hold 2–3 s on every result.
   - `glide(page, locator)` moves the cursor and logs the target's box; `focus(page, locator)` logs a result without moving. Keynote and social then look exactly there (else they find the action from motion; a live page that changes everywhere defeats that).
   - Real clicks, real typing, real answers: wait for the actual response with a generous timeout (10 min); fast-forward compresses the wait.
   - **Logged-in sites:** a person signs in; the agent never types or holds credentials. If the app's session cookie is session-only, a saved profile opens signed out in every clip: sign in once per run in a launched window and pass its in-memory `storageState` to the rig (example, option B), never written to disk. Otherwise `node scripts/login.mjs <url> <profileDir>` once and pass `profileDir`. Keep profiles outside any repo; keep tokens out of logs.
   - `SCENES=s3 node record.mjs` (the rig's `only`) re-records one scene; `clips.json` is merged and saved after every clip.
   - Demo data only; nothing private or customer-identifying. Prefer screens with real data over empty states.
4. **Look at frames from every clip before building** (start, middle, end of each `webm`): skeletons, sample data, empty states, UI bugs. Report bugs rather than editing around them.
5. **Write `video.json`** (`examples/video.example.json`; `python3 scripts/config.py video.json` checks it, with "did you mean"): `style`, brand colours, intro, scenes (`clip`, `title` as `[[text, ""], [text, "a"]]` where `"a"` is the accent, `sub`; per style `kind`/`cam` (heist), `layout`, `callout`/`chapter`/`focus`/`zoom` (keynote, social), `crop` or `"fit": "content"`), end card (`end.logo`; mark a mascot's eyes `data-blink` and it blinks), `music` (`"sync": true | "beat" | "bar"`), `voice` with each line anchored to its scene (`voice[].scene`: 0 intro, 1..n, `"end"`), `sfx`. For manifesto/vision beats with no footage, a type scene: `{"kind": "type", "title", "lines", "strike", "then", "chips", "len" | "beats"}`, no `clip`.
6. **Contact sheet, then build:** `python3 scripts/build.py video.json --sheet` (HUD only, one frame per scene), then `python3 scripts/build.py video.json` → the mp4 (H.264 high@4.1, faststart), `out/contact.png`, keynote's `out/slides/`, then the checks (`scripts/check.py`): non-zero exit = a FAIL; WARNs are pacing and loudness worth a look. The build prints where each scene's camera looks (`focus`, `logged`, `motion`). **Look at the contact sheet and at frames you pick yourself** (zoom holds, captions, cuts, posters) before sharing: text over footage, cut-off words, empty frames, jittery pans.

Another way to put a look in, for long narrated walkthroughs: highlights injected into the page and recorded in-frame, then chapters and a narrator (a teammate's rig). The recording step (`rig.mjs`) serves both; only the look stage differs.

## Rules
- Real product footage only, never mockups.
- **Text and badges never cover the footage**, in any style: type gets its own column, band or card; callouts and chips sit outside the footage.
- No ffmpeg `drawtext`: all text belongs in the style's `hud.html`. Cap any generated audio with `-t`.
- A new style is a folder `styles/<name>/`: `hud.html` (defines `window.render(t)` as a pure function of t, loads `../common.js`, whose helpers it must not redefine) and `style.json` (cut, cutSound, footage, layouts, beat grid, camera, size…); copy the closest one.
- HUD fps = footage fps (30), or the cards drift.
- The video doubles as QA: if a frame shows a UI bug, report it.
