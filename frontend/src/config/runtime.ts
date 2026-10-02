// Build configuration is public, never a place for Admin credentials or secrets.
export const FIREBASE_PROJECT = 'stethofuse-c18cd-3cca0';
export const PUBLIC_ORIGIN = 'https://stethofuse.ashraf-alsaloul.com';
export const DEMO_ENABLED = import.meta.env.DEV &&
  (import.meta.env.VITE_APP_MODE === 'demo' || import.meta.env.MODE === 'demo');

export function firebaseConfiguration(env: Record<string, unknown> = import.meta.env) {
  const value = (key: string) => typeof env[key] === 'string' ? (env[key] as string).trim() : '';
  const config = {
    apiKey: value('VITE_FIREBASE_API_KEY'), authDomain: value('VITE_FIREBASE_AUTH_DOMAIN'),
    projectId: value('VITE_FIREBASE_PROJECT_ID'), appId: value('VITE_FIREBASE_APP_ID'),
  };
  if (Object.values(config).some(v => !v) || config.projectId !== FIREBASE_PROJECT ||
      !/^AIza[A-Za-z0-9_-]+$/.test(config.apiKey) || !/^1:\d+:web:[a-zA-Z0-9]+$/.test(config.appId) ||
      ![`${FIREBASE_PROJECT}.firebaseapp.com`, 'stethofuse.ashraf-alsaloul.com'].includes(config.authDomain)) {
    throw new Error('Authentication configuration is incomplete. The project owner must configure the selected Firebase web app. No demo session will be substituted.');
  }
  return config;
}

export const firebaseConfigurationError = (() => {
  if (DEMO_ENABLED) return '';
  try { firebaseConfiguration(); return ''; } catch (error) { return (error as Error).message; }
})();
