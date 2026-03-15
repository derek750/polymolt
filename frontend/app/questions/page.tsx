"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { BACKEND_URL as BACKEND } from "@/lib/config"

interface QuestionSummary {
  id: number
  question_text: string
  location: string
  created_at: string
  yes_count: number
  no_count: number
}

interface StakeholderResponse {
  id: number
  question_id: number
  phase: string
  stakeholder_id: string
  stakeholder_role: string
  ai_agent_id: string
  answer: string
  confidence: number | null
  reasoning: string | null
  created_at: string
}

interface QuestionDetail {
  question: QuestionSummary
  responses: StakeholderResponse[]
}

export default function QuestionsPage() {
  const [questions, setQuestions] = useState<QuestionSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    fetch(`${BACKEND}/db/questions?limit=50`)
      .then((res) => {
        if (!res.ok) throw new Error(`Backend returned ${res.status}`)
        return res.json()
      })
      .then((data) => {
        setQuestions(data.questions || [])
        setLoading(false)
      })
      .catch((e) => {
        setError(e.message)
        setLoading(false)
      })
  }, [])

  const handleQuestionClick = async (q: QuestionSummary) => {
    setDetailLoading(true)
    try {
      const res = await fetch(`${BACKEND}/db/questions/${q.id}`)
      if (!res.ok) throw new Error(`Backend returned ${res.status}`)
      const data: QuestionDetail = await res.json()
      setSelectedQuestion(data)
    } catch (e) {
      console.error("Failed to load question detail:", e)
    } finally {
      setDetailLoading(false)
    }
  }

  const yesPercent = selectedQuestion
    ? Math.round(
        (selectedQuestion.question.yes_count /
          Math.max(1, selectedQuestion.question.yes_count + selectedQuestion.question.no_count)) *
          100
      )
    : 0

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <header className="sticky top-0 z-50 flex items-center justify-between px-6 py-3 bg-white border-b border-neutral-200">
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="font-bold text-neutral-900 text-lg tracking-tight hover:opacity-70 transition-opacity">
            polymolt
          </Link>
          <nav className="flex items-center gap-1 ml-2">
            <Link href="/dashboard" className="px-3 py-1.5 text-xs text-neutral-500 rounded hover:text-neutral-700 transition-colors">
              Dashboard
            </Link>
            <Link href="/agents" className="px-3 py-1.5 text-xs text-neutral-500 rounded hover:text-neutral-700 transition-colors">
              Agents
            </Link>
            <Link href="/map" className="px-3 py-1.5 text-xs text-neutral-500 rounded hover:text-neutral-700 transition-colors">
              Map
            </Link>
            <Link href="/questions" className="px-3 py-1.5 text-xs text-neutral-900 bg-neutral-100 rounded font-medium">
              Questions
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 flex flex-col lg:flex-row gap-0 max-w-[1400px] mx-auto w-full">
        {/* Left: Questions List */}
        <div className="w-full lg:w-[400px] border-r border-neutral-200 flex flex-col">
          <div className="p-4 border-b border-neutral-100">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-lg font-bold text-neutral-900">Questions</h1>
                <p className="text-xs text-neutral-500 mt-0.5">
                  {questions.length} saved
                </p>
              </div>
              <Link
                href="/map"
                className="px-3 py-1.5 rounded border text-xs transition-colors bg-neutral-900 text-white hover:bg-neutral-800"
              >
                + New
              </Link>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {loading && (
              <div className="flex items-center justify-center py-20">
                <p className="text-neutral-500 text-sm">Loading...</p>
              </div>
            )}

            {error && (
              <div className="p-4">
                <p className="text-red-600 text-sm">Error: {error}</p>
              </div>
            )}

            {!loading && !error && questions.length === 0 && (
              <div className="flex flex-col items-center justify-center gap-4 py-20 px-4">
                <p className="text-neutral-500 text-sm text-center">No questions saved yet.</p>
                <Link
                  href="/map"
                  className="px-5 py-2.5 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 transition-colors"
                >
                  Ask Your First Question
                </Link>
              </div>
            )}

            {!loading && !error && questions.length > 0 && (
              <div className="divide-y divide-neutral-100">
                {questions.map((q) => {
                  const isSelected = selectedQuestion?.question.id === q.id
                  const total = q.yes_count + q.no_count
                  const yesPct = total > 0 ? Math.round((q.yes_count / total) * 100) : 50
                  return (
                    <button
                      key={q.id}
                      onClick={() => handleQuestionClick(q)}
                      className={`w-full text-left p-4 transition-all hover:bg-neutral-50 ${
                        isSelected ? "bg-neutral-50 border-l-2 border-l-neutral-900" : ""
                      }`}
                    >
                      <p className="text-sm font-medium text-neutral-900 mb-1 line-clamp-2">
                        {q.question_text}
                      </p>
                      <p className="text-xs text-neutral-400 mb-2">{q.location}</p>
                      <div className="flex items-center gap-3">
                        <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-green-500 rounded-full"
                            style={{ width: `${yesPct}%` }}
                          />
                        </div>
                        <span className="text-xs text-neutral-500 whitespace-nowrap">
                          {q.yes_count}Y / {q.no_count}N
                        </span>
                      </div>
                      <p className="text-[10px] text-neutral-400 mt-1.5">
                        {new Date(q.created_at).toLocaleString()}
                      </p>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right: Question Detail */}
        <div className="flex-1 p-6 overflow-y-auto">
          {!selectedQuestion && !detailLoading && (
            <div className="flex flex-col items-center justify-center h-full text-neutral-400 gap-2">
              <p className="text-sm">Select a question to view betting outcomes</p>
            </div>
          )}

          {detailLoading && (
            <div className="flex items-center justify-center h-full">
              <p className="text-sm text-neutral-500">Loading details...</p>
            </div>
          )}

          {selectedQuestion && !detailLoading && (
            <div className="space-y-6">
              {/* Question Header */}
              <div>
                <h2 className="text-xl font-bold text-neutral-900 mb-1">
                  {selectedQuestion.question.question_text}
                </h2>
                <p className="text-sm text-neutral-500">{selectedQuestion.question.location}</p>
                <p className="text-xs text-neutral-400 mt-1">
                  {new Date(selectedQuestion.question.created_at).toLocaleString()}
                </p>
              </div>

              {/* Outcome Summary */}
              <div className="flex gap-4">
                <div className="flex-1 p-4 rounded-lg bg-green-50 border border-green-200">
                  <p className="text-2xl font-bold text-green-700">{selectedQuestion.question.yes_count}</p>
                  <p className="text-xs text-green-600 font-medium">YES votes</p>
                  <p className="text-xs text-green-500 mt-0.5">{yesPercent}%</p>
                </div>
                <div className="flex-1 p-4 rounded-lg bg-red-50 border border-red-200">
                  <p className="text-2xl font-bold text-red-700">{selectedQuestion.question.no_count}</p>
                  <p className="text-xs text-red-600 font-medium">NO votes</p>
                  <p className="text-xs text-red-500 mt-0.5">{100 - yesPercent}%</p>
                </div>
              </div>

              {/* Market Bar */}
              <div>
                <div className="flex justify-between text-xs text-neutral-500 mb-1">
                  <span>YES</span>
                  <span>NO</span>
                </div>
                <div className="h-3 bg-red-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500 rounded-full transition-all"
                    style={{ width: `${yesPercent}%` }}
                  />
                </div>
              </div>

              {/* Agent Responses */}
              <div>
                <h3 className="text-sm font-semibold text-neutral-900 mb-3">
                  Agent Responses ({selectedQuestion.responses.length})
                </h3>
                <div className="space-y-3">
                  {selectedQuestion.responses.map((r) => (
                    <div
                      key={r.id}
                      className={`p-4 rounded-lg border ${
                        r.answer.toUpperCase() === "YES"
                          ? "border-green-200 bg-green-50/50"
                          : "border-red-200 bg-red-50/50"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-neutral-900">
                            {r.stakeholder_role}
                          </span>
                          <span className="text-[10px] text-neutral-400">
                            ({r.ai_agent_id})
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {r.confidence != null && (
                            <span className="text-xs text-neutral-500">
                              {(r.confidence * 100).toFixed(0)}% conf
                            </span>
                          )}
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-bold ${
                              r.answer.toUpperCase() === "YES"
                                ? "bg-green-100 text-green-700"
                                : "bg-red-100 text-red-700"
                            }`}
                          >
                            {r.answer.toUpperCase()}
                          </span>
                        </div>
                      </div>
                      {r.reasoning && (
                        <p className="text-xs text-neutral-600 leading-relaxed">
                          {r.reasoning}
                        </p>
                      )}
                      {r.phase !== "legacy" && (
                        <p className="text-[10px] text-neutral-400 mt-1">Phase: {r.phase}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
