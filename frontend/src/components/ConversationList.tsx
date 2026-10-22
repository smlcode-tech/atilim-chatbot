import { MessageSquare, Trash2 } from 'lucide-react'
import type { ConversationSummary } from '../types'

type ConversationListProps = {
  conversations: ConversationSummary[]
  activeId: string | null
  onOpen: (id: string) => void
  onDelete: (id: string) => void
}

export function ConversationList({
  conversations,
  activeId,
  onOpen,
  onDelete,
}: ConversationListProps) {
  return (
    <div className="sidebar-history">
      <p className="section-label">GEÇMİŞ</p>

      {conversations.length === 0 ? (
        <p className="history-empty">Henüz kayıtlı sohbet yok.</p>
      ) : (
        <ul className="history-list">
          {conversations.map(({ id, title }) => (
            <li key={id} className={`history-item ${id === activeId ? 'history-item-active' : ''}`}>
              <button
                className="history-open"
                title={title}
                onClick={() => onOpen(id)}
                onTouchEnd={(e) => { e.preventDefault(); onOpen(id) }}
              >
                <MessageSquare size={15} />
                <span>{title}</span>
              </button>
              <button
                className="history-delete"
                aria-label={`${title} sohbetini sil`}
                onClick={() => onDelete(id)}
                onTouchEnd={(e) => { e.preventDefault(); onDelete(id) }}
              >
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
