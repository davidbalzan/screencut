// Render a style's HUD (styles/<style>/hud.html) frame by frame. Overlay styles (heist) give
// transparent PNGs; styles that draw the footage themselves (footage "hud": kinetic, keynote,
// social) are opaque, so they give JPEGs, which are far smaller and faster. The frame size is
// the timeline's `size` (default 1920x1080; social is 1080x1920).
//   node render.mjs <timeline.json> <out-dir> [fps=30] [--frames 0,45,120] [--png]
//   (--frames: only those, for contact sheets and posters; --png: opaque PNGs instead of JPEGs)
import { chromium } from "patchright";
import { readFileSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const args = process.argv.slice(2);
const [tlFile, out] = args;
const fps = Number(args[2] && !args[2].startsWith("--") ? args[2] : 30);
const only = args.includes("--frames") ? args[args.indexOf("--frames") + 1].split(",").map(Number) : null;
if (!tlFile || !out) { console.error("usage: node render.mjs <timeline.json> <out-dir> [fps]"); process.exit(2); }

const tl = JSON.parse(readFileSync(tlFile, "utf8"));
const style = tl.style ?? { name: "heist" };
const html = join(dirname(fileURLToPath(import.meta.url)), "..", "styles", style.name, "hud.html");
const opaque = style.footage === "hud";
const png = !opaque || args.includes("--png");
const [W, H] = tl.size ?? [1920, 1080];
mkdirSync(out, { recursive: true });
const b = await chromium.launch({ channel: "chrome", headless: true });
const p = await b.newPage({ viewport: { width: W, height: H } });
// patchright evaluates in an isolated world, so the timeline goes in as a page script.
await p.addInitScript({ content: `window.__TL = ${JSON.stringify(tl)};` });
await p.goto("file://" + resolve(html), { waitUntil: "networkidle" });
// Web fonts load lazily, on first use: load every declared face now, so frame 0 (and any text
// measuring the HUD does) already uses them.
await p.evaluate(() => Promise.all([...document.fonts].map((f) => f.load().catch(() => null))));
await p.waitForFunction(() => document.fonts.status === "loaded");
const frames = only ?? Array.from({ length: Math.round(tl.total * fps) }, (_, i) => i);
for (const i of frames) {
  await p.evaluate((t) => { const s = document.createElement("script"); s.textContent = `window.render(${t})`; document.head.appendChild(s); s.remove(); }, i / fps);
  // The DOM is shared across worlds: wait until every image (footage frames, logos) is decoded.
  await p.evaluate(() => Promise.all([...document.images].map((im) => (im.getAttribute("src") ? im.decode().catch(() => null) : null))));
  const name = join(out, `${String(i).padStart(5, "0")}.${png ? "png" : "jpg"}`);
  await p.screenshot(png ? { path: name, omitBackground: !opaque } : { path: name, type: "jpeg", quality: 92 });
  if (i % 150 === 0) console.error(`frame ${i}/${frames.length}`);
}
await b.close();
console.error("hud frames:", frames.length);
