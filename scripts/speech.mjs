// Text-to-speech and speech-to-text behind one interface, for voice.mjs and check.py.
//
// Providers
//   elevenlabs  key: ELEVENLABS_API_KEY.  TTS eleven_multilingual_v2, STT scribe_v1.
//   google      Cloud Text-to-Speech + Speech-to-Text (v1). Auth: GOOGLE_API_KEY (an API key
//               restricted to those two APIs), else the gcloud login (`gcloud auth
//               print-access-token`), billed to GOOGLE_CLOUD_PROJECT — set it, or Google bills the
//               gcloud default project, which may be a production one.
// Keys come from the environment only; never as arguments, never in a file.
//
// CLI (used by check.py):  node speech.mjs stt <audio file> <provider> [languageCode]   → prints the transcript
import { readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export const PROVIDERS = ["elevenlabs", "google"];
export const DEFAULT_VOICE = { elevenlabs: "nPczCjzI2devNBz1zQrb", google: "en-US-Chirp3-HD-Charon" };

/** The provider to use when none is named: whichever has an API key in the environment. */
export function defaultProvider() {
  if (process.env.ELEVENLABS_API_KEY) return "elevenlabs";
  if (process.env.GOOGLE_API_KEY) return "google";
  return null;
}

function elevenKey() {
  const k = process.env.ELEVENLABS_API_KEY;
  if (!k) throw new Error("ELEVENLABS_API_KEY is not set");
  return k;
}

let gToken = null;
function google(url) {
  if (process.env.GOOGLE_API_KEY) return { url: `${url}?key=${encodeURIComponent(process.env.GOOGLE_API_KEY)}`, headers: {} };
  if (!gToken) {
    try { gToken = execFileSync("gcloud", ["auth", "print-access-token"], { stdio: ["ignore", "pipe", "ignore"] }).toString().trim(); }
    catch { throw new Error("google: set GOOGLE_API_KEY, or log in with `gcloud auth login`"); }
  }
  const headers = { authorization: `Bearer ${gToken}` };
  if (process.env.GOOGLE_CLOUD_PROJECT) headers["x-goog-user-project"] = process.env.GOOGLE_CLOUD_PROJECT;
  return { url, headers };
}

const langOf = (voice) => voice.split("-").slice(0, 2).join("-"); // "en-US-Chirp3-HD-Charon" → "en-US"

/**
 * Speak one line into an mp3 file.
 * line: { text, provider?, voice?, ssml? (google), languageCode? (google), speakingRate?, pitch? (google, not Chirp 3 HD),
 *         model?, stability?, style? (elevenlabs) }
 */
export async function tts(line, file) {
  const provider = line.provider ?? defaultProvider();
  if (provider === "elevenlabs") {
    const r = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${line.voice ?? DEFAULT_VOICE.elevenlabs}?output_format=mp3_44100_128`, {
      method: "POST",
      headers: { "xi-api-key": elevenKey(), "content-type": "application/json" },
      body: JSON.stringify({ text: line.text, model_id: line.model ?? "eleven_multilingual_v2",
        voice_settings: { stability: line.stability ?? 0.38, similarity_boost: 0.8, style: line.style ?? 0.55, use_speaker_boost: true } }),
    });
    if (!r.ok) throw new Error(`elevenlabs TTS: HTTP ${r.status} ${(await r.text()).slice(0, 200)}`);
    writeFileSync(file, Buffer.from(await r.arrayBuffer()));
  } else if (provider === "google") {
    const voice = line.voice ?? DEFAULT_VOICE.google;
    const audioConfig = { audioEncoding: "MP3", sampleRateHertz: 44100 };
    if (line.speakingRate != null) audioConfig.speakingRate = line.speakingRate;
    if (line.pitch != null) audioConfig.pitch = line.pitch;
    const g = google("https://texttospeech.googleapis.com/v1/text:synthesize");
    const r = await fetch(g.url, {
      method: "POST",
      headers: { ...g.headers, "content-type": "application/json" },
      body: JSON.stringify({ input: line.ssml ? { ssml: line.ssml } : { text: line.text },
        voice: { languageCode: line.languageCode ?? langOf(voice), name: voice }, audioConfig }),
    });
    if (!r.ok) throw new Error(`google TTS: HTTP ${r.status} ${(await r.text()).slice(0, 300)}`);
    writeFileSync(file, Buffer.from((await r.json()).audioContent, "base64"));
  } else {
    throw new Error(`no TTS provider: set "provider" (${PROVIDERS.join(" | ")}) or put an API key in the environment`);
  }
}

/** Transcribe an audio file (any format ffmpeg reads; Google's sync API takes up to 60 s). */
export async function stt(file, provider = defaultProvider(), languageCode = "en-US") {
  if (provider === "elevenlabs") {
    const form = new FormData();
    form.append("model_id", "scribe_v1");
    form.append("file", new Blob([readFileSync(file)]), file.split("/").pop());
    const r = await fetch("https://api.elevenlabs.io/v1/speech-to-text", { method: "POST", headers: { "xi-api-key": elevenKey() }, body: form });
    if (!r.ok) throw new Error(`elevenlabs STT: HTTP ${r.status} ${(await r.text()).slice(0, 200)}`);
    return (await r.json()).text ?? "";
  }
  if (provider === "google") {
    const pcm = execFileSync("ffmpeg", ["-nostdin", "-v", "error", "-i", file, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], { maxBuffer: 1 << 28 });
    if (pcm.length > 16000 * 2 * 59) throw new Error(`google STT: ${file} is over 59 s (sync recognize limit)`);
    const g = google("https://speech.googleapis.com/v1/speech:recognize");
    const r = await fetch(g.url, {
      method: "POST",
      headers: { ...g.headers, "content-type": "application/json" },
      body: JSON.stringify({ config: { encoding: "LINEAR16", sampleRateHertz: 16000, languageCode, enableAutomaticPunctuation: true },
        audio: { content: pcm.toString("base64") } }),
    });
    if (!r.ok) throw new Error(`google STT: HTTP ${r.status} ${(await r.text()).slice(0, 300)}`);
    return ((await r.json()).results ?? []).map((x) => x.alternatives?.[0]?.transcript ?? "").join(" ").trim();
  }
  throw new Error(`no STT provider: name one (${PROVIDERS.join(" | ")}) or put an API key in the environment`);
}

const norm = (s) => s.toLowerCase().replace(/[^\p{L}\p{N} ]/gu, " ").replace(/\s+/g, " ").trim();
/** Share of words in common, 0..1 (order-insensitive, punctuation and case ignored). */
export function similar(a, b) {
  const A = new Set(norm(a).split(" ")), Bw = norm(b).split(" ").filter(Boolean);
  return Bw.filter((w) => A.has(w)).length / Math.max(A.size, Bw.length, 1);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [cmd, file, provider, lang] = process.argv.slice(2);
  if (cmd !== "stt" || !file) { console.error("usage: node speech.mjs stt <audio file> <provider> [languageCode]"); process.exit(2); }
  try { process.stdout.write(await stt(file, provider || defaultProvider(), lang || "en-US")); }
  catch (e) { console.error(e.message); process.exit(1); }
}
