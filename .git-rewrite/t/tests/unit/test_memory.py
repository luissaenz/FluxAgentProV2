"""tests/unit/test_memory.py — Semantic memory unit tests (Phase 3).

All OpenAI and Supabase calls are mocked — no external dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.db.memory import (
    embed,
    save_memory,
    search_memory,
    cleanup_expired_memory,
    MemoryRecord,
    MemoryError,
)


FIXED_EMBEDDING = [0.1] * 1536


class TestEmbed:
    """embed() generates 1536-dim vectors via lazy OpenAI client."""

    @patch("src.db.memory._get_openai_client")
    def test_embed_returns_1536_dimensions(self, mock_get_client):
        mock_oai = MagicMock()
        mock_oai.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=FIXED_EMBEDDING)]
        )
        mock_get_client.return_value = mock_oai

        result = embed("test text")

        assert len(result) == 1536
        mock_oai.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small", input="test text"
        )

    @patch("src.db.memory._get_openai_client")
    def test_embed_lazy_init(self, mock_get_client):
        """OpenAI client is not created until the first call."""
        from src.db import memory as mem_module

        mem_module._client = None  # reset

        mock_oai = MagicMock()
        mock_oai.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=FIXED_EMBEDDING)]
        )
        mock_get_client.return_value = mock_oai

        embed("test")

        mock_get_client.assert_called_once()


class TestSaveMemory:
    """save_memory() persists to Supabase and returns MemoryRecord."""

    @patch("src.db.session.get_service_client")
    @patch("src.db.memory.embed")
    def test_save_memory_returns_memory_record(self, mock_embed, mock_get_client):
        mock_embed.return_value = FIXED_EMBEDDING
        mock_svc = MagicMock()
        mock_svc.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "mem-123", "org_id": "org-123", "content": "test content"}]
        )
        mock_get_client.return_value = mock_svc

        record = save_memory(
            org_id="org-123",
            content="test content",
            source_type="conversation",
            agent_role="sales",
            metadata={"task_id": "abc"},
        )

        assert isinstance(record, MemoryRecord)
        assert record.content == "test content"
        assert record.org_id == "org-123"
        assert record.agent_role == "sales"

    @patch("src.db.session.get_service_client")
    @patch("src.db.memory.embed")
    def test_save_memory_inserts_embedding_version(self, mock_embed, mock_get_client):
        mock_embed.return_value = FIXED_EMBEDDING
        mock_svc = MagicMock()
        mock_svc.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "mem-1"}]
        )
        mock_get_client.return_value = mock_svc

        save_memory(org_id="org-1", content="text", source_type="document")

        insert_data = mock_svc.table.return_value.insert.call_args[0][0]
        assert insert_data["embedding_version"] == "text-embedding-3-small"

    @patch("src.db.session.get_service_client")
    @patch("src.db.memory.embed")
    def test_save_memory_with_ttl_sets_valid_to(self, mock_embed, mock_get_client):
        mock_embed.return_value = FIXED_EMBEDDING
        mock_svc = MagicMock()
        mock_svc.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "mem-1"}]
        )
        mock_get_client.return_value = mock_svc

        save_memory(
            org_id="org-1",
            content="datos temporales",
            source_type="conversation",
            ttl_hours=24,
        )

        insert_data = mock_svc.table.return_value.insert.call_args[0][0]
        assert insert_data["valid_to"] != "infinity"

    @patch("src.db.session.get_service_client")
    @patch("src.db.memory.embed")
    def test_save_memory_without_ttl_sets_infinity(self, mock_embed, mock_get_client):
        mock_embed.return_value = FIXED_EMBEDDING
        mock_svc = MagicMock()
        mock_svc.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "mem-1"}]
        )
        mock_get_client.return_value = mock_svc

        save_memory(org_id="org-1", content="texto", source_type="document")

        insert_data = mock_svc.table.return_value.insert.call_args[0][0]
        assert insert_data["valid_to"] == "infinity"

    def test_save_memory_raises_on_empty_org_id(self):
        with pytest.raises(ValueError, match="org_id and content son requeridos"):
            save_memory(org_id="", content="test", source_type="doc")

    def test_save_memory_raises_on_empty_content(self):
        with pytest.raises(ValueError, match="org_id and content son requeridos"):
            save_memory(org_id="org-1", content="", source_type="doc")

    @patch("src.db.session.get_service_client")
    @patch("src.db.memory.embed")
    def test_save_memory_raises_memory_error_on_insert_failure(
        self, mock_embed, mock_get_client
    ):
        mock_embed.return_value = FIXED_EMBEDDING
        mock_svc = MagicMock()
        mock_svc.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_get_client.return_value = mock_svc

        with pytest.raises(MemoryError):
            save_memory(org_id="org-1", content="test", source_type="doc")


class TestSearchMemory:
    """search_memory() returns list[MemoryRecord] ordered by similarity."""

    @patch("src.db.session.get_service_client")
    @patch("src.db.memory.embed")
    def test_search_memory_returns_memory_records(self, mock_embed, mock_get_client):
        mock_embed.return_value = FIXED_EMBEDDING
        mock_svc = MagicMock()
        mock_svc.rpc.return_value.execute.return_value = MagicMock(
            data=[
                {"id": "r1", "content": "result1", "similarity": 0.92},
                {"id": "r2", "content": "result2", "similarity": 0.85},
            ]
        )
        mock_get_client.return_value = mock_svc

        results = search_memory(
            org_id="org-123",
            query="test query",
            agent_role="sales",
            limit=5,
        )

        assert len(results) == 2
        assert all(isinstance(r, MemoryRecord) for r in results)
        assert results[0].similarity == 0.92
        assert results[1].content == "result2"

    @patch("src.db.session.get_service_client")
    @patch("src.db.memory.embed")
    def test_search_memory_empty_result(self, mock_embed, mock_get_client):
        mock_embed.return_value = FIXED_EMBEDDING
        mock_svc = MagicMock()
        mock_svc.rpc.return_value.execute.return_value = MagicMock(data=[])
        mock_get_client.return_value = mock_svc

        results = search_memory(org_id="org-123", query="no results")

        assert results == []

    @patch("src.db.session.get_service_client")
    @patch("src.db.memory.embed")
    def test_search_memory_excludes_agent_role_when_none(
        self, mock_embed, mock_get_client
    ):
        """p_agent_role must NOT be sent when None (avoids serialisation as 'null')."""
        mock_embed.return_value = FIXED_EMBEDDING
        mock_svc = MagicMock()
        mock_svc.rpc.return_value.execute.return_value = MagicMock(data=[])
        mock_get_client.return_value = mock_svc

        search_memory(org_id="org-123", query="q", agent_role=None)

        _, rpc_params = mock_svc.rpc.call_args
        # p_agent_role must be absent from the positional args dict
        positional_params = mock_svc.rpc.call_args[0][1]
        assert "p_agent_role" not in positional_params

    @patch("src.db.session.get_service_client")
    @patch("src.db.memory.embed")
    def test_search_memory_includes_agent_role_when_set(
        self, mock_embed, mock_get_client
    ):
        mock_embed.return_value = FIXED_EMBEDDING
        mock_svc = MagicMock()
        mock_svc.rpc.return_value.execute.return_value = MagicMock(data=[])
        mock_get_client.return_value = mock_svc

        search_memory(org_id="org-123", query="q", agent_role="sales")

        positional_params = mock_svc.rpc.call_args[0][1]
        assert positional_params["p_agent_role"] == "sales"


class TestCleanupExpiredMemory:
    """cleanup_expired_memory() deletes expired records and returns count."""

    @patch("src.db.session.get_service_client")
    def test_cleanup_returns_deleted_count(self, mock_get_client):
        mock_svc = MagicMock()
        (
            mock_svc.table.return_value
            .delete.return_value
            .lt.return_value
            .eq.return_value
            .execute.return_value
        ) = MagicMock(data=[{"id": "1"}, {"id": "2"}])
        mock_get_client.return_value = mock_svc

        deleted = cleanup_expired_memory("org-123")

        assert deleted == 2

    @patch("src.db.session.get_service_client")
    def test_cleanup_returns_zero_when_nothing_deleted(self, mock_get_client):
        mock_svc = MagicMock()
        (
            mock_svc.table.return_value
            .delete.return_value
            .lt.return_value
            .eq.return_value
            .execute.return_value
        ) = MagicMock(data=[])
        mock_get_client.return_value = mock_svc

        deleted = cleanup_expired_memory("org-123")

        assert deleted == 0
