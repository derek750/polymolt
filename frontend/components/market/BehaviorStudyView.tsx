"use client"

import { Agent } from "@/types/agent"

interface Props {
  agents: Agent[]
  marketPrice: number
  onAgentClick?: (agentId: string) => void
}

export function BehaviorStudyView({ agents, marketPrice, onAgentClick }: Props) {
  const sorted = [...agents].sort((a, b) => b.currentBelief - a.currentBelief)
  const marketPct = Math.round(marketPrice * 100)

  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-medium text-neutral-400 uppercase tracking-wider">
          Belief Distribution
        </span>
        <span className="text-xs text-neutral-400">
          Market {marketPct}%
        </span>
      </div>

      <div className="space-y-1.5">
        {sorted.map((agent) => {
          const gap = agent.currentBelief - marketPrice

          return (
            <button
              key={agent.id}
              onClick={() => onAgentClick?.(agent.id)}
              className="flex items-center gap-2 w-full hover:bg-neutral-50 rounded px-1 py-1 transition-colors"
            >
              <span className="text-xs text-neutral-500 w-36 text-left truncate flex-shrink-0">
                {agent.name}
              </span>

              <div className="flex-1 relative h-3 bg-neutral-100 rounded overflow-visible">
                <div
                  className="h-full rounded bg-neutral-900 transition-all duration-500"
                  style={{
                    width: `${agent.currentBelief * 100}%`,
                    opacity: 0.7,
                  }}
                />
                <div
                  className="absolute top-1/2 -translate-y-1/2 w-px h-4 pointer-events-none z-10 bg-neutral-400"
                  style={{ left: `${marketPrice * 100}%` }}
                />
              </div>

              <span className="text-xs w-8 text-right tabular-nums font-medium text-neutral-700 flex-shrink-0">
                {Math.round(agent.currentBelief * 100)}%
              </span>

              <span className={`text-xs w-8 text-right flex-shrink-0 ${
                gap > 0.02 ? "text-green-600" : gap < -0.02 ? "text-red-600" : "text-neutral-400"
              }`}>
                {gap > 0.02 ? "▲" : gap < -0.02 ? "▼" : "—"}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
