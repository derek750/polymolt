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
    }
    yield {"event": "phase1_complete", "result": result}


# ── Phase 2: Orchestrator ───────────────────────────────────────────────

_KEY_FACTS_SYSTEM = (
    "You are an analyst for a prediction market about Toronto locations (hospitals, nurseries, attractions). "
    "Given RAG-retrieved text chunks and a question, you identify key facts from the chunks that are relevant to the question. "
    "Each fact must include a short, verbatim quote from the RAG that supports it."
)

_KEY_FACTS_USER = """\
Question: \"\"\"{question}\"\"\"

RAG chunks (retrieved context), numbered:
{rag_chunks_numbered}

Task: List key facts from the RAG that are relevant to evaluating this question. For each fact, include a brief verbatim quote from the chunks.

Respond with ONLY a strict JSON object:
{{
  "key_facts": [
    {{ "fact": "<one-sentence fact>", "quote": "<short verbatim quote from the RAG>" }},
    ...
  ]
}}
"""


def _extract_key_facts_from_rag(
    question: str,
    rag_chunks: list[str],
    model: str | None,
) -> list[dict[str, str]]:
    """
    Use the orchestrator's RAG to identify key facts (with quotes) relevant to the question.
    Returns list of {"fact": "...", "quote": "..."}; empty list if no chunks or parse failure.
    """
    if not rag_chunks:
        return []
    rag_numbered = "\n\n".join(
        f"[Chunk {i+1}]\n{chunk}" for i, chunk in enumerate(rag_chunks)
    )
    user = _KEY_FACTS_USER.format(question=question, rag_chunks_numbered=rag_numbered)
    raw = generate(user, system_prompt=_KEY_FACTS_SYSTEM, model=model, max_tokens=1500)
    try:
        data = json.loads(raw)
        items = data.get("key_facts") or []
        return [
            {"fact": str(x.get("fact", "")), "quote": str(x.get("quote", ""))}
            for x in items
            if isinstance(x, dict)
        ]
    except Exception:
        logger.warning("Key facts extraction returned non-JSON: %s", raw[:300])
        return []


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

Key facts from RAG (quoted), identified as relevant to the topic:
{key_facts_text}

RAG chunks (full text), numbered for reference:
{rag_chunks_numbered}

The following specialist agents each placed a bet on this question:
{agent_summaries}

Additional context (e.g. from search; may be none):
{web_snippets}

Available agents — id, name, description, and full system prompt (their specialization):
{agent_descriptions_with_prompts}

Tasks:
1. Provide an "overall_topic_reasoning" about what this topic/question is about.
2. Provide a single "context_for_agents": a summary for the selected agents that uses the key facts above (and their quotes) to explain how the RAG relates to the question. Weave in the quoted facts where relevant.
3. Identify ALL agents whose specialization is important for this question. For each, provide only "agent_id" and "choice_reasoning" (why this agent's expertise is needed).

Respond with ONLY a strict JSON object:
{{
  "overall_topic_reasoning": "<explanation>",
  "context_for_agents": "<summary using the key facts and quotes for the agents>",
  "relevant_agents": [
    {{ "agent_id": "<id>", "choice_reasoning": "<why this agent>" }}
  ]
}}
"""


def _identify_expertise_and_assign_rag(
    question: str,
    question_prompt: str,
    rag_chunks: list[str],
    bets: list[dict[str, Any]],
    web_snippets: list[str],
    key_facts: list[dict[str, str]],
    model: str | None,
) -> tuple[str, str, list[dict[str, Any]]]:
    """
    Return (topic_reasoning, context_for_agents, relevant_agents_list).
    context_for_agents: single shared context string for all agents.
    relevant_agents_list: list of dicts with {agent_id, choice_reasoning}.
    key_facts: list of {"fact", "quote"} from _extract_key_facts_from_rag.
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
    key_facts_text = "\n".join(
        f"- {item['fact']} (quote: \"{item['quote']}\")" for item in key_facts
    ) if key_facts else "(no key facts extracted)"

    user = _EXPERTISE_USER.format(
        question_prompt=question_prompt,
        question=question,
        key_facts_text=key_facts_text,
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
        context_for_agents = str(data.get("context_for_agents", ""))
        relevant_agents = data.get("relevant_agents") or []
        if not relevant_agents:
            relevant_agents = [{"agent_id": AGENTS[0].id, "choice_reasoning": "Default agent selection."}]
    except Exception:
        logger.warning("Expertise identification returned non-JSON: %s", raw)
        topic_reasoning = "Failed to parse orchestrator topic reasoning."
        context_for_agents = ""
        relevant_agents = [{"agent_id": AGENTS[0].id, "choice_reasoning": "Fallback due to parsing error."}]

    return topic_reasoning, context_for_agents, relevant_agents


def _run_single_agent_second_bet(
    agent_id: str,
    question: str,
    context_for_agent: str,
    model: str | None,
    question_embedding: list[float] | None = None,
) -> dict[str, Any]:
    """Run pipeline for one triggered agent: original RAG (agent's own) + orchestrator context as extra."""
    agent = get_agent(agent_id) or AGENTS[0]
    raw = run_pipeline(
        message=question,
        agent_id=agent_id,
        use_rag=True,
        model=model,
        additional_context=context_for_agent,
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
    }


def run_phase1(
    question: str,
    use_rag: bool = True,
    model: str | None = None,
    where_filter: dict | None = None,
) -> dict[str, Any]:
    """
    Phase 1: Same as /run but runs every agent with /run.
    For each agent, run the same pipeline as POST /run; collect responses as initial_bets.
    Phase 2 fetches its own RAG when invoked.
    """
    bets = _run_phase1_via_pipeline(question, use_rag=use_rag, model=model)
    return {
        "question": question,
        "initial_bets": bets,
    }


def run_orchestrated_phase2(
    question: str,
    initial_bets: list[dict[str, Any]],
    question_prompt: str | None = None,
    model: str | None = None,
    where_filter: dict | None = None,
) -> dict[str, Any]:
    """
    Phase 2 of the orchestrated pipeline:
    1. Fetches RAG (news) for the question.
    2. Extracts key facts (with quotes from RAG) relevant to the topic.
    3. Orchestrator produces context_for_agents (using those facts) and selects relevant agents.
    4. Runs each triggered agent with the same shared context; collects results.
    """
    bets = initial_bets
    q_prompt = question_prompt or QUESTION_PROMPT_PLACEHOLDER
    rag_chunks = retrieve_chunks(question, top_k=4, collection_name="news_rag", where_filter=where_filter)
    chunks = rag_chunks if rag_chunks else []

    key_facts = _extract_key_facts_from_rag(question, chunks, model)
    _debug_log(f"Phase 2: extracted {len(key_facts)} key facts from RAG.")

    topic_reasoning, context_for_agents, relevant_agents_info = _identify_expertise_and_assign_rag(
        question=question,
        question_prompt=q_prompt,
        rag_chunks=chunks,
        bets=bets,
        web_snippets=[],
        key_facts=key_facts,
        model=model,
    )

    q_emb = embed_text(question)
    _debug_log(f"Phase 2 processing: {len(relevant_agents_info)} relevant agents found.")
    triggered_agents: list[dict[str, Any]] = []
    for i, info in enumerate(relevant_agents_info):
        aid = info.get("agent_id")
        _debug_log(f"Triggering agent {i+1}/{len(relevant_agents_info)}: {aid}")
        choice_reasoning = info.get("choice_reasoning", "")

        bet = _run_single_agent_second_bet(
            agent_id=aid,
            question=question,
            context_for_agent=context_for_agents,
            model=model,
            question_embedding=q_emb,
        )
        triggered_agents.append({
            "agent_id": bet["agent_id"],
            "agent_name": bet["agent_name"],
            "choice_reasoning": choice_reasoning,
            "answer": bet["answer"],
            "confidence": bet["confidence"],
            "analysis": bet["reasoning"],
        })

    relevant_agents_with_rag = [
        {"agent_id": t["agent_id"], "agent_name": t["agent_name"], "expertise_rationale": t["choice_reasoning"]}
        for t in triggered_agents
    ]
    second_bets = [
        {"agent_id": t["agent_id"], "agent_name": t["agent_name"], "answer": t["answer"], "confidence": t["confidence"], "reasoning": t["analysis"]}
        for t in triggered_agents
    ]

    return {
        "topic_reasoning": topic_reasoning,
        "context_for_agents": context_for_agents,
        "triggered_agents": triggered_agents,
        "relevant_agents_with_rag": relevant_agents_with_rag,
        "second_bets": second_bets,
    }


def run_phase2_stream(
    question: str,
    initial_bets: list[dict[str, Any]],
    question_prompt: str | None = None,
    model: str | None = None,
    where_filter: dict | None = None,
) -> Iterator[dict[str, Any]]:
    """
    Phase 2 with SSE: fetches RAG, extracts key facts, orchestrator produces context_for_agents and selects agents;
    each makes a second bet (streamed); final phase2_complete with full result.
    Events: orchestrator_done, agent_second_bet_done (per relevant agent), phase2_complete.
    """
    q_prompt = question_prompt or QUESTION_PROMPT_PLACEHOLDER
    rag_chunks = retrieve_chunks(question, top_k=4, collection_name="news_rag", where_filter=where_filter)
    chunks = rag_chunks if rag_chunks else []

    key_facts = _extract_key_facts_from_rag(question, chunks, model)
    _debug_log(f"Phase 2: extracted {len(key_facts)} key facts from RAG.")

    topic_reasoning, context_for_agents, relevant_agents_info = _identify_expertise_and_assign_rag(
        question=question,
        question_prompt=q_prompt,
        rag_chunks=chunks,
        bets=initial_bets,
        web_snippets=[],
        key_facts=key_facts,
        model=model,
    )
    relevant_agents_with_rag = [
        {
            "agent_id": r["agent_id"],
            "agent_name": (get_agent(r["agent_id"]) or AGENTS[0]).name,
            "expertise_rationale": r.get("choice_reasoning", ""),
        }
        for r in relevant_agents_info
    ]

    q_emb = embed_text(question)

    yield {
        "event": "orchestrator_done",
        "topic_reasoning": topic_reasoning,
        "context_for_agents": context_for_agents,
        "relevant_agents_with_rag": relevant_agents_with_rag,
    }

    second_bets: list[dict[str, Any]] = []
    if relevant_agents_info:
        with ThreadPoolExecutor(max_workers=len(relevant_agents_info)) as executor:
            future_to_agent = {
                executor.submit(
                    _run_single_agent_second_bet,
                    info.get("agent_id"),
                    question,
                    context_for_agents,
                    model,
                    q_emb,
                ): info.get("agent_id")
                for info in relevant_agents_info
            }
            for future in as_completed(future_to_agent):
                bet = future.result()
                second_bets.append(bet)
                yield {"event": "agent_second_bet_done", "bet": bet}

    rationale_by_id = {r["agent_id"]: r.get("expertise_rationale", "") for r in relevant_agents_with_rag}
    triggered_agents = [
        {
            "agent_id": b["agent_id"],
            "agent_name": b["agent_name"],
            "choice_reasoning": rationale_by_id.get(b["agent_id"], ""),
            "answer": b["answer"],
            "confidence": b["confidence"],
            "analysis": b["reasoning"],
        }
        for b in second_bets
    ]
    result = {
        "topic_reasoning": topic_reasoning,
        "context_for_agents": context_for_agents,
        "triggered_agents": triggered_agents,
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
    # Phase 1 — initial bets
    phase1 = run_orchestrated_initial(question=question, use_rag=use_rag, model=model, where_filter=where_filter)
    _debug_log("Phase 1 complete.")

    # Phase 2 — fetches its own RAG; expertise selection + context assignment + second bets
    phase2 = run_orchestrated_phase2(
        question=question,
        initial_bets=phase1["initial_bets"],
        question_prompt=QUESTION_PROMPT_PLACEHOLDER,
        model=model,
        where_filter=where_filter,
    )

    return {**phase1, **phase2}
