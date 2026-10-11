import type { SourceLink } from '../types'

export type ChatAnswer = {
  answer: string
  sources: SourceLink[]
  prepared: boolean
}

/** Sunucuya hiç ulaşılamadığında fırlatılır. */
export class ApiUnreachableError extends Error {}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch('/api/health')
    return response.ok
  } catch {
    return false
  }
}

export async function askQuestion(question: string): Promise<ChatAnswer> {
  let response: Response
  try {
    response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    })
  } catch {
    throw new ApiUnreachableError('Sunucuya bağlanılamadı. API sunucusunun çalıştığını kontrol edin.')
  }

  const payload: Partial<ChatAnswer> & { detail?: unknown } = await response
    .json()
    .catch(() => ({}))

  if (!response.ok) {
    // Vite proxy'si arkadaki API kapalıyken JSON olmayan bir 5xx döndürür.
    if (response.status >= 500 && payload.detail === undefined) {
      throw new ApiUnreachableError('Sunucuya bağlanılamadı. API sunucusunun çalıştığını kontrol edin.')
    }
    throw new Error(
      typeof payload.detail === 'string'
        ? payload.detail
        : 'Yanıt alınamadı. Lütfen tekrar deneyin.',
    )
  }
  if (!payload.answer) {
    throw new Error('Asistandan boş bir yanıt alındı. Lütfen tekrar deneyin.')
  }
  return {
    answer: payload.answer,
    sources: payload.sources ?? [],
    prepared: payload.prepared ?? false,
  }
}
