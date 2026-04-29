"""src/utils/context_utils.py — Utilities for managing execution context and mocking.

Provides MockOrgContext for transiently injecting organization context during
local execution and testing.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional
from unittest.mock import MagicMock, patch

logger = logging.getLogger(__name__)


@contextmanager
def MockOrgContext(
    org_id: str, user_id: Optional[str] = None
) -> Generator[None, None, None]:
    """Context manager to mock organizational context and persistence.

    Injects org_id and patches DB clients to prevent production side-effects.
    Includes mocking for Vault access.
    """
    logger.info("Entering MockOrgContext for org_id: %s", org_id)

    # 1. Create a universal mock DB client
    mock_db = MagicMock()
    # Mock common Supabase patterns
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock_db.table.return_value.upsert.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock_db.rpc.return_value.execute.return_value = MagicMock(data=[])

    # 2. Patch session clients
    # We patch the context manager itself for get_tenant_client
    @contextmanager
    def mocked_tenant_client(*args, **kwargs):
        yield mock_db

    with (
        patch("src.db.session.get_tenant_client", side_effect=mocked_tenant_client),
        patch("src.db.session.get_service_client", return_value=mock_db),
        patch("src.db.session.get_anon_client", return_value=mock_db),
        patch("src.db.session.execute_with_retry", side_effect=lambda x: x.execute()),
    ):
        # 3. Patch Vault (Analysis Final §2.5)
        with patch("src.db.vault.get_secret", return_value="mocked-secret-value"):
            yield

    logger.info("Exited MockOrgContext for org_id: %s", org_id)
