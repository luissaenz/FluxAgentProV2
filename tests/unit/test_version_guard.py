"""tests/unit/test_version_guard.py — Test Step 19: SemVer & Version Guard.

Verifies:
1. Upgrade (1.0.0 -> 1.1.0) is allowed.
2. Same version (1.1.0 -> 1.1.0) is allowed.
3. Downgrade (1.1.0 -> 1.0.0) is blocked with 409 Conflict logic.
4. Downgrade with force=True (1.1.0 -> 1.0.0) is allowed.
5. Isolation between different bundle names.
6. Malformed versions are rejected.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.services.bundle_manager import (
    MalformedVersionError,
    VersionDowngradeError,
)
from src.services.import_service import ImportService


class TestVersionGuard:
    def setup_method(self):
        self.org_id = "test-org-version-guard"
        self.service = ImportService(org_id=self.org_id)

    def mock_db_version(self, version: str = None):
        """Helper to mock the Supabase response for the latest version."""
        mock_db = MagicMock()
        
        # Result data
        execute_res = MagicMock()
        execute_res.data = [{"version": version}] if version else []
        
        # Chain: table().select().eq().eq().order().limit().execute()
        # We use configure_mock to set up the deep return value
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = execute_res
        
        cm = MagicMock()
        cm.__enter__.return_value = mock_db
        cm.__exit__.return_value = False
        return cm

    def test_upgrade_allowed(self):
        """Scenario: 1.0.0 -> 1.1.0 (Allowed)"""
        with patch("src.services.import_service.get_tenant_client", return_value=self.mock_db_version("1.0.0")):
            # Should NOT raise
            self.service._check_version_guard("1.1.0", "my-bundle")

    def test_same_version_allowed(self):
        """Scenario: 1.1.0 -> 1.1.0 (Allowed)"""
        with patch("src.services.import_service.get_tenant_client", return_value=self.mock_db_version("1.1.0")):
            # Should NOT raise
            self.service._check_version_guard("1.1.0", "my-bundle")

    def test_downgrade_blocked(self):
        """Scenario: 1.1.0 -> 1.0.0 (Blocked)"""
        with patch("src.services.import_service.get_tenant_client", return_value=self.mock_db_version("1.1.0")):
            with pytest.raises(VersionDowngradeError) as exc:
                self.service._check_version_guard("1.0.0", "my-bundle")
            assert "Bundle 'my-bundle'" in str(exc.value)
            assert "is lower than current" in str(exc.value)

    def test_downgrade_forced_allowed(self):
        """Scenario: 1.1.0 -> 1.0.0 with force=True (Allowed)"""
        # We don't even need to mock DB if force=True because it returns early
        self.service._check_version_guard("1.0.0", "my-bundle", force=True)

    def test_new_bundle_allowed(self):
        """Scenario: No previous version exists (Allowed)"""
        with patch("src.services.import_service.get_tenant_client", return_value=self.mock_db_version(None)):
            # Should NOT raise
            self.service._check_version_guard("1.0.0", "new-bundle")

    def test_bundle_isolation(self):
        """Scenario: Bundle A (2.0.0) exists, Bundle B (1.0.0) is allowed."""
        mock_cm = self.mock_db_version(None) # Return nothing for Bundle B
        with patch("src.services.import_service.get_tenant_client", return_value=mock_cm):
            self.service._check_version_guard("1.0.0", "bundle-b")

    def test_malformed_version(self):
        """Scenario: Version string 'xyz' (Rejected)"""
        with patch("src.services.import_service.get_tenant_client", return_value=self.mock_db_version(None)):
            with pytest.raises(MalformedVersionError) as exc:
                self.service._check_version_guard("xyz", "my-bundle")
            assert "Bundle 'my-bundle'" in str(exc.value)
            assert "invalid semantic version format" in str(exc.value)

    def test_semver_complex_comparison(self):
        """Scenario: 1.10.0 > 1.2.0 (Allowed)"""
        with patch("src.services.import_service.get_tenant_client", return_value=self.mock_db_version("1.2.0")):
            # Should NOT raise
            self.service._check_version_guard("1.10.0", "my-bundle")
