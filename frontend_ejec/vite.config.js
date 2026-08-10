import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// El build de produccion se sirve desde Flask bajo /patologias-beta/, por
// eso el base debe coincidir con esa ruta (assets referenciados en el
// index.html generado). En dev, /api se proxea al Flask local (puerto 8080).
export default defineConfig({
  base: '/patologias-beta/',
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8080',
    },
  },
})
