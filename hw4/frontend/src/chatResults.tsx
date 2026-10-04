import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import type { ProductCard } from './api'

export interface ChatResults {
  question: string
  products: ProductCard[]
}

interface ChatResultsValue {
  results: ChatResults | null
  setResults: (results: ChatResults | null) => void
}

const ChatResultsContext = createContext<ChatResultsValue | null>(null)

// Holds the latest product cards returned by the chat, so the chat panel
// can fill them in and the main page area can show them.
export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatResults | null>(null)
  return (
    <ChatResultsContext.Provider value={{ results, setResults }}>
      {children}
    </ChatResultsContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChatResults(): ChatResultsValue {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside ChatResultsProvider')
  return ctx
}
