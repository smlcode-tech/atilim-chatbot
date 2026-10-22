import { useEffect, useRef } from 'react'
import { ShieldCheck, UserRound } from 'lucide-react'
import { assistant } from '../config/assistant'

type SignInProps = {
  error: string | null
  guestLimit: number | null
  onMountGoogleButton: (parent: HTMLElement) => void
  onContinueAsGuest: () => void
}

/**
 * Giriş ekranı: Google ile giriş ya da misafir olarak devam. Sol panel marka, sağ panel form;
 * dar ekranda alt alta dizilir.
 */
export function SignIn({ error, guestLimit, onMountGoogleButton, onContinueAsGuest }: SignInProps) {
  const buttonRef = useRef<HTMLDivElement>(null)

  // Google düğmesi React dışında, Google betiği tarafından bu boş kutuya çizilir.
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

          <div className="signin-divider"><span>ya da</span></div>

          <button type="button" className="signin-guest" onClick={onContinueAsGuest}>
            <UserRound size={16} />
            Misafir olarak devam et
          </button>
          <p className="signin-guest-note">
            Geçmiş kaydedilmez
            {guestLimit !== null && <>; günde {guestLimit} soru sorabilirsin</>}.
          </p>

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
