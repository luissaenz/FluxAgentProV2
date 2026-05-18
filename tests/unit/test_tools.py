"""tests/unit/test_tools.py — Unit tests for tools endpoint (Paso 15, ID-002)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.tools.registry import ToolMetadata

TEST_ORG_ID = "00000000-0000-0000-0000-000000000001"

HEADERS = {"X-Org-ID": TEST_ORG_ID}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_registry():
    """Mock tool_registry with sample local tools."""
    registry = MagicMock()
    registry.list_tools.return_value = ["fetch_url", "search", "code_analyzer"]
    registry.get_metadata.side_effect = lambda name: {
        "fetch_url": ToolMetadata(
            name="fetch_url",
            description="Fetch a URL",
            tags=["web", "utility"],
            parameters={},
            requires_approval=False,
            timeout_seconds=30,
        ),
        "search": ToolMetadata(
            name="search",
            description="Search the web",
            tags=["web", "search"],
            parameters={},
            requires_approval=False,
            timeout_seconds=30,
        ),
        "code_analyzer": ToolMetadata(
            name="code_analyzer",
            description="Analyze source code",
            tags=["development", "code"],
            parameters={},
            requires_approval=False,
            timeout_seconds=30,
        ),
    }.get(name)
    return registry


class TestToolsEndpoint:
    def _get(self, client, path: str = "/api/tools/available", params: str = "") -> Any:
        return client.get(f"{path}?{params}" if params else path, headers=HEADERS)

    def test_list_empty_registry(self, client):
        """No tools registered → empty list."""
        reg = MagicMock()
        reg.list_tools.return_value = []
        with patch("src.api.routes.tools.tool_registry", reg):
            with patch("src.api.routes.tools._fetch_mcp_tools", AsyncMock(return_value=[])):
                resp = self._get(client)
        assert resp.status_code == 200
        body = resp.json()
        assert body["tools"] == []
        assert body["count"] == 0

    def test_list_local_tools(self, client, mock_registry):
        """Local tools returned with correct structure."""
        with patch("src.api.routes.tools.tool_registry", mock_registry):
            with patch("src.api.routes.tools._fetch_mcp_tools", AsyncMock(return_value=[])):
                resp = self._get(client)
        assert resp.status_code == 200
        body = resp.json()
        tools = body["tools"]
        tool_names = [t["name"] for t in tools]
        assert "fetch_url" in tool_names
        assert "search" in tool_names
        assert "code_analyzer" in tool_names
        assert body["count"] == 3

        fetch_url = next(t for t in tools if t["name"] == "fetch_url")
        assert fetch_url["source"] == "local"
        assert fetch_url["description"] == "Fetch a URL"
        assert fetch_url["is_active"] is True

    def test_list_filter_source_local(self, client, mock_registry):
        """Filter by source=local returns only local tools."""
        with patch("src.api.routes.tools.tool_registry", mock_registry):
            with patch("src.api.routes.tools._fetch_mcp_tools", AsyncMock(return_value=[])):
                resp = self._get(client, params="source=local")
        assert resp.status_code == 200
        body = resp.json()
        assert all(t["source"] == "local" for t in body["tools"])
        assert body["count"] == 3

    def test_list_filter_source_mcp(self, client, mock_registry):
        """Filter by source=mcp returns only MCP tools."""
        mcp_tools = [
            {
                "name": "mcp:server-a:read_file",
                "description": "Read file via MCP",
                "category": "server-a",
                "categories": ["mcp", "server-a"],
                "source": "mcp",
                "parameters": {},
                "requires_approval": False,
                "timeout_seconds": 30,
                "is_active": True,
            }
        ]
        with patch("src.api.routes.tools.tool_registry", mock_registry):
            with patch("src.api.routes.tools._fetch_mcp_tools", AsyncMock(return_value=mcp_tools)):
                resp = self._get(client, params="source=mcp")
        assert resp.status_code == 200
        body = resp.json()
        assert all(t["source"] == "mcp" for t in body["tools"])
        assert body["count"] == 1

    def test_list_filter_category(self, client, mock_registry):
        """Filter by category returns only matching tools."""
        with patch("src.api.routes.tools.tool_registry", mock_registry):
            with patch("src.api.routes.tools._fetch_mcp_tools", AsyncMock(return_value=[])):
                resp = self._get(client, params="category=web")
        assert resp.status_code == 200
        body = resp.json()
        tool_names = [t["name"] for t in body["tools"]]
        assert "fetch_url" in tool_names
        assert "search" in tool_names
        assert "code_analyzer" not in tool_names
        assert body["count"] == 2

    def test_list_includes_mcp_tools(self, client, mock_registry):
        """MCP tools are included alongside local tools."""
        mcp_tools = [
            {
                "name": "mcp:server-a:list_files",
                "description": "List files via MCP",
                "category": "server-a",
                "categories": ["mcp", "server-a"],
                "source": "mcp",
                "parameters": {},
                "requires_approval": False,
                "timeout_seconds": 30,
                "is_active": True,
            }
        ]
        with patch("src.api.routes.tools.tool_registry", mock_registry):
            with patch("src.api.routes.tools._fetch_mcp_tools", AsyncMock(return_value=mcp_tools)):
                resp = self._get(client)
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 4  # 3 local + 1 mcp
        mcp_names = [t["name"] for t in body["tools"] if t["source"] == "mcp"]
        assert "mcp:server-a:list_files" in mcp_names

    def test_mcp_graceful_degradation(self, client, mock_registry):
        """MCP failure returns local tools without error."""
        with patch("src.api.routes.tools.tool_registry", mock_registry):
            with patch("src.api.routes.tools._fetch_mcp_tools", AsyncMock(side_effect=Exception("MCP down"))):
                resp = self._get(client)
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 3  # Only local tools
        assert all(t["source"] == "local" for t in body["tools"])

    def test_tools_count_matches(self, client, mock_registry):
        """count field matches actual tools array length."""
        with patch("src.api.routes.tools.tool_registry", mock_registry):
            with patch("src.api.routes.tools._fetch_mcp_tools", AsyncMock(return_value=[])):
                resp = self._get(client)
        body = resp.json()
        assert len(body["tools"]) == body["count"]
