import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { previewIdentity, handleError } from "./domain";
import { readPreference, writePreference } from "./preferences";

type Identity = {
  name: string;
  handle: string;
  publicId: string;
  handleUsed: boolean;
  photo: string;
};
const IdentityContext = createContext<{
  identity: Identity;
  saveIdentity: (name: string, handle: string) => void;
  savePhoto: (url: string) => void;
} | null>(null);

/** Non-production preview identity; the authoritative UID is never replaced. */
export function PreviewIdentityProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentity] = useState<Identity>(() => {
    const candidate = readPreference("handle", previewIdentity.handle);
    const name = readPreference("name", previewIdentity.name)
      .trim()
      .slice(0, 64);
    return {
      ...previewIdentity,
      name: name || previewIdentity.name,
      handle: handleError(candidate) ? previewIdentity.handle : candidate,
      handleUsed: readPreference("handle-used", "false") === "true",
      photo: "",
    };
  });
  const photo = useRef("");
  useEffect(
    () => () => {
      if (photo.current) URL.revokeObjectURL(photo.current);
    },
    [],
  );
  function saveIdentity(name: string, handle: string) {
    const normalized = handle.trim().toLowerCase();
    if (identity.handleUsed && normalized !== identity.handle)
      throw new Error("Your handle change has already been used.");
    const handleUsed = identity.handleUsed || normalized !== identity.handle;
    writePreference("name", name.trim());
    writePreference("handle", normalized);
    writePreference("handle-used", String(handleUsed));
    setIdentity((current) => ({
      ...current,
      name: name.trim(),
      handle: normalized,
      handleUsed,
    }));
  }
  function savePhoto(url: string) {
    if (photo.current) URL.revokeObjectURL(photo.current);
    photo.current = url;
    setIdentity((current) => ({ ...current, photo: url }));
  }
  return (
    <IdentityContext.Provider value={{ identity, saveIdentity, savePhoto }}>
      {children}
    </IdentityContext.Provider>
  );
}
export function usePreviewIdentity() {
  const value = useContext(IdentityContext);
  if (!value) throw new Error("Preview identity provider missing.");
  return value;
}
