import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import basicSsl from '@vitejs/plugin-basic-ssl'

export default defineConfig({
  plugins: [react(), tailwindcss(), basicSsl()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        timeout: 5000,
        configure: (proxy) => {
          proxy.on('error', (_err, _req, res) => {
            if ('writeHead' in res && !res.headersSent) {
              res.writeHead(502, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({
                error: {
                  code: 'BACKEND_UNAVAILABLE',
                  message: 'Backend server is not responding. Is it running on port 8001?',
                },
              }))
            }
          })
        },
      },
      '/health': {
        target: 'http://localhost:8001',
        timeout: 5000,
      },
    },
  },
})
