import { ArrowUpRight, CircleHelp, GraduationCap, Plus, Sparkles } from 'lucide-react'
import { assistant } from '../config/assistant'

type SidebarProps = {
  onNewChat: () => void
}

export function Sidebar({ onNewChat }: SidebarProps) {
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

      <div className="sidebar-note">
        <span className="note-icon"><CircleHelp size={17} /></span>
        <div>
          <strong>Nasıl yardımcı olur?</strong>
          <p>{assistant.sidebarHelp}</p>
        </div>
      </div>

      <div className="sidebar-bottom">
        <div className="privacy-note">
          <span className="privacy-dot" />
          Üniversite verileriyle desteklenir
        </div>
      </div>
    </aside>
  )
}
