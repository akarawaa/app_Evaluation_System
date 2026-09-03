/** @type {import('tailwindcss').Config} */
export default {
  // shared design tokens, vendored from platform-core (src/shared, PORTAL.md C5)
  presets: [require('./src/shared/tokens-preset.cjs')],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
