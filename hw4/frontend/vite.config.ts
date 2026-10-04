import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Forward API, chat, and image requests to the FastAPI backend on port 8000.
    proxy: {
      '/api': 'http://localhost:8000',
      // Regex so /chat and /chat/history are proxied but the /chat-results page is not.
      '^/chat(/|$)': 'http://localhost:8000',
      '/images': 'http://localhost:8000',
    },
  },
})
