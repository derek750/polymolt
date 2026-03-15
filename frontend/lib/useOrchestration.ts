"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import type { TradeEntry } from "@/types/trade"

const BACKEND = "http://localhost:8000"
const YEARS = [2021, 2022, 2023, 2024, 2025]

// ── Types ─────────────────────────────────────────────────────────────

interface AgentBet {
  agent_id: string
  agent_name: string
  answer: string // "YES" | "NO"
  confidence: number // 0-100
  reasoning: string
}

export type OrchestrationStatus = "idle" | "running" | "done" | "error"

export interface OrchestrationState {
  question: string
  location: string
  status: OrchestrationStatus
  phaseLabel: string
  currentPrice: number
  priceHistory: number[]
  trades: TradeEntry[]
  initialBets: AgentBet[]
  tradeCount: number
  roundNumber: number
  error: string | null
}

const INITIAL_STATE: OrchestrationState = {
  question: "",
  location: "",
  status: "idle",
  phaseLabel: "",
  currentPrice: 0.5,
  priceHistory: [0.5],
  trades: [],
  initialBets: [],
  tradeCount: 0,
  roundNumber: 0,
  error: null,
}

// ── Hook ──────────────────────────────────────────────────────────────

export function useOrchestration() {
  const [state, setState] = useState<OrchestrationState>(INITIAL_STATE)
  const abortRef = useRef<AbortController | null>(null)
  const tradeIdRef = useRef(0)

  // Place a YES/NO order on the LMSR market and return price before/after
  async function placeOrder(
    side: string,
    dollars: number,
  ): Promise<{ priceBefore: number; priceAfter: number } | null> {
    try {
      const res = await fetch(`${BACKEND}/market/order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          side: side.toUpperCase(),
          dollars: Math.max(0.5, dollars),
        }),
      })
      if (!res.ok) return null
      const data = await res.json()
      return {
        priceBefore: data.trade.price_yes_before,
        priceAfter: data.trade.price_yes_after,
      }
    } catch {
      return null
    }
  }

  // Process an agent bet: place market order, create TradeEntry, update state
  async function handleBet(bet: AgentBet, label: string) {
    const dollars = Math.max(2, bet.confidence / 5)
    const side = bet.answer === "YES" ? "YES" : "NO"
    const result = await placeOrder(side, dollars)
    if (!result) return

    tradeIdRef.current += 1
    const trade: TradeEntry = {
      id: `t-${tradeIdRef.current}`,
      timestamp: new Date().toISOString(),
      agentId: bet.agent_id,
      agentName: bet.agent_name,
      agentType: "specialist",
      direction: side as "YES" | "NO",
      size: dollars,
      priceBefore: result.priceBefore,
      priceAfter: result.priceAfter,
      reasoning: `[${label}] ${bet.reasoning}`.slice(0, 300),
      evidenceTitles: [],
    }

    setState((prev) => ({
      ...prev,
      currentPrice: result.priceAfter,
      priceHistory: [...prev.priceHistory, result.priceAfter],
      trades: [trade, ...prev.trades],
      tradeCount: prev.tradeCount + 1,
    }))
  }

  // Read a Server-Sent Events stream from a POST request
  async function readSSE(
    url: string,
    body: object,
    onEvent: (type: string, data: Record<string, unknown>) => Promise<void>,
    signal: AbortSignal,
  ) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    })
    if (!res.ok) {
      const text = await res.text().catch(() => "")
      throw new Error(`Backend returned ${res.status}: ${text.slice(0, 200)}`)
    }

    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buf = ""
    let eventType = "message"

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })

      const parts = buf.split("\n")
      buf = parts.pop() || ""

      for (const line of parts) {
        if (line.startsWith("event: ")) {
          eventType = line.slice(7).trim()
        } else if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6))
            await onEvent(eventType, data)
          } catch {
            /* skip malformed data */
          }
          eventType = "message"
        }
      }
    }
  }

  // ── Main entry point ────────────────────────────────────────────────

  const start = useCallback(
    async (question: string, location: string) => {
      // Abort any previous run
      abortRef.current?.abort()
      const ac = new AbortController()
      abortRef.current = ac
      tradeIdRef.current = 0

      setState({
        ...INITIAL_STATE,
        question,
        location,
        status: "running",
        phaseLabel: "Resetting market...",
      })

      try {
        // 1. Reset the LMSR market
        await fetch(`${BACKEND}/market/reset`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, starting_price: 0.5 }),
          signal: ac.signal,
        })

        // 2. Phase 1 -- stream initial bets from all agents
        setState((prev) => ({
          ...prev,
          phaseLabel: "Phase 1: Agents placing initial bets...",
          roundNumber: 1,
        }))

        const bets: AgentBet[] = []

        await readSSE(
          `${BACKEND}/ai/phase1/stream`,
          { question, location, use_rag: true },
          async (type, data) => {
            if (type === "agent_done" && data.bet) {
              const bet = data.bet as unknown as AgentBet
              bets.push(bet)
              setState((prev) => ({
                ...prev,
                initialBets: [...bets],
                phaseLabel: `Phase 1: ${bets.length} agent(s) voted...`,
              }))
              await handleBet(bet, "Phase 1")
            }
          },
          ac.signal,
        )

        setState((prev) => ({
          ...prev,
          phaseLabel: "Phase 1 complete. Starting year-by-year analysis...",
        }))

        // 3. Phase 2 -- run for each year sequentially
        for (let i = 0; i < YEARS.length; i++) {
          if (ac.signal.aborted) break
          const year = YEARS[i]

          setState((prev) => ({
            ...prev,
            roundNumber: i + 2,
            phaseLabel: `Phase 2 (Year ${year}): Agents analyzing with RAG context...`,
          }))

          const phase2Body = {
            question,
            location,
            initial_bets: bets.map((b) => ({
              agent_id: b.agent_id,
              agent_name: b.agent_name,
              answer: b.answer,
              confidence: b.confidence,
              reasoning: b.reasoning,
            })),
            year,
          }

          await readSSE(
            `${BACKEND}/ai/phase2/stream`,
            phase2Body,
            async (type, data) => {
              if (type === "agent_second_bet_done" && data.bet) {
                const bet = data.bet as unknown as AgentBet
                await handleBet(bet, `Year ${year}`)
              }
              if (type === "orchestrator_done") {
                const reasoning =
                  typeof data.topic_reasoning === "string"
                    ? data.topic_reasoning
                    : ""
                if (reasoning) {
                  setState((prev) => ({
                    ...prev,
                    phaseLabel: `Phase 2 (Year ${year}): ${reasoning.slice(0, 80)}...`,
                  }))
                }
              }
            },
            ac.signal,
          )

          setState((prev) => ({
            ...prev,
            phaseLabel: `Year ${year} complete.${i < YEARS.length - 1 ? ` Starting ${YEARS[i + 1]}...` : ""}`,
          }))
        }

        // 4. Done
        setState((prev) => ({
          ...prev,
          status: "done",
          phaseLabel: `Analysis complete across ${YEARS.length} years.`,
        }))
      } catch (e) {
        if (ac.signal.aborted) return
        setState((prev) => ({
          ...prev,
          status: "error",
          error: e instanceof Error ? e.message : "Orchestration failed",
          phaseLabel: "Error occurred.",
        }))
      }
    },
    [], // eslint-disable-line react-hooks/exhaustive-deps
  )

  // Abort orchestration on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setState(INITIAL_STATE)
  }, [])

  return { ...state, start, reset }
}
