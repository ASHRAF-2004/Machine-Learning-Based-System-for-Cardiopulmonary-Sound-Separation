import { useEffect, useRef, useState } from "react";
import type { AudioSignal } from "./signal";

export function usePlayback(gainPercent: number) {
  const context = useRef<AudioContext | null>(null),
    node = useRef<AudioBufferSourceNode | null>(null);
  const gain = useRef<GainNode | null>(null),
    compressor = useRef<DynamicsCompressorNode | null>(null);
  const current = useRef<{
    id: string;
    signal: AudioSignal;
    offset: number;
    started: number;
  } | null>(null);
  const [active, setActive] = useState(""),
    [playing, setPlaying] = useState(false),
    [position, setPosition] = useState(0),
    [error, setError] = useState("");
  const playingRef = useRef(false),
    generation = useRef(0);

  function stopNode() {
    if (node.current) {
      node.current.onended = null;
      node.current.stop();
      node.current.disconnect();
      node.current = null;
    }
    playingRef.current = false;
    setPlaying(false);
  }
  function pause(id?: string) {
    if (id && current.current?.id !== id) return;
    generation.current++;
    if (current.current && playingRef.current) {
      current.current.offset = Math.min(
        current.current.signal.duration,
        current.current.offset +
          context.current!.currentTime -
          current.current.started,
      );
      setPosition(current.current.offset);
    }
    stopNode();
  }
  function applyGain(percent: number) {
    const audio = context.current,
      g = gain.current,
      comp = compressor.current;
    if (!audio || !g || !comp) return;
    g.gain.setTargetAtTime(percent / 100, audio.currentTime, 0.02);
    g.disconnect();
    comp.disconnect();
    if (percent > 100) {
      g.connect(comp);
      comp.connect(audio.destination);
    } else g.connect(audio.destination);
  }
  function clear(id?: string) {
    if (id && current.current?.id !== id) return;
    pause(id);
    current.current = null;
    setActive('');
    setPosition(0);
  }
  async function play(
    id: string,
    signal: AudioSignal,
    offset = current.current?.id === id ? current.current.offset : 0,
  ) {
    pause();
    const epoch = ++generation.current;
    setError("");
    try {
      const audio = context.current || new AudioContext();
      context.current = audio;
      if (!gain.current) {
        gain.current = audio.createGain();
        compressor.current = audio.createDynamicsCompressor();
        compressor.current.threshold.value = -3;
        compressor.current.knee.value = 6;
        compressor.current.ratio.value = 20;
        compressor.current.attack.value = 0.003;
        compressor.current.release.value = 0.15;
      }
      await audio.resume();
      if (generation.current !== epoch) return;
      const buffer = audio.createBuffer(1, signal.samples.length, signal.rate);
      buffer.copyToChannel(new Float32Array(signal.samples), 0);
      const source = audio.createBufferSource();
      source.buffer = buffer;
      source.connect(gain.current!);
      const start = offset >= signal.duration ? 0 : Math.max(0, offset);
      current.current = {
        id,
        signal,
        offset: start,
        started: audio.currentTime,
      };
      node.current = source;
      applyGain(gainPercent);
      source.start(0, start);
      playingRef.current = true;
      setActive(id);
      setPosition(start);
      setPlaying(true);
      source.onended = () => {
        if (node.current !== source) return;
        node.current = null;
        source.disconnect();
        playingRef.current = false;
        setPlaying(false);
        setPosition(signal.duration);
        if (current.current) current.current.offset = signal.duration;
      };
    } catch {
      if (generation.current !== epoch) return;
      stopNode();
      setError(
        "Playback could not start. Check your browser audio permissions and try again.",
      );
    }
  }
  function seek(id: string, signal: AudioSignal, seconds: number) {
    const wasPlaying = playingRef.current && current.current?.id === id;
    pause();
    current.current = { id, signal, offset: seconds, started: 0 };
    setActive(id);
    setPosition(seconds);
    if (wasPlaying) void play(id, signal, seconds);
  }
  useEffect(() => applyGain(gainPercent), [gainPercent]);
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => {
      const item = current.current;
      if (item)
        setPosition(
          Math.min(
            item.signal.duration,
            item.offset + context.current!.currentTime - item.started,
          ),
        );
    }, 100);
    return () => clearInterval(timer);
  }, [playing]);
  useEffect(
    () => () => {
      generation.current++;
      if (node.current) {
        node.current.onended = null;
        node.current.stop();
        node.current.disconnect();
      }
      gain.current?.disconnect();
      compressor.current?.disconnect();
      void context.current?.close();
    },
    [],
  );
  return { active, playing, position, error, play, pause, seek, clear };
}
export type Playback = ReturnType<typeof usePlayback>;
