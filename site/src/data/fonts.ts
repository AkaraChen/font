// Reads the manifest written by scripts/fetch-fonts.mjs.
//
// The manifest is generated, not committed, so the site has to survive it being
// absent — `pnpm dev` without having run `pnpm fonts` should still render, just
// with system fonts. Everything here degrades to an empty manifest.

export interface FontFile {
  weight: string
  subset: string
  subsetBytes: number
  full?: string
  fullBytes?: number
}

export interface FontProduct {
  id: string
  product: string
  files: FontFile[]
}

export interface FontManifest {
  repo: string
  tag: string
  releaseUrl: string
  products: FontProduct[]
  hash?: string
}

const EMPTY: FontManifest = {
  repo: 'AkaraChen/font',
  tag: '',
  releaseUrl: 'https://github.com/AkaraChen/font/releases',
  products: [],
}

const generated = import.meta.glob<{ default: FontManifest }>('./fonts.generated.json', { eager: true })

export const manifest: FontManifest
  = Object.values(generated)[0]?.default ?? EMPTY

export const hasFonts = manifest.products.length > 0

/** CSS font-family name for a family id. Kept short so CSS stays readable. */
export function cssFamily(id: string): string {
  return `AKR ${id.split('-').map(part => part[0]!.toUpperCase() + part.slice(1)).join(' ')}`
}

export function productFor(id: string): FontProduct | undefined {
  return manifest.products.find(p => p.id === id)
}

export function fullFontFor(id: string): FontFile | undefined {
  return productFor(id)?.files.find(f => f.weight === 'Regular' && f.full)
}

const WEIGHT_VALUE: Record<string, number> = { Light: 300, Regular: 400, Bold: 700 }

/** `@font-face` rules for the subsetted faces — small enough to load eagerly. */
export function subsetFontFaceCss(): string {
  return manifest.products
    .flatMap(product =>
      product.files.map(file => [
        '@font-face{',
        `font-family:"${cssFamily(product.id)}";`,
        `font-weight:${WEIGHT_VALUE[file.weight] ?? 400};`,
        'font-style:normal;font-display:swap;',
        `src:url("${file.subset}") format("woff2");`,
        '}',
      ].join('')),
    )
    .join('\n')
}

export function downloadUrl(tag: string, product: string): string {
  const version = tag.replace(/^v/, '')
  return `https://github.com/${manifest.repo}/releases/download/${tag}/${product.replace(/\s+/g, '')}-${version}.zip`
}
