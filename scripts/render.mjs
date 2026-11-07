// Render the HUD (hud.html) frame by frame to transparent PNGs.
//   node render.mjs <timeline.json> <out-dir> [fps=30] [--frames 0,45,120]   (--frames: only those, for contact sheets)
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
const html = join(dirname(fileURLToPath(import.meta.url)), "hud.html");
mkdirSync(out, { recursive: true });
const b = await chromium.launch({ channel: "chrome", headless: true });
const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
// patchright evaluates in an isolated world, so the timeline goes in as a page script.
await p.addInitScript({ content: `window.__TL = ${JSON.stringify(tl)};` });
await p.goto("file://" + resolve(html), { waitUntil: "networkidle" });
await p.waitForFunction(() => document.fonts.status === "loaded");
const frames = only ?? Array.from({ length: Math.round(tl.total * fps) }, (_, i) => i);
for (const i of frames) {
  await p.evaluate((t) => { const s = document.createElement("script"); s.textContent = `window.render(${t})`; document.head.appendChild(s); s.remove(); }, i / fps);
  await p.screenshot({ path: join(out, `${String(i).padStart(5, "0")}.png`), omitBackground: true });
  if (i % 150 === 0) console.error(`frame ${i}/${frames.length}`);
}
await b.close();
console.error("hud frames:", frames.length);
