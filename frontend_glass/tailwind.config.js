/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        palette: {
          900: '#190019',
          800: '#2B124C',
          700: '#522B5B',
          600: '#854F6C',
          300: '#DFB6B2',
          100: '#FBE4D8',
        },
        glass: {
          50: 'rgba(255, 255, 255, 0.05)',
          100: 'rgba(255, 255, 255, 0.10)',
          200: 'rgba(255, 255, 255, 0.20)',
          300: 'rgba(255, 255, 255, 0.30)',
          bg: '#0a0a0c',
        },
        accent: {
          cyan: '#00d4ff',
          green: '#5fe39a',
          purple: '#a78bfa',
          yellow: '#ffe600',
          orange: '#ff6b1a',
          pink: '#ff5e99',
        }
      },
      fontFamily: {
        geist: ['Geist', 'sans-serif'],
        grotesk: ['Space Grotesk', 'sans-serif'],
      },
      backdropBlur: {
        glass: '10px',
      }
    },
  },
  plugins: [],
}
