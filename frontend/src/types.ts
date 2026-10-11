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
}

export type ApiStatus = 'checking' | 'online' | 'offline'
