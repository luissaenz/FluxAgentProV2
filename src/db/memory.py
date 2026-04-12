"""Semantic memory — vectorial long-term memory for agents (Phase 3).

Provides:
- embed(): generates embedding with text-embedding-3-small (1536 dims)
- save_memory(): persists a memory fragment with its embedding
- search_memory(): searches by semantic similarity
- cleanup_expired_memory(): deletes memories with expired valid_to

Rule R7: All tables have org_id + RLS.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, List

from pydantic import BaseModel

if TYPE_CHECKING:
    from openai import OpenAI

logger = logging.getLogger(__name__)


class MemoryRecord(BaseModel):
    """Represents a persisted or retrieved memory fragment."""

    id: str
    org_id: str
    agent_role: Optional[str]
    content: str
    similarity: Optional[float] = None


class MemoryError(Exception):
    """Raised when a memory cannot be persisted or retrieved."""


# ── Lazy OpenAI client ────────────────────────────────────────────

_client: Optional["OpenAI"] = None


def _get_openai_client() -> "OpenAI":
    """Lazy-initialise the OpenAI client — does not fail at import time."""
    global _client
    if _client is None:
        from openai import OpenAI
        from src.config import get_settings

        settings = get_settings()
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def embed(text: str) -> List[float]:
    """Generate an embedding with text-embedding-3-small (1536 dims)."""
    client = _get_openai_client()
    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding


async def embed_async(text: str) -> List[float]:
    """Async version of embed() — runs in a thread pool."""
    import asyncio

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, embed, text)


def save_memory(
    org_id: str,
    content: str,
    source_type: str,
    agent_role: Optional[str] = None,
    metadata: Optional[dict] = None,
    ttl_hours: Optional[int] = None,
) -> MemoryRecord:
    """Persist a memory fragment with its embedding.

    Args:
        org_id: Organisation UUID.
        content: Text to remember.
        source_type: "conversation" | "document" | "task_result".
        agent_role: Scopes memory to a specific role; None = org-wide.
        metadata: Extra data to store alongside the memory.
        ttl_hours: If set, the memory expires after N hours. Default: never.

    Returns:
        MemoryRecord with the generated ID.

    Raises:
        ValueError: if org_id or content are empty.
        MemoryError: if the insert fails.
    """
    if not org_id or not content:
        raise ValueError("org_id and content son requeridos")

    embedding = embed(content)

    from src.db.session import get_service_client

    svc = get_service_client()

    memory_id = str(uuid.uuid4())
    valid_to: Optional[str] = None
    if ttl_hours is not None:
        valid_to = (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat()

    result = svc.table("memory_vectors").insert({
        "id": memory_id,
        "org_id": org_id,
        "agent_role": agent_role,
        "source_type": source_type,
        "content": content,
        "embedding": embedding,
        "embedding_version": "text-embedding-3-small",
        "metadata": metadata or {},
        "valid_to": valid_to or "infinity",
    }).execute()

    if not result.data:
        raise MemoryError(f"No se pudo persistir memoria para org {org_id}")

    return MemoryRecord(
        id=memory_id,
        org_id=org_id,
        agent_role=agent_role,
        content=content,
    )


async def save_memory_async(
    org_id: str,
    content: str,
    source_type: str,
    agent_role: Optional[str] = None,
    metadata: Optional[dict] = None,
    ttl_hours: Optional[int] = None,
) -> MemoryRecord:
    """Async version of save_memory()."""
    import asyncio

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: save_memory(org_id, content, source_type, agent_role, metadata, ttl_hours),
    )


def search_memory(
    org_id: str,
    query: str,
    agent_role: Optional[str] = None,
    limit: int = 5,
    min_similarity: float = 0.7,
) -> List[MemoryRecord]:
    """Search memory fragments by semantic similarity.

    Args:
        org_id: Organisation UUID.
        query: Natural-language query.
        agent_role: Filter to a specific role; None searches org-wide.
        limit: Max results to return.
        min_similarity: Minimum cosine similarity threshold (0–1).

    Returns:
        List of MemoryRecord ordered by relevance (most similar first).
        Empty list if no matches above threshold.

    Note:
        p_agent_role is excluded from the RPC call when None so the SQL
        default NULL applies correctly (avoids serialising as the string "null").
    """
    embedding = embed(query)

    from src.db.session import get_service_client

    svc = get_service_client()

    rpc_params = {
        "query_embedding": embedding,
        "p_org_id": org_id,
        "match_limit": limit,
        "min_similarity": min_similarity,
    }
    if agent_role is not None:
        rpc_params["p_agent_role"] = agent_role

    result = svc.rpc("search_memories", rpc_params).execute()

    return [
        MemoryRecord(
            id=row["id"],
            org_id=org_id,
            agent_role=agent_role,
            content=row["content"],
            similarity=row["similarity"],
        )
        for row in (result.data or [])
    ]


def cleanup_expired_memory(org_id: str) -> int:
    """Delete all expired memories for an organisation.

    Returns:
        Number of deleted records.
    """
    from src.db.session import get_service_client

    svc = get_service_client()
    result = (
        svc.table("memory_vectors")
        .delete()
        .lt("valid_to", "now()")
        .eq("org_id", org_id)
        .execute()
    )

    deleted = len(result.data or [])
    logger.info("memory_cleanup org=%s deleted=%d", org_id, deleted)
    return deleted
