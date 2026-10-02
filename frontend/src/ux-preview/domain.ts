import type { ApiClient } from "../data/api";

export type Screen = "overview" | "library" | "recording" | "settings";
export type Theme = "system" | "frost" | "midnight";
export type SourceKind = "original" | "heart" | "lung";
export type RecordingStatus = "ready" | "processing" | "recorded" | "failed";
export interface PreviewRecording {
  id: string;
  publicId: string;
  title: string;
  date: string;
  duration: number;
  status: RecordingStatus;
  shared: boolean;
}
// This interface intentionally matches the existing protected API's media method.
// Live use must inject the current authenticated client, never the fixture provider.
export type MediaProvider = Pick<ApiClient, "media">;
export const sourceLabels: Record<SourceKind, string> = {
  original: "Original",
  heart: "Heart",
  lung: "Lung",
};
export const sourceFiles: Record<SourceKind, string> = {
  original: "M0001.wav",
  heart: "H0001.wav",
  lung: "L0001.wav",
};
export const previewIdentity = {
  name: "Ashraf Alsaloul",
  handle: "silverdragonfly",
  publicId: "USR-7K4M-2P9DXQ",
};
export const recordings: PreviewRecording[] = [
  {
    id: "study-01",
    publicId: "REC-4MT7-Q2P8KF",
    title: "Morning sound study",
    date: "Today, 08:14",
    duration: 15,
    status: "ready",
    shared: false,
  },
  {
    id: "study-02",
    publicId: "REC-9K3F-D1V6ZQ",
    title: "Quiet-room recording",
    date: "Today, 07:42",
    duration: 22,
    status: "processing",
    shared: false,
  },
  {
    id: "study-03",
    publicId: "REC-H8N2-P7J4XM",
    title: "Afternoon reference",
    date: "Yesterday, 16:28",
    duration: 18,
    status: "recorded",
    shared: false,
  },
  {
    id: "study-04",
    publicId: "REC-6R2K-V9T4MD",
    title: "Seated listening session",
    date: "Yesterday, 11:05",
    duration: 30,
    status: "ready",
    shared: true,
  },
  {
    id: "study-05",
    publicId: "REC-3F8M-C5K2NX",
    title: "Second sound study",
    date: "28 Sep, 14:36",
    duration: 15,
    status: "ready",
    shared: false,
  },
  {
    id: "study-06",
    publicId: "REC-7P2Q-A8M6KF",
    title: "Room comparison",
    date: "28 Sep, 09:20",
    duration: 24,
    status: "ready",
    shared: true,
  },
  {
    id: "study-07",
    publicId: "REC-2M6T-B4R8XK",
    title: "Short reference capture",
    date: "27 Sep, 10:42",
    duration: 12,
    status: "failed",
    shared: false,
  },
  {
    id: "study-08",
    publicId: "REC-8X4K-N2M7PQ",
    title: "Evening listening session",
    date: "26 Sep, 17:08",
    duration: 20,
    status: "ready",
    shared: false,
  },
];
export const reservedHandles = new Set([
  "admin",
  "administrator",
  "root",
  "system",
  "support",
  "stethofuse",
  "official",
  "security",
  "api",
  "help",
  "staff",
]);
export function handleError(input: string): string {
  const handle = input.trim().toLowerCase();
  if (handle.length < 3 || handle.length > 20)
    return "Use between 3 and 20 characters.";
  if (!/^[a-z][a-z0-9_.]*[a-z0-9]$/.test(handle) || /[_.]{2}/.test(handle))
    return "Start with a letter. Use letters, numbers, dots or underscores without consecutive or ending separators.";
  if (reservedHandles.has(handle))
    return "That handle is reserved. Try another name.";
  if (handle === "wintercedar")
    return "That handle is already in use. Try another name.";
  return "";
}
export function timeLabel(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}
