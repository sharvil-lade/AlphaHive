"""Search over indexed SEC-filing chunks, stored in Postgres.

Two ranking modes, chosen by whether EMBEDDING_MODEL is configured:

  - semantic — pgvector cosine distance over the stored embeddings.
  - keyword  — Postgres full-text `ts_rank` over the chunk text.

The keyword mode exists because the embedding path is genuinely optional: many
LiteLLM keys have no embedding-model access. Ranking real words beats ranking
nothing, and it needs no extra infrastructure.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.services.llm_client import llm_client

logger = logging.getLogger("sec-index")

# Cosine distance above which a chunk is too unrelated to cite. pgvector's `<=>`
# returns 0 (identical) to 2 (opposite); 0.6 keeps loosely-related paragraphs and
# drops noise.
_MAX_COSINE_DISTANCE = 0.6

_SEMANTIC_SQL = text("""
    SELECT content, section, chunk_id, 1 - (embedding <=> CAST(:query AS vector)) AS score
    FROM sec_chunks
    WHERE symbol = :symbol
      AND embedding IS NOT NULL
      AND embedding <=> CAST(:query AS vector) < :max_distance
    ORDER BY embedding <=> CAST(:query AS vector)
    LIMIT :limit
""")

# Agents ask in whole sentences ("regulatory risk factors, competition, liabilities"),
# and tsquery ANDs its terms by default, so a chunk would have to contain every word to
# match at all. Swapping `&` for `|` on the already-sanitised tsquery turns it into
# "rank by how many terms hit", which is what ts_rank is for. Going through
# websearch_to_tsquery first is what makes the text substitution safe on any input.
_OR_TSQUERY = "replace(websearch_to_tsquery('english', :query)::text, '&', '|')::tsquery"

_KEYWORD_SQL = text(f"""
    SELECT content, section, chunk_id,
           ts_rank(to_tsvector('english', content), {_OR_TSQUERY}) AS score
    FROM sec_chunks
    WHERE symbol = :symbol
      AND to_tsvector('english', content) @@ {_OR_TSQUERY}
    ORDER BY score DESC
    LIMIT :limit
""")

_UPSERT_SQL = text("""
    INSERT INTO sec_chunks (id, symbol, chunk_id, section, content, embedding, created_at)
    VALUES (:id, :symbol, :chunk_id, :section, :content, CAST(:embedding AS vector), now())
    ON CONFLICT (symbol, chunk_id)
    DO UPDATE SET section = EXCLUDED.section,
                  content = EXCLUDED.content,
                  embedding = EXCLUDED.embedding
""")


def _to_vector_literal(embedding: list[float] | None) -> str | None:
    """pgvector accepts its text input form, so the value crosses asyncpg as a plain
    string and needs no per-connection type codec."""
    if embedding is None:
        return None
    return "[" + ",".join(f"{v:.6f}" for v in embedding) + "]"


async def index_chunks(symbol: str, chunks: list[dict[str, Any]]) -> int:
    """Store (or replace) a filing's chunks for `symbol`. Returns the number written."""
    symbol = symbol.upper()
    if not chunks:
        return 0

    embeddings = await llm_client.embed([c["text"] for c in chunks])
    if embeddings is None:
        logger.info(f"Indexing {len(chunks)} chunks for {symbol} without embeddings (keyword search only)")
    elif len(embeddings) != len(chunks):
        logger.warning(
            f"Embedding count {len(embeddings)} != chunk count {len(chunks)} for {symbol}; "
            "storing without embeddings"
        )
        embeddings = None

    rows = [
        {
            "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"{symbol}:{chunk['chunk_id']}"),
            "symbol": symbol,
            "chunk_id": chunk["chunk_id"],
            "section": chunk["section"],
            "content": chunk["text"],
            "embedding": _to_vector_literal(embeddings[i] if embeddings else None),
        }
        for i, chunk in enumerate(chunks)
    ]

    async with AsyncSessionLocal() as db:
        await db.execute(_UPSERT_SQL, rows)
        await db.commit()

    logger.info(f"Indexed {len(rows)} SEC chunks for {symbol}")
    return len(rows)


async def search(symbol: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Rank a symbol's indexed chunks against `query`. Empty list if nothing matches."""
    symbol = symbol.upper()
    query_embedding = (await llm_client.embed([query]) or [None])[0]

    if query_embedding is not None:
        sql = _SEMANTIC_SQL
        params = {
            "symbol": symbol,
            "query": _to_vector_literal(query_embedding),
            "limit": limit,
            "max_distance": _MAX_COSINE_DISTANCE,
        }
    else:
        sql = _KEYWORD_SQL
        params = {"symbol": symbol, "query": query, "limit": limit}

    async with AsyncSessionLocal() as db:
        result = await db.execute(sql, params)
        matches = [
            {
                "text": row.content,
                "section": row.section,
                "chunk_id": row.chunk_id,
                "score": float(row.score),
            }
            for row in result
        ]

    logger.info(f"SEC search returned {len(matches)} chunks for {symbol}: '{query}'")
    return matches
