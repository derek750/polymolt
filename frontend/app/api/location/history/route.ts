import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const name = searchParams.get("name")
  if (!name) {
    return NextResponse.json(
      { error: "Missing name parameter" },
      { status: 400 }
    )
  }
  // Stub: return empty history. Wire to backend /db later if you have per-location history.
  return NextResponse.json({ history: [] })
}
