import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.utils import emit_chat_event, get_redis, redis_available
from app.core.deps import (
    Principal,
    get_principal,
    owned_conversation,
    owned_message,
    require_principal,
)
from app.core.rate_limiter import limit_10_per_min
from app.db.session import get_db
from app.models.models import Conversation, Message
from app.schemas.schemas import (
    ChatMessageCreate,
    ChatMessageCreateResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationSchema,
    ConversationUpdate,
)
from app.services.chat_service import chat_service

router = APIRouter()
logger = logging.getLogger("chat-api")

# In-flight runs by assistant message id. Holding the task handle (rather than using
# BackgroundTasks) is what lets /stop actually cancel the next LLM call.
_running_runs: dict[UUID, asyncio.Task] = {}


async def _persist_run_artifacts(message_id: UUID) -> None:
    """Snapshot the ephemeral Redis event stream into Postgres: each node's final
    status and each specialist's verdict, so both survive a page reload."""
    try:
        redis = get_redis()
        raw_events = await redis.lrange(f"chat_events:{message_id}", 0, -1)

        node_status: dict[str, str] = {}
        verdicts: dict[str, dict] = {}
        for raw in raw_events:
            try:
                event = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            if event.get("type") == "agent-status":
                node_status[event["node"]] = event["status"]
            elif event.get("type") == "agent-verdict":
                verdicts[event["node"]] = event

        for node, node_final_status in node_status.items():
            verdict = verdicts.get(node, {})
            await chat_service.record_trace(
                message_id,
                node=node,
                status=node_final_status,
                summary=verdict.get("rationale"),
                label=verdict.get("label"),
                rating=verdict.get("rating"),
                confidence=verdict.get("confidence"),
            )
    except Exception as e:
        logger.error(f"Failed to persist agent traces for message {message_id}: {e}")


async def _load_portfolio_context(session_id: str) -> str:
    """Best-effort: build the portfolio summary the agents get as context."""
    try:
        from app.db.session import AsyncSessionLocal
        from app.services.portfolio_service import portfolio_service

        async with AsyncSessionLocal() as db:
            return await portfolio_service.build_context_text(db, session_id)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to load portfolio context for session {session_id}: {e}")
        return "The user's portfolio could not be loaded."


async def execute_chat_workflow(assistant_message_id: UUID, session_id: str, query: str) -> None:
    """Run the chat LangGraph state machine for one turn."""
    try:
        from app.agents.graph import chat_graph

        portfolio_context = await _load_portfolio_context(session_id)

        initial_state = {
            "session_id": session_id,
            "ticker": "",
            "run_id": str(assistant_message_id),
            "status": "running",
            "quotes": {},
            "indicators": {},
            "sentiment": {},
            "sec_context": [],
            "risk_metrics": {},
            "decision": {},
            "logs": [],
            "query": query,
            "message_id": str(assistant_message_id),
            "market": "IN",
            "intent": "general_question",
            "needs_agents": False,
            "tickers": [],
            "selected_agents": [],
            "portfolio_review": False,
            "portfolio_context": portfolio_context,
            "findings": [],
        }
        result = await chat_graph.ainvoke(initial_state)
        content = (result.get("decision") or {}).get("content_markdown", "")
        if not content:
            content = "Sorry, I couldn't generate a response for that. Please try rephrasing your question."
        await chat_service.update_message(assistant_message_id, content=content, status="completed")
        await emit_chat_event(
            assistant_message_id, {"type": "done", "status": "completed", "content": content}
        )
    except asyncio.CancelledError:
        # User pressed Stop. Keep whatever text already streamed rather than blanking it.
        existing = await chat_service.get_message(assistant_message_id)
        content = (existing.content if existing else "") or "_Stopped._"
        await chat_service.update_message(assistant_message_id, content=content, status="cancelled")
        await emit_chat_event(
            assistant_message_id, {"type": "done", "status": "cancelled", "content": content}
        )
        raise
    except Exception as e:
        logger.error(f"Error executing chat workflow for message {assistant_message_id}: {e}")
        content = "Sorry, something went wrong while processing your request."
        await chat_service.update_message(assistant_message_id, content=content, status="failed")
        await emit_chat_event(assistant_message_id, {"type": "done", "status": "failed", "content": content})
    finally:
        await _persist_run_artifacts(assistant_message_id)
        _running_runs.pop(assistant_message_id, None)


@router.post("/conversations", response_model=ConversationSchema, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    principal: Principal = Depends(get_principal),
):
    """Create a conversation owned by the caller's session."""
    return await chat_service.create_conversation(principal.session_id, payload.title)


@router.get("/conversations", response_model=list[ConversationSchema])
async def list_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    principal: Principal = Depends(get_principal),
):
    """List the caller's conversations, most recently updated first."""
    return await chat_service.list_conversations(principal.session_id, limit=limit, offset=offset)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conv: Conversation = Depends(owned_conversation)):
    """A conversation's message history, including persisted agent traces."""
    detail = await chat_service.get_conversation(conv.id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return detail


@router.patch("/conversations/{conversation_id}", response_model=ConversationSchema)
async def rename_conversation(
    payload: ConversationUpdate,
    conv: Conversation = Depends(owned_conversation),
    db: AsyncSession = Depends(get_db),
):
    """Rename a conversation."""
    conv.title = payload.title.strip()
    await db.commit()
    return conv


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conv: Conversation = Depends(owned_conversation),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and everything under it (messages, traces cascade)."""
    await db.delete(conv)
    await db.commit()


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageCreateResponse,
    status_code=status.HTTP_201_CREATED,
    # Spends real LLM budget, so tighter than the router's 60/min default.
    dependencies=[Depends(limit_10_per_min)],
)
async def post_message(
    payload: ChatMessageCreate,
    conv: Conversation = Depends(owned_conversation),
):
    """Post a user message and kick off the chat graph, returning immediately — the
    client then opens the SSE stream for the assistant message to watch live agent
    status and streamed response text."""
    # Without Redis the run would start, stream nowhere, and leave the client
    # spinning forever. A clear error beats an infinite "Thinking…".
    if not await redis_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat is temporarily unavailable. Please try again in a moment.",
        )

    from app.services.token_budget_service import token_budget_service

    if not await token_budget_service.check_budget(conv.session_id):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="You've hit this session's usage limit. Try again later.",
        )

    user_message = await chat_service.add_message(conv.id, "user", payload.content, status="completed")
    assistant_message = await chat_service.add_message(conv.id, "assistant", "", status="pending")

    task = asyncio.create_task(execute_chat_workflow(assistant_message.id, conv.session_id, payload.content))
    _running_runs[assistant_message.id] = task

    return {"user_message": user_message, "assistant_message": assistant_message}


@router.post("/messages/{message_id}/stop", status_code=status.HTTP_202_ACCEPTED)
async def stop_message(msg: Message = Depends(owned_message)):
    """Interrupt an in-flight agent run. Idempotent: stopping a finished run is a no-op."""
    task = _running_runs.get(msg.id)
    if task and not task.done():
        task.cancel()
        return {"status": "cancelling"}

    # Already finished, or running on another worker. Emit a terminal event anyway so
    # a listening client is never left hanging.
    if msg.status in ("pending", "running"):
        await chat_service.update_message(msg.id, status="cancelled")
        await emit_chat_event(
            msg.id, {"type": "done", "status": "cancelled", "content": msg.content or "_Stopped._"}
        )
    return {"status": "stopped"}


async def _give_up(message_id: UUID, reason: str) -> str:
    """End a stream that cannot make progress, and persist that outcome.

    Without the DB write the message stays `pending` forever, so every page reload
    re-attaches and starts another doomed stream.
    """
    try:
        await chat_service.update_message(message_id, content=reason, status="failed")
    except Exception as e:
        logger.error(f"Could not mark message {message_id} failed: {e}")
    return f"data: {json.dumps({'type': 'done', 'status': 'failed', 'content': reason})}\n\n"


async def chat_event_generator(message_id: UUID, start_index: int = 0):
    """SSE stream of agent-status + text-delta events for one assistant message,
    read from the Redis list `chat_events:{message_id}` and terminated by its `done`
    event.

    `start_index` supports resume: a reconnecting client passes the number of events it
    already applied, so deltas aren't replayed and duplicated into the message body.
    """
    redis = get_redis()
    cache_key = f"chat_events:{message_id}"
    read_idx = start_index
    idle_ticks = 0
    errors = 0
    # ~5 min of silence with no terminal event means the worker died mid-run.
    max_idle_ticks = 1000
    max_errors = 3

    while True:
        try:
            events = await redis.lrange(cache_key, read_idx, -1)
            errors = 0
            if events:
                idle_ticks = 0
                read_idx += len(events)
                for ev in events:
                    yield f"data: {ev}\n\n"
                    try:
                        if json.loads(ev).get("type") == "done":
                            return
                    except (json.JSONDecodeError, TypeError):
                        pass
            else:
                idle_ticks += 1
                if idle_ticks > max_idle_ticks:
                    yield await _give_up(message_id, "The analysis timed out. Please try again.")
                    return
        except Exception as e:
            # Redis is the only source of events, so retrying forever just spins and
            # floods the log. Give up, and mark the message so a page reload doesn't
            # re-attach to a stream that can never produce anything.
            errors += 1
            if errors >= max_errors:
                logger.error(f"Giving up on chat stream for message {message_id}: {e}")
                yield await _give_up(message_id, "Chat is temporarily unavailable. Please try again.")
                return

        await asyncio.sleep(0.3)


@router.get("/messages/{message_id}/stream")
async def stream_chat_message(
    from_index: int = Query(0, ge=0, description="Resume from this event index"),
    msg: Message = Depends(owned_message),
    _: Principal = Depends(require_principal),
):
    """Stream live agent-status and text-delta events for one assistant message."""
    return StreamingResponse(
        chat_event_generator(msg.id, from_index),
        media_type="text/event-stream",
        # Proxies buffer by default, batching the stream into one late chunk.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
