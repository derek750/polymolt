"use client"

import { useState } from "react"
import { useMarket } from "@/lib/useMarket"
import { Header } from "@/components/header/Header"
import { MarketPanel } from "@/components/market/MarketPanel"
import { BehaviorStudyView } from "@/components/market/BehaviorStudyView"
import { TradeFeed } from "@/components/trades/TradeFeed"
import { AgentGrid } from "@/components/agents/AgentGrid"
import { AgentDrawer } from "@/components/agents/AgentDrawer"
import { Region } from "@/types/market"

export default function HomePage() {
  const { market, agents, trades, regions, selectedRegion, connectionStatus, selectRegion, resetMarket, shockMarket } = useMarket("scandinavia")
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [showStudyView, setShowStudyView] = useState(false)

  const selectedAgent = agents.find((a) => a.id === selectedAgentId) ?? null
  const currentRegion = (regions.find((r) => r.id === selectedRegion) ?? null) as Region | null

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Header
        regions={regions as Region[]}
        selectedRegion={selectedRegion}
        connectionStatus={connectionStatus}
        onSelectRegion={selectRegion}
        onReset={resetMarket}
      />

      <main className="flex-1 flex flex-col gap-4 p-4 lg:p-5 max-w-[1400px] mx-auto w-full">
        {/* Market + trade feed */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4 items-start">
          <MarketPanel market={market} region={currentRegion} trades={trades} />
          <div className="h-[560px]">
            <TradeFeed
              trades={trades}
              onAgentClick={(id) => setSelectedAgentId(id)}
            />
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3 flex-wrap">
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

          {market?.isRunning && (
            <div className="flex items-center gap-2 ml-auto">
              <button
                onClick={() => shockMarket("negative")}
                className="px-3 py-1.5 rounded border border-neutral-200 text-xs text-neutral-500 hover:border-neutral-400 transition-colors"
              >
                Shock ↓
              </button>
              <button
                onClick={() => shockMarket("positive")}
                className="px-3 py-1.5 rounded border border-neutral-200 text-xs text-neutral-500 hover:border-neutral-400 transition-colors"
              >
                Recover ↑
              </button>
            </div>
          )}
        </div>

        {/* Belief distribution */}
        {showStudyView && market && agents.length > 0 && (
          <BehaviorStudyView
            agents={agents}
            marketPrice={market.currentPrice}
            onAgentClick={(id) => setSelectedAgentId(id)}
          />
        )}

        {/* Agent grid */}
        <AgentGrid
          agents={agents}
          onAgentClick={(id) => setSelectedAgentId(id)}
        />
      </main>

      {/* Agent detail drawer */}
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
