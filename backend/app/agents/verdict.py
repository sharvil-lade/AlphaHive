import json
import logging
from typing import Any, Dict, Optional

from app.services.llm_client import llm_client

logger = logging.getLogger("agent-verdict")

DEFAULT_RATING = "NEUTRAL"


async def get_agent_verdict(
    role: str,
    data_summary: str,
    rating_options: str,
    session_id: Optional[str] = None,
    anchor_rating: Optional[str] = None,
) -> Dict[str, Any]:
    """Ask the LLM to act as an independent specialist analyst and produce a short,
    structured verdict from the data the calling node already gathered.

    This is what turns a specialist node from a pure data-fetcher/calculator into a
    genuine reasoning agent: it doesn't just report numbers, it forms and explains
    an opinion on them, which `synthesis.py` then weighs against the other three
    agents' independent opinions instead of narrating raw numbers alone.

    Never raises — returns a deterministic neutral verdict if the LLM is
    unreachable or unconfigured, so callers can merge the result in unconditionally.
    """
    if not llm_client.is_configured:
        return {
            "rating": anchor_rating or DEFAULT_RATING,
            "confidence": 50,
            "rationale": "LLM not configured — no independent agent read available.",
        }

    anchor_note = (
        f' A quantitative rating of "{anchor_rating}" has already been computed from the raw data — '
        "you may agree or add nuance, but do not contradict it outright."
        if anchor_rating
        else ""
    )

    prompt = (
        f"You are {role}, an independent specialist analyst on a stock research team. "
        f"Based only on the data below, give your professional read.{anchor_note}\n\n"
        f"Data:\n{data_summary}\n\n"
        "Respond with JSON only:\n"
        f'{{"rating": {rating_options}, "confidence": <integer 0-100>, '
        '"rationale": "<1-2 sentence professional rationale>"}'
    )

    result = await llm_client.complete(
        messages=[
            {"role": "system", "content": f"You are {role}. Return strictly valid JSON."},
            {"role": "user", "content": prompt},
        ],
        json_mode=True,
        session_id=session_id,
        timeout=12.0,
    )
    if not result:
        return {
            "rating": anchor_rating or DEFAULT_RATING,
            "confidence": 50,
            "rationale": "Independent agent read unavailable — LLM call failed.",
        }

    try:
        parsed = json.loads(result.content)
        return {
            "rating": str(parsed.get("rating", anchor_rating or DEFAULT_RATING)).upper(),
            "confidence": int(parsed.get("confidence", 50)),
            "rationale": str(parsed.get("rationale", "")),
        }
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.error(f"Failed to parse {role} verdict: {e}")
        return {
            "rating": anchor_rating or DEFAULT_RATING,
            "confidence": 50,
            "rationale": "Could not parse independent agent verdict.",
        }
