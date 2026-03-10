/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        'medical-blue': '#1A6B9A',
        'medical-blue-light': '#2196F3',
        'critical': '#C0392B',
        'critical-light': '#E74C3C',
        'high': '#E67E22',
        'high-light': '#F39C12',
        'normal': '#1E8449',
        'normal-light': '#27AE60',
        'bg-dark': '#0D1117',
        'bg-card': '#161B22',
        'bg-card-hover': '#1C2333',
        'border-dark': '#30363D',
        'border-light': '#484F58',
      },
      keyframes: {
        'pulse-critical': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.4', transform: 'scale(1.2)' },
        },
        'slide-down': {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'glow': {
          '0%, 100%': { boxShadow: '0 0 5px rgba(26, 107, 154, 0.3)' },
          '50%': { boxShadow: '0 0 20px rgba(26, 107, 154, 0.6)' },
        },
        'heartbeat': {
          '0%, 100%': { transform: 'scale(1)' },
          '14%': { transform: 'scale(1.1)' },
          '28%': { transform: 'scale(1)' },
          '42%': { transform: 'scale(1.1)' },
          '70%': { transform: 'scale(1)' },
        },
      },
      animation: {
        'pulse-critical': 'pulse-critical 1s ease-in-out infinite',
        'slide-down': 'slide-down 0.3s ease-out',
        'fade-in': 'fade-in 0.5s ease-out',
        'glow': 'glow 2s ease-in-out infinite',
        'heartbeat': 'heartbeat 1.5s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
