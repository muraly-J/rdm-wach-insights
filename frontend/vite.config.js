import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
<<<<<<< HEAD
    port: 5173,
    host: '0.0.0.0',   // bind to all interfaces so Windows laptop can reach Mac Studio
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',  // backend on same machine (Mac Studio)
=======
    // Dev only: proxy /api to local FastAPI
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
>>>>>>> dev
        changeOrigin: true,
      }
    }
  }
})