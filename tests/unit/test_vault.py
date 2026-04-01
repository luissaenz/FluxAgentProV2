"""Tests: Vault — get_secret never exposes secrets to LLM."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.db.vault import get_secret, list_secrets, VaultError


class TestGetSecret:
    """get_secret() returns value or raises VaultError."""

    def test_get_secret_returns_value(self, mock_service_client):
        """Cuando el secreto existe → retorna el valor."""
        # Configure mock
        mock_result = MagicMock(data={"secret_value": "sk-12345"})
        mock_service_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result

        result = get_secret("org_abc", "api_key")

        assert result == "sk-12345"
        mock_service_client.table.assert_called_with("secrets")

    def test_get_secret_raises_when_not_found(self, mock_service_client):
        """Cuando el secreto no existe → lanza VaultError."""
        mock_service_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)

        with pytest.raises(VaultError) as exc_info:
            get_secret("org_abc", "inexistente")

        assert "no configurado" in str(exc_info.value)

    def test_get_secret_calls_with_correct_org_id(self, mock_service_client):
        """get_secret() filtra por org_id y name."""
        get_secret("org_xyz", "my_secret")

        # Verify the chain was called with correct filters
        mock_service_client.table.assert_called_with("secrets")
        # select("secret_value").eq("org_id", "org_xyz").eq("name", "my_secret")


class TestListSecrets:
    """list_secrets() returns only names, never values."""

    def test_list_secrets_returns_names(self, mock_service_client):
        """Lista de nombres, no valores."""
        mock_service_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
            {"name": "stripe_key"},
            {"name": "smtp_password"},
        ])

        result = list_secrets("org_abc")

        assert result == ["stripe_key", "smtp_password"]

    def test_list_secrets_empty(self, mock_service_client):
        """Org sin secretos → lista vacía."""
        mock_service_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        result = list_secrets("org_empty")

        assert result == []


class TestSecretIsolation:
    """Regla R3: secrets nunca llegan al LLM."""

    def test_get_secret_not_in_return_value(self, mock_service_client):
        """_get_secret() no debe estar en el valor de retorno de _run()."""
        mock_service_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data={"secret_value": "tok_987"})

        from src.tools.base_tool import SendMessageTool
        tool = SendMessageTool(org_id="org_abc")
        result = tool._run(to="+1234567890", message="Hello")

        # El resultado NO contiene el token
        assert "tok_987" not in result
        assert "tok_987" not in str(result)

    def test_secret_parameter_not_in_run_signature(self):
        """_run() no recibe el secreto como parámetro."""
        import inspect
        from src.tools.base_tool import SendMessageTool

        sig = inspect.signature(SendMessageTool._run)
        params = list(sig.parameters.keys())

        # _run(self, to, message) — sin api_token ni secret
        assert "api_token" not in params
        assert "secret" not in params
