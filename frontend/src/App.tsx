import { useCallback, useEffect, useState } from 'react'
import { PanelLeft } from 'lucide-react'
import { Composer } from './components/Composer'
import { MessageList } from './components/MessageList'
import { Sidebar } from './components/Sidebar'
import { SignIn } from './components/SignIn'
import { Topbar } from './components/Topbar'
import { Welcome } from './components/Welcome'
import { assistant } from './config/assistant'
import { useAuth } from './hooks/useAuth'
import { useChat } from './hooks/useChat'
import { useConversations } from './hooks/useConversations'

function App() {
  const { user, isChecking, error, mountGoogleButton, signOut } = useAuth()
  const { conversations, refresh, remove } = useConversations(user !== null)
  const { messages, conversationId, isLoading, apiStatus, sendMessage, startNew, open } = useChat({
    onConversationChanged: refresh,
  })

  // Yeni sohbette Composer'ı yeniden kurarak yazılmış taslağı temizler ve odağı geri verir.
  const [chatKey, setChatKey] = useState(0)
  // Dar ekranda yan bar üstten kayan bir çekmeceye dönüşür.
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

  const startNewChat = useCallback(() => {
    startNew()
    setChatKey((key) => key + 1)
    setIsDrawerOpen(false)
  }, [startNew])

  const openConversation = useCallback(
    (id: string) => {
      void open(id)
      setChatKey((key) => key + 1)
      setIsDrawerOpen(false)
    },
    [open],
  )

  const deleteConversation = useCallback(
    (id: string) => {
      void remove(id)
      if (id === conversationId) startNewChat()
    },
    [conversationId, remove, startNewChat],
  )

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        startNewChat()
      }
    }

    window.addEventListener('keydown', handleShortcut)
    return () => window.removeEventListener('keydown', handleShortcut)
  }, [startNewChat])

  if (isChecking) return <div className="boot-screen" aria-label="Yükleniyor" />

  if (user === null) {
    return <SignIn error={error} onMountGoogleButton={mountGoogleButton} />
  }

  const send = (text: string) => void sendMessage(text)
  const isEmpty = messages.length === 0

  return (
    <main className={`app-shell ${isDrawerOpen ? 'drawer-open' : ''}`}>
      <Sidebar
        user={user}
        conversations={conversations}
        activeConversationId={conversationId}
        onNewChat={startNewChat}
        onOpenConversation={openConversation}
        onDeleteConversation={deleteConversation}
        onSignOut={signOut}
      />

      <button
        className="drawer-backdrop"
        onClick={() => setIsDrawerOpen(false)}
        aria-label="Geçmişi kapat"
        tabIndex={isDrawerOpen ? 0 : -1}
      />

      <section className="chat-panel" aria-label={`${assistant.name} sohbeti`}>
        <Topbar status={apiStatus}>
          <button
            className="drawer-toggle"
            onClick={() => setIsDrawerOpen((open) => !open)}
            aria-label="Sohbet geçmişi"
            aria-expanded={isDrawerOpen}
          >
            <PanelLeft size={18} />
          </button>
        </Topbar>

        <div className={`conversation ${isEmpty ? 'conversation-welcome' : ''}`}>
          {isEmpty ? (
            <Welcome onPickSuggestion={send} />
          ) : (
            <MessageList messages={messages} isLoading={isLoading} />
          )}
        </div>

        <Composer key={chatKey} disabled={isLoading} onSend={send} />
      </section>
    </main>
  )
}

export default App
