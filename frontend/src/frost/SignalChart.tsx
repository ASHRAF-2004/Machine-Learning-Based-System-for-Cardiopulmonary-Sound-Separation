import { useEffect, useMemo, useRef } from "react";
import { spectrogram, waveformPeaks, type AudioSignal } from "./signal";
import type { SourceKind } from "./contracts";

export function Waveform({
  samples,
  source,
  compact = false,
}: {
  samples: Float32Array;
  source: SourceKind;
  compact?: boolean;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const peaks = useMemo(
    () => waveformPeaks(samples, compact ? 48 : 240),
    [samples, compact],
  );
  useEffect(() => {
    const canvas = ref.current!;
    const draw = () => {
      const width = Math.max(1, canvas.clientWidth),
        height = canvas.clientHeight,
        ratio = Math.min(devicePixelRatio, 2);
      canvas.width = width * ratio;
      canvas.height = height * ratio;
      const ctx = canvas.getContext("2d")!;
      ctx.scale(ratio, ratio);
      ctx.strokeStyle = getComputedStyle(canvas)
        .getPropertyValue(`--source-${source}`)
        .trim();
      const max = Math.max(...peaks, 0.001);
      ctx.lineWidth = compact ? 1.5 : 1.2;
      ctx.beginPath();
      peaks.forEach((peak, i) => {
        const x = ((i + 0.5) / peaks.length) * width,
          size = Math.max(1, (peak / max) * height * 0.44);
        ctx.moveTo(x, height / 2 - size);
        ctx.lineTo(x, height / 2 + size);
      });
      ctx.stroke();
    };
    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(canvas);
    // Palette changes are signalled without coupling animation to React frames.
    window.addEventListener("sf-theme-change", draw);
    return () => {
      observer.disconnect();
      window.removeEventListener("sf-theme-change", draw);
    };
  }, [peaks, compact, source]);
  return (
    <canvas
      className={`sf-waveform ${compact ? "sf-waveform--compact" : ""}`}
      ref={ref}
      aria-hidden="true"
    />
  );
}

const palette = [
  [15, 34, 40],
  [26, 72, 79],
  [43, 119, 122],
  [114, 177, 152],
  [232, 223, 160],
];
function heat(db: number): string {
  const value = Math.max(0, Math.min(1, (db + 80) / 60)) * 4,
    at = Math.min(3, Math.floor(value)),
    f = value - at;
  return `rgb(${palette[at].map((v, i) => Math.round(v + (palette[at + 1][i] - v) * f)).join(",")})`;
}
export function SignalChart({
  signal,
  source,
  mode,
}: {
  signal: AudioSignal;
  source: SourceKind;
  mode: "spectrogram" | "waveform";
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const spectrum = useMemo(
    () => (mode === "spectrogram" ? spectrogram(signal) : []),
    [signal, mode],
  );
  const peaks = useMemo(() => waveformPeaks(signal.samples), [signal]);
  useEffect(() => {
    const canvas = ref.current!;
    const draw = () => {
      const width = Math.max(1, canvas.clientWidth),
        height = canvas.clientHeight,
        ratio = Math.min(devicePixelRatio, 2);
      canvas.width = width * ratio;
      canvas.height = height * ratio;
      const ctx = canvas.getContext("2d")!;
      ctx.scale(ratio, ratio);
      ctx.fillStyle = "#102228";
      ctx.fillRect(0, 0, width, height);
      if (mode === "spectrogram") {
        spectrum.forEach((column, x) =>
          column.forEach((power, k) => {
            ctx.fillStyle = heat(power);
            ctx.fillRect(
              (x / spectrum.length) * width,
              ((128 - k) / 129) * height,
              Math.ceil(width / spectrum.length) + 1,
              Math.ceil(height / 129) + 1,
            );
          }),
        );
      } else {
        ctx.strokeStyle = "#405b60";
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let i = 1; i < 4; i++) {
          ctx.moveTo(0, (height * i) / 4);
          ctx.lineTo(width, (height * i) / 4);
        }
        ctx.stroke();
        ctx.strokeStyle = getComputedStyle(canvas)
          .getPropertyValue(`--source-${source}-chart`)
          .trim();
        ctx.beginPath();
        // Common absolute ±1 full-scale axis; never imply source normalisation.
        peaks.forEach((v, i) => {
          const x = (i / peaks.length) * width;
          ctx.moveTo(x, height / 2 - (v * height) / 2);
          ctx.lineTo(x, height / 2 + (v * height) / 2);
        });
        ctx.stroke();
      }
    };
    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(canvas);
    window.addEventListener("sf-theme-change", draw);
    return () => {
      observer.disconnect();
      window.removeEventListener("sf-theme-change", draw);
    };
  }, [spectrum, peaks, mode, source]);
  return (
    <figure className="sf-signal-chart">
      <div className="sf-chart-area">
        <div className="sf-y-axis">
          <span>
            {mode === "spectrogram"
              ? `${Number((signal.rate / 2000).toFixed(2))}kHz`
              : "+1"}
          </span>
          <span>
            {mode === "spectrogram"
              ? `${Number((signal.rate / 4000).toFixed(2))}kHz`
              : "0"}
          </span>
          <span>{mode === "spectrogram" ? "0" : "−1"}</span>
        </div>
        <canvas
          ref={ref}
          role="img"
          aria-label={`${source} ${mode}. ${signal.duration} seconds, ${signal.rate} Hz. ${mode === "spectrogram" ? "Frequency runs from zero to Nyquist; colours show single-sided magnitude from minus80 to minus20 dBFS." : "Amplitude uses an absolute full-scale axis."}`}
        />
        {mode === "spectrogram" && (
          <div className="sf-colour-axis">
            <span>−20</span>
            <i />
            <span>−80</span>
          </div>
        )}
      </div>
      <div className="sf-x-axis">
        {Array.from({ length: 6 }, (_, i) => (
          <span key={i}>
            {((i * signal.duration) / 5).toFixed(signal.duration % 5 ? 1 : 0)}s
          </span>
        ))}
      </div>
      <figcaption>
        {mode === "spectrogram"
          ? "Frequency over time · Hann 256 / hop 64 · magnitude dBFS"
          : "Sample amplitude over time · full-scale waveform"}
      </figcaption>
    </figure>
  );
}
