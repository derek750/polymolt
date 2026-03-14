"use client"

import { useState, useEffect, useRef } from "react"
import { Agent } from "@/types/agent"
import { CATEGORY_LABELS } from "@/lib/constants"

interface Props {
  agent: Agent
  onClick: () => void
}

export function AgentCard({ agent, onClick }: Props) {
  const beliefPct = Math.round(agent.currentBelief * 100)
  const [flash, setFlash] = useState(false)
  const prevBeliefRef = useRef(agent.currentBelief)

  useEffect(() => {
    if (Math.abs(agent.currentBelief - prevBeliefRef.current) > 0.001) {
      prevBeliefRef.current = agent.currentBelief
      setFlash(true)
      const t = setTimeout(() => setFlash(false), 400)
      return () => clearTimeout(t)
    }
  }, [agent.currentBelief])

  const lastTrade = agent.tradeHistory?.[0]
  const lastDelta = lastTrade
    ? (lastTrade.priceAfter - lastTrade.priceBefore) * 100
    : null

  const typeLabel =
    agent.agentType === "master" ? "Master" :
    agent.agentType === "hybrid" ? "Hybrid" : "Specialist"

  return (
    <button
      onClick={onClick}
      className={`flex flex-col gap-2 p-3 bg-white border rounded-lg hover:border-neutral-400 transition-colors text-left cursor-pointer w-full ${
        flash ? "border-neutral-400" : "border-neutral-200"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-0.5 min-w-0">
          <span className="text-sm font-semibold text-neutral-900 leading-tight truncate">
            {agent.name}
          </span>
          <span className="text-xs text-neutral-400">{typeLabel}</span>
        </div>
        <div className="flex flex-col items-end flex-shrink-0">
          <span className="text-lg font-bold tabular-nums text-neutral-900">
            {beliefPct}%
          </span>
          {lastTrade && lastDelta !== null ? (
            <span className={`text-xs font-medium tabular-nums ${
              (lastTrade.direction === "BUY" || lastTrade.direction === "YES") ? "text-green-600" : "text-red-600"
            }`}>
              {lastDelta >= 0 ? "+" : ""}{lastDelta.toFixed(1)}pp
            </span>
          ) : (
            <span className="text-xs text-neutral-400 tabular-nums">
              {agent.currentPosition >= 0 ? "+" : ""}{agent.currentPosition.toFixed(1)}
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-1">
        {agent.categories.map((cat) => (
          <span key={cat} className="text-xs text-neutral-400">
            {CATEGORY_LABELS[cat] ?? cat}
          </span>
        ))}
      </div>

      {agent.lastReasoning && (
        <p className="text-xs text-neutral-400 leading-relaxed line-clamp-2">
          {agent.lastReasoning}
        </p>
      )}
    </button>
  )
}
