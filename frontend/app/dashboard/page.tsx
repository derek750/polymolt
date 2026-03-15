"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { useOrchestration } from "@/lib/OrchestrationContext"
import { Header } from "@/components/header/Header"
import { MarketPanel } from "@/components/market/MarketPanel"
import { TradeFeed } from "@/components/trades/TradeFeed"
import { AgentReasoningDrawer } from "@/components/trades/AgentReasoningDrawer"
import type { MarketState, Region } from "@/types/market"
import type { QuestionSummary } from "@/types/question"
import { BACKEND_URL } from "@/lib/config"

export default function DashboardPage() {
  const router = useRouter()
  const orch = useOrchestration()
  const [hasStarted, setHasStarted] = useState(false)
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [pastQuestions, setPastQuestions] = useState<QuestionSummary[]>([])
  const [loadingQuestions, setLoadingQuestions] = useState(false)
  const [questionsError, setQuestionsError] = useState<string | null>(null)
  const [fetchTrigger, setFetchTrigger] = useState(0)

  // Read URL params on mount and auto-start orchestration or load historical
  useEffect(() => {
    if (hasStarted) return
    const sp = new URLSearchParams(window.location.search)

    const qid = sp.get("question_id")
    if (qid) {
      const id = parseInt(qid, 10)
      if (!isNaN(id)) {
        setHasStarted(true)
        orch.loadHistorical(id)
        return
      }
    }

    const q = sp.get("question")
    const loc = sp.get("location")
    if (q) {
      setHasStarted(true)
      orch.start(q, loc || "")
    }
  }, [hasStarted]) // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch past questions when idle
  useEffect(() => {
    if (hasStarted) return
    setLoadingQuestions(true)
    setQuestionsError(null)
    fetch(`${BACKEND_URL}/db/questions`)
      .then(async (r) => {
        const data = await r.json().catch(() => ({}))
        if (!r.ok) {
          const msg = typeof (data as { detail?: string }).detail === "string"
            ? (data as { detail: string }).detail
            : `Failed to load questions (${r.status})`
          throw new Error(msg)
        }
        return data as { questions?: QuestionSummary[] }
      })
      .then((data) => {
        const list = Array.isArray(data?.questions) ? data.questions : []
        setPastQuestions(list)
      })
      .catch((e) => {
        setPastQuestions([])
        setQuestionsError(e instanceof Error ? e.message : "Failed to load questions")
      })
      .finally(() => setLoadingQuestions(false))
  }, [hasStarted, fetchTrigger])

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
        onOpenQuestions={() => router.push("/questions")}
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

        {/* Idle: show past questions */}
        {orch.status === "idle" && !hasStarted && (
          <div className="flex flex-col gap-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-neutral-900">Past Questions</h2>
                <p className="text-sm text-neutral-500 mt-0.5">
                  Select a question to rerun the market simulation, or ask a new one from the map.
                </p>
              </div>
              <Link
                href="/map"
                className="flex-shrink-0 px-4 py-2 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 transition-colors"
              >
                Ask New Question
              </Link>
            </div>

            {loadingQuestions && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="rounded-lg border border-neutral-200 p-4 space-y-3 animate-pulse">
                    <div className="h-4 w-24 bg-neutral-100 rounded" />
                    <div className="h-3 w-full bg-neutral-50 rounded" />
                    <div className="h-3 w-20 bg-neutral-50 rounded" />
                  </div>
                ))}
              </div>
            )}

            {!loadingQuestions && questionsError && (
              <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
                <p className="text-red-600 text-sm">{questionsError}</p>
                <button
                  type="button"
                  onClick={() => setFetchTrigger((n) => n + 1)}
                  className="px-5 py-2.5 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 transition-colors"
                >
                  Retry
                </button>
              </div>
            )}

            {!loadingQuestions && !questionsError && pastQuestions.length === 0 && (
              <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
                <p className="text-neutral-400 text-sm">No questions yet. Head to the map to ask your first one.</p>
                <Link
                  href="/map"
                  className="px-5 py-2.5 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 transition-colors"
                >
                  Go to Map
                </Link>
              </div>
            )}

            {!loadingQuestions && !questionsError && pastQuestions.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {pastQuestions.map((q) => {
                  const total = q.yes_count + q.no_count
                  const yesPct = total > 0 ? Math.round((q.yes_count / total) * 100) : null
                  return (
                    <button
                      key={q.id}
                      onClick={() => {
                        setHasStarted(true)
                        const hasVotes = (q.yes_count + q.no_count) > 0
                        if (hasVotes) {
                          orch.loadHistorical(q.id)
                        } else {
                          orch.start(q.question_text, q.location)
                        }
                      }}
                      className="text-left rounded-lg border border-neutral-200 p-4 hover:border-neutral-400 hover:shadow-sm transition-all group"
                    >
                      <div className="text-xs font-medium text-neutral-500 group-hover:text-neutral-700 transition-colors">
                        {q.location}
                      </div>
                      <p className="mt-1 text-sm text-neutral-900 line-clamp-2">
                        {q.question_text}
                      </p>
                      <div className="mt-3 flex items-center gap-2 text-xs text-neutral-400">
                        {yesPct != null ? (
                          <>
                            <span className="text-emerald-600">Yes {yesPct}%</span>
                            <span>·</span>
                            <span>{total} votes</span>
                          </>
                        ) : (
                          <span>No votes yet</span>
                        )}
                        <span>·</span>
                        <span>{new Date(q.created_at).toLocaleDateString()}</span>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
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
                  onAgentClick={(agentId) => setSelectedAgentId(agentId)}
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

      {selectedAgentId && (
        <AgentReasoningDrawer
          agentId={selectedAgentId}
          trades={orch.trades}
          onClose={() => setSelectedAgentId(null)}
        />
      )}
    </div>
  )
}
