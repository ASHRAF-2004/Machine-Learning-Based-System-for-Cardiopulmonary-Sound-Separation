import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Microphone, UploadSimple } from "@phosphor-icons/react";
import { Overview } from "./Overview";
import { Library } from "./Library";
import { RecordingDetail } from "./RecordingDetail";
import { Settings } from "./Settings";
import { PreviewShell } from "./Shell";
import { Button, Modal, Notice } from "./primitives";
import { useGain, useTheme } from "./preferences";
import type { Screen } from "./domain";
import { PreviewIdentityProvider } from "./Identity";
import "./tokens.css";
import "./preview.css";

function currentScreen(): Screen {
  const key = location.hash.slice(1);
  return ["overview", "library", "recording", "settings"].includes(key)
    ? (key as Screen)
    : "overview";
}
function PreviewApp() {
  const [screen, setScreen] = useState<Screen>(currentScreen),
    [toast, setToast] = useState(""),
    [drawer, setDrawer] = useState(false),
    [newRecording, setNewRecording] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const { theme, setTheme, resolved } = useTheme(),
    { gain, setGain } = useGain();
  const notify = (message: string) => {
    clearTimeout(timer.current);
    setToast(message);
    timer.current = setTimeout(() => setToast(""), 5000);
  };
  useEffect(() => {
    const change = () => {
      setScreen(currentScreen());
      setDrawer(false);
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", change);
    return () => {
      window.removeEventListener("hashchange", change);
      clearTimeout(timer.current);
    };
  }, []);
  useEffect(() => {
    document.title = `StethoFuse · ${screen === "recording" ? "Morning sound study" : screen === "settings" ? "Profile & settings" : screen[0].toUpperCase() + screen.slice(1)} · Design preview`;
    document.getElementById("sf-main")?.focus({ preventScroll: true });
  }, [screen]);
  return (
    <PreviewShell
      screen={screen}
      dark={resolved === "midnight"}
      toggleTheme={() =>
        setTheme(resolved === "midnight" ? "frost" : "midnight")
      }
      toast={toast}
      notify={notify}
      drawer={drawer}
      setDrawer={setDrawer}
    >
      {screen === "overview" && (
        <Overview onNew={() => setNewRecording(true)} />
      )}
      {screen === "library" && <Library onNew={() => setNewRecording(true)} />}
      {screen === "recording" && (
        <RecordingDetail gain={gain} setGain={setGain} notify={notify} />
      )}
      {screen === "settings" && (
        <Settings
          theme={theme}
          setTheme={setTheme}
          gain={gain}
          setGain={setGain}
          notify={notify}
        />
      )}
      {newRecording && (
        <Modal
          title="Start a new recording"
          onClose={() => setNewRecording(false)}
        >
          <p>Record now or bring in a WAV you already have.</p>
          <div className="sf-capture-options">
            <Button
              variant="secondary"
              onClick={() =>
                notify(
                  "The existing capture flow will be connected after owner approval. No microphone is opened by this preview.",
                )
              }
            >
              <Microphone size={25} />
              Record audio<small>Use your microphone or input device</small>
            </Button>
            <Button
              variant="secondary"
              onClick={() =>
                notify(
                  "The existing WAV upload flow will be reused. No file is sent from this preview.",
                )
              }
            >
              <UploadSimple size={25} />
              Upload WAV<small>WAV files, up to25MiB</small>
            </Button>
          </div>
          <Notice>
            This design preview contains only generated audio. Capture and
            upload remain in the existing application until approval.
          </Notice>
        </Modal>
      )}
    </PreviewShell>
  );
}
export function mountPreview() {
  createRoot(document.getElementById("root")!).render(
    <PreviewIdentityProvider>
      <PreviewApp />
    </PreviewIdentityProvider>,
  );
}
