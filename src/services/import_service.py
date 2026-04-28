"""src/services/import_service.py — Orchestrator for bundle imports.

Bridges BundleManager (validation) and Supabase RPC (persistence).
"""

from __future__ import annotations

import logging

from src.db.session import get_tenant_client

from .bundle_manager import BundleManager
from .bundle_schemas import BundleRPCPayload, BundleRPCResult, BundleValidationResult

logger = logging.getLogger(__name__)


class ImportService:
    """Orchestrates the end-to-end bundle import flow."""

    def __init__(self, org_id: str):
        self.org_id = org_id
        self.bundle_manager = BundleManager(org_id=org_id)

    def process_bundle(self, zip_bytes: bytes) -> BundleRPCResult:
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

        # 2. Prepare RPC Payload
        bundle_name = (
            content.manifest.bundle_info.name
            if content.manifest.bundle_info
            else content.manifest.version
        )
        payload = BundleRPCPayload(
            bundle_name=bundle_name,
            bundle_hash=content.bundle_hash,  # Analysis-FINAL §2.1: Use real SHA256 hash
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

    def _register_skills(self, content: any) -> None:
        """Register imported skills in the in-memory ToolRegistry."""
        from RestrictedPython import compile_restricted, safe_builtins

        from src.tools.registry import tool_registry

        # We use a safe environment similar to SecurityGuard
        safe_env = safe_builtins.copy()
        # SUPUESTO: Standard __import__ is needed to resolve allowed imports (pydantic, etc)
        safe_env["__import__"] = __import__

        for filename, code in content.skills.items():
            skill_name = filename.replace(".py", "").lower()
            try:
                # Compile restricted
                byte_code = compile_restricted(code, filename=filename, mode="exec")

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
