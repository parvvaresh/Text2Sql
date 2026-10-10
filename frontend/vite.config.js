import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The backend address used by the dev server proxy
const API_TARGET = process.env.API_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  // The production build is served by FastAPI under /ui
  base: '/ui/',
  server: {
    proxy: {
      '/api': API_TARGET,
    },
  },
})
