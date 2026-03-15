"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { X } from "lucide-react"
import type { SelectedFeature } from "@/types/map"
import type { HistoryItem } from "@/types/map"
import { getLocationHistory } from "@/lib/locationApi"

interface LocationSidePanelProps {
  feature: SelectedFeature
  onClose: () => void
  isMobile: boolean
}

export function LocationSidePanel({ feature, onClose, isMobile }: LocationSidePanelProps) {
  const router = useRouter()
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [input, setInput] = useState("")
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setHistory([])
    setError(null)
    setLoadingHistory(true)
    getLocationHistory(feature.name)
      .then(setHistory)
      .catch(() => setHistory([]))
      .finally(() => setLoadingHistory(false))
  }, [feature.name, feature.coordinates?.join(",")])

  const sendMessage = () => {
    const q = input.trim()
    if (!q) return

    // Navigate to dashboard with question params; orchestration runs there
    const params = new URLSearchParams({
      question: q,
      location: feature.name,
    })
    router.push(`/dashboard?${params.toString()}`)
    onClose()
  }

  const askAgain = (question: string) => {
    setInput(question)
    inputRef.current?.focus()
  }

  const [lng, lat] = feature.coordinates
  const coordText = `${lat.toFixed(5)}, ${lng.toFixed(5)}`

  const panelWidth = isMobile ? "100%" : "380px"

  return (
    <div
      className={`fixed top-0 z-40 flex flex-col bg-white shadow-2xl border-l border-neutral-200 overflow-hidden ${isMobile ? "left-0 right-0 bottom-0 max-h-[85vh] rounded-t-2xl" : "right-0 h-full"}`}
      style={!isMobile ? { width: panelWidth } : undefined}
      role="dialog"
      aria-modal="true"
      aria-labelledby="location-panel-title"
    >
      <div className="flex-shrink-0 flex items-start justify-between gap-3 p-5 border-b border-neutral-100">
          <div className="min-w-0">
            <h2 id="location-panel-title" className="font-semibold text-neutral-900 text-lg truncate">
              {feature.name}
            </h2>
            <span className="inline-block mt-1.5 px-2 py-0.5 rounded-md text-xs bg-neutral-100 text-neutral-600">
              {feature.type}
            </span>
            <p className="mt-1 text-xs text-neutral-400">{coordText}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex-shrink-0 p-2 rounded-lg hover:bg-neutral-100 text-neutral-500 hover:text-neutral-700 transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          <div>
            <label htmlFor="location-question-input" className="block text-sm font-medium text-neutral-700 mb-2">
              Ask a question about this place
            </label>
            <div className="flex gap-2">
              <input
                ref={inputRef}
                id="location-question-input"
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    sendMessage()
                  }
                }}
                placeholder="e.g. Is this place accessible?"
                className="flex-1 rounded-xl border border-neutral-200 bg-neutral-50 text-neutral-900 placeholder-neutral-400 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              />
              <button
                type="button"
                onClick={sendMessage}
                disabled={!input.trim()}
                className="px-4 py-2.5 rounded-xl bg-neutral-900 text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-neutral-800 transition-colors"
              >
                Ask
              </button>
            </div>
            {error && (
              <p className="mt-2 text-sm text-red-600 flex items-center gap-2">
                {error}
                <button type="button" onClick={() => setError(null)} className="underline">
                  Dismiss
                </button>
              </p>
            )}
            <p className="mt-2 text-xs text-neutral-500">
              After you ask, you&apos;ll be taken to the market view to see predictions and the graph.
            </p>
          </div>

          <div>
            <h3 className="text-sm font-medium text-neutral-700 mb-3">Past questions</h3>
            {loadingHistory ? (
              <p className="text-sm text-neutral-500">Loading…</p>
            ) : history.length === 0 ? (
              <p className="text-sm text-neutral-500">No previous questions for this location yet.</p>
            ) : (
              <ul className="space-y-3">
                {history.map((item) => (
                  <li
                    key={item.id}
                    className="rounded-xl border border-neutral-200 bg-neutral-50/80 overflow-hidden"
                  >
                    <div className="px-3 py-2.5 border-b border-neutral-200/80">
                      <p className="text-sm font-medium text-neutral-900">{item.question}</p>
                    </div>
                    <div className="px-3 py-2.5">
                      <p className="text-sm text-neutral-600 whitespace-pre-wrap">{item.answer}</p>
                      <button
                        type="button"
                        onClick={() => askAgain(item.question)}
                        className="mt-2 text-xs font-medium text-neutral-900 hover:underline"
                      >
                        Ask again
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
    </div>
  )
}
