"""LangChain chat-model factory for the tool-calling agents.

The rest of the app talks to the LiteLLM proxy through the raw `openai` client
(`services/llm_client.py`) for plain completion + token-streaming. The *agents*,
however, need a LangChain `BaseChatModel` that supports `.bind_tools()` so that
`langgraph.prebuilt.create_react_agent` can drive a real tool-calling loop.

`ChatOpenAI` pointed at the LiteLLM proxy gives us exactly that: LiteLLM normalizes
function/tool calling across providers, so the same react agent works whether the
underlying model is Gemini, Claude, or GPT — swap it via env vars, no code change.
"""

import logging

from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = logging.getLogger("agent-llm")


def is_agent_llm_configured() -> bool:
    """Agents need a real tool-calling model; without a proxy they can't run."""
    return bool(settings.LITELLM_BASE_URL and settings.LITELLM_API_KEY)


def get_chat_model(
    model: str | None = None,
    *,
    temperature: float = 0.1,
    timeout: float = 60.0,
) -> ChatOpenAI:
    """Build a LiteLLM-backed chat model for a tool-calling agent.

    `model` defaults to `LLM_MODEL_PRIMARY` (the fast tier the specialist slaves
    run on); pass `LLM_MODEL_SYNTHESIS` for the master's heavier reasoning.
    """
    return ChatOpenAI(
        base_url=settings.LITELLM_BASE_URL,
        api_key=settings.LITELLM_API_KEY,
        model=model or settings.LLM_MODEL_PRIMARY,
        temperature=temperature,
        timeout=timeout,
        max_retries=0,
    )
