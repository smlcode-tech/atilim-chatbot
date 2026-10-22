/**
 * API istemcisi: arayüzün sunucuyla konuştuğu tek yer.
 *
 * Sunucunun snake_case gövdeleri burada arayüzün camelCase tiplerine çevrilir; bileşenler
 * API'nin biçimini bilmez. İstekler göreli yola (`/api/...`) gider: geliştirmede Vite
 * (`vite.config.ts`), yayında Vercel (`vercel.json`) bunları Render'daki API'ye iletir. Böylece
 * tarayıcı tek bir kaynakla konuşur, CORS ayarı gerekmez.
 */
import type { ConversationSummary, Message, SourceLink, User } from '../types'

/** `POST /api/chat` yanıtı, arayüzün kullandığı biçimde. */
export type ChatAnswer = {
  answer: string
  sources: SourceLink[]
  prepared: boolean
  suggestions: string[]
  conversationId: string | null
  title: string | null
  /** Bu sorudan sonra bugün kalan soru hakkı; sunucu sayacı tutamıyorsa bilinmez. */
  remaining: number | null
}

/** Sunucuya hiç ulaşılamadığında fırlatılır. */
export class ApiUnreachableError extends Error {}

/** Oturum geçersiz ya da süresi dolmuş; arayüz giriş ekranına döner. */
export class UnauthorizedError extends Error {}

/** Oturum jetonu `localStorage`'da tutulur: sekme kapanıp açılınca kullanıcı yeniden giriş yapmaz. */
const TOKEN_KEY = 'atilim-assistant-token'
const UNREACHABLE = 'Sunucuya bağlanılamadı. API sunucusunun çalıştığını kontrol edin.'

/** Saklanan oturum jetonu; yoksa ya da depolama kapalıysa null. */
export function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

/** Jetonu saklar; `null` siler (çıkış ya da süresi dolmuş oturum). */
export function writeToken(token: string | null) {
  try {
    if (token === null) localStorage.removeItem(TOKEN_KEY)
    else localStorage.setItem(TOKEN_KEY, token)
  } catch {
    // Gizli sekmede depolama kapalı olabilir; oturum yalnızca bu sekme boyunca sürer.
  }
}

/**
 * Oturum jetonunun taşıdığı kullanıcı; imza doğrulanmaz, yalnızca sunucuya ulaşılamadığında
 * arayüzü giriş ekranına düşürmemek için kullanılır. Jeton geçersizse sunucu ilk istekte 401
 * döner ve oturum yine kapanır.
 */
export function userFromToken(token: string): User | null {
  try {
    const part = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const bytes = Uint8Array.from(atob(part), (char) => char.charCodeAt(0))
    const claims = JSON.parse(new TextDecoder().decode(bytes)) as Record<string, unknown>
    const { sub, email, name } = claims
    if (typeof sub !== 'string' || typeof email !== 'string' || typeof name !== 'string') {
      return null
    }
    return { id: sub, email, name }
  } catch {
    return null
  }
}

/** `body` verilirse JSON'a çevrilip gönderilir. */
type RequestOptions = {
  method?: string
  body?: unknown
}

/**
 * Tüm uç noktaların ortak yolu: oturum başlığı, JSON ayrıştırma, Türkçe hata mesajları.
 *
 * Hatalar üç türe ayrılır, çünkü arayüz her birine farklı davranır: `UnauthorizedError`
 * giriş ekranına döndürür, `ApiUnreachableError` "sunucuya ulaşılamıyor" durumunu gösterir,
 * düz `Error` ise sunucunun mesajını (`detail`) olduğu gibi kullanıcıya yazar. 401'de
 * `atilim:unauthorized` olayı da yayılır: hangi istek düşürürse düşürsün `useAuth` oturumu kapatır.
 */
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

  const raw = await response.text().catch(() => '')
  let payload: Record<string, unknown> = {}
  try {
    payload = raw ? (JSON.parse(raw) as Record<string, unknown>) : {}
  } catch {
    // JSON olmayan gövde (ör. sunucunun düz metin "Internal Server Error" yanıtı).
  }

  if (response.status === 401) {
    writeToken(null)
    window.dispatchEvent(new CustomEvent('atilim:unauthorized'))
    throw new UnauthorizedError(
      typeof payload.detail === 'string' ? payload.detail : 'Oturumunuz sona erdi.',
    )
  }
  if (!response.ok) {
    // API'ye hiç ulaşılamadı: Vite proxy'si arkadaki API kapalıyken gövdesiz 500, Vercel ve
    // Render uyanırken 502/503/504 döndürür. Gövdeli bir 500 ise sunucunun kendi hatasıdır;
    // onu "bağlanılamadı" diye göstermek sorunu yanlış yere işaret ederdi.
    const gateway = response.status >= 502 && response.status <= 504
    if (payload.detail === undefined && (gateway || (response.status === 500 && !raw))) {
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

/** `GET /api/health` sonucu; arayüz açılışta giriş ekranını buna göre kurar. */
export type Health = {
  online: boolean
  /** false ise sunucuda giriş yapılandırılmamıştır; sorular misafir olarak sorulur. */
  authRequired: boolean
  /** Misafirin günlük soru sınırı; sunucuya ulaşılamadıysa bilinmez. */
  guestQuestionLimit: number | null
}

/**
 * Sunucu ayakta mı, giriş açık mı. Hiçbir zaman hata fırlatmaz: sunucuya ulaşılamazsa
 * `online: false` döner ve giriş açık varsayılır (en güvenli varsayım). `request` kullanılmaz,
 * çünkü bu çağrı oturum jetonundan bağımsızdır ve 401 olayı yaymamalıdır.
 */
export async function checkHealth(): Promise<Health> {
  try {
    const response = await fetch('/api/health')
    if (!response.ok) return { online: false, authRequired: true, guestQuestionLimit: null }
    const body: { auth_required?: boolean; guest_question_limit?: number } = await response
      .json()
      .catch(() => ({}))
    return {
      online: true,
      authRequired: body.auth_required !== false,
      guestQuestionLimit: body.guest_question_limit ?? null,
    }
  } catch {
    return { online: false, authRequired: true, guestQuestionLimit: null }
  }
}

/** Google'ın verdiği kimlik jetonunu sunucunun oturum jetonuyla değiştirir ve onu saklar. */
export async function signInWithGoogle(idToken: string): Promise<{ token: string; user: User }> {
  const body = await request<{ token: string; user: User }>('/api/auth/google', {
    method: 'POST',
    body: { id_token: idToken },
  })
  writeToken(body.token)
  return body
}

/** Saklanan oturumun hâlâ geçerli olduğunu doğrular; açılışta çağrılır. */
export function fetchMe(): Promise<User> {
  return request<User>('/api/auth/me')
}

/** Misafirin sunucuda saklanmayan geçmişi; takip soruları için her soruyla gönderilir. */
export type HistoryTurn = { role: 'user' | 'assistant'; content: string }

/**
 * Soruyu sorar. `conversationId` boşsa (girişli kullanıcıda) sunucu yeni konuşma açar ve
 * kimliğini döndürür. Eksik alanlar güvenli varsayılanlara çevrilir; boş yanıt hata sayılır,
 * ekrana boş bir balon düşmez.
 */
export async function askQuestion(
  question: string,
  conversationId: string | null,
  history: HistoryTurn[] = [],
): Promise<ChatAnswer> {
  const payload = await request<{
    answer?: string
    sources?: SourceLink[]
    prepared?: boolean
    suggestions?: string[]
    conversation_id?: string | null
    title?: string | null
    remaining?: number | null
  }>('/api/chat', {
    method: 'POST',
    body: { question, conversation_id: conversationId, history },
  })

  if (!payload.answer) {
    throw new Error('Asistandan boş bir yanıt alındı. Lütfen tekrar deneyin.')
  }
  return {
    answer: payload.answer,
    sources: payload.sources ?? [],
    prepared: payload.prepared ?? false,
    suggestions: payload.suggestions ?? [],
    conversationId: payload.conversation_id ?? null,
    title: payload.title ?? null,
    remaining: payload.remaining ?? null,
  }
}

/** Günlük soru sınırı ve bugün kalan hak (giriş yapana ya da misafire göre). */
export type Quota = {
  limit: number
  /** Sunucu sayacı tutamıyorsa bilinmez; sınır da uygulanmaz. */
  remaining: number | null
}

/** Bugünkü soru hakkı; sayacı değiştirmez. */
export function fetchQuota(): Promise<Quota> {
  return request<Quota>('/api/quota')
}

/** Yan bardaki konuşma listesi (yalnızca girişli kullanıcı). */
export async function fetchConversations(): Promise<ConversationSummary[]> {
  const rows = await request<{ id: string; title: string; updated_at: string }[]>(
    '/api/conversations',
  )
  return rows.map(({ id, title, updated_at }) => ({ id, title, updatedAt: updated_at }))
}

/**
 * Bir konuşmanın turları, ekrandaki mesaj biçiminde. Sunucu turlara kimlik vermez; React
 * listesi için rol, zaman ve sıradan kararlı bir kimlik üretilir.
 */
export async function fetchConversation(id: string): Promise<Message[]> {
  const body = await request<{
    turns: {
      role: 'user' | 'assistant'
      content: string
      created_at: string
      sources?: SourceLink[]
      suggestions?: string[]
    }[]
  }>(`/api/conversations/${encodeURIComponent(id)}`)

  return body.turns.map((turn, index) => ({
    id: `${turn.role}-${turn.created_at}-${index}`,
    role: turn.role,
    content: turn.content,
    createdAt: turn.created_at,
    sources: turn.sources?.length ? turn.sources : undefined,
    suggestions: turn.suggestions?.length ? turn.suggestions : undefined,
  }))
}

/** Konuşmayı sunucudan kalıcı olarak siler. */
export function deleteConversation(id: string): Promise<void> {
  return request<void>(`/api/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' })
}
