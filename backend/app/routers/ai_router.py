"""
AI pipeline router — run the RAG + agent pipeline and list agents.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.ai.pipeline import run_pipeline
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
