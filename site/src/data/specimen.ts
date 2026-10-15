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

export const isPixel = (id: string) => id === 'pixel'
export const isProportional = (id: string) => id === 'hand-text'

/** Inline style that sets a family in its own subsetted face. */
export function faceStyle(id: string, extra = ''): string | undefined {
  const parts = [hasFonts ? `font-family:"${cssFamily(id)}", ui-monospace, monospace` : '', extra].filter(Boolean)
  return parts.length ? parts.join(';') : undefined
}

const ZH_NUMERALS = ['壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖', '拾']

/** Section numerals: formal Chinese numerals in Chinese, two digits in English. */
export function numeral(locale: Locale, n: number): string {
  return locale === 'zh' ? (ZH_NUMERALS[n - 1] ?? String(n)) : String(n).padStart(2, '0')
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
