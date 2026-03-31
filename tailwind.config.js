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
  content: ['**/templates/**/*.html'],
  safelist: safelistCategorias,
  theme: {
    extend: {},
  },
  plugins: [],
}

