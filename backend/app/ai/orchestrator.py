"""
Orchestrated prediction-market pipeline.

Flow
----
1. **Initial bet** — every agent evaluates the question and places a YES/NO
   bet with confidence + reasoning.
2. **Orchestrator** (this module):
   a. Collects the reasons from all agents.
   b. Web-scrapes the question (pure-Python, no AI).
   c. Asks the LLM to identify which expertise the question falls under and
      picks the best-fit agent.
   d. The assigned agent performs a deep analysis using the web data + the
      other agents' reasoning as additional context.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Iterator

from app.models import generate
from app.ai.pipeline import run_pipeline
from app.ai.rag import retrieve, retrieve_chunks
from app.ai.web_scraper import scrape_web

# Placeholder for the question prompt until a real one is wired in.
QUESTION_PROMPT_PLACEHOLDER = "[Placeholder: question prompt for the prediction market]"
from app.agents.config import AGENTS, get_agent, AgentConfig

logger = logging.getLogger(__name__)


# ── Phase 1: Initial bets ───────────────────────────────────────────────

_BET_SYSTEM = "You are {agent_name}. {system_prompt}"

_BET_USER = """\
A prediction market asks the following question:

\"\"\"{question}\"\"\"

{context_block}

Evaluate this question from your area of expertise.
Respond with ONLY a strict JSON object (no prose before or after):
{{
  "answer": "YES" or "NO",
  "confidence": <integer 0-100>,
  "reasoning": "<1-3 sentence explanation>"
}}
"""


def _run_single_bet(
    question: str,
    agent: AgentConfig,
    context: str,
    model: str | None,
) -> dict[str, Any]:
    ctx = f"Context:\n{context}" if context else "(No additional context.)"
    system = _BET_SYSTEM.format(agent_name=agent.name, system_prompt=agent.system_prompt)
    user = _BET_USER.format(question=question, context_block=ctx)
    raw = generate(user, system_prompt=system, model=agent.model or model, max_tokens=300)

    try:
        data = json.loads(raw)
    except Exception:
        logger.warning("Agent %s returned non-JSON bet: %s", agent.id, raw)
        data = {"answer": "UNKNOWN", "confidence": 0, "reasoning": raw}

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "answer": str(data.get("answer", "UNKNOWN")).upper(),
        "confidence": int(data.get("confidence", 0)),
        "reasoning": str(data.get("reasoning", "")),
    }


def _run_all_bets(
    question: str,
    context: str,
    model: str | None,
) -> list[dict[str, Any]]:
    return [
        _run_single_bet(question, agent, context, model)
        for agent in AGENTS
    ]


def _run_single_agent_bet(
    agent: AgentConfig,
    question: str,
    use_rag: bool,
    model: str | None,
) -> dict[str, Any]:
    """Run pipeline for one agent and return bet dict. Used for parallel phase1."""
    raw = run_pipeline(
        message=question,
        agent_id=agent.id,
        use_rag=use_rag,
        model=model,
    )
    try:
        data = json.loads(raw)
        answer = str(data.get("answer", "UNKNOWN")).upper()
        confidence = int(data.get("confidence", 0))
        reasoning = str(data.get("reasoning", ""))
    except Exception:
        logger.warning("Agent %s pipeline returned non-JSON: %s", agent.id, raw[:200])
        answer = "UNKNOWN"
        confidence = 0
        reasoning = raw
    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "answer": answer,
        "confidence": confidence,
        "reasoning": reasoning,
    }


def _run_phase1_via_pipeline(
    question: str,
    use_rag: bool = True,
    model: str | None = None,
) -> list[dict[str, Any]]:
    """
    Phase 1 using /run pipeline: run run_pipeline for each agent (same as POST /run per agent).
    Returns list of bets; each response is parsed as JSON if possible, else reasoning=response.
    """
    bets: list[dict[str, Any]] = []
    for agent in AGENTS:
        bet = _run_single_agent_bet(agent, question, use_rag, model)
        bets.append(bet)
    return bets


def run_phase1_stream(
    question: str,
    use_rag: bool = True,
    model: str | None = None,
) -> Iterator[dict[str, Any]]:
    """
    Phase 1 with SSE: run agents in parallel, yield an event when each agent finishes,
    then a final phase1_complete event with the full result.
    Events: {"event": "agent_done", "bet": {...}} and {"event": "phase1_complete", "result": Phase1Response dict}.
    """
    if use_rag:
        rag_chunks = retrieve_chunks(question, top_k=4)
        rag_context = "\n\n".join(rag_chunks) if rag_chunks else ""
    else:
        rag_chunks = []
        rag_context = ""

    bets: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=len(AGENTS)) as executor:
        future_to_agent = {
            executor.submit(_run_single_agent_bet, agent, question, use_rag, model): agent
            for agent in AGENTS
        }
        for future in as_completed(future_to_agent):
            bet = future.result()
            bets.append(bet)
            yield {"event": "agent_done", "bet": bet}

    scrape = scrape_web(question)
    result = {
        "question": question,
        "initial_bets": bets,
        "web_scrape_snippets": scrape.snippets,
        "rag_context": rag_context,
        "rag_chunks": rag_chunks,
    }
    yield {"event": "phase1_complete", "result": result}


# ── Phase 2: Orchestrator ───────────────────────────────────────────────

_EXPERTISE_SYSTEM = (
    "You are an orchestrator for a prediction market. "
    "You have RAG context (retrieved chunks), a question, and specialist agents with system prompts. "
    "Your job: (1) Read the RAG chunks and each agent's specialization (system prompt + description). "
    "(2) List every agent whose specialization is relevant to the question; for each such agent, "
    "select the most relevant part(s) of the RAG and provide that as the context to give that agent. "
    "Use the specialist agents' bets and web research to inform your choices."
)

_EXPERTISE_USER = """\
Question prompt: {question_prompt}

Question: \"\"\"{question}\"\"\"

RAG chunks (retrieved context), numbered for reference:
{rag_chunks_numbered}

The following specialist agents each placed a bet on this question:
{agent_summaries}

Web research snippets:
{web_snippets}

Available agents — id, name, description, and full system prompt (their specialization):
{agent_descriptions_with_prompts}

Tasks:
1. For each agent whose specialization you consider important for this question, list that agent and assign a related part of the RAG: copy or summarize the most relevant RAG excerpt for that agent into "rag_context_for_agent". Omit agents that are not relevant.
2. Choose the single best agent for deeper analysis ("assigned_agent_id") and give a short "rationale".

Respond with ONLY a strict JSON object (no markdown, no prose):
{{
  "relevant_agents": [
    {{ "agent_id": "<id>", "agent_name": "<name>", "rag_context_for_agent": "<excerpt from RAG chunks most relevant to this agent's expertise>" }}
  ],
  "assigned_agent_id": "<agent id>",
  "rationale": "<1-2 sentence explanation>"
}}
"""


def _identify_expertise_and_assign_rag(
    question: str,
    question_prompt: str,
    rag_chunks: list[str],
    bets: list[dict[str, Any]],
    web_snippets: list[str],
    model: str | None,
) -> tuple[str, str, dict[str, str]]:
    """
    Return (assigned_agent_id, rationale, agent_rag_context_map).
    agent_rag_context_map: agent_id -> rag_context string for that agent.
    """
    agent_summaries = "\n".join(
        f"- {b['agent_name']} ({b['agent_id']}): {b['answer']} "
        f"(confidence {b['confidence']}%) — {b['reasoning']}"
        for b in bets
    )
    agent_descriptions_with_prompts = "\n\n".join(
        f"- id: {a.id}\n  name: {a.name}\n  description: {a.description}\n  system_prompt: {a.system_prompt}"
        for a in AGENTS
    )
    snippets_text = "\n".join(web_snippets) if web_snippets else "(none)"
    rag_chunks_numbered = "\n\n".join(
        f"[Chunk {i+1}]\n{chunk}" for i, chunk in enumerate(rag_chunks)
    ) if rag_chunks else "(no RAG chunks provided)"

    user = _EXPERTISE_USER.format(
        question_prompt=question_prompt,
        question=question,
        rag_chunks_numbered=rag_chunks_numbered,
        agent_summaries=agent_summaries,
        web_snippets=snippets_text,
        agent_descriptions_with_prompts=agent_descriptions_with_prompts,
    )
    raw = generate(user, system_prompt=_EXPERTISE_SYSTEM, model=model, max_tokens=1500)

    agent_rag_map: dict[str, str] = {}
    try:
        data = json.loads(raw)
        for item in data.get("relevant_agents") or []:
            aid = str(item.get("agent_id", ""))
            if aid and get_agent(aid):
                agent_rag_map[aid] = str(item.get("rag_context_for_agent", "")).strip()
        agent_id = str(data.get("assigned_agent_id", ""))
        rationale = str(data.get("rationale", ""))
    except Exception:
        logger.warning("Expertise identification returned non-JSON: %s", raw)
        agent_id = AGENTS[0].id
        rationale = f"Defaulting to {AGENTS[0].name} (failed to parse orchestrator output)."

    if not get_agent(agent_id):
        logger.warning("Orchestrator picked unknown agent '%s'; falling back.", agent_id)
        agent_id = AGENTS[0].id
        rationale += f" (original pick was invalid; fell back to {AGENTS[0].name})"

    return agent_id, rationale, agent_rag_map


# ── Phase 2d: Deep analysis ─────────────────────────────────────────────

_DEEP_SYSTEM = (
    "You are {agent_name}. {system_prompt} "
    "You have been selected as the most qualified analyst for this question."
)

_DEEP_USER = """\
A prediction market is evaluating the question:

\"\"\"{question}\"\"\"

Other analysts placed the following bets:
{other_bets}

Relevant web research:
{web_snippets}

{context_block}

Provide a thorough, evidence-based analysis. Consider the other analysts'
perspectives and the web research. Conclude with your final assessment
of whether the answer is YES or NO, and your overall confidence level.
"""


def _run_deep_analysis(
    question: str,
    agent_id: str,
    bets: list[dict[str, Any]],
    web_snippets: list[str],
    context: str,
    model: str | None,
) -> str:
    agent = get_agent(agent_id) or AGENTS[0]

    other_bets = "\n".join(
        f"- {b['agent_name']}: {b['answer']} (confidence {b['confidence']}%) "
        f"— {b['reasoning']}"
        for b in bets
    )
    snippets_text = "\n".join(web_snippets) if web_snippets else "(none)"
    ctx = f"RAG context:\n{context}" if context else "(No RAG context available.)"

    system = _DEEP_SYSTEM.format(agent_name=agent.name, system_prompt=agent.system_prompt)
    user = _DEEP_USER.format(
        question=question,
        other_bets=other_bets,
        web_snippets=snippets_text,
        context_block=ctx,
    )
    analysis = generate(user, system_prompt=system, model=agent.model or model, max_tokens=1024)

    # Add visual RAG indicator
    if context:
        header = "🟢 [ORCHESTRATOR: RAG CONTEXT ACTIVE]\n" + "="*40 + "\n"
    else:
        header = "🔴 [ORCHESTRATOR: NO RAG CONTEXT FOUND]\n" + "="*40 + "\n"
    
    return f"{header}{analysis}"


def _run_single_agent_second_bet(
    agent_id: str,
    question: str,
    rag_context_for_agent: str,
    model: str | None,
) -> dict[str, Any]:
    """Run pipeline for one relevant agent with orchestrator-assigned RAG; return bet dict."""
    agent = get_agent(agent_id) or AGENTS[0]
    raw = run_pipeline(
        message=question,
        agent_id=agent_id,
        use_rag=False,
        model=model,
        additional_context=rag_context_for_agent,
    )
    try:
        data = json.loads(raw)
        answer = str(data.get("answer", "UNKNOWN")).upper()
        confidence = int(data.get("confidence", 0))
        reasoning = str(data.get("reasoning", ""))
    except Exception:
        logger.warning("Agent %s second bet returned non-JSON: %s", agent_id, raw[:200])
        answer = "UNKNOWN"
        confidence = 0
        reasoning = raw
    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "answer": answer,
        "confidence": confidence,
        "reasoning": reasoning,
    }


# ── Public entry points ─────────────────────────────────────────────────

def run_orchestrated_initial(
    question: str,
    use_rag: bool = True,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Phase 1 (legacy): RAG + internal bet prompt per agent + web scrape.
    Use run_phase1 for "same as /run per agent".
    """
    if use_rag:
        rag_chunks = retrieve_chunks(question, top_k=4)
        context = "\n\n".join(rag_chunks) if rag_chunks else ""
    else:
        rag_chunks = []
        context = ""
    bets = _run_all_bets(question, context, model)
    scrape = scrape_web(question)

    return {
        "question": question,
        "initial_bets": bets,
        "web_scrape_snippets": scrape.snippets,
        "rag_context": context,
        "rag_chunks": rag_chunks,
    }


def run_phase1(
    question: str,
    use_rag: bool = True,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Phase 1: Same as /run but runs every agent with /run.
    1. Optional RAG retrieval (shared rag_context/rag_chunks for phase 2).
    2. For each agent, run the same pipeline as POST /run; collect responses as initial_bets.
    3. Web scraping for additional non-AI context.
    """
    if use_rag:
        rag_chunks = retrieve_chunks(question, top_k=4)
        rag_context = "\n\n".join(rag_chunks) if rag_chunks else ""
    else:
        rag_chunks = []
        rag_context = ""
    bets = _run_phase1_via_pipeline(question, use_rag=use_rag, model=model)
    scrape = scrape_web(question)
    return {
        "question": question,
        "initial_bets": bets,
        "web_scrape_snippets": scrape.snippets,
        "rag_context": rag_context,
        "rag_chunks": rag_chunks,
    }


def run_orchestrated_phase2(
    question: str,
    initial_bets: list[dict[str, Any]],
    web_scrape_snippets: list[str],
    rag_context: str,
    rag_chunks: list[str] | None = None,
    question_prompt: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Phase 2 of the orchestrated pipeline:
    1. Orchestrator receives RAG (and optional chunks), question, question_prompt (placeholder ok).
    2. Reads all agent system prompts; lists agents whose specialization is important and assigns each a related part of the RAG as context.
    3. Picks the best-fit expert agent and runs a deep analysis with that agent's assigned RAG context.
    """
    bets = initial_bets
    web_snippets = web_scrape_snippets
    chunks = rag_chunks if rag_chunks is not None else ([s for s in rag_context.split("\n\n") if s.strip()] if rag_context else [])
    q_prompt = question_prompt or QUESTION_PROMPT_PLACEHOLDER

    assigned_id, rationale, agent_rag_map = _identify_expertise_and_assign_rag(
        question=question,
        question_prompt=q_prompt,
        rag_chunks=chunks,
        bets=bets,
        web_snippets=web_snippets,
        model=model,
    )
    assigned_agent = get_agent(assigned_id) or AGENTS[0]
    # Use orchestrator-assigned RAG context for this agent if available; else full rag_context.
    agent_specific_rag = agent_rag_map.get(assigned_id) or rag_context

    # Relevant agents each make a second bet with their assigned RAG context.
    second_bets: list[dict[str, Any]] = []
    for aid, ctx in agent_rag_map.items():
        bet = _run_single_agent_second_bet(aid, question, ctx, model)
        second_bets.append(bet)

    analysis = _run_deep_analysis(
        question=question,
        agent_id=assigned_id,
        bets=bets,
        web_snippets=web_snippets,
        context=agent_specific_rag,
        model=model,
    )

    relevant_agents = [
        {"agent_id": aid, "rag_context_for_agent": ctx}
        for aid, ctx in agent_rag_map.items()
    ]

    return {
        "assigned_agent_id": assigned_agent.id,
        "assigned_agent_name": assigned_agent.name,
        "expertise_rationale": rationale,
        "relevant_agents_with_rag": relevant_agents,
        "second_bets": second_bets,
        "deep_analysis": analysis,
    }


def run_phase2_stream(
    question: str,
    initial_bets: list[dict[str, Any]],
    web_scrape_snippets: list[str],
    rag_context: str,
    rag_chunks: list[str] | None = None,
    question_prompt: str | None = None,
    model: str | None = None,
) -> Iterator[dict[str, Any]]:
    """
    Phase 2 with SSE: orchestrator assigns RAG to relevant agents; each makes a second bet (streamed);
    then assigned agent runs deep analysis; final phase2_complete with full result.
    Events: orchestrator_done, agent_second_bet_done (per relevant agent), deep_analysis_done, phase2_complete.
    """
    web_snippets = web_scrape_snippets
    chunks = rag_chunks if rag_chunks is not None else ([s for s in rag_context.split("\n\n") if s.strip()] if rag_context else [])
    q_prompt = question_prompt or QUESTION_PROMPT_PLACEHOLDER

    assigned_id, rationale, agent_rag_map = _identify_expertise_and_assign_rag(
        question=question,
        question_prompt=q_prompt,
        rag_chunks=chunks,
        bets=initial_bets,
        web_snippets=web_snippets,
        model=model,
    )
    assigned_agent = get_agent(assigned_id) or AGENTS[0]
    relevant_agents_with_rag = [
        {"agent_id": aid, "rag_context_for_agent": ctx}
        for aid, ctx in agent_rag_map.items()
    ]

    yield {
        "event": "orchestrator_done",
        "assigned_agent_id": assigned_agent.id,
        "assigned_agent_name": assigned_agent.name,
        "expertise_rationale": rationale,
        "relevant_agents_with_rag": relevant_agents_with_rag,
    }

    second_bets: list[dict[str, Any]] = []
    if agent_rag_map:
        with ThreadPoolExecutor(max_workers=len(agent_rag_map)) as executor:
            future_to_agent = {
                executor.submit(
                    _run_single_agent_second_bet,
                    aid,
                    question,
                    ctx,
                    model,
                ): aid
                for aid, ctx in agent_rag_map.items()
            }
            for future in as_completed(future_to_agent):
                bet = future.result()
                second_bets.append(bet)
                yield {"event": "agent_second_bet_done", "bet": bet}

    agent_specific_rag = agent_rag_map.get(assigned_id) or rag_context
    analysis = _run_deep_analysis(
        question=question,
        agent_id=assigned_id,
        bets=initial_bets,
        web_snippets=web_snippets,
        context=agent_specific_rag,
        model=model,
    )
    yield {"event": "deep_analysis_done", "deep_analysis": analysis}

    result = {
        "assigned_agent_id": assigned_agent.id,
        "assigned_agent_name": assigned_agent.name,
        "expertise_rationale": rationale,
        "relevant_agents_with_rag": relevant_agents_with_rag,
        "second_bets": second_bets,
        "deep_analysis": analysis,
    }
    yield {"event": "phase2_complete", "result": result}


def run_orchestrated_pipeline(
    question: str,
    use_rag: bool = True,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Full orchestrated pipeline:
    1. All agents place an initial bet.
    2. Orchestrator collects reasons, web-scrapes, identifies expertise,
       assigns the best agent for a deep analysis.
    """
    # Phase 1 — initial bets + RAG + web scrape
    phase1 = run_orchestrated_initial(question=question, use_rag=use_rag, model=model)
    context = phase1["rag_context"]
    bets = phase1["initial_bets"]
    web_snippets = phase1["web_scrape_snippets"]

    # Phase 2 — expertise selection + RAG assignment + deep analysis
    phase2 = run_orchestrated_phase2(
        question=question,
        initial_bets=bets,
        web_scrape_snippets=web_snippets,
        rag_context=context,
        rag_chunks=phase1.get("rag_chunks"),
        question_prompt=QUESTION_PROMPT_PLACEHOLDER,
        model=model,
    )

    return {**phase1, **phase2}
