/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Neutral dark scale
        bg: '#0b0d11',
        surface: '#12151b',
        'surface-2': '#191d25',
        'surface-3': '#222835',
        line: '#262b36',
        'line-2': '#333a48',
        // Text
        ink: '#eef1f6',
        'ink-dim': '#98a2b3',
        'ink-faint': '#5f6b7d',
        // Brand accent (deals = amber)
        brand: '#f59e0b',
        'brand-hi': '#fbbf24',
        'on-brand': '#201200',
        // Semantic
        good: '#4ade80',
        warn: '#fb7185',
      },
      borderRadius: {
        DEFAULT: '0.25rem',
        lg: '0.5rem',
        xl: '0.75rem',
        full: '9999px',
      },
      spacing: {
        gutter: '16px',
        sm: '0.5rem',
        md: '1rem',
        'margin-mobile': '16px',
        xl: '2.5rem',
        base: '4px',
        lg: '1.5rem',
        xs: '0.25rem',
        'margin-desktop': '48px',
      },
      fontFamily: {
        display: ['Hanken Grotesk', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
