"""
Orchestrated prediction-market pipeline.

Flow
----
1. **Initial bet** — every agent evaluates the question and places a YES/NO
   bet with confidence + reasoning.
2. **Orchestrator** (this module):
   a. Collects the reasons from all agents.
   b. Uses RAG (news/search) context only; no web scraping.
   c. Asks the LLM to identify which expertise the question falls under and
      picks the best-fit agent(s).
   d. Each relevant agent runs the pipeline again with orchestrator-assigned
      RAG context (second bet); results are collected as triggered_agents.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Iterator

from app.models import generate
from app.ai.pipeline import run_pipeline
from app.ai.rag import retrieve, retrieve_chunks, embed as embed_text
from app.ai.bet_sizing import get_bet_for_agent, compute_confidence

# Placeholder for the question prompt until a real one is wired in.
QUESTION_PROMPT_PLACEHOLDER = "[Placeholder: question prompt for the prediction market]"
from app.agents.config import AGENTS, get_agent, AgentConfig

logger = logging.getLogger(__name__)


def _debug_log(msg: str):
    logger.debug(msg)


def _normalize_answer(answer: str) -> str:
    """Treat UNKNOWN or invalid answers as NO. Returns YES or NO."""
    a = (answer or "").strip().upper()
    return "YES" if a == "YES" else "NO"


# ── Phase 1: Initial bets ───────────────────────────────────────────────

_BET_SYSTEM = "You are {agent_name}. {system_prompt}"

_BET_USER = """\
A prediction market is predicting outcomes and evaluating claims about locations in Toronto (e.g., hospitals, nurseries, attractions) to help mitigate asymmetric information for the public.
Consider the following question or claim:

\"\"\"{question}\"\"\"

{context_block}

Evaluate this location/claim from your area of expertise.
Respond with ONLY a strict JSON object (no prose before or after):
{{
  "answer": "YES" or "NO",
  "reasoning": "<1-3 sentence explanation>"
}}
"""


def _run_single_bet(
    question: str,
    agent: AgentConfig,
    context: str,
    model: str | None,
    question_embedding: list[float] | None = None,
) -> dict[str, Any]:
    ctx = f"Context:\n{context}" if context else "(No additional context.)"
    system = _BET_SYSTEM.format(agent_name=agent.name, system_prompt=agent.system_prompt)
    user = _BET_USER.format(question=question, context_block=ctx)
    raw = generate(user, system_prompt=system, model=agent.model or model, max_tokens=300)

    try:
        data = json.loads(raw)
    except Exception:
        logger.warning("Agent %s returned non-JSON bet: %s", agent.id, raw)
        data = {"answer": "UNKNOWN", "reasoning": raw}

    reasoning = str(data.get("reasoning", ""))
    bet_info = get_bet_for_agent(
        agent,
        question_prompt=question,
        response_text=reasoning,
        question_embedding=question_embedding,
    )
    confidence = compute_confidence(bet_info)

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "answer": _normalize_answer(str(data.get("answer", "UNKNOWN"))),
        "confidence": confidence,
        "reasoning": reasoning,
    }


def _run_all_bets(
    question: str,
    context: str,
    model: str | None,
) -> list[dict[str, Any]]:
    q_emb = embed_text(question)
    bets = []
    for i, agent in enumerate(AGENTS):
        _debug_log(f"Phase 1: Agent {i+1}/{len(AGENTS)} betting: {agent.id}")
        bets.append(_run_single_bet(question, agent, context, model, question_embedding=q_emb))
    return bets


def _run_single_agent_bet(
    agent: AgentConfig,
    question: str,
    use_rag: bool,
    model: str | None,
    question_embedding: list[float] | None = None,
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
        answer = _normalize_answer(str(data.get("answer", "UNKNOWN")))
        reasoning = str(data.get("reasoning", ""))
    except Exception:
        logger.warning("Agent %s pipeline returned non-JSON: %s", agent.id, raw[:200])
        answer = "NO"  # UNKNOWN → NO
        reasoning = raw

    bet_info = get_bet_for_agent(
        agent,
        question_prompt=question,
        response_text=reasoning,
        question_embedding=question_embedding,
    )
    confidence = compute_confidence(bet_info)

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
    q_emb = embed_text(question)
    bets: list[dict[str, Any]] = []
    for agent in AGENTS:
        bet = _run_single_agent_bet(agent, question, use_rag, model, question_embedding=q_emb)
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
        rag_chunks = retrieve_chunks(question, top_k=4, collection_name="news_rag")
        rag_context = "\n\n".join(rag_chunks) if rag_chunks else ""
    else:
        rag_chunks = []
        rag_context = ""

    q_emb = embed_text(question)
    bets: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=len(AGENTS)) as executor:
        future_to_agent = {
            executor.submit(_run_single_agent_bet, agent, question, use_rag, model, q_emb): agent
            for agent in AGENTS
        }
        for future in as_completed(future_to_agent):
            bet = future.result()
            bets.append(bet)
            yield {"event": "agent_done", "bet": bet}

    result = {
        "question": question,
        "initial_bets": bets,
        "web_scrape_snippets": [],
        "rag_context": rag_context,
        "rag_chunks": rag_chunks,
    }
    yield {"event": "phase1_complete", "result": result}


# ── Phase 2: Orchestrator ───────────────────────────────────────────────

_EXPERTISE_SYSTEM = (
    "You are an orchestrator for a prediction market focused on evaluating Toronto locations (hospitals, nurseries, attractions). "
    "You have RAG context (retrieved news/reviews), a question, and specialist agents with system prompts. "
    "Your job: (1) Read the RAG chunks and each agent's specialization (system prompt + description). "
    "(2) List every agent whose specialization is relevant to evaluating this location/claim; for each such agent, "
    "select the most relevant part(s) of the RAG and provide that as the context to give that agent. "
    "Use the specialist agents' bets and the RAG context to inform your choices to mitigate asymmetric information."
)

_EXPERTISE_USER = """\
Question prompt: {question_prompt}

Question: \"\"\"{question}\"\"\"

RAG chunks (retrieved context), numbered for reference:
{rag_chunks_numbered}

The following specialist agents each placed a bet on this question:
{agent_summaries}

Additional context (e.g. from search; may be none):
{web_snippets}

Available agents — id, name, description, and full system prompt (their specialization):
{agent_descriptions_with_prompts}

Tasks:
1. Provide an "overall_topic_reasoning" about what this topic/question is about.
2. Identify ALL agents whose specialization is important for this question.
3. For each relevant agent:
   - Provide a "choice_reasoning" for why this specific agent's expertise is needed.
   - Assign a "rag_context_for_agent": copy or summarize the most relevant RAG excerpt for that agent.

Respond with ONLY a strict JSON object:
{{
  "overall_topic_reasoning": "<explanation>",
  "relevant_agents": [
    {{ 
      "agent_id": "<id>", 
      "choice_reasoning": "<why this agent>",
      "rag_context_for_agent": "<relevant RAG excerpt>" 
    }}
  ]
}}
"""


def _identify_expertise_and_assign_rag(
    question: str,
    question_prompt: str,
    rag_chunks: list[str],
    bets: list[dict[str, Any]],
    web_snippets: list[str],
    model: str | None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Return (topic_reasoning, relevant_agents_list).
    relevant_agents_list: list of dicts with {agent_id, choice_reasoning, rag_context_for_agent}
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
    # Using a larger max_tokens because we're asking for more detail
    raw = generate(user, system_prompt=_EXPERTISE_SYSTEM, model=model, max_tokens=2000)

    try:
        data = json.loads(raw)
        topic_reasoning = str(data.get("overall_topic_reasoning", ""))
        relevant_agents = data.get("relevant_agents") or []
        # Ensure minimal structure
        if not relevant_agents:
             # Fallback: if none selected, pick the first one
             relevant_agents = [{"agent_id": AGENTS[0].id, "choice_reasoning": "Default agent selection.", "rag_context_for_agent": ""}]
    except Exception:
        logger.warning("Expertise identification returned non-JSON: %s", raw)
        topic_reasoning = "Failed to parse orchestrator topic reasoning."
        relevant_agents = [{"agent_id": AGENTS[0].id, "choice_reasoning": "Fallback due to parsing error.", "rag_context_for_agent": ""}]

    return topic_reasoning, relevant_agents


def _run_single_agent_second_bet(
    agent_id: str,
    question: str,
    rag_context_for_agent: str,
    model: str | None,
    question_embedding: list[float] | None = None,
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
        answer = _normalize_answer(str(data.get("answer", "UNKNOWN")))
        reasoning = str(data.get("reasoning", ""))
    except Exception:
        logger.warning("Agent %s second bet returned non-JSON: %s", agent_id, raw[:200])
        answer = "NO"  # UNKNOWN → NO
        reasoning = raw

    bet_info = get_bet_for_agent(
        agent,
        question_prompt=question,
        response_text=reasoning,
        question_embedding=question_embedding,
    )
    confidence = compute_confidence(bet_info)

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
    where_filter: dict | None = None,
) -> dict[str, Any]:
    """
    Phase 1 (legacy): RAG + internal bet prompt per agent. No web scraping.
    Use run_phase1 for "same as /run per agent".
    """
    if use_rag:
        rag_chunks = retrieve_chunks(question, top_k=4, collection_name="news_rag", where_filter=where_filter)
        context = "\n\n".join(rag_chunks) if rag_chunks else ""
    else:
        rag_chunks = []
        context = ""
    bets = _run_all_bets(question, context, model)

    return {
        "question": question,
        "initial_bets": bets,
        "web_scrape_snippets": [],
        "rag_context": context,
        "rag_chunks": rag_chunks,
    }


def run_phase1(
    question: str,
    use_rag: bool = True,
    model: str | None = None,
    where_filter: dict | None = None,
) -> dict[str, Any]:
    """
    Phase 1: Same as /run but runs every agent with /run.
    1. Optional RAG retrieval (shared rag_context/rag_chunks for phase 2).
    2. For each agent, run the same pipeline as POST /run; collect responses as initial_bets.
    """
    if use_rag:
        rag_chunks = retrieve_chunks(question, top_k=4, collection_name="news_rag", where_filter=where_filter)
        rag_context = "\n\n".join(rag_chunks) if rag_chunks else ""
    else:
        rag_chunks = []
        rag_context = ""
    bets = _run_phase1_via_pipeline(question, use_rag=use_rag, model=model)
    return {
        "question": question,
        "initial_bets": bets,
        "web_scrape_snippets": [],
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
    1. Orchestrator receives RAG chunks, question, question_prompt.
    2. Identifies ONE OR MORE relevant agents and assigns specific RAG context.
    3. Runs each triggered agent and collects their results.
    """
    bets = initial_bets
    web_snippets = web_scrape_snippets
    chunks = rag_chunks if rag_chunks is not None else ([s for s in rag_context.split("\n\n") if s.strip()] if rag_context else [])
    q_prompt = question_prompt or QUESTION_PROMPT_PLACEHOLDER

    topic_reasoning, relevant_agents_info = _identify_expertise_and_assign_rag(
        question=question,
        question_prompt=q_prompt,
        rag_chunks=chunks,
        bets=bets,
        web_snippets=web_snippets,
        model=model,
    )

    q_emb = embed_text(question)
    _debug_log(f"Phase 2 processing: {len(relevant_agents_info)} relevant agents found.")
    triggered_agents: list[dict[str, Any]] = []
    for i, info in enumerate(relevant_agents_info):
        aid = info.get("agent_id")
        _debug_log(f"Triggering agent {i+1}/{len(relevant_agents_info)}: {aid}")
        choice_reasoning = info.get("choice_reasoning", "")
        agent_specific_rag = info.get("rag_context_for_agent", "") or rag_context

        bet = _run_single_agent_second_bet(
            agent_id=aid,
            question=question,
            rag_context_for_agent=agent_specific_rag,
            model=model,
            question_embedding=q_emb,
        )
        triggered_agents.append({
            "agent_id": bet["agent_id"],
            "agent_name": bet["agent_name"],
            "choice_reasoning": choice_reasoning,
            "context": agent_specific_rag,
            "answer": bet["answer"],
            "confidence": bet["confidence"],
            "analysis": bet["reasoning"],
        })

    # Legacy / Phase2Response: primary = first triggered agent
    primary = triggered_agents[0] if triggered_agents else {
        "agent_id": "none", "agent_name": "None", "choice_reasoning": "None",
        "context": "", "answer": "NO", "confidence": 0, "analysis": "No agents triggered.",
    }

    # Phase2Response also expects relevant_agents_with_rag and second_bets
    relevant_agents_with_rag = [
        {"agent_id": t["agent_id"], "rag_context_for_agent": t["context"]}
        for t in triggered_agents
    ]
    second_bets = [
        {
            "agent_id": t["agent_id"],
            "agent_name": t["agent_name"],
            "answer": t["answer"],
            "confidence": t["confidence"],
            "reasoning": t["analysis"],
        }
        for t in triggered_agents
    ]

    return {
        "topic_reasoning": topic_reasoning,
        "triggered_agents": triggered_agents,
        "assigned_agent_id": primary["agent_id"],
        "assigned_agent_name": primary["agent_name"],
        "expertise_rationale": primary["choice_reasoning"],
        "relevant_agents_with_rag": relevant_agents_with_rag,
        "second_bets": second_bets,
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
    final phase2_complete with full result.
    Events: orchestrator_done, agent_second_bet_done (per relevant agent), phase2_complete.
    """
    web_snippets = web_scrape_snippets
    chunks = rag_chunks if rag_chunks is not None else ([s for s in rag_context.split("\n\n") if s.strip()] if rag_context else [])
    q_prompt = question_prompt or QUESTION_PROMPT_PLACEHOLDER

    topic_reasoning, relevant_agents_info = _identify_expertise_and_assign_rag(
        question=question,
        question_prompt=q_prompt,
        rag_chunks=chunks,
        bets=initial_bets,
        web_snippets=web_snippets,
        model=model,
    )
    # Derive single-assigned shape for stream events (first relevant agent)
    assigned_id = relevant_agents_info[0]["agent_id"] if relevant_agents_info else (AGENTS[0].id if AGENTS else "")
    rationale = relevant_agents_info[0].get("choice_reasoning", "") if relevant_agents_info else ""
    agent_rag_map = {r["agent_id"]: r.get("rag_context_for_agent", "") for r in relevant_agents_info}
    assigned_agent = get_agent(assigned_id) or (AGENTS[0] if AGENTS else None)
    if not assigned_agent:
        raise ValueError("No agents configured")
    relevant_agents_with_rag = [
        {"agent_id": r["agent_id"], "rag_context_for_agent": r.get("rag_context_for_agent", "")}
        for r in relevant_agents_info
    ]

    q_emb = embed_text(question)

    yield {
        "event": "orchestrator_done",
        "topic_reasoning": topic_reasoning,
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
                    q_emb,
                ): aid
                for aid, ctx in agent_rag_map.items()
            }
            for future in as_completed(future_to_agent):
                bet = future.result()
                second_bets.append(bet)
                yield {"event": "agent_second_bet_done", "bet": bet}

    result = {
        "topic_reasoning": topic_reasoning,
        "assigned_agent_id": assigned_agent.id,
        "assigned_agent_name": assigned_agent.name,
        "expertise_rationale": rationale,
        "relevant_agents_with_rag": relevant_agents_with_rag,
        "second_bets": second_bets,
    }
    yield {"event": "phase2_complete", "result": result}


def run_orchestrated_pipeline(
    question: str,
    use_rag: bool = True,
    model: str | None = None,
    where_filter: dict | None = None,
) -> dict[str, Any]:
    """
    Full orchestrated pipeline:
    1. All agents place an initial bet.
    2. Orchestrator identifies expertise, assigns RAG to relevant agents,
       and each runs a second bet via the pipeline.
    """
    _debug_log(f"Starting pipeline for question: {question}")
    # Phase 1 — initial bets + RAG (no web scrape)
    phase1 = run_orchestrated_initial(question=question, use_rag=use_rag, model=model, where_filter=where_filter)
    _debug_log("Phase 1 complete.")
    context = phase1["rag_context"]
    bets = phase1["initial_bets"]
    web_snippets = phase1["web_scrape_snippets"]

    # Phase 2 — expertise selection + RAG assignment + second bets
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
