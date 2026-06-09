import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/extract': 'http://localhost:8000',
      '/jobs': 'http://localhost:8000',
    },
  },
})
