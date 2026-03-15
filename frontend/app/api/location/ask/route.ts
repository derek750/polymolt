import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = (process.env.BACKEND_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "")

async function fetchBackend(
  path: string,
  body: Record<string, unknown>
): Promise<Response> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 60000)
  try {
    return await fetch(`${BACKEND_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    })
  } finally {
    clearTimeout(timeout)
  }
}

function parseErrorBody(text: string): string {
  try {
    const parsed = JSON.parse(text) as { detail?: string; message?: string; error?: string }
    return parsed.detail ?? parsed.message ?? parsed.error ?? text
  } catch {
    return text || "Unknown error"
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { question, locationName } = body as {
      question?: string
      locationName?: string
      locationType?: string
      coordinates?: [number, number]
    }
    const questionText =
      typeof question === "string" && question.trim()
        ? question.trim()
        : "Is this location a good place to visit?"
    const fullQuestion = locationName
      ? `About ${locationName}: ${questionText}`
      : questionText

    let res: Response
    try {
      res = await fetchBackend("/ai/orchestrate", { question: fullQuestion, use_rag: true })
    } catch (e) {
      const isNetwork =
        e instanceof TypeError && (e.message === "fetch failed" || e.message.includes("ECONNREFUSED"))
      const msg = isNetwork
        ? `Backend not reachable at ${BACKEND_URL}. Start the backend with: cd polymolt/backend && python3 -m uvicorn main:app --reload --port 8000`
        : e instanceof Error ? e.message : "Request failed"
      return NextResponse.json({ error: msg }, { status: 502 })
    }

    if (res.status === 404) {
      try {
        res = await fetchBackend("/ai/run", { message: fullQuestion, use_rag: true })
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Request failed"
        return NextResponse.json({ error: msg }, { status: 502 })
      }
    }

    if (!res.ok) {
      const errBody = await res.text()
      const errMessage = parseErrorBody(errBody) || `Backend returned ${res.status}`
      return NextResponse.json({ error: errMessage }, { status: 502 })
    }

    const data = (await res.json()) as {
      deep_analysis?: string
      topic_reasoning?: string
      response?: string
    }
    const answer =
      data.deep_analysis ??
      data.topic_reasoning ??
      data.response ??
      "No analysis available."
    return NextResponse.json({ answer })
  } catch (e) {
    const message = e instanceof Error ? e.message : "Request failed"
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
