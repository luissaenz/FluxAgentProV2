"""Tests: Guardrails — Approval threshold validation."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.guardrails.base_guardrail import (
    make_approval_check,
    check_quota,
    QuotaExceededError,
    load_org_limits,
)


class TestMakeApprovalCheck:
    """make_approval_check() crea validators según config de org."""

    def test_above_threshold_returns_true(self):
        """Cuando value > threshold → requiere aprobación."""
        check = make_approval_check("monto", "approval_threshold", 50_000)

        with patch("src.guardrails.base_guardrail.load_org_limits") as mock_load:
            mock_load.return_value = {"approval_threshold": 50_000}
            result = check(60_000, "org_test")

            assert result is True

    def test_below_threshold_returns_false(self):
        """Cuando value <= threshold → no requiere aprobación."""
        check = make_approval_check("monto", "approval_threshold", 50_000)

        with patch("src.guardrails.base_guardrail.load_org_limits") as mock_load:
            mock_load.return_value = {"approval_threshold": 50_000}
            result = check(40_000, "org_test")

            assert result is False

    def test_exactly_threshold_returns_false(self):
        """Cuando value == threshold → no requiere aprobación."""
        check = make_approval_check("monto", "approval_threshold", 50_000)

        with patch("src.guardrails.base_guardrail.load_org_limits") as mock_load:
            mock_load.return_value = {"approval_threshold": 50_000}
            result = check(50_000, "org_test")

            assert result is False

    def test_uses_default_when_no_config(self):
        """Sin config → usa default_threshold."""
        check = make_approval_check("monto", "approval_threshold", 50_000)

        with patch("src.guardrails.base_guardrail.load_org_limits") as mock_load:
            mock_load.return_value = {}  # Sin límites configurados
            result = check(60_000, "org_test")

            assert result is True  # 60k > 50k default


class TestCheckQuota:
    """check_quota() lanza QuotaExceededError cuando se agota."""

    def test_within_quota_does_not_raise(self):
        with patch("src.guardrails.base_guardrail.load_org_limits") as mock_load:
            mock_load.return_value = {"max_tasks_per_month": 100}

            # No debe lanzar
            check_quota("org_test", "tasks_per_month", 50)

    def test_at_quota_raises(self):
        with patch("src.guardrails.base_guardrail.load_org_limits") as mock_load:
            mock_load.return_value = {"max_tasks_per_month": 100}

            with pytest.raises(QuotaExceededError) as exc_info:
                check_quota("org_test", "tasks_per_month", 100)

            assert "tasks_per_month" in str(exc_info.value)
            assert "100/100" in str(exc_info.value)

    def test_over_quota_raises(self):
        with patch("src.guardrails.base_guardrail.load_org_limits") as mock_load:
            mock_load.return_value = {"max_tasks_per_month": 100}

            with pytest.raises(QuotaExceededError):
                check_quota("org_test", "tasks_per_month", 150)

    def test_unlimited_quota(self):
        """Sin límite configurado → no lanza."""
        with patch("src.guardrails.base_guardrail.load_org_limits") as mock_load:
            mock_load.return_value = {}
            # No lanza aunque usage sea altísimo
            check_quota("org_test", "tasks_per_month", 999_999_999)


class TestLoadOrgLimits:
    """load_org_limits() lee desde la BD."""

    def test_returns_limits_from_org_config(self, mock_tenant_client):
        """Config con limits → dict con valores."""
        mock_tenant_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "config": {"limits": {"approval_threshold": 25_000, "max_tokens": 1_000_000}}
        })

        result = load_org_limits("org_abc")

        assert result == {"approval_threshold": 25_000, "max_tokens": 1_000_000}

    def test_returns_empty_dict_on_error(self, mock_tenant_client):
        """Si la query falla → dict vacío (no lanza)."""
        mock_tenant_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("DB error")

        result = load_org_limits("org_broken")

        assert result == {}
