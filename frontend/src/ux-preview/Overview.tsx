import {
  ArrowRight,
  Check,
  Circle,
  Clock,
  Plus,
  ShareNetwork,
  SpinnerGap,
} from "@phosphor-icons/react";
import { Button, GlassPanel, SectionHeading, StatusChip } from "./primitives";
import { recordings } from "./domain";
import { RecordingList } from "./RecordingList";
import { PreviewOwl } from "./PreviewOwl";
import { usePreviewIdentity } from "./Identity";
import botanicalPerch from "./assets/botanical-perch.webp";

export function Overview({ onNew }: { onNew: () => void }) {
  const { identity } = usePreviewIdentity();
  return (
    <>
      <header className="sf-page-heading sf-greeting">
        <div>
          <p className="sf-date">Wednesday, 30 September</p>
          <h1>Good morning, {identity.name.split(" ")[0]}.</h1>
          <p>A clear place for every recording.</p>
          <Button onClick={onNew}>
            <Plus size={20} />
            New recording
          </Button>
        </div>
        <div className="sf-greeting-art" aria-hidden="true">
          <img
            className="sf-botanical-perch"
            src={botanicalPerch}
            alt=""
            width={1774}
            height={887}
          />
          <PreviewOwl />
        </div>
      </header>
      <GlassPanel className="sf-progress-panel">
        <div>
          <div className="sf-progress-title">
            <span className="sf-progress-icon">
              <SpinnerGap size={22} />
            </span>
            <div>
              <h2>One recording in progress</h2>
              <p>
                Quiet-room recording <span>·22s</span>
              </p>
            </div>
          </div>
          <p className="sf-progress-copy">
            You can leave this page. Your result will be waiting here.
          </p>
        </div>
        <ol className="sf-progress-steps" aria-label="Recording progress">
          <li className="is-complete">
            <span>
              <Check size={17} />
            </span>
            <strong>Recorded</strong>
            <small>Saved privately</small>
          </li>
          <li className="is-current" aria-current="step">
            <span>
              <SpinnerGap size={18} />
            </span>
            <strong>Processing</strong>
            <small>Separating sounds</small>
          </li>
          <li>
            <span>
              <Circle size={17} />
            </span>
            <strong>Ready</strong>
            <small>Next: listen & review</small>
          </li>
        </ol>
        <a
          href="#library"
          className="sf-progress-link"
          aria-label="View processing recording in Library"
        >
          <ArrowRight size={21} />
        </a>
      </GlassPanel>
      <div className="sf-overview-grid">
        <GlassPanel className="sf-recent-panel">
          <SectionHeading
            title="Recent recordings"
            description="From first capture to a closer listen."
            action={
              <a className="sf-text-link" href="#library">
                View library
                <ArrowRight size={16} />
              </a>
            }
          />
          <RecordingList compact items={recordings.slice(0, 4)} />
          <div className="sf-recent-footer">
            <Clock size={16} />
            <span>Your complete recording history stays in the Library.</span>
          </div>
        </GlassPanel>
        <div className="sf-overview-rail">
          <GlassPanel className="sf-attention-panel">
            <SectionHeading title="Shared with you" />
            <div className="sf-shared-icon">
              <ShareNetwork size={25} />
            </div>
            <h3>A second pair of ears</h3>
            <p>Maya shared a reference recording for your review.</p>
            <div className="sf-shared-recording">
              <strong>Seated listening session</strong>
              <span>@wintercedar ·30s</span>
              <StatusChip status="ready" />
            </div>
            <a href="#recording" className="sf-text-link">
              Open recording
              <ArrowRight size={17} />
            </a>
          </GlassPanel>
          <div className="sf-week-summary">
            <h2>Your week, at a glance.</h2>
            <div>
              <span>
                <strong>6</strong> recordings this week
              </span>
              <span>
                <strong>4</strong> ready to review
              </span>
            </div>
            <p>Your completed and unfinished work, kept together.</p>
          </div>
        </div>
      </div>
    </>
  );
}
