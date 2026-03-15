"use client"

import { useState } from "react"
import { MarketState, Region } from "@/types/market"
import { TradeEntry } from "@/types/trade"
import { ProbabilityDisplay } from "./ProbabilityDisplay"
import { ProbabilityChart } from "./ProbabilityChart"

interface Props {
  market: MarketState | null
  region: Region | null
  trades?: TradeEntry[]
}

export function MarketPanel({ market, region, trades }: Props) {
  const [tradeWindow, setTradeWindow] = useState(60)

  return (
    <div className="flex flex-col gap-3 p-5 bg-white border border-neutral-200 rounded-lg h-full">
      {market ? (
        <>
          <ProbabilityDisplay
            price={market.currentPrice}
            priceHistory={market.priceHistory}
            question={market.question}
          />

          {region && (
            <p className="text-xs text-neutral-400 leading-relaxed border-t border-neutral-100 pt-3">
              {region.description}
            </p>
          )}

          {/* Trade window input */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-neutral-400">Last</span>
            <input
              type="number"
              min={5}
              max={9999}
              value={tradeWindow}
              onChange={(e) => {
                const v = parseInt(e.target.value, 10)
                if (!isNaN(v) && v >= 1) setTradeWindow(v)
              }}
              className="w-16 px-2 py-1 text-xs text-neutral-700 border border-neutral-200 rounded focus:outline-none focus:border-neutral-400 tabular-nums"
            />
            <span className="text-xs text-neutral-400">trades</span>
          </div>

          <div className="flex-1 min-h-[360px]">
            <ProbabilityChart
              priceHistory={market.priceHistory}
              trades={trades}
              maxPoints={tradeWindow}
            />
          </div>

          <div className="flex items-center gap-3 text-xs text-neutral-400 border-t border-neutral-100 pt-3">
            <span>Round {market.roundNumber}</span>
            <span>·</span>
            <span>{market.tradeCount} trades</span>
            <span>·</span>
            <span className={market.isRunning ? "text-neutral-900" : "text-neutral-400"}>
              {market.isRunning ? "Live" : "Paused"}
            </span>
          </div>
        </>
      ) : (
        <div className="flex flex-col gap-3 flex-1 min-h-0">
          <div className="h-12 w-32 rounded bg-neutral-100 animate-pulse" />
          <div className="flex-1 min-h-[360px] rounded bg-neutral-50 animate-pulse" />
        </div>
      )}
    </div>
  )
}
