import type { ConversationSummary, Message, SourceLink, User } from '../types'

export type ChatAnswer = {
  answer: string
  sources: SourceLink[]
  prepared: boolean
  conversationId: string | null
  title: string | null
}

/** Sunucuya hiç ulaşılamadığında fırlatılır. */
export class ApiUnreachableError extends Error {}

/** Oturum geçersiz ya da süresi dolmuş; arayüz giriş ekranına döner. */
export class UnauthorizedError extends Error {}

const TOKEN_KEY = 'atilim-assistant-token'
const UNREACHABLE = 'Sunucuya bağlanılamadı. API sunucusunun çalıştığını kontrol edin.'

export function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function writeToken(token: string | null) {
  try {
    if (token === null) localStorage.removeItem(TOKEN_KEY)
    else localStorage.setItem(TOKEN_KEY, token)
  } catch {
    // Gizli sekmede depolama kapalı olabilir; oturum yalnızca bu sekme boyunca sürer.
  }
}

type RequestOptions = {
  method?: string
  body?: unknown
}

/** Tüm uç noktaların ortak yolu: oturum başlığı, JSON ayrıştırma, Türkçe hata mesajları. */
async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = readToken()
  let response: Response
  try {
    response = await fetch(path, {
      method: options.method ?? 'GET',
      headers: {
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(token === null ? {} : { Authorization: `Bearer ${token}` }),
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    })
  } catch {
    throw new ApiUnreachableError(UNREACHABLE)
  }

  if (response.status === 204) return undefined as T

  const payload: Record<string, unknown> = await response.json().catch(() => ({}))

  if (response.status === 401) {
    writeToken(null)
    window.dispatchEvent(new CustomEvent('atilim:unauthorized'))
    throw new UnauthorizedError(
      typeof payload.detail === 'string' ? payload.detail : 'Oturumunuz sona erdi.',
    )
  }
  if (!response.ok) {
    // Vite proxy'si arkadaki API kapalıyken JSON olmayan bir 5xx döndürür.
    if (response.status >= 500 && payload.detail === undefined) {
      throw new ApiUnreachableError(UNREACHABLE)
    }
    throw new Error(
      typeof payload.detail === 'string'
        ? payload.detail
        : 'Yanıt alınamadı. Lütfen tekrar deneyin.',
    )
  }
  return payload as T
}

export type Health = {
  online: boolean
  /** false ise sunucuda giriş yapılandırılmamıştır; sorular misafir olarak sorulur. */
  authRequired: boolean
}

export async function checkHealth(): Promise<Health> {
  try {
    const response = await fetch('/api/health')
    if (!response.ok) return { online: false, authRequired: true }
    const body: { auth_required?: boolean } = await response.json().catch(() => ({}))
    return { online: true, authRequired: body.auth_required !== false }
  } catch {
    return { online: false, authRequired: true }
  }
}

export async function signInWithGoogle(idToken: string): Promise<{ token: string; user: User }> {
  const body = await request<{ token: string; user: User }>('/api/auth/google', {
    method: 'POST',
    body: { id_token: idToken },
  })
  writeToken(body.token)
  return body
}

export function fetchMe(): Promise<User> {
  return request<User>('/api/auth/me')
}

export async function askQuestion(
  question: string,
  conversationId: string | null,
): Promise<ChatAnswer> {
  const payload = await request<{
    answer?: string
    sources?: SourceLink[]
    prepared?: boolean
    conversation_id?: string | null
    title?: string | null
  }>('/api/chat', {
    method: 'POST',
    body: { question, conversation_id: conversationId },
  })

  if (!payload.answer) {
    throw new Error('Asistandan boş bir yanıt alındı. Lütfen tekrar deneyin.')
  }
  return {
    answer: payload.answer,
    sources: payload.sources ?? [],
    prepared: payload.prepared ?? false,
    conversationId: payload.conversation_id ?? null,
    title: payload.title ?? null,
  }
}

export async function fetchConversations(): Promise<ConversationSummary[]> {
  const rows = await request<{ id: string; title: string; updated_at: string }[]>(
    '/api/conversations',
  )
  return rows.map(({ id, title, updated_at }) => ({ id, title, updatedAt: updated_at }))
}

export async function fetchConversation(id: string): Promise<Message[]> {
  const body = await request<{
    turns: {
      role: 'user' | 'assistant'
      content: string
      created_at: string
      sources?: SourceLink[]
    }[]
  }>(`/api/conversations/${encodeURIComponent(id)}`)

  return body.turns.map((turn, index) => ({
    id: `${turn.role}-${turn.created_at}-${index}`,
    role: turn.role,
    content: turn.content,
    createdAt: turn.created_at,
    sources: turn.sources?.length ? turn.sources : undefined,
  }))
}

export function deleteConversation(id: string): Promise<void> {
  return request<void>(`/api/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' })
}
