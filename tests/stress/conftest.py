"""Local conftest for stress tests — isolates from global conftest.

Provides shared fixtures: MCPPool reset, flow_registry save/restore.
"""

from __future__ import annotations

import pytest

from src.flows.registry import flow_registry
from src.tools.mcp_pool import MCPPool


@pytest.fixture(autouse=True)
def _reset_pool():
    """Reset singleton MCPPool before and after each stress test."""
    MCPPool.reset()
    yield
    MCPPool.reset()


@pytest.fixture(autouse=True)
def _clean_flow_registry():
    """Save and restore flow_registry to isolate stress tests."""
    saved_flows = dict(flow_registry._flows)
    saved_metadata = dict(flow_registry._metadata)
    yield
    flow_registry._flows.clear()
    flow_registry._flows.update(saved_flows)
    flow_registry._metadata.clear()
    flow_registry._metadata.update(saved_metadata)
