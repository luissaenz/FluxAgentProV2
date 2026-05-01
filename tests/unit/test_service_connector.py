"""Unit tests: ServiceConnectorTool error paths — Paso 1, Gap 2.

Tests U2.1-U2.7: 7 modos de fallo en ServiceConnectorTool._run().
Estrategia mocking: patch httpx.Client para HTTP, patch get_secret para Vault.
6 ramas error, 7 tests (U2.4 y U2.5 comparten mismo branch HTTPStatusError).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.db.vault import VaultError
from src.tools.service_connector import ServiceConnectorTool


@pytest.fixture
def _mock_get_service_client(mock_service_client):
    """Configure mock_service_client fixture to work with ServiceConnectorTool."""
    yield mock_service_client


def _build_tool(org_id: str = "test_org_123") -> ServiceConnectorTool:
    """Build a ServiceConnectorTool instance with given org_id."""
    return ServiceConnectorTool(org_id=org_id)


# ── U2.1: Tool no encontrada en service_tools ──────────────────


def test_run_tool_not_found(mock_service_client):
    """U2.1: Tool ID inexistente → retorna string descriptivo."""
    mock_service_client.reset_mock()
    chain = mock_service_client.table.return_value
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute.return_value.data = None

    tool = _build_tool()
    result = tool._run(tool_id="fake_tool", input_data={})

    assert "Error: Tool 'fake_tool' no encontrada" in result


# ── U2.2: Servicio no activo para la org ───────────────────────


def test_run_service_inactive(mock_service_client):
    """U2.2: Servicio no activo → retorna error descriptivo."""
    mock_service_client.reset_mock()

    def _table_side_effect(name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        if name == "service_tools":
            chain.execute.return_value.data = {
                "id": "tool_1",
                "service_id": "svc_1",
                "execution": {"url": "https://example.com/api"},
            }
        elif name == "org_service_integrations":
            chain.execute.return_value.data = None
        else:
            chain.execute.return_value.data = None
        return chain

    mock_service_client.table.side_effect = _table_side_effect

    tool = _build_tool()
    result = tool._run(tool_id="tool_1", input_data={})

    assert "no está activo para esta organización" in result


# ── U2.3: VaultError al obtener secreto ────────────────────────


def test_run_vault_error(mock_service_client):
    """U2.3: VaultError → retorna error descriptivo."""
    mock_service_client.reset_mock()

    def _table_side_effect(name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        if name == "service_tools":
            chain.execute.return_value.data = {
                "id": "tool_1",
                "service_id": "svc_1",
                "execution": {"url": "https://example.com/api"},
            }
        elif name == "org_service_integrations":
            chain.execute.return_value.data = {
                "org_id": "test_org_123",
                "service_id": "svc_1",
                "status": "active",
                "secret_names": ["secret_1"],
            }
        else:
            chain.execute.return_value.data = None
        return chain

    mock_service_client.table.side_effect = _table_side_effect

    with patch(
        "src.tools.service_connector.get_secret",
        side_effect=VaultError("Secreto no encontrado"),
    ):
        tool = _build_tool()
        result = tool._run(tool_id="tool_1", input_data={})

    assert "Error:" in result
    assert "Secreto no encontrado" in result


# ── U2.4: HTTP 401 ─────────────────────────────────────────────


def test_run_http_401(mock_service_client):
    """U2.4: HTTP 401 Unauthorized → retorna 'Error HTTP: 401'."""
    mock_service_client.reset_mock()

    def _table_side_effect(name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        if name == "service_tools":
            chain.execute.return_value.data = {
                "id": "tool_1",
                "service_id": "svc_1",
                "execution": {"url": "https://example.com/api", "method": "POST"},
            }
        elif name == "org_service_integrations":
            chain.execute.return_value.data = {
                "org_id": "test_org_123",
                "service_id": "svc_1",
                "status": "active",
                "secret_names": [],
            }
        elif name == "domain_events":
            chain.insert.return_value = chain
            chain.execute.return_value.data = []
        else:
            chain.execute.return_value.data = None
        return chain

    mock_service_client.table.side_effect = _table_side_effect

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("HTTP error")
    mock_response.status_code = 401
    mock_response.is_success = False

    import httpx

    mock_http_error = httpx.HTTPStatusError(
        "401 Unauthorized", request=MagicMock(), response=mock_response
    )

    with patch("httpx.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.request.return_value = mock_response
        mock_client_instance.request.return_value.raise_for_status.side_effect = (
            mock_http_error
        )
        mock_client_class.return_value = mock_client_instance

        tool = _build_tool()
        result = tool._run(tool_id="tool_1", input_data={})

    assert "Error HTTP: 401" in str(result)


# ── U2.5: HTTP 500 ─────────────────────────────────────────────


def test_run_http_500(mock_service_client):
    """U2.5: HTTP 500 Internal Server Error → retorna 'Error HTTP: 500'."""
    mock_service_client.reset_mock()

    def _table_side_effect(name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        if name == "service_tools":
            chain.execute.return_value.data = {
                "id": "tool_1",
                "service_id": "svc_1",
                "execution": {"url": "https://example.com/api", "method": "POST"},
            }
        elif name == "org_service_integrations":
            chain.execute.return_value.data = {
                "org_id": "test_org_123",
                "service_id": "svc_1",
                "status": "active",
                "secret_names": [],
            }
        elif name == "domain_events":
            chain.insert.return_value = chain
            chain.execute.return_value.data = []
        else:
            chain.execute.return_value.data = None
        return chain

    mock_service_client.table.side_effect = _table_side_effect

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.is_success = False

    import httpx

    mock_http_error = httpx.HTTPStatusError(
        "500 Internal Server Error", request=MagicMock(), response=mock_response
    )

    with patch("httpx.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.request.return_value = mock_response
        mock_client_instance.request.return_value.raise_for_status.side_effect = (
            mock_http_error
        )
        mock_client_class.return_value = mock_client_instance

        tool = _build_tool()
        result = tool._run(tool_id="tool_1", input_data={})

    assert "Error HTTP: 500" in str(result)


# ── U2.6: httpx.ConnectError ───────────────────────────────────


def test_run_connect_error(mock_service_client):
    """U2.6: Error de conexión (RequestError) → retorna 'Error HTTP:'."""
    mock_service_client.reset_mock()

    def _table_side_effect(name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        if name == "service_tools":
            chain.execute.return_value.data = {
                "id": "tool_1",
                "service_id": "svc_1",
                "execution": {"url": "https://example.com/api", "method": "POST"},
            }
        elif name == "org_service_integrations":
            chain.execute.return_value.data = {
                "org_id": "test_org_123",
                "service_id": "svc_1",
                "status": "active",
                "secret_names": [],
            }
        elif name == "domain_events":
            chain.insert.return_value = chain
            chain.execute.return_value.data = []
        else:
            chain.execute.return_value.data = None
        return chain

    mock_service_client.table.side_effect = _table_side_effect

    import httpx

    connect_error = httpx.ConnectError("Connection refused")

    with patch("httpx.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.request.side_effect = connect_error
        mock_client_class.return_value = mock_client_instance

        tool = _build_tool()
        result = tool._run(tool_id="tool_1", input_data={})

    assert "Error HTTP:" in str(result)
    assert "Connection refused" in str(result)


# ── U2.7: Non-JSON response truncado ≤ 500 chars ───────────────


def test_run_non_json_response_truncated(mock_service_client):
    """U2.7: Response no-JSON → truncado a 500 chars sin crash."""
    mock_service_client.reset_mock()

    def _table_side_effect(name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        if name == "service_tools":
            chain.execute.return_value.data = {
                "id": "tool_1",
                "service_id": "svc_1",
                "execution": {"url": "https://example.com/api", "method": "POST"},
            }
        elif name == "org_service_integrations":
            chain.execute.return_value.data = {
                "org_id": "test_org_123",
                "service_id": "svc_1",
                "status": "active",
                "secret_names": [],
            }
        elif name == "domain_events":
            chain.insert.return_value = chain
            chain.execute.return_value.data = []
        else:
            chain.execute.return_value.data = None
        return chain

    mock_service_client.table.side_effect = _table_side_effect

    long_text = "x" * 800

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.text = long_text
    mock_response.json.side_effect = Exception("Not JSON")

    with patch("httpx.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.request.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        tool = _build_tool()
        result = tool._run(tool_id="tool_1", input_data={})

    assert isinstance(result, str)
    assert len(result) <= 500
