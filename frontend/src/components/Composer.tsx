import { useEffect, useRef, useState } from 'react'
import { ArrowUp } from 'lucide-react'
import type { Quota } from '../api/client'
import { assistant } from '../config/assistant'

/** Yazma alanı metinle birlikte bu yüksekliğe (px) kadar uzar, sonra kendi içinde kayar. */
const MAX_TEXTAREA_HEIGHT = 160

type ComposerProps = {
  disabled: boolean
  onSend: (text: string) => void
  /** Her artışta yazma alanı odaklanır (ör. "Diğer" seçildiğinde). */
  focusRequest?: number
  /** Bugün kalan soru hakkı; bilinmiyorsa gösterilmez. */
  quota?: Quota | null
  /** Hak bitince giriş yaparak devam edilebileceği söylenir (misafir). */
  suggestsSignIn?: boolean
}

/** Bu kadar ya da daha az hak kalınca sayı vurgulanır. */
const LOW_QUOTA = 2

/**
 * Soru yazma alanı, gönder düğmesi ve kalan soru hakkı. Enter gönderir, Shift+Enter yeni satır
 * açar. Yanıt beklenirken kilitlenir: aynı anda iki soru gönderilip sıraları karışmaz.
 */
export function Composer({
  disabled,
  onSend,
  focusRequest = 0,
  quota = null,
  suggestsSignIn = false,
}: ComposerProps) {
  const [question, setQuestion] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Yanıt gelince (kilit açılınca) ya da odak istendiğinde yazma alanına dönülür: kullanıcı
  // fareye uzanmadan bir sonraki soruyu yazabilir.
  useEffect(() => {
    if (!disabled) textareaRef.current?.focus()
  }, [disabled, focusRequest])

  /** Boş değilse gönderir, alanı temizler ve yüksekliği tek satıra döndürür. */
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
            <span className="hint-divider" aria-hidden="true">·</span>
            <span className="hint-key">⇧ ↵</span> yeni satır
          </span>
          {quota !== null && quota.remaining !== null && (
            <QuotaNote remaining={quota.remaining} limit={quota.limit} suggestsSignIn={suggestsSignIn} />
          )}
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

/** Kalan hak notu; az kalınca ve bitince farklı renkte gösterilir. */
function QuotaNote({
  remaining,
  limit,
  suggestsSignIn,
}: {
  remaining: number
  limit: number
  suggestsSignIn: boolean
}) {
  const level = remaining === 0 ? 'quota-out' : remaining <= LOW_QUOTA ? 'quota-low' : ''
  return (
    // role="status": hak azaldığında ekran okuyucu da duyurur.
    <span className={`composer-quota ${level}`} role="status">
      {remaining === 0 ? (
        <>Bugünlük soru hakkın bitti{suggestsSignIn && <>; Google ile giriş yaparak devam edebilirsin</>}</>
      ) : (
        <>
          Bugün <strong>{remaining}</strong>/{limit} soru hakkın kaldı
        </>
      )}
    </span>
  )
}
