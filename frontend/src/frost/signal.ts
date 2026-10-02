export interface AudioSignal {
  samples: Float32Array;
  rate: number;
  channels: number;
  duration: number;
}
export interface SignalMetrics {
  rmsDb: number;
  peakDb: number;
  crestDb: number | null;
  dc: number;
  clipped: number;
  nearSilence: number;
  lowLevel: boolean;
}
const db = (level: number) => 20 * Math.log10(Math.max(1e-8, level));

/** Read bounded PCM/float WAV for display/playback only; no ML preprocessing. */
export async function decodeWav(blob: Blob): Promise<AudioSignal> {
  if (blob.size > 25 * 1024 * 1024)
    throw new Error("This audio is too large to preview.");
  const bytes = await blob.arrayBuffer(),
    view = new DataView(bytes);
  const text = (offset: number, length: number) =>
    String.fromCharCode(...new Uint8Array(bytes, offset, length));
  if (bytes.byteLength < 44 || text(0, 4) !== "RIFF" || text(8, 4) !== "WAVE")
    throw new Error("This WAV could not be read.");
  let format = 0,
    channels = 0,
    rate = 0,
    bits = 0,
    start = 0,
    count = 0,
    block = 0;
  for (let p = 12; p + 8 <= bytes.byteLength; ) {
    const size = view.getUint32(p + 4, true),
      end = p + 8 + size;
    if (end > bytes.byteLength)
      throw new Error("This audio file is incomplete.");
    if (text(p, 4) === "fmt " && size >= 16) {
      format = view.getUint16(p + 8, true);
      channels = view.getUint16(p + 10, true);
      rate = view.getUint32(p + 12, true);
      block = view.getUint16(p + 20, true);
      bits = view.getUint16(p + 22, true);
      // Python's existing upload contract also accepts extensible PCM WAVs.
      // Interpret only its PCM subtype, never an unknown extensible codec.
      if (format === 0xfffe && size >= 40) {
        const pcmSubtype = [1, 0, 0, 0, 0, 0, 16, 0, 128, 0, 0, 170, 0, 56, 155, 113];
        if (pcmSubtype.every((byte, index) => view.getUint8(p + 32 + index) === byte))
          format = 1;
      }
    }
    if (text(p, 4) === "data") {
      start = p + 8;
      count = size;
    }
    p = end + (size % 2);
  }
  if (
    ![1, 2].includes(channels) ||
    rate < 1000 ||
    rate > 192000 ||
    !start ||
    !count ||
    ![8, 16, 24, 32].includes(bits) ||
    (format !== 1 && !(format === 3 && bits === 32)) ||
    block !== (channels * bits) / 8 ||
    count % block || count / block / rate > 120
  )
    throw new Error("This WAV format cannot be displayed. The saved file remains unchanged.");
  const samples = new Float32Array(count / block);
  for (let i = 0; i < samples.length; i++) {
    let sum = 0;
    for (let c = 0; c < channels; c++) {
      const at = start + i * block + (c * bits) / 8;
      const value =
        format === 3
          ? view.getFloat32(at, true)
          : bits === 8
            ? (view.getUint8(at) - 128) / 128
          : bits === 16
            ? view.getInt16(at, true) / 32768
            : bits === 32
              ? view.getInt32(at, true) / 2147483648
              : (view.getUint8(at) |
                  (view.getUint8(at + 1) << 8) |
                  (view.getInt8(at + 2) << 16)) /
                8388608;
      if (!Number.isFinite(value))
        throw new Error("This audio contains unreadable samples.");
      sum += value;
    }
    samples[i] = sum / channels;
  }
  return { samples, rate, channels, duration: samples.length / rate };
}

export function measureSignal({ samples, rate }: AudioSignal): SignalMetrics {
  let square = 0,
    peak = 0,
    sum = 0,
    clipped = 0,
    quiet = 0,
    windows = 0;
  const segment = Math.max(1, Math.round(rate / 4));
  for (let start = 0; start < samples.length; start += segment) {
    const end = Math.min(samples.length, start + segment);
    let energy = 0;
    for (let i = start; i < end; i++) {
      const value = samples[i];
      square += value * value;
      energy += value * value;
      sum += value;
      peak = Math.max(peak, Math.abs(value));
      if (Math.abs(value) >= 0.999) clipped++;
    }
    if (db(Math.sqrt(energy / (end - start))) < -50) quiet++;
    windows++;
  }
  const rms = Math.sqrt(square / samples.length);
  return {
    rmsDb: db(rms),
    peakDb: db(peak),
    crestDb: rms === 0 ? null : db(peak) - db(rms),
    dc: sum / samples.length,
    clipped,
    nearSilence: quiet / windows,
    lowLevel: db(rms) < -35,
  };
}

export function waveformPeaks(samples: Float32Array, bins = 240): number[] {
  return Array.from({ length: bins }, (_, index) => {
    let peak = 0;
    for (
      let i = Math.floor((index * samples.length) / bins);
      i < Math.floor(((index + 1) * samples.length) / bins);
      i++
    )
      peak = Math.max(peak, Math.abs(samples[i]));
    return peak;
  });
}

/** Display STFT: periodic Hann256, hop64; bounded columns span the complete file. */
export function spectrogram(
  signal: AudioSignal,
  maxColumns = 180,
): Float32Array[] {
  const N = 256,
    frames = Math.max(1, Math.floor((signal.samples.length - N) / 64) + 1);
  const columns = Math.min(maxColumns, frames),
    window = Array.from(
      { length: N },
      (_, n) => 0.5 - 0.5 * Math.cos((2 * Math.PI * n) / N),
    );
  return Array.from({ length: columns }, (_, column) => {
    const offset =
      Math.round((column * (frames - 1)) / Math.max(1, columns - 1)) * 64;
    const real = new Float64Array(N),
      imaginary = new Float64Array(N);
    for (let n = 0; n < N; n++) {
      let reversed = 0,
        v = n;
      for (let bit = 0; bit < 8; bit++) {
        reversed = reversed * 2 + (v & 1);
        v >>= 1;
      }
      real[reversed] = (signal.samples[offset + n] || 0) * window[n];
    }
    for (let size = 2; size <= N; size *= 2) {
      for (let start = 0; start < N; start += size) {
        for (let n = 0; n < size / 2; n++) {
          const a = start + n,
            b = a + size / 2,
            angle = (-2 * Math.PI * n) / size;
          const r = real[b] * Math.cos(angle) - imaginary[b] * Math.sin(angle);
          const im = real[b] * Math.sin(angle) + imaginary[b] * Math.cos(angle);
          real[b] = real[a] - r;
          imaginary[b] = imaginary[a] - im;
          real[a] += r;
          imaginary[a] += im;
        }
      }
    }
    return Float32Array.from({ length: 129 }, (_, k) =>
      db((Math.hypot(real[k], imaginary[k]) / 128) * (k && k < 128 ? 2 : 1)),
    );
  });
}
