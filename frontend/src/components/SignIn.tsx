import { useEffect, useRef } from 'react'
import { ShieldCheck } from 'lucide-react'
import { assistant } from '../config/assistant'

type SignInProps = {
  error: string | null
  onMountGoogleButton: (parent: HTMLElement) => void
}

export function SignIn({ error, onMountGoogleButton }: SignInProps) {
  const buttonRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (buttonRef.current) onMountGoogleButton(buttonRef.current)
  }, [onMountGoogleButton])

  return (
    <main className="signin-shell">
      {/* Sol — marka */}
      <div className="signin-brand">
        <div className="signin-brand-content">
          <img src="/favicon.svg" alt="Logo" className="signin-logo" />
          <p className="signin-brand-uni">{assistant.university.name}</p>
          <h1 className="signin-brand-name">{assistant.name}</h1>
          <p className="signin-brand-desc">{assistant.welcomeDescription}</p>

          <div className="signin-brand-divider" />

          <p className="signin-brand-footnote">{assistant.welcomeFootnote}</p>
        </div>
      </div>

      {/* Sağ — giriş formu */}
      <div className="signin-form-panel">
        <div className="signin-form-inner">
          <div className="signin-form-header">
            <h2 className="signin-form-title">Giriş yap</h2>
            <p className="signin-lead">
              Sohbet geçmişine erişmek ve daha akıllı yanıtlar almak için Google hesabınla devam et.
            </p>
          </div>

          <div className="signin-button" ref={buttonRef} />

          {error && <p className="signin-error">{error}</p>}

          <p className="signin-privacy">
            <ShieldCheck size={14} />
            Yalnızca adın ve e-posta adresin saklanır.
          </p>
        </div>
      </div>
    </main>
  )
}
