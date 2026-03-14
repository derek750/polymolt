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
from app.ai.rag import retrieve, add_documents, get_collection
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
    RagRetrieveRequest,
    RagRetrieveResponse,
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
        agent_id=request.agent_id,
        use_rag=request.use_rag,
        model=request.model,
    )
    return RunResponse(response=response)


@router.post("/run/chudbot1", response_model=ChudbotTestResponse)
def run_chudbot1(request: ChudbotTestRequest):
    """
    Convenience endpoint to test the `chudbot1` agent directly.
    Uses the same pipeline as /ai/run but forces agent_id="chudbot1".
    """
    response = run_pipeline(
        message=request.message,
        system_prompt=None,
        agent_id="chudbot1",
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
        where_filter=request.where_filter,
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
    1. Read RAG (and chunks), question, question_prompt (placeholder ok), initial bets + web scrape.
    2. Orchestrator lists agents whose specialization is important and assigns each a related part of the RAG.
    3. Picks the best-suited agent and runs a deep analysis with that agent's RAG context.
    """
    # Convert AgentBet models to plain dicts for the orchestrator.
    bets = [b.model_dump() for b in request.initial_bets]

    phase2 = run_orchestrated_phase2(
        question=request.question,
        initial_bets=bets,
        web_scrape_snippets=request.web_scrape_snippets,
        rag_context=request.rag_context,
        rag_chunks=request.rag_chunks or None,
        question_prompt=request.question_prompt or None,
        model=request.model,
    )

    return OrchestratorPhase2Response(
        question=request.question,
        initial_bets=request.initial_bets,
        web_scrape_snippets=request.web_scrape_snippets,
        rag_context=request.rag_context,
        rag_chunks=request.rag_chunks,
        **phase2,
    )


@router.post("/rag/retrieve", response_model=RagRetrieveResponse)
def rag_retrieve(request: RagRetrieveRequest):
    """
    Return only the RAG context for a query (no LLM call).
    Use this to verify that retrieval and embeddings are working.
    """
    from app.config import OPENAI_API_KEY

    hint = None
    if not OPENAI_API_KEY:
        hint = (
            "OPENAI_API_KEY is not set. Set it in your environment (or .env in backend/) "
            "so RAG can compute embeddings for the query and for ingested documents."
        )
        return RagRetrieveResponse(
            query=request.query,
            context="",
            has_context=False,
            hint=hint,
        )

    try:
        coll = get_collection(request.collection_name)
        doc_count = coll.count()
    except Exception:
        doc_count = 0
    if doc_count == 0:
        hint = (
            "No documents in the RAG store. Ingest some first, e.g. "
            'curl -X POST http://localhost:8000/ai/ingest -H "Content-Type: application/json" '
            '-d \'{"texts": ["Your document text here."]}\''
        )
        return RagRetrieveResponse(
            query=request.query,
            context="",
            has_context=False,
            hint=hint,
        )

    context = retrieve(
        request.query,
        top_k=request.top_k,
        collection_name=request.collection_name,
        where_filter=request.where_filter,
    )
    if not context.strip():
        hint = "Retrieval returned no context (embedding or collection issue). Check OPENAI_API_KEY and EMBED_MODEL."
    return RagRetrieveResponse(
        query=request.query,
        context=context,
        has_context=bool(context.strip()),
        hint=hint,
    )


@router.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest):
    """Ingest documents into the vector store."""
    add_documents(
        texts=request.texts,
        ids=request.ids,
        collection_name=request.collection_name,
        metadatas=request.metadatas,
    )
    return IngestResponse(
        count=len(request.texts),
        message=f"Successfully ingested {len(request.texts)} documents into '{request.collection_name}'.",
    )

