import { useEffect, useRef } from 'react'
import { GraduationCap, ShieldCheck } from 'lucide-react'
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
      <section className="signin-card">
        <span className="brand-mark signin-mark">
          <GraduationCap size={26} strokeWidth={1.8} />
        </span>

        <h1>{assistant.name}</h1>
        <p className="signin-scope">{assistant.scopeLabel}</p>
        <p className="signin-lead">
          Sohbetlerinin kaydedilmesi ve sorularının önceki yanıtlarla birlikte anlaşılması için
          Google hesabınla giriş yap.
        </p>

        <div className="signin-button" ref={buttonRef} />

        {error && <p className="signin-error">{error}</p>}

        <p className="signin-privacy">
          <ShieldCheck size={13} />
          Yalnızca adın ve e-posta adresin saklanır.
        </p>
      </section>
    </main>
  )
}
