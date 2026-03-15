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

def _debug_log(msg: str):
    with open("c:/Users/tteth/Downloads/polymolt/polymolt/backend/debug_orchestrator.txt", "a", encoding="utf-8") as f:
        f.write(f"{msg}\n")

# Placeholder for the question prompt until a real one is wired in.
QUESTION_PROMPT_PLACEHOLDER = "[Placeholder: question prompt for the prediction market]"
from app.agents.config import AGENTS, get_agent, AgentConfig

logger = logging.getLogger(__name__)


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
    bets = []
    for i, agent in enumerate(AGENTS):
        _debug_log(f"Phase 1: Agent {i+1}/{len(AGENTS)} betting: {agent.id}")
        bets.append(_run_single_bet(question, agent, context, model))
    return bets


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
    "You are an orchestrator for a prediction market focused on evaluating Toronto locations (hospitals, nurseries, attractions). "
    "You have RAG context (retrieved news/reviews), a question, and specialist agents with system prompts. "
    "Your job: (1) Read the RAG chunks and each agent's specialization (system prompt + description). "
    "(2) List every agent whose specialization is relevant to evaluating this location/claim; for each such agent, "
    "select the most relevant part(s) of the RAG and provide that as the context to give that agent. "
    "Use the specialist agents' bets and web research to inform your choices to mitigate asymmetric information."
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


# ── Phase 2d: Deep analysis ─────────────────────────────────────────────

_DEEP_SYSTEM = (
    "You are {agent_name}. {system_prompt} "
    "You have been selected as the most qualified analyst for this question."
)

_DEEP_USER = """\
A prediction market is evaluating a claim about a Toronto location (e.g., hospital, nursery, attraction) to mitigate asymmetric information:

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


def _parse_agent_analysis(raw_analysis: str) -> tuple[str, int, str]:
    """Parse the agent's final deep analysis to extract Answer and Confidence."""
    answer = "UNKNOWN"
    confidence = 0
    clean_analysis = raw_analysis.strip()
    
    # Try to find "Answer: Yes/No" at the end
    lines = [line.strip() for line in clean_analysis.split("\n") if line.strip()]
    if lines:
        last_line = lines[-1].lower()
        if "answer: yes" in last_line:
            answer = "YES"
        elif "answer: no" in last_line:
            answer = "NO"
            
    # Heuristic for confidence: looking for "confidence: X%" or similar
    # (Optional: the prompt asks for it, but for now we'll keep it simple or look for numbers)
    import re
    conf_match = re.search(r"confidence:\s*(\d+)", clean_analysis.lower())
    if conf_match:
        confidence = int(conf_match.group(1))
    elif answer != "UNKNOWN":
        confidence = 70  # Default if they gave an answer but no clear confidence
        
    return answer, confidence, clean_analysis


def _run_deep_analysis(
    question: str,
    agent_id: str,
    bets: list[dict[str, Any]],
    web_snippets: list[str],
    context: str,
    model: str | None,
) -> tuple[str, int, str]:
    """Returns (answer, confidence, analysis_text)."""
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
    raw = generate(user, system_prompt=system, model=agent.model or model, max_tokens=1024)
    answer, confidence, clean_analysis = _parse_agent_analysis(raw)
    # Add visual RAG indicator to analysis text
    if context:
        header = "🟢 [ORCHESTRATOR: RAG CONTEXT ACTIVE]\n" + "="*40 + "\n"
    else:
        header = "🔴 [ORCHESTRATOR: NO RAG CONTEXT FOUND]\n" + "="*40 + "\n"
    analysis = f"{header}{clean_analysis}"
    return answer, confidence, analysis


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
    where_filter: dict | None = None,
) -> dict[str, Any]:
    """
    Phase 1 (legacy): RAG + internal bet prompt per agent + web scrape.
    Use run_phase1 for "same as /run per agent".
    """
    if use_rag:
        rag_chunks = retrieve_chunks(question, top_k=4, where_filter=where_filter)
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

    _debug_log(f"Phase 2 processing: {len(relevant_agents_info)} relevant agents found.")
    triggered_agents: list[dict[str, Any]] = []
    for i, info in enumerate(relevant_agents_info):
        aid = info.get("agent_id")
        _debug_log(f"Triggering agent {i+1}/{len(relevant_agents_info)}: {aid}")
        reasoning = info.get("choice_reasoning", "")
        agent_specific_rag = info.get("rag_context_for_agent", "") or rag_context

        agent_obj = get_agent(aid) or AGENTS[0]

        ans, conf, analysis = _run_deep_analysis(
            question=question,
            agent_id=agent_obj.id,
            bets=bets,
            web_snippets=web_snippets,
            context=agent_specific_rag,
            model=model,
        )

        triggered_agents.append({
            "agent_id": agent_obj.id,
            "agent_name": agent_obj.name,
            "choice_reasoning": reasoning,
            "context": agent_specific_rag,
            "answer": ans,
            "confidence": conf,
            "analysis": analysis,
        })

    # Legacy / Phase2Response: primary = first triggered agent
    primary = triggered_agents[0] if triggered_agents else {
        "agent_id": "none", "agent_name": "None", "choice_reasoning": "None",
        "context": "", "answer": "UNKNOWN", "confidence": 0, "analysis": "No agents triggered.",
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
        "deep_analysis": primary["analysis"],
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
                ): aid
                for aid, ctx in agent_rag_map.items()
            }
            for future in as_completed(future_to_agent):
                bet = future.result()
                second_bets.append(bet)
                yield {"event": "agent_second_bet_done", "bet": bet}

    agent_specific_rag = agent_rag_map.get(assigned_id) or rag_context
    _ans, _conf, analysis = _run_deep_analysis(
        question=question,
        agent_id=assigned_id,
        bets=initial_bets,
        web_snippets=web_snippets,
        context=agent_specific_rag,
        model=model,
    )
    yield {"event": "deep_analysis_done", "deep_analysis": analysis}

    result = {
        "topic_reasoning": topic_reasoning,
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
    where_filter: dict | None = None,
) -> dict[str, Any]:
    """
    Full orchestrated pipeline:
    1. All agents place an initial bet.
    2. Orchestrator collects reasons, web-scrapes, identifies expertise,
       assigns the best agent for a deep analysis.
    """
    _debug_log(f"Starting pipeline for question: {question}")
    # Phase 1 — initial bets + RAG + web scrape
    phase1 = run_orchestrated_initial(question=question, use_rag=use_rag, model=model, where_filter=where_filter)
    _debug_log("Phase 1 complete.")
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
