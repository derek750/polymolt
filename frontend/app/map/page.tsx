"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { TorontoMap, type TorontoMapRef } from "@/components/map/TorontoMap"
import { LocationSidePanel } from "@/components/map/LocationSidePanel"
import type { SelectedFeature } from "@/types/map"

const MAPBOX_STREETS = "mapbox://styles/mapbox/streets-v12"
const MAPBOX_SATELLITE = "mapbox://styles/mapbox/satellite-streets-v12"

export default function MapPage() {
  const [selectedFeature, setSelectedFeature] = useState<SelectedFeature | null>(null)
  const [pulseCoordinates, setPulseCoordinates] = useState<[number, number] | null>(null)
  const [mapStyle, setMapStyle] = useState(MAPBOX_STREETS)
  const [panelOpen, setPanelOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const [mapError, setMapError] = useState<string | null>(null)

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)")
    const fn = () => setIsMobile(mq.matches)
    fn()
    mq.addEventListener("change", fn)
    return () => mq.removeEventListener("change", fn)
  }, [])

  const handleFeatureSelect = useCallback((feature: SelectedFeature | null) => {
    if (feature) {
      setSelectedFeature((prev) => {
        if (prev && prev.name === feature.name && prev.coordinates[0] === feature.coordinates[0] && prev.coordinates[1] === feature.coordinates[1]) {
          return prev
        }
        return feature
      })
      setPulseCoordinates(feature.coordinates)
      setPanelOpen(true)
    } else {
      setSelectedFeature(null)
      setPulseCoordinates(null)
      setPanelOpen(false)
    }
  }, [])

  const handleClosePanel = useCallback(() => {
    setSelectedFeature(null)
    setPulseCoordinates(null)
    setPanelOpen(false)
  }, [])

  const [searchQuery, setSearchQuery] = useState("")
  const [searching, setSearching] = useState(false)
  const mapRef = useRef<TorontoMapRef>(null)

  const handleSearch = useCallback(async () => {
    const q = searchQuery.trim()
    if (!q) return
    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN
    if (!token) {
      setMapError("Mapbox token not configured")
      return
    }
    setSearching(true)
    setMapError(null)
    try {
      const res = await fetch(
        `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(q)}.json?access_token=${token}&country=CA&bbox=-79.6392,43.5810,-79.1152,43.8555`
      )
      const data = await res.json()
      const features = data.features ?? []
      if (features.length === 0) {
        setMapError("No results in Toronto")
        return
      }
      const [lng, lat] = features[0].center
      mapRef.current?.flyTo(lng, lat, 15)
    } catch {
      setMapError("Geocoding failed")
    } finally {
      setSearching(false)
    }
  }, [searchQuery])

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      <TorontoMap
        ref={mapRef}
        selectedFeature={selectedFeature}
        onFeatureSelect={handleFeatureSelect}
        pulseCoordinates={pulseCoordinates}
        mapStyle={mapStyle}
        panelOpen={panelOpen}
        onError={setMapError}
      />

      {/* Top-left controls */}
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2 max-w-[280px]">
        <div className="flex gap-2 rounded-lg bg-white/95 backdrop-blur shadow-lg border border-neutral-200 p-1.5">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Search Toronto..."
            className="flex-1 min-w-0 rounded-md border-0 bg-transparent px-2 py-1.5 text-sm text-neutral-900 placeholder-neutral-400 focus:outline-none focus:ring-0"
          />
          <button
            type="button"
            onClick={handleSearch}
            disabled={searching}
            className="px-3 py-1.5 rounded-md bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 disabled:opacity-50"
          >
            {searching ? "…" : "Go"}
          </button>
        </div>
        <button
          type="button"
          onClick={() => setMapStyle((s) => (s === MAPBOX_STREETS ? MAPBOX_SATELLITE : MAPBOX_STREETS))}
          className="rounded-lg bg-white/95 backdrop-blur shadow-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-50"
        >
          {mapStyle === MAPBOX_STREETS ? "Satellite" : "Streets"}
        </button>
      </div>

      {mapError && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 rounded-lg bg-red-500/90 text-white px-4 py-2 text-sm shadow-lg">
          {mapError}
        </div>
      )}

      {selectedFeature && panelOpen && (
        <LocationSidePanel
          feature={selectedFeature}
          onClose={handleClosePanel}
          isMobile={isMobile}
        />
      )}
    </div>
  )
}
