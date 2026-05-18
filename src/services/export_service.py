"""src/services/export_service.py — Orchestrator for bundle exports.

Bridges request validation (handler) with ZIP generation (BundleManager).
Follows same pattern as ImportService for consistency.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from src.utils.bundle_utils import create_base_manifest

from .bundle_manager import BundleManager
from .bundle_schemas import BundleManifest, ExportBundleRequest

logger = logging.getLogger(__name__)


class ExportService:
    """Orchestrates end-to-end bundle export flow."""

    def __init__(self, org_id: str, bundle_manager: Optional[BundleManager] = None):
        self.org_id = org_id
        self.bundle_manager = bundle_manager or BundleManager(org_id=org_id)

    def export(self, payload: ExportBundleRequest) -> tuple[bytes, str]:
        """Generate a FAP-Bundle v2 ZIP from the export request payload.

        Returns:
            tuple[bytes, str]: (zip_bytes, filename)
        """
        bundle_name = (
            payload.bundle_name
            or f"export_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
        )

        manifest_dict = create_base_manifest(bundle_name, version="1.0.0", author=self.org_id[:8])
        manifest = BundleManifest(**manifest_dict)

        agents = [
            {
                "role": a.role,
                "soul_json": a.soul_json,
                "allowed_tools": a.allowed_tools,
                "max_iter": a.max_iter,
            }
            for a in payload.agents
        ]

        skills: dict[str, str] = {}
        if payload.skills:
            for s in payload.skills:
                filename = f"{s.name}.py"
                skills[filename] = s.code

        zip_bytes = self.bundle_manager.create_bundle(
            manifest=manifest,
            agents=agents,
            flows=[],
            skills=skills,
        )

        filename = f"{bundle_name}.zip"
        return zip_bytes, filename
