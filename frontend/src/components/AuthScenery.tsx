import {useId} from 'react';

/** Preserve the supplied owl pixels. Mask edges finish outside the feathers;
 * live HTML sits over the cleaned landscape, with no baked interface pixels. */
export function AuthScenery() {
  const mask = `auth-scene-${useId().replace(/:/g, '')}`;
  return <div className="auth-reference-scene" aria-hidden="true">
    <svg viewBox="0 0 1536 1024" preserveAspectRatio="xMidYMid slice" focusable="false">
      <defs><filter id={`${mask}-edge`} x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="5"/></filter><mask id={mask} maskUnits="userSpaceOnUse" x="0" y="0" width="1536" height="1024">
        <path d="M1238 544 C1305 529 1365 560 1374 624 L1380 681 C1435 728 1467 839 1469 950 L1290 957 L1188 942 C1157 933 1173 900 1176 877 C1159 818 1155 695 1172 620 C1183 566 1204 550 1238 544Z" fill="white" filter={`url(#${mask}-edge)`}/>
      </mask></defs>
      <image href="/assets/public-reference/login-reference.webp" width="1536" height="1024" mask={`url(#${mask})`}/>
    </svg>
  </div>;
}

/** The multicolor provider mark already present in the supplied reference. */
export function AuthGoogleMark() {
  const clip = `google-mark-${useId().replace(/:/g, '')}`;
  return <svg width="22" height="22" viewBox="676 709 25 25" aria-hidden="true" focusable="false">
    <defs><clipPath id={clip}><rect x="676" y="709" width="25" height="25"/></clipPath></defs>
    <image href="/assets/public-reference/login-reference.webp" width="1536" height="1024" clipPath={`url(#${clip})`}/>
  </svg>;
}
