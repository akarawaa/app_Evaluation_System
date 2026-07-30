import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // Default to 5173, but let the environment override it so the dev server can
  // still start when something else already holds that port.
  server: { port: Number(process.env.PORT) || 5173 },
})
