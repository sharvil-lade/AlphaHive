"""Accounts: signup, login, logout, and data rights (export / delete).

There is no `users.id` foreign key on the data tables. All user data is partitioned by
`session_id`, and an account simply owns one — which makes signup a claim operation.
See `app/core/deps.py`.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    Principal,
    clear_session_cookie,
    get_principal,
    new_session_id,
    require_user,
    set_session_cookie,
)
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.models import (
    AgentRun,
    Conversation,
    Message,
    Portfolio,
    PortfolioHolding,
    User,
)
from app.schemas.schemas import LoginRequest, SessionResponse, SignupRequest

router = APIRouter()
logger = logging.getLogger("auth-api")

# Deliberately identical for "no such email" and "wrong password" so the endpoint
# cannot be used to enumerate which email addresses have accounts.
_BAD_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password."
)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _session_taken(db: AsyncSession, session_id: str) -> bool:
    stmt = select(User.id).where(User.session_id == session_id)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


@router.get("/session", response_model=SessionResponse)
async def read_session(principal: Principal = Depends(get_principal)):
    """Caller identity, minting an anonymous session cookie on first visit."""
    return SessionResponse(
        authenticated=principal.is_authenticated,
        user_id=principal.user_id,
        email=principal.email,
    )


@router.post("/signup", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    response: Response,
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
):
    """Create an account, claiming the current anonymous session so the visitor keeps
    the portfolio and chat history they already have."""
    email = _normalize_email(payload.email)

    existing = (await db.execute(select(User.id).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )

    # Claim the anonymous session unless it already belongs to an account.
    session_id = principal.session_id
    if principal.is_authenticated or await _session_taken(db, session_id):
        session_id = new_session_id()

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        name=(payload.name or "").strip() or None,
        session_id=session_id,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # Lost a race against a concurrent signup for the same email.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )

    authed = Principal(session_id=user.session_id, user_id=user.id, email=user.email)
    set_session_cookie(response, authed)
    logger.info("Account created", extra={"user_id": str(user.id)})
    return SessionResponse(authenticated=True, user_id=user.id, email=user.email, name=user.name)


@router.post("/login", response_model=SessionResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Exchange credentials for a session cookie bound to the account's session id."""
    email = _normalize_email(payload.email)
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    # Always run a hash comparison, even when the user does not exist, so response time
    # does not reveal whether the email is registered.
    reference_hash = user.password_hash if user else hash_password("timing-equalizer")
    if not verify_password(payload.password, reference_hash) or not user:
        raise _BAD_CREDENTIALS

    authed = Principal(session_id=user.session_id, user_id=user.id, email=user.email)
    set_session_cookie(response, authed)
    return SessionResponse(authenticated=True, user_id=user.id, email=user.email, name=user.name)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    """Drop the session cookie. The next request is issued a fresh anonymous session."""
    clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


async def _holdings_of(db: AsyncSession, portfolio_id):
    stmt = select(PortfolioHolding).where(PortfolioHolding.portfolio_id == portfolio_id)
    return (await db.execute(stmt)).scalars().all()


@router.get("/export")
async def export_my_data(principal: Principal = Depends(require_user), db: AsyncSession = Depends(get_db)):
    """Export everything stored about the account as JSON (DPDP / GDPR portability)."""
    sid = principal.session_id

    portfolios = (await db.execute(select(Portfolio).where(Portfolio.session_id == sid))).scalars().all()
    conversations = (
        (await db.execute(select(Conversation).where(Conversation.session_id == sid))).scalars().all()
    )
    conv_ids = [c.id for c in conversations]
    messages = (
        (await db.execute(select(Message).where(Message.conversation_id.in_(conv_ids)))).scalars().all()
        if conv_ids
        else []
    )

    portfolio_payload = []
    for p in portfolios:
        holdings = await _holdings_of(db, p.id)
        portfolio_payload.append(
            {
                "name": p.name,
                "created_at": p.created_at.isoformat(),
                "holdings": [
                    {
                        "symbol": h.symbol,
                        "shares": h.shares,
                        "average_buy_price": h.average_buy_price,
                    }
                    for h in holdings
                ],
            }
        )

    return {
        "exported_at": datetime.utcnow().isoformat(),
        "account": {"email": principal.email, "user_id": str(principal.user_id)},
        "portfolios": portfolio_payload,
        "conversations": [
            {
                "title": c.title,
                "created_at": c.created_at.isoformat(),
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in messages
                    if m.conversation_id == c.id
                ],
            }
            for c in conversations
        ],
    }


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    response: Response,
    principal: Principal = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently erase the account and every row keyed to its session (DPDP / GDPR).

    Child rows cascade via the ON DELETE CASCADE on their foreign keys.
    """
    sid = principal.session_id
    for model in (Portfolio, Conversation, AgentRun):
        await db.execute(sa_delete(model).where(model.session_id == sid))
    await db.execute(sa_delete(User).where(User.id == principal.user_id))
    await db.commit()

    clear_session_cookie(response)
    logger.info("Account deleted", extra={"user_id": str(principal.user_id)})
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
