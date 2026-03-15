"use client"

import { useState, useMemo } from "react"
import Link from "next/link"
import { useOrchestration } from "@/lib/OrchestrationContext"
import { AgentReasoningDrawer } from "@/components/trades/AgentReasoningDrawer"
import { X } from "lucide-react"

interface AgentSummary {
  agentId: string
  agentName: string
  tradeCount: number
  yesCount: number
  noCount: number
  lastDirection: "YES" | "NO"
  totalSize: number
  avgConfidence: number
}

export default function AgentsPage() {
  const orch = useOrchestration()
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)

  // Derive unique agents from trades
  const agents: AgentSummary[] = useMemo(() => {
    const map = new Map<string, AgentSummary>()
    // trades are newest-first, iterate in reverse for chronological order
    for (let i = orch.trades.length - 1; i >= 0; i--) {
      const t = orch.trades[i]
      const existing = map.get(t.agentId)
      const isYes = t.direction === "YES" || t.direction === "BUY"
      if (existing) {
        existing.tradeCount += 1
        if (isYes) existing.yesCount += 1
        else existing.noCount += 1
        existing.lastDirection = isYes ? "YES" : "NO"
        existing.totalSize += t.size
      } else {
        map.set(t.agentId, {
          agentId: t.agentId,
          agentName: t.agentName,
          tradeCount: 1,
          yesCount: isYes ? 1 : 0,
          noCount: isYes ? 0 : 1,
          lastDirection: isYes ? "YES" : "NO",
          totalSize: t.size,
          avgConfidence: 0,
        })
      }
    }
    return Array.from(map.values())
  }, [orch.trades])

  const statusLabel =
    orch.status === "running" ? "Running" :
    orch.status === "done" ? "Complete" :
    orch.status === "error" ? "Error" : "Idle"

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <header className="sticky top-0 z-50 flex items-center justify-between px-6 py-3 bg-white border-b border-neutral-200">
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="font-bold text-neutral-900 text-lg tracking-tight hover:opacity-70 transition-opacity">
            polymolt
          </Link>
          <nav className="flex items-center gap-1 ml-2">
            <Link
              href="/dashboard"
              className="px-3 py-1.5 text-xs text-neutral-500 rounded hover:text-neutral-700 transition-colors"
            >
              Dashboard
            </Link>
            <Link
              href="/agents"
              className="px-3 py-1.5 text-xs text-neutral-900 bg-neutral-100 rounded font-medium"
            >
              Agents
            </Link>
            <Link
              href="/map"
              className="px-3 py-1.5 text-xs text-neutral-500 rounded hover:text-neutral-700 transition-colors"
            >
              Map
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <span className={`text-xs ${
            orch.status === "running" || orch.status === "done" ? "text-neutral-500" : "text-neutral-400"
          }`}>
            {statusLabel}
          </span>
        </div>
      </header>

      <main className="flex-1 flex flex-col gap-4 p-4 lg:p-5 max-w-[1400px] mx-auto w-full">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-neutral-900">Agents</h1>
            <p className="text-sm text-neutral-500 mt-0.5">
              {agents.length} agent{agents.length !== 1 ? "s" : ""} trading on the market
            </p>
          </div>
          {orch.question && (
            <div className="text-right">
              <p className="text-xs text-neutral-400">Current question</p>
              <p className="text-sm text-neutral-700 max-w-[300px] truncate">{orch.question}</p>
            </div>
          )}
        </div>

        {agents.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-4 py-20">
            <p className="text-neutral-500 text-sm">
              {orch.status === "idle"
                ? "No agents have traded yet. Start a question from the map."
                : orch.status === "running"
                  ? "Agents are being activated... trades will appear shortly."
                  : "No agent data available."}
            </p>
            {orch.status === "idle" && (
              <Link
                href="/map"
                className="px-5 py-2.5 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 transition-colors"
              >
                Go to Map
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {agents.map((agent) => (
              <button
                key={agent.agentId}
                onClick={() => setSelectedAgentId(agent.agentId)}
                className="text-left p-4 rounded-lg border border-neutral-200 hover:border-neutral-300 hover:shadow-sm transition-all bg-white"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-neutral-900 truncate">
                    {agent.agentName}
                  </span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    agent.lastDirection === "YES"
                      ? "bg-green-50 text-green-700"
                      : "bg-red-50 text-red-700"
                  }`}>
                    {agent.lastDirection}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-neutral-500">
                  <span>{agent.tradeCount} trade{agent.tradeCount !== 1 ? "s" : ""}</span>
                  <span className="text-green-600">{agent.yesCount} YES</span>
                  <span className="text-red-600">{agent.noCount} NO</span>
                  <span className="ml-auto text-neutral-400">{agent.totalSize.toFixed(1)}u total</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </main>

      {selectedAgentId && (
        <AgentReasoningDrawer
          agentId={selectedAgentId}
          trades={orch.trades}
          onClose={() => setSelectedAgentId(null)}
        />
      )}
    </div>
  )
}
