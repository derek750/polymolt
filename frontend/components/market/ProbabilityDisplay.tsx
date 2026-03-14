"use client"

interface Props {
  price: number
  priceHistory: number[]
  question: string
}

function getDelta(history: number[]): number | null {
  if (history.length < 2) return null
  const recent = history.slice(-5)
  return (recent[recent.length - 1] - recent[0]) * 100
}

export function ProbabilityDisplay({ price, priceHistory, question }: Props) {
  const pct = Math.round(price * 100)
  const delta = getDelta(priceHistory)
  const deltaStr = delta !== null ? `${delta >= 0 ? "+" : ""}${delta.toFixed(1)}` : null

  return (
    <div className="flex flex-col gap-0.5">
      <p className="text-sm text-neutral-500">{question}</p>
      <div className="flex items-baseline gap-2">
        <span className="text-4xl font-bold tracking-tight text-neutral-900 tabular-nums">
          {pct}%
        </span>
        {deltaStr && (
          <span className={`text-sm font-medium tabular-nums ${
            delta! > 0 ? "text-green-600" : delta! < 0 ? "text-red-600" : "text-neutral-400"
          }`}>
            {deltaStr}pp
          </span>
        )}
        <span className="text-sm text-neutral-400">chance</span>
      </div>
    </div>
  )
}
