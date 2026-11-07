// Example recording script: copy it next to your video.json and change the scenes.
//   node record.mjs                       (writes ./clips/<name>/*.webm and ./clips/clips.json)
//   SCENES=s2 node record.mjs             (records only s2; the other clips stay in clips.json)
// Import the rig by the skill's ABSOLUTE path: a record script outside the skill folder can't
// resolve "patchright" from its own folder.
import { openRig, glide, focus, wait, typeSlow } from "/ABSOLUTE/PATH/TO/screencut/scripts/rig.mjs";

const URL = "http://localhost:3000";

// ---- Signing in (pick one; skip both for a public site)
// A. A saved profile: `node <skill>/scripts/login.mjs <url> <profileDir>`, a person logs in once,
//    then pass `profileDir` to openRig. Fails when the app's sign-in cookie is session-only:
//    every clip then opens signed out.
// B. Sign in once per run, keep the session IN MEMORY (never written to disk) and start every
//    recording context with it. A person signs in in the window (or a one-time sign-in link for
//    the local address does it); the window closes by itself once the app shows it is signed in.
const SIGN_IN = false;
let storageState;
if (SIGN_IN) {
  const { chromium } = await import("/ABSOLUTE/PATH/TO/screencut/scripts/node_modules/patchright/index.mjs");
  const login = await chromium.launch({ channel: "chrome", headless: false });
  const ctx = await login.newContext({ viewport: null });
  const page = await ctx.newPage();
  await page.goto(URL);
  console.error("Sign in in the window; it closes by itself once you are in.");
  await page.getByTestId("signed-in-as").waitFor({ timeout: 15 * 60_000 }); // something only a signed-in page shows
  storageState = await ctx.storageState(); // cookies + local storage, in memory only
  await login.close();
}

// 16:9 at 2400x1350 CSS px, captured at 2x: scaled to 1080p it reads as the page zoomed out to
// ~80 %, showing far more of each screen, with crisp text.
const rig = await openRig({
  out: "clips",
  viewport: { width: 2400, height: 1350 },
  contextOptions: { deviceScaleFactor: 2, ...(storageState ? { storageState } : {}) },
  only: process.env.SCENES,
  // profileDir: "/path/outside/any/repo/profile",   // option A
});

// setup (the 3rd argument) is cut off: load, wait until the page has REALLY loaded (no
// "Loading…", no sample data, network idle), dismiss banners, scroll after hydration.
const ready = async (page) => {
  await page.goto(URL, { waitUntil: "load" });
  await page.mouse.move(2340, 1300); // park the cursor out of the way
  const busy = page.getByText(/^Loading\b/);
  for (let i = 0; i < 120 && (await busy.count()) > 0; i++) await wait(page, 500);
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  await wait(page, 1200);
};

await rig.clip("s1", async (page) => {
  const btn = page.getByRole("button", { name: /open/i }).filter({ visible: true }).first(); // visible: a hidden duplicate may match first
  await glide(page, btn, 1200); // glide() also logs the box, so keynote/social look there
  await btn.click();
  await focus(page, page.getByRole("dialog")); // where to look next, without moving the mouse
  await wait(page, 2500); // hold on the result: the viewer needs time to read
}, ready);

await rig.clip("s2", async (page) => {
  const box = page.getByRole("textbox").first();
  await glide(page, box, 900);
  await box.click();
  await typeSlow(box, "How is it doing today?");
  await page.keyboard.press("Enter");
  // wait for the real answer; a busy back end can take minutes: the build fast-forwards the wait
  const answer = page.getByText(/done|ready/i).filter({ visible: true }).first();
  await answer.waitFor({ timeout: 10 * 60_000 });
  await focus(page, answer);
  await wait(page, 2500);
}, ready);

await rig.done();
