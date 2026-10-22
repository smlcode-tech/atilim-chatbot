import { useCallback, useEffect, useRef, useState } from 'react'
import { deleteConversation, fetchConversations } from '../api/client'
import type { ConversationSummary } from '../types'

/** Silinen konuşma bu süre boyunca geri alınabilir; süre dolunca sunucudan silinir. */
const UNDO_MS = 5000

type PendingDelete = { conversation: ConversationSummary; timer: number }

export function useConversations(isSignedIn: boolean) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [pendingDelete, setPendingDelete] = useState<ConversationSummary | null>(null)
  const pending = useRef<PendingDelete | null>(null)

  const refresh = useCallback(async () => {
    if (!isSignedIn) return
    try {
      const rows = await fetchConversations()
      // Geri alma süresi dolmamış konuşma sunucuda hâlâ durur; listede yeniden belirmemeli.
      setConversations(rows.filter((row) => row.id !== pending.current?.conversation.id))
    } catch {
      // Geçmiş listesi ikincil bir bilgi: alınamazsa sohbet çalışmaya devam eder.
    }
  }, [isSignedIn])

  const commit = useCallback(
    async (id: string) => {
      try {
        await deleteConversation(id)
      } catch {
        void refresh()
      }
    },
    [refresh],
  )

  /** Bekleyen silmeyi beklemeden sunucuya gönderir (yeni silme, çıkış ya da sayfa kapanışı). */
  const flush = useCallback(() => {
    const current = pending.current
    if (current === null) return
    window.clearTimeout(current.timer)
    pending.current = null
    setPendingDelete(null)
    void commit(current.conversation.id)
  }, [commit])

  useEffect(() => {
    if (!isSignedIn) {
      setConversations([])
      return
    }
    void refresh()
  }, [isSignedIn, refresh])

  useEffect(() => {
    window.addEventListener('pagehide', flush)
    return () => window.removeEventListener('pagehide', flush)
  }, [flush])

  const remove = useCallback(
    (id: string) => {
      const conversation = conversations.find((row) => row.id === id)
      if (conversation === undefined) return
      flush()
      setConversations((current) => current.filter((row) => row.id !== id))
      const timer = window.setTimeout(() => {
        pending.current = null
        setPendingDelete(null)
        void commit(id)
      }, UNDO_MS)
      pending.current = { conversation, timer }
      setPendingDelete(conversation)
    },
    [commit, conversations, flush],
  )

  const undoDelete = useCallback(() => {
    const current = pending.current
    if (current === null) return
    window.clearTimeout(current.timer)
    pending.current = null
    setPendingDelete(null)
    setConversations((rows) =>
      [...rows, current.conversation].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    )
  }, [])

  return { conversations, refresh, remove, pendingDelete, undoDelete, flushDelete: flush }
}
