"""Bet sizing utilities based on agent system prompts and response relevance.

This module computes a bet size for each agent based on:
1. The length of its system prompt (base size).
2. Cosine similarity between system prompt and question.
3. Cosine similarity between agent response and question.

The final effective bet is multiplicative:
effective_bet = max_bet * prompt_similarity * response_similarity
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

import tiktoken

from app.agents.config import AgentConfig, AGENTS
from app.ai.rag import embed

# Bet sizing constants
BASE_BET: int = 100
MAX_BET: int = 1000
BASELINE: int = 200


_ENCODING = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    """Return the token count for the given text using cl100k_base."""
    if not text:
        return 0
    return len(_ENCODING.encode(text))


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not vec1 or not vec2:
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def get_bet_for_agent(
    agent: AgentConfig,
    question_prompt: Optional[str] = None,
    response_text: Optional[str] = None,
    question_embedding: Optional[List[float]] = None,
) -> Dict[str, float]:
    """Compute bet sizing info for a single agent.

    Returns a dict with keys:
    - agent_id: the agent's id
    - token_count: number of tokens in system_prompt
    - max_bet: the computed maximum bet size based on length
    - prompt_similarity: cosine similarity between system_prompt and question
    - response_similarity: cosine similarity between response and question
    - effective_bet: the final bet size
    """
    # 1. Length-based max bet
    token_count = _count_tokens(agent.system_prompt)
    if token_count <= 0:
        max_bet = 0.0
    else:
        max_bet = min(
            BASE_BET * math.log1p(token_count / BASELINE),
            float(MAX_BET),
        )

    # 2. Similarities
    prompt_similarity = 0.0
    response_similarity = 0.0

    if question_prompt:
        # Use provided embedding or compute it
        q_emb = question_embedding if question_embedding else embed(question_prompt)
        
        if q_emb:
            # System prompt similarity
            if agent.system_prompt:
                sys_emb = embed(agent.system_prompt)
                prompt_similarity = _cosine_similarity(sys_emb, q_emb)
            
            # Response similarity
            if response_text:
                resp_emb = embed(response_text)
                response_similarity = _cosine_similarity(resp_emb, q_emb)

    # 3. Multiplicative combination
    # We clamp similarities to [0, 1] just in case, though cosine is [-1, 1] usually.
    # For bet sizing, negative similarity should probably be 0.
    p_sim = max(0.0, prompt_similarity)
    r_sim = max(0.0, response_similarity)
    
    effective_bet = max_bet * p_sim * r_sim

    return {
        "agent_id": agent.id,
        "token_count": token_count,
        "max_bet": max_bet,
        "prompt_similarity": prompt_similarity,
        "response_similarity": response_similarity,
        "effective_bet": effective_bet,
    }


def compute_confidence(bet_info: Dict[str, float]) -> int:
    """Convert bet-sizing info into a 0-100 confidence score.

    Weighted average of prompt_similarity (40%) and response_similarity (60%)
    so that response relevance has more influence than expertise match alone.
    """
    p_sim = max(0.0, bet_info.get("prompt_similarity", 0.0))
    r_sim = max(0.0, bet_info.get("response_similarity", 0.0))
    raw = p_sim * 0.4 + r_sim * 0.6
    return min(100, round(raw * 100))


def get_all_bets(question_prompt: Optional[str] = None) -> List[Dict[str, float]]:
    """Compute bet sizing info for all agents in AGENTS.

    Returns a list of dicts sorted by effective_bet descending.
    Note: Without response_text, response_similarity will be 0.
    """
    # Pre-compute question embedding if possible
    q_emb = embed(question_prompt) if question_prompt else None
    
    bets = [
        get_bet_for_agent(
            agent, 
            question_prompt=question_prompt, 
            question_embedding=q_emb
        ) 
        for agent in AGENTS
    ]
    bets.sort(key=lambda b: b["effective_bet"], reverse=True)
    return bets