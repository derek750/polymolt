"use client"

import { useEffect, useRef, useState } from "react"
import { X } from "lucide-react"
import type { SelectedFeature } from "@/types/map"
import type { Message } from "@/types/map"
import type { HistoryItem } from "@/types/map"
import { askLocation, getLocationHistory } from "@/lib/locationApi"

interface LocationSidePanelProps {
  feature: SelectedFeature
  onClose: () => void
  isMobile: boolean
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-2 px-3 rounded-2xl rounded-bl-sm bg-neutral-100 text-neutral-500 w-fit">
      <span className="w-2 h-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "0ms" }} />
      <span className="w-2 h-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "150ms" }} />
      <span className="w-2 h-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "300ms" }} />
    </div>
  )
}

export function LocationSidePanel({ feature, onClose, isMobile }: LocationSidePanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [historyOpen, setHistoryOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setMessages([])
    setError(null)
    setHistory([])
    setHistoryOpen(false)
    setLoadingHistory(true)
    getLocationHistory(feature.name)
      .then(setHistory)
      .catch(() => setHistory([]))
      .finally(() => setLoadingHistory(false))
  }, [feature.name, feature.coordinates?.join(",")])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const sendMessage = async () => {
    const q = input.trim()
    if (!q || sending) return
    setInput("")
    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      content: q,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setSending(true)
    setError(null)
    try {
      const res = await askLocation({
        locationName: feature.name,
        locationType: feature.type,
        coordinates: feature.coordinates,
        question: q,
      })
      const answer = (res as { answer?: string }).answer ?? "No response."
      const assistantMsg: Message = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: answer,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMsg])
      setHistory((prev) => [...prev, { id: `h-${Date.now()}`, question: q, answer, createdAt: new Date().toISOString() }])
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : "Request failed"
      setError(errMsg)
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: `Error: ${errMsg}`,
          timestamp: new Date(),
        },
      ])
    } finally {
      setSending(false)
    }
  }

  const retryLast = () => {
    setError(null)
    const lastUser = [...messages].reverse().find((m) => m.role === "user")
    if (lastUser) {
      setMessages((prev) => prev.filter((m) => m.id !== lastUser.id && !m.id.startsWith("err-")))
      setInput(lastUser.content)
      inputRef.current?.focus()
    }
  }

  const askAgain = (question: string) => {
    setInput(question)
    setHistoryOpen(false)
    inputRef.current?.focus()
  }

  const [lng, lat] = feature.coordinates
  const coordText = `${lat.toFixed(5)}, ${lng.toFixed(5)}`

  const panelWidth = isMobile ? "100%" : "380px"

  return (
    <div
      className={`fixed flex flex-col bg-black/40 backdrop-blur-xl shadow-2xl z-50 ${isMobile ? "left-0 right-0 bottom-0 max-h-[85vh] rounded-t-2xl border-t border-white/10 animate-slide-in-bottom" : "top-0 right-0 h-full w-[380px] border-l border-white/10 animate-slide-in-right"}`}
      style={isMobile ? undefined : { width: panelWidth }}
    >
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b border-white/10">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="font-semibold text-white text-lg truncate">{feature.name}</h2>
            <span className="inline-block mt-1 px-2 py-0.5 rounded text-xs bg-white/20 text-white/90">
              {feature.type}
            </span>
            <p className="mt-1 text-xs text-white/50">{coordText}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex-shrink-0 p-1.5 rounded-lg hover:bg-white/10 text-white/80 hover:text-white transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Chat */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && !loadingHistory && (
            <p className="text-sm text-white/50">Ask a question about this location.</p>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                  m.role === "user"
                    ? "bg-blue-500 text-white rounded-br-sm"
                    : m.id.startsWith("err-")
                      ? "bg-red-500/20 text-red-200 rounded-bl-sm"
                      : "bg-white/10 text-white rounded-bl-sm"
                }`}
              >
                {m.content}
                {m.id.startsWith("err-") && (
                  <button
                    type="button"
                    onClick={retryLast}
                    className="block mt-2 text-xs underline text-red-200 hover:text-white"
                  >
                    Retry
                  </button>
                )}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <TypingIndicator />
            </div>
          )}
        </div>
        <div className="flex-shrink-0 p-4 border-t border-white/10">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage()
                }
              }}
              placeholder="Ask about this place..."
              className="flex-1 rounded-xl bg-white/10 border border-white/20 text-white placeholder-white/40 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-white/30"
            />
            <button
              type="button"
              onClick={sendMessage}
              disabled={!input.trim() || sending}
              className="px-4 py-2 rounded-xl bg-blue-500 text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-600 transition-colors"
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* Past questions */}
      <div className="flex-shrink-0 border-t border-white/10">
        <button
          type="button"
          onClick={() => setHistoryOpen((o) => !o)}
          className="w-full flex items-center justify-between px-4 py-3 text-left text-sm text-white/80 hover:bg-white/5 transition-colors"
        >
          <span>Past questions</span>
          <span className="text-white/50">{history.length}</span>
        </button>
        {historyOpen && (
          <div className="max-h-48 overflow-y-auto px-4 pb-4 space-y-2">
            {loadingHistory ? (
              <p className="text-xs text-white/50">Loading...</p>
            ) : history.length === 0 ? (
              <p className="text-xs text-white/50">No previous questions.</p>
            ) : (
              history.map((item) => (
                <details
                  key={item.id}
                  className="group rounded-lg bg-white/5 border border-white/10 overflow-hidden"
                >
                  <summary className="px-3 py-2 text-sm text-white/90 cursor-pointer list-none">
                    <span className="truncate block">{item.question}</span>
                  </summary>
                  <div className="px-3 py-2 pt-0 text-sm text-white/70 border-t border-white/10">
                    {item.answer}
                    <button
                      type="button"
                      onClick={() => askAgain(item.question)}
                      className="mt-2 block text-xs text-blue-300 hover:text-blue-200"
                    >
                      Ask again
                    </button>
                  </div>
                </details>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
