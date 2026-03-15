"""Market simulation — agents bet YES/NO on a question to derive fair value.

Each agent is asked the user's question and votes YES or NO with reasoning.
Bet sizing (max_bet, relevance) comes entirely from bet_sizing.py.
Fair value = sum(effective_bet for YES voters) / sum(effective_bet for all voters).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.config import CHAT_MODEL, GOOGLE_API_KEY, OPENAI_API_KEY
from app.ai.rag import retrieve, embed
from app.ai.bet_sizing import get_bet_for_agent
from app.agents.config import AgentConfig, AGENTS

logger = logging.getLogger(__name__)


def _is_gemini_model(model: str) -> bool:
    return model.strip().lower().startswith("gemini-")


def _choose_model(agent: AgentConfig, model_override: Optional[str]) -> str:
    if model_override:
        return model_override.strip()
    if agent.model:
        return agent.model
    return CHAT_MODEL


def _call_llm(prompt: str, model: str, max_tokens: int = 512) -> str:
    if _is_gemini_model(model):
        if not GOOGLE_API_KEY:
            return "Error: GOOGLE_API_KEY required for Gemini models."
        try:
            import google.generativeai as genai

            genai.configure(api_key=GOOGLE_API_KEY)
            response = genai.GenerativeModel(model).generate_content(prompt)
            if response.text:
                return response.text.strip()
            return "Error: No text in Gemini response."
        except Exception as e:
            logger.exception("Market simulation Gemini call failed")
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
            logger.exception("Market simulation OpenAI call failed")
            return f"Error: {e!s}"


def _parse_vote(raw: str) -> Dict[str, str]:
    """Extract vote and reasoning from an LLM response.

    Tries JSON first, then falls back to keyword detection.
    """
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").removeprefix("json").strip()

    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            vote = str(data.get("vote", "")).upper().strip()
            reasoning = str(data.get("reasoning", "")).strip()
            if vote in ("YES", "NO"):
                return {"vote": vote, "reasoning": reasoning}
    except (json.JSONDecodeError, ValueError):
        pass

    upper = raw.upper()
    if "YES" in upper:
        return {"vote": "YES", "reasoning": raw.strip()}
    if "NO" in upper:
        return {"vote": "NO", "reasoning": raw.strip()}

    return {"vote": "NO", "reasoning": raw.strip()}


def _ask_agent_vote(
    agent: AgentConfig,
    question: str,
    context: str,
    model_override: Optional[str] = None,
) -> Dict[str, str]:
    """Ask a single agent to vote YES or NO on the question."""
    model = _choose_model(agent, model_override)

    context_block = (
        f"\n\nContext (from RAG):\n{context}\n"
        if context
        else "\n\n(No RAG context loaded.)\n"
    )

    prompt = (
        f"{agent.system_prompt}\n"
        f"{context_block}\n"
        f"Question: {question}\n\n"
        "You must vote YES or NO on the question above. "
        "Return ONLY strict JSON with two fields:\n"
        '  "vote": "YES" or "NO"\n'
        '  "reasoning": a brief explanation for your vote\n'
        "Do not include any text outside the JSON object."
    )

    raw = _call_llm(prompt, model=model, max_tokens=512)
    return _parse_vote(raw)


def run_market_simulation(
    question: str,
    use_rag: bool = True,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the full market simulation and return the fair value.

    1. Optionally retrieve RAG context (shared across agents).
    2. Each agent votes YES/NO with reasoning.
    3. Bet sizing from bet_sizing.py provides max_bet and relevance per agent.
    4. effective_bet = max_bet * relevance.
    5. fair_value = sum(YES effective_bets) / sum(all effective_bets).
    """
    context = retrieve(question, top_k=4) if use_rag else ""

    # Pre-compute question embedding for efficiency
    q_emb = embed(question)

    agent_votes: List[Dict[str, Any]] = []
    yes_total = 0.0
    all_total = 0.0

    for agent in AGENTS:
        vote_result = _ask_agent_vote(agent, question, context, model_override=model)
        sizing = get_bet_for_agent(
            agent, 
            question_prompt=question, 
            response_text=vote_result["reasoning"],
            question_embedding=q_emb
        )

        max_bet = sizing["max_bet"]
        prompt_sim = sizing["prompt_similarity"]
        response_sim = sizing["response_similarity"]
        effective_bet = sizing["effective_bet"]

        if vote_result["vote"] == "YES":
            yes_total += effective_bet
        all_total += effective_bet

        agent_votes.append({
            "agent_id": agent.id,
            "agent_name": agent.name,
            "vote": vote_result["vote"],
            "max_bet": round(max_bet, 2),
            "prompt_similarity": round(prompt_sim, 4),
            "response_similarity": round(response_sim, 4),
            "effective_bet": round(effective_bet, 2),
            "reasoning": vote_result["reasoning"],
        })

    fair_value = (yes_total / all_total) if all_total > 0 else 0.5

    return {
        "question": question,
        "fair_value": round(fair_value, 4),
        "agent_votes": agent_votes,
    }