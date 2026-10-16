/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#070a12',
        bg2: '#0c101d',
        card: '#121826',
        line: '#1f293d',
        safe: '#22c55e',
        danger: '#ef4444',
        rose: '#f43f5e',
        gold: '#f59e0b',
        cyan: '#06b6d4',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        head: ['Rajdhani', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
