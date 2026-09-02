// @ts-check
import sitemap from '@astrojs/sitemap'
import { defineConfig } from 'astro/config'

// Prefer SITE_URL in CI/Vercel; default to the production custom domain.
const site = process.env.SITE_URL || 'https://font.akr.moe'

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
