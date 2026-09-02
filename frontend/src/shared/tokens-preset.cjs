/**
 * HR Suite shared Tailwind preset (PORTAL.md C5).
 *
 * Each frontend's tailwind.config.js does:
 *   presets: [require('./vendor/platform-core/tokens/preset.cjs')]
 * then uses the semantic tokens (bg-primary, text-muted, border-line, ...)
 * instead of raw palette classes (bg-blue-600). Change a value here -> every
 * app that has adopted it updates.
 */
module.exports = {
  theme: {
    extend: {
      colors: {
        // brand
        primary: {
          DEFAULT: '#2563eb', // blue-600
          hover: '#1d4ed8', // blue-700
          soft: '#eff6ff', // blue-50
          fg: '#ffffff',
        },
        danger: {
          DEFAULT: '#dc2626', // red-600
          soft: '#fef2f2', // red-50
        },
        // surfaces / text (slate scale, named by role)
        canvas: '#f8fafc', // page background      (slate-50)
        surface: '#ffffff', // cards, header
        line: '#e2e8f0', // borders               (slate-200)
        ink: '#0f172a', // primary text            (slate-900)
        muted: '#64748b', // secondary text        (slate-500)
        faint: '#94a3b8', // tertiary / disabled   (slate-400)
      },
      borderRadius: {
        card: '0.75rem', // rounded-xl
      },
      fontFamily: {
        // Thai-first stack; each app can still @import a webfont if it wants
        sans: ['"Sarabun"', 'ui-sans-serif', 'system-ui', '"Noto Sans Thai"', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
      },
    },
  },
}
