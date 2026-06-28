import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Во время разработки проксируем /api и /media на локальный бэкенд,
// чтобы фронт работал так же, как за nginx в проде.
const backend = process.env.VITE_BACKEND_ORIGIN ?? 'http://localhost:8000'
// Бэкенд прайса (nn_vla) — отдельный сервис. В деве /price-api проксируем на него,
// в проде то же делает nginx чата. /price-api/api/... -> price-backend /api/...
const priceBackend = process.env.VITE_PRICE_BACKEND_ORIGIN ?? 'http://localhost:8010'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: backend, changeOrigin: true },
      '/media': { target: backend, changeOrigin: true },
      '/price-api': {
        target: priceBackend,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/price-api/, ''),
      },
    },
  },
})
