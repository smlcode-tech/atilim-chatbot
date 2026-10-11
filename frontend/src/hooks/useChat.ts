import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiUnreachableError, askQuestion, checkHealth } from '../api/client'
import type { ApiStatus, Message } from '../types'

function currentTime() {
  return new Intl.DateTimeFormat('tr-TR', { hour: '2-digit', minute: '2-digit' }).format(new Date())
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const nextId = useRef(1)

  useEffect(() => {
    let isMounted = true
    void checkHealth().then((isOnline) => {
      if (isMounted) setApiStatus(isOnline ? 'online' : 'offline')
    })
    return () => {
      isMounted = false
    }
  }, [])

  const append = useCallback((message: Omit<Message, 'id' | 'time'>) => {
    setMessages((current) => [...current, { ...message, id: nextId.current++, time: currentTime() }])
  }, [])

  const sendMessage = useCallback(
    async (text: string) => {
      const question = text.trim()
      if (!question || isLoading) return

      append({ role: 'user', content: question })
      setIsLoading(true)
      try {
        const { answer, sources, prepared } = await askQuestion(question)
        setApiStatus('online')
        append({ role: 'assistant', content: answer, sources, isPrepared: prepared })
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
    [append, isLoading],
  )

  const reset = useCallback(() => setMessages([]), [])

  return { messages, isLoading, apiStatus, sendMessage, reset }
}
