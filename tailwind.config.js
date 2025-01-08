/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.{html,j2,js}",
    "./app/static/**/*.{html,js,css}"
  ],
  safelist: [
    // Ensure all col-span classes are included
    {
      pattern: /^col-span-/,
      variants: ['sm', 'md', 'lg', 'xl', '2xl']
    },
    // Ensure all row-span classes are included
    {
      pattern: /^row-span-/,
      variants: ['sm', 'md', 'lg', 'xl', '2xl']
    }
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
