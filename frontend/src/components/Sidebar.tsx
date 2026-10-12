import { ArrowUpRight, CircleHelp, GraduationCap, LogOut, Plus, Sparkles } from 'lucide-react'
import { assistant } from '../config/assistant'
import type { ConversationSummary, User } from '../types'
import { ConversationList } from './ConversationList'

type SidebarProps = {
  user: User
  conversations: ConversationSummary[]
  activeConversationId: string | null
  onNewChat: () => void
  onOpenConversation: (id: string) => void
  onDeleteConversation: (id: string) => void
  onSignOut: () => void
}

export function Sidebar({
  user,
  conversations,
  activeConversationId,
  onNewChat,
  onOpenConversation,
  onDeleteConversation,
  onSignOut,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <a
        className="brand"
        href={assistant.university.url}
        target="_blank"
        rel="noreferrer"
        aria-label={`${assistant.university.name} ana sayfası`}
      >
        <span className="brand-mark">
          <GraduationCap size={22} strokeWidth={1.8} />
        </span>
        <span className="brand-copy">
          <strong>{assistant.university.shortName}</strong>
          <span>{assistant.name.toLocaleUpperCase('tr-TR')}</span>
        </span>
      </a>

      <button className="new-chat-button" onClick={onNewChat}>
        <Plus size={18} />
        <span>Yeni sohbet</span>
        <span className="shortcut">⌘ K</span>
      </button>

      <div className="sidebar-section">
        <p className="section-label">KEŞFET</p>
        <div className="nav-item nav-item-active">
          <Sparkles size={17} />
          <span>{assistant.name}</span>
          <span className="active-dot" />
        </div>
        {assistant.links.map(({ label, url }) => (
          <a className="nav-item" key={url} href={url} target="_blank" rel="noreferrer">
            <GraduationCap size={17} />
            <span>{label}</span>
            <ArrowUpRight className="external-icon" size={13} />
          </a>
        ))}
      </div>

      <ConversationList
        conversations={conversations}
        activeId={activeConversationId}
        onOpen={onOpenConversation}
        onDelete={onDeleteConversation}
      />

      <div className="sidebar-note">
        <span className="note-icon"><CircleHelp size={17} /></span>
        <div>
          <strong>Nasıl yardımcı olur?</strong>
          <p>{assistant.sidebarHelp}</p>
        </div>
      </div>

      <div className="sidebar-bottom">
        <div className="sidebar-user">
          <span className="user-initial">{user.name.slice(0, 1).toLocaleUpperCase('tr-TR')}</span>
          <span className="user-copy">
            <strong>{user.name}</strong>
            <span>{user.email}</span>
          </span>
          <button className="sign-out" onClick={onSignOut} aria-label="Çıkış yap">
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  )
}
