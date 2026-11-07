// Example recording script: copy it next to your video.json and change the scenes.
// Run from the skill's scripts/ install (so "patchright" resolves):
//   node record.mjs                       (writes ./clips/<name>/*.webm and ./clips/clips.json)
// For a site behind a login, first: node <skill>/scripts/login.mjs <url> <profileDir>
import { openRig, glide, wait, typeSlow } from "../scripts/rig.mjs"; // adjust the path to where the skill lives

const URL = "http://localhost:3000";
const rig = await openRig({ out: "clips" /* , profileDir: "/path/outside/any/repo/profile" */ });

// setup (2nd argument after run) is cut off: load, dismiss banners, scroll after hydration.
const ready = async (page) => {
  await page.goto(URL, { waitUntil: "load" });
  await page.mouse.move(1180, 330); // park the cursor out of the way
  await wait(page, 2000);
};

await rig.clip("s1", async (page) => {
  const btn = page.getByRole("button", { name: /open/i });
  await glide(page, btn, 1200);
  await btn.click();
  await wait(page, 2500); // hold on the result: the viewer needs time to read
}, ready);

await rig.clip("s2", async (page) => {
  const box = page.getByRole("textbox").first();
  await glide(page, box, 900);
  await box.click();
  await typeSlow(box, "How is it doing today?");
  await page.keyboard.press("Enter");
  await page.getByText(/done|ready/i).first().waitFor({ timeout: 120000 }); // wait for the real answer
  await wait(page, 2500);
}, ready);

await rig.done();
