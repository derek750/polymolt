"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useOrchestration } from "@/lib/useOrchestration"
import { Header } from "@/components/header/Header"
import { MarketPanel } from "@/components/market/MarketPanel"
import { TradeFeed } from "@/components/trades/TradeFeed"
import type { MarketState, Region } from "@/types/market"

export default function DashboardPage() {
  const orch = useOrchestration()
  const [hasStarted, setHasStarted] = useState(false)

  // Read URL params on mount and auto-start orchestration
  useEffect(() => {
    if (hasStarted) return
    const sp = new URLSearchParams(window.location.search)
    const q = sp.get("question")
    const loc = sp.get("location")
    if (q) {
      setHasStarted(true)
      orch.start(q, loc || "")
    }
  }, [hasStarted]) // eslint-disable-line react-hooks/exhaustive-deps

  // Construct MarketState for MarketPanel
  const market: MarketState | null =
    orch.question
      ? {
          regionId: "orchestration",
          question: orch.question,
          currentPrice: orch.currentPrice,
          priceHistory: orch.priceHistory,
          roundNumber: orch.roundNumber,
          isRunning: orch.status === "running",
          tradeCount: orch.tradeCount,
        }
      : null

  const connectionStatus =
    orch.status === "running"
      ? "connected"
      : orch.status === "error"
        ? "error"
        : orch.status === "done"
          ? "connected"
          : "disconnected"

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Header
        regions={[] as Region[]}
        selectedRegion=""
        connectionStatus={connectionStatus as "connected" | "connecting" | "disconnected" | "error"}
        onSelectRegion={() => {}}
        onReset={() => {
          orch.reset()
          setHasStarted(false)
        }}
        onOpenQuestions={() => {}}
      />

      <main className="flex-1 flex flex-col gap-4 p-4 lg:p-5 max-w-[1400px] mx-auto w-full">
        {/* Phase status indicator */}
        {orch.status === "running" && (
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-neutral-50 border border-neutral-200">
            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse flex-shrink-0" />
            <span className="text-sm text-neutral-700">{orch.phaseLabel}</span>
          </div>
        )}

        {orch.status === "done" && (
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-green-50 border border-green-200">
            <div className="h-2 w-2 rounded-full bg-green-600 flex-shrink-0" />
            <span className="text-sm text-green-700">
              {orch.phaseLabel} {orch.tradeCount} total trades.
            </span>
          </div>
        )}

        {orch.status === "error" && (
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-red-50 border border-red-200">
            <span className="text-sm text-red-700">{orch.error}</span>
            <button
              onClick={() => {
                orch.reset()
                setHasStarted(false)
              }}
              className="ml-auto text-xs text-red-600 underline"
            >
              Reset
            </button>
          </div>
        )}

        {/* No question selected */}
        {orch.status === "idle" && !hasStarted && (
          <div className="flex flex-col items-center justify-center gap-4 py-20">
            <p className="text-neutral-500 text-sm">
              No question selected. Click a location on the map to ask a question.
            </p>
            <Link
              href="/map"
              className="px-5 py-2.5 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 transition-colors"
            >
              Go to Map
            </Link>
          </div>
        )}

        {/* Main content: chart + trade feed */}
        {(market || orch.status !== "idle") && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4" style={{ gridTemplateRows: "560px" }}>
              <div className="flex flex-col gap-4 min-h-0 h-full">
                <div className="flex-1 min-h-0 h-full">
                  <MarketPanel market={market} region={null} trades={orch.trades} />
                </div>
              </div>
              <div className="h-full overflow-hidden">
                <TradeFeed
                  trades={orch.trades}
                  onAgentClick={() => window.location.href = "/agents"}
                />
              </div>
            </div>

            <div className="flex items-center gap-3 flex-wrap">
              <Link
                href="/agents"
                className="px-3 py-1.5 rounded border text-xs transition-colors bg-white border-neutral-200 text-neutral-500 hover:border-neutral-400"
              >
                View Agents
              </Link>
              <Link
                href="/map"
                className="px-3 py-1.5 rounded border text-xs transition-colors bg-white border-neutral-200 text-neutral-500 hover:border-neutral-400"
              >
                Ask Another Question
              </Link>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
