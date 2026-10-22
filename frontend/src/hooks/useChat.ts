import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ApiUnreachableError,
  askQuestion,
  fetchConversation,
  type HistoryTurn,
} from '../api/client'
import type { ApiStatus, Message } from '../types'

type UseChatOptions = {
  /** Yeni bir konuşma açıldığında ya da bir konuşmaya yazıldığında yan bar tazelenir. */
  onConversationChanged: () => void
  /** Misafirin geçmişi sunucuda tutulmaz; takip soruları için her soruyla gönderilir. */
  sendsHistory: boolean
  /** Her yanıt bugün kalan soru hakkını taşır. */
  onRemaining: (remaining: number | null) => void
  /** Soru yanıtlanamadı (sınır dolu ya da hata): kalan hak sunucudan yeniden alınır. */
  onQuotaStale: () => void
  /** Açılıştaki sağlık denetiminin sonucu (`useAuth`); `/api/health` ikinci kez istenmez. */
  initialApiStatus: ApiStatus
}

/**
 * Sunucu geçmişin yalnızca son `history_turns` (6) mesajını kullanır; fazlası boşa gönderilir.
 * Uzunluk sunucunun `MAX_HISTORY_TURN_LENGTH` sınırı içinde kalır.
 */
const HISTORY_TURNS = 6
const HISTORY_TURN_LENGTH = 4000

/**
 * Misafirin sunucuya göndereceği geçmiş: hata ve yalnızca arayüzde gösterilen mesajlar
 * çıkarılır, son turlar alınır ve uzun yanıtlar kırpılır.
 */
function historyOf(messages: Message[]): HistoryTurn[] {
  return messages
    .filter((message) => !message.isError && !message.isLocal)
    .slice(-HISTORY_TURNS)
    .map(({ role, content }) => ({ role, content: content.slice(0, HISTORY_TURN_LENGTH) }))
}

/**
 * Ekrandaki konuşmanın durumu: mesajlar, açık konuşmanın kimliği, yükleniyor bilgisi ve
 * bağlantı durumu. Soru gönderme, kayıtlı konuşmayı açma ve yeni sohbete geçme buradadır.
 *
 * Kullanıcı soru beklerken başka bir konuşmaya geçebilir; geç dönen yanıt yanlış konuşmaya
 * yazılmasın diye her istek bir "bilet" (`view`) alır ve dönüşte karşılaştırılır.
 */
export function useChat({
  onConversationChanged,
  sendsHistory,
  onRemaining,
  onQuotaStale,
  initialApiStatus,
}: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>([])
  // Gönderim anındaki mesajlar; sendMessage her mesajda yeniden kurulmasın diye ref'te tutulur.
  const messagesRef = useRef<Message[]>([])
  messagesRef.current = messages
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  // Ekrandaki konuşma her değiştiğinde artar. Yanıtı beklenen istek döndüğünde sayı değişmişse
  // kullanıcı başka bir konuşmaya geçmiştir; sonuç oraya yazılmaz.
  const view = useRef(0)

  // İlk bağlantı durumu açılıştaki sağlık denetiminden gelir; sonrasında her istek durumu
  // kendisi günceller.
  useEffect(() => {
    setApiStatus(initialApiStatus)
  }, [initialApiStatus])

  /** Mesajı listenin sonuna ekler; kimlik ve zaman burada verilir. */
  const append = useCallback((message: Omit<Message, 'id' | 'createdAt'>) => {
    setMessages((current) => [
      ...current,
      { ...message, id: crypto.randomUUID(), createdAt: new Date().toISOString() },
    ])
  }, [])

  /**
   * Soruyu gönderir. Soru hemen ekrana yazılır, yanıt gelince eklenir. Hata da bir mesaj olarak
   * konuşmaya düşer: kullanıcı ne olduğunu sorusunun hemen altında görür. Her durumda kalan
   * hak güncellenir.
   */
  const sendMessage = useCallback(
    async (text: string) => {
      const question = text.trim()
      if (!question || isLoading) return

      const history = sendsHistory ? historyOf(messagesRef.current) : []
      append({ role: 'user', content: question })
      setIsLoading(true)
      const ticket = view.current
      try {
        const answer = await askQuestion(question, conversationId, history)
        setApiStatus('online')
        onRemaining(answer.remaining)
        if (ticket !== view.current) {
          // Soru sunucuda kendi konuşmasına kaydedildi; yalnızca yan bar tazelenir.
          if (answer.conversationId !== null) onConversationChanged()
          return
        }
        append({
          role: 'assistant',
          content: answer.answer,
          sources: answer.sources,
          isPrepared: answer.prepared,
          suggestions: answer.suggestions.length ? answer.suggestions : undefined,
        })
        if (answer.conversationId !== null) {
          setConversationId(answer.conversationId)
          onConversationChanged()
        }
      } catch (error) {
        setApiStatus(error instanceof ApiUnreachableError ? 'offline' : 'online')
        onQuotaStale()
        if (ticket !== view.current) return
        append({
          role: 'assistant',
          content: error instanceof Error ? error.message : 'Beklenmeyen bir hata oluştu.',
          isError: true,
        })
      } finally {
        if (ticket === view.current) setIsLoading(false)
      }
    },
    [append, conversationId, isLoading, onConversationChanged, onQuotaStale, onRemaining, sendsHistory],
  )

  /** Önerilen sorulardan hiçbiri değilse: soru sunucuya gitmez, kullanıcı yeniden sorar. */
  const askAgain = useCallback(() => {
    append({ role: 'user', content: 'Diğer', isLocal: true })
    append({
      role: 'assistant',
      content: 'Anladım. Sorunu farklı sözcüklerle ya da biraz daha ayrıntıyla yazar mısın?',
      isLocal: true,
    })
  }, [append])

  /** Boş bir sohbete geçer; bekleyen yanıt varsa bilet artar ve o yanıt yok sayılır. */
  const startNew = useCallback(() => {
    view.current += 1
    setMessages([])
    setConversationId(null)
    setIsLoading(false)
  }, [])

  /** Kayıtlı bir konuşmayı açar; yüklenemezse hata mesajıyla boş bir konuşma gösterir. */
  const open = useCallback(async (id: string) => {
    const ticket = ++view.current
    setIsLoading(true)
    try {
      const stored = await fetchConversation(id)
      if (ticket !== view.current) return
      setMessages(stored)
      setConversationId(id)
    } catch (error) {
      if (ticket !== view.current) return
      setConversationId(null)
      setMessages([
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content:
            error instanceof Error ? error.message : 'Konuşma yüklenemedi. Lütfen tekrar deneyin.',
          isError: true,
          createdAt: new Date().toISOString(),
        },
      ])
    } finally {
      if (ticket === view.current) setIsLoading(false)
    }
  }, [])

  return { messages, conversationId, isLoading, apiStatus, sendMessage, askAgain, startNew, open }
}
