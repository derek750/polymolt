import { TradeEntry as TradeEntryType } from "@/types/trade"

interface Props {
  trade: TradeEntryType
  onAgentClick?: (agentId: string) => void
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("en-US", {
      hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false
    })
  } catch {
    return iso
  }
}

function fmtPct(n: number): string {
  return `${(n * 100).toFixed(1)}%`
}

export function TradeEntryRow({ trade, onAgentClick }: Props) {
  const isBuy = trade.direction === "BUY" || trade.direction === "YES"
  const displayDirection = isBuy ? "YES" : "NO"
  const delta = trade.priceAfter - trade.priceBefore

  return (
    <div className="animate-slide-in-down flex flex-col gap-0.5 px-3 py-2 border-b border-neutral-100 hover:bg-neutral-50 transition-colors">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`text-xs font-semibold ${isBuy ? "text-green-600" : "text-red-600"}`}>
            {displayDirection}
          </span>
          <button
            onClick={() => onAgentClick?.(trade.agentId)}
            className="text-xs font-medium text-neutral-700 truncate hover:underline"
          >
            {trade.agentName}
          </button>
          <span className="text-xs text-neutral-300">{trade.size.toFixed(1)}u</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs flex-shrink-0">
          <span className="text-neutral-400">{fmtPct(trade.priceBefore)}</span>
          <span className="text-neutral-300">→</span>
          <span className="text-neutral-700 font-medium">{fmtPct(trade.priceAfter)}</span>
          <span className={`font-mono ${delta >= 0 ? "text-green-600" : "text-red-600"}`}>
            {delta >= 0 ? "+" : ""}{(delta * 100).toFixed(1)}
          </span>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <p className="text-xs text-neutral-400 leading-relaxed line-clamp-1 flex-1">{trade.reasoning}</p>
        <span className="text-xs text-neutral-300 ml-2 flex-shrink-0">{formatTime(trade.timestamp)}</span>
      </div>
    </div>
  )
}
