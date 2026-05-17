"""tests/e2e/conftest.py — Builder-specific fixtures.

Moved from global conftest.py to avoid autouse interference with
non-builder test suites (Analysis-FINAL §ID-052).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True, scope="session")
def global_llm_mock():
    """Automatically mock all major LLM provider entry points.

    Scoped to the e2e directory so it does NOT affect unit tests
    or integration tests that may need real LLM interactions.
    """
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
