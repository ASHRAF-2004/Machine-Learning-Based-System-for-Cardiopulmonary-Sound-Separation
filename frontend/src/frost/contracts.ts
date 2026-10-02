import type {ApiClient} from '../data/api';

// Fixture-free presentation contracts shared with the approved visual prototype.
export type Theme = 'system' | 'frost' | 'midnight';
export type SourceKind = 'original' | 'heart' | 'lung';
export type RecordingStatus = 'recorded' | 'processing' | 'ready' | 'failed';
export type MediaProvider = Pick<ApiClient, 'media'> & Partial<Pick<ApiClient, 'checkMedia'>>;
export const sourceLabels: Record<SourceKind, string> = {original:'Original',heart:'Heart',lung:'Lung'};
export function timeLabel(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2,'0')}`;
}
