// Optional voice-over (ElevenLabs or Google Cloud TTS, see speech.mjs for auth). Each line is
// generated, transcribed back, and regenerated (up to 3 tries) until the transcript matches and
// the line fits its slot. Keys come from the environment only.
//
//   node voice.mjs <lines.json> <out-dir> [--provider elevenlabs|google] [--stt elevenlabs|google]
//   lines.json: [{ "id": "l1", "text": "Meet Joey.", "voice": "nPczCjzI2devNBz1zQrb", "maxSec": 2.5, "start": 0.4,
//                  "provider": "google", "spoken": "how it should be heard", … }, …]
//   provider: per line > --provider > whichever API key is set. Transcription uses --stt, else the line's provider.
//   google voices: e.g. "en-US-Chirp3-HD-Charon" (default), "en-GB-Chirp3-HD-Algenib"; languageCode is taken from the name.
// Writes <out-dir>/<id>.mp3 and <out-dir>/voice.json = [{file,start,text}] to put under "voice" in video.json.
// Write numbers and acronyms the way they should sound ("Find My R T P", "sixty-two").
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join, resolve } from "node:path";
import { tts, stt, similar, defaultProvider } from "./speech.mjs";

const args = process.argv.slice(2);
const opt = (k) => (args.includes(k) ? args[args.indexOf(k) + 1] : undefined);
const [linesFile, outDir] = args.filter((a, i) => !a.startsWith("--") && !args[i - 1]?.startsWith("--"));
if (!linesFile || !outDir) { console.error("usage: node voice.mjs <lines.json> <out-dir> [--provider elevenlabs|google] [--stt elevenlabs|google]"); process.exit(2); }
mkdirSync(outDir, { recursive: true });
const dur = (f) => Number(execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).toString().trim());

const out = [];
for (const line of JSON.parse(readFileSync(linesFile, "utf8"))) {
  const provider = line.provider ?? opt("--provider") ?? defaultProvider();
  const sttProvider = opt("--stt") ?? provider;
  const file = resolve(join(outDir, `${line.id}.mp3`));
  let ok = false;
  for (let attempt = 1; attempt <= 3 && !ok; attempt++) {
    await tts({ ...line, provider }, file);
    const heard = await stt(file, sttProvider, line.languageCode ?? (provider === "google" && line.voice ? line.voice.split("-").slice(0, 2).join("-") : "en-US"));
    const score = similar(line.spoken ?? line.text, heard), d = dur(file);
    ok = score >= 0.85 && (!line.maxSec || d <= line.maxSec);
    console.error(`${line.id} [${provider}] try ${attempt}: ${d.toFixed(2)} s, match ${(score * 100).toFixed(0)}% — heard "${heard}"${ok ? " ✓" : ""}`);
  }
  if (!ok) console.error(`${line.id}: still off after 3 tries; rewrite the line or widen its slot`);
  out.push({ file, start: line.start ?? 0, text: line.spoken ?? line.text }); // text: check.py hears it back in the final mix
}
writeFileSync(join(outDir, "voice.json"), JSON.stringify(out, null, 2) + "\n");
console.error(`wrote ${join(outDir, "voice.json")}`);
