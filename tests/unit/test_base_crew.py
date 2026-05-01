"""tests/unit/test_base_crew.py — Phase 3 BaseCrew tests.

Covers:
  - Agent loading from agent_catalog
  - Tool resolution
  - run() and run_async() behavior
  - Error handling for missing agents
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crews.base_crew import BaseCrew, CrewConfigError

# Import conftest fixtures


# ── Agent loading tests ─────────────────────────────────────────


class TestAgentLoading:
    """BaseCrew agent loading from agent_catalog."""

    def test_loads_agent_from_catalog(self, sample_org_id):
        """BaseCrew loads agent definition from agent_catalog."""
        agent_data = {
            "id": "agent-123",
            "org_id": sample_org_id,
            "role": "analyst",
            "name": "Data Analyst",
            "soul_json": {
                "role": "analyst",
                "goal": "Analyze data thoroughly",
                "backstory": "You are an expert analyst.",
            },
            "allowed_tools": ["db_read", "web_search"],
            "model": "claude-sonnet-4-20250514",
            "max_iter": 5,
            "is_active": True,
        }

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table

        mock_execute = MagicMock()
        mock_execute.data = agent_data
        mock_table.execute.return_value = mock_execute

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table

        with patch("src.crews.base_crew.get_service_client", return_value=mock_client):
            crew = BaseCrew(org_id=sample_org_id, role="analyst")
            config = crew._load_agent_config()

            assert config["role"] == "analyst"
            assert config["soul_json"]["goal"] == "Analyze data thoroughly"
            assert config["allowed_tools"] == ["db_read", "web_search"]

    def test_raises_when_agent_not_found(self, sample_org_id):
        """BaseCrew raises CrewConfigError when agent not found."""
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table

        mock_execute = MagicMock()
        mock_execute.data = None
        mock_table.execute.return_value = mock_execute

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table

        with patch("src.crews.base_crew.get_service_client", return_value=mock_client):
            crew = BaseCrew(org_id=sample_org_id, role="nonexistent_role")

            with pytest.raises(CrewConfigError, match="No active agent"):
                crew._load_agent_config()

    def test_raises_when_agent_inactive(self, sample_org_id):
        """BaseCrew raises when agent is inactive."""
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table

        mock_execute = MagicMock()
        mock_execute.data = None
        mock_table.execute.return_value = mock_execute

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table

        with patch("src.crews.base_crew.get_service_client", return_value=mock_client):
            crew = BaseCrew(org_id=sample_org_id, role="inactive_agent")

            with pytest.raises(CrewConfigError):
                crew._load_agent_config()

    def test_caches_agent_config(self, sample_org_id):
        """BaseCrew caches agent config after first load."""
        agent_data = {
            "org_id": sample_org_id,
            "role": "analyst",
            "soul_json": {"role": "analyst", "goal": "Goal", "backstory": "Backstory"},
            "allowed_tools": [],
            "model": "claude-sonnet-4-20250514",
            "max_iter": 5,
            "is_active": True,
        }

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table

        mock_execute = MagicMock()
        mock_execute.data = agent_data
        mock_table.execute.return_value = mock_execute

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table

        with patch("src.crews.base_crew.get_service_client", return_value=mock_client):
            crew = BaseCrew(org_id=sample_org_id, role="analyst")

            config1 = crew._load_agent_config()
            config2 = crew._load_agent_config()

            assert mock_table.select.call_count == 1
            assert config1 is config2


# ── Tool resolution tests ───────────────────────────────────────


class TestToolResolution:
    """BaseCrew._resolve_tools() behavior."""

    @patch("src.crews.factory.tool_registry")
    def test_resolves_tools_from_registry(self, mock_registry, sample_org_id):
        """BaseCrew resolves tool names to instances via AgentFactory."""
        from src.crews.factory import AgentFactory

        mock_tool_class = MagicMock()
        mock_tool_instance = MagicMock()
        mock_tool_class.return_value = mock_tool_instance
        mock_registry.get.return_value = mock_tool_class

        tools = AgentFactory.resolve_tools(["db_read", "web_search"], sample_org_id)

        assert len(tools) == 2
        mock_registry.get.assert_any_call("db_read", org_id=sample_org_id)
        mock_registry.get.assert_any_call("web_search", org_id=sample_org_id)
        mock_tool_class.assert_called_with(org_id=sample_org_id)

    @patch("src.crews.factory.tool_registry")
    def test_skips_unknown_tools(self, mock_registry, sample_org_id):
        """BaseCrew skips tools not in registry."""
        from src.crews.factory import AgentFactory

        mock_registry.get.side_effect = ValueError("Tool not found")

        tools = AgentFactory.resolve_tools(
            ["unknown_tool", "another_unknown"], sample_org_id
        )

        assert len(tools) == 0

    @patch("src.crews.factory.tool_registry")
    def test_handles_empty_allowed_tools(self, mock_registry, sample_org_id):
        """BaseCrew handles empty allowed_tools list."""
        from src.crews.factory import AgentFactory

        tools = AgentFactory.resolve_tools([], sample_org_id)

        assert tools == []

    def test_resolve_tools_delegates_to_factory(self, sample_org_id):
        """BaseCrew._resolve_tools delegates to AgentFactory.resolve_tools."""
        from src.crews.factory import AgentFactory

        with patch.object(
            AgentFactory, "resolve_tools", return_value=[MagicMock()]
        ) as mock_resolve:
            crew = BaseCrew(org_id=sample_org_id, role="analyst")
            tools = crew._resolve_tools(["db_read"])

            mock_resolve.assert_called_once_with(["db_read"], sample_org_id)
            assert len(tools) == 1


# ── run() method tests ──────────────────────────────────────────


class TestRunMethod:
    """BaseCrew.run() synchronous execution."""

    def test_run_builds_and_executes_crew(self, sample_org_id):
        """BaseCrew.run() builds agent, task, and crew correctly."""
        agent_config = {
            "org_id": sample_org_id,
            "role": "analyst",
            "soul_json": {
                "role": "analyst",
                "goal": "Analyze data",
                "backstory": "Expert analyst",
            },
            "allowed_tools": [],
            "model": "claude-sonnet-4-20250514",
            "max_iter": 5,
            "is_active": True,
        }

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table

        mock_execute = MagicMock()
        mock_execute.data = agent_config
        mock_table.execute.return_value = mock_execute

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table

        mock_settings = MagicMock()

        with patch("src.crews.base_crew.get_service_client", return_value=mock_client):
            with patch("src.crews.base_crew.get_settings", return_value=mock_settings):
                with patch("src.crews.factory.get_settings", return_value=mock_settings):
                    with patch("src.crews.factory.AgentFactory.create_agent") as mock_create:
                        with patch("crewai.Task") as mock_task_cls:
                            with patch("crewai.Crew") as mock_crew_cls:
                                mock_agent = MagicMock()
                                mock_create.return_value = mock_agent

                                mock_task = MagicMock()
                                mock_task_cls.return_value = mock_task

                                mock_crew = MagicMock()
                                mock_crew_cls.return_value = mock_crew
                                mock_crew.kickoff.return_value = MagicMock(raw="Result")

                                crew = BaseCrew(org_id=sample_org_id, role="analyst")
                                crew.run(
                                    task_description="Analyze this data",
                                    inputs={"data": "test"},
                                    expected_output="Detailed analysis",
                                )

                                mock_create.assert_called_once_with(agent_config, sample_org_id)

                                mock_crew.kickoff.assert_called_once_with(
                                    inputs={"data": "test"}
                                )

    def test_run_uses_default_expected_output(self, sample_org_id):
        """BaseCrew.run() uses default expected_output if not provided."""
        agent_config = {
            "org_id": sample_org_id,
            "role": "analyst",
            "soul_json": {
                "role": "analyst",
                "goal": "Goal",
                "backstory": "Backstory",
            },
            "allowed_tools": [],
            "model": "claude-sonnet-4-20250514",
            "max_iter": 5,
            "is_active": True,
        }

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table

        mock_execute = MagicMock()
        mock_execute.data = agent_config
        mock_table.execute.return_value = mock_execute

        mock_client = MagicMock()
        mock_client.table.return_value = mock_table

        mock_settings = MagicMock()

        with patch("src.crews.base_crew.get_service_client", return_value=mock_client):
            with patch("src.crews.base_crew.get_settings", return_value=mock_settings):
                with patch("crewai.Agent"):
                    with patch("crewai.Task") as mock_task_cls:
                        with patch("crewai.Crew") as mock_crew_cls:
                            mock_crew = MagicMock()
                            mock_crew_cls.return_value = mock_crew
                            mock_crew.kickoff.return_value = MagicMock(raw="Result")

                            crew = BaseCrew(org_id=sample_org_id, role="analyst")
                            crew.run(task_description="Do something")

                            task_call_kwargs = mock_task_cls.call_args[1]
                            assert (
                                "Structured result"
                                in task_call_kwargs["expected_output"]
                            )


# ── run_async() method tests ────────────────────────────────────


class TestRunAsyncMethod:
    """BaseCrew.run_async() asynchronous execution."""

    @pytest.mark.asyncio
    async def test_run_async_builds_and_executes_crew(self, sample_org_id):
        """BaseCrew.run_async() builds and executes crew asynchronously."""
        agent_data = {
            "org_id": sample_org_id,
            "role": "analyst",
            "soul_json": {
                "role": "analyst",
                "goal": "Goal",
                "backstory": "Backstory",
            },
            "allowed_tools": [],
            "model": "claude-sonnet-4-20250514",
            "max_iter": 5,
            "is_active": True,
        }

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = agent_data
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result

        mock_settings = MagicMock()

        with patch("src.crews.base_crew.get_service_client", return_value=mock_db):
            with patch("src.crews.base_crew.get_settings", return_value=mock_settings):
                with patch("src.crews.factory.get_settings", return_value=mock_settings):
                    with patch(
                        "src.crews.factory.AgentFactory.create_agent_async"
                    ) as mock_create:
                        with patch("crewai.Task"):
                            with patch("crewai.Crew") as mock_crew_cls:
                                mock_agent = MagicMock()
                                mock_create.return_value = mock_agent

                                mock_crew = MagicMock()
                                mock_crew_cls.return_value = mock_crew
                                mock_crew.kickoff_async = AsyncMock(
                                    return_value=MagicMock(raw="Async Result")
                                )

                                crew = BaseCrew(org_id=sample_org_id, role="analyst")
                                await crew.run_async(
                                    task_description="Async analysis",
                                    inputs={"data": "test"},
                                )

                                assert mock_create.called
                                mock_crew.kickoff_async.assert_called_once()


# ── kickoff_async() alias tests ─────────────────────────────────


class TestKickoffAsyncAlias:
    """BaseCrew.kickoff_async() alias behavior."""

    @patch("src.crews.base_crew.get_service_client")
    @patch("src.crews.base_crew.get_settings")
    @pytest.mark.asyncio
    async def test_kickoff_async_calls_run_async(
        self, mock_get_settings, mock_get_svc, sample_org_id
    ):
        """kickoff_async() is an alias for run_async()."""
        mock_svc = MagicMock()
        mock_get_svc.return_value = mock_svc

        mock_svc.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={
                "org_id": sample_org_id,
                "role": "analyst",
                "soul_json": {
                    "role": "analyst",
                    "goal": "Goal",
                    "backstory": "Backstory",
                },
                "allowed_tools": [],
                "model": "claude-sonnet-4-20250514",
                "max_iter": 5,
                "is_active": True,
            }
        )

        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        crew = BaseCrew(org_id=sample_org_id, role="analyst")

        with patch.object(crew, "run_async", new_callable=AsyncMock) as mock_run_async:
            await crew.kickoff_async(inputs={"test": "data"})

            mock_run_async.assert_called_once()
