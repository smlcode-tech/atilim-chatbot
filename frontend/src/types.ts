export type SourceLink = {
  title: string
  url: string
}

export type Message = {
  id: string
  role: 'assistant' | 'user'
  content: string
  /** ISO zaman damgası; saat biçimlendirmesi görüntülenirken yapılır. */
  createdAt: string
  isError?: boolean
  sources?: SourceLink[]
  /** Yanıt model tarafından üretilmedi, hazır yanıtlardan verildi. */
  isPrepared?: boolean
  /** Soru yanıtlanamadığında seçenek olarak sunulan, yanıtı olan yakın sorular. */
  suggestions?: string[]
  /** Yalnızca arayüzde gösterilen mesaj ("Diğer" seçimi); sunucuya geçmiş olarak gitmez. */
  isLocal?: boolean
}

export type ApiStatus = 'checking' | 'online' | 'offline'

export type User = {
  id: string
  email: string
  name: string
}

export type ConversationSummary = {
  id: string
  title: string
  updatedAt: string
}
