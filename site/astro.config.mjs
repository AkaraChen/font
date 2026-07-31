// @ts-check
import sitemap from '@astrojs/sitemap'
import { defineConfig } from 'astro/config'

// Set SITE_URL in CI once the domain is decided; the default keeps sitemap and
// canonical URLs working for a GitHub Pages deploy.
const site = process.env.SITE_URL || 'https://akarachen.github.io/font'

export default defineConfig({
  site,
  base: process.env.SITE_BASE || '/',
  output: 'static',
  trailingSlash: 'ignore',
  i18n: {
    defaultLocale: 'zh',
    locales: ['zh', 'en'],
    routing: { prefixDefaultLocale: false },
  },
  integrations: [sitemap()],
  build: { inlineStylesheets: 'auto' },
})
