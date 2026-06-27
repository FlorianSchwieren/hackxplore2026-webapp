/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#0a0a0a',
        glass: 'rgba(15, 15, 15, 0.75)',
        accent: {
          green: '#22c55e',
          teal: '#06b6d4',
        },
        status: {
          dry: '#ef4444',
          low: '#f97316',
          normal: '#22c55e',
          moist: '#06b6d4',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glass: '0 0 0 1px rgba(255,255,255,0.06), 0 4px 24px rgba(0,0,0,0.4)',
        glow: '0 0 20px rgba(34,197,94,0.25)',
        'glow-teal': '0 0 20px rgba(6,182,212,0.25)',
      },
    },
  },
  plugins: [],
}
