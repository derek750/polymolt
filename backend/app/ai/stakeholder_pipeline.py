from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from app.config import CHAT_MODEL, GOOGLE_API_KEY, OPENAI_API_KEY
from app.ai.rag import retrieve
from app.ai.langflow_client import run_websearch_flow


logger = logging.getLogger(__name__)


@dataclass
class Stakeholder:
    name: str
    type: str
    description: str


@dataclass
class StakeholderAnalysis:
    stakeholder: Stakeholder
    search_query: str
    search_snippet: str
    reasoning: str


def _is_gemini_model(model: str) -> bool:
    return model.strip().lower().startswith("gemini-")


def _choose_model(model_override: Optional[str]) -> str:
    if model_override:
        return model_override.strip()
    return CHAT_MODEL


def _call_llm(prompt: str, model: Optional[str] = None, max_tokens: int = 1024) -> str:
    model_name = _choose_model(model)
    if _is_gemini_model(model_name):
        if not GOOGLE_API_KEY:
            return "Error: GOOGLE_API_KEY required for Gemini models."
        try:
            import google.generativeai as genai

            genai.configure(api_key=GOOGLE_API_KEY)
            gen_model = genai.GenerativeModel(model_name)
            response = gen_model.generate_content(prompt)
            if response.text:
                return response.text.strip()
            return "Error: No text in Gemini response."
        except Exception as e:
            logger.exception("Stakeholder pipeline Gemini call failed")
            return f"Error: {e!s}"
    else:
        if not OPENAI_API_KEY:
            return "Error: OPENAI_API_KEY required for OpenAI models."
        try:
            from openai import OpenAI

            client = OpenAI(api_key=OPENAI_API_KEY)
            r = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return (r.choices[0].message.content or "").strip()
        except Exception as e:
            logger.exception("Stakeholder pipeline LLM call failed")
            return f"Error: {e!s}"


def identify_stakeholders(
    message: str,
    context: Optional[str] = None,
    model: Optional[str] = None,
) -> List[Stakeholder]:
    system_prompt = (
        "You are a climate and sustainability analyst. "
        "Given the user's question, identify the key stakeholders affected by the issue. "
        "Stakeholders can be people, communities, companies, NGOs, governments, or ecosystems. "
        "Return ONLY a strict JSON array of objects with fields: "
        '"name", "type", and "description". Do not include any prose before or after the JSON.'
    )
    parts = [system_prompt, "\n\nUser question:\n", message]
    if context:
        parts.append("\n\nAdditional context:\n")
        parts.append(context)
    prompt = "".join(parts)

    raw = _call_llm(prompt, model=model, max_tokens=800)
    try:
        data = json.loads(raw)
    except Exception:
        logger.warning("Failed to parse stakeholders JSON; raw response: %s", raw)
        return []

    stakeholders: List[Stakeholder] = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            stype = str(item.get("type", "")).strip()
            desc = str(item.get("description", "")).strip()
            if name:
                stakeholders.append(Stakeholder(name=name, type=stype, description=desc))
    return stakeholders


def run_stakeholder_search(
    stakeholders: List[Stakeholder],
    message: str,
) -> List[StakeholderAnalysis]:
    analyses: List[StakeholderAnalysis] = []
    for s in stakeholders:
        search_query = f"{message} – impacts on {s.name} ({s.type})"
        snippet = run_websearch_flow(search_query, stakeholder_name=s.name)
        reasoning = (
            "Summary of websearch results relevant to this stakeholder based on Langflow output."
        )
        analyses.append(
            StakeholderAnalysis(
                stakeholder=s,
                search_query=search_query,
                search_snippet=snippet,
                reasoning=reasoning,
            )
        )
    return analyses


def summarize_analyses(
    message: str,
    analyses: List[StakeholderAnalysis],
    model: Optional[str] = None,
) -> str:
    if not analyses:
        return "No stakeholder-specific analyses were generated."

    system_prompt = (
        "You are a climate and sustainability analyst summarizing stakeholder-specific websearch results. "
        "Write a concise overview of the situation, highlighting key risks, opportunities, and trade-offs "
        "across stakeholders. Make the reasoning clear but keep the answer focused."
    )

    lines: List[str] = [system_prompt, "\n\nUser question:\n", message, "\n\nStakeholder findings:\n"]
    for a in analyses:
        lines.append(
            f"- Stakeholder: {a.stakeholder.name} ({a.stakeholder.type})\n"
            f"  Search query: {a.search_query}\n"
            f"  Websearch snippet: {a.search_snippet}\n"
        )
    prompt = "".join(lines)
    return _call_llm(prompt, model=model, max_tokens=800)


def run_stakeholder_websearch_pipeline(
    message: str,
    use_rag: bool = True,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    context = retrieve(message, top_k=4) if use_rag else ""
    stakeholders = identify_stakeholders(message=message, context=context or None, model=model)

    if not stakeholders:
        return {
            "message": message,
            "stakeholders": [],
            "combined_summary": (
                "No stakeholders could be reliably identified for this question. "
                "Try rephrasing the problem with more detail about who is affected."
            ),
            "details": [],
        }

    analyses = run_stakeholder_search(stakeholders=stakeholders, message=message)
    combined_summary = summarize_analyses(message=message, analyses=analyses, model=model)

    # Convert dataclasses into dicts shaped for WebsearchResponse
    result_stakeholders = [asdict(s) for s in stakeholders]
    result_details: List[Dict[str, Any]] = []
    for a in analyses:
        result_details.append(
            {
                "stakeholder": asdict(a.stakeholder),
                "search_query": a.search_query,
                "search_snippet": a.search_snippet,
                "reasoning": a.reasoning,
            }
        )

    return {
        "message": message,
        "stakeholders": result_stakeholders,
        "combined_summary": combined_summary,
        "details": result_details,
    }

