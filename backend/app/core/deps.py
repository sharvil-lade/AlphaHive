"""Request-scoped identity.

All user data is partitioned by `session_id`, derived from a signed httpOnly cookie and
never accepted from the request body or query string. Anonymous visitors get an
unguessable session id on first hit; signing up claims it, so nothing is lost.
"""

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_session, encode_session
from app.db.session import get_db
from app.models.models import Conversation, Message, Portfolio, PortfolioHolding

logger = logging.getLogger("deps")

COOKIE_NAME = "ah_session"


@dataclass(frozen=True)
class Principal:
    """Who is making this request. `session_id` is the data-partition key."""

    session_id: str
    user_id: Optional[UUID] = None
    email: Optional[str] = None

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None


def new_session_id() -> str:
    """Session ids are bearer credentials, so they must not be guessable."""
    return f"session_{uuid4()}"


def set_session_cookie(response: Response, principal: Principal) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=encode_session(
            principal.session_id,
            str(principal.user_id) if principal.user_id else None,
            principal.email,
        ),
        max_age=settings.SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure(),
        samesite="lax",
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=settings.cookie_secure(),
        samesite="lax",
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


def _principal_from_request(request: Request) -> Optional[Principal]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    payload = decode_session(token)
    if not payload or not payload.get("sid"):
        return None
    uid = payload.get("uid")
    return Principal(
        session_id=payload["sid"],
        user_id=UUID(uid) if uid else None,
        email=payload.get("email"),
    )


async def get_principal(request: Request, response: Response) -> Principal:
    """Issues an anonymous session on first visit, so the app works before signup."""
    principal = _principal_from_request(request)
    if principal:
        return principal
    principal = Principal(session_id=new_session_id())
    set_session_cookie(response, principal)
    return principal


async def require_principal(request: Request) -> Principal:
    """For endpoints returning a Response directly (SSE, downloads), where a
    `set_cookie` on the injected response would be dropped."""
    principal = _principal_from_request(request)
    if not principal:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No active session."
        )
    return principal


async def require_user(principal: Principal = Depends(get_principal)) -> Principal:
    """Identity for endpoints that need a real account, not an anonymous session."""
    if not principal.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue."
        )
    return principal


# ── Ownership guards ──
# Return 404 (not 403) on a session mismatch, so the status code can't be used to
# confirm that a given id exists.

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")


async def owned_conversation(
    conversation_id: UUID,
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    conv = await db.get(Conversation, conversation_id)
    if not conv or conv.session_id != principal.session_id:
        raise _NOT_FOUND
    return conv


async def owned_message(
    message_id: UUID,
    principal: Principal = Depends(require_principal),
    db: AsyncSession = Depends(get_db),
) -> Message:
    stmt = (
        select(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Message.id == message_id, Conversation.session_id == principal.session_id)
    )
    msg = (await db.execute(stmt)).scalar_one_or_none()
    if not msg:
        raise _NOT_FOUND
    return msg


async def owned_holding(
    holding_id: UUID,
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
) -> PortfolioHolding:
    stmt = (
        select(PortfolioHolding)
        .join(Portfolio, Portfolio.id == PortfolioHolding.portfolio_id)
        .where(
            PortfolioHolding.id == holding_id,
            Portfolio.session_id == principal.session_id,
        )
    )
    holding = (await db.execute(stmt)).scalar_one_or_none()
    if not holding:
        raise _NOT_FOUND
    return holding
