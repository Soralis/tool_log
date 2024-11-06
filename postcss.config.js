module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
    'postcss-purgecss': {
      content: [
        './app/templates/**/*.j2',
        './app/templates/*.j2',
      ],
      defaultExtractor: (content) => content.match(/[\w-/:]+(?<!:)/g) || [],
    },
  },
}
