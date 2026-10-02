import { useEffect, useRef, useState } from "react";
import {
  Bell,
  Camera,
  Check,
  GearSix,
  LockSimple,
  Palette,
  ShieldCheck,
  SpeakerHigh,
  UserCircle,
} from "@phosphor-icons/react";
import { handleError, previewIdentity, type Theme } from "./domain";
import {
  Button,
  CopyId,
  GlassPanel,
  Notice,
  ProfileIdentity,
  SectionHeading,
} from "./primitives";
import { usePreviewIdentity } from "./Identity";
import { AvatarCrop, readAvatar } from "./AvatarCrop";
import {
  Appearance,
  AudioSettings,
  Notifications,
  PrivacySettings,
  SecuritySettings,
} from "./SettingsSections";

type Section =
  | "profile"
  | "appearance"
  | "audio"
  | "notifications"
  | "privacy"
  | "security";
export function Settings({
  theme,
  setTheme,
  gain,
  setGain,
  notify,
}: {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  gain: number;
  setGain: (gain: number) => void;
  notify: (message: string) => void;
}) {
  const { identity, saveIdentity, savePhoto } = usePreviewIdentity();
  const [section, setSection] = useState<Section>("profile"),
    [name, setName] = useState(identity.name),
    [handle, setHandle] = useState(identity.handle);
  const savedHandle = identity.handle,
    changed = identity.handleUsed,
    photo = identity.photo;
  const [error, setError] = useState(""),
    [saved, setSaved] = useState(false),
    [crop, setCrop] = useState<ImageBitmap | null>(null);
  const file = useRef<HTMLInputElement>(null),
    mounted = useRef(true);
  useEffect(
    () => () => {
      mounted.current = false;
    },
    [],
  );
  const nav = [
    { id: "profile", label: "Profile", Icon: UserCircle },
    { id: "appearance", label: "Appearance", Icon: Palette },
    { id: "audio", label: "Audio", Icon: SpeakerHigh },
    { id: "notifications", label: "Notifications", Icon: Bell },
    { id: "privacy", label: "Privacy & data", Icon: ShieldCheck },
    { id: "security", label: "Security", Icon: LockSimple },
  ] as const;
  async function avatar(selected?: File) {
    if (!selected) return;
    try {
      const bitmap = await readAvatar(selected);
      if (mounted.current) {
        setCrop(bitmap);
        setError("");
      } else bitmap.close();
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "This image could not be opened.",
      );
    }
    if (file.current) file.current.value = "";
  }
  function save() {
    const issue = handleError(handle);
    if (!name.trim() || name.length > 64 || issue) {
      setError(issue || "Enter a display name, up to 64 characters.");
      return;
    }
    saveIdentity(name, handle);
    setHandle(handle.trim().toLowerCase());
    setError("");
    setSaved(true);
    notify("Profile preview saved locally. No production identity changed.");
  }
  return (
    <>
      <header className="sf-page-heading">
        <div>
          <h1>Make it yours.</h1>
          <p>Your identity, your workspace, your preferences.</p>
        </div>
        <span className="sf-settings-private">
          <ShieldCheck size={18} />
          Personal settings
        </span>
      </header>
      <div className="sf-settings-layout">
        <nav className="sf-settings-nav" aria-label="Settings sections">
          {nav.map(({ id, label, Icon }) => (
            <button
              type="button"
              key={id}
              aria-pressed={section === id}
              onClick={() => {
                setSection(id);
                setSaved(false);
              }}
            >
              <Icon size={19} />
              {label}
            </button>
          ))}
          <p>
            <GearSix size={17} />
            Changes here affect only the design preview.
          </p>
        </nav>
        <GlassPanel className="sf-settings-content">
          {section === "profile" && (
            <>
              <SectionHeading
                title="Your profile"
                description="This is how you’ll appear when you share and review."
              />
              <div className="sf-profile-summary">
                <ProfileIdentity
                  name={name}
                  handle={savedHandle}
                  photo={photo}
                />
                <div className="sf-avatar-actions">
                  <input
                    ref={file}
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    className="sf-sr"
                    tabIndex={-1}
                    onChange={(e) => void avatar(e.target.files?.[0])}
                  />
                  <Button
                    variant="secondary"
                    onClick={() => file.current?.click()}
                  >
                    <Camera size={17} />
                    Change photo
                  </Button>
                  <small>PNG, JPEG or WebP ·2MiB max</small>
                </div>
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  save();
                }}
              >
                <div className="sf-profile-fields">
                  <label className="sf-field">
                    <span>Display name</span>
                    <input
                      maxLength={64}
                      value={name}
                      onChange={(e) => {
                        setName(e.target.value);
                        setSaved(false);
                      }}
                      autoComplete="name"
                    />
                  </label>
                  <label className="sf-field">
                    <span id="public-handle-label">Public handle</span>
                    <div className="sf-handle-input">
                      <span>@</span>
                      <input
                        aria-labelledby="public-handle-label"
                        value={handle}
                        maxLength={20}
                        disabled={changed}
                        aria-describedby="handle-help"
                        onChange={(e) => {
                          setHandle(e.target.value);
                          setSaved(false);
                        }}
                        autoComplete="off"
                      />
                    </div>
                    <small id="handle-help">
                      {changed
                        ? "Your one self-service handle change has been used."
                        : "One self-service change available. Choose a name that feels like you."}
                    </small>
                  </label>
                </div>
                <div className="sf-profile-save">
                  <CopyId value={previewIdentity.publicId} />
                  <Button type="submit">
                    {saved ? <Check size={17} /> : null}
                    {saved ? "Saved in preview" : "Save profile"}
                  </Button>
                </div>
                {error && <Notice danger>{error}</Notice>}
              </form>
              <hr />
              <Appearance theme={theme} setTheme={setTheme} />
              <hr />
              <AudioSettings gain={gain} setGain={setGain} />
              <hr />
              <div className="sf-settings-shortcuts">
                <span>
                  <ShieldCheck size={19} />
                  Your recordings stay yours.
                </span>
                <Button variant="ghost" onClick={() => setSection("privacy")}>
                  Privacy & data →
                </Button>
              </div>
            </>
          )}
          {section === "appearance" && (
            <>
              <Appearance theme={theme} setTheme={setTheme} />
              <Notice>
                System follows your device’s colour preference. Frost and
                Midnight keep their own contrast and chart colours.
              </Notice>
            </>
          )}
          {section === "audio" && (
            <>
              <AudioSettings gain={gain} setGain={setGain} />
              <Notice>
                Above100%, a compressor reduces clipping risk. Start at a
                comfortable level. Files and model outputs are never amplified
                or rewritten.
              </Notice>
            </>
          )}
          {section === "notifications" && <Notifications notify={notify} />}
          {section === "privacy" && (
            <PrivacySettings handle={savedHandle} notify={notify} />
          )}
          {section === "security" && <SecuritySettings />}
        </GlassPanel>
      </div>
      {crop && (
        <AvatarCrop
          image={crop}
          onClose={() => setCrop(null)}
          onSave={savePhoto}
        />
      )}
    </>
  );
}
