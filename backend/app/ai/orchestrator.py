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
from typing import Any

from app.models import generate
from app.ai.rag import retrieve
from app.ai.web_scraper import scrape_web
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


# ── Phase 2: Orchestrator ───────────────────────────────────────────────

_EXPERTISE_SYSTEM = (
    "You are an orchestrator for a sustainability prediction market. "
    "Your job is to read the specialist agents' bets and the web research, "
    "then assign the single best-qualified agent for deeper analysis."
)

_EXPERTISE_USER = """\
Question: \"\"\"{question}\"\"\"

The following specialist agents each placed a bet on this question:
{agent_summaries}

Web research snippets:
{web_snippets}

Available agents and their expertise:
{agent_descriptions}

Decide which single agent is best suited to perform a deeper analysis.

Respond with ONLY a strict JSON object:
{{
  "assigned_agent_id": "<agent id>",
  "rationale": "<1-2 sentence explanation of why this expertise fits>"
}}
"""


def _identify_expertise(
    question: str,
    bets: list[dict[str, Any]],
    web_snippets: list[str],
    model: str | None,
) -> tuple[str, str]:
    """Return (agent_id, rationale) for the best-fit agent."""
    agent_summaries = "\n".join(
        f"- {b['agent_name']} ({b['agent_id']}): {b['answer']} "
        f"(confidence {b['confidence']}%) — {b['reasoning']}"
        for b in bets
    )
    agent_descriptions = "\n".join(
        f"- {a.id}: {a.name} — {a.description}" for a in AGENTS
    )
    snippets_text = "\n".join(web_snippets) if web_snippets else "(none)"

    user = _EXPERTISE_USER.format(
        question=question,
        agent_summaries=agent_summaries,
        web_snippets=snippets_text,
        agent_descriptions=agent_descriptions,
    )
    raw = generate(user, system_prompt=_EXPERTISE_SYSTEM, model=model, max_tokens=300)

    try:
        data = json.loads(raw)
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

    return agent_id, rationale


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
    return generate(user, system_prompt=system, model=agent.model or model, max_tokens=1024)


# ── Public entry points ─────────────────────────────────────────────────

def run_orchestrated_initial(
    question: str,
    use_rag: bool = True,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Phase 1 of the orchestrated pipeline:
    1. Optional RAG retrieval (shared context).
    2. All agents place an initial bet.
    3. Web scraping for additional non-AI context.
    """
    context = retrieve(question, top_k=4) if use_rag else ""
    bets = _run_all_bets(question, context, model)
    scrape = scrape_web(question)

    return {
        "question": question,
        "initial_bets": bets,
        "web_scrape_snippets": scrape.snippets,
        "rag_context": context,
    }


def run_orchestrated_phase2(
    question: str,
    initial_bets: list[dict[str, Any]],
    web_scrape_snippets: list[str],
    rag_context: str,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Phase 2 of the orchestrated pipeline:
    1. Orchestrator reads the initial bets + web data.
    2. Identifies the best-fit expert agent.
    3. That agent performs a deep analysis.
    """
    bets = initial_bets
    web_snippets = web_scrape_snippets
    context = rag_context

    assigned_id, rationale = _identify_expertise(
        question, bets, web_snippets, model,
    )
    assigned_agent = get_agent(assigned_id) or AGENTS[0]

    analysis = _run_deep_analysis(
        question, assigned_id, bets, web_snippets, context, model,
    )

    return {
        "assigned_agent_id": assigned_agent.id,
        "assigned_agent_name": assigned_agent.name,
        "expertise_rationale": rationale,
        "deep_analysis": analysis,
    }


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

    # Phase 2 — expertise selection + deep analysis
    phase2 = run_orchestrated_phase2(
        question=question,
        initial_bets=bets,
        web_scrape_snippets=web_snippets,
        rag_context=context,
        model=model,
    )

    return {**phase1, **phase2}
