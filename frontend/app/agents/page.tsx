"use client"

import { useState } from "react"
import Link from "next/link"
import { useMarket } from "@/lib/useMarket"
import { AgentGrid } from "@/components/agents/AgentGrid"
import { AgentDrawer } from "@/components/agents/AgentDrawer"
import { BehaviorStudyView } from "@/components/market/BehaviorStudyView"
import { Region } from "@/types/market"
import { RegionSelector } from "@/components/header/RegionSelector"

export default function AgentsPage() {
  const { market, agents, regions, selectedRegion, connectionStatus, selectRegion } = useMarket("scandinavia")
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [showStudyView, setShowStudyView] = useState(false)

  const selectedAgent = agents.find((a) => a.id === selectedAgentId) ?? null

  const statusText =
    connectionStatus === "connected" ? "Connected" :
    connectionStatus === "connecting" ? "Connecting…" :
    connectionStatus === "error" ? "Error" : "Disconnected"

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
          <RegionSelector
            regions={regions as Region[]}
            selectedRegion={selectedRegion}
            onSelect={selectRegion}
          />
          <span className={`text-xs ${
            connectionStatus === "connected" ? "text-neutral-500" : "text-neutral-400"
          }`}>
            {statusText}
          </span>
        </div>
      </header>

      <main className="flex-1 flex flex-col gap-4 p-4 lg:p-5 max-w-[1400px] mx-auto w-full">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-neutral-900">Agents</h1>
            <p className="text-sm text-neutral-500 mt-0.5">
              {agents.length} agents trading on the market
            </p>
          </div>
          <button
            onClick={() => setShowStudyView((v) => !v)}
            className={`px-3 py-1.5 rounded border text-xs transition-colors ${
              showStudyView
                ? "bg-neutral-900 border-neutral-900 text-white"
                : "bg-white border-neutral-200 text-neutral-500 hover:border-neutral-400"
            }`}
          >
            {showStudyView ? "Hide" : "Show"} Beliefs
          </button>
        </div>

        {showStudyView && market && agents.length > 0 && (
          <BehaviorStudyView
            agents={agents}
            marketPrice={market.currentPrice}
            onAgentClick={(id) => setSelectedAgentId(id)}
          />
        )}

        <AgentGrid
          agents={agents}
          onAgentClick={(id) => setSelectedAgentId(id)}
        />
      </main>

      {selectedAgentId && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/20"
            onClick={() => setSelectedAgentId(null)}
          />
          <AgentDrawer
            agent={selectedAgent}
            marketPrice={market?.currentPrice}
            onClose={() => setSelectedAgentId(null)}
          />
        </>
      )}
    </div>
  )
}
