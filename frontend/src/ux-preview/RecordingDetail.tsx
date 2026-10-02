import { useCallback, useMemo, useState } from "react";
import {
  CheckCircle,
  Clock,
  DotsThree,
  Info,
  LockSimple,
  ShareNetwork,
  ShieldCheck,
  SpeakerHigh,
  WarningCircle,
  Waveform,
} from "@phosphor-icons/react";
import { AudioPlayer } from "./AudioPlayer";
import { fixtureMedia } from "./fixtures";
import { sourceLabels, type SourceKind } from "./domain";
import { measureSignal, type AudioSignal } from "./signal";
import { usePlayback } from "./usePlayback";
import { SignalChart } from "./SignalChart";
import { ShareDialog } from "./Sharing";
import {
  Button,
  CopyId,
  GlassPanel,
  MetricCard,
  Notice,
  SectionHeading,
  Segments,
  StatusChip,
} from "./primitives";

export function RecordingDetail({
  gain,
  setGain,
  notify,
}: {
  gain: number;
  setGain: (value: number) => void;
  notify: (message: string) => void;
}) {
  const [source, setSource] = useState<SourceKind>("original"),
    [mode, setMode] = useState<"spectrogram" | "waveform">("spectrogram");
  const [signals, setSignals] = useState<
      Partial<Record<SourceKind, AudioSignal>>
    >({}),
    [share, setShare] = useState(false);
  const playback = usePlayback(gain),
    signal = signals[source];
  const onLoaded = useCallback(
    (kind: SourceKind, value: AudioSignal) =>
      setSignals((current) => ({ ...current, [kind]: value })),
    [],
  );
  const metrics = useMemo(
    () => (signal ? measureSignal(signal) : null),
    [signal],
  );
  const permissionState = new URLSearchParams(location.search).get(
    "mediaState",
  );
  return (
    <>
      <header className="sf-page-heading sf-detail-heading">
        <div>
          <h1>Morning sound study</h1>
          <div className="sf-detail-meta">
            <CopyId value="REC-4MT7-Q2P8KF" />
            <StatusChip status="ready" />
            <span>30 Sep 2026, 08:14</span>
            <span>
              <LockSimple size={14} />
              Private
            </span>
          </div>
        </div>
        <div className="sf-heading-actions">
          <Button variant="secondary" onClick={() => setShare(true)}>
            <ShareNetwork size={19} />
            Share
          </Button>
          <Button
            variant="icon"
            aria-label="Recording actions"
            onClick={() =>
              notify(
                "Download individual synthetic WAVs from each player. Full rename/export actions are specified in the handoff.",
              )
            }
          >
            <DotsThree size={25} />
          </Button>
        </div>
      </header>
      <div className="sf-detail-grid">
        <div className="sf-detail-main">
          <GlassPanel className="sf-audio-panel" label="Audio workspace">
            <SectionHeading
              title="Listen to the difference"
              description="Original and components, kept together."
              action={<span className="sf-format">15s ·4kHz ·mono</span>}
            />
            <div className="sf-mobile-source">
              <Segments<SourceKind>
                label="Audio source"
                value={source}
                onChange={(value) => {
                  playback.pause();
                  setSource(value);
                }}
                items={[
                  { id: "original", label: "Original" },
                  { id: "heart", label: "Heart" },
                  { id: "lung", label: "Lung" },
                ]}
              />
            </div>
            {(["original", "heart", "lung"] as SourceKind[]).map((kind) => (
              <div
                className="sf-audio-lane"
                key={kind}
                data-selected={source === kind}
              >
                <AudioPlayer
                  key={kind}
                  source={kind}
                  resourceId={
                    kind === "heart" &&
                    ["denied", "expired"].includes(permissionState || "")
                      ? permissionState!
                      : kind
                  }
                  provider={fixtureMedia}
                  playback={playback}
                  gain={gain}
                  setGain={setGain}
                  onLoaded={onLoaded}
                />
              </div>
            ))}
            <div className="sf-playback-note">
              <SpeakerHigh size={15} />
              <span id="sf-playback-help">
                Playback volume up to 200%. Saved files stay unchanged.
              </span>
            </div>
            {playback.error && <Notice danger>{playback.error}</Notice>}
          </GlassPanel>
          <GlassPanel
            className="sf-analysis-panel"
            label="Technical signal analysis"
          >
            <div className="sf-analysis-heading" id="analysis">
              <h2>Look closer</h2>
              <Segments
                label="Analysis view"
                value={mode}
                onChange={setMode}
                items={[
                  { id: "waveform", label: "Waveform" },
                  { id: "spectrogram", label: "Spectrogram" },
                ]}
              />
            </div>
            <div className="sf-analysis-subhead">
              <Segments<SourceKind>
                label="Analysis source"
                value={source}
                onChange={setSource}
                items={[
                  { id: "original", label: "Original" },
                  { id: "heart", label: "Heart" },
                  { id: "lung", label: "Lung" },
                ]}
              />
              <span>
                <Info size={14} />
                Technical measurements, not diagnosis
              </span>
            </div>
            {signal ? (
              <SignalChart signal={signal} source={source} mode={mode} />
            ) : (
              <div className="sf-chart-loading" role="status">
                <Waveform size={24} />
                Loading audio for analysis…
              </div>
            )}
          </GlassPanel>
        </div>
        <aside className="sf-detail-rail">
          <GlassPanel className="sf-quality-panel">
            <SectionHeading
              title="Signal checks"
              description={`${sourceLabels[source]} audio`}
            />
            {metrics ? (
              <>
                <ul className="sf-quality-list">
                  <li>
                    {metrics.lowLevel ? (
                      <WarningCircle
                        className="sf-check-warning"
                        size={21}
                        weight="fill"
                      />
                    ) : (
                      <CheckCircle size={21} weight="fill" />
                    )}
                    <div>
                      <strong>
                        {metrics.lowLevel
                          ? "Low signal level"
                          : "Usable signal level"}
                      </strong>
                      <span>
                        {metrics.lowLevel
                          ? "Consider playback boost"
                          : "Above the −35dBFS review threshold"}
                      </span>
                    </div>
                  </li>
                  <li>
                    {metrics.clipped ? (
                      <WarningCircle
                        className="sf-check-warning"
                        size={21}
                        weight="fill"
                      />
                    ) : (
                      <CheckCircle size={21} weight="fill" />
                    )}
                    <div>
                      <strong>
                        {metrics.clipped
                          ? "Clipping to review"
                          : "No clipping detected"}
                      </strong>
                      <span>
                        {metrics.clipped} samples at |amplitude|≥0.999
                      </span>
                    </div>
                  </li>
                  <li>
                    <Clock size={21} />
                    <div>
                      <strong>{signal!.duration.toFixed(1)} seconds</strong>
                      <span>
                        {(signal!.rate / 1000).toFixed(0)}kHz ·{" "}
                        {signal!.channels === 1
                          ? "Mono"
                          : "Stereo downmix for display"}
                      </span>
                    </div>
                  </li>
                </ul>
                <dl className="sf-measurements">
                  <MetricCard
                    label="RMS level"
                    value={`${metrics.rmsDb.toFixed(1)} dBFS`}
                  />
                  <MetricCard
                    label="Peak level"
                    value={`${metrics.peakDb.toFixed(1)} dBFS`}
                  />
                  <MetricCard
                    label="Crest factor"
                    value={`${metrics.crestDb.toFixed(1)} dB`}
                  />
                </dl>
                <details className="sf-check-rules">
                  <summary>How checks are measured</summary>
                  <p>
                    Low level: RMS below−35dBFS. Clipping: |sample|≥0.999.
                    Near-silence:250ms windows below−50dBFS. These are technical
                    checks, not clinical judgments.
                  </p>
                  <p>
                    Near-silence {(metrics.nearSilence * 100).toFixed(1)}% · DC
                    offset {metrics.dc.toFixed(5)}.
                  </p>
                </details>
              </>
            ) : (
              <p className="sf-subtle">
                Measurements appear when the audio loads.
              </p>
            )}
          </GlassPanel>
          <GlassPanel className="sf-share-panel">
            <ShieldCheck size={27} />
            <h2>Private, by default.</h2>
            <p>
              Share only what someone needs. Access to one sound does not unlock
              the others.
            </p>
            <Button variant="secondary" onClick={() => setShare(true)}>
              <ShareNetwork size={18} />
              Share with @username
            </Button>
          </GlassPanel>
          <details className="sf-technical">
            <summary>Technical details</summary>
            <dl>
              <dt>Fixture files</dt>
              <dd>M0001 / H0001 / L0001.wav</dd>
              <dt>Samples per source</dt>
              <dd>60,000 at4kHz</dd>
              <dt>Model contract</dt>
              <dd>Frozen HLS-only T8v2</dd>
              <dt>Preview processing</dt>
              <dd>Generated locally, no ML executed</dd>
              <dt>Semantics</dt>
              <dd>Heart, then lung</dd>
            </dl>
            <p>
              Only an actual job may present its persisted provenance. This
              local result is a visual fixture.
            </p>
          </details>
        </aside>
      </div>
      {share && <ShareDialog onClose={() => setShare(false)} notify={notify} />}
    </>
  );
}
