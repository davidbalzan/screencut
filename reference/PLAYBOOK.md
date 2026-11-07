# Product videos from the real UI: the playbook

How the FindMyRTP trailer (Sep 2026), the My Casinos tutorial (Oct 2026) and the Citrillo explainer (Nov 2026, in kinetic, keynote and social) were made, turned into the generic scripts in `../scripts`. Everything is scripted; there is no video editor and no post-production step.

## The look (heist)
- 1920×1080, 30 fps, near-black `#03060b`; one accent colour from the product's logo (FindMyRTP used green `#4ade80`) and a red for REC/alerts.
- Oswald bold uppercase for titles, letter-spaced mono small caps for labels (Google Fonts). The product's own logo SVGs on the end card.
- Surveillance HUD: blinking REC and a running timestamp, `CAM 01 // <PLACE>` labels, corner brackets that lock onto the footage, titles that decode from random glyphs, typed subtitles, decoding intro and end cards.
- Glitch hits (RGB split + noise) only at the cuts; fine grain throughout; scanlines and a soft vignette.

## The look (kinetic)
- After Scenario's [Kinetic Film](https://www.scenario.com/explorations/kinetic-film/): huge words on every beat (slams, stacks, splits), colour flips, hard cuts on the beat grid, a sound on every cut.
- Inter Tight Black, all caps, tight tracking; Inter for the subtitle. A slam is scale 1.4 → 1 with a fast ease-out and a blur that clears as it lands, opaque from its first frame.
- Grounds: a deep tinted dark (`brand.ground`, not near-black) with a soft glow, and flips through `brand.palette` (Citrillo: lime, a warm orange, a pale lime, mid green). Text on a flip is dark or white by contrast.
- Each scene: a 2-beat lead-in (the title split in two, one half per beat, the ground flipping colour on each), then a hard cut to the footage. **Nothing is ever drawn over the screen.** `layout`:
  - `split` (default): the whole 16:9 screen in a frame on the right (~64 % of the width, rounded, a soft coloured glow), the page pushing in 1.00 → 1.04 inside it; the type in its own left column: step number, the title stacking one word per beat (sized so the longest word fits even at the slam's start), the subtitle wrapping under it, the fast-forward chip at the column's foot.
  - `cards`: the lead-in card is the title; the screen then plays clean at ~90 % height with a slim caption bar under it (step, title, subtitle, chip).
  - `window`: the screen in a rounded window with a soft shadow and an offset palette block, tilting in, the title stacked beside it.
- Typed subtitles finish at least 1.2 s before the cut, and wrap inside their column.
- End card: the logo slams in and blinks (elements marked `data-blink`, at 0.6 s and a double at 2.2 s), the line lands phrase by phrase, then the url types.
- "I don't really like the heist style" (David, Nov 2026) and "more colour, less black, still a dark background"; "the shots are missing a lot of the screen; square is not ideal"; "use a fullscreen window, just scale the text / zoom out"; then, of a full-bleed build with a scrim, "we need to scale the screenshot content so that it's not covered". Hence: record 16:9 zoomed out, and lay the type out beside or before the screen, never over it.

## The look (keynote)
- Corporate but dynamic, for presentations: calm, premium, nothing slams. A deep slate ground tinted toward `brand.ground` (`#0f172a` mixed 30 % toward it), or, when `brand.ground` is light, that light ground with slate text; the accent used sparingly (step label, the title's accent words, the spotlight ring, the current chapter).
- Inter Tight 600 for titles (sentence case, ~52 px), Inter for the rest. Titles and subtitles glide in: opacity, a 16 px rise and an 8 px blur clearing, eased over ~0.7 s, staggered; they glide out in the last 0.3 s.
- The footage sits in a still light browser-window frame (a 38 px top bar, three dots, the site in a pill; 14 px corners, a soft deep shadow). Layout `above` (default): step label, title and subtitle above the frame, aligned to it; `beside`: in a column left of it. A chapter bar under the frame: one segment per step, the current one filling in the accent, short labels (`chapter`, else the title).
- **Smart zoom:** per scene the camera eases (ease-in-out) into where the action is, holds, and eases back to the whole screen by the cut; the frame never moves, only the footage inside it. Zoom 1.3× to 2.2× (`zoom` caps it; `zoom: 1` turns it off). While zoomed, a spotlight dims the rest of the screen a little (slate at 34 %) and rings the region in the accent; the `callout` (2–4 words) sits in the ground beside the window, level with the region, a thin accent line running to it.
- Soft cuts: the previous scene's last frame dissolves into the next (0.35 s) inside the still frame; a soft whoosh peaks on each cut. Cuts land on the bar when the music has sync (`"sync": true`). No grain, no glitch.
- Slides (`exports.slides`, default on): every scene alone as `NN-<clip>.mp4` (the frame, zoom, spotlight and callout; no title, no chapter bar, no voice; fades from and to the ground so it loops) with a `.png` poster at the settled zoom and an `index.md`, ready to drop one per slide into Keynote or PowerPoint; `exports.aspect: "4:3"` for older decks.

## The look (social)
- Vertical 1080×1920 for LinkedIn and Shorts. The kinetic ground and palette, Inter Tight Black.
- A hook in the first second: the intro title slams in on frame 0, the kicker and the line right after.
- Per scene: step and title in a band at the top, the footage in a 1000×1080 rounded window in the middle, a vertical crop of the 16:9 recording that pans after the action (smoothed, a dead zone in its middle, at most half its width a second, 1.3× to 1.8× closer than the full height), big word-by-word captions in their own band below it (the voice lines' text, each word timed by its length across the line's speech, the current word in the accent), a progress bar at the foot. Nothing sits on the footage; the fast-forward chip sits in the title band.
- Hard cuts on the beat, speed 2×, fast-forward on: short scenes.
## What worked, what was rejected
| Worked | Rejected |
|---|---|
| The "heist / CCTV" HUD composited over clean footage | Captions and spotlights injected into the page and recorded ("overengineering"); keynote's spotlight is composited by the HUD, the page stays clean |
| Moving HUD scenes | Static title cards ("the CCTV version is way more smooth") |
| Real site footage | Mockups |
| A real music track chosen by the person; 1.5× speed for tutorials | A generated music bed ("music is shit") |
| Brand colours sampled from the logo | Naming countries or locations on screen or in voice ("makes it easier to block us") |
| For marketing: bigger and crazier | |
| The whole screen, recorded 16:9 and zoomed out, beside the type | Square crops of a 16:10 screen ("missing a lot of the screen") |
| Type in its own column or card | Type and a dark scrim over the screen (it hid the release titles) |
| Loads fast-forwarded (8×, ~0.25 s each), still visible | Sitting through a 20 s wait for an answer |
| Kinetic or keynote for a product explainer | Heist for a product explainer (David: "I don't really like the heist style") |
| A voice picked from 4–5 samples of the same line (George) | A stock voice everyone knows (Brian: "overused on YouTube") |

## Pipeline, as the scripts do it
1. **Record** (`rig.mjs`): one `recordVideo` per scene, an injected arrow cursor and nothing else; 2400×1350 at deviceScaleFactor 2 for anything 16:9 (the rig's default 1280×800 is for heist's desk rect; phone 390×844). `clips.json` (written after every clip) holds each clip's seconds of useful action, which the build keeps, and the boxes `glide()`/`focus()` logged with their times.
2. **Timeline** (`build.py`): per scene, length = the style's lead-in + the action played at its speeds (`speed`, then `ramps` and fast-forwarded still stretches), a footage rect (heist: desk 1074×960 at x=90; wide 1280×800; phone 444×960 centred; full 1200×750; kinetic, keynote, social: the box of its layout, the footage keeping its aspect except social's crop), title, subtitle, cam label. Intro 3.0 s, end card 3.4 s. Every cut snaps later to the beat grid when there is one. Camera styles plan their moves here (`camera.py`, see below).
3. **Base footage:** `setpts=PTS/speed` (with ramps: each stretch trimmed, retimed and concatenated), crop (given, `fit: "content"`, or centred to the rect's aspect), scale, overlay on the dark canvas, the style's grade. Concat, then (heist) glitch around each cut and grain everywhere. Kinetic, keynote and social also extract the footage as JPEG frames for their HUD (at the scale of the closest zoom).
4. **HUD** (`hud.html` + `render.mjs`): `window.render(t)` is a pure function of time; the renderer screenshots each frame (heist: transparent PNGs overlaid; the others draw the footage too, opaque JPEGs).
5. **Audio:** the mix is always padded to the whole timeline (without music it used to end with the last sound, and `-shortest` clipped the end card); music from 0 s with a 0.3 s fade-in and 2.2 s fade-out; optional `sync` snaps every cut to the next beat/bar of the track (idea from Scenario's Kinetic Film, which cuts on a beat grid); `sfx` hits on each cut; optional voice lines placed by start time.
6. **Export:** `libx264 -preset slow -crf 22 -profile:v high -level:v 4.1 -maxrate 10M`, AAC 192k, `+faststart`. A contact sheet (`out/contact.png`) with one frame per scene.
7. **Checks** (`check.py`): length vs timeline, phone playback (codec/profile/level; level ≤ 4.2 up to 1080p in either orientation, 1080×1920@30 fits 4.1), faststart, per-scene blank footage and holds (measured on `base_raw.mp4`, before grain and the HUD clock), loudness (EBU R128, aim ≈ -14 LUFS) and true peak ≤ -1 dBTP.

## Where the camera looks (keynote, social)
In order: the scene's `focus` [x, y, w, h] (recording pixels); the boxes the recorder logged (`glide()` logs its target, `focus(page, locator)` marks a result without moving the mouse; times are seconds into the clip's action, mapped through the speed plan); else the motion finder (`focus.py`):
- Frames of the kept action are sampled (gray, 480 px wide, 8 fps, at most 360) and differenced. A pair where shifting the frame up or down explains the change, within the columns that changed, is a scroll; a pair where over 18 % changed is a page swap. Neither says where to look, so both are kept apart.
- The rest is summed per 0.25 s of ON-SCREEN time, as the union of what changed in that stretch: a 4-minute wait fast-forwarded to 1 s counts for 1 s, and a clock ticking in place counts once. Later stretches weigh more (0.4 → 1), as the result is held at the end.
- The region holds the central 84 % of that heat on each axis, padded 3.5 %, clamped to the frame. If only the cursor moved while the page scrolled (local heat under 2 % of the scroll heat), the region is what scrolled.
- Keynote's view fits the region at 80 % × 72 % of the view, zoom kept in 1.3–2.2×; several logged boxes become stops the camera moves between, or their union when one view holds them all or the scene is too short. Social's crop fits the largest box, follows the change's centroid (Gaussian-weighted over ±0.5 s, held where nothing changes), smoothed twice, with a dead zone and a speed limit.
- Where it fails: a live page that changes everywhere during a long wait (Citrillo's Activity screen while the lead answered) spreads the heat over the whole screen; a scene where only the cursor glides from its parking spot gives the cursor's trail. Log the box (`glide`/`focus`) or give `focus`. The build prints which source each scene used.

## Lessons from the Citrillo explainer, Nov 2026
**Story and style**
- Ask for the style first (heist, kinetic, keynote, social): it decides the recording (16:9 or not), the pacing and what the titles say. Heist did not fit a product explainer.
- Offer voice samples before generating the lines: the same line in 4–5 voices, the person picks. A famous stock voice (ElevenLabs "Brian") reads as "overused on YouTube"; George was chosen.

**Signing in to a real app**
- A saved Chrome profile does not survive between clips when the app's sign-in cookie is session-only: every clip opened signed out. Sign in once per run in a launched window and pass the in-memory `storageState` to every recording context (`examples/record.example.mjs`, option B); never write it to disk.
- One-time sign-in links work well (the person, or the agent if allowed, makes one per run): only on the local address, never written to a file. Keep the login window open until the script closes it, or the profile stays locked.
- A restored browser tab can replay an old sign-in URL into the log: filter tokens out of anything printed.

**Recording**
- Record wide 16:9 at 2× density (2400×1350 CSS px, deviceScaleFactor 2): scaled to 1080p it reads as the page zoomed out to ~80 %, showing far more of each screen, with crisp text (and room for keynote's zoom). The 1280×800 1× default looked cramped and soft.
- Wait for the page to really load before the camera starts (in `setup`): no "Loading…"/"Reading…" text, no sample-data banner, network idle. A slow screen made clips end on skeletons.
- Wait on VISIBLE elements (`.filter({ visible: true })`): a hidden duplicate matched first and the wait timed out.
- An app that shows sample or fixture data while loading (Citrillo's Decisions screen did): exclude it in the wait, and report it as a UI bug.
- Back ends are slow when busy: the lead's answer took 20 s to 4 min. Give real waits generous timeouts (10 min) and let fast-forward compress them rather than trimming. Keep the page quiet meanwhile if you can: a live page ticking for minutes defeats the motion finder (log a `focus`).
- Record one scene at a time when needed (`SCENES=s4 node record.mjs`, the rig's `only`); `clips.json` is merged and written after every clip, so a crash keeps the clips already recorded.
- A record script outside the skill folder can't resolve `patchright`: import `rig.mjs` (and patchright, for a sign-in window) by the skill's absolute path.
- Prefer scenes that show real data: empty states ("Nothing yet", "Nothing reached main today") make thin footage. Fold empty board lanes, or record when there is activity.
- Mark what matters while recording: `glide()` logs its target, `focus(page, locator)` logs a result; keynote and social then look exactly there.

**Building**
- Text never covers the footage, in any style: big titles with a scrim hid half the screen. The footage gets its own area and the type its own column, band or card; badges (the fast-forward chip) and callouts sit outside the footage too.
- Typed subtitles finish with time to read (≥ 1.2 s before the cut) and wrap, never cut mid-word.
- Fast-forward still stretches instead of trimming them: the viewer sees the load happen, quickly. Typing small text can fall under the stillness threshold and be fast-forwarded with the wait (Citrillo's question typed in s5 went at 230×): ramp it by hand if the typing matters.
- Fit short pages to their content (`fit: "content"`; the brief form filled half the screen) or record at a viewport that fits them.
- The mix spans the whole timeline: with no music the output used to end with the last sound, clipping the end card.
- Anchor voice lines to scenes (`voice[].scene`), not absolute seconds: re-timing scenes then needs no hand re-timing, and a scene holds until its line ends.

**Voice and music (ElevenLabs)**
- Text-to-speech works on the free plan; music generation needs a paid plan (`paid_plan_required`). Ask for a track anyway: generated beds were rejected.
- The API key needs the Speech to Text permission for the hear-back check, and Voices read to list voices.
- Speech-to-text writes "dot com" as ".com": set the line's `spoken` text to what the transcript will say.
- Keys live in a 0600 file sourced by the shell profile, never in chat, arguments or repo files; a fresh shell loads them for the voice step.

**QA**
- Look at frames from every clip before building (one from the start, the middle and the end of each `webm`), then at the contact sheet and frames you pick after. The video is QA: it surfaced two Citrillo bugs (sample decisions flash while loading; "Reading the decision…" for ~3 s).

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
- Pad the end with blank footage and cut to the total, or the end card is clipped (the audio too: see the lessons).
- Fast-forward finds still stretches with the same measure as the checks (`freezedetect`, noise 0.003). A deliberate mid-clip reading hold is "still" too and gets sped up: turn `fastForward` off for that scene or ramp by hand.
- Playwright pads a page smaller than the viewport with grey; `fit: "content"` crops that away (see the lessons).
- HUD fps must match the footage or cards drift.
- patchright's `page.evaluate` runs in an isolated world: page globals (`window.render`) aren't visible. `render.mjs` therefore calls it through an injected `<script>`.
- Scroll after hydration (it resets scroll), with `mouse.wheel`. Wait for dropdowns to be open before touching their rows.
- Never trust a frame you haven't looked at. The My Casinos tutorial's frames exposed two real UI bugs, Citrillo's two more: the video doubles as QA.
- HUD scripts share one global scope with `common.js`: a helper defined in both (`rgb`, `mix`, `lum`…) is a SyntaxError and a blank render. Shared helpers live in `common.js` only.
- 1080×1920 at 30 fps is 8160 macroblocks a frame: level 4.1 holds it; a vertical video is not "above 1080p".
