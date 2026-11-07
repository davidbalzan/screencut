// Recording helpers: one short Playwright video per scene of the REAL UI, an arrow cursor
// (recordings have none), nothing else drawn on the page. Import this from your own
// record script (see examples/record.example.mjs).
//
//   const rig = await openRig({ profileDir, headless: false, only: process.env.SCENES });
//   await rig.clip("s1", async (page) => { ... });   // records clips/s1/*.webm
//   await rig.done();                                  // closes the browser
//
// Every clip writes how many seconds of useful action it holds (from the moment
// `run` starts to its end); the build trims each recording to that tail, so page loads
// and settling time never reach the video. clips.json is written after EACH clip (merged
// with what is already there), so a crash mid-run keeps the clips already recorded.
// glide() and focus() log the target's box with its time into the clip, so the camera of
// keynote and social looks exactly there (clips.json: focus: [{t, box: [x, y, w, h]}], in
// pixels of the recorded video).
import { chromium } from "patchright";
import { mkdirSync, writeFileSync, readdirSync, readFileSync, existsSync } from "node:fs";
import { join, relative, resolve } from "node:path";

const ARROW = () => {
  const add = () => {
    const c = document.createElement("div");
    c.setAttribute("data-rig-cursor", "");
    c.style.cssText = "position:fixed;z-index:2147483647;left:-60px;top:-60px;width:22px;height:30px;pointer-events:none;filter:drop-shadow(0 2px 3px rgba(0,0,0,.6));transition:transform .1s;transform-origin:2px 2px";
    c.innerHTML = '<svg width="22" height="30" viewBox="0 0 22 30"><path d="M2 2 L2 24 L8 18.5 L12.5 28 L16.5 26.2 L12 17 L20 17 Z" fill="#fff" stroke="#0f172a" stroke-width="1.8" stroke-linejoin="round"/></svg>';
    document.documentElement.appendChild(c);
    addEventListener("pointermove", (e) => { c.style.left = e.clientX - 2 + "px"; c.style.top = e.clientY - 2 + "px"; }, true);
    addEventListener("pointerdown", () => (c.style.transform = "scale(.82)"), true);
    addEventListener("pointerup", () => (c.style.transform = "scale(1)"), true);
  };
  if (document.documentElement) add(); else addEventListener("DOMContentLoaded", add);
};

export const wait = (page, ms) => page.waitForTimeout(ms);

// The clip a page is recording ({t0, scale, w, h, focus[]}), so glide() and focus() can log boxes.
const recording = new WeakMap();

function logBox(page, b) {
  const r = recording.get(page);
  if (!r || r.t0 == null || !b) return; // setup (cut off) or not a rig page: nothing to log
  const x0 = Math.max(0, b.x), y0 = Math.max(0, b.y);
  const x1 = Math.min(r.w, b.x + b.width), y1 = Math.min(r.h, b.y + b.height);
  if (x1 <= x0 || y1 <= y0) return; // off screen
  r.focus.push({ t: Math.round((Date.now() - r.t0) / 10) / 100, box: [x0, y0, x1 - x0, y1 - y0].map((v) => Math.round(v * r.scale)) });
}

/** Move the mouse smoothly to the centre of a locator (Playwright jumps otherwise); logs its box. */
export async function glide(page, locator, ms = 800) {
  const b = await locator.boundingBox();
  if (!b) throw new Error("glide: element not visible");
  logBox(page, b);
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: Math.max(1, Math.round(ms / 16)) });
}

/** Mark where the viewer should look now (a result appearing, a panel opening): logs the
 *  locator's box for the camera without moving the mouse. */
export async function focus(page, locator) {
  logBox(page, await locator.boundingBox());
}

/** Type like a person: one key at a time, so the recording shows it. */
export async function typeSlow(locator, text, delay = 45) {
  await locator.pressSequentially(text, { delay });
}

/**
 * @param {object} o
 * @param {string} o.out          clips directory (default ./clips)
 * @param {string} [o.profileDir] a persistent browser profile. Use one for sites behind a login:
 *                                run `node login.mjs <url> <profileDir>` first, a person logs in, the
 *                                session is kept. Keep it OUTSIDE any repo.
 * @param {boolean} [o.headless]  default false: real sites challenge headless browsers
 * @param {{width:number,height:number}} [o.viewport] default 1280×800 (phone: 390×844)
 * @param {boolean} [o.chrome]    default true: the installed Google Chrome, not bundled Chromium
 * @param {object} [o.contextOptions] extra Playwright context options (isMobile, hasTouch, deviceScaleFactor,
 *                                storageState: a signed-in session kept in memory, see the example)
 * @param {string|string[]} [o.only] record only these clips (names, or "a,b" as from SCENES=a,b); the
 *                                others are skipped and keep their entries in clips.json
 */
export async function openRig(o = {}) {
  const out = resolve(o.out ?? "clips");
  const viewport = o.viewport ?? { width: 1280, height: 800 };
  const only = typeof o.only === "string" ? o.only.split(",").map((s) => s.trim()).filter(Boolean) : o.only;
  mkdirSync(out, { recursive: true });
  const index = join(out, "clips.json");
  const clips = existsSync(index) ? JSON.parse(readFileSync(index, "utf8")) : [];
  const save = () => writeFileSync(index, JSON.stringify(clips, null, 2) + "\n");
  let browser = null;

  const newContext = async (dir) => {
    const opts = {
      ...(o.chrome === false ? {} : { channel: "chrome" }),
      headless: o.headless ?? false,
      viewport,
      ...(o.contextOptions ?? {}),
      recordVideo: { size: viewport, ...(o.contextOptions?.recordVideo ?? {}), dir }, // the clip's folder always
    };
    if (o.profileDir) return chromium.launchPersistentContext(resolve(o.profileDir), opts);
    browser ??= await chromium.launch({ ...(o.chrome === false ? {} : { channel: "chrome" }), headless: o.headless ?? false });
    const { channel, headless, ...ctxOpts } = opts;
    return browser.newContext(ctxOpts);
  };

  return {
    /**
     * Record one scene. `setup(page)` runs first and is cut off (navigate, scroll, settle);
     * `run(page)` is the action the viewer sees.
     */
    async clip(name, run, setup) {
      if (only && !only.includes(name)) {
        console.error(`clip ${name}: skipped (only ${only.join(", ")})`);
        return undefined;
      }
      const dir = join(out, name);
      mkdirSync(dir, { recursive: true });
      for (const f of readdirSync(dir)) if (f.endsWith(".webm")) throw new Error(`clip ${name}: ${dir} already has a recording; delete it to re-record`);
      const ctx = await newContext(dir);
      await ctx.addInitScript(ARROW);
      const page = ctx.pages()[0] ?? (await ctx.newPage());
      // boxes are logged in CSS px; the video may be recorded at another size
      const size = o.contextOptions?.recordVideo?.size ?? viewport;
      const rec = { t0: null, scale: size.width / viewport.width, w: viewport.width, h: viewport.height, focus: [] };
      recording.set(page, rec);
      if (setup) await setup(page);
      const t0 = (rec.t0 = Date.now());
      await run(page);
      const dur = (Date.now() - t0) / 1000;
      const video = page.video();
      await ctx.close();
      const file = video ? await video.path() : null;
      if (!file) throw new Error(`clip ${name}: no video was recorded`);
      const entry = { name, file: relative(out, file), dur: Math.round(dur * 1000) / 1000, ...(rec.focus.length ? { focus: rec.focus } : {}) };
      const at = clips.findIndex((c) => c.name === name);
      if (at >= 0) clips[at] = entry; else clips.push(entry);
      save();
      console.error(`clip ${name}: ${dur.toFixed(1)} s of action${rec.focus.length ? `, ${rec.focus.length} focus boxes` : ""}`);
      return page;
    },
    async done() {
      if (browser) await browser.close();
      console.error(`${index}: ${clips.length} clips`);
    },
  };
}
