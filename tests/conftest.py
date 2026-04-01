"""Global test fixtures for FluxAgentPro-v2 Phase 2.

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


# ── Supabase mock factory ──────────────────────────────────────

def make_mock_client():
    """Build a fully-mocked Supabase Client."""
    client = MagicMock()

    # rpc().execute() chain
    rpc_chain = MagicMock()
    rpc_chain.execute = MagicMock(return_value=MagicMock(data=None))
    client.rpc = MagicMock(return_value=rpc_chain)

    # table().X().Y().eq().execute() chain
    def _make_chain(data=None):
        chain = MagicMock()
        chain.execute = MagicMock(return_value=MagicMock(data=data))
        return chain

    def _table(table_name):
        tbl = MagicMock()
        tbl.insert = MagicMock(return_value=_make_chain())
        tbl.upsert = MagicMock(return_value=_make_chain())
        tbl.update = MagicMock(return_value=_make_chain())
        tbl.delete = MagicMock(return_value=_make_chain())
        tbl.select = MagicMock(return_value=_make_chain())
        return tbl

    client.table = _table
    return client


# ── service client fixture ─────────────────────────────────────

@pytest.fixture
def mock_service_client():
    """Mock for get_service_client() — bypasses RLS."""
    client = make_mock_client()
    with patch("src.db.session.get_service_client", return_value=client):
        yield client


# ── anon client fixture ────────────────────────────────────────

@pytest.fixture
def mock_anon_client():
    """Mock for get_anon_client() — respects RLS."""
    client = make_mock_client()
    with patch("src.db.session.get_anon_client", return_value=client):
        yield client


# ── TenantClient fixture ────────────────────────────────────────

@pytest.fixture
def mock_tenant_client(mock_service_client):
    """
    Mock for get_tenant_client() context manager.

    Usage::

        with mock_tenant_client as db:
            db.table("tasks").select("*").execute()
    """
    mock_db = MagicMock()
    mock_db.table = mock_service_client.table
    mock_db.rpc = mock_service_client.rpc

    with patch("src.db.session.get_service_client", return_value=mock_service_client):
        with patch("src.db.session.TenantClient") as MockTC:
            MockTC.return_value.__enter__ = MagicMock(return_value=mock_db)
            MockTC.return_value.__exit__ = MagicMock(return_value=False)
            yield mock_db


# ── Event Store mock ────────────────────────────────────────────

@pytest.fixture
def mock_event_store():
    """Mock the EventStore so flush() is a no-op."""
    with patch("src.events.store.get_tenant_client") as mock_gtc:
        mock_db = MagicMock()
        chain = MagicMock()
        chain.execute = MagicMock(return_value=MagicMock(data=[]))
        mock_db.table = MagicMock(return_value=MagicMock(insert=MagicMock(return_value=chain)))
        mock_gtc.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_gtc.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_gtc
