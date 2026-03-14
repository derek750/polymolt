from __future__ import annotations

from pydantic import BaseModel


# ── Single-agent run (kept for backwards compat) ──

class RunRequest(BaseModel):
    message: str
    system_prompt: str | None = None
    agent_type: str | None = None
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


class OrchestratorPhase1Response(BaseModel):
    question: str
    initial_bets: list[AgentBet]
    web_scrape_snippets: list[str]
    rag_context: str


class OrchestratorResponse(OrchestratorPhase1Response):
    assigned_agent_id: str
    assigned_agent_name: str
    expertise_rationale: str
    deep_analysis: str


class OrchestratorPhase2Request(OrchestratorPhase1Response):
    model: str | None = None


class OrchestratorPhase2Response(OrchestratorResponse):
    pass

