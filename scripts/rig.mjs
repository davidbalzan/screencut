// Recording helpers: one short Playwright video per scene of the REAL UI, an arrow cursor
// (recordings have none), nothing else drawn on the page. Import this from your own
// record script (see examples/record.example.mjs).
//
//   const rig = await openRig({ profileDir, headless: false });
//   await rig.clip("s1", async (page) => { ... });   // records clips/s1/*.webm
//   await rig.done();                                  // writes clips/clips.json
//
// Every clip writes how many seconds of useful action it holds (from the moment
// `run` starts to its end); the build trims each recording to that tail, so page loads
// and settling time never reach the video.
import { chromium } from "patchright";
import { mkdirSync, writeFileSync, readdirSync } from "node:fs";
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

/** Move the mouse smoothly to the centre of a locator (Playwright jumps otherwise). */
export async function glide(page, locator, ms = 800) {
  const b = await locator.boundingBox();
  if (!b) throw new Error("glide: element not visible");
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: Math.max(1, Math.round(ms / 16)) });
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
 * @param {object} [o.contextOptions] extra Playwright context options (isMobile, hasTouch, deviceScaleFactor…)
 */
export async function openRig(o = {}) {
  const out = resolve(o.out ?? "clips");
  const viewport = o.viewport ?? { width: 1280, height: 800 };
  mkdirSync(out, { recursive: true });
  const clips = [];
  let browser = null;

  const newContext = async (dir) => {
    const opts = {
      ...(o.chrome === false ? {} : { channel: "chrome" }),
      headless: o.headless ?? false,
      viewport,
      recordVideo: { dir, size: viewport },
      ...(o.contextOptions ?? {}),
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
      const dir = join(out, name);
      mkdirSync(dir, { recursive: true });
      for (const f of readdirSync(dir)) if (f.endsWith(".webm")) throw new Error(`clip ${name}: ${dir} already has a recording; delete it to re-record`);
      const ctx = await newContext(dir);
      await ctx.addInitScript(ARROW);
      const page = ctx.pages()[0] ?? (await ctx.newPage());
      if (setup) await setup(page);
      const t0 = Date.now();
      await run(page);
      const dur = (Date.now() - t0) / 1000;
      const video = page.video();
      await ctx.close();
      const file = video ? await video.path() : null;
      if (!file) throw new Error(`clip ${name}: no video was recorded`);
      clips.push({ name, file: relative(out, file), dur: Math.round(dur * 1000) / 1000 });
      console.error(`clip ${name}: ${dur.toFixed(1)} s of action`);
      return page;
    },
    async done() {
      if (browser) await browser.close();
      writeFileSync(join(out, "clips.json"), JSON.stringify(clips, null, 2) + "\n");
      console.error(`wrote ${join(out, "clips.json")} (${clips.length} clips)`);
    },
  };
}
