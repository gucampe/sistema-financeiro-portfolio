/** @type {import('tailwindcss').Config} */
const coresCategoria = [
  '#1D4ED8',
  '#2563EB',
  '#3B82F6',
  '#059669',
  '#10B981',
  '#22C55E',
  '#4F46E5',
  '#6366F1',
  '#DC2626',
  '#EF4444',
  '#F97316',
  '#F59E0B',
  '#EC4899',
  '#4B5563',
  '#6B7280',
  '#9CA3AF',
]
const safelistCategorias = coresCategoria.flatMap((hex) => [
  `bg-[${hex}20]`,
  `border-[${hex}40]`,
  `text-[${hex}]`,
])

module.exports = {
  content: [
    '**/templates/**/*.html',
    'static/css/input.css',
    '**/forms.py',
    'core/**/*.py',
  ],
  safelist: safelistCategorias,
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        surface: {
          DEFAULT: '#f4f5f7',
          muted: '#f1f5f4',
          elevated: '#ffffff',
        },
        fg: {
          DEFAULT: '#334155',
          muted: '#64748b',
          subtle: '#475569',
          oninverse: '#f8fafc',
        },
        danger: {
          DEFAULT: '#dc2626',
          soft: '#fef2f2',
          border: 'rgba(220, 38, 38, 0.25)',
        },
        warning: {
          DEFAULT: '#f59e0b',
          soft: '#fffbeb',
          border: 'rgba(245, 158, 11, 0.4)',
        },
        success: {
          DEFAULT: '#16a34a',
          soft: '#ecfdf5',
          border: 'rgba(22, 163, 74, 0.15)',
        },
        primary: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
}
