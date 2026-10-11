import { useCallback, useEffect, useState } from 'react'
import { Composer } from './components/Composer'
import { MessageList } from './components/MessageList'
import { Sidebar } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import { Welcome } from './components/Welcome'
import { assistant } from './config/assistant'
import { useChat } from './hooks/useChat'

function App() {
  const { messages, isLoading, apiStatus, sendMessage, reset } = useChat()
  // Yeni sohbette Composer'ı yeniden kurarak yazılmış taslağı temizler ve odağı geri verir.
  const [chatKey, setChatKey] = useState(0)

  const startNewChat = useCallback(() => {
    reset()
    setChatKey((key) => key + 1)
  }, [reset])

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
    <main className="app-shell">
      <Sidebar onNewChat={startNewChat} />

      <section className="chat-panel" aria-label={`${assistant.name} sohbeti`}>
        <Topbar status={apiStatus} />

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
