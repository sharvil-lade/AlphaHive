import asyncio
import json
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.agents.utils import get_redis, emit_chat_event
from app.schemas.schemas import (
    ChatMessageCreate,
    ChatMessageCreateResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationSchema,
)
from app.services.chat_service import chat_service

router = APIRouter()
logger = logging.getLogger("chat-api")


async def _persist_traces_from_events(message_id: UUID) -> None:
    """Snapshot each node's final status from the ephemeral Redis event stream into
    the AgentTrace table, so the trace panel survives a page reload (live running ->
    completed transitions are only visible during the SSE stream itself)."""
    try:
        redis = get_redis()
        raw_events = await redis.lrange(f"chat_events:{message_id}", 0, -1)
        node_status = {}
        for raw in raw_events:
            try:
                event = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            if event.get("type") == "agent-status":
                node_status[event["node"]] = event["status"]

        for node, node_final_status in node_status.items():
            trace = await chat_service.start_trace(message_id, node)
            await chat_service.end_trace(trace.id, node_final_status)
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
    """Background execution of the chat LangGraph state machine for one turn."""
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
        await emit_chat_event(assistant_message_id, {"type": "done", "status": "completed", "content": content})
    except Exception as e:
        logger.error(f"Error executing chat workflow for message {assistant_message_id}: {e}")
        content = "Sorry, something went wrong while processing your request."
        await chat_service.update_message(assistant_message_id, content=content, status="failed")
        await emit_chat_event(assistant_message_id, {"type": "done", "status": "failed", "content": content})
    finally:
        await _persist_traces_from_events(assistant_message_id)


@router.post("/conversations", response_model=ConversationSchema, status_code=status.HTTP_201_CREATED)
async def create_conversation(payload: ConversationCreate):
    """Create a new conversation for a client session."""
    return await chat_service.create_conversation(payload.session_id, payload.title)


@router.get("/conversations", response_model=List[ConversationSchema])
async def list_conversations(session_id: str = Query(..., description="Client Session ID")):
    """List all conversations for a client session, most recently updated first."""
    return await chat_service.list_conversations(session_id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: UUID):
    """Fetch a conversation's full message history, including persisted agent traces."""
    conv = await chat_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_message(
    conversation_id: UUID,
    payload: ChatMessageCreate,
    background_tasks: BackgroundTasks,
):
    """Post a free-form user message, kick off the chat graph in the background, and
    return immediately — the client opens the SSE stream for the assistant message
    to watch live agent status + streamed response text."""
    conv = await chat_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    from app.services.token_budget_service import token_budget_service
    is_budget_ok = await token_budget_service.check_budget(conv.session_id)
    if not is_budget_ok:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Token budget exceeded for this session. Please reset or wait.",
        )

    user_message = await chat_service.add_message(conversation_id, "user", payload.content, status="completed")
    assistant_message = await chat_service.add_message(conversation_id, "assistant", "", status="pending")

    background_tasks.add_task(execute_chat_workflow, assistant_message.id, conv.session_id, payload.content)

    return {"user_message": user_message, "assistant_message": assistant_message}


async def chat_event_generator(message_id: UUID):
    """Server-Sent Events generator streaming agent-status + text-delta events for
    one assistant message, reading from the Redis list `chat_events:{message_id}`.

    Terminates as soon as it sees the `done` event that `execute_chat_workflow`
    appends to this same list — a single source of truth, rather than also
    separately polling Postgres for the message status on every tick. Under many
    concurrent open chat streams, that extra per-poll DB round trip scaled linearly
    with active connections for no benefit, since completion is already signaled
    through the Redis list this generator is polling anyway. This also makes
    reconnects (a client re-opening the stream after the run already finished)
    work correctly: the persisted list (24h TTL) still contains the `done` event,
    so replaying it from the start still terminates the generator immediately.
    """
    redis = get_redis()
    cache_key = f"chat_events:{message_id}"
    read_idx = 0

    while True:
        try:
            events = await redis.lrange(cache_key, read_idx, -1)
            if events:
                read_idx += len(events)
                for ev in events:
                    yield f"data: {ev}\n\n"
                    try:
                        if json.loads(ev).get("type") == "done":
                            return
                    except (json.JSONDecodeError, TypeError):
                        pass
        except Exception as e:
            logger.error(f"Error reading chat events from Redis for message {message_id}: {e}")

        await asyncio.sleep(0.3)


@router.get("/messages/{message_id}/stream")
async def stream_chat_message(message_id: UUID):
    """Stream live agent-status and text-delta events for one assistant message."""
    return StreamingResponse(chat_event_generator(message_id), media_type="text/event-stream")
