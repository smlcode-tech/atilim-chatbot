import { useCallback, useEffect, useRef, useState } from 'react'
import { checkHealth, fetchMe, readToken, signInWithGoogle, writeToken } from '../api/client'
import type { User } from '../types'

const GSI_SRC = 'https://accounts.google.com/gsi/client'
/** Sunucuda giriş yapılandırılmamışken kullanılan kimlik; geçmiş tutulmaz. */
const GUEST: User = { id: 'guest', email: 'Geçmiş kaydedilmiyor', name: 'Misafir' }
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined

type GoogleCredentialResponse = { credential: string }

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize(config: {
            client_id: string
            callback: (response: GoogleCredentialResponse) => void
          }): void
          renderButton(parent: HTMLElement, options: Record<string, unknown>): void
        }
      }
    }
  }
}

function loadGoogleScript(): Promise<void> {
  const existing = document.querySelector<HTMLScriptElement>(`script[src="${GSI_SRC}"]`)
  if (existing) return Promise.resolve()

  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = GSI_SRC
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Google giriş servisi yüklenemedi.'))
    document.head.appendChild(script)
  })
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [isChecking, setIsChecking] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isGuest, setIsGuest] = useState(false)
  // StrictMode etkileri iki kez çalıştırır; Google'ın düğmesi iki kez kurulmamalı.
  const isInitialized = useRef(false)

  useEffect(() => {
    let isMounted = true
    const resolveUser = async () => {
      const health = await checkHealth()
      if (health.online && !health.authRequired) {
        if (isMounted) {
          setIsGuest(true)
          setUser(GUEST)
        }
        return
      }
      if (readToken() === null) return
      try {
        const me = await fetchMe()
        if (isMounted) setUser(me)
      } catch {
        // Geçersiz oturumu istemci 401'de zaten siler; sunucuya ulaşılamaması oturumu bitirmez.
      }
    }
    void resolveUser().finally(() => {
      if (isMounted) setIsChecking(false)
    })
    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    const handleUnauthorized = () => {
      isInitialized.current = false
      setUser(null)
    }
    window.addEventListener('atilim:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('atilim:unauthorized', handleUnauthorized)
  }, [])

  const mountGoogleButton = useCallback(async (parent: HTMLElement) => {
    if (isInitialized.current) return
    if (!CLIENT_ID) {
      setError('Google giriş yapılandırılmamış (VITE_GOOGLE_CLIENT_ID eksik).')
      return
    }

    try {
      await loadGoogleScript()
    } catch {
      setError('Google giriş servisine ulaşılamadı. Bağlantınızı kontrol edin.')
      return
    }
    if (!window.google) return

    isInitialized.current = true
    window.google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: ({ credential }) => {
        setError(null)
        void signInWithGoogle(credential)
          .then(({ user: signedIn }) => setUser(signedIn))
          .catch((cause: unknown) => {
            isInitialized.current = false
            setError(cause instanceof Error ? cause.message : 'Giriş yapılamadı.')
          })
      },
    })
    window.google.accounts.id.renderButton(parent, {
      theme: 'outline',
      size: 'large',
      shape: 'pill',
      text: 'continue_with',
      locale: 'tr',
      width: 280,
    })
  }, [])

  const signOut = useCallback(() => {
    writeToken(null)
    isInitialized.current = false
    setUser(null)
  }, [])

  return { user, isGuest, isChecking, error, mountGoogleButton, signOut }
}
