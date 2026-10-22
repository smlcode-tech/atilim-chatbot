import { ArrowUp, Check, Sparkles } from 'lucide-react'
import { assistant } from '../config/assistant'

type WelcomeProps = {
  onPickSuggestion: (prompt: string) => void
}

/**
 * Boş sohbetin karşılama ekranı. Hazır soru kartları ilk soruyu yazma zahmetini kaldırır ve
 * asistanın neyi bildiğini gösterir; kart seçilince soru doğrudan gönderilir.
 */
export function Welcome({ onPickSuggestion }: WelcomeProps) {
  return (
    <div className="welcome-content">
      <div className="welcome-emblem">
        <Sparkles size={24} strokeWidth={1.8} />
        <span className="emblem-orbit" />
      </div>
      <p className="eyebrow">{assistant.scopeLabel}</p>
      <h1>
        Merhaba, nasıl
        <br />
        <span>yardımcı olabilirim?</span>
      </h1>
      <p className="welcome-description">{assistant.welcomeDescription}</p>

      <div className="suggestion-grid">
        {assistant.suggestions.map(({ icon: Icon, title, prompt }) => (
          <button className="suggestion-card" key={title} onClick={() => onPickSuggestion(prompt)}>
            <span className="suggestion-icon"><Icon size={18} /></span>
            <span className="suggestion-title">{title}</span>
            <span className="suggestion-prompt">{prompt}</span>
            <ArrowUp className="suggestion-arrow" size={15} />
          </button>
        ))}
      </div>
      <div className="welcome-footnote">
        <Check size={14} />
        {assistant.welcomeFootnote}
      </div>
    </div>
  )
}
