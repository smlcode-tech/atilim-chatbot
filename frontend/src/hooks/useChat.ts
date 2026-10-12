import { useCallback, useEffect, useState } from 'react'
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

  useEffect(() => {
    let isMounted = true
    void checkHealth().then((isOnline) => {
      if (isMounted) setApiStatus(isOnline ? 'online' : 'offline')
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
      try {
        const answer = await askQuestion(question, conversationId)
        setApiStatus('online')
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
        append({
          role: 'assistant',
          content: error instanceof Error ? error.message : 'Beklenmeyen bir hata oluştu.',
          isError: true,
        })
      } finally {
        setIsLoading(false)
      }
    },
    [append, conversationId, isLoading, onConversationChanged],
  )

  const startNew = useCallback(() => {
    setMessages([])
    setConversationId(null)
  }, [])

  const open = useCallback(async (id: string) => {
    setIsLoading(true)
    try {
      const stored = await fetchConversation(id)
      setMessages(stored)
      setConversationId(id)
    } catch (error) {
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
      setIsLoading(false)
    }
  }, [])

  return { messages, conversationId, isLoading, apiStatus, sendMessage, startNew, open }
}
