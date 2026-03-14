"use client"

import { Region } from "@/types/market"
import { ConnectionStatus } from "@/lib/useMarket"
import { RegionSelector } from "./RegionSelector"

interface Props {
  regions: Region[]
  selectedRegion: string
  connectionStatus: ConnectionStatus
  onSelectRegion: (id: string) => void
  onReset: () => void
}

export function Header({ regions, selectedRegion, connectionStatus, onSelectRegion, onReset }: Props) {
  const statusText =
    connectionStatus === "connected" ? "Connected" :
    connectionStatus === "connecting" ? "Connecting…" :
    connectionStatus === "error" ? "Error" : "Disconnected"

  return (
    <header className="sticky top-0 z-50 flex items-center justify-between px-6 py-3 bg-white border-b border-neutral-200">
      <div className="flex items-center gap-3">
        <span className="font-bold text-neutral-900 text-lg tracking-tight">polymolt</span>
      </div>

      <div className="flex items-center gap-3">
        <RegionSelector
          regions={regions}
          selectedRegion={selectedRegion}
          onSelect={onSelectRegion}
        />

        <button
          onClick={onReset}
          className="px-3 py-1.5 text-xs text-neutral-500 border border-neutral-200 rounded hover:border-neutral-400 hover:text-neutral-700 transition-colors"
        >
          Reset
        </button>

        <span className={`text-xs ${
          connectionStatus === "connected" ? "text-neutral-500" : "text-neutral-400"
        }`}>
          {statusText}
        </span>
      </div>
    </header>
  )
}
