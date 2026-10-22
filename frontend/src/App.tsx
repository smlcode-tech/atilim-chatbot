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
import { useQuota } from './hooks/useQuota'
import { useTheme } from './hooks/useTheme'

// Splash screen en az bu kadar görünür (ms), auth ne kadar hızlı biterse bitsin.
const SPLASH_MIN_MS = 2200

/**
 * Kök bileşen: hook'ları birbirine bağlar ve hangi ekranın görüneceğine karar verir
 * (splash → giriş ya da sohbet).
 *
 * Durum hook'larda, görünüm bileşenlerde durur; App ikisini birleştirir. Hook'lar birbirini
 * tanımaz, birbirlerine buradaki geri çağrılarla haber verir (ör. yanıt gelince yan bar
 * tazelenir, kalan hak güncellenir).
 */
function App() {
  const { theme, toggle: toggleTheme } = useTheme()
  const {
    user,
    isGuest,
    canSignIn,
    guestQuestionLimit,
    apiStatus: initialApiStatus,
    isChecking,
    error,
    mountGoogleButton,
    continueAsGuest,
    signOut,
  } = useAuth()
  const { conversations, refresh, remove } = useConversations(user !== null && !isGuest)
  // Giriş, çıkış ya da misafire geçiş kalan hakkı değiştirir; kimlik değişince yeniden alınır.
  const { quota, refresh: refreshQuota, setRemaining } = useQuota(user === null ? null : user.id)
  const { messages, conversationId, isLoading, apiStatus, sendMessage, askAgain, startNew, open } = useChat({
    onConversationChanged: refresh,
    sendsHistory: isGuest,
    onRemaining: setRemaining,
    onQuotaStale: refreshQuota,
    initialApiStatus,
  })

  // Çıkışta ya da oturum düştüğünde sohbet ekranda kalmamalı: aynı tarayıcıda giriş yapan
  // bir sonraki kişi öncekinin konuşmasını görürdü.
  useEffect(() => {
    if (user === null) startNew()
  }, [user, startNew])

  // Composer'ın `key`'i: konuşma değişince artar ve yazma alanı yarım kalmış metinle birlikte
  // sıfırlanır.
  const [chatKey, setChatKey] = useState(0)
  // Composer'a "odaklan" isteği; her artış bir istek ("Diğer" seçildiğinde).
  const [composerFocus, setComposerFocus] = useState(0)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [showSplash, setShowSplash] = useState(true)
  // Splash iki koşul birlikte sağlanınca kalkar: en kısa süre doldu ve oturum denetimi bitti.
  // İkisi farklı anlarda biter; ref'ler hangisinin önce bittiğini öbür effect'e taşır.
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

  // Açık konuşma silinirse ekranda silinmiş bir konuşma kalmasın diye yeni sohbete geçilir.
  const deleteConversation = useCallback(
    (id: string) => {
      void remove(id)
      if (id === conversationId) startNewChat()
    },
    [conversationId, remove, startNewChat],
  )

  // ⌘K (macOS) / Ctrl+K: yeni sohbet. Tarayıcının kendi kısayolu engellenir.
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
  // "Diğer": soru sunucuya gitmez; kullanıcıdan yeniden yazması istenir ve yazma alanı odaklanır.
  const chooseOther = () => {
    askAgain()
    setComposerFocus((count) => count + 1)
  }
  const isEmpty = messages.length === 0

  return (
    <>
      <AnimatePresence>
        {showSplash && <SplashScreen key="splash" />}
      </AnimatePresence>

      {/* Sayfa, oturum kontrolü biter bitmez splash'in altında kurulur: Google düğmesi splash
          kalkmadan yüklenir, splash kalkınca hazır sayfa görünür. Giriş ve uygulama ekranları
          arasında kısa bir geçiş vardır; ilk açılışta geçişi splash yapar (initial={false}). */}
      <AnimatePresence mode="wait" initial={false}>
        {!isChecking && (
        <motion.div
          key={user === null ? 'signin' : 'app'}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
        >
        {user === null ? (
          <SignIn
            error={error}
            guestLimit={guestQuestionLimit}
            onMountGoogleButton={mountGoogleButton}
            onContinueAsGuest={continueAsGuest}
          />
        ) : (
          <main className={`app-shell ${isDrawerOpen ? 'drawer-open' : ''}`}>
            <Sidebar
              user={user}
              conversations={conversations}
              activeConversationId={conversationId}
              onNewChat={startNewChat}
              onOpenConversation={openConversation}
              onDeleteConversation={deleteConversation}
              // Giriş yapılandırılmamışsa misafirin gidebileceği bir giriş ekranı yoktur.
              onSignOut={isGuest && !canSignIn ? undefined : signOut}
              isGuest={isGuest}
            />

            <button
              className="drawer-backdrop"
              onClick={() => setIsDrawerOpen(false)}
              aria-label="Geçmişi kapat"
              tabIndex={isDrawerOpen ? 0 : -1}
            />

            <section className="chat-panel" aria-label={`${assistant.name} sohbeti`}>
              <Topbar status={apiStatus} theme={theme} onToggleTheme={toggleTheme}>
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
                  <MessageList
                    messages={messages}
                    isLoading={isLoading}
                    onPickSuggestion={send}
                    onChooseOther={chooseOther}
                  />
                )}
              </div>

              <Composer
                key={chatKey}
                disabled={isLoading}
                onSend={send}
                focusRequest={composerFocus}
                quota={quota}
                // Hakkı biten misafire giriş yapınca devam edebileceği söylenir.
                suggestsSignIn={isGuest && canSignIn}
              />
            </section>
          </main>
        )}
        </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

export default App
