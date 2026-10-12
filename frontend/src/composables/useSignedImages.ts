import { reactive } from 'vue'
import { useApi } from './useApi'

// <img> tags cannot send the Bearer token, so the API issues short-lived signed links.
// Links are requested in batches and cached until shortly before they expire.

type Kind = 'original' | 'annotated'

const cache = reactive<Record<string, { url: string; expiresAt: number }>>({})
const pending = new Set<string>()
let timer: ReturnType<typeof setTimeout> | null = null

async function flush() {
  timer = null
  const keys = [...pending]
  pending.clear()
  if (!keys.length) return
  const imageIds = keys.filter(k => k.startsWith('original:')).map(k => k.slice(9))
  const annotatedIds = keys.filter(k => k.startsWith('annotated:')).map(k => k.slice(10))
  try {
    const res = await useApi().post<{ expiresIn: number; images: Record<string, string>; annotated: Record<string, string> }>(
      '/images/signed-urls', { imageIds, annotatedIds },
    )
    const expiresAt = Date.now() + res.expiresIn * 1000
    for (const [id, url] of Object.entries(res.images)) cache[`original:${id}`] = { url, expiresAt }
    for (const [id, url] of Object.entries(res.annotated)) cache[`annotated:${id}`] = { url, expiresAt }
  } catch {
    // leave the images empty; the next render retries
  }
}

export function useSignedImages() {
  function link(kind: Kind, id?: string | null): string {
    if (!id) return ''
    const key = `${kind}:${id}`
    const entry = cache[key]
    if (entry && entry.expiresAt - 60_000 > Date.now()) return entry.url
    if (!pending.has(key)) {
      pending.add(key)
      if (!timer) timer = setTimeout(flush, 30)
    }
    return entry?.url || ''
  }
  return {
    imageUrl: (id?: string | null) => link('original', id),
    annotatedUrl: (id?: string | null) => link('annotated', id),
  }
}
