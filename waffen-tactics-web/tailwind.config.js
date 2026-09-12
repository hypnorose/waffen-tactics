/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: 'rgb(var(--wt-color-accent) / <alpha-value>)',
        secondary: 'rgb(var(--wt-color-success) / <alpha-value>)',
        background: 'rgb(var(--wt-color-canvas) / <alpha-value>)',
        surface: 'rgb(var(--wt-color-surface) / <alpha-value>)',
        text: 'rgb(var(--wt-color-text-primary) / <alpha-value>)',
      }
    },
  },
  plugins: [],
}
