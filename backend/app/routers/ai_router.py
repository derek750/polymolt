"""
AI pipeline router — run the RAG + agent pipeline and list agents.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.ai.pipeline import run_pipeline
from app.ai.stakeholder_pipeline import run_stakeholder_websearch_pipeline
from app.agents.config import list_agents

router = APIRouter(prefix="/ai", tags=["ai"])


class RunRequest(BaseModel):
    message: str
    system_prompt: str | None = None
    agent_type: str | None = None
    use_rag: bool = True
    model: str | None = None


class RunResponse(BaseModel):
    response: str


class WebsearchStakeholder(BaseModel):
    name: str
    type: str
    description: str


class WebsearchDetail(BaseModel):
    stakeholder: WebsearchStakeholder
    search_query: str
    search_snippet: str
    reasoning: str


class WebsearchRequest(BaseModel):
    message: str
    use_rag: bool = True
    model: str | None = None


class WebsearchResponse(BaseModel):
    message: str
    stakeholders: list[WebsearchStakeholder]
    combined_summary: str
    details: list[WebsearchDetail]


@router.get("/agents")
def agents():
    """List configured agents (id, name, description). Use agent_type=id in POST /run."""
    return {
        "agents": [
            {"id": a.id, "name": a.name, "description": a.description, "model": a.model}
            for a in list_agents()
        ]
    }


@router.post("/run", response_model=RunResponse)
def run(request: RunRequest):
    """Run the pipeline: RAG (optional) + specialized system prompt + LLM."""
    response = run_pipeline(
        message=request.message,
        system_prompt=request.system_prompt,
        agent_type=request.agent_type,
        use_rag=request.use_rag,
        model=request.model,
    )
    return RunResponse(response=response)


@router.post("/websearch", response_model=WebsearchResponse)
def websearch(request: WebsearchRequest):
    """
    Run the stakeholder-aware websearch pipeline.
    This is separate from /ai/run and focuses on stakeholders + external search.
    """
    result = run_stakeholder_websearch_pipeline(
        message=request.message,
        use_rag=request.use_rag,
        model=request.model,
    )
    return WebsearchResponse(**result)
