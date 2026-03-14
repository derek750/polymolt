"use client"

import { useState, useEffect, useRef } from "react"
import { TradeEntry } from "@/types/trade"
import { TradeEntryRow } from "./TradeEntry"
import { X } from "lucide-react"

interface Props {
  trades: TradeEntry[]
  onAgentClick?: (agentId: string) => void
}

const VISIBLE_COUNT = 5

export function TradeFeed({ trades, onAgentClick }: Props) {
  const [expanded, setExpanded] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to top of expanded view when new trade arrives
  useEffect(() => {
    if (expanded && scrollRef.current) {
      scrollRef.current.scrollTop = 0
    }
  }, [trades.length, expanded])

  const recentTrades = trades.slice(0, VISIBLE_COUNT)

  return (
    <>
      <div className="flex flex-col bg-white border border-neutral-200 rounded-lg h-full overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2.5 border-b border-neutral-200">
          <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider">Activity</span>
          {trades.length > VISIBLE_COUNT && (
            <button
              onClick={() => setExpanded(true)}
              className="text-xs text-neutral-400 hover:text-neutral-700 transition-colors"
            >
              View all {trades.length}
            </button>
          )}
          {trades.length <= VISIBLE_COUNT && trades.length > 0 && (
            <span className="text-xs text-neutral-400">{trades.length}</span>
          )}
        </div>

        <div className="flex-1 overflow-hidden">
          {recentTrades.length === 0 ? (
            <div className="flex items-center justify-center h-24 text-neutral-400 text-sm">
              Waiting for trades…
            </div>
          ) : (
            recentTrades.map((trade) => (
              <TradeEntryRow
                key={trade.id}
                trade={trade}
                onAgentClick={onAgentClick}
              />
            ))
          )}
        </div>
      </div>

      {/* Full trade history modal */}
      {expanded && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/20"
            onClick={() => setExpanded(false)}
          />
          <div className="fixed inset-y-0 right-0 z-50 w-[420px] bg-white border-l border-neutral-200 shadow-lg flex flex-col animate-slide-in-right">
            <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
              <span className="text-sm font-medium text-neutral-900">All Trades ({trades.length})</span>
              <button
                onClick={() => setExpanded(false)}
                className="text-neutral-400 hover:text-neutral-600 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div ref={scrollRef} className="flex-1 overflow-y-auto">
              {trades.map((trade) => (
                <TradeEntryRow
                  key={trade.id}
                  trade={trade}
                  onAgentClick={(id) => {
                    setExpanded(false)
                    onAgentClick?.(id)
                  }}
                />
              ))}
            </div>
          </div>
        </>
      )}
    </>
  )
}
