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
  sourceLabels,
  timeLabel,
  type MediaProvider,
  type SourceKind,
} from "./contracts";
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
  filename,
}: {
  source: SourceKind;
  resourceId: string;
  provider: MediaProvider;
  playback: Playback;
  gain: number;
  setGain: (value: number) => void;
  onLoaded: (source: SourceKind, signal: AudioSignal | null) => void;
  filename?: string;
}) {
  const [signal, setSignal] = useState<AudioSignal | null>(null),
    [url, setUrl] = useState(""),
    [error, setError] = useState("");
  const callback = useRef(onLoaded);
  callback.current = onLoaded;
  const clear = useRef(playback.clear);
  clear.current = playback.clear;
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let allocated = "";
    callback.current(source, null);
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
    let checking = false;
    async function recheck() {
      if (controller.signal.aborted || checking || document.hidden || !provider.checkMedia) return;
      checking = true;
      try { await provider.checkMedia(resourceId, controller.signal); }
      catch (failure) {
        if (controller.signal.aborted) return;
        controller.abort();
        clear.current(source);
        if (allocated) { URL.revokeObjectURL(allocated); allocated = ''; }
        setUrl('');setSignal(null);callback.current(source, null);
        setError(failure instanceof Error ? failure.message : 'Audio access is unavailable.');
      } finally { checking = false; }
    }
    const timer = setInterval(() => void recheck(), 30000);
    window.addEventListener('focus',recheck);
    document.addEventListener('visibilitychange',recheck);
    window.addEventListener('sf-recheck-media',recheck);
    return () => {
      controller.abort();clearInterval(timer);
      window.removeEventListener('focus',recheck);
      document.removeEventListener('visibilitychange',recheck);
      window.removeEventListener('sf-recheck-media',recheck);
      clear.current(source);callback.current(source,null);
      if (allocated) URL.revokeObjectURL(allocated);
    };
  }, [provider, resourceId, source, revision]);
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
        <span>{source === "original" ? "Input audio" : "Component"}</span>
      </div>
      {error ? (
        <><Notice danger>{error}</Notice><Button variant="ghost" onClick={() => setRevision(v => v + 1)}>Retry audio access</Button></>
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
                max={signal?.duration || 0}
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
                <time>{signal ? timeLabel(signal.duration) : "—"}</time>
              </div>
            </div>
            <div className="sf-gain" data-boosted={gain > 100}>
              <label htmlFor={`gain-${source}`} aria-hidden="true">
                <SpeakerHigh size={15} />
                <span className="sf-gain-value">{gain}%</span>
                <span className="sf-gain-boost">Boost</span>
              </label>
              <div className="sf-gain-track">
                <input
                  id={`gain-${source}`}
                  aria-label={`${sourceLabels[source]} playback volume`}
                  aria-valuetext={`${gain} percent${gain > 100 ? ", boost enabled" : ""}`}
                  aria-describedby="sf-playback-help"
                  type="range"
                  min={0}
                  max={200}
                  step={5}
                  value={gain}
                  onChange={(e) => setGain(Number(e.target.value))}
                />
                <div className="sf-gain-scale" aria-hidden="true">
                  <span>0</span><span>100</span><span>200%</span>
                </div>
              </div>
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
        download={filename || `${source}.wav`}
        aria-label={`Download ${sourceLabels[source]}`}
        className={`sf-icon-link sf-player-download ${!url ? "is-disabled" : ""}`}
        tabIndex={url ? 0 : -1}
        aria-disabled={!url}
      >
        <DownloadSimple size={17} />
      </a>
    </div>
  );
}
