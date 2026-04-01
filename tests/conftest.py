"""Global test fixtures for FluxAgentPro-v2 Phase 2 + 3.

All Supabase, LLM, and OpenAI interactions are mocked so that tests run
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

    # Cache for table mocks to keep them stable
    table_mocks = {}

    def _make_chain(data=None):
        """Helper to create a chainable mock that defaults to empty list data."""
        if data is None:
            data = []
        chain = MagicMock()
        # Default response object
        response = MagicMock()
        response.data = data
        chain.execute.return_value = response
        
        # All chaining methods return the same chain by default
        chain.select.return_value = chain
        chain.insert.return_value = chain
        chain.upsert.return_value = chain
        chain.update.return_value = chain
        chain.delete.return_value = chain
        chain.eq.return_value = chain
        chain.neq.return_value = chain
        chain.gt.return_value = chain
        chain.lt.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain.like.return_value = chain
        chain.ilike.return_value = chain
        chain.is_.return_value = chain
        chain.in_.return_value = chain
        chain.maybe_single.return_value = chain
        chain.single.return_value = chain
        chain.limit.return_value = chain
        chain.order.return_value = chain
        chain.range.return_value = chain
        return chain

    def _table(table_name):
        if table_name not in table_mocks:
            table_mocks[table_name] = _make_chain()
        return table_mocks[table_name]

    client.table = MagicMock(side_effect=_table)

    # rpc().execute() chain
    rpc_chain = MagicMock()
    rpc_chain.execute = MagicMock(return_value=MagicMock(data=None))
    client.rpc = MagicMock(return_value=rpc_chain)

    return client


# ── service client fixture ─────────────────────────────────────

@pytest.fixture
def mock_service_client():
    """Mock for get_service_client() — patches multiple potential import points."""
    client = make_mock_client()
    
    # Patch points where get_service_client is imported and used
    patch_points = [
        "src.db.session.get_service_client",
        "src.db.vault.get_service_client",
        "src.flows.base_flow.get_service_client",
        "src.events.store.get_service_client",
        "src.tools.mcp_pool.get_service_client",
        "src.crews.base_crew.get_service_client",
    ]
    
    stack = []
    for p in patch_points:
        try:
            pt = patch(p, return_value=client)
            pt.start()
            stack.append(pt)
        except (AttributeError, ImportError):
            continue
            
    yield client
    
    for pt in stack:
        pt.stop()


# ── anon client fixture ────────────────────────────────────────

@pytest.fixture
def mock_anon_client():
    """Mock for get_anon_client() — patches multiple potential import points."""
    client = make_mock_client()
    patch_points = [
        "src.db.session.get_anon_client",
        "src.db.vault.get_anon_client",
        "src.flows.base_flow.get_anon_client",
    ]
    
    stack = []
    for p in patch_points:
        try:
            pt = patch(p, return_value=client)
            pt.start()
            stack.append(pt)
        except (AttributeError, ImportError):
            continue
            
    yield client
    
    for pt in stack:
        pt.stop()


# ── TenantClient fixture ────────────────────────────────────────

@pytest.fixture
def mock_tenant_client(mock_service_client):
    """
    Mock for get_tenant_client() context manager — patches multiple points.
    """
    mock_db = MagicMock()
    mock_db.table = mock_service_client.table
    mock_db.rpc = mock_service_client.rpc

    # Context manager mock behavior
    cm = MagicMock()
    cm.__enter__.return_value = mock_db
    cm.__exit__.return_value = False

    patch_points = [
        "src.db.session.get_tenant_client",
        "src.db.vault.get_tenant_client",
        "src.flows.base_flow.get_tenant_client",
        "src.guardrails.base_guardrail.get_tenant_client",
        "src.events.store.get_tenant_client",
        "src.flows.multi_crew_flow.get_tenant_client",
    ]
    
    stack = []
    for p in patch_points:
        try:
            pt = patch(p, return_value=cm)
            pt.start()
            stack.append(pt)
        except (AttributeError, ImportError):
            continue
            
    yield mock_db
    
    for pt in stack:
        pt.stop()


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
