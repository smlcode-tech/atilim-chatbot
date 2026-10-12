import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowUpRight, Info, Sparkles, UserRound } from 'lucide-react'
import { assistant } from '../config/assistant'
import type { Message } from '../types'

type MessageListProps = {
  messages: Message[]
  isLoading: boolean
}

const timeFormat = new Intl.DateTimeFormat('tr-TR', { hour: '2-digit', minute: '2-digit' })

export function MessageList({ messages, isLoading }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className="message-list">
      {messages.map((message) => (
        <MessageRow key={message.id} message={message} />
      ))}
      {isLoading && (
        <article className="message-row message-assistant">
          <span className="message-avatar assistant-avatar"><Sparkles size={15} /></span>
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

function MessageRow({ message }: { message: Message }) {
  const isAssistant = message.role === 'assistant'

  return (
    <article className={`message-row message-${message.role}`}>
      {isAssistant && (
        <span className="message-avatar assistant-avatar"><Sparkles size={15} /></span>
      )}
      <div className="message-content">
        <div className="message-meta">
          <strong>{isAssistant ? assistant.name : 'Sen'}</strong>
          <span>{timeFormat.format(new Date(message.createdAt))}</span>
        </div>
        <div className={`message-bubble ${message.isError ? 'message-error' : ''}`}>
          {isAssistant && !message.isError ? (
            <div className="markdown-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          ) : (
            message.content
          )}
        </div>
        {message.isPrepared && (
          <p className="message-notice">
            <Info size={11} />
            Yapay zekâ modeli şu anda yanıt üretemiyor; bu, kaynak sayfadan hazırlanmış bir yanıttır.
          </p>
        )}
        {message.sources && message.sources.length > 0 && (
          <ul className="message-sources" aria-label="Kaynaklar">
            {message.sources.map(({ title, url }) => (
              <li key={url}>
                <a href={url} target="_blank" rel="noreferrer">
                  {title}
                  <ArrowUpRight size={11} />
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
      {!isAssistant && (
        <span className="message-avatar user-avatar"><UserRound size={14} /></span>
      )}
    </article>
  )
}
