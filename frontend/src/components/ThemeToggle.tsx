import { Moon, Sun } from 'lucide-react'
import type { Theme } from '../hooks/useTheme'

type ThemeToggleProps = {
  theme: Theme
  onToggle: () => void
}

export function ThemeToggle({ theme, onToggle }: ThemeToggleProps) {
  return (
    <button
      className="theme-toggle"
      onClick={onToggle}
      aria-label={theme === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç'}
      title={theme === 'dark' ? 'Açık tema' : 'Koyu tema'}
    >
      {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
    </button>
  )
}
