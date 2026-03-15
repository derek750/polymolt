"use client"

import { X } from "lucide-react"
import type { TradeEntry } from "@/types/trade"

interface Props {
  agentId: string
  trades: TradeEntry[]
  onClose: () => void
}

function fmtPct(n: number): string {
  return `${(n * 100).toFixed(1)}%`
}

export function AgentReasoningDrawer({ agentId, trades, onClose }: Props) {
  const agentTrades = trades.filter((t) => t.agentId === agentId)
  const agentName = agentTrades[0]?.agentName ?? agentId

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/20"
        onClick={onClose}
      />
      <div className="fixed inset-y-0 right-0 z-50 w-[440px] max-w-full bg-white border-l border-neutral-200 shadow-lg flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-sm font-semibold text-neutral-900 truncate">{agentName}</span>
            <span className="text-xs text-neutral-400">{agentTrades.length} trade{agentTrades.length !== 1 ? "s" : ""}</span>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Trade list */}
        <div className="flex-1 overflow-y-auto">
          {agentTrades.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-neutral-400 text-sm">
              No trades from this agent yet.
            </div>
          ) : (
            agentTrades.map((trade) => {
              const isBuy = trade.direction === "BUY" || trade.direction === "YES"
              const delta = trade.priceAfter - trade.priceBefore
              return (
                <div
                  key={trade.id}
                  className="px-4 py-3 border-b border-neutral-100"
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className={`text-xs font-semibold ${isBuy ? "text-green-600" : "text-red-600"}`}>
                      {isBuy ? "YES" : "NO"}
                    </span>
                    <div className="flex items-center gap-1.5 text-xs">
                      <span className="text-neutral-400">{fmtPct(trade.priceBefore)}</span>
                      <span className="text-neutral-300">&rarr;</span>
                      <span className="text-neutral-700 font-medium">{fmtPct(trade.priceAfter)}</span>
                      <span className={`font-mono ${delta >= 0 ? "text-green-600" : "text-red-600"}`}>
                        {delta >= 0 ? "+" : ""}{(delta * 100).toFixed(1)}
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-neutral-600 leading-relaxed whitespace-pre-wrap">
                    {trade.reasoning}
                  </p>
                  <span className="text-[10px] text-neutral-300 mt-1 block">
                    {new Date(trade.timestamp).toLocaleTimeString("en-US", {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                      hour12: false,
                    })}
                  </span>
                </div>
              )
            })
          )}
        </div>
      </div>
    </>
  )
}
