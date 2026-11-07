# CCTV-style product videos: the playbook

How the FindMyRTP trailer (Sep 2026) and the My Casinos tutorial (Oct 2026) were made, turned into the generic scripts in `../scripts`. Everything is scripted; there is no video editor and no post-production step.

## The look (heist)
- 1920×1080, 30 fps, near-black `#03060b`; one accent colour from the product's logo (FindMyRTP used green `#4ade80`) and a red for REC/alerts.
- Oswald bold uppercase for titles, letter-spaced mono small caps for labels (Google Fonts). The product's own logo SVGs on the end card.
- Surveillance HUD: blinking REC and a running timestamp, `CAM 01 // <PLACE>` labels, corner brackets that lock onto the footage, titles that decode from random glyphs, typed subtitles, decoding intro and end cards.
- Glitch hits (RGB split + noise) only at the cuts; fine grain throughout; scanlines and a soft vignette.

## The look (kinetic)
- After Scenario's [Kinetic Film](https://www.scenario.com/explorations/kinetic-film/): huge words on every beat (slams, stacks, splits), colour flips, hard cuts on the beat grid, a sound on every cut.
- Inter Tight Black, all caps, tight tracking; Inter for the subtitle. A slam is scale 1.4 → 1 with a fast ease-out and a blur that clears as it lands, opaque from its first frame.
- Grounds: a deep tinted dark (`brand.ground`, not near-black) with a soft glow, and flips through `brand.palette` (Citrillo: lime, a warm orange, a pale lime, mid green). Text on a flip is dark or white by contrast.
- Each scene: a 2-beat lead-in (the title split in two, one half per beat, the ground flipping colour on each), a hard cut to the footage full bleed, pushing in 1.00 → 1.04; the title stacks big over a scrim one word per beat, then drops to a lower third on the next beat so the screen can be read.
- `"frame": "window"` instead: the screen in a rounded window with a soft shadow and an offset palette block, tilting in, the title stacked beside it.
- End card: the logo slams in and blinks (elements marked `data-blink`, at 0.6 s and a double at 2.2 s), the line lands phrase by phrase, then the url types.
- "I don't really like the heist style" (David, Nov 2026) and "more colour, less black, still a dark background"; "the shots are missing a lot of the screen; square is not ideal"; "use a fullscreen window, just scale the text / zoom out". Hence full bleed by default and a 16:9 recording at a zoomed-out scale.

## What worked, what was rejected
| Worked | Rejected |
|---|---|
| The "heist / CCTV" HUD composited over clean footage | Captions and spotlights drawn inside the page ("overengineering") |
| Moving HUD scenes | Static title cards ("the CCTV version is way more smooth") |
| Real site footage | Mockups |
| A real music track chosen by the person; 1.5× speed for tutorials | A generated music bed ("music is shit") |
| Brand colours sampled from the logo | Naming countries or locations on screen or in voice ("makes it easier to block us") |
| For marketing: bigger and crazier | |
| The whole screen, recorded 16:9 and zoomed out, full bleed | Square crops of a 16:10 screen ("missing a lot of the screen") |
| Loads fast-forwarded (8×, ~0.25 s each), still visible | Sitting through a 20 s wait for an answer |

## Pipeline, as the scripts do it
1. **Record** (`rig.mjs`): one `recordVideo` per scene, 1280×800 (phone 390×844), an injected arrow cursor and nothing else. `clips.json` holds each clip's seconds of useful action; the build keeps only that tail.
2. **Timeline** (`build.py`): per scene, length = the style's lead-in + the action played at its speeds (`speed`, then `ramps` and fast-forwarded still stretches), a footage rect (heist: desk 1074×960 at x=90; wide 1280×800; phone 444×960 centred; full 1200×750; kinetic: the whole frame or a window box), title, subtitle, cam label. Intro 3.0 s, end card 3.4 s. Every cut snaps later to the beat grid when there is one.
3. **Base footage:** `setpts=PTS/speed` (with ramps: each stretch trimmed, retimed and concatenated), crop (given, `fit: "content"`, or centred to the rect's aspect), scale, overlay on the dark canvas, the style's grade. Concat, then (heist) glitch around each cut and grain everywhere. Kinetic also extracts the footage as JPEG frames for its HUD.
4. **HUD** (`hud.html` + `render.mjs`): `window.render(t)` is a pure function of time; the renderer screenshots each frame with a transparent background; ffmpeg overlays the PNG sequence.
5. **Audio:** the mix is always padded to the whole timeline (without music it used to end with the last sound, and `-shortest` clipped the end card); music from 0 s with a 0.3 s fade-in and 2.2 s fade-out; optional `sync` snaps every cut to the next beat/bar of the track (idea from Scenario's Kinetic Film, which cuts on a beat grid); `sfx` hits on each cut; optional voice lines placed by start time.
6. **Export:** `libx264 -preset slow -crf 22 -profile:v high -level:v 4.1 -maxrate 10M`, AAC 192k, `+faststart`. A contact sheet (`out/contact.png`) with one frame per scene.
7. **Checks** (`check.py`): length vs timeline, phone playback (codec/profile/level), faststart, per-scene blank footage and holds (measured on `base_raw.mp4`, before grain and the HUD clock), loudness (EBU R128, aim ≈ -14 LUFS) and true peak ≤ -1 dBTP.

## Voice (trailers)
- Providers live in `scripts/speech.mjs`: ElevenLabs (below) or Google Cloud TTS (Chirp 3 HD voices; `speakingRate`; `pitch` only on non-Chirp voices; `ssml` for older voices). Google speech-to-text is the sync v1 API, so 60 s max per call; lines and check slices are a few seconds.
- ElevenLabs TTS `eleven_multilingual_v2`, `mp3_44100_128`, stability 0.35–0.4, similarity 0.8, style 0.55–0.6, speaker boost on.
- Voices that worked: narrator **Brian** `nPczCjzI2devNBz1zQrb` (deep, classy), announcements **Daniel** `onwK4e9ZLuTAKqWW03F9` (steady broadcaster), a rough character **Harry** `SOYHLrjzK2X1ezoPC6cr` with a walkie-talkie filter (`highpass=f=500,lowpass=f=3000,acrusher,aecho`).
- **Every line is transcribed back with `scribe_v1`** and regenerated (up to 3 tries) until it matches and fits its slot (`voice.mjs`). Write numbers and acronyms as they should sound.
- Sound effects were generated with ffmpeg `aevalsrc`/`anoisesrc` and placed by an event list, each landing on a visual event. **Always cap generated audio with `-t`/`d=`**: an unbounded expression once wrote a 95 GB wav.
- Final check: transcribe the whole mix with word timings; loudness with `ebur128`.

## Traps
- Beat detection on raw FFT bins puts a pitch-sweeping kick ~150 ms late; `beats.py` measures flux on coarse log bands for that reason.
- x264 picks level 5.0 for 1080p with `-preset slow` unless pinned; older phones/TVs refuse it.
- ffmpeg 8+ has no `-vsync`; use `-fps_mode`.
- Some ffmpeg builds have no `drawtext`. All text is HTML.
- Commas inside ffmpeg expressions must be escaped (`min(1\,t*14)`).
- Pad the end with blank footage and cut to the total, or the end card is clipped. Pad the audio too (`apad=whole_dur`).
- Fast-forward finds still stretches with the same measure as the checks (`freezedetect`, noise 0.003). A deliberate mid-clip reading hold is "still" too and gets sped up: turn `fastForward` off for that scene or ramp by hand.
- Playwright pads a page smaller than the viewport with grey; `fit: "content"` crops that away, but recording at the right viewport is better.
- HUD fps must match the footage or cards drift.
- patchright's `page.evaluate` runs in an isolated world: page globals (`window.render`) aren't visible. `render.mjs` therefore calls it through an injected `<script>`.
- Scroll after hydration (it resets scroll), with `mouse.wheel`. Wait for dropdowns to be open before touching their rows.
- Never trust a frame you haven't looked at. The tutorial's frames exposed two real UI bugs: the video doubles as QA.
