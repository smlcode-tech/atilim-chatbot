import { useCallback, useEffect, useState } from 'react'
import { deleteConversation, fetchConversations } from '../api/client'
import type { ConversationSummary } from '../types'

export function useConversations(isSignedIn: boolean) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])

  const refresh = useCallback(async () => {
    if (!isSignedIn) return
    try {
      setConversations(await fetchConversations())
    } catch {
      // Geçmiş listesi ikincil bir bilgi: alınamazsa sohbet çalışmaya devam eder.
    }
  }, [isSignedIn])

  useEffect(() => {
    if (!isSignedIn) {
      setConversations([])
      return
    }
    void refresh()
  }, [isSignedIn, refresh])

  const remove = useCallback(async (id: string) => {
    setConversations((current) => current.filter((row) => row.id !== id))
    try {
      await deleteConversation(id)
    } catch {
      void refresh()
    }
  }, [refresh])

  return { conversations, refresh, remove }
}
