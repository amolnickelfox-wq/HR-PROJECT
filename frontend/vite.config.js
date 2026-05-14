import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    proxy: {
      '/analyze':      'http://localhost:8000',
      '/parse':        'http://localhost:8000',
      '/health':       'http://localhost:8000',
      '/interview':    'http://localhost:8000',
      '/upload-resume':'http://localhost:8000',
      '/batch':        'http://localhost:8000',
      '/twilio':       'http://localhost:8000',
    },
  },
})
