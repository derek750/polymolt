from __future__ import annotations

from pydantic import BaseModel


# ── Single-agent run (kept for backwards compat) ──

class RunRequest(BaseModel):
    message: str
    system_prompt: str | None = None
    agent_id: str | None = None
    use_rag: bool = True
    model: str | None = None


class RunResponse(BaseModel):
    response: str


# ── Orchestrated pipeline ──


class AgentBet(BaseModel):
    agent_id: str
    agent_name: str
    answer: str          # "YES" or "NO"
    confidence: int      # 0-100
    reasoning: str


class OrchestratorRequest(BaseModel):
    question: str
    use_rag: bool = True
    model: str | None = None
    where_filter: dict | None = None


class OrchestratorPhase1Response(BaseModel):
    question: str
    initial_bets: list[AgentBet]
    web_scrape_snippets: list[str]
    rag_context: str
    rag_chunks: list[str] = []


class RelevantAgentWithRag(BaseModel):
    agent_id: str
    rag_context_for_agent: str


class OrchestratorResponse(OrchestratorPhase1Response):
    assigned_agent_id: str
    assigned_agent_name: str
    expertise_rationale: str
    relevant_agents_with_rag: list[RelevantAgentWithRag] = []
    deep_analysis: str


class OrchestratorPhase2Request(OrchestratorPhase1Response):
    question_prompt: str = "[Placeholder: question prompt for the prediction market]"
    model: str | None = None


class OrchestratorPhase2Response(OrchestratorResponse):
    pass


# ── Convenience testing schemas ──


class ChudbotTestRequest(BaseModel):
    message: str
    use_rag: bool = True
    model: str | None = None


class ChudbotTestResponse(RunResponse):
    pass


# ── RAG retrieval (for testing) ──

class RagRetrieveRequest(BaseModel):
    query: str
    top_k: int = 4
    collection_name: str = "rag"
    where_filter: dict | None = None


class RagRetrieveResponse(BaseModel):
    query: str
    context: str
    has_context: bool
    hint: str | None = None  # Set when has_context is false, to help debug


# ── RAG Ingestion ──

class IngestRequest(BaseModel):
    texts: list[str]
    ids: list[str] | None = None
    collection_name: str = "rag"
    metadatas: list[dict] | None = None


class IngestResponse(BaseModel):
    count: int
    message: str

