"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { MarketState, Region } from "@/types/market"
import { Agent } from "@/types/agent"
import { TradeEntry } from "@/types/trade"

const API_BASE = "http://localhost:8000"
const MAX_TRADES = 150
const MAX_BELIEF_HISTORY = 50

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error"

interface UseMarketReturn {
  market: MarketState | null
  agents: Agent[]
  trades: TradeEntry[]
  regions: Region[]
  selectedRegion: string
  connectionStatus: ConnectionStatus
  selectRegion: (regionId: string) => void
  resetMarket: () => void
  shockMarket: (type: "negative" | "positive") => Promise<void>
}

export function useMarket(defaultRegion = "scandinavia"): UseMarketReturn {
  const [market, setMarket] = useState<MarketState | null>(null)
  const [agents, setAgents] = useState<Agent[]>([])
  const [trades, setTrades] = useState<TradeEntry[]>([])
  const [regions, setRegions] = useState<Region[]>([])
  const [selectedRegion, setSelectedRegion] = useState(defaultRegion)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("connecting")

  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const currentRegionRef = useRef(defaultRegion)
  const beliefHistoryRef = useRef<Record<string, number[]>>({})

  // Fetch region list once
  useEffect(() => {
    fetch(`${API_BASE}/regions`)
      .then((r) => r.json())
      .then((data) => setRegions(data.regions ?? []))
      .catch(console.error)
  }, [])

  // Append current belief to per-agent history and return augmented agent
  const augmentWithHistory = useCallback((agent: Agent): Agent => {
    const prev = beliefHistoryRef.current[agent.id] ?? []
    const next = [...prev, agent.currentBelief].slice(-MAX_BELIEF_HISTORY)
    beliefHistoryRef.current[agent.id] = next
    return { ...agent, beliefHistory: next }
  }, [])

  const connect = useCallback((regionId: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }

    setConnectionStatus("connecting")
    const es = new EventSource(`${API_BASE}/market/${regionId}/stream`)
    eventSourceRef.current = es

    es.onopen = () => {
      setConnectionStatus("connected")
    }

    es.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        handleMessage(msg)
      } catch (e) {
        console.error("SSE parse error", e)
      }
    }

    es.onerror = () => {
      setConnectionStatus("disconnected")
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      reconnectTimer.current = setTimeout(() => {
        connect(currentRegionRef.current)
      }, 3000)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleMessage = useCallback((msg: { type: string; data: unknown }) => {
    switch (msg.type) {
      case "market_reset": {
        const d = msg.data as { agents?: Agent[]; recentTrades?: TradeEntry[] } & MarketState
        // Clear belief history on reset
        beliefHistoryRef.current = {}
        setMarket({
          regionId: d.regionId,
          question: d.question,
          currentPrice: d.currentPrice,
          priceHistory: d.priceHistory ?? [],
          roundNumber: d.roundNumber,
          isRunning: d.isRunning,
          tradeCount: d.tradeCount ?? 0,
        })
        if (d.agents) setAgents(d.agents.map((a) => augmentWithHistory(a)))
        if (d.recentTrades) setTrades(d.recentTrades)
        else setTrades([])
        break
      }

      case "trade": {
        const d = msg.data as { trade: TradeEntry; agent: Agent; market: MarketState }
        setTrades((prev) => {
          const next = [d.trade, ...prev]
          return next.slice(0, MAX_TRADES)
        })
        setMarket(d.market)
        setAgents((prev) =>
          prev.map((a) => (a.id === d.agent.id ? augmentWithHistory(d.agent) : a))
        )
        break
      }

      case "agent_update": {
        const agent = msg.data as Agent
        setAgents((prev) =>
          prev.map((a) => (a.id === agent.id ? augmentWithHistory(agent) : a))
        )
        break
      }

      default:
        break
    }
  }, [augmentWithHistory])

  // Initial connection
  useEffect(() => {
    connect(defaultRegion)
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (eventSourceRef.current) eventSourceRef.current.close()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const selectRegion = useCallback((regionId: string) => {
    currentRegionRef.current = regionId
    setSelectedRegion(regionId)
    setTrades([])
    setMarket(null)
    connect(regionId)
  }, [connect])

  const resetMarket = useCallback(async () => {
    setTrades([])
    const regionId = currentRegionRef.current
    try {
      await fetch(`${API_BASE}/market/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ market_id: regionId }),
      })
      connect(regionId)
    } catch (e) {
      console.error("Reset request failed", e)
    }
  }, [connect])

  const shockMarket = useCallback(async (type: "negative" | "positive") => {
    const regionId = currentRegionRef.current
    try {
      await fetch(`${API_BASE}/market/${regionId}/shock?shock_type=${type}&rounds=20`, {
        method: "POST",
      })
    } catch (e) {
      console.error("Shock request failed", e)
    }
  }, [])

  return {
    market,
    agents,
    trades,
    regions,
    selectedRegion,
    connectionStatus,
    selectRegion,
    resetMarket,
    shockMarket,
  }
}
