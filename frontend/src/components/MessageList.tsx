import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
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

const timeFormat = new Intl.DateTimeFormat('tr-TR', { hour: '2-digit', minute: '2-digit' })

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

type Choices = {
  onPick: (question: string) => void
  onOther: () => void
}

function MessageRow({ message, choices }: { message: Message; choices?: Choices }) {
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

        {choices && message.suggestions && message.suggestions.length > 0 && (
          <ul className="message-choices" aria-label="Bunu mu sormak istedin?">
            {message.suggestions.map((question) => (
              <li key={question}>
                <button type="button" onClick={() => choices.onPick(question)}>
                  <CornerDownRight size={13} />
                  {question}
                </button>
              </li>
            ))}
            <li>
              <button type="button" className="choice-other" onClick={choices.onOther}>
                <PencilLine size={13} />
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
