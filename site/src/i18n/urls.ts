// Absolute URLs for canonical / hreflang / sitemap.
//
// `new URL('/a', site)` throws away any path in `site`, which silently drops the
// sub-path when the site is served from one (a GitHub Pages project URL, a docs
// sub-path). Joining by hand keeps it.

import { localePath, type Locale } from './ui'

export function absolute(site: URL | undefined, path: string): string {
  if (!site) return path
  const base = site.href.replace(/\/+$/, '')
  const clean = path === '/' ? '' : `/${path.replace(/^\/+/, '')}`
  return `${base}${clean}` || `${base}/`
}

export function localeAbsolute(site: URL | undefined, locale: Locale, path: string): string {
  return absolute(site, localePath(locale, path))
}
