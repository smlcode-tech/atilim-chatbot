import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ArrowDown,
  ArrowUp,
  BookOpen,
  BrainCircuit,
  Check,
  ChevronDown,
  CircleHelp,
  GraduationCap,
  Plus,
  Sparkles,
  UserRound,
} from 'lucide-react'

type Message = {
  id: number
  role: 'assistant' | 'user'
  content: string
  time: string
  isError?: boolean
}

type ApiStatus = 'checking' | 'online' | 'offline'

const suggestions = [
  {
    icon: UserRound,
    title: 'Akademik kadroyu tanı',
    prompt: 'Yazılım Mühendisliği bölümündeki akademik personeli tanıtır mısın?',
  },
  {
    icon: BrainCircuit,
    title: 'Araştırma konuları',
    prompt: 'Makine öğrenmesi üzerine çalışan akademisyenler kimler?',
  },
  {
    icon: BookOpen,
    title: 'Bir akademisyeni keşfet',
    prompt: 'Ali Yazıcı’nın araştırma konuları neler?',
  },
]

function currentTime() {
  return new Intl.DateTimeFormat('tr-TR', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date())
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let isMounted = true
    fetch('/api/health')
      .then((response) => {
        if (!response.ok) throw new Error('API bağlantısı kurulamadı.')
        return response.json() as Promise<{ status?: string }>
      })
      .then((health) => {
        if (isMounted) setApiStatus(health.status === 'ok' ? 'online' : 'offline')
      })
      .catch(() => {
        if (isMounted) setApiStatus('offline')
      })

    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setMessages([])
        setQuestion('')
        textareaRef.current?.focus()
      }
    }

    window.addEventListener('keydown', handleShortcut)
    return () => window.removeEventListener('keydown', handleShortcut)
  }, [])

  async function sendMessage(text = question) {
    const cleanQuestion = text.trim()
    if (!cleanQuestion || isLoading) return

    setQuestion('')
    setMessages((current) => [
      ...current,
      { id: Date.now(), role: 'user', content: cleanQuestion, time: currentTime() },
    ])
    setIsLoading(true)

    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: cleanQuestion }),
      })
      setApiStatus('online')
      const payload: { answer?: string; error?: string } = await response.json()

      if (!response.ok) {
        throw new Error(payload.error || 'Yanıt alınamadı. Lütfen tekrar deneyin.')
      }
      const assistantAnswer = payload.answer
      if (!assistantAnswer) {
        throw new Error('Asistandan boş bir yanıt alındı. Lütfen tekrar deneyin.')
      }

      setMessages((current) => [
        ...current,
        { id: Date.now() + 1, role: 'assistant', content: assistantAnswer, time: currentTime() },
      ])
    } catch (error) {
      const message =
        error instanceof TypeError
          ? 'Sunucuya bağlanılamadı. API sunucusunun çalıştığını kontrol edin.'
          : error instanceof Error
            ? error.message
            : 'Beklenmeyen bir hata oluştu.'
      if (error instanceof TypeError) setApiStatus('offline')
      setMessages((current) => [
        ...current,
        { id: Date.now() + 1, role: 'assistant', content: message, time: currentTime(), isError: true },
      ])
    } finally {
      setIsLoading(false)
      textareaRef.current?.focus()
    }
  }

  function startNewChat() {
    setMessages([])
    setQuestion('')
    textareaRef.current?.focus()
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="https://www.atilim.edu.tr/"
          target="_blank"
          rel="noreferrer"
          aria-label="Atılım Üniversitesi ana sayfası"
        >
          <span className="brand-mark">
            <GraduationCap size={22} strokeWidth={1.8} />
          </span>
          <span className="brand-copy">
            <strong>Atılım</strong>
            <span>AKADEMİK ASİSTAN</span>
          </span>
        </a>

        <button className="new-chat-button" onClick={startNewChat}>
          <Plus size={18} />
          <span>Yeni sohbet</span>
          <span className="shortcut">⌘ K</span>
        </button>

        <div className="sidebar-section">
          <p className="section-label">KEŞFET</p>
          <div className="nav-item nav-item-active">
            <Sparkles size={17} />
            <span>Akademik asistan</span>
            <span className="active-dot" />
          </div>
          <a
            className="nav-item"
            href="https://www.atilim.edu.tr/tr/se/page/2286/akademik-personel"
            target="_blank"
            rel="noreferrer"
          >
            <GraduationCap size={17} />
            <span>Akademik kadro</span>
            <ArrowDown className="external-icon" size={13} />
          </a>
        </div>

        <div className="sidebar-note">
          <span className="note-icon"><CircleHelp size={17} /></span>
          <div>
            <strong>Nasıl yardımcı olur?</strong>
            <p>Akademik personel, araştırma alanları ve iletişim bilgileri hakkında soru sor.</p>
          </div>
        </div>

        <div className="sidebar-bottom">
          <div className="privacy-note">
            <span className="privacy-dot" />
            Üniversite verileriyle desteklenir
          </div>
          <div className="profile-button">
            <span className="profile-avatar">B</span>
            <span className="profile-copy">
              <strong>Hoş geldin</strong>
              <span>Misafir kullanıcı</span>
            </span>
            <ChevronDown size={16} />
          </div>
        </div>
      </aside>

      <section className="chat-panel" aria-label="Akademik asistan sohbeti">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Atılım Üniversitesi</span>
            <span className="breadcrumb-divider">/</span>
            <strong>Akademik Asistan</strong>
          </div>
          <div className={`topbar-status status-${apiStatus}`} aria-live="polite">
            <span className="status-indicator" />
            <span>
              {apiStatus === 'online'
                ? 'Asistan hazır'
                : apiStatus === 'checking'
                  ? 'Bağlantı kontrol ediliyor'
                  : 'Sunucuya ulaşılamıyor'}
            </span>
          </div>
        </header>

        <div className={`conversation ${messages.length === 0 ? 'conversation-welcome' : ''}`}>
          {messages.length === 0 ? (
            <div className="welcome-content">
              <div className="welcome-emblem">
                <Sparkles size={24} strokeWidth={1.8} />
                <span className="emblem-orbit" />
              </div>
              <p className="eyebrow">ATILIM ÜNİVERSİTESİ · YAZILIM MÜHENDİSLİĞİ</p>
              <h1>
                Merhaba, nasıl
                <br />
                <span>yardımcı olabilirim?</span>
              </h1>
              <p className="welcome-description">
                Akademik kadromuz, araştırma alanları ve daha fazlası hakkında merak ettiklerini sor.
              </p>

              <div className="suggestion-grid">
                {suggestions.map(({ icon: Icon, title, prompt }) => (
                  <button
                    className="suggestion-card"
                    key={title}
                    onClick={() => void sendMessage(prompt)}
                  >
                    <span className="suggestion-icon"><Icon size={18} /></span>
                    <span className="suggestion-title">{title}</span>
                    <span className="suggestion-prompt">{prompt}</span>
                    <ArrowUp className="suggestion-arrow" size={15} />
                  </button>
                ))}
              </div>
              <div className="welcome-footnote">
                <Check size={14} />
                Cevaplar üniversitenin akademik personel verilerine dayanır.
              </div>
            </div>
          ) : (
            <div className="message-list">
              {messages.map((message) => (
                <article className={`message-row message-${message.role}`} key={message.id}>
                  {message.role === 'assistant' && (
                    <span className="message-avatar assistant-avatar">
                      <Sparkles size={15} />
                    </span>
                  )}
                  <div className="message-content">
                    <div className="message-meta">
                      <strong>{message.role === 'assistant' ? 'Akademik Asistan' : 'Sen'}</strong>
                      <span>{message.time}</span>
                    </div>
                    <div className={`message-bubble ${message.isError ? 'message-error' : ''}`}>
                      {message.role === 'assistant' && !message.isError ? (
                        <div className="markdown-content">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        message.content
                      )}
                    </div>
                  </div>
                  {message.role === 'user' && <span className="message-avatar user-avatar">B</span>}
                </article>
              ))}
              {isLoading && (
                <article className="message-row message-assistant">
                  <span className="message-avatar assistant-avatar"><Sparkles size={15} /></span>
                  <div className="message-content">
                    <div className="message-meta"><strong>Akademik Asistan</strong></div>
                    <div className="typing-bubble" aria-label="Yanıt hazırlanıyor">
                      <span /><span /><span />
                    </div>
                  </div>
                </article>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="composer-area">
          <form
            className="composer"
            onSubmit={(event) => {
              event.preventDefault()
              void sendMessage()
            }}
          >
            <textarea
              ref={textareaRef}
              aria-label="Mesajınız"
              placeholder="Merak ettiğin bir şeyi sor..."
              value={question}
              rows={1}
              onChange={(event) => {
                setQuestion(event.target.value)
                event.target.style.height = 'auto'
                event.target.style.height = `${Math.min(event.target.scrollHeight, 160)}px`
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  void sendMessage()
                }
              }}
              disabled={isLoading}
            />
            <div className="composer-footer">
              <span className="composer-hint">
                <span className="hint-key">↵</span> gönder
                <span className="hint-divider">·</span>
                <span className="hint-key">⇧ ↵</span> yeni satır
              </span>
              <button
                className="send-button"
                type="submit"
                aria-label="Mesajı gönder"
                disabled={!question.trim() || isLoading}
              >
                <ArrowUp size={18} strokeWidth={2.3} />
              </button>
            </div>
          </form>
          <p className="disclaimer">
            Akademik Asistan hata yapabilir. Önemli bilgileri <a href="https://www.atilim.edu.tr/tr/se/page/2286/akademik-personel" target="_blank" rel="noreferrer">kaynaklardan</a> doğrulayın.
          </p>
        </div>
      </section>
    </main>
  )
}

export default App
