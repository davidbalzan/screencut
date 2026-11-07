// Open a real, headed Chrome on <url> with a persistent profile so a PERSON can log in
// (SSO, passkey, Cloudflare Access). The agent never types credentials. Close the window
// when you're logged in; the session stays in <profileDir> for the recordings.
//
//   node login.mjs https://app.example.com ~/.cache/screencut/example-profile
import { chromium } from "patchright";
import { resolve } from "node:path";

const [url, profileDir] = process.argv.slice(2);
if (!url || !profileDir) {
  console.error("usage: node login.mjs <url> <profileDir>");
  process.exit(2);
}
const ctx = await chromium.launchPersistentContext(resolve(profileDir), { channel: "chrome", headless: false, viewport: null });
const page = ctx.pages()[0] ?? (await ctx.newPage());
await page.goto(url);
console.error("Log in in the window, then close it.");
await new Promise((r) => ctx.on("close", r));
console.error(`session saved in ${resolve(profileDir)}`);
