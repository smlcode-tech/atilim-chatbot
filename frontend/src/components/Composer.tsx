import { useEffect, useRef, useState } from 'react'
import { ArrowUp } from 'lucide-react'
import { assistant } from '../config/assistant'

const MAX_TEXTAREA_HEIGHT = 160

type ComposerProps = {
  disabled: boolean
  onSend: (text: string) => void
  /** Her artışta yazma alanı odaklanır (ör. "Diğer" seçildiğinde). */
  focusRequest?: number
}

export function Composer({ disabled, onSend, focusRequest = 0 }: ComposerProps) {
  const [question, setQuestion] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!disabled) textareaRef.current?.focus()
  }, [disabled, focusRequest])

  function submit() {
    if (!question.trim() || disabled) return
    onSend(question)
    setQuestion('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  return (
    <div className="composer-area">
      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
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
            event.target.style.height = `${Math.min(event.target.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              submit()
            }
          }}
          disabled={disabled}
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
            disabled={!question.trim() || disabled}
          >
            <ArrowUp size={20} strokeWidth={2.3} />
          </button>
        </div>
      </form>
      <p className="disclaimer">
        {assistant.name} hata yapabilir. Önemli bilgileri yanıtın altındaki kaynaklardan doğrulayın.
      </p>
    </div>
  )
}
