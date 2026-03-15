"use client"

import { useEffect, useMemo, useState } from "react"
import { QuestionDetail, QuestionSummary } from "@/types/question"
import { X, PlusCircle } from "lucide-react"
import { BACKEND_URL as API_BASE } from "@/lib/config"

interface Props {
  open: boolean
  onClose: () => void
}

export function QuestionMenu({ open, onClose }: Props) {
  const [questions, setQuestions] = useState<QuestionSummary[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<QuestionDetail | null>(null)
  const [loadingList, setLoadingList] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [newQuestionText, setNewQuestionText] = useState("")
  const [newLocation, setNewLocation] = useState("")
  const [creating, setCreating] = useState(false)

  // Temporary test states
  const [testResponse, setTestResponse] = useState<string | null>(null)
  const [testingRag, setTestingRag] = useState(false)

  const handleTestRag = async () => {
    if (!selectedQuestion) return
    setTestingRag(true)
    setTestResponse(null)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/ai/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: selectedQuestion.question_text,
          use_rag: true,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setTestResponse(data.response)
    } catch (e) {
      console.error("RAG test failed", e)
      setError("RAG test failed. Check backend console.")
    } finally {
      setTestingRag(false)
    }
  }

  // Fetch recent questions when drawer opens
  useEffect(() => {
    if (!open) return

    setLoadingList(true)
    setError(null)
    fetch(`${API_BASE}/db/questions`)
      .then((r) => r.json())
      .then((data) => {
        const list = (data.questions ?? []) as QuestionSummary[]
        setQuestions(list)
        if (list.length > 0) {
          setSelectedId((prev) => prev ?? list[0].id)
        }
      })
      .catch((e) => {
        console.error("Failed to load questions", e)
        setError("Failed to load questions")
      })
      .finally(() => setLoadingList(false))
  }, [open])

  // Fetch detail when selectedId changes
  useEffect(() => {
    setTestResponse(null)
    if (!open || selectedId == null) {
      setDetail(null)
      return
    }

    setLoadingDetail(true)
    setError(null)
    fetch(`${API_BASE}/db/questions/${selectedId}`)
      .then((r) => r.json())
      .then((data: QuestionDetail) => {
        setDetail(data)
      })
      .catch((e) => {
        console.error("Failed to load question detail", e)
        setError("Failed to load question details")
      })
      .finally(() => setLoadingDetail(false))
  }, [open, selectedId])

  const selectedQuestion = useMemo(
    () => questions.find((q) => q.id === selectedId) ?? null,
    [questions, selectedId],
  )

  const handleCreate = async () => {
    if (!newQuestionText.trim() || !newLocation.trim()) return
    setCreating(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/db/questions/basic`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: newQuestionText.trim(),
          location: newLocation.trim(),
        }),
      })
      if (!res.ok) {
        throw new Error(await res.text())
      }
      const data = (await res.json()) as { question_id: number }

      // Refresh list and select the new question
      const listRes = await fetch(`${API_BASE}/db/questions`)
      const listData = await listRes.json()
      const list = (listData.questions ?? []) as QuestionSummary[]
      setQuestions(list)
      setSelectedId(data.question_id)
      setNewQuestionText("")
      setNewLocation("")
    } catch (e) {
      console.error("Failed to create question", e)
      setError("Failed to create question")
    } finally {
      setCreating(false)
    }
  }

  if (!open) return null

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/20"
        onClick={onClose}
      />
      <div className="fixed inset-y-0 right-0 z-50 w-[420px] bg-white border-l border-neutral-200 shadow-lg flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
          <div className="flex flex-col">
            <span className="text-sm font-medium text-neutral-900">Questions</span>
            <span className="text-xs text-neutral-400">
              Browse saved questions & stakeholder runs
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* New question form */}
        <div className="px-4 py-3 border-b border-neutral-200 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium text-neutral-600 uppercase tracking-wide">
              New question
            </span>
            <button
              onClick={handleCreate}
              disabled={creating || !newQuestionText.trim() || !newLocation.trim()}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded border border-neutral-200 text-neutral-600 hover:border-neutral-400 hover:text-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <PlusCircle className="w-3 h-3" />
              <span>Create</span>
            </button>
          </div>
          <div className="space-y-1.5">
            <input
              type="text"
              placeholder="Location (e.g. California)"
              value={newLocation}
              onChange={(e) => setNewLocation(e.target.value)}
              className="w-full px-2 py-1.5 text-xs border border-neutral-200 rounded focus:outline-none focus:border-neutral-400 text-neutral-800 placeholder:text-neutral-300"
            />
            <textarea
              rows={2}
              placeholder="Ask a sustainability question…"
              value={newQuestionText}
              onChange={(e) => setNewQuestionText(e.target.value)}
              className="w-full px-2 py-1.5 text-xs border border-neutral-200 rounded focus:outline-none focus:border-neutral-400 text-neutral-800 placeholder:text-neutral-300 resize-none"
            />
          </div>
          <p className="text-[11px] text-neutral-400">
            Creating a question stores it in Supabase. Your stakeholder AI pipeline can attach
            yes/no perspectives to this question later.
          </p>
        </div>

        {/* Body: list + details */}
        <div className="flex-1 flex overflow-hidden">
          {/* Question list */}
          <div className="w-48 border-r border-neutral-200 flex flex-col">
            <div className="px-3 py-2 border-b border-neutral-100 flex items-center justify-between">
              <span className="text-[11px] font-medium text-neutral-500 uppercase tracking-wide">
                History
              </span>
              {loadingList && (
                <span className="text-[11px] text-neutral-400">Loading…</span>
              )}
            </div>
            <div className="flex-1 overflow-y-auto">
              {questions.length === 0 && !loadingList ? (
                <div className="px-3 py-4 text-[11px] text-neutral-400">
                  No questions yet. Create one above.
                </div>
              ) : (
                questions.map((q) => {
                  const isActive = q.id === selectedId
                  const total = q.yes_count + q.no_count
                  const yesPct = total > 0 ? Math.round((q.yes_count / total) * 100) : null
                  return (
                    <button
                      key={q.id}
                      onClick={() => setSelectedId(q.id)}
                      className={`w-full text-left px-3 py-2 border-b border-neutral-100 text-[11px] ${
                        isActive
                          ? "bg-neutral-900 text-white"
                          : "bg-white text-neutral-700 hover:bg-neutral-50"
                      }`}
                    >
                      <div className="truncate">{q.location}</div>
                      <div className={isActive ? "text-[10px] text-neutral-200" : "text-[10px] text-neutral-400"}>
                        {q.question_text}
                      </div>
                      {yesPct != null && (
                        <div className="mt-1 flex items-center gap-1 text-[10px]">
                          <span className={isActive ? "text-emerald-200" : "text-emerald-600"}>
                            Yes {yesPct}%
                          </span>
                          <span className={isActive ? "text-neutral-300" : "text-neutral-400"}>·</span>
                          <span className={isActive ? "text-neutral-200" : "text-neutral-400"}>
                            {total} votes
                          </span>
                        </div>
                      )}
                    </button>
                  )
                })
              )}
            </div>
          </div>

          {/* Detail panel */}
          <div className="flex-1 flex flex-col">
            {error && (
              <div className="px-4 py-2 text-xs text-red-500 border-b border-neutral-200 bg-red-50">
                {error}
              </div>
            )}

            {loadingDetail && (
              <div className="p-4 space-y-3">
                <div className="h-4 w-40 rounded bg-neutral-100 animate-pulse" />
                <div className="h-3 w-64 rounded bg-neutral-100 animate-pulse" />
                <div className="h-24 w-full rounded bg-neutral-50 animate-pulse" />
              </div>
            )}

            {!loadingDetail && selectedQuestion && detail && (
              <div className="p-4 flex-1 flex flex-col gap-3">
                <div className="space-y-1">
                  <div className="text-xs font-medium text-neutral-900">
                    {selectedQuestion.location}
                  </div>
                  <div className="text-xs text-neutral-600">
                    {selectedQuestion.question_text}
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-neutral-400">
                    <span>{new Date(selectedQuestion.created_at).toLocaleString()}</span>
                    <span>·</span>
                    <span>
                      {selectedQuestion.yes_count} yes / {selectedQuestion.no_count} no
                    </span>
                  </div>
                </div>

                {/* TEMPORARY RAG TEST BUTTON */}
                <div className="bg-neutral-50 border border-neutral-200 rounded p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-neutral-500 uppercase">RAG Lab (Temporary)</span>
                    <button
                      onClick={handleTestRag}
                      disabled={testingRag}
                      className="px-2 py-1 bg-neutral-900 text-white text-[10px] rounded hover:bg-neutral-800 disabled:opacity-50 transition-colors"
                    >
                      {testingRag ? "Running..." : "Run RAG Test"}
                    </button>
                  </div>
                  {testResponse && (
                    <div className="text-[11px] text-neutral-700 bg-white border border-neutral-100 p-2 rounded max-h-40 overflow-y-auto whitespace-pre-wrap">
                      {testResponse}
                    </div>
                  )}
                </div>

                <div className="border-t border-neutral-100 pt-2 flex-1 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium text-neutral-500 uppercase tracking-wide">
                      Stakeholder perspectives
                    </span>
                    <span className="text-[11px] text-neutral-400">
                      {detail.responses.length} agents
                    </span>
                  </div>

                  {detail.responses.length === 0 ? (
                    <div className="text-[11px] text-neutral-400">
                      No stakeholder responses stored yet. Your AI pipeline can attach them to this
                      question in the database.
                    </div>
                  ) : (
                    <div className="flex-1 overflow-y-auto space-y-2">
                      {detail.responses.map((r) => (
                        <div
                          key={r.id}
                          className="border border-neutral-200 rounded-md px-2.5 py-2 bg-white"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex flex-col">
                              <span className="text-[11px] font-medium text-neutral-800">
                                {r.stakeholder_role}
                              </span>
                              <span className="text-[10px] text-neutral-400">
                                Agent {r.ai_agent_id} · {r.stakeholder_id}
                              </span>
                            </div>
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                                r.answer.toUpperCase() === "YES"
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                  : "bg-red-50 text-red-600 border-red-200"
                              }`}
                            >
                              {r.answer.toUpperCase()}
                            </span>
                          </div>
                          {r.reasoning && (
                            <p className="mt-1.5 text-[11px] text-neutral-600">
                              {r.reasoning}
                            </p>
                          )}
                          <div className="mt-1 flex items-center justify-between text-[10px] text-neutral-400">
                            <span>
                              {r.confidence != null
                                ? `Confidence ${(r.confidence * 100).toFixed(0)}%`
                                : "Confidence n/a"}
                            </span>
                            <span>{new Date(r.created_at).toLocaleString()}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {!loadingDetail && !selectedQuestion && (
              <div className="p-4 text-xs text-neutral-400">
                Select a question on the left to see details.
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

