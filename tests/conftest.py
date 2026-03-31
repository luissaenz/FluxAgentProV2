"""Global test fixtures for FluxAgentPro-v2 Phase 1.

All Supabase and LLM interactions are mocked so that tests run
without external dependencies.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4


# ── identity fixtures ───────────────────────────────────────────

@pytest.fixture
def sample_org_id() -> str:
    return str(uuid4())


@pytest.fixture
def sample_user_id() -> str:
    return str(uuid4())


@pytest.fixture
def sample_input_data() -> dict:
    return {"text": "Hello, World!"}


# ── Supabase mocks ─────────────────────────────────────────────

@pytest.fixture
def mock_supabase_client():
    """Fully mocked Supabase ``Client``."""
    client = MagicMock()

    # table().insert/upsert/update/select().eq().execute() chain
    table_mock = MagicMock()
    chain = MagicMock()
    chain.execute = MagicMock(return_value=MagicMock(data=[]))
    table_mock.insert = MagicMock(return_value=chain)
    table_mock.upsert = MagicMock(return_value=chain)
    table_mock.select = MagicMock(return_value=chain)
    table_mock.update = MagicMock(return_value=chain)
    chain.eq = MagicMock(return_value=chain)
    chain.order = MagicMock(return_value=chain)
    chain.limit = MagicMock(return_value=chain)

    client.table = MagicMock(return_value=table_mock)

    # rpc().execute() chain
    rpc_chain = MagicMock()
    rpc_chain.execute = MagicMock(return_value=MagicMock(data=None))
    client.rpc = MagicMock(return_value=rpc_chain)

    return client


@pytest.fixture
def mock_tenant_client(mock_supabase_client):
    """Patch ``get_tenant_client`` so every ``with`` block yields our mock."""
    with patch("src.db.session.get_supabase_client", return_value=mock_supabase_client):
        yield mock_supabase_client


# ── Event Store mock ───────────────────────────────────────────

@pytest.fixture
def mock_event_store():
    with patch("src.events.store.get_tenant_client") as mock_gtc:
        # make the context manager yield a mock db
        mock_db = MagicMock()
        chain = MagicMock()
        chain.execute = MagicMock(return_value=MagicMock(data=[]))
        mock_db.table = MagicMock(return_value=MagicMock(insert=MagicMock(return_value=chain)))
        mock_gtc.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_gtc.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_gtc
