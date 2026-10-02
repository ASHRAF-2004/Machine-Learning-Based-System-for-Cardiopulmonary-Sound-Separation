# Frontend performance observations

Measured 2026-09-23T17:27:22.612Z with Chrome 151.0.7922.137, headless on Ubuntu, against http://127.0.0.1:4181.

## Method

Each sample uses a fresh isolated browser context and disables the browser HTTP cache. Server and operating-system caches are not flushed. These are one-shot local lab observations, not production field percentiles, a Lighthouse score, or real-device measurements. The machine is shared with ongoing development work; host load is not controlled. No pointer movement was sent during the initial-load window. Fonts and hero images were ready before a final one-second idle observation.

The desktop sample uses 1440 × 900 at DPR 1. The mobile sample emulates 390 × 844 at DPR 2 with touch/coarse-pointer behavior. The throttled desktop uses CDP network emulation: 150 ms latency, 1.6 Mbps down, 0.75 Mbps up, plus 4× CPU slowdown. This does not model every property of a slow phone or remote deployment.

The web-perf skill’s Chrome DevTools MCP was unavailable. The existing Playwright/Chrome connection and CDP supplied Resource Timing, paint observers, layout shifts and heap snapshots without installing tools. No Core Web Vitals rating is inferred from these isolated samples.

| Sample | FCP | LCP | CLS | Encoded response bodies | Browser-reported transfer |
|---|---:|---:|---:|---:|---:|
| desktop-localhost | 376 ms | 396 ms | 0.0009 | 455.2 KiB | 459.3 KiB |
| mobile-emulation-localhost | 356 ms | 356 ms | 0.0000 | 455.2 KiB | 459.3 KiB |
| desktop-throttled-emulation | 1464 ms | 3092 ms | 0.0023 | 455.2 KiB | 459.3 KiB |

## Initial resources by type

| Sample | Resource type | Requests | Encoded body | Decoded response body |
|---|---|---:|---:|---:|
| desktop-localhost | document | 1 | 0.7 KiB | 0.7 KiB |
| desktop-localhost | javascript | 5 | 137.0 KiB | 453.9 KiB |
| desktop-localhost | stylesheets | 2 | 8.0 KiB | 30.0 KiB |
| desktop-localhost | images | 4 | 248.6 KiB | 283.0 KiB |
| desktop-localhost | fonts | 2 | 61.0 KiB | 61.0 KiB |
| mobile-emulation-localhost | document | 1 | 0.7 KiB | 0.7 KiB |
| mobile-emulation-localhost | javascript | 5 | 137.0 KiB | 453.9 KiB |
| mobile-emulation-localhost | stylesheets | 2 | 8.0 KiB | 30.0 KiB |
| mobile-emulation-localhost | images | 4 | 248.6 KiB | 283.0 KiB |
| mobile-emulation-localhost | fonts | 2 | 61.0 KiB | 61.0 KiB |
| desktop-throttled-emulation | document | 1 | 0.7 KiB | 0.7 KiB |
| desktop-throttled-emulation | javascript | 5 | 137.0 KiB | 453.9 KiB |
| desktop-throttled-emulation | stylesheets | 2 | 8.0 KiB | 30.0 KiB |
| desktop-throttled-emulation | images | 4 | 248.6 KiB | 283.0 KiB |
| desktop-throttled-emulation | fonts | 2 | 61.0 KiB | 61.0 KiB |

**Encoded body bytes** are the actual encoded response bodies reported by Chrome. **Decoded body bytes** are response-body decompression sizes, not decoded texture/RGBA, GPU, canvas or total application memory. The preview server used the content encodings listed in `evidence/performance/results.json`; do not substitute gzip estimates for these observed transfers. Resource Timing transfer sizes include browser-reported overhead.

## Route splitting and gzip comparison

The following gzip values are measured by compressing build artifacts locally at gzip level 9. They are potential delivery sizes if a server enables that compression; this task did not change deployment or server compression settings.

| Build file | Raw | Gzip level 9 | Requested by initial public page |
|---|---:|---:|---|
| AccountPages-DVvz1yU2.js | 70.5 KiB | 18.5 KiB | No |
| AccountPages-DhKqxZBs.css | 4.1 KiB | 1.2 KiB | No |
| ArrowLeft.es-C0ApE77u.js | 1.5 KiB | 0.6 KiB | Yes |
| AudioWorkbench-6-38TDO8.js | 13.7 KiB | 4.9 KiB | No |
| LockKey.es-CHU4q8Y3.js | 4.5 KiB | 1.3 KiB | Yes |
| PublicPages-8rUfmNXK.js | 54.3 KiB | 16.1 KiB | Yes |
| PublicPages-DadjDMtk.css | 4.5 KiB | 1.4 KiB | Yes |
| UploadSimple.es-DrGzevCz.js | 5.0 KiB | 1.3 KiB | Yes |
| WorkspacePages-R4VMFkjQ.css | 6.2 KiB | 1.8 KiB | No |
| WorkspacePages-WsQodmO0.js | 68.3 KiB | 17.9 KiB | No |
| index-Ch4Bc_2e.css | 25.5 KiB | 6.6 KiB | Yes |
| index-D4Z4vJuz.js | 388.7 KiB | 117.5 KiB | Yes |

Initial requested JavaScript + CSS gzip-level-9 total: **144.7 KiB**. Fonts and decorative images are accounted for separately above. Private workspace, administration/account and audio-workbench chunks must remain absent from public initial requests. The complete file list, actual requests and errors are preserved in the JSON evidence.

## Checks

- PASS: desktop-localhost · heroLoaded.
- PASS: desktop-localhost · noInitialAnimationFrames.
- PASS: desktop-localhost · noPrivateWorkspaceChunks.
- PASS: desktop-localhost · noPersonaButtons.
- PASS: desktop-localhost · noStorageWritten.
- PASS: desktop-localhost · noHorizontalOverflow.
- PASS: desktop-localhost · noRuntimeErrors.
- PASS: desktop-localhost · noConsoleErrors.
- PASS: desktop-localhost · noHttpErrors.
- PASS: desktop-localhost · noFailedRequests.
- PASS: desktop-localhost · initialJavaScriptUnder250KB.
- PASS: desktop-localhost · initialImagesUnder500KB.
- PASS: mobile-emulation-localhost · heroLoaded.
- PASS: mobile-emulation-localhost · noInitialAnimationFrames.
- PASS: mobile-emulation-localhost · noPrivateWorkspaceChunks.
- PASS: mobile-emulation-localhost · noPersonaButtons.
- PASS: mobile-emulation-localhost · noStorageWritten.
- PASS: mobile-emulation-localhost · noHorizontalOverflow.
- PASS: mobile-emulation-localhost · noRuntimeErrors.
- PASS: mobile-emulation-localhost · noConsoleErrors.
- PASS: mobile-emulation-localhost · noHttpErrors.
- PASS: mobile-emulation-localhost · noFailedRequests.
- PASS: mobile-emulation-localhost · initialJavaScriptUnder250KB.
- PASS: mobile-emulation-localhost · initialImagesUnder500KB.
- PASS: desktop-throttled-emulation · heroLoaded.
- PASS: desktop-throttled-emulation · noInitialAnimationFrames.
- PASS: desktop-throttled-emulation · noPrivateWorkspaceChunks.
- PASS: desktop-throttled-emulation · noPersonaButtons.
- PASS: desktop-throttled-emulation · noStorageWritten.
- PASS: desktop-throttled-emulation · noHorizontalOverflow.
- PASS: desktop-throttled-emulation · noRuntimeErrors.
- PASS: desktop-throttled-emulation · noConsoleErrors.
- PASS: desktop-throttled-emulation · noHttpErrors.
- PASS: desktop-throttled-emulation · noFailedRequests.
- PASS: desktop-throttled-emulation · initialJavaScriptUnder250KB.
- PASS: desktop-throttled-emulation · initialImagesUnder500KB.
- PASS: Normal production login has no persona selector and states authentication is unconfigured.
- PASS: Direct /app route redirects to login rather than granting fixture access.
- PASS: Forged demo storage does not enable a production authentication bypass.
- PASS: Production sign-in remains an honest failure and sends no credentials.

Initial-load frame fetching is checked separately from pointer-driven animation. The interaction renderer may load assets after input; that is outside this initial-load measurement. Canvas drawing dimensions, displayed dimensions, DPR, selected poster sources, and per-resource timings are in the JSON. Image `naturalWidth`/`naturalHeight` are DOM density-corrected values when `srcset` is used, not necessarily raw file dimensions. JavaScript heap snapshots are observable but are not total browser or decoded-image memory.

## Reproduce

```bash
cd /home/ashraf/Documents/StethoFuse/implementation/frontend
npm run build
npm run preview -- --port 4181
# In another terminal:
node tests/performance.mjs
```

Do not set `VITE_ENABLE_DEMO=true` for this production-boundary check. The development-only personas remain available through `npm run dev` on port 4180. Live authentication remains unconfigured and requires the documented Firebase adapter/backend integration.

Evidence: `evidence/performance/results.json`, desktop/mobile/throttled screenshots and `production-login.png`. No HTML, stylesheet, assets, renderer or deployment configuration was modified by this performance task.

Overall automated measurement/check status: **PASS**. This is not a claim that the complete app or owl has production field-performance approval.
