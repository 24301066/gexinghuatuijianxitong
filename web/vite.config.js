import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Dev mode proxies /api to the local FastAPI service; the packaged desktop build
// serves the same files from FastAPI itself, so no base path is needed.
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
})
