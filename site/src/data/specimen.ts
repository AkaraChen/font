// How families are *shown* — never what they are. Facts live in families.ts;
// this file only holds the choices a specimen makes about presenting them.

import { cssFamily, hasFonts } from './fonts'
import type { Locale } from '../i18n/ui'

/** The one character each family is introduced by, taken from its Chinese name. */
export const glyphOf: Record<string, string> = {
  'slab': '宋',
  'sans': '黑',
  'round': '圆',
  'type': '打',
  'pixel': '像',
  'hand': '楷',
  'hand-text': '文',
  'casual': '随',
}

/**
 * One Latin cell in em, measured from the released fonts (advance of `A` over
 * units per em). Everything not listed is 500 / 1000.
 */
export const cellEm: Record<string, number> = { sans: 0.55, type: 0.6 }

/**
 * How far to move each face's characters (in em) so their ink sits centred
 * in a cell drawn with line-height 1. Measured from the release fonts: the
 * typo ascender and descender place the baseline, the bounding boxes of the
 * family characters place the ink.
 */
export const centreShift: Record<string, number> = {
  'slab': 0.038,
  'sans': 0.002,
  'round': -0.023,
  'type': -0.046,
  'pixel': -0.042,
  'hand': 0.021,
  'hand-text': 0.021,
  'casual': 0.031,
}

export const isPixel = (id: string) => id === 'pixel'
export const isProportional = (id: string) => id === 'hand-text'

/** Inline style that sets a family in its own subsetted face. */
export function faceStyle(id: string, extra = ''): string | undefined {
  const parts = [hasFonts ? `font-family:"${cssFamily(id)}", ui-monospace, monospace` : '', extra].filter(Boolean)
  return parts.length ? parts.join(';') : undefined
}

/** Detail numbers, as a drawing calls them out: two digits in either language. */
export function numeral(_locale: Locale, n: number): string {
  return String(n).padStart(2, '0')
}

/** The second line every family band sets under its own sample. */
export const proofLine = '永安 Ag 0Oo 1lI {} -> => != <='

/** What the glyph overview shows, grouped. CJK is the opening of 兰亭集序. */
export const glyphSet = {
  upper: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
  lower: 'abcdefghijklmnopqrstuvwxyz',
  figures: '0123456789',
  marks: '!?@#$%&*()[]{}<>/\\|^~_=+-:;.,"\'`',
  cjk: '永和九年岁在癸丑暮春之初会于会稽山阴之兰亭',
  cjkMarks: '、。，；：？！“”（）《》【】…—',
}

/** Operator pairs a coding face is judged on, shown with and without calt. */
export const ligatures = ['->', '=>', '!=', '===', '<=', '>=', '|>', '::', '//', '/*', '<!--', '&&', '||', '++', '..=']

/** Nerd Font icons the subset keeps: GitHub, branch, folder, code, gear, terminal. */
export const icons = ['', '', '', '', '', '']
