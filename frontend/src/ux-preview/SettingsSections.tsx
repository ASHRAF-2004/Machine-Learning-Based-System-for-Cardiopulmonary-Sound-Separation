import { useEffect, useRef, useState } from "react";
import {
  CheckCircle,
  DownloadSimple,
  EnvelopeSimple,
  LockSimple,
  Moon,
  ShieldCheck,
  SpeakerHigh,
  Sun,
  Trash,
  WarningCircle,
} from "@phosphor-icons/react";
import type { Theme } from "./domain";
import {
  Button,
  GlassPanel,
  Modal,
  Notice,
  SectionHeading,
} from "./primitives";

export function Appearance({
  theme,
  setTheme,
}: {
  theme: Theme;
  setTheme: (value: Theme) => void;
}) {
  const options: { id: Theme; title: string; note: string }[] = [
    { id: "system", title: "System", note: "Follow your device" },
    { id: "frost", title: "Frost", note: "A clear, light workspace" },
    { id: "midnight", title: "Midnight", note: "A calm, low-light workspace" },
  ];
  return (
    <div className="sf-appearance">
      <SectionHeading
        title="Appearance"
        description="Choose how StethoFuse looks on this device."
      />
      <div
        className="sf-theme-options"
        role="group"
        aria-label="Appearance theme"
      >
        {options.map((option) => (
          <button
            key={option.id}
            type="button"
            aria-pressed={theme === option.id}
            onClick={() => setTheme(option.id)}
            className={`sf-theme-option sf-theme-option--${option.id}`}
          >
            <span className="sf-theme-mini">
              <i />
              <span>
                <b />
                <b />
                <b />
              </span>
            </span>
            <span className="sf-theme-option-label">
              {option.id === "midnight" ? (
                <Moon size={17} />
              ) : option.id === "frost" ? (
                <Sun size={17} />
              ) : (
                <span className="sf-system-icon" />
              )}
              <strong>{option.title}</strong>
              {theme === option.id && <CheckCircle size={18} weight="fill" />}
            </span>
            <small>{option.note}</small>
          </button>
        ))}
      </div>
    </div>
  );
}
export function AudioSettings({
  gain,
  setGain,
}: {
  gain: number;
  setGain: (value: number) => void;
}) {
  return (
    <div className="sf-audio-setting">
      <div>
        <SpeakerHigh size={22} />
        <div>
          <h2>Playback, your way.</h2>
          <p>Playback volume up to 200%. Saved files stay unchanged.</p>
        </div>
      </div>
      <label>
        <span>
          Preferred playback gain<strong>{gain}%</strong>
        </span>
        <input
          aria-label="Preferred playback gain"
          aria-valuetext={`${gain} percent${gain > 100 ? ", boost enabled" : ""}`}
          type="range"
          min={0}
          max={200}
          step={5}
          value={gain}
          onChange={(e) => setGain(Number(e.target.value))}
        />
        <small>
          <span>0%</span>
          <span>100%</span>
          <span>200%</span>
        </small>
      </label>
    </div>
  );
}
export function PrivacySettings({
  handle,
  notify,
  compact = false,
}: {
  handle: string;
  notify: (message: string) => void;
  compact?: boolean;
}) {
  const [state, setState] = useState<"idle" | "preparing" | "ready">("idle"),
    [deleting, setDeleting] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  return (
    <div className={`sf-privacy-setting ${compact ? "is-compact" : ""}`}>
      <SectionHeading
        title="Your data belongs to you"
        description={
          !compact
            ? "A copy when you need it. Control when you want it."
            : undefined
        }
      />
      <div className="sf-setting-row">
        <span className="sf-setting-icon">
          <DownloadSimple size={22} />
        </span>
        <div>
          <h3>Export my data</h3>
          <p>
            {state === "idle"
              ? "Prepare a private copy of your recordings and account data."
              : state === "preparing"
                ? "Preparing your export. You can leave and come back."
                : "Your export is ready. Use the protected download when available."}
          </p>
          {state !== "idle" && (
            <small>
              If you don’t see the email, check your spam or junk folder.
            </small>
          )}
        </div>
        <Button
          variant="secondary"
          disabled={state === "preparing"}
          onClick={() => {
            if (state === "ready") {
              notify(
                "Download state previewed. No archive or email is created by this design preview.",
              );
              return;
            }
            setState("preparing");
            timer.current = setTimeout(() => setState("ready"), 1600);
          }}
        >
          {state === "idle"
            ? "Prepare export"
            : state === "preparing"
              ? "Preparing…"
              : "Download"}
        </Button>
      </div>
      <div className="sf-setting-row sf-danger-row">
        <span className="sf-setting-icon">
          <Trash size={21} />
        </span>
        <div>
          <h3>Delete account</h3>
          <p>Permanent removal requires a recent sign-in and confirmation.</p>
        </div>
        <Button variant="danger" onClick={() => setDeleting(true)}>
          Delete account
        </Button>
      </div>
      {!compact && (
        <Notice>
          Local flow prototype only. No archive, email, deletion or backend
          change is performed.
        </Notice>
      )}
      {deleting && (
        <DeleteAccount handle={handle} onClose={() => setDeleting(false)} />
      )}
    </div>
  );
}
function DeleteAccount({
  handle,
  onClose,
}: {
  handle: string;
  onClose: () => void;
}) {
  const [step, setStep] = useState(0),
    [typed, setTyped] = useState("");
  return (
    <Modal
      title={
        step === 0
          ? "Before you delete your account"
          : step === 1
            ? "Confirm it’s you"
            : step === 2
              ? "A final, deliberate confirmation"
              : "Deletion flow preview complete"
      }
      onClose={onClose}
    >
      {step === 0 && (
        <>
          <Notice danger>
            Your account, recordings and owned audio would be removed according
            to the approved retention policy. Access you have shared would end.
          </Notice>
          <h3>Save what you want to keep</h3>
          <p>
            Prepare and download an export first. Completed deletion cannot be
            undone.
          </p>
          <div className="sf-dialog-actions">
            <Button variant="secondary" onClick={onClose}>
              Keep my account
            </Button>
            <Button variant="danger" onClick={() => setStep(1)}>
              Continue to identity check
            </Button>
          </div>
        </>
      )}
      {step === 1 && (
        <>
          <LockSimple size={32} />
          <p>
            The live application must request recent authentication through
            Firebase before continuing. This preview does not collect a
            password.
          </p>
          <Notice>
            No real reauthentication or account mutation takes place.
          </Notice>
          <Button variant="secondary" onClick={() => setStep(2)}>
            Preview successful recent sign-in
          </Button>
        </>
      )}
      {step === 2 && (
        <>
          <p>
            Type <strong>@{handle}</strong> to confirm. You are reviewing a
            local prototype, not deleting a real account.
          </p>
          <label className="sf-field">
            <span>Confirm your handle</span>
            <input
              autoComplete="off"
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              placeholder={`@${handle}`}
            />
          </label>
          <div className="sf-dialog-actions">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={typed !== `@${handle}`}
              onClick={() => setStep(3)}
            >
              Delete account
            </Button>
          </div>
        </>
      )}
      {step === 3 && (
        <>
          <CheckCircle size={34} />
          <p>
            No account was deleted. Luna must implement this flow only after
            visual approval and separate security/retention review.
          </p>
          <Button variant="secondary" onClick={onClose}>
            Close preview
          </Button>
        </>
      )}
    </Modal>
  );
}
export function Notifications({
  notify,
}: {
  notify: (message: string) => void;
}) {
  const [ready, setReady] = useState(true),
    [shared, setShared] = useState(true),
    [email, setEmail] = useState(false);
  return (
    <>
      <SectionHeading
        title="Only the updates you need"
        description="Choose what reaches you. Nothing is sent from this preview."
      />
      {[
        {
          label: "Recording ready",
          note: "When separation finishes",
          checked: ready,
          change: setReady,
        },
        {
          label: "Shared with you",
          note: "When someone grants you access",
          checked: shared,
          change: setShared,
        },
        {
          label: "Email updates",
          note: "Receive the updates you chose by email",
          checked: email,
          change: setEmail,
        },
      ].map((item) => (
        <label className="sf-setting-row" key={item.label}>
          <EnvelopeSimple size={23} />
          <span>
            <strong>{item.label}</strong>
            <small>{item.note}</small>
          </span>
          <input
            type="checkbox"
            role="switch"
            checked={item.checked}
            onChange={(e) => item.change(e.target.checked)}
          />
        </label>
      ))}
      <Button
        variant="secondary"
        onClick={() =>
          notify(
            "Notification states previewed. No server preferences or email settings changed.",
          )
        }
      >
        Save notification preferences
      </Button>
    </>
  );
}
export function SecuritySettings() {
  const [connections, setConnections] = useState(false);
  return (
    <>
      <SectionHeading
        title="Keep your account secure"
        description="Your identity remains protected by the existing sign-in system."
      />
      <div className="sf-setting-row">
        <ShieldCheck size={24} />
        <div>
          <h3>Connected accounts</h3>
          <p>Review Google and email sign-in connections.</p>
        </div>
        <Button variant="secondary" onClick={() => setConnections(true)}>
          Review
        </Button>
      </div>
      <div className="sf-setting-row">
        <LockSimple size={24} />
        <div>
          <h3>Recent sign-in for sensitive changes</h3>
          <p>
            Export access, unlinking and deletion must use the approved security
            flow.
          </p>
        </div>
      </div>
      <Notice>
        <WarningCircle size={17} />
        Handle login is not enabled. Secure email/password and Google sign-in
        remain unchanged.
      </Notice>
      {connections && (
        <Modal title="Connected accounts" onClose={() => setConnections(false)}>
          <p>
            This section will show only the authenticated account’s actual
            Firebase providers.
          </p>
          <GlassPanel>
            <h3>Email & Google</h3>
            <p>
              Unlinking must preserve at least one viable sign-in method and
              require recent authentication. This preview cannot connect or
              unlink a provider.
            </p>
          </GlassPanel>
        </Modal>
      )}
    </>
  );
}
