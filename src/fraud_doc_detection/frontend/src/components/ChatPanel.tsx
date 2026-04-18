import { useState, useRef, useEffect } from 'react'
import { MessageSquare, Send, Loader2, Trash2 } from 'lucide-react'
import type { ChatMessage } from '../types'

interface ChatPanelProps {
  documentId: string
  history: ChatMessage[]
  loading: boolean
  error: string | null
  onSend: (question: string) => void
  onClear: () => void
}

export function ChatPanel({ history, loading, error, onSend, onClear }: ChatPanelProps) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, loading])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const q = input.trim()
    if (!q || loading) return
    setInput('')
    onSend(q)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#e0e0e0] bg-white flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-[#C8102E] flex items-center justify-center">
            <MessageSquare size={13} className="text-white" />
          </div>
          <span className="text-sm font-semibold text-[#333333]">Ask Document</span>
        </div>
        {history.length > 0 && (
          <button
            onClick={onClear}
            className="flex items-center gap-1 text-xs text-[#888888] hover:text-red-600 transition-colors"
          >
            <Trash2 size={12} />
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {history.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-3 py-8">
            <div className="w-12 h-12 rounded-full bg-[#f0f0f0] flex items-center justify-center">
              <MessageSquare size={22} className="text-[#aaaaaa]" />
            </div>
            <p className="text-sm font-medium text-[#333333]">Ask anything about this document</p>
            <div className="flex flex-col gap-2 w-full max-w-xs">
              {[
                'What is the total credit amount?',
                'Who is the account holder?',
                'What is the net profit for this year?',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => onSend(suggestion)}
                  className="text-xs px-3 py-2 rounded border border-[#e0e0e0] text-[#555555] hover:border-[#C8102E] hover:text-[#C8102E] transition-colors text-left"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {history.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-xs leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-[#C8102E] text-white rounded-br-sm'
                  : 'bg-white border border-[#e0e0e0] text-[#333333] rounded-bl-sm'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-[#e0e0e0] rounded-lg rounded-bl-sm px-3 py-2">
              <Loader2 size={14} className="text-[#C8102E] animate-spin" />
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 px-4 py-3 border-t border-[#e0e0e0] bg-white flex-shrink-0"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about this document…"
          disabled={loading}
          className="flex-1 text-xs px-3 py-2 rounded border border-[#e0e0e0] focus:outline-none focus:border-[#C8102E] transition-colors placeholder-[#aaaaaa] disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="w-8 h-8 flex items-center justify-center rounded bg-[#C8102E] text-white hover:bg-[#a50d26] transition-colors disabled:opacity-40"
        >
          <Send size={13} />
        </button>
      </form>
    </div>
  )
}
