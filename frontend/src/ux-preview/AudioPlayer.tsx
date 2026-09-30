import { useEffect, useRef, useState } from "react";
import {
  DownloadSimple,
  Pause,
  Play,
  SpeakerHigh,
  SpinnerGap,
} from "@phosphor-icons/react";
import { ApiError } from "../data/api";
import {
  sourceFiles,
  sourceLabels,
  timeLabel,
  type MediaProvider,
  type SourceKind,
} from "./domain";
import { decodeWav, type AudioSignal } from "./signal";
import type { Playback } from "./usePlayback";
import { Button, Notice } from "./primitives";
import { Waveform } from "./SignalChart";

export function AudioPlayer({
  source,
  resourceId,
  provider,
  playback,
  gain,
  setGain,
  onLoaded,
}: {
  source: SourceKind;
  resourceId: string;
  provider: MediaProvider;
  playback: Playback;
  gain: number;
  setGain: (value: number) => void;
  onLoaded: (source: SourceKind, signal: AudioSignal) => void;
}) {
  const [signal, setSignal] = useState<AudioSignal | null>(null),
    [url, setUrl] = useState(""),
    [error, setError] = useState("");
  const callback = useRef(onLoaded);
  callback.current = onLoaded;
  const pause = useRef(playback.pause);
  pause.current = playback.pause;
  useEffect(() => {
    const controller = new AbortController();
    let allocated = "";
    setSignal(null);
    setError("");
    setUrl("");
    void provider
      .media(resourceId, controller.signal)
      .then(async (blob) => {
        const decoded = await decodeWav(blob);
        if (controller.signal.aborted) return;
        allocated = URL.createObjectURL(blob);
        setUrl(allocated);
        setSignal(decoded);
        callback.current(source, decoded);
      })
      .catch((failure) => {
        if (controller.signal.aborted) return;
        setError(
          failure instanceof ApiError && failure.status === 401
            ? "Sign in again to listen to this audio."
            : failure instanceof ApiError && [403, 404].includes(failure.status)
              ? "You do not currently have access to this audio."
              : failure instanceof Error
                ? failure.message
                : "This audio could not be loaded.",
        );
      });
    return () => {
      controller.abort();
      pause.current(source);
      if (allocated) URL.revokeObjectURL(allocated);
    };
  }, [provider, resourceId, source]);
  const isPlaying = playback.active === source && playback.playing,
    position = playback.active === source ? playback.position : 0;
  const ready = Boolean(signal);
  return (
    <div
      className={`sf-player sf-player--${source}`}
      aria-label={`${sourceLabels[source]} audio player`}
      data-media-state={error ? "denied-or-error" : ready ? "ready" : "loading"}
    >
      <div className="sf-player-label">
        <strong>{sourceLabels[source]}</strong>
        <span>{source === "original" ? "Mixed audio" : "Component"}</span>
      </div>
      {error ? (
        <Notice danger>{error}</Notice>
      ) : (
        <>
          <div className="sf-player-main">
            <Button
              variant="icon"
              className="sf-play"
              disabled={!ready}
              aria-label={`${isPlaying ? "Pause" : "Play"} ${sourceLabels[source]}`}
              aria-pressed={isPlaying}
              onClick={() => {
                if (isPlaying) playback.pause();
                else if (signal) void playback.play(source, signal, position);
              }}
            >
              {!ready ? (
                <SpinnerGap size={24} />
              ) : isPlaying ? (
                <Pause size={21} weight="fill" />
              ) : (
                <Play size={21} weight="fill" />
              )}
            </Button>
            <div className="sf-timeline">
              {signal ? (
                <Waveform samples={signal.samples} source={source} />
              ) : (
                <div className="sf-audio-skeleton" aria-hidden="true" />
              )}
              <input
                type="range"
                aria-label={`Seek ${sourceLabels[source]}`}
                min={0}
                max={signal?.duration || 15}
                step={0.05}
                value={position}
                disabled={!ready}
                onChange={(e) => {
                  if (signal)
                    playback.seek(source, signal, Number(e.target.value));
                }}
              />
              <div className="sf-time">
                <time>{timeLabel(position)}</time>
                <time>{timeLabel(signal?.duration || 15)}</time>
              </div>
            </div>
            <div className="sf-gain">
              <label htmlFor={`gain-${source}`}>
                <SpeakerHigh size={15} />
                <span>{gain}%</span>
              </label>
              <input
                id={`gain-${source}`}
                aria-label={`${sourceLabels[source]} playback gain`}
                type="range"
                min={0}
                max={200}
                step={5}
                value={gain}
                onChange={(e) => setGain(Number(e.target.value))}
              />
              <small>Playback gain</small>
            </div>
          </div>
          <span className="sf-sr" role="status">
            {ready
              ? `${sourceLabels[source]} audio ready. No autoplay.`
              : "Loading audio…"}
          </span>
        </>
      )}
      <a
        href={url || undefined}
        download={sourceFiles[source]}
        aria-label={`Download synthetic ${source}`}
        className={`sf-icon-link sf-player-download ${!url ? "is-disabled" : ""}`}
        tabIndex={url ? 0 : -1}
      >
        <DownloadSimple size={17} />
      </a>
    </div>
  );
}
