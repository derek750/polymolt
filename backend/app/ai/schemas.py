from __future__ import annotations

from pydantic import BaseModel


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

