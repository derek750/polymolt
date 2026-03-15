"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import Link from "next/link"
import { TorontoMap, type TorontoMapRef } from "@/components/map/TorontoMap"
import { LocationSidePanel } from "@/components/map/LocationSidePanel"
import { BetLocationList } from "@/components/map/BetLocationList"
import type { SelectedFeature, BetLocation } from "@/types/map"
import type { QuestionSummary } from "@/types/question"
import { BACKEND_URL } from "@/lib/config"

const MAPBOX_STREETS = "mapbox://styles/mapbox/streets-v12"
const MAPBOX_SATELLITE = "mapbox://styles/mapbox/satellite-streets-v12"

const TORONTO_BBOX = "-79.6392,43.5810,-79.1152,43.8555"

interface SearchResult {
  id: string
  place_name: string
  center: [number, number]
  text?: string
}

async function geocodeLocation(
  location: string,
  token: string
): Promise<[number, number] | null> {
  try {
    const res = await fetch(
      `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(location)}.json?access_token=${token}&bbox=${TORONTO_BBOX}&limit=1`
    )
    const data = await res.json()
    const coords = data.features?.[0]?.center as [number, number] | undefined
    return coords ?? null
  } catch {
    return null
  }
}

export default function MapPage() {
  const [selectedFeature, setSelectedFeature] = useState<SelectedFeature | null>(null)
  const [pulseCoordinates, setPulseCoordinates] = useState<[number, number] | null>(null)
  const [mapStyle, setMapStyle] = useState(MAPBOX_STREETS)
  const [panelOpen, setPanelOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const [mapError, setMapError] = useState<string | null>(null)

  const [betLocations, setBetLocations] = useState<BetLocation[]>([])
  const [betsLoading, setBetsLoading] = useState(true)
  const [activeBetId, setActiveBetId] = useState<number | null>(null)

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)")
    const fn = () => setIsMobile(mq.matches)
    fn()
    mq.addEventListener("change", fn)
    return () => mq.removeEventListener("change", fn)
  }, [])

  // Fetch questions from DB and geocode their locations
  useEffect(() => {
    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN
    if (!token) {
      setBetsLoading(false)
      return
    }

    let cancelled = false

    async function loadBets() {
      try {
        const res = await fetch(`${BACKEND_URL}/db/questions?limit=50`)
        if (!res.ok) throw new Error("Failed to fetch questions")
        const data = await res.json()
        const questions: QuestionSummary[] = data.questions ?? data ?? []

        const withLocation = questions.filter((q) => q.location?.trim())

        // Deduplicate location strings for geocoding
        const uniqueLocations = [...new Set(withLocation.map((q) => q.location.trim()))]
        const coordCache = new Map<string, [number, number]>()

        await Promise.all(
          uniqueLocations.map(async (loc) => {
            const coords = await geocodeLocation(loc, token!)
            if (coords) coordCache.set(loc, coords)
          })
        )

        if (cancelled) return

        const bets: BetLocation[] = withLocation
          .filter((q) => coordCache.has(q.location.trim()))
          .map((q) => ({
            questionId: q.id,
            questionText: q.question_text,
            location: q.location,
            coordinates: coordCache.get(q.location.trim())!,
            createdAt: q.created_at,
            yesCount: q.yes_count,
            noCount: q.no_count,
          }))

        setBetLocations(bets)
      } catch {
        // Silently fail — bets panel will show "no bets"
      } finally {
        if (!cancelled) setBetsLoading(false)
      }
    }

    loadBets()
    return () => { cancelled = true }
  }, [])

  const handleFeatureSelect = useCallback((feature: SelectedFeature | null) => {
    if (feature) {
      setHintDismissed(true)
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
      setActiveBetId(null)
    }
  }, [])

  const handleClosePanel = useCallback(() => {
    setSelectedFeature(null)
    setPulseCoordinates(null)
    setPanelOpen(false)
    setActiveBetId(null)
  }, [])

  const handleBetClick = useCallback(
    (bet: BetLocation) => {
      const [lng, lat] = bet.coordinates
      const feature: SelectedFeature = {
        name: bet.location,
        type: "bet",
        coordinates: [lng, lat],
        layerId: "bet",
      }
      setHintDismissed(true)
      setSelectedFeature(feature)
      setPulseCoordinates([lng, lat])
      setPanelOpen(true)
      setActiveBetId(bet.questionId)
      mapRef.current?.flyTo(lng, lat, 15)
    },
    []
  )

  const [searchQuery, setSearchQuery] = useState("")
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searchDropdownOpen, setSearchDropdownOpen] = useState(false)
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [flyComplete, setFlyComplete] = useState(false)
  const [hintDismissed, setHintDismissed] = useState(false)
  const mapRef = useRef<TorontoMapRef>(null)

  useEffect(() => {
    const q = searchQuery.trim()
    if (!q) {
      setSearchResults([])
      setSearchDropdownOpen(false)
      return
    }
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current)
    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN
    if (!token) return
    searchDebounceRef.current = setTimeout(async () => {
      setSearching(true)
      setMapError(null)
      try {
        const res = await fetch(
          `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(q)}.json?access_token=${token}&country=CA&bbox=${TORONTO_BBOX}&limit=6`
        )
        const data = await res.json()
        const features = (data.features ?? []) as Array<{ id: string; place_name: string; center: [number, number]; text?: string }>
        setSearchResults(features)
        setSearchDropdownOpen(features.length > 0)
      } catch {
        setMapError("Geocoding failed")
        setSearchResults([])
      } finally {
        setSearching(false)
      }
    }, 300)
    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current)
    }
  }, [searchQuery])

  const handleSelectSearchResult = useCallback(
    (result: SearchResult) => {
      const [lng, lat] = result.center
      const feature: SelectedFeature = {
        name: result.place_name,
        type: "place",
        coordinates: [lng, lat],
        layerId: "search",
      }
      setHintDismissed(true)
      setSearchQuery("")
      setSearchResults([])
      setSearchDropdownOpen(false)
      setSelectedFeature(feature)
      setPulseCoordinates([lng, lat])
      setPanelOpen(true)
      setActiveBetId(null)
      mapRef.current?.flyTo(lng, lat, 16)
    },
    []
  )

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
        animateFromWorld
        onFlyComplete={() => setFlyComplete(true)}
      />

      {/* Top-left controls */}
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2 max-w-[320px]">
        <Link
          href="/"
          className="rounded-lg bg-white/95 backdrop-blur shadow-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 flex items-center gap-2 w-fit"
        >
          ← Back to home
        </Link>
        <div className="relative">
          <div className="flex gap-2 rounded-lg bg-white/95 backdrop-blur shadow-lg border border-neutral-200 p-1.5">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => searchResults.length > 0 && setSearchDropdownOpen(true)}
              onBlur={() => setTimeout(() => setSearchDropdownOpen(false), 150)}
              placeholder="Search Toronto..."
              className="flex-1 min-w-0 rounded-md border-0 bg-transparent px-2 py-1.5 text-sm text-neutral-900 placeholder-neutral-400 focus:outline-none focus:ring-0"
              aria-expanded={searchDropdownOpen}
              aria-haspopup="listbox"
              aria-controls="search-results-list"
            />
            {searching && (
              <span className="flex items-center px-2 text-neutral-400 text-sm">…</span>
            )}
          </div>
          {searchDropdownOpen && searchResults.length > 0 && (
            <ul
              id="search-results-list"
              role="listbox"
              className="absolute top-full left-0 right-0 mt-1 rounded-lg bg-white shadow-xl border border-neutral-200 overflow-hidden max-h-64 overflow-y-auto z-30"
            >
              {searchResults.map((result) => (
                <li
                  key={result.id}
                  role="option"
                  tabIndex={0}
                  className="px-3 py-2.5 text-sm text-neutral-900 hover:bg-neutral-50 cursor-pointer border-b border-neutral-100 last:border-b-0"
                  onMouseDown={(e) => {
                    e.preventDefault()
                    handleSelectSearchResult(result)
                  }}
                >
                  <span className="font-medium">{result.text ?? result.place_name}</span>
                  {result.place_name !== (result.text ?? result.place_name) && (
                    <span className="block text-xs text-neutral-500 mt-0.5 truncate">{result.place_name}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
        <button
          type="button"
          onClick={() => setMapStyle((s) => (s === MAPBOX_STREETS ? MAPBOX_SATELLITE : MAPBOX_STREETS))}
          className="rounded-lg bg-white/95 backdrop-blur shadow-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-50"
        >
          {mapStyle === MAPBOX_STREETS ? "Satellite" : "Streets"}
        </button>

        {/* Bet locations list */}
        <BetLocationList
          bets={betLocations}
          loading={betsLoading}
          onBetClick={handleBetClick}
          activeBetId={activeBetId}
        />
      </div>

      {mapError && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 rounded-lg bg-red-500/90 text-white px-4 py-2 text-sm shadow-lg">
          {mapError}
        </div>
      )}

      {!panelOpen && !hintDismissed && (
        <div
          className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 flex items-center gap-3 px-5 py-3.5 rounded-2xl bg-neutral-900 text-white shadow-xl border border-neutral-700 ring-2 ring-white/20"
          role="status"
          aria-live="polite"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/20 text-lg" aria-hidden>
            👆
          </span>
          <div>
            <p className="text-sm font-semibold">Click any location on the map</p>
            <p className="text-xs text-white/80 mt-0.5">to ask questions and see market predictions</p>
          </div>
        </div>
      )}

      {selectedFeature && panelOpen && (
        <LocationSidePanel
          feature={selectedFeature}
          onClose={handleClosePanel}
          isMobile={isMobile}
          betLocations={betLocations}
        />
      )}
    </div>
  )
}
