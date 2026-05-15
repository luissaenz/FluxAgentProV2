"""tests/unit/test_agent_run.py — Unit tests for `fap agent run` CLI command.

Tests:
- TP-5: Successful agent run → exit code 0
- TP-6: Agent not found (status failed) → exit code 1
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import typer

from src.cli.commands.agent_run import run_agent


class MockResponse:
    def __init__(self, status_code: int, json_data: dict | None = None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = ""

    def json(self):
        return self._json_data


def _make_run_response(task_id: str = "task-123") -> MockResponse:
    return MockResponse(202, {"task_id": task_id, "status": "accepted"})


def _make_poll_completed(tokens: int = 42, result: str = "OK") -> MockResponse:
    return MockResponse(200, {
        "task_id": "task-123",
        "status": "completed",
        "result": result,
        "tokens_used": tokens,
    })


def _make_poll_failed(error: str = "Agent 'noexiste' not found") -> MockResponse:
    return MockResponse(200, {
        "task_id": "task-123",
        "status": "failed",
        "error": error,
    })


def test_agent_run_success():
    """TP-5: CLI run_agent exits with code 0 on successful completion."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post = MagicMock(return_value=_make_run_response())
    mock_client.get = MagicMock(return_value=_make_poll_completed(tokens=42, result="Agent response"))

    with patch("httpx.Client", return_value=mock_client):
        with pytest.raises(typer.Exit) as exc_info:
            run_agent(
                role="test_agent",
                message="Hello",
                org_id="00000000-0000-0000-0000-000000000001",
                watch=False,
                timeout=120,
            )

    assert exc_info.value.exit_code == 0
    mock_client.post.assert_called_once()
    mock_client.get.assert_called()


def test_agent_run_role_not_found():
    """TP-6: CLI run_agent exits with code 1 when agent not found (status failed)."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post = MagicMock(return_value=_make_run_response())
    mock_client.get = MagicMock(return_value=_make_poll_failed("Agent 'nonexistent' not found"))

    with patch("httpx.Client", return_value=mock_client):
        with pytest.raises(typer.Exit) as exc_info:
            run_agent(
                role="nonexistent",
                message="Test",
                org_id="00000000-0000-0000-0000-000000000001",
                watch=False,
                timeout=120,
            )

    assert exc_info.value.exit_code == 1
    mock_client.post.assert_called_once()
    mock_client.get.assert_called()


def test_agent_run_connection_error():
    """CLI run_agent exits with code 1 on connection error."""
    with patch("httpx.Client", side_effect=Exception("Connection refused")):
        with pytest.raises(typer.Exit) as exc_info:
            run_agent(
                role="test",
                message="Hello",
                org_id="00000000-0000-0000-0000-000000000001",
                watch=False,
                timeout=120,
            )

    assert exc_info.value.exit_code == 1
