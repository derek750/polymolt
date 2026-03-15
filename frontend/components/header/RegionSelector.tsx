"use client"

import { Region } from "@/types/market"

interface Props {
  regions: Region[]
  selectedRegion: string
  onSelect: (regionId: string) => void
}

export function RegionSelector({ regions, selectedRegion, onSelect }: Props) {
  if (regions.length === 0) {
    return null
  }

  return (
    <select
      value={selectedRegion}
      onChange={(e) => onSelect(e.target.value)}
      className="appearance-none bg-white border border-neutral-200 rounded px-3 py-1.5 text-sm text-neutral-700 cursor-pointer hover:border-neutral-400 focus:outline-none focus:border-neutral-500 transition-colors"
    >
      {regions.map((region) => (
        <option key={region.id} value={region.id}>
          {region.name}
        </option>
      ))}
    </select>
  )
}
