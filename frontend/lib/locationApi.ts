import type { HistoryItem } from "@/types/map"

const API_BASE = "/api"

export interface AskLocationBody {
  locationName: string
  locationType: string
  coordinates: [number, number]
  question: string
}

export interface AskLocationResponse {
  answer?: string
  error?: string
}

export async function askLocation(body: AskLocationBody): Promise<AskLocationResponse> {
  const res = await fetch(`${API_BASE}/location/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.message ?? err?.error ?? `Request failed: ${res.status}`)
  }
  return res.json()
}

export interface HistoryResponse {
  history?: HistoryItem[]
  error?: string
}

export async function getLocationHistory(locationName: string): Promise<HistoryItem[]> {
  const res = await fetch(
    `${API_BASE}/location/history?name=${encodeURIComponent(locationName)}`
  )
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.message ?? err?.error ?? `Request failed: ${res.status}`)
  }
  const data: HistoryResponse = await res.json()
  return data.history ?? []
}
