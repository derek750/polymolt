from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class StakeholderPerspectiveIn(BaseModel):
    """Request model for a single stakeholder AI perspective."""

    stakeholder_id: str = Field(..., description="Stable identifier for the stakeholder.")
    stakeholder_role: str = Field(..., description="Human-readable stakeholder role/title.")
    ai_agent_id: str = Field(..., description="ID of the AI agent that took this stakeholder's role.")
    answer: Literal["yes", "no"] = Field(..., description="Binary answer from this stakeholder AI.")
    confidence: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Optional confidence score in [0,1].",
    )
    reasoning: str | None = Field(
        None,
        description="Optional free-text explanation from the AI.",
    )
    # Optional: arbitrary additional payload from your pipeline (e.g. full model output)
    raw_payload: dict[str, Any] | None = Field(
        None,
        description="Optional raw model payload or extra fields.",
    )


class SaveQuestionRequest(BaseModel):
    """
    Persist a single user question and all stakeholder AI perspectives for that question.

    This is intended to be called once per question after your pipeline
    has:
      1. Assigned a location
      2. Generated all stakeholder AI yes/no answers
    """

    question: str = Field(..., description="The user's question in natural language.")
    location: str = Field(..., description="Location assigned to this question.")
    stakeholders: list[StakeholderPerspectiveIn] = Field(
        ...,
        description="All stakeholder AI perspectives for this question.",
        min_items=1,
    )


class SaveQuestionResponse(BaseModel):
    question_id: int


class QuestionSummaryOut(BaseModel):
    id: int
    question_text: str
    location: str
    created_at: str
    yes_count: int
    no_count: int


class QuestionListResponse(BaseModel):
    questions: list[QuestionSummaryOut]


class StakeholderResponseOut(BaseModel):
    id: int
    question_id: int
    phase: str = "legacy"
    stakeholder_id: str
    stakeholder_role: str
    ai_agent_id: str
    answer: str
    confidence: float | None = None
    reasoning: str | None = None
    created_at: str


class QuestionDetailResponse(BaseModel):
    question: QuestionSummaryOut
    responses: list[StakeholderResponseOut]


class OrchestrateRunOut(BaseModel):
    """Full orchestrate run for a question (from orchestrate_runs + full_response JSON)."""

    question_id: int
    topic_reasoning: str = ""
    deep_analysis: str = ""
    assigned_agent_id: str | None = None
    expertise_rationale: str | None = None
    rag_context: str | None = None
    full_response: dict[str, Any] | None = None
    created_at: str = ""


class CreateQuestionOnlyRequest(BaseModel):
    question: str
    location: str

