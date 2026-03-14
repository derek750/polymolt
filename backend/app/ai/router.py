"""
AI pipeline router — single-agent run + orchestrated prediction pipeline.
"""

from fastapi import APIRouter

from app.ai.pipeline import run_pipeline
from app.ai.orchestrator import (
    run_orchestrated_pipeline,
    run_orchestrated_initial,
    run_orchestrated_phase2,
)
from app.ai.rag import retrieve, add_documents
from app.ai.schemas import (
    RunRequest,
    RunResponse,
    OrchestratorRequest,
    OrchestratorResponse,
    OrchestratorPhase1Response,
    OrchestratorPhase2Request,
    OrchestratorPhase2Response,
    ChudbotTestRequest,
    ChudbotTestResponse,
    IngestRequest,
    IngestResponse,
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


@router.post("/run/chudbot1", response_model=ChudbotTestResponse)
def run_chudbot1(request: ChudbotTestRequest):
    """
    Convenience endpoint to test the `chudbot1` agent directly.
    Uses the same pipeline as /ai/run but forces agent_type="chudbot1".
    """
    response = run_pipeline(
        message=request.message,
        system_prompt=None,
        agent_type="chudbot1",
        use_rag=request.use_rag,
        model=request.model,
    )
    return ChudbotTestResponse(response=response)


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


@router.post("/orchestrate/phase1", response_model=OrchestratorPhase1Response)
def orchestrate_phase1(request: OrchestratorRequest):
    """
    Phase 1 of the orchestrated pipeline:
    1. Optional RAG retrieval (shared context).
    2. All agents place an initial bet.
    3. Web scraping for additional non-AI context.
    """
    result = run_orchestrated_initial(
        question=request.question,
        use_rag=request.use_rag,
        model=request.model,
    )
    return OrchestratorPhase1Response(**result)


@router.post("/orchestrate/phase2", response_model=OrchestratorPhase2Response)
def orchestrate_phase2(request: OrchestratorPhase2Request):
    """
    Phase 2 of the orchestrated pipeline:
    1. Read initial bets + web scrape + RAG context.
    2. Pick the best-suited agent.
    3. Run a deep analysis with that agent.
    """
    # Convert AgentBet models to plain dicts for the orchestrator.
    bets = [b.model_dump() for b in request.initial_bets]

    phase2 = run_orchestrated_phase2(
        question=request.question,
        initial_bets=bets,
        web_scrape_snippets=request.web_scrape_snippets,
        rag_context=request.rag_context,
        model=request.model,
    )

    return OrchestratorPhase2Response(
        question=request.question,
        initial_bets=request.initial_bets,
        web_scrape_snippets=request.web_scrape_snippets,
        rag_context=request.rag_context,
        **phase2,
    )


@router.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest):
    """Ingest documents into the vector store."""
    add_documents(
        texts=request.texts,
        ids=request.ids,
        collection_name=request.collection_name,
    )
    return IngestResponse(
        count=len(request.texts),
        message=f"Successfully ingested {len(request.texts)} documents into '{request.collection_name}'.",
    )

