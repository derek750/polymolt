"use client"

import { useState } from "react"
import Link from "next/link"
import { useMarket } from "@/lib/useMarket"
import { Header } from "@/components/header/Header"
import { MarketPanel } from "@/components/market/MarketPanel"
import { TradeFeed } from "@/components/trades/TradeFeed"
import { RegionNews } from "@/components/region/RegionNews"
import { Region } from "@/types/market"
import { QuestionMenu } from "@/components/questions/QuestionMenu"

export default function DashboardPage() {
  const { market, agents, trades, regions, selectedRegion, connectionStatus, selectRegion, resetMarket, shockMarket } = useMarket("scandinavia")
  const [showQuestions, setShowQuestions] = useState(false)

  const currentRegion = (regions.find((r) => r.id === selectedRegion) ?? null) as Region | null

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Header
        regions={regions as Region[]}
        selectedRegion={selectedRegion}
        connectionStatus={connectionStatus}
        onSelectRegion={selectRegion}
        onReset={resetMarket}
        onOpenQuestions={() => setShowQuestions(true)}
      />

      <main className="flex-1 flex flex-col gap-4 p-4 lg:p-5 max-w-[1400px] mx-auto w-full">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4 items-stretch">
          <div className="flex flex-col gap-4 min-h-0">
            <div className="flex-1 min-h-0">
              <MarketPanel market={market} region={currentRegion} trades={trades} />
            </div>
            <RegionNews region={currentRegion} />
          </div>
          <div className="min-h-[560px] h-full">
            <TradeFeed
              trades={trades}
              onAgentClick={(id) => window.location.href = `/agents`}
            />
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <Link
            href="/agents"
            className="px-3 py-1.5 rounded border text-xs transition-colors bg-white border-neutral-200 text-neutral-500 hover:border-neutral-400"
          >
            View Agents ({agents.length})
          </Link>

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
      </main>

      <QuestionMenu
        open={showQuestions}
        onClose={() => setShowQuestions(false)}
      />
    </div>
  )
}
