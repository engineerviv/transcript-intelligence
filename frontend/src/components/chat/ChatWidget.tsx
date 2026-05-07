import { useState, useRef, useEffect, useCallback } from 'react'
import { MessageCircle, X, Send, ChevronDown } from 'lucide-react'
import { api } from '@/lib/api'
import type { ChatMessage } from '@/types'

const SUGGESTIONS = [
  'What are the top customer complaints?',
  'Which accounts are at risk of churning?',
  'What are the most urgent open issues?',
  'Summarize the key action items',
]

function TypingDots() {
  return (
    <div className="flex gap-1 items-center h-4">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </div>
  )
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}

export function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    if (open && inputRef.current) inputRef.current.focus()
  }, [open])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || streaming) return

    const userMsg: Message = { role: 'user', content: text.trim() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setStreaming(true)

    const history: ChatMessage[] = messages.map(m => ({ role: m.role, content: m.content }))

    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }])

    let closed = false
    const stream = api.chatStream(text.trim(), history)
    const reader = stream.getReader()

    abortRef.current = () => { closed = true; reader.cancel() }

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done || closed) break
        setMessages(prev => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last?.role === 'assistant') {
            updated[updated.length - 1] = { ...last, content: last.content + value }
          }
          return updated
        })
      }
    } finally {
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last?.role === 'assistant' && last.streaming) {
          updated[updated.length - 1] = { ...last, streaming: false }
        }
        return updated
      })
      setStreaming(false)
      abortRef.current = null
    }
  }, [messages, streaming])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    sendMessage(input)
  }

  function clearChat() {
    abortRef.current?.()
    setMessages([])
    setStreaming(false)
  }

  const hasMessages = messages.length > 0

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full bg-blue-600 hover:bg-blue-500
            shadow-lg shadow-blue-900/50 flex items-center justify-center transition-all
            hover:scale-105 active:scale-95"
          aria-label="Open AI assistant"
        >
          <MessageCircle className="w-5 h-5 text-white" />
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-[#0f172a]" />
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-6 right-6 z-50 w-[380px] h-[540px] flex flex-col
          bg-surface border border-border rounded-2xl shadow-2xl shadow-black/50
          overflow-hidden">

          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-[#1a2744]">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center">
                <MessageCircle className="w-3.5 h-3.5 text-white" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-100">TI Assistant</p>
                <div className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                  <span className="text-[10px] text-muted">Powered by GPT-4o-mini</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {hasMessages && (
                <button
                  onClick={clearChat}
                  className="text-muted hover:text-slate-300 text-xs px-2 py-1 rounded transition-colors"
                >
                  Clear
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                className="text-muted hover:text-slate-200 p-1 rounded transition-colors"
              >
                <ChevronDown className="w-4 h-4" />
              </button>
              <button
                onClick={() => { setOpen(false); clearChat() }}
                className="text-muted hover:text-slate-200 p-1 rounded transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {!hasMessages ? (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                <div className="w-12 h-12 rounded-full bg-blue-600/20 flex items-center justify-center">
                  <MessageCircle className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-200">Ask about your transcripts</p>
                  <p className="text-xs text-muted mt-1">I have full context on all 100 calls</p>
                </div>
                <div className="w-full space-y-1.5">
                  {SUGGESTIONS.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => sendMessage(s)}
                      className="w-full text-left text-xs px-3 py-2 rounded-lg bg-slate-800/60
                        hover:bg-slate-700/60 text-slate-300 hover:text-slate-100 border border-border/50
                        transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed ${
                        msg.role === 'user'
                          ? 'bg-blue-600 text-white rounded-br-sm'
                          : 'bg-slate-800 text-slate-200 rounded-bl-sm border border-border/50'
                      }`}
                    >
                      {msg.streaming && !msg.content
                        ? <TypingDots />
                        : <span className="whitespace-pre-wrap">{msg.content}</span>
                      }
                      {msg.streaming && msg.content && (
                        <span className="inline-block w-1 h-3 bg-slate-400 ml-0.5 animate-pulse" />
                      )}
                    </div>
                  </div>
                ))}
                <div ref={bottomRef} />
              </>
            )}
          </div>

          {/* Suggestion chips (after first message) */}
          {hasMessages && !streaming && (
            <div className="px-4 pb-2 flex gap-1.5 flex-wrap">
              {SUGGESTIONS.slice(0, 2).map((s, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(s)}
                  className="text-[10px] px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700
                    text-slate-400 hover:text-slate-200 border border-border/50 transition-colors"
                >
                  {s.length > 28 ? s.slice(0, 28) + '…' : s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <form
            onSubmit={handleSubmit}
            className="px-3 pb-3 pt-1 border-t border-border flex items-center gap-2"
          >
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask about your call data…"
              disabled={streaming}
              className="flex-1 bg-[#0f172a] border border-border rounded-xl px-3 py-2 text-xs
                text-slate-200 placeholder:text-muted focus:outline-none focus:border-blue-500
                disabled:opacity-50 transition-colors"
            />
            <button
              type="submit"
              disabled={!input.trim() || streaming}
              className="w-8 h-8 rounded-xl bg-blue-600 hover:bg-blue-500 flex items-center justify-center
                disabled:opacity-40 disabled:cursor-not-allowed transition-all shrink-0"
            >
              <Send className="w-3.5 h-3.5 text-white" />
            </button>
          </form>
        </div>
      )}
    </>
  )
}
