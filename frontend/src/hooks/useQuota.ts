import { useCallback, useEffect, useState } from 'react'
import { fetchQuota, type Quota } from '../api/client'

/**
 * Bugün kalan soru hakkı. `identity` değişince (giriş, çıkış, misafir) yeniden alınır; her
 * yanıt da kalan hakkı taşır (`setRemaining`). Hata ya da sınır yanıtından sonra `refresh`
 * sunucudaki gerçek değeri getirir: yanıtlanamayan soru sayaçtan geri düşülür.
 */
export function useQuota(identity: string | null) {
  const [quota, setQuota] = useState<Quota | null>(null)

  const refresh = useCallback(async () => {
    if (identity === null) return
    try {
      setQuota(await fetchQuota())
    } catch {
      // Kalan hak ikincil bir bilgi: alınamazsa gösterilmez, sohbet çalışmaya devam eder.
      setQuota(null)
    }
  }, [identity])

  useEffect(() => {
    setQuota(null)
    void refresh()
  }, [refresh])

  const setRemaining = useCallback((remaining: number | null) => {
    setQuota((current) => (current === null ? current : { ...current, remaining }))
  }, [])

  return { quota, refresh, setRemaining }
}
