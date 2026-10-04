import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { matchPath, useLocation, useNavigate } from 'react-router-dom'
import { fetchChatHistory, sendChatMessage } from '../api'
import type { ChatMessage, PageContext } from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'
import Crest from './Crest'

// `note` is shown in the panel only; it is never sent back to the agent.
type Message = ChatMessage & { note?: string }

// Earlier turns sent with each message so the agent has context.
const HISTORY_TURNS = 10

const GREETING: Message = { role: 'assistant', content: 'Hi! Ask me about Campus Customs gear.' }

// One-tap starter questions, shown until the shopper sends a message.
const GENERAL_SUGGESTIONS = [
  'What hoodies do you have?',
  'Show me T-shirts under $35',
  'Do you do custom orders?',
]
const PRODUCT_SUGGESTIONS = [
  'Is this in stock in medium?',
  'What colors does this come in?',
  'Show me similar items',
]

// App remounts this panel (via `key`) when the signed-in user changes,
// so each user starts with their own history and guests start fresh.
export default function ChatPanel() {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [messages, setMessages] = useState<Message[]>([GREETING])
  const endRef = useRef<HTMLDivElement>(null)
  const { setResults } = useChatResults()
  const { user } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()

  // Signed in: reload saved chat history from the server.
  useEffect(() => {
    if (!user) return
    fetchChatHistory()
      .then((saved) => {
        if (saved.length === 0) return
        const restored: Message[] = saved.map(({ role, content }) => ({ role, content }))
        restored[restored.length - 1] = {
          ...restored[restored.length - 1],
          note: 'Earlier conversation restored.',
        }
        setMessages([GREETING, ...restored])
      })
      .catch(() => {})
  }, [user])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  const productId = matchPath('/products/:productId', pathname)?.params.productId ?? null
  const suggestions = productId ? PRODUCT_SUGGESTIONS : GENERAL_SUGGESTIONS
  const showSuggestions = !busy && !messages.some((m) => m.role === 'user')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    send(input)
  }

  async function send(raw: string) {
    const text = raw.trim()
    if (!text || busy) return
    // Skip the opening greeting; it isn't part of the real conversation.
    const history = messages
      .slice(1)
      .slice(-HISTORY_TURNS)
      .map(({ role, content }) => ({ role, content }))
    // Which page the shopper is on; on a product page, which product.
    const page: PageContext = { path: pathname, product_id: productId }
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: text }])
    setBusy(true)
    try {
      const { reply, products } = await sendChatMessage(text, history, page)
      let note: string | undefined
      if (products.length > 0) {
        // Show the matches as product cards in the main page area.
        setResults({ question: text, products })
        navigate('/chat-results')
        note = `Showing ${products.length} product${products.length === 1 ? '' : 's'} on the page.`
      }
      setMessages((m) => [...m, { role: 'assistant', content: reply, note }])
    } catch (err) {
      const content =
        err instanceof Error ? err.message : 'Sorry, something went wrong. Please try again.'
      setMessages((m) => [...m, { role: 'assistant', content }])
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <button className="chat-toggle" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path
            d="M4 5h16v11H8l-4 4z"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="round"
          />
        </svg>
        Chat with us
      </button>
    )
  }

  return (
    <section className="chat-panel" aria-label="Chat">
      <div className="chat-header">
        <Crest size={34} />
        <div className="chat-title">
          <span>Campus Customs Assistant</span>
          <small>Sizes, stock &amp; styles from our live catalogue</small>
        </div>
        <button onClick={() => setOpen(false)} aria-label="Close chat">
          ×
        </button>
      </div>
      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            {m.content}
            {m.note && <div className="chat-note">{m.note}</div>}
          </div>
        ))}
        {busy && (
          <div className="chat-msg assistant typing" role="status" aria-live="polite">
            <span className="dots" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            Assistant is thinking…
          </div>
        )}
        {showSuggestions && (
          <div className="chat-suggestions" aria-label="Suggested questions">
            {suggestions.map((q) => (
              <button key={q} type="button" onClick={() => send(q)}>
                {q}
              </button>
            ))}
          </div>
        )}
        <div ref={endRef} />
      </div>
      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={busy ? 'Waiting for the assistant…' : 'Type a message…'}
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
