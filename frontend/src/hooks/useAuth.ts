import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ApiUnreachableError,
  checkHealth,
  fetchMe,
  readToken,
  signInWithGoogle,
  userFromToken,
  writeToken,
} from '../api/client'
import type { User } from '../types'

/**
 * Oturum durumu: kim giriş yapmış (girişli kullanıcı, misafir ya da kimse), giriş açık mı ve
 * Google düğmesinin kurulması.
 */

/** Google Identity Services betiği; giriş ekranı açılınca yüklenir, açılışı yavaşlatmaz. */
const GSI_SRC = 'https://accounts.google.com/gsi/client'
/** Misafir kimliği: giriş yapılmadan ya da sunucuda giriş yapılandırılmamışken; geçmiş tutulmaz. */
const GUEST: User = { id: 'guest', email: 'Geçmiş kaydedilmiyor', name: 'Misafir' }
/** Misafir olarak devam etme seçimi sekme açık kaldıkça hatırlanır; sayfa yenilenince sorulmaz. */
const GUEST_KEY = 'atilim-assistant-guest'

/** Misafir seçimini sekme boyunca saklar ya da siler. */
function rememberGuest(isGuest: boolean) {
  try {
    if (isGuest) sessionStorage.setItem(GUEST_KEY, '1')
    else sessionStorage.removeItem(GUEST_KEY)
  } catch {
    // Depolama kapalıysa seçim yalnızca bu sayfa açıkken geçerlidir.
  }
}

/** Bu sekmede daha önce misafir olarak devam edildi mi. */
function choseGuest(): boolean {
  try {
    return sessionStorage.getItem(GUEST_KEY) === '1'
  } catch {
    return false
  }
}
/** Derleme sırasında gömülür (Vercel ortam değişkeni); yoksa Google düğmesi kurulmaz. */
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined

type GoogleCredentialResponse = { credential: string }

// Google betiğinin `window.google` üzerine kurduğu API'nin kullanılan kısmı; resmi tip paketi
// yalnızca bu birkaç işlev için eklenmez.
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

/** Google betiğini bir kez yükler; sayfada zaten varsa yeniden eklemez. */
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

/**
 * Açılışta oturumu çözer: önce sunucunun giriş açık olup olmadığına bakar (kapalıysa herkes
 * misafirdir), sonra saklanan jetonu doğrular, jeton yoksa sekmedeki misafir seçimini hatırlar.
 * `isChecking` bu süreç bitene kadar true kalır; App bu sırada splash gösterir.
 */
export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [isChecking, setIsChecking] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isGuest, setIsGuest] = useState(false)
  /** Sunucuda Google girişi var mı; yoksa herkes misafirdir ve giriş seçeneği gösterilmez. */
  const [canSignIn, setCanSignIn] = useState(true)
  const [guestQuestionLimit, setGuestQuestionLimit] = useState<number | null>(null)
  // StrictMode etkileri iki kez çalıştırır; Google'ın düğmesi iki kez kurulmamalı.
  const isInitialized = useRef(false)

  useEffect(() => {
    let isMounted = true
    const resolveUser = async () => {
      const health = await checkHealth()
      if (isMounted) setGuestQuestionLimit(health.guestQuestionLimit)
      if (health.online && !health.authRequired) {
        if (isMounted) {
          setCanSignIn(false)
          setIsGuest(true)
          setUser(GUEST)
        }
        return
      }
      const token = readToken()
      if (token === null) {
        if (choseGuest() && isMounted) {
          setIsGuest(true)
          setUser(GUEST)
        }
        return
      }
      try {
        const me = await fetchMe()
        if (isMounted) setUser(me)
      } catch (cause) {
        // Geçersiz oturumu istemci 401'de zaten siler. Sunucuya ulaşılamaması (ör. Render
        // uyanırken) oturumu bitirmez: kullanıcı giriş ekranına değil, çevrimdışı sohbete döner.
        if (cause instanceof ApiUnreachableError && isMounted) setUser(userFromToken(token))
      }
    }
    void resolveUser().finally(() => {
      if (isMounted) setIsChecking(false)
    })
    return () => {
      isMounted = false
    }
  }, [])

  // Herhangi bir istek 401 alınca (`api/client.ts`) oturum kapanır ve giriş ekranı gelir.
  // Düğme bayrağı da sıfırlanır: giriş ekranı yeniden kurulduğunda Google düğmesi yeniden çizilmeli.
  useEffect(() => {
    const handleUnauthorized = () => {
      isInitialized.current = false
      setUser(null)
    }
    window.addEventListener('atilim:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('atilim:unauthorized', handleUnauthorized)
  }, [])

  /**
   * Google düğmesini verilen öğeye çizer ve giriş sonucunu dinler. Düğmeyi ve giriş penceresini
   * Google çizer; uygulama yalnızca sonuçtaki kimlik jetonunu alıp sunucuya gönderir. Giriş
   * başarısız olursa bayrak sıfırlanır ki kullanıcı yeniden deneyebilsin.
   */
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
          .then(({ user: signedIn }) => {
            rememberGuest(false)
            setIsGuest(false)
            setUser(signedIn)
          })
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

  /** Giriş yapmadan devam eder; seçim sekme boyunca hatırlanır. */
  const continueAsGuest = useCallback(() => {
    rememberGuest(true)
    setError(null)
    setIsGuest(true)
    setUser(GUEST)
  }, [])

  /** Girişli kullanıcı için çıkış; misafir için giriş ekranına dönüş. */
  const signOut = useCallback(() => {
    writeToken(null)
    rememberGuest(false)
    isInitialized.current = false
    setIsGuest(false)
    setUser(null)
  }, [])

  return {
    user,
    isGuest,
    canSignIn,
    guestQuestionLimit,
    isChecking,
    error,
    mountGoogleButton,
    continueAsGuest,
    signOut,
  }
}
