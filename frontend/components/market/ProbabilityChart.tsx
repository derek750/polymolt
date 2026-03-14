"use client"

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"
import { TradeEntry } from "@/types/trade"

interface DataPoint {
  index: number
  probability: number
  agentName?: string
  direction?: "BUY" | "SELL" | "YES" | "NO"
}

interface Props {
  priceHistory: number[]
  trades?: TradeEntry[]
  maxPoints?: number // 0 or undefined = show all
}

function formatPct(v: number) {
  return `${Math.round(v * 100)}%`
}

interface TooltipProps {
  active?: boolean
  payload?: Array<{ value: number; payload: DataPoint }>
}

function ChartTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={{
      backgroundColor: "#fff",
      border: "1px solid #e5e7eb",
      borderRadius: 4,
      padding: "6px 10px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
    }}>
      {d.agentName && (
        <div style={{ color: "#6b7280", fontSize: 11, marginBottom: 2 }}>
          {(d.direction === "BUY" || d.direction === "YES") ? "YES" : "NO"} · {d.agentName}
        </div>
      )}
      <div style={{ color: "#171717", fontSize: 14, fontWeight: 600 }}>
        {formatPct(d.probability)}
      </div>
    </div>
  )
}

export function ProbabilityChart({ priceHistory, trades, maxPoints }: Props) {
  const allData: DataPoint[] = trades && trades.length > 0
    ? [...trades].reverse().map((t, i) => ({
        index: i,
        probability: t.priceAfter,
        agentName: t.agentName,
        direction: t.direction,
      }))
    : priceHistory.map((p, i) => ({ index: i, probability: p }))

  // Sliding window: show last N points, or all if maxPoints is 0/undefined
  const data = maxPoints && allData.length > maxPoints
    ? allData.slice(allData.length - maxPoints)
    : allData

  if (data.length < 2) {
    return (
      <div className="flex items-center justify-center h-full text-neutral-400 text-sm">
        Waiting for trades…
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#171717" stopOpacity={0.08} />
            <stop offset="100%" stopColor="#171717" stopOpacity={0.01} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="index"
          tick={false}
          axisLine={{ stroke: "#e5e7eb" }}
          tickLine={false}
        />
        <YAxis
          domain={[0, 1]}
          tickFormatter={formatPct}
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={36}
          ticks={[0, 0.25, 0.5, 0.75, 1]}
        />
        <Tooltip content={<ChartTooltip />} />
        <ReferenceLine
          y={0.5}
          stroke="#e5e7eb"
          strokeDasharray="4 4"
        />
        <Area
          type="monotone"
          dataKey="probability"
          stroke="#171717"
          strokeWidth={1.5}
          fill="url(#areaFill)"
          dot={false}
          activeDot={{ r: 3, fill: "#171717", stroke: "#fff", strokeWidth: 2 }}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
