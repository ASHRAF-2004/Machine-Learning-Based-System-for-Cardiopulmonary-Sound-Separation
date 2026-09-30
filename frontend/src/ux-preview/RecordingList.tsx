import {
  ArrowRight,
  LockSimple,
  ShareNetwork,
  Waveform,
} from "@phosphor-icons/react";
import { CopyId, StatusChip } from "./primitives";
import { timeLabel, type PreviewRecording } from "./domain";

export function RecordingList({
  items,
  compact = false,
}: {
  items: PreviewRecording[];
  compact?: boolean;
}) {
  return (
    <div className={`sf-recordings ${compact ? "sf-recordings--compact" : ""}`}>
      {!compact && (
        <div className="sf-list-head" aria-hidden="true">
          <span>Recording</span>
          <span>Added</span>
          <span>Duration</span>
          <span>Status</span>
          <span>Access</span>
          <span />
        </div>
      )}
      <ul aria-label="Recordings">
        {items.map((item) => (
          <li key={item.id}>
            <div className="sf-recording-title">
              <span className="sf-recording-symbol">
                <Waveform size={22} />
              </span>
              <div>
                <strong>{item.title}</strong>
                <div className="sf-recording-reference">
                  <CopyId value={item.publicId} />
                  {compact && (
                    <span className="sf-compact-date">{item.date}</span>
                  )}
                </div>
              </div>
            </div>
            {!compact && <span className="sf-recording-date">{item.date}</span>}
            <span className="sf-recording-duration">
              {timeLabel(item.duration)}
            </span>
            <StatusChip status={item.status} />
            <span className="sf-recording-access">
              {item.shared ? (
                <ShareNetwork size={15} />
              ) : (
                <LockSimple size={15} />
              )}
              <span>{item.shared ? "Shared" : "Private"}</span>
            </span>
            <a
              href="#recording"
              className="sf-row-action"
              aria-label={`Open representative recording detail for ${item.title}`}
            >
              {compact ? (
                <ArrowRight size={21} />
              ) : (
                <>
                  Open
                  <ArrowRight size={17} />
                </>
              )}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
