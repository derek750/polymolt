"""
AI pipeline router — single-agent run + orchestrated prediction pipeline.
"""

from fastapi import APIRouter

from app.ai.pipeline import run_pipeline
from app.ai.orchestrator import run_orchestrated_pipeline
from app.ai.schemas import (
    RunRequest,
    RunResponse,
    OrchestratorRequest,
    OrchestratorResponse,
)
from app.agents.config import list_agents

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/agents")
def agents():
    """List configured agents (id, name, description)."""
    return {
        "agents": [
            {"id": a.id, "name": a.name, "description": a.description, "model": a.model}
            for a in list_agents()
        ]
    }


@router.post("/run", response_model=RunResponse)
def run(request: RunRequest):
    """Run a single-agent pipeline: RAG (optional) + system prompt + LLM."""
    response = run_pipeline(
        message=request.message,
        system_prompt=request.system_prompt,
        agent_type=request.agent_type,
        use_rag=request.use_rag,
        model=request.model,
    )
    return RunResponse(response=response)


@router.post("/orchestrate", response_model=OrchestratorResponse)
def orchestrate(request: OrchestratorRequest):
    """
    Orchestrated prediction pipeline:
    1. All agents place an initial bet (YES/NO + confidence + reasoning).
    2. Orchestrator web-scrapes, identifies the best expertise, and
       assigns one agent for a deep analysis.
    """
    result = run_orchestrated_pipeline(
        question=request.question,
        use_rag=request.use_rag,
        model=request.model,
    )
    return OrchestratorResponse(**result)

