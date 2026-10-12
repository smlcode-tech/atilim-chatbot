import { assistant } from '../config/assistant'
import type { ApiStatus } from '../types'
import type { Theme } from '../hooks/useTheme'
import { ThemeToggle } from './ThemeToggle'

const statusLabels: Record<ApiStatus, string> = {
  online: 'Asistan hazır',
  checking: 'Bağlantı kontrol ediliyor',
  offline: 'Sunucuya ulaşılamıyor',
}

type TopbarProps = {
  status: ApiStatus
  theme: Theme
  onToggleTheme: () => void
  children?: React.ReactNode
}

export function Topbar({ status, theme, onToggleTheme, children }: TopbarProps) {
  return (
    <header className="topbar">
      {children}
      <div className="breadcrumbs">
        <span>{assistant.university.name}</span>
        <span className="breadcrumb-divider">/</span>
        <strong>{assistant.name}</strong>
      </div>
      <div className="topbar-end">
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        <div className={`topbar-status status-${status}`} aria-live="polite">
          <span className="status-indicator" />
          <span>{statusLabels[status]}</span>
        </div>
      </div>
    </header>
  )
}
