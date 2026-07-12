import logging
import uuid
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from app.core.config import settings

logger = logging.getLogger("vector-store")


class VectorStoreService:
    """Service interfacing with Qdrant vector database for indexing and RAG queries."""

    def __init__(self):
        self.qdrant_host = settings.QDRANT_HOST
        self.qdrant_port = settings.QDRANT_PORT
        self._client: Optional[QdrantClient] = None

    def get_client(self) -> QdrantClient:
        """Lazily initialize Qdrant client connection."""
        if self._client is None:
            self._client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        return self._client

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate a 1536-dimensional embedding via the LiteLLM proxy, or a deterministic lexical mock fallback."""
        if settings.LITELLM_BASE_URL and settings.LITELLM_API_KEY:
            try:
                # Synchronous-like fetch using LangChain OpenAIEmbeddings, pointed at the LiteLLM proxy
                from langchain_openai import OpenAIEmbeddings
                embeddings_model = OpenAIEmbeddings(
                    openai_api_key=settings.LITELLM_API_KEY,
                    openai_api_base=settings.LITELLM_BASE_URL,
                )
                return embeddings_model.embed_query(text)
            except Exception as e:
                logger.error(f"LiteLLM embedding generation failed: {e}. Falling back to mock.")

        return self._generate_mock_embedding(text)

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate a deterministic 1536-dimensional unit-norm vector derived from the text hash."""
        # Create deterministic digest
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:4], "big")
        
        # Seed numpy generator for consistent vectors
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(1536)
        
        # Normalize to unit length (cosine similarity constraint)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
            
        return vec.tolist()

    async def ensure_collection(self, collection_name: str = "sec_filings"):
        """Ensure collection exists in Qdrant; creates it if not found."""
        qc = self.get_client()
        
        def _check_and_create():
            try:
                qc.get_collection(collection_name=collection_name)
            except Exception:
                logger.info(f"Qdrant collection '{collection_name}' not found. Creating collection...")
                qc.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
                )

        import asyncio
        await asyncio.to_thread(_check_and_create)

    async def upsert_document_chunks(self, symbol: str, chunks: List[Dict[str, Any]], collection_name: str = "sec_filings"):
        """Embeds and indexes list of document chunks into Qdrant vector space."""
        symbol = symbol.upper()
        qc = self.get_client()
        await self.ensure_collection(collection_name)

        points = []
        for chunk in chunks:
            text = chunk["text"]
            section = chunk["section"]
            chunk_id = chunk["chunk_id"]

            vector = self._generate_embedding(text)
            
            # Generate deterministic point UUID based on symbol and chunk index
            pt_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{symbol}:{chunk_id}"))

            points.append(
                PointStruct(
                    id=pt_id,
                    vector=vector,
                    payload={
                        "symbol": symbol,
                        "text": text,
                        "section": section,
                        "chunk_id": chunk_id
                    }
                )
            )

        # Bulk upsert into collection inside worker thread
        if points:
            import asyncio
            await asyncio.to_thread(qc.upsert, collection_name=collection_name, points=points)
            logger.info(f"Successfully upserted {len(points)} vector chunks for {symbol} in Qdrant")

    async def search_chunks(self, symbol: str, query: str, limit: int = 5, collection_name: str = "sec_filings") -> List[Dict[str, Any]]:
        """Search relevant filing chunks in Qdrant matching the query."""
        symbol = symbol.upper()
        qc = self.get_client()
        await self.ensure_collection(collection_name)

        query_vector = self._generate_embedding(query)

        # Apply metadata filter for ticker symbol compatibility
        query_filter = Filter(
            must=[
                FieldCondition(key="symbol", match=MatchValue(value=symbol))
            ]
        )

        import asyncio
        response = await asyncio.to_thread(
            qc.query_points,
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit
        )

        formatted_results = []
        for r in response.points:
            payload = r.payload or {}
            formatted_results.append({
                "text": payload.get("text", ""),
                "section": payload.get("section", "general"),
                "chunk_id": int(payload.get("chunk_id", 0)),
                "score": float(r.score)
            })

        logger.info(f"Vector search returned {len(formatted_results)} results for {symbol} query: '{query}'")
        return formatted_results


vector_store = VectorStoreService()
