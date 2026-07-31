import { glob } from 'astro/loaders'
import { defineCollection } from 'astro:content'
import { z } from 'astro/zod'

// Long-form pages. Posts carry their own locale, so /blog and /en/blog each
// show only what was written in that language rather than a machine mirror.
const blog = defineCollection({
  loader: glob({ base: './src/content/blog', pattern: '**/*.md' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    lang: z.enum(['zh', 'en']),
    date: z.coerce.date(),
    /** Slug shared across languages, so the language switch can find the pair. */
    pair: z.string().optional(),
    draft: z.boolean().default(false),
  }),
})

export const collections = { blog }
