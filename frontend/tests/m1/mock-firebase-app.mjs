// TEST ONLY: browser-network substitution for the official Firebase app module.
// No application build imports this file or exposes a test-auth runtime flag.
const apps=[];
export const getApps=()=>apps;
export function initializeApp(options,name){const app={options,name};apps.push(app);return app;}
