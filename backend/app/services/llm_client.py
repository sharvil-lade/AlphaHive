import logging
import re
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.token_budget_service import token_budget_service

logger = logging.getLogger("llm-client")

_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)


def _strip_json_fence(text: str) -> str:
    """Some models (Claude in particular) wrap JSON-mode output in a ```json ... ```
    markdown fence even when instructed to return JSON only — strip it so every
    json_mode caller can safely `json.loads()` the result."""
    match = _JSON_FENCE_RE.match(text)
    return match.group(1) if match else text


class LLMResult:
    def __init__(self, content: str, model_used: str, total_tokens: int = 0):
        self.content = content
        self.model_used = model_used
        self.total_tokens = total_tokens


class LLMClient:
    """Single entry point for every LLM call in the app, routed through the LiteLLM proxy.

    No call site should talk to a model provider directly. `complete()` tries the
    requested model (LLM_MODEL_PRIMARY by default, or `model=` to use a different
    tier — e.g. LLM_MODEL_SYNTHESIS for the final decision/report step) and retries
    once against LLM_MODEL_FALLBACK on any error; it returns None (never raises) if
    both fail or no proxy is configured, so callers fall through to their own
    deterministic local logic.
    """

    def __init__(self):
        self._client: AsyncOpenAI | None = None
        self._embeddings_disabled = False
        if settings.LITELLM_BASE_URL and settings.LITELLM_API_KEY:
            self._client = AsyncOpenAI(
                base_url=settings.LITELLM_BASE_URL,
                api_key=settings.LITELLM_API_KEY,
                # We already retry once via the primary -> fallback model chain below;
                # the SDK's own default retries (2) would silently triple every
                # per-call timeout, which is what caused real multi-minute hangs.
                max_retries=0,
            )

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    async def complete(
        self,
        messages: list[dict],
        *,
        json_mode: bool = False,
        session_id: str | None = None,
        timeout: float = 20.0,
        model: str | None = None,
    ) -> LLMResult | None:
        if not self._client:
            return None

        primary = model or settings.LLM_MODEL_PRIMARY
        for m in (primary, settings.LLM_MODEL_FALLBACK):
            if not m:
                continue
            try:
                kwargs = {
                    "model": m,
                    "messages": messages,
                    "temperature": 0.2,
                    "timeout": timeout,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = await self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                if json_mode:
                    content = _strip_json_fence(content)
                usage = response.usage
                total_tokens = usage.total_tokens if usage else 0

                if session_id and total_tokens:
                    await token_budget_service.track_usage(session_id, total_tokens)

                return LLMResult(content=content, model_used=m, total_tokens=total_tokens)
            except Exception as e:
                logger.error(f"LLM call failed for model={m}: {e}")
                continue

        return None

    async def embed(self, texts: list[str]) -> list[list[float]] | None:
        """Embed a batch of texts, or None if embeddings aren't available.

        Returns None (never raises) when no proxy or no EMBEDDING_MODEL is configured,
        and latches `_embeddings_disabled` on the first failure — many LiteLLM keys
        have no embedding-model access, and retrying just yields a 401 per chunk.
        Callers fall back to keyword search.
        """
        if not self._client or not settings.EMBEDDING_MODEL or self._embeddings_disabled:
            return None
        try:
            response = await self._client.embeddings.create(model=settings.EMBEDDING_MODEL, input=texts)
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.warning(
                f"Embedding model '{settings.EMBEDDING_MODEL}' unavailable ({e}); "
                "falling back to keyword search for the rest of this process."
            )
            self._embeddings_disabled = True
            return None

    async def stream(
        self,
        messages: list[dict],
        *,
        session_id: str | None = None,
        timeout: float = 60.0,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Streams text deltas from the requested model (LLM_MODEL_PRIMARY by default,
        or `model=` for a different tier, e.g. LLM_MODEL_SYNTHESIS) only.

        Once tokens have reached the client, switching models mid-stream would
        produce a garbled response, so there is no mid-stream fallback. If the
        primary errors out before yielding anything, falls back to a single
        non-streamed call (via `complete`, which tries the fallback model) and
        yields its full text as one chunk.
        """
        if not self._client:
            return

        primary = model or settings.LLM_MODEL_PRIMARY
        try:
            response_stream = await self._client.chat.completions.create(
                model=primary,
                messages=messages,
                temperature=0.2,
                timeout=timeout,
                stream=True,
                stream_options={"include_usage": True},
            )
            total_tokens = 0
            yielded_any = False
            async for chunk in response_stream:
                if chunk.usage:
                    total_tokens = chunk.usage.total_tokens
                if chunk.choices and chunk.choices[0].delta.content:
                    yielded_any = True
                    yield chunk.choices[0].delta.content

            if session_id and total_tokens:
                await token_budget_service.track_usage(session_id, total_tokens)
            if yielded_any:
                return
        except Exception as e:
            logger.error(f"LLM stream failed for model={primary}: {e}")

        result = await self.complete(messages, session_id=session_id, timeout=timeout)
        if result and result.content:
            yield result.content


llm_client = LLMClient()
