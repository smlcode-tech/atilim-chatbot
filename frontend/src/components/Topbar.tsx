import { assistant } from '../config/assistant'
import type { ApiStatus } from '../types'

const statusLabels: Record<ApiStatus, string> = {
  online: 'Asistan hazır',
  checking: 'Bağlantı kontrol ediliyor',
  offline: 'Sunucuya ulaşılamıyor',
}

type TopbarProps = {
  status: ApiStatus
  children?: React.ReactNode
}

export function Topbar({ status, children }: TopbarProps) {
  return (
    <header className="topbar">
      {children}
      <div className="breadcrumbs">
        <span>{assistant.university.name}</span>
        <span className="breadcrumb-divider">/</span>
        <strong>{assistant.name}</strong>
      </div>
      <div className={`topbar-status status-${status}`} aria-live="polite">
        <span className="status-indicator" />
        <span>{statusLabels[status]}</span>
      </div>
    </header>
  )
}
