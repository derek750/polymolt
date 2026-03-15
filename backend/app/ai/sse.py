"""
Server-Sent Events generators for phase1 and phase2 streams.
"""

import json
from typing import Iterator

from app.ai.orchestrator import run_phase1_stream, run_phase2_stream
from app.ai.schemas import Phase1Request, Phase2Request


def phase1_sse_generator(request: Phase1Request) -> Iterator[str]:
    """Yield SSE-formatted lines for phase1 stream."""
    for payload in run_phase1_stream(
        question=request.question,
        use_rag=request.use_rag,
        model=request.model,
    ):
        event_type = payload.get("event", "message")
        data = json.dumps(payload)
        yield f"event: {event_type}\ndata: {data}\n\n"


def phase2_sse_generator(request: Phase2Request) -> Iterator[str]:
    """Yield SSE-formatted lines for phase2 stream."""
    bets = [b.model_dump() for b in request.initial_bets]
    for payload in run_phase2_stream(
        question=request.question,
        initial_bets=bets,
        question_prompt=request.question_prompt or None,
        model=request.model,
    ):
        event_type = payload.get("event", "message")
        data = json.dumps(payload)
        yield f"event: {event_type}\ndata: {data}\n\n"
