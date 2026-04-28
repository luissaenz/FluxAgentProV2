"""src/services/import_service.py — Orchestrator for bundle imports.

Bridges BundleManager (validation) and Supabase RPC (persistence).
"""

from __future__ import annotations

import logging

from packaging.version import InvalidVersion, Version

from src.db.session import get_tenant_client

from .bundle_manager import BundleManager, VersionConflictError
from .bundle_schemas import BundleRPCPayload, BundleRPCResult, BundleValidationResult

logger = logging.getLogger(__name__)


class ImportService:
    """Orchestrates the end-to-end bundle import flow."""

    def __init__(self, org_id: str):
        self.org_id = org_id
        self.bundle_manager = BundleManager(org_id=org_id)

    def process_bundle(self, zip_bytes: bytes, force: bool = False) -> BundleRPCResult:
        """Execute the full import pipeline: validate -> process -> persist.

        Raises:
            BundleError: If validation, integrity or limits fail.
            SecurityError: If AST scan or RestrictedPython fails.
            Exception: For unexpected DB or internal errors.
        """
        logger.info("Starting bundle import for org_id: %s", self.org_id)

        # 1. Process ZIP (Integrity + Security + Parsing)
        # This will raise BundleError or SecurityError if invalid
        content = self.bundle_manager.process_zip(zip_bytes)

        # 2. Version Guard (Roadmap T15.2)
        # SUPUESTO: El campo bundle_info.version es obligatorio para el Roadmap.
        new_version_str = (
            content.manifest.bundle_info.version
            if content.manifest.bundle_info
            else "1.0.0"
        )
        bundle_name = (
            content.manifest.bundle_info.name
            if content.manifest.bundle_info
            else content.manifest.version
        )
        self._check_version_guard(new_version_str, bundle_name, force=force)
        payload = BundleRPCPayload(
            bundle_name=bundle_name,
            bundle_hash=content.bundle_hash,  # Analysis-FINAL §2.1: Use real SHA256 hash
            version=new_version_str,
            agents=content.agents,
            flows=content.flows,
            skills=content.skills,
        )

        # 3. Invoke Atomic Persistence via RPC
        try:
            with get_tenant_client(self.org_id) as db:
                # Supabase RPC call
                # Analisis-FINAL §2.1: Use import_bundle_atomic(p_org_id, p_payload)
                response = db.rpc(
                    "import_bundle_atomic",
                    {"p_org_id": self.org_id, "p_payload": payload.model_dump()},
                ).execute()

                if not response.data:
                    logger.error("RPC returned no data for org_id %s", self.org_id)
                    raise Exception("Atomic import failed: No response from database")

                # The RPC returns the BundleRPCResult directly as JSON
                result = BundleRPCResult(**response.data)

                if result.status == "failed":
                    logger.error("Atomic import failed: %s", result.error)
                    # We keep it as a successful call but with failed status
                    # so the API can decide what to return.
                else:
                    logger.info(
                        "Import successful for bundle '%s'. IDs: %s",
                        bundle_name,
                        result.bundle_id,
                    )
                    # Analysis-FINAL §2.4: Runtime registration of skills
                    self._register_skills(content)

                return result

        except Exception:
            logger.exception(
                "Unexpected error during RPC execution for org %s", self.org_id
            )
            raise

    def _check_version_guard(
        self, new_version_str: str, bundle_name: str, force: bool = False
    ) -> None:
        """Prevent downgrades by comparing with the latest imported bundle version.

        Granularized by bundle_name to allow independent versioning.
        """
        try:
            # 1. Validate format ALWAYS (Analysis TP-V5)
            new_v = Version(new_version_str)
        except InvalidVersion:
            raise VersionConflictError(
                f"Invalid semantic version format: {new_version_str}"
            )

        if force:
            logger.info(
                "Version guard bypassed via force=True for bundle '%s' (org: %s)",
                bundle_name,
                self.org_id,
            )
            return

        try:
            with get_tenant_client(self.org_id) as db:
                logger.debug(
                    "Checking version guard for bundle '%s': %s",
                    bundle_name,
                    new_version_str,
                )

                # Fetch latest version for this specific bundle in this org
                # Analysis-FINAL §1.2: Added .eq("bundle_name", bundle_name)
                result = (
                    db.table("bundle_imports")
                    .select("version")
                    .eq("org_id", self.org_id)
                    .eq("bundle_name", bundle_name)
                    .order("imported_at", desc=True)
                    .limit(1)
                    .execute()
                )

                if result.data and result.data[0].get("version"):
                    current_version_str = result.data[0]["version"]
                    curr_v = Version(current_version_str)

                    if new_v < curr_v:
                        logger.warning(
                            "Downgrade rejected for '%s': %s < %s",
                            bundle_name,
                            new_version_str,
                            current_version_str,
                        )
                        raise VersionConflictError(
                            f"Incoming version {new_version_str} is lower than current {current_version_str}. "
                            "Use force=true to override."
                        )

        except VersionConflictError:
            raise
        except Exception:
            logger.exception("Error in version guard check")
            raise

    def validate_only(self, zip_bytes: bytes) -> BundleValidationResult:
        """Validate a bundle without persisting anything.

        Returns:
            BundleValidationResult: Details about the bundle and any issues.
        """
        try:
            content = self.bundle_manager.process_zip(zip_bytes)

            return BundleValidationResult(
                status="success",
                bundle_info=content.manifest.bundle_info,
                agents_count=len(content.agents),
                flows_count=len(content.flows),
                skills_count=len(content.skills),
                # SUPUESTO: Full security report could be more detailed, for now we return success if it passed
                security_report={"ast_scan": "passed", "restricted_python": "passed"},
            )
        except Exception as e:
            logger.warning(
                "Bundle validation failed for org %s: %s", self.org_id, str(e)
            )
            return BundleValidationResult(status="failed", error=str(e))

    def list_history(self) -> list[dict]:
        """List previous bundle imports for the tenant."""
        from src.db.session import get_tenant_client

        with get_tenant_client(self.org_id) as db:
            result = (
                db.table("bundle_imports")
                .select("*")
                .eq("org_id", self.org_id)
                .order("imported_at", desc=True)
                .execute()
            )
            return result.data or []

    def get_details(self, bundle_id: str) -> dict:
        """Get details of agents, flows and skills included in a bundle."""
        from src.db.session import get_tenant_client

        with get_tenant_client(self.org_id) as db:
            # Fetch agents
            agents = (
                db.table("agent_catalog")
                .select("role")
                .eq("bundle_id", bundle_id)
                .execute()
                .data
            )
            # Fetch flows
            flows = (
                db.table("workflow_templates")
                .select("flow_type")
                .eq("bundle_id", bundle_id)
                .execute()
                .data
            )
            # Fetch skills
            skills = (
                db.table("skill_catalog")
                .select("name, code_source")
                .eq("bundle_id", bundle_id)
                .execute()
                .data
            )

            return {
                "bundle_id": bundle_id,
                "agents": [a["role"] for a in agents],
                "flows": [f["flow_type"] for f in flows],
                "skills": [{"name": s["name"], "code": s["code_source"]} for s in skills],
            }

    def delete_bundle(self, bundle_id: str) -> bool:
        """Soft-delete a bundle and its components."""
        from src.db.session import get_tenant_client
        from src.flows.registry import flow_registry
        from src.tools.registry import tool_registry

        with get_tenant_client(self.org_id) as db:
            # 1. Mark bundle as inactive
            db.table("bundle_imports").update({"is_active": False}).eq(
                "id", bundle_id
            ).execute()
            # 2. Mark components as inactive (Roadmap T15.3 + Analysis-FINAL)
            db.table("agent_catalog").update({"is_active": False}).eq(
                "bundle_id", bundle_id
            ).execute()
            db.table("skill_catalog").update({"is_active": False}).eq(
                "bundle_id", bundle_id
            ).execute()
            # Added in Paso 18: Soft-delete workflow templates
            db.table("workflow_templates").update({"is_active": False}).eq(
                "bundle_id", bundle_id
            ).execute()

            # 3. Invalidate memory cache to trigger reload without deleted assets
            tool_registry.invalidate_tenant_cache(self.org_id)
            flow_registry.invalidate_tenant_cache(self.org_id)

            return True

    def _register_skills(self, content: any) -> None:
        """Register imported skills in the in-memory ToolRegistry."""
        import RestrictedPython

        from src.flows.registry import flow_registry
        from src.tools.registry import tool_registry

        # Roadmap T15.1: Invalidate cache before re-registering (Avoid collisions)
        tool_registry.invalidate_tenant_cache(self.org_id)
        flow_registry.invalidate_tenant_cache(self.org_id)

        # We use a safe environment similar to SecurityGuard
        safe_env = RestrictedPython.safe_builtins.copy()
        # SUPUESTO: Standard __import__ is needed to resolve allowed imports (pydantic, etc)
        safe_env["__import__"] = __import__

        for filename, code in content.skills.items():
            skill_name = filename.replace(".py", "").lower()
            try:
                # Compile restricted
                byte_code = RestrictedPython.compile_restricted(
                    code, filename=filename, mode="exec"
                )

                # Execute in safe env to extract classes
                exec_globals = {"__builtins__": safe_env}
                exec(byte_code, exec_globals)

                # Look for the tool class
                # We expect at least one class that looks like a Tool
                for attr_name, attr in exec_globals.items():
                    if isinstance(attr, type) and not attr_name.startswith("_"):
                        # If it has docstring or looks like a tool, register it
                        if "Tool" in attr_name or hasattr(attr, "_is_tool"):
                            # SUPUESTO: Use tenant prefix to ensure isolation (Analysis R3)
                            scoped_name = f"{self.org_id}:{skill_name}"
                            tool_registry.register(name=scoped_name)(attr)
                            logger.info(
                                "Registered imported skill in memory for tenant %s: %s",
                                self.org_id,
                                skill_name,
                            )
                            break
            except Exception as e:
                logger.warning(
                    "Failed to register imported skill '%s' in memory: %s",
                    skill_name,
                    e,
                )
