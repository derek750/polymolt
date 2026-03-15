"""
Supabase (PostgreSQL) helpers for saving question runs and stakeholder AI perspectives.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Literal

logger = logging.getLogger(__name__)

_supabase_client = None


def get_supabase():
    """Lazy-init the Supabase client (singleton)."""
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client

        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise RuntimeError(
                "Supabase not configured. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env"
            )
        _supabase_client = create_client(url, key)
    return _supabase_client


# ── Dataclasses (unchanged public API) ──────────────────────────────────


@dataclass
class StakeholderPerspective:
    """Single stakeholder AI response for a question."""

    stakeholder_id: str
    stakeholder_role: str
    ai_agent_id: str
    answer: Literal["yes", "no"]
    confidence: float | None = None
    reasoning: str | None = None
    location: str | None = None
    raw_payload: dict[str, Any] | None = None


@dataclass
class QuestionSummary:
    """Lightweight view of a question with simple yes/no counts."""

    id: int
    question_text: str
    location: str
    created_at: str
    yes_count: int
    no_count: int


@dataclass
class QuestionRow:
    """Full question row without aggregated counts."""

    id: int
    question_text: str
    location: str
    created_at: str


@dataclass
class StakeholderResponseRow:
    """Single stored stakeholder response row."""

    id: int
    question_id: int
    phase: str
    stakeholder_id: str
    stakeholder_role: str
    ai_agent_id: str
    answer: str
    confidence: float | None
    reasoning: str | None
    created_at: str


@dataclass
class OrchestrateRunRow:
    """One row from orchestrate_runs."""

    id: int
    question_id: int
    topic_reasoning: str
    deep_analysis: str
    assigned_agent_id: str | None
    expertise_rationale: str | None
    rag_context: str | None
    context_for_agents: str | None
    year: int | None
    model: str | None
    full_response: str | None
    created_at: str


# ── Internal helpers ────────────────────────────────────────────────────


def _insert_question(question: str, location: str) -> int:
    """Insert a question row and return its new ID."""
    sb = get_supabase()
    result = (
        sb.table("questions")
        .insert({"question_text": question, "location": location})
        .execute()
    )
    row = result.data[0]
    return int(row["id"])


def _insert_stakeholder_response(
    question_id: int,
    phase: str,
    stakeholder_id: str,
    stakeholder_role: str,
    ai_agent_id: str,
    answer: str,
    confidence: int | float | None,
    reasoning: str | None,
    raw_payload: dict[str, Any] | None,
) -> None:
    if reasoning and len(reasoning) > 32700:
        reasoning = reasoning[:32700]
    sb = get_supabase()
    sb.table("stakeholder_responses").insert({
        "question_id": question_id,
        "phase": phase[:50],
        "stakeholder_id": stakeholder_id[:100],
        "stakeholder_role": stakeholder_role[:255],
        "ai_agent_id": ai_agent_id[:100],
        "answer": answer[:3],
        "confidence": float(confidence) if confidence is not None else None,
        "reasoning": reasoning,
        "raw_payload": raw_payload,
    }).execute()


def _invalidate_db_cache() -> None:
    """Clear all DB read caches after a write operation."""
    from app.cache import cache_invalidate_namespace, NS_DB
    cache_invalidate_namespace(NS_DB)


# ── Public API ──────────────────────────────────────────────────────────


def save_question_with_perspectives(
    question: str,
    location: str,
    perspectives: list[StakeholderPerspective],
) -> int:
    """
    Persist a single user question and all stakeholder AI perspectives.

    Returns the created question_id.
    """
    question_id = _insert_question(question, location)

    if perspectives:
        sb = get_supabase()
        rows = []
        for p in perspectives:
            answer_normalized = p.answer.lower()
            if answer_normalized not in {"yes", "no"}:
                raise ValueError(f"Invalid answer value: {p.answer!r}")
            answer_db = "YES" if answer_normalized == "yes" else "NO"
            rows.append({
                "question_id": question_id,
                "phase": "legacy",
                "stakeholder_id": p.stakeholder_id,
                "stakeholder_role": p.stakeholder_role,
                "ai_agent_id": p.ai_agent_id,
                "answer": answer_db,
                "confidence": p.confidence,
                "reasoning": p.reasoning,
                "raw_payload": p.raw_payload,
            })
        sb.table("stakeholder_responses").insert(rows).execute()

    logger.info(
        "Saved question %s with %d stakeholder perspectives",
        question_id,
        len(perspectives),
    )
    _invalidate_db_cache()
    return question_id


def create_question_only(question: str, location: str) -> int:
    """
    Create a question row without any stakeholder responses.

    Useful for frontends that collect the question/location first and attach
    stakeholder AI runs later.
    """
    question_id = _insert_question(question, location)
    logger.info("Created question %s (no stakeholder responses yet)", question_id)
    _invalidate_db_cache()
    return question_id


def list_recent_questions(limit: int = 50) -> list[QuestionSummary]:
    """
    Return most recent questions with simple yes/no counts.  Cached in Redis.

    Uses the ``questions_with_counts`` database view.
    """
    from app.cache import cache_get, cache_set, NS_DB, TTL_DB_READ

    cache_key_parts = ("list_recent_questions", limit)
    cached = cache_get(NS_DB, *cache_key_parts)
    if cached is not None:
        return [QuestionSummary(**row) for row in cached]

    sb = get_supabase()
    result = (
        sb.table("questions_with_counts")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    results: list[QuestionSummary] = []
    for row in result.data:
        results.append(
            QuestionSummary(
                id=int(row["id"]),
                question_text=str(row["question_text"]),
                location=str(row["location"]),
                created_at=str(row["created_at"]),
                yes_count=int(row["yes_count"]),
                no_count=int(row["no_count"]),
            )
        )

    serializable = [
        {
            "id": r.id, "question_text": r.question_text, "location": r.location,
            "created_at": r.created_at, "yes_count": r.yes_count, "no_count": r.no_count,
        }
        for r in results
    ]
    cache_set(NS_DB, *cache_key_parts, value=serializable, ttl=TTL_DB_READ)
    return results


def get_question_with_responses(
    question_id: int,
) -> tuple[QuestionRow, list[StakeholderResponseRow]]:
    """
    Load a single question and all of its stakeholder responses.  Cached in Redis.
    """
    from app.cache import cache_get, cache_set, NS_DB, TTL_DB_READ

    cache_key_parts = ("get_question_with_responses", question_id)
    cached = cache_get(NS_DB, *cache_key_parts)
    if cached is not None:
        q_data, resp_data = cached["question"], cached["responses"]
        question_obj = QuestionRow(**q_data)
        responses = [StakeholderResponseRow(**r) for r in resp_data]
        return question_obj, responses

    sb = get_supabase()

    q_result = (
        sb.table("questions")
        .select("id, question_text, location, created_at")
        .eq("id", question_id)
        .execute()
    )
    if not q_result.data:
        raise ValueError(f"Question {question_id} not found.")

    q_row = q_result.data[0]
    question_obj = QuestionRow(
        id=int(q_row["id"]),
        question_text=str(q_row["question_text"]),
        location=str(q_row["location"]),
        created_at=str(q_row["created_at"]),
    )

    r_result = (
        sb.table("stakeholder_responses")
        .select("id, question_id, phase, stakeholder_id, stakeholder_role, "
                "ai_agent_id, answer, confidence, reasoning, created_at")
        .eq("question_id", question_id)
        .order("created_at")
        .order("id")
        .execute()
    )

    responses: list[StakeholderResponseRow] = []
    for r_row in r_result.data:
        confidence_val = r_row.get("confidence")
        responses.append(
            StakeholderResponseRow(
                id=int(r_row["id"]),
                question_id=int(r_row["question_id"]),
                phase=str(r_row.get("phase") or "legacy"),
                stakeholder_id=str(r_row["stakeholder_id"]),
                stakeholder_role=str(r_row["stakeholder_role"]),
                ai_agent_id=str(r_row["ai_agent_id"]),
                answer=str(r_row["answer"]),
                confidence=float(confidence_val) if confidence_val is not None else None,
                reasoning=str(r_row["reasoning"]) if r_row.get("reasoning") is not None else None,
                created_at=str(r_row["created_at"]),
            )
        )

    serializable = {
        "question": {
            "id": question_obj.id, "question_text": question_obj.question_text,
            "location": question_obj.location, "created_at": question_obj.created_at,
        },
        "responses": [
            {
                "id": r.id, "question_id": r.question_id, "phase": r.phase,
                "stakeholder_id": r.stakeholder_id, "stakeholder_role": r.stakeholder_role,
                "ai_agent_id": r.ai_agent_id, "answer": r.answer,
                "confidence": r.confidence, "reasoning": r.reasoning,
                "created_at": r.created_at,
            }
            for r in responses
        ],
    }
    cache_set(NS_DB, *cache_key_parts, value=serializable, ttl=TTL_DB_READ)
    return question_obj, responses


def save_orchestrate_response(
    question: str,
    location: str,
    response: dict[str, Any],
    year: int | None = None,
    model: str | None = None,
) -> int:
    """
    Save a full /ai/orchestrate response under one question.

    Creates:
    - one ``questions`` row (question_text, location)
    - one ``orchestrate_runs`` row (topic_reasoning, context_for_agents,
      year, model, full_response JSON, etc.)
    - ``stakeholder_responses`` rows:
        phase='initial_bet'  -- every agent's first bet
        phase='triggered'    -- orchestrator's agent selection metadata
        phase='second_bet'   -- triggered agents' second bet

    Returns the created question_id.
    """
    question_id = _insert_question(question, location)

    topic_reasoning = response.get("topic_reasoning") or ""
    deep_analysis = response.get("deep_analysis") or ""
    assigned_agent_id = response.get("assigned_agent_id") or ""
    expertise_rationale = response.get("expertise_rationale") or ""
    context_for_agents = response.get("context_for_agents") or ""

    sb = get_supabase()
    sb.table("orchestrate_runs").insert({
        "question_id": question_id,
        "topic_reasoning": topic_reasoning,
        "deep_analysis": deep_analysis,
        "assigned_agent_id": assigned_agent_id[:100] if assigned_agent_id else None,
        "expertise_rationale": expertise_rationale,
        "rag_context": context_for_agents,
        "context_for_agents": context_for_agents,
        "year": year,
        "model": (model or "")[:100] if model else None,
        "full_response": response,
    }).execute()

    # --- initial_bets -> phase='initial_bet' ---
    initial_bets = response.get("initial_bets") or []
    for bet in initial_bets:
        answer = (bet.get("answer") or "UNKNOWN").strip().upper()
        if answer not in ("YES", "NO"):
            answer = "NO"
        _insert_stakeholder_response(
            question_id,
            phase="initial_bet",
            stakeholder_id=bet.get("agent_id") or "",
            stakeholder_role=bet.get("agent_name") or "",
            ai_agent_id=bet.get("agent_id") or "",
            answer=answer,
            confidence=bet.get("confidence"),
            reasoning=(bet.get("reasoning") or "")[:32700],
            raw_payload=None,
        )

    # --- triggered_agents -> phase='triggered' (selection metadata only) ---
    triggered = response.get("triggered_agents") or []
    for t in triggered:
        answer = (t.get("answer") or "UNKNOWN").strip().upper()
        if answer not in ("YES", "NO"):
            answer = "NO"
        raw = {"choice_reasoning": t.get("choice_reasoning") or ""}
        _insert_stakeholder_response(
            question_id,
            phase="triggered",
            stakeholder_id=t.get("agent_id") or "",
            stakeholder_role=t.get("agent_name") or "",
            ai_agent_id=t.get("agent_id") or "",
            answer=answer,
            confidence=None,
            reasoning=None,
            raw_payload=raw,
        )

    # --- second_bets -> phase='second_bet' ---
    choice_reasoning_by_id = {
        t.get("agent_id"): t.get("choice_reasoning", "")
        for t in triggered
    }
    second_bets = response.get("second_bets") or []
    for sb_bet in second_bets:
        answer = (sb_bet.get("answer") or "UNKNOWN").strip().upper()
        if answer not in ("YES", "NO"):
            answer = "NO"
        aid = sb_bet.get("agent_id") or ""
        raw = {"choice_reasoning": choice_reasoning_by_id.get(aid, "")}
        _insert_stakeholder_response(
            question_id,
            phase="second_bet",
            stakeholder_id=aid,
            stakeholder_role=sb_bet.get("agent_name") or "",
            ai_agent_id=aid,
            answer=answer,
            confidence=sb_bet.get("confidence"),
            reasoning=(sb_bet.get("reasoning") or "")[:32700],
            raw_payload=raw,
        )

    logger.info(
        "Saved orchestrate response for question %s: %d initial_bets, %d triggered, %d second_bets",
        question_id,
        len(initial_bets),
        len(triggered),
        len(second_bets),
    )
    _invalidate_db_cache()
    return question_id


def get_orchestrate_run(question_id: int) -> OrchestrateRunRow | None:
    """Load the orchestrate run for a question, if any.  Cached in Redis."""
    from app.cache import cache_get, cache_set, NS_DB, TTL_DB_READ

    cache_key_parts = ("get_orchestrate_run", question_id)
    cached = cache_get(NS_DB, *cache_key_parts)
    if cached is not None:
        return OrchestrateRunRow(**cached) if cached != "__none__" else None

    sb = get_supabase()
    result = (
        sb.table("orchestrate_runs")
        .select("*")
        .eq("question_id", question_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        cache_set(NS_DB, *cache_key_parts, value="__none__", ttl=TTL_DB_READ)
        return None

    row = result.data[0]
    full_resp = row.get("full_response")
    if isinstance(full_resp, dict):
        full_resp_str = json.dumps(full_resp)
    elif full_resp is not None:
        full_resp_str = str(full_resp)
    else:
        full_resp_str = None

    run = OrchestrateRunRow(
        id=int(row["id"]),
        question_id=int(row["question_id"]),
        topic_reasoning=str(row.get("topic_reasoning") or ""),
        deep_analysis=str(row.get("deep_analysis") or ""),
        assigned_agent_id=str(row["assigned_agent_id"]) if row.get("assigned_agent_id") else None,
        expertise_rationale=str(row["expertise_rationale"]) if row.get("expertise_rationale") else None,
        rag_context=str(row["rag_context"]) if row.get("rag_context") else None,
        context_for_agents=str(row["context_for_agents"]) if row.get("context_for_agents") else None,
        year=int(row["year"]) if row.get("year") is not None else None,
        model=str(row["model"]) if row.get("model") else None,
        full_response=full_resp_str,
        created_at=str(row["created_at"]),
    )

    serializable = {
        "id": run.id, "question_id": run.question_id,
        "topic_reasoning": run.topic_reasoning, "deep_analysis": run.deep_analysis,
        "assigned_agent_id": run.assigned_agent_id, "expertise_rationale": run.expertise_rationale,
        "rag_context": run.rag_context, "context_for_agents": run.context_for_agents,
        "year": run.year, "model": run.model,
        "full_response": run.full_response,
        "created_at": run.created_at,
    }
    cache_set(NS_DB, *cache_key_parts, value=serializable, ttl=TTL_DB_READ)
    return run
