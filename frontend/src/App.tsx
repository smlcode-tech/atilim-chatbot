import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { PanelLeft } from 'lucide-react'
import { Composer } from './components/Composer'
import { MessageList } from './components/MessageList'
import { Sidebar } from './components/Sidebar'
import { SignIn } from './components/SignIn'
import { SplashScreen } from './components/SplashScreen'
import { Topbar } from './components/Topbar'
import { Welcome } from './components/Welcome'
import { assistant } from './config/assistant'
import { useAuth } from './hooks/useAuth'
import { useChat } from './hooks/useChat'
import { useConversations } from './hooks/useConversations'

// Splash screen en az bu kadar görünür (ms), auth ne kadar hızlı biterse bitsin.
const SPLASH_MIN_MS = 2200

function App() {
  const { user, isChecking, error, mountGoogleButton, signOut } = useAuth()
  const { conversations, refresh, remove } = useConversations(user !== null)
  const { messages, conversationId, isLoading, apiStatus, sendMessage, startNew, open } = useChat({
    onConversationChanged: refresh,
  })

  const [chatKey, setChatKey] = useState(0)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [showSplash, setShowSplash] = useState(true)
  const minElapsed = useRef(false)
  const isCheckingRef = useRef(isChecking)

  useEffect(() => {
    isCheckingRef.current = isChecking
    // Minimum süre geçtikten sonra auth da bittiyse splash'i kapat.
    if (!isChecking && minElapsed.current) setShowSplash(false)
  }, [isChecking])

  useEffect(() => {
    const t = setTimeout(() => {
      minElapsed.current = true
      // Auth zaten bitmişse hemen kapat; yoksa yukarıdaki effect kapatır.
      if (!isCheckingRef.current) setShowSplash(false)
    }, SPLASH_MIN_MS)
    return () => clearTimeout(t)
  }, [])

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

  const send = (text: string) => void sendMessage(text)
  const isEmpty = messages.length === 0

  return (
    <>
      <AnimatePresence>
        {showSplash && <SplashScreen key="splash" />}
      </AnimatePresence>

      {!showSplash && (
        <motion.div
          style={{ flex: 1, display: 'contents' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        >
        {user === null ? (
          <SignIn error={error} onMountGoogleButton={mountGoogleButton} />
        ) : (
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
        )}
        </motion.div>
      )}
    </>
  )
}

export default App
