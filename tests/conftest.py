"""Global test fixtures for FluxAgentPro-v2 Phase 2 + 3.

All Supabase, LLM, and OpenAI interactions are mocked so that tests run
without external dependencies.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

if sys.platform == "win32" and sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

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

        # Support execute_with_retry pattern from session.py
        chain.execute_with_retry.side_effect = lambda x: (
            x.execute() if hasattr(x, "execute") else x
        )

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

    # client.execute_with_retry(query) pattern
    client.execute_with_retry = MagicMock(
        side_effect=lambda x: x.execute() if hasattr(x, "execute") else x
    )

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
        "src.tools.service_connector.get_service_client",
        "src.crews.base_crew.get_service_client",
        "src.services.warmup.get_service_client",
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
    mock_db.execute_with_retry = mock_service_client.execute_with_retry

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
        "src.api.routes.tickets.get_tenant_client",
        "src.api.routes.tasks.get_tenant_client",
        "src.api.routes.webhooks.get_tenant_client",
        "src.api.routes.workflows.get_tenant_client",
        "src.api.routes.agents.get_tenant_client",
        "src.api.routes.tools.get_tenant_client",
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
        mock_db.table = MagicMock(
            return_value=MagicMock(insert=MagicMock(return_value=chain))
        )
        mock_gtc.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_gtc.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_gtc


# ── LLM Mocking ──────────────────────────────────────────────────


class MockLLMManager:
    """Mock manager for LLM interactions."""

    def __init__(self):
        self.responses = []
        self.last_call = None

    def add_response(self, content: str):
        self.responses.append(content)

    def __call__(self, *args, **kwargs):
        self.last_call = {"args": args, "kwargs": kwargs}
        if self.responses:
            return self.responses.pop(0)

        # Retornar JSON si detectamos peticiones a pydantic o response_format
        if "response_format" in kwargs or "pydantic" in str(kwargs).lower():
            return '{"status": "success", "data": "mocked"}'

        return "Default Mocked LLM Response"


@pytest.fixture
def mock_llm_manager():
    return MockLLMManager()


# Ensure missing LLM modules don't break test discovery/execution
for mod_name in [
    "langchain_openai",
    "langchain_community",
    "langchain_community.chat_models",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()


@pytest.fixture(autouse=True)
def global_llm_mock():
    """Automatically mock all major LLM provider entry points."""
    with (
        patch("langchain_openai.ChatOpenAI") as mock_openai,
        patch("langchain_community.chat_models.ChatOllama") as mock_ollama,
        patch("crewai.Agent") as mock_agent,
        patch("crewai.Task") as mock_task,
        patch("crewai.Crew") as mock_crew,
    ):
        # Setup default mock responses
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = MagicMock(content="Mocked LLM Result")
        mock_openai.return_value = mock_instance
        mock_ollama.return_value = mock_instance

        mock_crew_instance = MagicMock()
        mock_crew_instance.kickoff.return_value = MagicMock(raw="Mocked Crew Result")
        mock_crew_instance.kickoff_async = AsyncMock(
            return_value=MagicMock(raw="Mocked Crew Result")
        )
        mock_crew.return_value = mock_crew_instance

        yield {
            "openai": mock_openai,
            "ollama": mock_ollama,
            "crew": mock_crew,
            "agent": mock_agent,
            "task": mock_task,
        }


@pytest.fixture
def mock_mcp_pool():
    """Mock MCPPool.get_tools() to return simulated MCP tools without real infrastructure."""
    from unittest.mock import AsyncMock, MagicMock

    mock_tools = []
    for tool_name in ["list_files", "read_file", "write_file"]:
        mock_tool = MagicMock()
        mock_tool.name = tool_name
        mock_tools.append(mock_tool)

    mock_pool = MagicMock()
    mock_pool.get_tools = AsyncMock(return_value=mock_tools)
    return mock_pool


@pytest.fixture
def mock_service_connector():
    """Mock ServiceConnectorTool._run() for testing without real HTTP calls."""
    from unittest.mock import MagicMock

    mock_tool = MagicMock()
    mock_tool._run = MagicMock(
        return_value='{"status": "success", "data": "mocked_response"}'
    )
    return mock_tool


@pytest.fixture
def sample_agent_config():
    """Sample agent configuration for tests."""
    return {
        "soul_json": {
            "role": "test_agent",
            "goal": "Test agent goal that is long enough",
            "backstory": "Test agent backstory that is long enough",
        },
        "allowed_tools": [],
        "max_iter": 3,
    }


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for ArchitectFlow tests."""
    import json

    def make_response(workflow_json: dict):
        return json.dumps(workflow_json)

    return make_response
