"""tests/unit/test_factory.py — AgentFactory tests with MCP tool resolution.

Covers:
  - resolve_tools() for regular tools
  - resolve_tools() for MCP tools (async mode)
  - MCP tool skipping in sync mode
  - Malformed mcp: prefix handling
  - create_agent() and create_agent_async()
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.crews.factory import AgentFactory


class TestResolveTools:
    """AgentFactory.resolve_tools() behavior."""

    @patch("src.crews.factory.tool_registry")
    def test_resolves_regular_tools(self, mock_registry, sample_org_id):
        """Regular tools resolved via tool_registry."""
        mock_tool_cls = MagicMock()
        mock_tool_cls.return_value = MagicMock()
        mock_registry.get.return_value = mock_tool_cls

        tools = AgentFactory.resolve_tools(["db_read", "web_search"], sample_org_id)

        assert len(tools) == 2
        mock_registry.get.assert_any_call("db_read", org_id=sample_org_id)

    @patch("src.crews.factory.tool_registry")
    def test_skips_unknown_regular_tools(self, mock_registry, sample_org_id):
        """Unknown regular tools skipped with warning."""
        mock_registry.get.side_effect = ValueError("Not found")

        tools = AgentFactory.resolve_tools(["unknown"], sample_org_id)

        assert tools == []

    def test_handles_empty_tools(self, sample_org_id):
        """Empty tool list returns empty list."""
        tools = AgentFactory.resolve_tools([], sample_org_id)
        assert tools == []


class TestMCPToolResolution:
    """MCP tool resolution in resolve_tools()."""

    def test_mcp_skipped_in_sync_mode(self, sample_org_id, caplog):
        """MCP tools skipped in sync mode with warning."""
        tools = AgentFactory.resolve_tools(
            ["mcp:file_server:list_files"], sample_org_id, async_mode=False
        )

        assert tools == []
        assert "skipped in sync mode" in caplog.text

    def test_malformed_mcp_prefix_skipped(self, sample_org_id, caplog):
        """Malformed mcp: prefix (e.g., mcp:) skipped with warning."""
        tools = AgentFactory.resolve_tools(
            ["mcp:"], sample_org_id, async_mode=True
        )

        assert tools == []
        assert "Malformed MCP tool prefix" in caplog.text

    @patch("src.crews.factory.tool_registry")
    @patch("src.crews.factory.AgentFactory._resolve_mcp_tool")
    def test_mcp_resolved_in_async_mode(
        self, mock_resolve_mcp, mock_registry, sample_org_id
    ):
        """MCP tools resolved in async mode."""
        mock_tool = MagicMock()
        mock_tool.name = "list_files"
        mock_resolve_mcp.return_value = mock_tool

        tools = AgentFactory.resolve_tools(
            ["mcp:file_server:list_files"], sample_org_id, async_mode=True
        )

        assert len(tools) == 1
        mock_resolve_mcp.assert_called_once_with(
            sample_org_id, "file_server", "list_files"
        )

    @patch("src.crews.factory.AgentFactory._resolve_mcp_tool")
    def test_mcp_error_logged_and_skipped(self, mock_resolve_mcp, sample_org_id, caplog):
        """MCP resolution errors logged and tool skipped."""
        mock_resolve_mcp.side_effect = Exception("Connection failed")

        tools = AgentFactory.resolve_tools(
            ["mcp:file_server:list_files"], sample_org_id, async_mode=True
        )

        assert tools == []
        assert "Failed to resolve MCP tool" in caplog.text


class TestCreateAgent:
    """AgentFactory.create_agent() behavior."""

    @patch("src.crews.factory.tool_registry")
    @patch("src.crews.factory.get_settings")
    @patch("src.crews.factory.Agent")
    def test_create_agent_uses_resolve_tools(
        self, mock_agent_cls, mock_settings, mock_registry, sample_org_id
    ):
        """create_agent() uses resolve_tools() for tool resolution."""
        mock_settings.return_value.get_llm.return_value = MagicMock()
        mock_tool_cls = MagicMock()
        mock_tool_cls.return_value = MagicMock()
        mock_registry.get.return_value = mock_tool_cls
        mock_agent_cls.return_value = MagicMock()

        config = {
            "soul_json": {"role": "analyst", "goal": "Goal", "backstory": "Story"},
            "allowed_tools": ["db_read"],
            "max_iter": 5,
        }

        AgentFactory.create_agent(config, sample_org_id)

        mock_registry.get.assert_called_with("db_read", org_id=sample_org_id)
        mock_agent_cls.assert_called_once()

    @patch("src.crews.factory.get_settings")
    @patch("src.crews.factory.Agent")
    def test_create_agent_async_enables_mcp(
        self, mock_agent_cls, mock_settings, sample_org_id
    ):
        """create_agent_async() enables MCP tool resolution."""
        mock_settings.return_value.get_llm.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()

        config = {
            "soul_json": {"role": "analyst", "goal": "Goal", "backstory": "Story"},
            "allowed_tools": ["mcp:file_server:list_files"],
            "max_iter": 5,
        }

        with patch.object(
            AgentFactory, "resolve_tools", return_value=[]
        ) as mock_resolve:
            AgentFactory.create_agent_async(config, sample_org_id)

            mock_resolve.assert_called_once_with(
                ["mcp:file_server:list_files"], sample_org_id, async_mode=True
            )
