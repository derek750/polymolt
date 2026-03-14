"use client"

import { useRef, useEffect, useCallback, useImperativeHandle, forwardRef } from "react"
import mapboxgl from "mapbox-gl"
import "mapbox-gl/dist/mapbox-gl.css"
import type { MapLayerMouseEvent } from "mapbox-gl"
import type { SelectedFeature } from "@/types/map"

const TORONTO_CENTER: [number, number] = [-79.3832, 43.6532]
const CLICKABLE_LAYERS = ["poi-label", "transit-label", "building", "road-label"]
const CLICKABLE_LAYERS_AFTER_LOAD = ["3d-buildings"]

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
}

export const TorontoMap = forwardRef<TorontoMapRef, TorontoMapProps>(function TorontoMap({
  selectedFeature,
  onFeatureSelect,
  pulseCoordinates,
  mapStyle,
  panelOpen,
  onError,
}, ref) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const pulseMarkerRef = useRef<mapboxgl.Marker | null>(null)

  useImperativeHandle(ref, () => ({
    flyTo(lng: number, lat: number, zoom = 15) {
      mapRef.current?.flyTo({ center: [lng, lat], zoom, duration: 1500 })
    },
  }), [])

  // Pan map slightly left when panel opens so feature isn't hidden
  useEffect(() => {
    const map = mapRef.current
    if (!map || !selectedFeature || !panelOpen) return
    const [lng, lat] = selectedFeature.coordinates
    map.easeTo({
      center: [lng - 0.008, lat],
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
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: mapStyle,
      center: TORONTO_CENTER,
      zoom: 13,
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
            minzoom: 13,
            paint: {
              "fill-extrusion-color": "#aaa",
              "fill-extrusion-height": ["interpolate", ["linear"], ["zoom"], 13, 0, 15, ["get", "height"]],
              "fill-extrusion-base": ["interpolate", ["linear"], ["zoom"], 13, 0, 15, ["get", "min_height"]],
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
