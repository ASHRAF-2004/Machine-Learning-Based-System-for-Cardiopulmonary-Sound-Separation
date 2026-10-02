import {
  Bell,
  ChartBar,
  FolderSimple,
  GearSix,
  House,
  List,
  MagnifyingGlass,
  Moon,
  Question,
  ShareNetwork,
  ShieldCheck,
  Sun,
  X,
} from "@phosphor-icons/react";
import { useEffect, type ReactNode } from "react";
import { Button, Modal, ProfileIdentity } from "./primitives";
import { type Screen } from "./domain";
import { usePreviewIdentity } from "./Identity";

export function navigate(screen: Screen) {
  window.location.hash = screen;
}
export function PreviewShell({
  screen,
  children,
  dark,
  toggleTheme,
  toast,
  notify,
  drawer,
  setDrawer,
  environmentNotice,
}: {
  screen: Screen;
  children: ReactNode;
  dark: boolean;
  toggleTheme: () => void;
  toast: string;
  notify: (message: string) => void;
  drawer: boolean;
  setDrawer: (value: boolean) => void;
  environmentNotice?: ReactNode;
}) {
  const { identity: previewIdentity } = usePreviewIdentity();
  const labels: Record<Screen, string> = {
    overview: "Overview",
    library: "Library",
    recording: "Recording",
    settings: "Profile & settings",
  };
  function search() {
    navigate("library");
    requestAnimationFrame(() =>
      requestAnimationFrame(() =>
        document.querySelector<HTMLInputElement>("#library-search")?.focus(),
      ),
    );
  }
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        search();
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  const links = (
    <>
      <a
        href="#overview"
        aria-current={screen === "overview" ? "page" : undefined}
        onClick={() => setDrawer(false)}
      >
        <House size={21} />
        Overview
      </a>
      <a
        href="#library"
        aria-current={
          screen === "library" || screen === "recording" ? "page" : undefined
        }
        onClick={() => setDrawer(false)}
      >
        <FolderSimple size={21} />
        Library<span className="sf-nav-count">8</span>
      </a>
      <button
        type="button"
        onClick={() => {
          setDrawer(false);
          notify(
            "Shared & assigned is specified in the handoff. This preview proves four screens only.",
          );
        }}
      >
        <ShareNetwork size={21} />
        Shared & assigned
        <span className="sf-nav-dot" />
      </button>
      <button
        type="button"
        onClick={() => {
          setDrawer(false);
          navigate("recording");
          document
            .querySelector("#analysis")
            ?.scrollIntoView({ block: "center" });
        }}
      >
        <ChartBar size={21} />
        Insights
      </button>
    </>
  );
  return (
    <div className="sf-app">
      <a
        href="#sf-main"
        className="sf-skip"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("sf-main")?.focus();
        }}
      >
        Skip to content
      </a>
      <aside className="sf-sidebar">
        <a
          href="#overview"
          className="sf-logo"
          aria-label="StethoFuse Overview"
        >
          <img
            src="/assets/logo.svg"
            width={185}
            height={49}
            alt="StethoFuse"
          />
        </a>
        <div className="sf-workspace-label">Personal workspace</div>
        <nav aria-label="Main navigation">{links}</nav>
        <div className="sf-sidebar-bottom">
          <div className="sf-private-note">
            <ShieldCheck size={22} />
            <span>Private workspace</span>
          </div>
          <nav aria-label="Personal navigation">
            <a
              href="#settings"
              aria-current={screen === "settings" ? "page" : undefined}
            >
              <GearSix size={21} />
              Profile & settings
            </a>
            <button
              type="button"
              onClick={() =>
                notify(
                  "Separate sounds, then listen and review. No diagnosis or per-recording accuracy score is provided.",
                )
              }
            >
              <Question size={21} />
              Help
            </button>
          </nav>
          <a href="#settings" className="sf-sidebar-account">
            <ProfileIdentity
              name={previewIdentity.name}
              handle={previewIdentity.handle}
              photo={previewIdentity.photo}
              compact
            />
            <span className="sf-role">Healthcare staff</span>
          </a>
        </div>
      </aside>
      <div className="sf-main-column">
        <header className="sf-topbar">
          <Button
            variant="icon"
            className="sf-mobile-menu"
            aria-label="Open navigation"
            onClick={() => setDrawer(true)}
          >
            <List size={23} />
          </Button>
          <div className="sf-location">
            <span>Workspace</span>
            <span>/</span>
            {screen === "recording" && (
              <>
                <a href="#library">Library</a>
                <span>/</span>
              </>
            )}
            <strong>{labels[screen]}</strong>
          </div>
          <div className="sf-topbar-actions">
            <Button
              variant="ghost"
              className="sf-search-shortcut"
              onClick={search}
            >
              <MagnifyingGlass size={18} />
              <span>Find a recording</span>
              <kbd>⌘ K</kbd>
            </Button>
            <Button
              variant="icon"
              aria-label={
                dark ? "Switch to Frost theme" : "Switch to Midnight theme"
              }
              onClick={toggleTheme}
            >
              {dark ? <Sun size={20} /> : <Moon size={20} />}
            </Button>
            <Button
              variant="icon"
              aria-label="Notifications"
              onClick={() =>
                notify(
                  "One recording is processing. You can leave and return to your Library.",
                )
              }
            >
              <Bell size={20} />
              <span className="sf-notification-dot" />
            </Button>
            <a
              href="#settings"
              aria-label="Open your profile"
              className="sf-header-avatar"
            >
              {previewIdentity.photo ? (
                <img src={previewIdentity.photo} alt="" />
              ) : (
                previewIdentity.name
                  .split(/\s+/)
                  .map((word) => word[0])
                  .slice(0, 2)
                  .join("")
              )}
            </a>
          </div>
        </header>
        {environmentNotice}
        <main id="sf-main" className="sf-main" tabIndex={-1}>
          {children}
        </main>
        <footer className="sf-footer">
          <span>Listen further.</span>
          <p>Separation supports review. Not a diagnostic system.</p>
          <span>StethoFuse</span>
        </footer>
      </div>
      <nav className="sf-mobile-nav" aria-label="Mobile quick navigation">
        <a
          href="#overview"
          aria-current={screen === "overview" ? "page" : undefined}
        >
          <House size={22} />
          Overview
        </a>
        <a
          href="#library"
          aria-current={
            ["library", "recording"].includes(screen) ? "page" : undefined
          }
        >
          <FolderSimple size={22} />
          Library
        </a>
        <a
          href="#settings"
          aria-current={screen === "settings" ? "page" : undefined}
        >
          <GearSix size={22} />
          Profile
        </a>
        <button type="button" onClick={() => setDrawer(true)}>
          <List size={22} />
          More
        </button>
      </nav>
      {drawer && (
        <Modal
          title="Your workspace"
          className="sf-nav-dialog"
          onClose={() => setDrawer(false)}
        >
          <nav>
            {links}
            <a href="#settings" onClick={() => setDrawer(false)}>
              <GearSix size={21} />
              Profile & settings
            </a>
          </nav>
          <Button variant="secondary" onClick={() => setDrawer(false)}>
            <X size={18} />
            Close navigation
          </Button>
        </Modal>
      )}
      {toast && (
        <div className="sf-toast" role="status">
          {toast}
        </div>
      )}
    </div>
  );
}
