import { ApiError } from "../data/api";
import type { MediaProvider, SourceKind } from "./domain";

const RATE = 4000;
const SECONDS = 15;
let cached: Record<SourceKind, Blob> | undefined;

export function encodeWav(samples: Float32Array, rate = RATE): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 4);
  const view = new DataView(buffer);
  const label = (at: number, value: string) => {
    for (let i = 0; i < value.length; i++)
      view.setUint8(at + i, value.charCodeAt(i));
  };
  label(0, "RIFF");
  view.setUint32(4, buffer.byteLength - 8, true);
  label(8, "WAVE");
  label(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 3, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 4, true);
  view.setUint16(32, 4, true);
  view.setUint16(34, 32, true);
  label(36, "data");
  view.setUint32(40, samples.length * 4, true);
  for (let i = 0; i < samples.length; i++)
    view.setFloat32(44 + i * 4, samples[i], true);
  return new Blob([buffer], { type: "audio/wav" });
}

function fixtureAudio(): Record<SourceKind, Blob> {
  if (cached) return cached;
  const heart = new Float32Array(RATE * SECONDS),
    lung = new Float32Array(heart.length);
  const mixture = new Float32Array(heart.length);
  let seed = 9421,
    filtered = 0;
  for (let i = 0; i < heart.length; i++) {
    const t = i / RATE,
      phase = t % 0.84;
    heart[i] =
      0.3 *
        Math.sin(2 * Math.PI * 73 * t) *
        Math.exp(-(((phase - 0.15) / 0.038) ** 2)) +
      0.19 *
        Math.sin(2 * Math.PI * 116 * t) *
        Math.exp(-(((phase - 0.41) / 0.024) ** 2));
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    filtered = 0.45 * filtered + 0.55 * ((seed / 4294967296) * 2 - 1);
    const envelope = 0.035 + 0.1 * (0.5 + 0.5 * Math.sin(t * 1.42)) ** 2;
    lung[i] =
      filtered * envelope +
      0.009 *
        Math.sin(2 * Math.PI * 420 * t) *
        (0.5 + 0.5 * Math.sin(t * 1.42));
    mixture[i] = heart[i] + lung[i];
  }
  cached = {
    original: encodeWav(mixture),
    heart: encodeWav(heart),
    lung: encodeWav(lung),
  };
  return cached;
}

export const fixtureMedia: MediaProvider = {
  async media(id, signal) {
    signal?.throwIfAborted();
    if (id === "denied")
      throw new ApiError(
        403,
        "forbidden",
        "You do not have access to this audio.",
      );
    if (id === "expired")
      throw new ApiError(401, "session_expired", "Sign in again to listen.");
    if (!["original", "heart", "lung"].includes(id))
      throw new ApiError(404, "unavailable", "This audio is unavailable.");
    // Local generation only: no dataset, model, production fetch or patient audio.
    const blob = fixtureAudio()[id as SourceKind];
    signal?.throwIfAborted();
    return blob;
  },
};
