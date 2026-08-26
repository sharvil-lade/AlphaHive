import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.models import Conversation, Message, AgentTrace

logger = logging.getLogger("chat-service")

_TITLE_MAX = 60


def _derive_title(content: str) -> str:
    """First line of the message, cut at a word boundary."""
    first_line = content.strip().splitlines()[0] if content.strip() else "New conversation"
    if len(first_line) <= _TITLE_MAX:
        return first_line
    cut = first_line[:_TITLE_MAX].rsplit(" ", 1)[0]
    return f"{cut or first_line[:_TITLE_MAX]}…"


class ChatService:
    """Owns all persistence for Conversation/Message/AgentTrace.

    Agent nodes and the LangGraph graph never write to Postgres directly for chat
    data — they return data, and the chat endpoint layer calls this service after
    the graph finishes. This keeps orchestration and persistence cleanly separated
    (unlike the older ticker-only `agents.py` flow, where `decision_node` wrote
    directly to the DB).
    """

    async def create_conversation(self, session_id: str, title: Optional[str] = None) -> Conversation:
        async with AsyncSessionLocal() as session:
            conv = Conversation(session_id=session_id, title=title)
            session.add(conv)
            await session.commit()
            return conv

    async def list_conversations(
        self, session_id: str, limit: int = 50, offset: int = 0
    ) -> List[Conversation]:
        """Most-recently-updated first, paginated."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Conversation)
                .where(Conversation.session_id == session_id)
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Conversation)
                .where(Conversation.id == conversation_id)
                .options(selectinload(Conversation.messages).selectinload(Message.traces))
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def add_message(
        self, conversation_id: UUID, role: str, content: str = "", status: str = "completed"
    ) -> Message:
        async with AsyncSessionLocal() as session:
            msg = Message(conversation_id=conversation_id, role=role, content=content, status=status)
            # A brand-new message can't have any traces yet — set this explicitly so
            # serializing it after the session closes doesn't trigger a lazy-load on
            # a now-detached instance (DetachedInstanceError).
            msg.traces = []
            session.add(msg)

            conv = await session.get(Conversation, conversation_id)
            if conv:
                conv.updated_at = datetime.utcnow()
                if not conv.title and role == "user":
                    conv.title = _derive_title(content)

            await session.commit()
            return msg

    async def get_message(self, message_id: UUID) -> Optional[Message]:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Message)
                .where(Message.id == message_id)
                .options(selectinload(Message.traces))
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update_message(
        self, message_id: UUID, content: Optional[str] = None, status: Optional[str] = None
    ) -> None:
        async with AsyncSessionLocal() as session:
            msg = await session.get(Message, message_id)
            if msg:
                if content is not None:
                    msg.content = content
                if status is not None:
                    msg.status = status
                await session.commit()

    async def record_trace(
        self,
        message_id: UUID,
        node: str,
        status: str,
        summary: Optional[str] = None,
        label: Optional[str] = None,
        rating: Optional[str] = None,
        confidence: Optional[int] = None,
    ) -> AgentTrace:
        """Write one node's finished trace, verdict included. Traces are only ever
        persisted after a run, from the Redis event log, so there is no running row to
        update."""
        async with AsyncSessionLocal() as session:
            trace = AgentTrace(
                message_id=message_id,
                node=node,
                status=status,
                summary=summary,
                label=label,
                rating=rating,
                confidence=confidence,
                ended_at=datetime.utcnow(),
            )
            session.add(trace)
            await session.commit()
            return trace


chat_service = ChatService()
