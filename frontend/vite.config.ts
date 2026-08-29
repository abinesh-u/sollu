import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss()
  ],
  server: {
    port: 3000,
    proxy: {
      '/tasks': 'http://127.0.0.1:8080',
      '/api': 'http://127.0.0.1:8080',
      '/health': 'http://127.0.0.1:8080',
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  }
})
