/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#5865F2',
        secondary: '#57F287',
        background: '#2C2F33',
        surface: '#23272A',
        text: '#DCDDDE',
      }
    },
  },
  plugins: [],
}
