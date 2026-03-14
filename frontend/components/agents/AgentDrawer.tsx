"use client"

import { Agent } from "@/types/agent"
import { EvidenceItem } from "@/types/evidence"
import { CATEGORY_LABELS } from "@/lib/constants"
import { X } from "lucide-react"

interface Props {
  agent: Agent | null
  marketPrice?: number
  onClose: () => void
}

function TraitBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100)
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-neutral-500 w-28 flex-shrink-0">{label}</span>
      <div className="flex-1 bg-neutral-100 rounded-full h-1.5">
        <div
          className="h-1.5 rounded-full bg-neutral-900 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-neutral-400 w-8 text-right tabular-nums">{pct}%</span>
    </div>
  )
}

function EvidenceCard({ item }: { item: EvidenceItem }) {
  const sentimentLabel =
    item.sentiment === "positive" ? "Positive" :
    item.sentiment === "negative" ? "Negative" : "Mixed"

  return (
    <div className="border border-neutral-200 rounded p-2.5">
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="text-xs font-medium text-neutral-900 leading-snug">{item.title}</span>
        <span className="text-xs text-neutral-400 flex-shrink-0">{Math.round(item.strength * 100)}%</span>
      </div>
      <p className="text-xs text-neutral-500 leading-relaxed">{item.summary}</p>
      <div className="flex items-center gap-2 mt-1.5 text-xs text-neutral-400">
        <span>{CATEGORY_LABELS[item.category] ?? item.category}</span>
        <span>·</span>
        <span>{sentimentLabel}</span>
      </div>
    </div>
  )
}

function BeliefSparkline({ history }: { history: number[] }) {
  if (history.length < 2) return null
  const W = 200
  const H = 32
  const pts = history
    .map((v, i) => {
      const x = (i / (history.length - 1)) * W
      const y = H - v * H
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(" ")

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} className="overflow-visible">
      <line x1={0} y1={H / 2} x2={W} y2={H / 2} stroke="#e5e7eb" strokeWidth={1} strokeDasharray="3 3" />
      <polyline points={pts} fill="none" stroke="#171717" strokeWidth={1.5} strokeLinejoin="round" />
      <circle cx={W} cy={H - history[history.length - 1] * H} r={2.5} fill="#171717" />
    </svg>
  )
}

export function AgentDrawer({ agent, marketPrice, onClose }: Props) {
  if (!agent) return null

  const beliefPct = Math.round(agent.currentBelief * 100)
  const typeLabel =
    agent.agentType === "master" ? "Master" :
    agent.agentType === "hybrid" ? "Hybrid" : "Specialist"

  return (
    <div className="animate-slide-in-right fixed inset-y-0 right-0 z-50 w-[400px] bg-white border-l border-neutral-200 overflow-y-auto shadow-lg">
      {/* Header */}
      <div className="sticky top-0 bg-white px-5 py-4 border-b border-neutral-200 flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-base font-bold text-neutral-900">{agent.name}</span>
            <span className="text-xs text-neutral-400">{typeLabel}</span>
          </div>
          <div className="flex items-center gap-3 text-xs text-neutral-400">
            <span>Power: <span className="text-neutral-700">{agent.bettingPower}x</span></span>
            <span>·</span>
            <span>Position: <span className={agent.currentPosition >= 0 ? "text-neutral-700" : "text-neutral-700"}>
              {agent.currentPosition >= 0 ? "+" : ""}{agent.currentPosition.toFixed(1)}
            </span></span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-neutral-400 hover:text-neutral-600 transition-colors mt-0.5"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="px-5 py-4 space-y-5">
        {/* Belief vs Market */}
        <section>
          <h3 className="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-2">Current Belief</h3>
          <div className="flex items-center gap-3">
            <div className="flex flex-col items-center px-4 py-2.5 border border-neutral-200 rounded">
              <span className="text-xs text-neutral-400 mb-0.5">Estimate</span>
              <span className="text-2xl font-bold text-neutral-900">{beliefPct}%</span>
            </div>
            <span className="text-neutral-300 text-sm">vs</span>
            <div className="flex flex-col items-center px-4 py-2.5 border border-neutral-200 rounded">
              <span className="text-xs text-neutral-400 mb-0.5">Market</span>
              <span className="text-2xl font-bold text-neutral-500">
                {marketPrice !== undefined ? `${Math.round(marketPrice * 100)}%` : "—"}
              </span>
            </div>
            {marketPrice !== undefined && (
              <div className="flex flex-col items-center px-3 py-2.5">
                <span className="text-xs text-neutral-400 mb-0.5">Gap</span>
                <span className="text-lg font-semibold text-neutral-700">
                  {((agent.currentBelief - marketPrice) * 100).toFixed(1)}pp
                </span>
              </div>
            )}
          </div>
        </section>

        {/* Belief Sparkline */}
        {agent.beliefHistory && agent.beliefHistory.length > 2 && (
          <section>
            <h3 className="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-2">
              Belief History ({agent.beliefHistory.length})
            </h3>
            <div className="border border-neutral-200 rounded px-3 py-2">
              <BeliefSparkline history={agent.beliefHistory} />
              <div className="flex justify-between mt-1 text-xs text-neutral-300">
                <span>earliest</span>
                <span>latest</span>
              </div>
            </div>
          </section>
        )}

        {/* Categories */}
        <section>
          <h3 className="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-2">Knowledge Access</h3>
          <div className="flex flex-wrap gap-1.5">
            {agent.categories.map((cat) => (
              <span key={cat} className="text-xs text-neutral-600 bg-neutral-100 border border-neutral-200 rounded px-2 py-0.5">
                {CATEGORY_LABELS[cat] ?? cat}
              </span>
            ))}
          </div>
        </section>

        {/* Behavior Traits */}
        <section>
          <h3 className="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-3">Behavior Traits</h3>
          <div className="space-y-2">
            <TraitBar label="Confidence" value={agent.confidence} />
            <TraitBar label="Risk Tolerance" value={agent.riskTolerance} />
            <TraitBar label="Stubbornness" value={agent.stubbornness} />
            <TraitBar label="Herd Sensitivity" value={agent.herdSensitivity} />
            <TraitBar label="Update Frequency" value={agent.updateFrequency} />
          </div>
          {agent.contrarian && (
            <div className="mt-2 text-xs text-neutral-600 border border-neutral-200 rounded px-2 py-1">
              ↺ Contrarian — trades against consensus
            </div>
          )}
        </section>

        {/* Latest Reasoning */}
        {agent.lastReasoning && (
          <section>
            <h3 className="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-2">Latest Reasoning</h3>
            <p className="text-sm text-neutral-700 leading-relaxed border border-neutral-200 rounded p-3">
              {agent.lastReasoning}
            </p>
          </section>
        )}

        {/* Evidence Used */}
        {agent.evidenceUsed && agent.evidenceUsed.length > 0 && (
          <section>
            <h3 className="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-2">
              Evidence ({agent.evidenceUsed.length})
            </h3>
            <div className="space-y-2">
              {agent.evidenceUsed.slice(0, 5).map((item) => (
                <EvidenceCard key={item.id} item={item} />
              ))}
            </div>
          </section>
        )}

        {/* Trade History */}
        {agent.tradeHistory && agent.tradeHistory.length > 0 && (
          <section>
            <h3 className="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-2">Recent Trades</h3>
            <div className="space-y-1">
              {agent.tradeHistory.slice(0, 5).map((trade, i) => (
                <div key={i} className="flex items-center justify-between text-xs px-2.5 py-2 border border-neutral-200 rounded">
                  <div className="flex items-center gap-2">
                    <span className={(trade.direction === "BUY" || trade.direction === "YES") ? "font-medium text-green-600" : "font-medium text-red-600"}>
                      {(trade.direction === "BUY" || trade.direction === "YES") ? "YES" : "NO"}
                    </span>
                    <span className="text-neutral-400">{trade.size?.toFixed(1)}u</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-neutral-500">
                    <span>{((trade.priceBefore ?? 0) * 100).toFixed(1)}%</span>
                    <span>→</span>
                    <span className="text-neutral-900">
                      {((trade.priceAfter ?? 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
