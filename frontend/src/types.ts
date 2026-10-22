/**
 * Arayüzün ortak tipleri. Sunucunun biçiminden bağımsızdır; dönüşüm `api/client.ts`'te yapılır.
 */

/** Yanıtın altında gösterilen kaynak sayfa. */
export type SourceLink = {
  title: string
  url: string
}

/** Ekrandaki bir mesaj: kullanıcının sorusu ya da asistanın yanıtı (hata ve yerel mesajlar dahil). */
export type Message = {
  id: string
  role: 'assistant' | 'user'
  content: string
  /** ISO zaman damgası; saat biçimlendirmesi görüntülenirken yapılır. */
  createdAt: string
  /** Yanıt değil hata mesajı; farklı biçimde gösterilir ve misafir geçmişine katılmaz. */
  isError?: boolean
  sources?: SourceLink[]
  /** Yanıt model tarafından üretilmedi, hazır yanıtlardan verildi. */
  isPrepared?: boolean
  /** Soru yanıtlanamadığında seçenek olarak sunulan, yanıtı olan yakın sorular. */
  suggestions?: string[]
  /** Yalnızca arayüzde gösterilen mesaj ("Diğer" seçimi); sunucuya geçmiş olarak gitmez. */
  isLocal?: boolean
}

/** Üst çubuktaki bağlantı göstergesi; ilk denetim bitene kadar `checking`. */
export type ApiStatus = 'checking' | 'online' | 'offline'

/** Girişli kullanıcı ya da misafir (`useAuth`'taki `GUEST`). */
export type User = {
  id: string
  email: string
  name: string
}

/** Yan bar geçmiş listesinin bir satırı; turlar konuşma açılınca ayrıca alınır. */
export type ConversationSummary = {
  id: string
  title: string
  updatedAt: string
}
