import { useEffect, useRef } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowUpRight, CornerDownRight, PencilLine, Sparkles, UserRound } from 'lucide-react'
import { assistant } from '../config/assistant'
import type { Message } from '../types'

type MessageListProps = {
  messages: Message[]
  isLoading: boolean
  onPickSuggestion: (question: string) => void
  onChooseOther: () => void
}

// Biçimlendirici bir kez kurulur; her mesaj için yeniden oluşturmak gereksizdir.
const timeFormat = new Intl.DateTimeFormat('tr-TR', { hour: '2-digit', minute: '2-digit' })

// Yalnızca Google Haritalar'ın gömme adresleri haritaya çevrilir; başka bağlantı iframe olmaz.
const MAP_EMBED_PREFIX = 'https://www.google.com/maps/embed?'

/**
 * Yanıttaki bağlantılar yeni sekmede açılır. Harita gömme bağlantısı (bkz. backend
 * `parsers/university/iletisim.py`) bağlantının altında gömülü harita olarak da gösterilir.
 */
const markdownComponents: Components = {
  a: ({ href, children }) => {
    const link = (
      <a href={href} target="_blank" rel="noreferrer">
        {children}
      </a>
    )
    if (!href?.startsWith(MAP_EMBED_PREFIX)) return link
    return (
      <span className="markdown-map">
        {link}
        <iframe
          src={href}
          title="Harita"
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
          allowFullScreen
        />
      </span>
    )
  },
}

/**
 * Konuşmanın mesajları ve yanıt beklenirken "yazıyor" göstergesi. Yeni mesaj ya da gösterge
 * gelince liste en alta kayar.
 */
export function MessageList({
  messages,
  isLoading,
  onPickSuggestion,
  onChooseOther,
}: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className="message-list">
      {messages.map((message, index) => (
        <MessageRow
          key={message.id}
          message={message}
          // Seçenekler yalnızca son yanıtta seçilebilir; konuşma ilerlediyse geçmiştedir.
          choices={
            index === messages.length - 1 && !isLoading
              ? { onPick: onPickSuggestion, onOther: onChooseOther }
              : undefined
          }
        />
      ))}
      {isLoading && (
        <article className="message-row message-assistant">
          <span className="message-avatar assistant-avatar"><Sparkles size={17} /></span>
          <div className="message-content">
            <div className="message-meta"><strong>{assistant.name}</strong></div>
            <div className="typing-bubble" aria-label="Yanıt hazırlanıyor">
              <span /><span /><span />
            </div>
          </div>
        </article>
      )}
      <div ref={endRef} />
    </div>
  )
}

/** Yanıtlanamayan soruda sunulan seçeneklerin eylemleri: bir öneriyi sor ya da "Diğer". */
type Choices = {
  onPick: (question: string) => void
  onOther: () => void
}

/**
 * Tek mesaj. Asistan yanıtları Markdown olarak çizilir (model listeler ve kalın yazı üretir;
 * GFM tabloları da destekler); kullanıcının sorusu ve hata mesajları düz metindir, kullanıcının
 * yazdığı "*" gibi karakterler biçime dönüşmez. `react-markdown` ham HTML'i çizmez (metin
 * olarak gösterir) ve `javascript:` gibi tehlikeli bağlantıları temizler; model çıktısına
 * gömülü betik çalışmaz.
 */
function MessageRow({ message, choices }: { message: Message; choices?: Choices }) {
  const isAssistant = message.role === 'assistant'

  return (
    <article className={`message-row message-${message.role}`}>
      {isAssistant && (
        <span className="message-avatar assistant-avatar"><Sparkles size={17} /></span>
      )}
      <div className="message-content">
        <div className="message-meta">
          <strong>{isAssistant ? assistant.name : 'Sen'}</strong>
          <span>{timeFormat.format(new Date(message.createdAt))}</span>
        </div>
        <div className={`message-bubble ${message.isError ? 'message-error' : ''}`}>
          {isAssistant && !message.isError ? (
            <div className="markdown-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{message.content}</ReactMarkdown>
            </div>
          ) : (
            message.content
          )}
        </div>

        {choices && message.suggestions && message.suggestions.length > 0 && (
          <ul className="message-choices" aria-label="Bunu mu sormak istedin?">
            {message.suggestions.map((question) => (
              <li key={question}>
                <button type="button" onClick={() => choices.onPick(question)}>
                  <CornerDownRight size={15} />
                  {question}
                </button>
              </li>
            ))}
            <li>
              <button type="button" className="choice-other" onClick={choices.onOther}>
                <PencilLine size={15} />
                Diğer
              </button>
            </li>
          </ul>
        )}

        {message.sources && message.sources.length > 0 && (
          <ul className="message-sources" aria-label="Kaynaklar">
            {message.sources.map(({ title, url }) => (
              <li key={url}>
                <a href={url} target="_blank" rel="noreferrer">
                  {title}
                  <ArrowUpRight size={13} />
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
      {!isAssistant && (
        <span className="message-avatar user-avatar"><UserRound size={16} /></span>
      )}
    </article>
  )
}
