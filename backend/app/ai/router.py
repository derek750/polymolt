"""
AI pipeline router — single-agent run + orchestrated prediction pipeline.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.ai.pipeline import run_pipeline
from app.ai.orchestrator import (
    run_orchestrated_phase2,
    run_orchestrated_pipeline,
    run_orchestrated_initial,
)
from app.ai.rag import add_documents, retrieve, get_collection
from app.ai.sse import phase1_sse_generator, phase2_sse_generator
from app.ai.schemas import (
    RunRequest,
    RunResponse,
    ContextRunRequest,
    ContextRunResponse,
    ChudbotTestRequest,
    ChudbotTestResponse,
    RagRetrieveRequest,
    RagRetrieveResponse,
    Phase1Request,
    Phase1Response,
    Phase2Request,
    Phase2Response,
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
    """Run a single-agent pipeline: RAG (optional) + system prompt + LLM. No additional context."""
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


@router.post("/contextrun", response_model=ContextRunResponse)
def contextrun(request: ContextRunRequest):
    """Run the same agent pipeline with optional additional context (e.g. orchestrator-assigned RAG)."""
    response = run_pipeline(
        message=request.message,
        system_prompt=request.system_prompt,
        agent_id=request.agent_id,
        use_rag=request.use_rag,
        model=request.model,
        additional_context=request.additional_context,
    )
    return ContextRunResponse(response=response)


@router.post("/phase1", response_model=Phase1Response)
def phase1(request: Phase1Request):
    """
    Phase 1: All agents place initial bet. Returns question + initial_bets.
    Phase 2 fetches its own RAG when invoked.
    """
    result = run_orchestrated_initial(
        question=request.question,
        location=request.location,
        use_rag=request.use_rag,
        model=request.model,
        where_filter=request.where_filter,
    )
    return Phase1Response(**result)


@router.post("/phase1/stream")
def phase1_stream(request: Phase1Request):
    """
    Phase 1 as Server-Sent Events: agents run in parallel; one event per agent when done,
    then a final phase1_complete event with the full result.
    """
    return StreamingResponse(
        phase1_sse_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/phase2", response_model=Phase2Response)
def phase2(request: Phase2Request):
    """
    Phase 2: Orchestrator reads RAG context and initiates agents with new context.
    Relevant agents make a second bet; assigned agent runs deep analysis.
    """
    bets = [b.model_dump() for b in request.initial_bets]

    phase2_result = run_orchestrated_phase2(
        question=request.question,
        initial_bets=bets,
        question_prompt=request.question_prompt or None,
        model=request.model,
    )

    return Phase2Response(
        question=request.question,
        location=request.location,
        initial_bets=request.initial_bets,
        **phase2_result,
    )


@router.post("/phase2/stream")
def phase2_stream(request: Phase2Request):
    """
    Phase 2 as Server-Sent Events: orchestrator_done, then one agent_second_bet_done per
    relevant agent (parallel), then phase2_complete with full result.
    """
    return StreamingResponse(
        phase2_sse_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/orchestrate", response_model=Phase2Response)
def orchestrate(request: Phase1Request):
    """
    Full orchestrated pipeline in one call:
    1. All agents place an initial bet (phase1).
    2. Orchestrator web-scrapes, identifies expertise, assigns agent(s), runs deep analysis (phase2).
    """
    result = run_orchestrated_pipeline(
        question=request.question,
        location=request.location,
        use_rag=request.use_rag,
        model=request.model,
        where_filter=request.where_filter,
    )
    return Phase2Response(**result)


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

