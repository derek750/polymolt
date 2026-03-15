"use client"

import { useRef, useEffect, useCallback, useImperativeHandle, forwardRef } from "react"
import mapboxgl from "mapbox-gl"
import "mapbox-gl/dist/mapbox-gl.css"
import type { MapLayerMouseEvent } from "mapbox-gl"
import type { SelectedFeature } from "@/types/map"

const TORONTO_CENTER: [number, number] = [-79.3832, 43.6532]
/** Toronto area bounds: [sw.lng, sw.lat, ne.lng, ne.lat] — lock pan/zoom inside */
const TORONTO_BOUNDS: [[number, number], [number, number]] = [
  [-79.6392, 43.581],   // SW
  [-79.1152, 43.8555],  // NE
]
/** World view zoom before flying in to Toronto */
const WORLD_ZOOM = 1.8
/** Toronto zoom after fly-in */
const TORONTO_ZOOM = 11.8
/** Fly-in duration (ms) */
const FLY_DURATION = 3200

const CLICKABLE_LAYERS = ["poi-label", "transit-label", "building", "road-label"]
const CLICKABLE_LAYERS_AFTER_LOAD = ["3d-buildings"]

/** Small polygon footprint (lng/lat) and height in meters for 3D landmarks */
const TORONTO_3D_LANDMARKS: Array<{
  id: string
  name: string
  polygon: [number, number][]
  height: number
  base?: number
  color?: string
}> = [
  {
    id: "cn-tower",
    name: "CN Tower",
    polygon: [
      [-79.3874, 43.6424],
      [-79.3868, 43.6424],
      [-79.3868, 43.6428],
      [-79.3874, 43.6428],
      [-79.3874, 43.6424],
    ],
    height: 553,
    base: 0,
    color: "#6366f1",
  },
  {
    id: "first-canadian-place",
    name: "First Canadian Place",
    polygon: [
      [-79.3816, 43.6485],
      [-79.3808, 43.6485],
      [-79.3808, 43.6491],
      [-79.3816, 43.6491],
      [-79.3816, 43.6485],
    ],
    height: 298,
    color: "#94a3b8",
  },
  {
    id: "rogers-centre",
    name: "Rogers Centre",
    polygon: [
      [-79.3894, 43.6410],
      [-79.3886, 43.6410],
      [-79.3886, 43.6418],
      [-79.3894, 43.6418],
      [-79.3894, 43.6410],
    ],
    height: 86,
    color: "#64748b",
  },
  {
    id: "scotiabank-arena",
    name: "Scotiabank Arena",
    polygon: [
      [-79.3782, 43.6430],
      [-79.3774, 43.6430],
      [-79.3774, 43.6436],
      [-79.3782, 43.6436],
      [-79.3782, 43.6430],
    ],
    height: 45,
    color: "#64748b",
  },
]

function addTorontoLandmarks3D(
  map: mapboxgl.Map,
  beforeId: string | undefined
): void {
  TORONTO_3D_LANDMARKS.forEach((landmark) => {
    const sourceId = `landmark-3d-${landmark.id}`
    const layerId = `landmark-3d-layer-${landmark.id}`
    if (map.getSource(sourceId)) return
    map.addSource(sourceId, {
      type: "geojson",
      data: {
        type: "Feature",
        properties: {
          height: landmark.height,
          min_height: landmark.base ?? 0,
          name: landmark.name,
        },
        geometry: {
          type: "Polygon",
          coordinates: [landmark.polygon],
        },
      },
    })
    map.addLayer(
      {
        id: layerId,
        type: "fill-extrusion",
        source: sourceId,
        minzoom: 8,
        paint: {
          "fill-extrusion-color": landmark.color ?? "#94a3b8",
          "fill-extrusion-height": ["get", "height"],
          "fill-extrusion-base": ["get", "min_height"],
          "fill-extrusion-opacity": 0.85,
        },
      },
      beforeId
    )
  })
}

export interface TorontoMapRef {
  flyTo: (lng: number, lat: number, zoom?: number) => void
}

interface TorontoMapProps {
  selectedFeature: SelectedFeature | null
  onFeatureSelect: (feature: SelectedFeature | null) => void
  pulseCoordinates: [number, number] | null
  mapStyle: string
  panelOpen: boolean
  onError?: (message: string) => void
  /** When true, map starts at world view then flies into Toronto and locks bounds. */
  animateFromWorld?: boolean
  /** Called when the initial fly-to-Toronto animation finishes (and bounds are locked). */
  onFlyComplete?: () => void
}

export const TorontoMap = forwardRef<TorontoMapRef, TorontoMapProps>(function TorontoMap({
  selectedFeature,
  onFeatureSelect,
  pulseCoordinates,
  mapStyle,
  panelOpen,
  onError,
  animateFromWorld = true,
  onFlyComplete,
}, ref) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const pulseMarkerRef = useRef<mapboxgl.Marker | null>(null)

  useImperativeHandle(ref, () => ({
    flyTo(lng: number, lat: number, zoom = 15) {
      mapRef.current?.flyTo({ center: [lng, lat], zoom, duration: 1500 })
    },
  }), [])

  // Center the selected location on screen when the panel opens
  useEffect(() => {
    const map = mapRef.current
    if (!map || !selectedFeature || !panelOpen) return
    const [lng, lat] = selectedFeature.coordinates
    map.easeTo({
      center: [lng, lat],
      duration: 300,
      easing: (t) => t,
    })
  }, [selectedFeature, panelOpen])

  // Pulse marker at clicked coordinates
  useEffect(() => {
    const map = mapRef.current
    if (!map || !pulseCoordinates) {
      if (pulseMarkerRef.current) {
        pulseMarkerRef.current.remove()
        pulseMarkerRef.current = null
      }
      return
    }
    if (pulseMarkerRef.current) pulseMarkerRef.current.remove()
    const el = document.createElement("div")
    el.className = "pulse-ring"
    el.style.width = "24px"
    el.style.height = "24px"
    el.style.borderRadius = "50%"
    el.style.border = "2px solid rgba(59, 130, 246, 0.8)"
    el.style.background = "rgba(59, 130, 246, 0.2)"
    el.style.animation = "pulse-ring 1.2s ease-out infinite"
    el.style.pointerEvents = "none"
    const marker = new mapboxgl.Marker({ element: el })
      .setLngLat(pulseCoordinates)
      .addTo(map)
    pulseMarkerRef.current = marker
    return () => {
      marker.remove()
      pulseMarkerRef.current = null
    }
  }, [pulseCoordinates])

  const handleMapClick = useCallback(
    (e: MapLayerMouseEvent) => {
      e.preventDefault()
      const features = e.features
      if (!features?.length) {
        onFeatureSelect(null)
        return
      }
      const f = features[0]
      const props = f.properties ?? {}
      const name =
        props.name ??
        props.name_en ??
        props.title ??
        props["name:en"] ??
        "Unnamed"
      const type = props.type ?? props.class ?? f.layer?.id ?? "Unknown"
      const coords = (f.geometry?.type === "Point"
        ? (f.geometry as GeoJSON.Point).coordinates
        : e.lngLat.toArray()) as [number, number]
      onFeatureSelect({
        name: String(name),
        type: String(type),
        coordinates: coords,
        layerId: f.layer?.id ?? "unknown",
      })
    },
    [onFeatureSelect]
  )

  useEffect(() => {
    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN
    if (!token) {
      onError?.("Mapbox token not set (NEXT_PUBLIC_MAPBOX_TOKEN)")
      return
    }
    if (!containerRef.current) return

    mapboxgl.accessToken = token
    const startZoom = animateFromWorld ? WORLD_ZOOM : TORONTO_ZOOM
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: mapStyle,
      center: TORONTO_CENTER,
      zoom: startZoom,
      maxBounds: animateFromWorld ? undefined : TORONTO_BOUNDS,
    })

    map.addControl(new mapboxgl.NavigationControl(), "top-right")

    map.on("error", (e) => {
      onError?.(e.error?.message ?? "Map failed to load")
    })

    map.on("load", () => {
      const style = map.getStyle()
      const layers = style.layers ?? []
      let firstSymbolId: string | undefined
      for (const layer of layers) {
        if (layer.type === "symbol") {
          firstSymbolId = layer.id
          break
        }
      }
      if (style.sources?.composite) {
        map.addLayer(
          {
            id: "3d-buildings",
            source: "composite",
            "source-layer": "building",
            filter: ["==", "extrude", "true"],
            type: "fill-extrusion",
            minzoom: 8,
            paint: {
              "fill-extrusion-color": "#aaa",
              "fill-extrusion-height": [
                "interpolate", ["linear"], ["zoom"],
                8, ["*", ["coalesce", ["get", "height"], 10], 0.15],
                11, ["*", ["coalesce", ["get", "height"], 10], 0.4],
                13, ["*", ["coalesce", ["get", "height"], 10], 0.7],
                15, ["coalesce", ["get", "height"], 10],
              ],
              "fill-extrusion-base": [
                "interpolate", ["linear"], ["zoom"],
                8, ["*", ["coalesce", ["get", "min_height"], 0], 0.15],
                11, ["*", ["coalesce", ["get", "min_height"], 0], 0.4],
                13, ["*", ["coalesce", ["get", "min_height"], 0], 0.7],
                15, ["coalesce", ["get", "min_height"], 0],
              ],
              "fill-extrusion-opacity": 0.7,
            },
          },
          firstSymbolId
        )
        CLICKABLE_LAYERS_AFTER_LOAD.forEach((layerId) => {
          if (map.getLayer(layerId)) {
            map.on("mouseenter", layerId, () => {
              map.getCanvas().style.cursor = "pointer"
            })
            map.on("mouseleave", layerId, () => {
              map.getCanvas().style.cursor = ""
            })
            map.on("click", layerId, handleMapClick)
          }
        })
      }

      addTorontoLandmarks3D(map, firstSymbolId)

      CLICKABLE_LAYERS.forEach((layerId) => {
        if (map.getLayer(layerId)) {
          map.on("mouseenter", layerId, () => {
            map.getCanvas().style.cursor = "pointer"
          })
          map.on("mouseleave", layerId, () => {
            map.getCanvas().style.cursor = ""
          })
          map.on("click", layerId, handleMapClick)
        }
      })

      const lockAndComplete = () => {
        map.setMaxBounds(TORONTO_BOUNDS)
        onFlyComplete?.()
      }

      if (animateFromWorld) {
        map.flyTo({
          center: TORONTO_CENTER,
          zoom: TORONTO_ZOOM,
          pitch: 45,
          bearing: 0,
          duration: FLY_DURATION,
          essential: true,
        })
        map.once("moveend", () => {
          lockAndComplete()
        })
      } else {
        map.setPitch(45)
        lockAndComplete()
      }
    })

    map.on("click", (e) => {
      const target = e.originalEvent?.target as HTMLElement
      if (target?.closest?.(".mapboxgl-popup")) return
      const features = map.queryRenderedFeatures(e.point, {
        layers: [...CLICKABLE_LAYERS, ...CLICKABLE_LAYERS_AFTER_LOAD],
      })
      if (!features.length) onFeatureSelect(null)
    })

    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [mapStyle]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 w-full h-full"
      style={{ width: "100vw", height: "100vh" }}
    />
  )
})
