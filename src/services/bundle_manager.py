"""src/services/bundle_manager.py — Core logic for ZIP bundle processing.

Implements memory-only extraction, limit validation, and integrity checks.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import zipfile
from typing import Dict, List, Optional

from src.config import get_settings

from .bundle_schemas import BundleContent, BundleManifest
from .integrity import verify_integrity
from .security_guard import SecurityError, SecurityGuard

logger = logging.getLogger(__name__)

# Constants for fallback or internal use if needed,
# but we prioritize settings.


class BundleError(Exception):
    """Base error for bundle processing failures."""

    pass


class VersionConflictError(BundleError):
    """Raised when a bundle version is invalid or a downgrade is attempted."""

    pass


class MalformedVersionError(BundleError):
    """Raised when a semantic version string is invalid."""

    pass


class VersionDowngradeError(VersionConflictError):
    """Raised when an import attempts to downgrade a bundle version."""

    pass


class BundleManager:
    """Manages the lifecycle of a bundle from ZIP to parsed content."""

    def __init__(self, org_id: str, security_guard: Optional[SecurityGuard] = None):
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
        settings = get_settings()
        max_size = settings.max_bundle_size_mb * 1024 * 1024
        size = len(zip_bytes)
        if size > max_size:
            raise BundleError(
                f"Bundle size ({size} bytes) exceeds limit of {max_size} bytes"
            )

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                # 2. Extract manifest
                if "manifest.json" not in z.namelist():
                    raise BundleError("Missing 'manifest.json' in bundle root")

                manifest_data = json.loads(z.read("manifest.json"))
                manifest = BundleManifest(**manifest_data)

                # Analysis Final §88: Trust system bundles
                if manifest.bundle_info and manifest.bundle_info.author == "FAP-CORE":
                    logger.info("System bundle detected: '%s'. Enabling core access.", manifest.bundle_info.name)
                    self.security_guard.is_system = True
                    self.security_guard.allowed_modules.add("src")

                # Calculate bundle hash for audit (Analisis-FINAL §2.1)
                bundle_hash = hashlib.sha256(zip_bytes).hexdigest()
                content = BundleContent(
                    manifest=manifest, size_bytes=size, bundle_hash=bundle_hash
                )

                # 3. Verify Integrity and Parse Files
                for rel_path, expected_hash in manifest.hashes.items():
                    if rel_path not in z.namelist():
                        raise BundleError(
                            f"File '{rel_path}' declared in manifest not found in ZIP"
                        )

                    file_data = z.read(rel_path)

                    # Verify hash
                    if not verify_integrity(file_data, expected_hash):
                        raise BundleError(f"Integrity check failed for '{rel_path}'")

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
            raise BundleError(f"Security validation failed: {str(e)}") from e

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
        elif path.startswith("flows/") and path.endswith(".py"):
            # Analysis Final §25: Support Python flows
            filename = path.split("/")[-1]
            flow_type = filename.replace(".py", "").lower()
            code = data.decode("utf-8")

            # Validate security
            self.security_guard.validate_skill(code, filename)

            content.flows.append({
                "flow_type": flow_type,
                "code_source": code,
                "is_python": True,
                "name": flow_type.replace("_", " ").title()
            })
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
        """Ensure bundle doesn't exceed architectural limits from config."""
        settings = get_settings()
        if len(content.agents) > settings.max_agents_per_bundle:
            raise BundleError(
                f"Exceeded max agents: {len(content.agents)} > {settings.max_agents_per_bundle}"
            )
        # Note: flows/skills limits can be added to config if needed,
        # using current defaults for now to keep it lean.
        if len(content.flows) > 20:
            raise BundleError(f"Exceeded max flows: {len(content.flows)} > 20")
        if len(content.skills) > 30:
            raise BundleError(f"Exceeded max skills: {len(content.skills)} > 30")

    def create_bundle(self, manifest: BundleManifest, agents: List[Dict], flows: List[Dict], skills: Dict[str, str]) -> bytes:
        """Create a valid FAP ZIP bundle in memory.
        
        Analysis Final §89: Centralize ZIP creation logic + Auto-hashing.
        """
        buffer = io.BytesIO()
        all_hashes = {}

        def add_file(z, path, content_bytes):
            sha = hashlib.sha256(content_bytes).hexdigest()
            all_hashes[path] = f"sha256:{sha}"
            z.writestr(path, content_bytes)

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
            # 1. Add agents
            for agent in agents:
                role = agent.get("role", "unknown")
                path = f"agents/{role}.json"
                data = json.dumps(agent, indent=2).encode("utf-8")
                add_file(z, path, data)

            # 2. Add flows
            for flow in flows:
                flow_type = flow.get("flow_type", "unknown")
                if flow.get("is_python"):
                    path = f"flows/{flow_type}.py"
                    data = flow["code_source"].encode("utf-8")
                else:
                    path = f"flows/{flow_type}.json"
                    data = json.dumps(flow, indent=2).encode("utf-8")
                add_file(z, path, data)

            # 3. Add skills
            for filename, code in skills.items():
                path = f"skills/{filename}"
                add_file(z, path, code.encode("utf-8"))

            # 4. Update manifest with hashes and add it
            manifest.hashes = all_hashes
            manifest_data = json.dumps(manifest.model_dump(), indent=2).encode("utf-8")
            z.writestr("manifest.json", manifest_data)

        return buffer.getvalue()
