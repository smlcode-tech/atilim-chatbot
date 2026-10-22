import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

/** Tarayıcı çubuğunun rengi; temanın zemin rengiyle (`--bg`) aynı. */
const THEME_COLORS: Record<Theme, string> = { light: '#f5f7fc', dark: '#0f111a' }

/** Başlangıç teması: index.html'in uyguladığı, yoksa saklanan, yoksa sistemin tercihi. */
function getInitialTheme(): Theme {
  // index.html'deki betik temayı ilk çizimden önce ayarlar; React aynı değerle başlar.
  const applied = document.documentElement.getAttribute('data-theme')
  if (applied === 'light' || applied === 'dark') return applied
  try {
    const stored = localStorage.getItem('theme')
    if (stored === 'light' || stored === 'dark') return stored
  } catch {}
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/**
 * Açık/koyu tema. Tema `<html data-theme>` özniteliğiyle uygulanır; renkler CSS değişkenleri
 * olduğu için bileşenler temayı bilmez. Seçim saklanır, sonraki açılışta korunur.
 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLORS[theme])
    try {
      localStorage.setItem('theme', theme)
    } catch {}
  }, [theme])

  const toggle = () => setTheme((t) => (t === 'light' ? 'dark' : 'light'))

  return { theme, toggle }
}
