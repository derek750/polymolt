"""
Database router — IBM Db2-backed endpoints for persisting questions and stakeholder AI perspectives.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db.db2 import (
    StakeholderPerspective,
    StakeholderResponseRow,
    QuestionRow,
    QuestionSummary,
    create_question_only,
    get_question_with_responses,
    get_orchestrate_run,
    list_recent_questions,
    save_question_with_perspectives,
)
from app.db.schemas import (
    CreateQuestionOnlyRequest,
    QuestionDetailResponse,
    QuestionListResponse,
    OrchestrateRunOut,
    QuestionSummaryOut,
    SaveQuestionRequest,
    SaveQuestionResponse,
    StakeholderPerspectiveIn,
    StakeholderResponseOut,
)

router = APIRouter(prefix="/db", tags=["database"])


@router.get("/health")
def db_health():
    """
    Health check for the Db2 integration. Tests actual connection.
    """
    from app.db.db2 import db2_connection, DB2_DSN
    
    if not DB2_DSN:
        return {
            "status": "error",
            "message": "DB2_DSN environment variable is not set.",
            "available": False,
        }
    
    try:
        with db2_connection() as conn:
            # Test query
            import ibm_db
            stmt = ibm_db.exec_immediate(conn, "SELECT 1 FROM SYSIBM.SYSDUMMY1")
            ibm_db.fetch_row(stmt)
        return {
            "status": "ok",
            "message": "Db2 connection successful",
            "available": True,
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Db2 connection failed: {str(exc)}",
            "available": False,
        }


@router.post("/questions", response_model=SaveQuestionResponse)
def save_question(request: SaveQuestionRequest) -> SaveQuestionResponse:
    """
    Save a question and all stakeholder AI perspectives to IBM Db2.

    Call this from your question pipeline once you have:
      - the final location label
      - the full set of stakeholder AIs and their yes/no answers
    
    If DB2 is unavailable, logs a warning but does not fail the orchestration.
    """
    try:
        perspectives = [
            StakeholderPerspective(
                stakeholder_id=s.stakeholder_id,
                stakeholder_role=s.stakeholder_role,
                ai_agent_id=s.ai_agent_id,
                answer=s.answer,
                confidence=s.confidence,
                reasoning=s.reasoning,
                location=request.location,
                raw_payload=s.raw_payload,
            )
            for s in request.stakeholders
        ]

        question_id = save_question_with_perspectives(
            question=request.question,
            location=request.location,
            perspectives=perspectives,
        )
    except Exception as exc:  # Log but don't crash - DB2 is optional
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to save question to DB2 (DB2 may be unavailable): {exc}")
        # Return a dummy ID - the orchestration should continue even if DB2 fails
        return SaveQuestionResponse(question_id=-1)

    return SaveQuestionResponse(question_id=question_id)


@router.post("/questions/basic", response_model=SaveQuestionResponse)
def create_question_basic(request: CreateQuestionOnlyRequest) -> SaveQuestionResponse:
    """
    Create a question row without any stakeholder responses.

    This is useful for frontends that collect questions first, then run
    stakeholder AI pipelines asynchronously and attach responses later.
    """
    try:
        question_id = create_question_only(
            question=request.question,
            location=request.location,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return SaveQuestionResponse(question_id=question_id)


@router.get("/questions", response_model=QuestionListResponse)
def list_questions(limit: int = 50) -> QuestionListResponse:
    """
    List recent questions with simple yes/no counts.
    
    Returns empty list if DB2 is unavailable (graceful degradation).
    """
    try:
        rows = list_recent_questions(limit=limit)
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"DB2 unavailable, returning empty list: {exc}")
        # Graceful degradation: return empty list instead of crashing
        return QuestionListResponse(questions=[])

    questions = [
        QuestionSummaryOut(
            id=row.id,
            question_text=row.question_text,
            location=row.location,
            created_at=row.created_at,
            yes_count=row.yes_count,
            no_count=row.no_count,
        )
        for row in rows
    ]
    return QuestionListResponse(questions=questions)


@router.get("/questions/{question_id}", response_model=QuestionDetailResponse)
def get_question(question_id: int) -> QuestionDetailResponse:
    """
    Get a single question and all stored stakeholder responses.
    """
    try:
        q_row, resp_rows = get_question_with_responses(question_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"DB2 unavailable for question {question_id}: {exc}")
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(exc)}") from exc

    # Compute aggregated counts to reuse QuestionSummaryOut
    yes_count = sum(1 for r in resp_rows if r.answer.upper() == "YES")
    no_count = sum(1 for r in resp_rows if r.answer.upper() == "NO")

    question = QuestionSummaryOut(
        id=q_row.id,
        question_text=q_row.question_text,
        location=q_row.location,
        created_at=q_row.created_at,
        yes_count=yes_count,
        no_count=no_count,
    )

    responses = [
        StakeholderResponseOut(
            id=r.id,
            question_id=r.question_id,
            phase=r.phase,
            stakeholder_id=r.stakeholder_id,
            stakeholder_role=r.stakeholder_role,
            ai_agent_id=r.ai_agent_id,
            answer=r.answer,
            confidence=r.confidence,
            reasoning=r.reasoning,
            created_at=r.created_at,
        )
        for r in resp_rows
    ]

    return QuestionDetailResponse(question=question, responses=responses)


@router.get("/questions/{question_id}/orchestrate", response_model=OrchestrateRunOut)
def get_question_orchestrate(question_id: int) -> OrchestrateRunOut:
    """
    Get the saved orchestrate run for a question (topic_reasoning, deep_analysis,
    assigned_agent_id, full_response JSON, etc.).
    """
    import json as _json
    try:
        row = get_orchestrate_run(question_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail=f"No orchestrate run for question {question_id}")
    full = None
    if row.full_response:
        try:
            full = _json.loads(row.full_response)
        except Exception:
            full = None
    return OrchestrateRunOut(
        question_id=row.question_id,
        topic_reasoning=row.topic_reasoning or "",
        deep_analysis=row.deep_analysis or "",
        assigned_agent_id=row.assigned_agent_id,
        expertise_rationale=row.expertise_rationale,
        rag_context=row.rag_context,
        context_for_agents=row.context_for_agents,
        year=row.year,
        model=row.model,
        full_response=full,
        created_at=row.created_at or "",
    )

