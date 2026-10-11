export type SourceLink = {
  title: string
  url: string
}

export type Message = {
  id: number
  role: 'assistant' | 'user'
  content: string
  time: string
  isError?: boolean
  sources?: SourceLink[]
  /** Yanıt model tarafından üretilmedi, hazır yanıtlardan verildi. */
  isPrepared?: boolean
}

export type ApiStatus = 'checking' | 'online' | 'offline'
