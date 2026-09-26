import { useId } from 'react';

/** Literal decorative pixels from the user's supplied references. SVG viewports
 * frame only artwork: never a form, table, link, button or replacement UI.
 * The source atlases are lossless and originals remain untouched. */
const crops = {
  owl: ['dashboard', 1114, 89, 472, 172],
  settingsOwl: ['settings', 1120, 98, 466, 180],
  ensembleOwl: ['ensemble', 1157, 55, 429, 166],
  sharedOwl: ['shared', 1173, 120, 413, 254],
  signal: ['dashboard', 704, 271, 407, 213],
  signalFine: ['ensemble', 977, 313, 290, 70],
  fusionForest: ['ensemble', 1252, 790, 288, 180],
  utilitySignal: ['utility', 987, 650, 235, 103],
  feather: ['dashboard', 1396, 744, 144, 127],
  forest: ['dashboard', 1418, 593, 111, 110],
  collection: ['collection', 520, 414, 700, 172],
  recordingCollection: ['recording-collection', 288, 458, 500, 360],
  dashboardCollection: ['dashboard', 420, 631, 580, 113],
  sidebar: ['assigned', 0, 762, 237, 126],
  mountains: ['assigned', 910, 93, 370, 211],
  utilityLandscape: ['utility', 0, 82, 1586, 830],
} as const;
export type ReferenceArtwork = keyof typeof crops;
export function ReferenceArt({kind,className=''}:{kind:ReferenceArtwork;className?:string}) {
  const clipId = `reference-${useId().replace(/:/g, '')}`;
  const [atlas,x,y,width,height] = crops[kind];
  if(kind==='utilityLandscape') return <svg className={`reference-art reference-utilityLandscape ${className}`} viewBox="0 82 1586 830" aria-hidden="true" focusable="false" preserveAspectRatio="xMidYMid slice"><defs><mask id={clipId}><rect width="1586" height="992" fill="white"/><rect x="375" y="256" width="838" height="488" rx="20" fill="black"/></mask></defs><image href="/assets/reference-match/utility.webp" width="1586" height="992" mask={`url(#${clipId})`}/></svg>;
  return <svg className={`reference-art reference-${kind} ${className}`} viewBox={`${x} ${y} ${width} ${height}`} width={width} height={height} aria-hidden="true" focusable="false" overflow="hidden" preserveAspectRatio="xMidYMid slice"><defs><clipPath id={clipId}><rect x={x} y={y} width={width} height={height}/></clipPath></defs><image href={`/assets/reference-match/${atlas}.webp`} width="1586" height="992" clipPath={`url(#${clipId})`}/></svg>;
}
