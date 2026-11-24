import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In dev, the dashboard runs on :5173 and forwards API calls to the backend.
// Built, it is served by the backend itself at /dashboard (same origin, no proxy).
const BACKEND = process.env.CHECK_BACKEND || 'http://localhost:8000';
const api = ['/health', '/stream', '/events', '/snapshots', '/stats', '/config',
  '/training', '/evaluation', '/dataset'];

export default defineConfig({
  base: '/dashboard/',
  build: { chunkSizeWarningLimit: 900 }, // local app; one bundle is fine
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      ...Object.fromEntries(api.map((p) => [p, BACKEND])),
      '/ws': { target: BACKEND.replace(/^http/, 'ws'), ws: true },
    },
  },
});
