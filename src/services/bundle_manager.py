"""src/services/bundle_manager.py — Core logic for ZIP bundle processing.

Implements memory-only extraction, limit validation, and integrity checks.
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from typing import Optional

from .bundle_schemas import BundleContent, BundleManifest
from .integrity import verify_integrity
from .security_guard import SecurityError, SecurityGuard

logger = logging.getLogger(__name__)

# Limits defined in plan.md §71-74
MAX_ZIP_SIZE = 50 * 1024 * 1024  # 50MB
MAX_AGENTS = 50
MAX_FLOWS = 20
MAX_SKILLS = 30


class BundleError(Exception):
    """Base error for bundle processing failures."""
    pass


class BundleManager:
    """Manages the lifecycle of a bundle from ZIP to parsed content."""

    def __init__(
        self,
        org_id: str,
        security_guard: Optional[SecurityGuard] = None
    ):
        self.org_id = org_id
        # Analysis Final §76: Inject SecurityGuard
        self.security_guard = security_guard or SecurityGuard()

    def process_zip(self, zip_bytes: bytes) -> BundleContent:
        """Process a raw ZIP byte stream.

        Steps:
        1. Size validation
        2. ZIP extraction (In-Memory)
        3. Manifest parsing
        4. Integrity verification (Hashing)
        5. Content parsing (Agents, Flows, Skills)
        6. Limit validation
        """
        # 1. Size check
        size = len(zip_bytes)
        if size > MAX_ZIP_SIZE:
            raise BundleError(
                f"Bundle size ({size} bytes) exceeds limit of {MAX_ZIP_SIZE}"
            )

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                # 2. Extract manifest
                if "manifest.json" not in z.namelist():
                    raise BundleError("Missing 'manifest.json' in bundle root")

                manifest_data = json.loads(z.read("manifest.json"))
                manifest = BundleManifest(**manifest_data)

                content = BundleContent(manifest=manifest, size_bytes=size)

                # 3. Verify Integrity and Parse Files
                for rel_path, expected_hash in manifest.hashes.items():
                    if rel_path not in z.namelist():
                        raise BundleError(
                            f"File '{rel_path}' declared in manifest "
                            f"not found in ZIP"
                        )

                    file_data = z.read(rel_path)

                    # Verify hash
                    if not verify_integrity(file_data, expected_hash):
                        raise BundleError(
                            f"Integrity check failed for '{rel_path}'"
                        )

                    # Sort into categories
                    self._parse_file_content(rel_path, file_data, content)

                # 4. Final limit validation
                self._validate_limits(content)

                return content

        except zipfile.BadZipFile as e:
            raise BundleError("Invalid ZIP file") from e
        except json.JSONDecodeError as e:
            raise BundleError(f"JSON parsing error: {str(e)}") from e
        except SecurityError as e:
            # Propagate security errors with context
            raise BundleError(
                f"Security validation failed: {str(e)}"
            ) from e

        except Exception as e:
            if isinstance(e, (BundleError, SecurityError)):
                raise
            logger.exception("Unexpected error processing bundle")
            raise BundleError(f"Internal error processing bundle: {str(e)}") from e

    def _parse_file_content(self, path: str, data: bytes, content: BundleContent):
        """Categorize and parse file content based on its path."""
        if path.startswith("agents/") and path.endswith(".json"):
            content.agents.append(json.loads(data))
        elif path.startswith("flows/") and path.endswith(".json"):
            content.flows.append(json.loads(data))
        elif path.startswith("skills/") and path.endswith(".py"):
            # Skills are stored as raw source code strings
            filename = path.split("/")[-1]
            code = data.decode("utf-8")

            # Analysis Final §77: Invoke validate_skill
            self.security_guard.validate_skill(code, filename)

            content.skills[filename] = code
        elif path == "manifest.json":
            pass  # Already handled
        else:
            logger.info("Ignoring file outside structure: %s", path)

    def _validate_limits(self, content: BundleContent):
        """Ensure bundle doesn't exceed architectural limits."""
        if len(content.agents) > MAX_AGENTS:
            raise BundleError(
                f"Exceeded max agents: {len(content.agents)} > {MAX_AGENTS}"
            )
        if len(content.flows) > MAX_FLOWS:
            raise BundleError(
                f"Exceeded max flows: {len(content.flows)} > {MAX_FLOWS}"
            )
        if len(content.skills) > MAX_SKILLS:
            raise BundleError(
                f"Exceeded max skills: {len(content.skills)} > {MAX_SKILLS}"
            )
