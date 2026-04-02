"""tests/unit/test_guardrails_additional.py — Phase 2 guardrails additional coverage.

Covers:
  - make_approval_check with various scenarios
  - check_quota edge cases
  - load_org_limits error handling
  - Approval threshold boundary conditions
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, mock_open

from src.guardrails.base_guardrail import (
    make_approval_check,
    load_org_limits,
    check_quota,
    QuotaExceededError,
)


class TestMakeApprovalCheckAdditional:
    """Additional tests for make_approval_check()."""

    def test_amount_exactly_at_threshold(self):
        """Amount exactly at threshold does NOT require approval."""
        check = make_approval_check(
            amount_field="monto",
            threshold_key="approval_threshold",
            default_threshold=50000,
        )
        
        # Exactly at threshold → False (no approval needed)
        assert check(50000, "org-123") is False

    def test_amount_one_cent_above_threshold(self):
        """Amount one unit above threshold requires approval."""
        check = make_approval_check(
            amount_field="monto",
            threshold_key="approval_threshold",
            default_threshold=50000,
        )
        
        # One above → True (approval needed)
        assert check(50001, "org-123") is True

    def test_amount_zero(self):
        """Zero amount does not require approval."""
        check = make_approval_check(
            amount_field="monto",
            threshold_key="approval_threshold",
            default_threshold=50000,
        )
        
        assert check(0, "org-123") is False

    def test_negative_amount(self):
        """Negative amount does not require approval."""
        check = make_approval_check(
            amount_field="monto",
            threshold_key="approval_threshold",
            default_threshold=50000,
        )
        
        assert check(-100, "org-123") is False

    def test_very_large_amount(self):
        """Very large amount requires approval."""
        check = make_approval_check(
            amount_field="monto",
            threshold_key="approval_threshold",
            default_threshold=50000,
        )
        
        assert check(1_000_000_000, "org-123") is True

    def test_custom_threshold_from_org_config(self):
        """Uses custom threshold from org config."""
        check = make_approval_check(
            amount_field="amount",
            threshold_key="custom_threshold",
            default_threshold=50000,
        )
        
        with patch(
            "src.guardrails.base_guardrail.load_org_limits",
            return_value={"custom_threshold": 100000}
        ):
            # Below custom threshold
            assert check(80000, "org-123") is False
            # Above custom threshold
            assert check(120000, "org-123") is True


class TestLoadOrgLimits:
    """Tests for load_org_limits()."""

    def test_returns_limits_from_config(self):
        """load_org_limits returns limits from org config."""
        mock_db = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_db)
        mock_cm.__exit__ = MagicMock(return_value=False)
        
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "config": {
                    "limits": {
                        "approval_threshold": 75000,
                        "max_tokens_per_month": 1000000,
                    }
                }
            }
        )
        
        with patch("src.guardrails.base_guardrail.get_tenant_client", return_value=mock_cm):
            limits = load_org_limits("org-123")
            
            assert limits == {
                "approval_threshold": 75000,
                "max_tokens_per_month": 1000000,
            }

    def test_returns_empty_dict_when_no_config(self):
        """load_org_limits returns empty dict when config is empty."""
        mock_db = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_db)
        mock_cm.__exit__ = MagicMock(return_value=False)
        
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"config": {}}
        )
        
        with patch("src.guardrails.base_guardrail.get_tenant_client", return_value=mock_cm):
            limits = load_org_limits("org-123")
            
            assert limits == {}

    def test_returns_empty_dict_on_error(self):
        """load_org_limits returns empty dict on error."""
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(side_effect=Exception("DB error"))
        mock_cm.__exit__ = MagicMock(return_value=False)
        
        with patch("src.guardrails.base_guardrail.get_tenant_client", return_value=mock_cm):
            limits = load_org_limits("org-123")
            
            assert limits == {}

    def test_returns_empty_dict_when_no_limits_key(self):
        """load_org_limits returns empty dict when 'limits' key missing."""
        mock_db = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_db)
        mock_cm.__exit__ = MagicMock(return_value=False)
        
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"config": {"other_key": "value"}}
        )
        
        with patch("src.guardrails.base_guardrail.get_tenant_client", return_value=mock_cm):
            limits = load_org_limits("org-123")
            
            assert limits == {}


class TestCheckQuota:
    """Tests for check_quota()."""

    @patch("src.guardrails.base_guardrail.load_org_limits")
    def test_within_quota_does_not_raise(self, mock_load_limits):
        """check_quota does not raise when within quota."""
        mock_load_limits.return_value = {
            "max_tasks_per_month": 100,
            "max_tokens_per_month": 1000000,
        }
        
        # Should not raise
        check_quota(org_id="org-123", quota_type="tasks_per_month", current_usage=50)

    @patch("src.guardrails.base_guardrail.load_org_limits")
    def test_at_quota_raises(self, mock_load_limits):
        """check_quota raises when at quota limit."""
        mock_load_limits.return_value = {
            "max_tasks_per_month": 100,
            "max_tokens_per_month": 1000000,
        }
        
        with pytest.raises(QuotaExceededError, match="agotada"):
            check_quota(org_id="org-123", quota_type="tasks_per_month", current_usage=100)

    @patch("src.guardrails.base_guardrail.load_org_limits")
    def test_over_quota_raises(self, mock_load_limits):
        """check_quota raises when over quota."""
        mock_load_limits.return_value = {
            "max_tasks_per_month": 100,
            "max_tokens_per_month": 1000000,
        }
        
        with pytest.raises(QuotaExceededError, match="agotada"):
            check_quota(org_id="org-123", quota_type="tasks_per_month", current_usage=150)

    @patch("src.guardrails.base_guardrail.load_org_limits")
    def test_unlimited_quota(self, mock_load_limits):
        """check_quota does not raise when limit is very high."""
        # Note: The implementation doesn't handle -1 as unlimited
        # So we test with a very high limit instead
        mock_load_limits.return_value = {
            "max_tasks_per_month": float("inf"),  # Use inf instead of -1
        }
        
        # Should not raise even with high usage
        check_quota(org_id="org-123", quota_type="tasks_per_month", current_usage=1000000)

    @patch("src.guardrails.base_guardrail.load_org_limits")
    def test_missing_quota_key_uses_default(self, mock_load_limits):
        """check_quota uses default when quota key is missing."""
        mock_load_limits.return_value = {}  # No limits configured
        
        # Should use default (inf) - should not raise
        check_quota(org_id="org-123", quota_type="tasks_per_month", current_usage=50)

    @patch("src.guardrails.base_guardrail.load_org_limits")
    def test_tokens_exceed_quota(self, mock_load_limits):
        """check_quota raises when tokens exceed quota."""
        mock_load_limits.return_value = {
            "max_tasks_per_month": 100,
            "max_tokens_per_month": 1000000,
        }
        
        with pytest.raises(QuotaExceededError, match="agotada"):
            check_quota(org_id="org-123", quota_type="tokens_per_month", current_usage=1000000)


class TestGuardrailComposition:
    """Tests for composing multiple guardrails."""

    @patch("src.guardrails.base_guardrail.load_org_limits")
    def test_multiple_checks_compose(self, mock_load_limits):
        """Multiple guardrails can be composed."""
        mock_load_limits.return_value = {
            "approval_threshold": 50000,
            "max_tasks_per_month": 100,
            "max_tokens_per_month": 1000000,
        }
        
        # Create multiple guardrails
        approval_check = make_approval_check(
            amount_field="monto",
            threshold_key="approval_threshold",
            default_threshold=50000,
        )
        
        # Both should pass
        assert approval_check(30000, "org-123") is False
        
        check_quota(org_id="org-123", quota_type="tasks_per_month", current_usage=50)

    @patch("src.guardrails.base_guardrail.load_org_limits")
    def test_approval_and_quota_together(self, mock_load_limits):
        """Test approval check and quota check together."""
        mock_load_limits.return_value = {
            "approval_threshold": 50000,
            "max_tasks_per_month": 100,
            "max_tokens_per_month": 1000000,
        }
        
        approval_check = make_approval_check(
            amount_field="monto",
            threshold_key="approval_threshold",
            default_threshold=50000,
        )
        
        # High amount but within quota
        assert approval_check(100000, "org-123") is True  # Needs approval
        
        check_quota(org_id="org-123", quota_type="tasks_per_month", current_usage=50)  # Within quota
        
        # High amount AND over quota
        assert approval_check(100000, "org-123") is True
        
        with pytest.raises(QuotaExceededError, match="agotada"):
            check_quota(org_id="org-123", quota_type="tasks_per_month", current_usage=100)
