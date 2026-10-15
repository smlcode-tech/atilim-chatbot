import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ApiUnreachableError,
  askQuestion,
  checkHealth,
  fetchConversation,
} from '../api/client'
import type { ApiStatus, Message } from '../types'

type UseChatOptions = {
  /** Yeni bir konuşma açıldığında ya da bir konuşmaya yazıldığında yan bar tazelenir. */
  onConversationChanged: () => void
}

export function useChat({ onConversationChanged }: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  // Ekrandaki konuşma her değiştiğinde artar. Yanıtı beklenen istek döndüğünde sayı değişmişse
  // kullanıcı başka bir konuşmaya geçmiştir; sonuç oraya yazılmaz.
  const view = useRef(0)

  useEffect(() => {
    let isMounted = true
    void checkHealth().then(({ online }) => {
      if (isMounted) setApiStatus(online ? 'online' : 'offline')
    })
    return () => {
      isMounted = false
    }
  }, [])

  const append = useCallback((message: Omit<Message, 'id' | 'createdAt'>) => {
    setMessages((current) => [
      ...current,
      { ...message, id: crypto.randomUUID(), createdAt: new Date().toISOString() },
    ])
  }, [])

  const sendMessage = useCallback(
    async (text: string) => {
      const question = text.trim()
      if (!question || isLoading) return

      append({ role: 'user', content: question })
      setIsLoading(true)
      const ticket = view.current
      try {
        const answer = await askQuestion(question, conversationId)
        setApiStatus('online')
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
        })
        if (answer.conversationId !== null) {
          setConversationId(answer.conversationId)
          onConversationChanged()
        }
      } catch (error) {
        setApiStatus(error instanceof ApiUnreachableError ? 'offline' : 'online')
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
    [append, conversationId, isLoading, onConversationChanged],
  )

  const startNew = useCallback(() => {
    view.current += 1
    setMessages([])
    setConversationId(null)
    setIsLoading(false)
  }, [])

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

  return { messages, conversationId, isLoading, apiStatus, sendMessage, startNew, open }
}
