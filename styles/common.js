// Shared by every style's hud.html (loaded before it). Small pure helpers and the end-card
// logo blink. Everything is a function of t: no CSS animations, no timers.
const rnd = (seed) => { const x = Math.sin(seed * 12.9898) * 43758.5453; return x - Math.floor(x); };
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const ease = (x) => 1 - Math.pow(1 - clamp(x), 3);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const typed = (text, p, cursor = "▌") => esc(text.slice(0, Math.floor(clamp(p) * text.length))) + (p < 1 && Math.floor(p * 18) % 2 ? cursor : "");
const pad = (v, n = 2) => String(v).padStart(n, "0");

// Blink: logo elements marked data-blink (or class "blink") squash to 10 % height and back
// around their own centre. [start s into the end card, length s]: one blink, then a quick double.
const BLINKS = [[0.6, 0.16], [2.2, 0.12], [2.38, 0.12]];
function blinkScale(lt) {
  for (const [b, d] of BLINKS) {
    const k = (lt - b) / d;
    if (k >= 0 && k <= 1) return 1 - 0.9 * Math.sin(Math.PI * k);
  }
  return 1;
}
function applyBlink(el, lt) {
  if (!window.__TL.end.blink) return;
  const s = blinkScale(lt);
  el.querySelectorAll("[data-blink], .blink").forEach((e) => {
    e.style.transformBox = "fill-box";
    e.style.transformOrigin = "center";
    e.style.transform = `scaleY(${s})`;
  });
}
