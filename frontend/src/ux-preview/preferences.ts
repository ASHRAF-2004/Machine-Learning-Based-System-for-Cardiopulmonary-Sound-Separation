import { useEffect, useState } from "react";
import type { Theme } from "./domain";

export function readPreference(key: string, fallback: string): string {
  try {
    return localStorage.getItem(`sf-design-${key}`) || fallback;
  } catch {
    return fallback;
  }
}
export function writePreference(key: string, value: string) {
  try {
    localStorage.setItem(`sf-design-${key}`, value);
  } catch {
    /* Non-sensitive preferences can remain session-only. */
  }
}
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    const value = readPreference("theme", "frost");
    return ["frost", "midnight", "system"].includes(value)
      ? (value as Theme)
      : "frost";
  });
  const [systemDark, setSystemDark] = useState(
    () => matchMedia("(prefers-color-scheme: dark)").matches,
  );
  const resolved =
    theme === "system" ? (systemDark ? "midnight" : "frost") : theme;
  useEffect(() => {
    const query = matchMedia("(prefers-color-scheme: dark)");
    const change = () => setSystemDark(query.matches);
    query.addEventListener("change", change);
    return () => query.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = resolved;
    document.documentElement.style.colorScheme =
      resolved === "midnight" ? "dark" : "light";
    writePreference("theme", theme);
    window.dispatchEvent(new Event("sf-theme-change"));
  }, [theme, resolved]);
  return { theme, setTheme, resolved };
}
export function useGain() {
  const [gain, setGain] = useState(() => {
    const value = Number(readPreference("gain", "100"));
    return Number.isFinite(value) && value >= 0 && value <= 200 ? value : 100;
  });
  useEffect(() => writePreference("gain", String(gain)), [gain]);
  return { gain, setGain };
}
