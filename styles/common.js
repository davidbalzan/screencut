// Shared by every style's hud.html (loaded before it). Small pure helpers and the end-card
// logo blink. Everything is a function of t: no CSS animations, no timers.
const rnd = (seed) => { const x = Math.sin(seed * 12.9898) * 43758.5453; return x - Math.floor(x); };
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const ease = (x) => 1 - Math.pow(1 - clamp(x), 3);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const typed = (text, p, cursor = "▌") => esc(text.slice(0, Math.floor(clamp(p) * text.length))) + (p < 1 && Math.floor(p * 18) % 2 ? cursor : "");
const pad = (v, n = 2) => String(v).padStart(n, "0");
const easeInOut = (x) => { x = clamp(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };

// Colour: "#rrggbb" in, "#rrggbb" or rgba() out.
const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const hex = (c) => "#" + c.map((v) => Math.round(clamp(v, 0, 255)).toString(16).padStart(2, "0")).join("");
const mix = (a, b, k) => hex(rgb(a).map((v, i) => v + (rgb(b)[i] - v) * k));
const alpha = (h, a) => `rgba(${rgb(h).join(",")},${a})`;
const lum = (h) => { const [r, g, b] = rgb(h).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };

// Text width in px for a CSS font ("600 22px Inter"); fonts must be loaded (render.mjs waits).
const _measure = document.createElement("canvas").getContext("2d");
const textWidth = (text, font) => { _measure.font = font; return _measure.measureText(String(text)).width; };

// Footage frames drawn by the HUD (kinetic, keynote, social): the src of a scene's frame at t.
const frameSrc = (sc, t, fps = 30) => sc.frames ? `file://${sc.frames.dir}/${pad(clamp(Math.floor((t - sc.start) * fps + 1e-6), 0, sc.frames.n - 1), 5)}.jpg` : null;

// Camera (keynote, social): the view [x, y, w, h] in footage pixels at t, from the scene's
// keyframes [[t, x, y, w, h], ...]; eased between keyframes (keynote) or linear (social, whose
// keyframes are dense and already smooth).
function viewAt(sc, t) {
  const K = sc.view ?? [];
  if (!K.length) return [0, 0, ...(sc.fsize ?? [1, 1])];
  if (t <= K[0][0]) return K[0].slice(1);
  for (let i = 0; i < K.length - 1; i++) {
    const [a, b] = [K[i], K[i + 1]];
    if (t < b[0]) {
      const u = (t - a[0]) / Math.max(b[0] - a[0], 1e-6), e = sc.viewEase === false ? u : easeInOut(u);
      return a.slice(1).map((v, j) => v + (b[j + 1] - v) * e);
    }
  }
  return K[K.length - 1].slice(1);
}
// Place an <img> of a scene's footage so it shows the view v inside a box w px wide.
function showView(img, sc, v, w) {
  const [cw, ch] = sc.fsize, s = w / v[2];
  Object.assign(img.style, { width: cw + "px", height: ch + "px", transformOrigin: "0 0",
    transform: `scale(${s.toFixed(5)}) translate(${(-v[0]).toFixed(2)}px,${(-v[1]).toFixed(2)}px)` });
  return s;
}

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
