export const brand = {
  name: 'StethoFuse',
  academicTitle: 'Machine Learning-Based System for Cardiopulmonary Sound Separation',
  publicOrigin: import.meta.env.VITE_PUBLIC_ORIGIN || 'https://hearme.ashraf-alsaloul.com',
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api',
  logo: '/assets/logo.svg',
  researchNotice: 'For research and education. Not a diagnostic system.',
};
export const DEMO_ENABLED = import.meta.env.DEV || import.meta.env.VITE_ENABLE_DEMO === 'true';
