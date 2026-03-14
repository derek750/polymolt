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
from dataclasses import asdict
from typing import Any

from app.config import CHAT_MODEL, OPENAI_API_KEY, GOOGLE_API_KEY
from app.ai.rag import retrieve
from app.ai.web_scraper import scrape_web
from app.agents.config import AGENTS, get_agent, AgentConfig

logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────

def _is_gemini(model: str) -> bool:
    return model.strip().lower().startswith("gemini-")


def _call_llm(prompt: str, model: str | None = None, max_tokens: int = 1024) -> str:
    """Thin wrapper that routes to OpenAI or Gemini."""
    model = (model or CHAT_MODEL).strip()

    if _is_gemini(model):
        if not GOOGLE_API_KEY:
            return "Error: GOOGLE_API_KEY required for Gemini models."
        try:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            gen = genai.GenerativeModel(model)
            resp = gen.generate_content(prompt)
            return (resp.text or "").strip()
        except Exception as e:
            logger.exception("Orchestrator Gemini call failed")
            return f"Error: {e!s}"
    else:
        if not OPENAI_API_KEY:
            return "Error: OPENAI_API_KEY required for OpenAI models."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return (r.choices[0].message.content or "").strip()
        except Exception as e:
            logger.exception("Orchestrator OpenAI call failed")
            return f"Error: {e!s}"


# ── Phase 1: Initial bets ───────────────────────────────────────────────

_BET_PROMPT = """\
You are {agent_name}. {system_prompt}

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
    prompt = _BET_PROMPT.format(
        agent_name=agent.name,
        system_prompt=agent.system_prompt,
        question=question,
        context_block=ctx,
    )
    raw = _call_llm(prompt, model=agent.model or model, max_tokens=300)

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

_EXPERTISE_PROMPT = """\
You are an orchestrator for a sustainability prediction market.

Question: \"\"\"{question}\"\"\"

The following specialist agents each placed a bet on this question:
{agent_summaries}

Web research snippets:
{web_snippets}

Available agents and their expertise:
{agent_descriptions}

Based on the question, the agents' reasoning, and the web research,
decide which single agent is best suited to perform a deeper analysis.

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

    prompt = _EXPERTISE_PROMPT.format(
        question=question,
        agent_summaries=agent_summaries,
        web_snippets=snippets_text,
        agent_descriptions=agent_descriptions,
    )
    raw = _call_llm(prompt, model=model, max_tokens=300)

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

_DEEP_ANALYSIS_PROMPT = """\
You are {agent_name}. {system_prompt}

A prediction market is evaluating the question:

\"\"\"{question}\"\"\"

Other analysts placed the following bets:
{other_bets}

Relevant web research:
{web_snippets}

{context_block}

You have been selected as the most qualified analyst for this question.
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

    prompt = _DEEP_ANALYSIS_PROMPT.format(
        agent_name=agent.name,
        system_prompt=agent.system_prompt,
        question=question,
        other_bets=other_bets,
        web_snippets=snippets_text,
        context_block=ctx,
    )
    return _call_llm(prompt, model=agent.model or model, max_tokens=1024)


# ── Public entry point ───────────────────────────────────────────────────

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
    # RAG context (shared across all agents)
    context = retrieve(question, top_k=4) if use_rag else ""

    # Phase 1 — initial bets
    bets = _run_all_bets(question, context, model)

    # Phase 2a-b — web scrape (pure Python)
    scrape = scrape_web(question)

    # Phase 2c — identify expertise & assign agent
    assigned_id, rationale = _identify_expertise(
        question, bets, scrape.snippets, model,
    )
    assigned_agent = get_agent(assigned_id) or AGENTS[0]

    # Phase 2d — deep analysis by the assigned agent
    analysis = _run_deep_analysis(
        question, assigned_id, bets, scrape.snippets, context, model,
    )

    return {
        "question": question,
        "initial_bets": bets,
        "web_scrape_snippets": scrape.snippets,
        "assigned_agent_id": assigned_agent.id,
        "assigned_agent_name": assigned_agent.name,
        "expertise_rationale": rationale,
        "deep_analysis": analysis,
    }
