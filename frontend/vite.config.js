import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8081',
        changeOrigin: true,
        onProxyReq(proxyReq, req, res) {
          // Pass through Authorization header if present
          const authHeader = req.headers['authorization'];
          if (authHeader) {
            proxyReq.setHeader('Authorization', authHeader);
            console.log('[Vite Proxy] Forwarded Authorization header');
          } else {
            console.log('[Vite Proxy] No Authorization header found');
          }
        },
      },
      '/dashboard': {
        target: 'http://127.0.0.1:8081',
        changeOrigin: true,
        onProxyReq(proxyReq, req, res) {
          // Pass through Authorization header if present
          const authHeader = req.headers['authorization'];
          if (authHeader) {
            proxyReq.setHeader('Authorization', authHeader);
            console.log('[Vite Proxy /dashboard] Forwarded Authorization header');
          } else {
            console.log('[Vite Proxy /dashboard] No Authorization header found');
          }
        },
        rewrite: (path) => path.replace(/^\/dashboard/, '/api/dashboard'),
      },
    },
    headers: {
      'Cache-Control': 'no-store, no-cache, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    }
  },
  build: {
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]'
      }
    }
  }
})
