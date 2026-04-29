/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  safelist: [
    // Navy surfaces
    { pattern: /bg-navy-(950|900|800|700|600)/ },
    { pattern: /border-navy-(950|900|800|700|600)/ },
    { pattern: /text-navy-(950|900|800|700|600)/ },
    // Pulse (indigo) accent
    { pattern: /bg-pulse-(100|200|300|400|500|600)(\/(5|10|15|20|25|30|40|50))?/ },
    { pattern: /text-pulse-(100|200|300|400|500|600)/ },
    { pattern: /border-pulse-(100|200|300|400|500|600)(\/(5|10|15|20|25|30|40|50))?/ },
    // HCH teal
    { pattern: /bg-hch-teal(\/(5|10|15|20|25|30|40|50))?/ },
    { pattern: /text-hch-teal/ },
    { pattern: /border-hch-teal(\/(5|10|15|20|25|30|40|50))?/ },
    // Surface
    { pattern: /bg-surface-(950|900|800|700)/ },
    // Commonly used status colors (dynamic strings)
    'bg-emerald-400', 'bg-emerald-500', 'text-emerald-300', 'text-emerald-400',
    'bg-emerald-500/10', 'border-emerald-500/20', 'bg-emerald-400/10',
    'bg-amber-400', 'bg-amber-500', 'text-amber-300', 'text-amber-400',
    'bg-amber-500/10', 'border-amber-500/20', 'bg-amber-400/10',
    'bg-rose-400', 'bg-rose-500',  'text-rose-300', 'bg-rose-500/10', 'border-rose-500/20',
    'bg-red-600', 'text-red-400',   'bg-red-900/20', 'border-red-800/30',
    'bg-blue-400', 'bg-blue-500',   'text-blue-300', 'bg-blue-500/10', 'border-blue-500/20',
    'bg-orange-400', 'bg-orange-500','text-orange-300','bg-orange-500/10','border-orange-500/20',
    'bg-indigo-400', 'bg-indigo-500','text-indigo-400','bg-indigo-500/10',
  ],
  theme: {
    extend: {
      colors: {
        // HCH brand navy — exact match to portal's --primary / --nav-bg
        navy: {
          950: '#1a2535',
          900: '#2d3e50',
          800: '#3d546b',
          700: '#4a6680',
          600: '#5b7a98',
        },
        // Pulsus accent — indigo (different from portal's teal, clearly distinct)
        pulse: {
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
        },
        // HCH secondary teal — used sparingly for brand continuity
        hch: {
          teal: '#4a7c9d',
          light: '#5b96bf',
        },
        // Dark surface layers
        surface: {
          950: '#0f1923',
          900: '#19263a',
          800: '#213045',
          700: '#2d3e50',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
