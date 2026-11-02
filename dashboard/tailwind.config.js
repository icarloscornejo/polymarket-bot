/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        profit: '#22c55e',
        loss: '#ef4444',
        accent: '#f59e0b',
      },
    },
  },
  plugins: [],
}
