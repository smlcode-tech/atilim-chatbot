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
