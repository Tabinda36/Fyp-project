import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const DJANGO = globalThis.process?.env?.DJANGO_ORIGIN || 'http://127.0.0.1:8000';

// Everything the Django backend owns is proxied, so the React dev server and Django
// share one origin (session cookie + CSRF work without CORS).
const backendPaths = [
  '/api',
  '^/admin/',
  '/media',
  '/static',
  '/public',
  // file downloads stay plain Django endpoints
  '^/lesson/\\d+/download-ppt',
  '^/certificate/\\d+/download-pdf',
  '^/download-assignment-pdf',
  // legacy JSON endpoints used by the lesson player and notification buttons
  '^/lesson/\\d+/watch-time',
  '^/notifications/read/\\d+',
];

export default defineConfig({
  plugins: [react()],
  base: '/',
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      backendPaths.map((p) => [p, { target: DJANGO, changeOrigin: false }]),
    ),
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
  },
});
