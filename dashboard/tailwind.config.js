/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        advisory: '#EAB308',
        warning: '#F97316',
        critical: '#EF4444',
      },
    },
  },
  plugins: [],
}
