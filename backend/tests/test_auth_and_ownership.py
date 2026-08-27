"""Auth, session identity, and the cross-session isolation guarantees.

These are the tests that would have caught the two IDOR bugs: a bare holding id or
conversation id used to be enough for any caller to read or mutate another user's data.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import decode_session, encode_session, hash_password, verify_password
from app.main import app


def _client() -> AsyncClient:
    # Each AsyncClient keeps its own cookie jar, which is exactly what we need to
    # simulate two unrelated visitors.
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


# ── Password hashing ──────────────────────────────────────────────────────────


def test_password_hash_roundtrip():
    h = hash_password("correct horse battery staple")
    assert h != "correct horse battery staple"
    assert verify_password("correct horse battery staple", h)
    assert not verify_password("wrong password", h)


def test_long_passwords_are_not_truncated():
    """bcrypt silently ignores bytes past 72; the SHA-256 pre-hash must prevent that."""
    base = "x" * 100
    assert not verify_password(base + "DIFFERENT", hash_password(base + "ORIGINAL"))


def test_malformed_hash_is_a_failed_login_not_a_crash():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


# ── Session tokens ────────────────────────────────────────────────────────────


def test_session_token_roundtrip():
    token = encode_session("session_abc", "11111111-1111-1111-1111-111111111111", "a@b.com")
    payload = decode_session(token)
    assert payload["sid"] == "session_abc"
    assert payload["email"] == "a@b.com"


def test_forged_session_token_is_rejected():
    token = encode_session("session_abc")
    assert decode_session(token + "tampered") is None
    assert decode_session("garbage") is None


# ── Session issuance ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_first_visit_issues_an_anonymous_session():
    async with _client() as c:
        res = await c.get("/api/v1/auth/session")
        assert res.status_code == 200
        assert res.json()["authenticated"] is False
        assert "ah_session" in res.cookies


@pytest.mark.asyncio
async def test_session_cookie_is_httponly():
    """JavaScript must not be able to read the session id, so XSS cannot lift it."""
    async with _client() as c:
        res = await c.get("/api/v1/auth/session")
        assert "httponly" in res.headers["set-cookie"].lower()


@pytest.mark.asyncio
async def test_signup_then_session_reports_authenticated():
    async with _client() as c:
        email = _email()
        res = await c.post("/api/v1/auth/signup", json={"email": email, "password": "hunter2hunter2"})
        assert res.status_code == 201, res.text
        assert res.json()["authenticated"] is True

        me = await c.get("/api/v1/auth/session")
        assert me.json()["email"] == email


@pytest.mark.asyncio
async def test_duplicate_email_is_rejected():
    async with _client() as c:
        email = _email()
        body = {"email": email, "password": "hunter2hunter2"}
        assert (await c.post("/api/v1/auth/signup", json=body)).status_code == 201
    async with _client() as c2:
        assert (await c2.post("/api/v1/auth/signup", json=body)).status_code == 409


@pytest.mark.asyncio
async def test_short_password_is_rejected():
    async with _client() as c:
        res = await c.post("/api/v1/auth/signup", json={"email": _email(), "password": "short"})
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_login_with_wrong_password_fails_without_revealing_the_account():
    email = _email()
    async with _client() as c:
        await c.post("/api/v1/auth/signup", json={"email": email, "password": "hunter2hunter2"})

    async with _client() as c:
        wrong = await c.post("/api/v1/auth/login", json={"email": email, "password": "nope-nope-nope"})
        missing = await c.post("/api/v1/auth/login", json={"email": _email(), "password": "nope-nope-nope"})
        assert wrong.status_code == missing.status_code == 401
        assert wrong.json()["detail"] == missing.json()["detail"]


@pytest.mark.asyncio
async def test_signup_claims_the_anonymous_portfolio():
    """A visitor who adds holdings before signing up must keep them."""
    async with _client() as c:
        await c.post(
            "/api/v1/portfolios/holdings", json={"symbol": "TCS", "shares": 5, "average_buy_price": 100.0}
        )
        await c.post("/api/v1/auth/signup", json={"email": _email(), "password": "hunter2hunter2"})

        summary = await c.get("/api/v1/portfolios/summary")
        assert "TCS" in [h["symbol"] for h in summary.json()["holdings"]]


# ── Cross-session isolation (the IDOR regressions) ────────────────────────────


@pytest.mark.asyncio
async def test_another_session_cannot_delete_your_holding():
    async with _client() as owner:
        created = await owner.post(
            "/api/v1/portfolios/holdings",
            json={"symbol": "INFY", "shares": 3, "average_buy_price": 50.0},
        )
        holding_id = created.json()["id"]

        async with _client() as attacker:
            await attacker.get("/api/v1/auth/session")
            assert (await attacker.delete(f"/api/v1/portfolios/holdings/{holding_id}")).status_code == 404
            assert (
                await attacker.put(
                    f"/api/v1/portfolios/holdings/{holding_id}",
                    json={"shares": 999, "average_buy_price": 1.0},
                )
            ).status_code == 404

        # Still intact, and still the owner's.
        assert (await owner.delete(f"/api/v1/portfolios/holdings/{holding_id}")).status_code == 204


@pytest.mark.asyncio
async def test_another_session_cannot_read_your_conversation():
    async with _client() as owner:
        conv_id = (await owner.post("/api/v1/chat/conversations", json={"title": "Private"})).json()["id"]
        assert (await owner.get(f"/api/v1/chat/conversations/{conv_id}")).status_code == 200

        async with _client() as attacker:
            await attacker.get("/api/v1/auth/session")
            assert (await attacker.get(f"/api/v1/chat/conversations/{conv_id}")).status_code == 404
            assert (await attacker.delete(f"/api/v1/chat/conversations/{conv_id}")).status_code == 404


@pytest.mark.asyncio
async def test_conversations_list_is_scoped_to_the_session():
    async with _client() as owner:
        conv_id = (await owner.post("/api/v1/chat/conversations", json={"title": "Mine"})).json()["id"]

        async with _client() as other:
            listed = await other.get("/api/v1/chat/conversations")
            assert conv_id not in [c["id"] for c in listed.json()]


@pytest.mark.asyncio
async def test_rename_and_delete_conversation():
    async with _client() as c:
        conv_id = (await c.post("/api/v1/chat/conversations", json={})).json()["id"]

        renamed = await c.patch(f"/api/v1/chat/conversations/{conv_id}", json={"title": "Reliance research"})
        assert renamed.json()["title"] == "Reliance research"

        assert (await c.delete(f"/api/v1/chat/conversations/{conv_id}")).status_code == 204
        assert (await c.get(f"/api/v1/chat/conversations/{conv_id}")).status_code == 404


@pytest.mark.asyncio
async def test_stream_without_a_session_cookie_is_rejected():
    async with _client() as c:
        res = await c.get(f"/api/v1/chat/messages/{uuid.uuid4()}/stream")
        assert res.status_code == 401


# ── Data rights ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_requires_an_account():
    async with _client() as c:
        await c.get("/api/v1/auth/session")
        assert (await c.get("/api/v1/auth/export")).status_code == 401


@pytest.mark.asyncio
async def test_delete_account_erases_the_data():
    async with _client() as c:
        await c.post("/api/v1/auth/signup", json={"email": _email(), "password": "hunter2hunter2"})
        await c.post(
            "/api/v1/portfolios/holdings", json={"symbol": "WIPRO", "shares": 1, "average_buy_price": 10.0}
        )

        export = await c.get("/api/v1/auth/export")
        assert export.status_code == 200
        assert export.json()["portfolios"][0]["holdings"][0]["symbol"] == "WIPRO"

        assert (await c.delete("/api/v1/auth/account")).status_code == 204
        # Cookie cleared, so the caller is anonymous again and has no account.
        assert (await c.get("/api/v1/auth/export")).status_code == 401


# ── Input validation ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_negative_shares_are_rejected():
    async with _client() as c:
        res = await c.post(
            "/api/v1/portfolios/holdings",
            json={"symbol": "TCS", "shares": -5, "average_buy_price": 100.0},
        )
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_oversized_chat_message_is_rejected():
    async with _client() as c:
        conv_id = (await c.post("/api/v1/chat/conversations", json={})).json()["id"]
        res = await c.post(f"/api/v1/chat/conversations/{conv_id}/messages", json={"content": "x" * 5000})
        assert res.status_code == 422
