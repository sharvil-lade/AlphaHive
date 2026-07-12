import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.models import Conversation, Message, AgentTrace

logger = logging.getLogger("chat-service")


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

    async def list_conversations(self, session_id: str) -> List[Conversation]:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Conversation)
                .where(Conversation.session_id == session_id)
                .order_by(Conversation.updated_at.desc())
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
                    conv.title = content[:80]

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

    async def start_trace(self, message_id: UUID, node: str) -> AgentTrace:
        async with AsyncSessionLocal() as session:
            trace = AgentTrace(message_id=message_id, node=node, status="running")
            session.add(trace)
            await session.commit()
            return trace

    async def end_trace(self, trace_id: UUID, status: str, summary: Optional[str] = None) -> None:
        async with AsyncSessionLocal() as session:
            trace = await session.get(AgentTrace, trace_id)
            if trace:
                trace.status = status
                trace.summary = summary
                trace.ended_at = datetime.utcnow()
                await session.commit()


chat_service = ChatService()
