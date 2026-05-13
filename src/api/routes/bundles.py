"""src/api/routes/bundles.py — Endpoints for bundle import, export, and management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from src.api.middleware import require_org_id
from src.services.bundle_manager import (
    BundleError,
    MalformedVersionError,
    VersionConflictError,
    VersionDowngradeError,
)
from src.services.bundle_schemas import (
    BundleRPCResult,
    BundleValidationResult,
    ExportBundleRequest,
)
from src.services.export_service import ExportService
from src.services.import_service import ImportService
from src.services.security_guard import SecurityError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bundles", tags=["Bundles"])


@router.get(
    "/security-config",
    status_code=status.HTTP_200_OK,
    summary="Get current security configuration",
)
async def get_security_config():
    """
    Returns the current security configuration used by the server's sandbox.
    Used by the CLI to synchronize local validation.
    """
    import sys

    from src.services.security_guard import ALLOWED_MODULES, FORBIDDEN_MODULES

    return {
        "allowed_modules": sorted(list(ALLOWED_MODULES)),
        "forbidden_modules": sorted(list(FORBIDDEN_MODULES)),
        "timeout_seconds": 30,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
    }


@router.post(
    "/import",
    response_model=BundleRPCResult,
    status_code=status.HTTP_201_CREATED,
    summary="Import a ZIP bundle (Agents, Flows, Skills)",
)
async def import_bundle(
    file: UploadFile = File(...),
    force: bool = False,
    org_id: str = Depends(require_org_id),
):
    """
    Upload a ZIP bundle to import agents, workflows, and skills atomically.

    The ZIP must contain a 'manifest.json' and follow the expected folder structure.
    All operations are performed within a single database transaction.

    - **force**: If true, allows downgrading the bundle version.
    """
    # 1. Basic format validation
    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ZIP files are supported",
        )

    try:
        # 2. Read bytes into memory (Max 50MB enforced in ImportService/BundleManager)
        zip_bytes = await file.read()

        # 3. Process via Service
        service = ImportService(org_id=org_id)
        result = service.process_bundle(zip_bytes, force=force)

        if result.status == "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Atomic import failed: {result.error}",
            )

        return result

    except MalformedVersionError as e:
        logger.warning("Malformed version for org %s: %s", org_id, str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except VersionDowngradeError as e:
        logger.warning("Version downgrade conflict for org %s: %s", org_id, str(e))
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except VersionConflictError as e:
        logger.warning("Version conflict for org %s: %s", org_id, str(e))
        # Fallback for any other version conflicts
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (BundleError, SecurityError) as e:
        logger.warning("Bundle validation failed for org %s: %s", org_id, str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error importing bundle for org %s", org_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during import: {str(e)}",
        )
    finally:
        await file.close()


@router.post(
    "/validate",
    response_model=BundleValidationResult,
    status_code=status.HTTP_200_OK,
    summary="Validate a ZIP bundle without importing (Dry-run)",
)
async def validate_bundle(
    file: UploadFile = File(...),
    org_id: str = Depends(require_org_id),
):
    """
    Dry-run validation of a ZIP bundle.
    Returns metadata and security report without modifying the database.
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ZIP files are supported",
        )

    try:
        zip_bytes = await file.read()
        service = ImportService(org_id=org_id)
        result = service.validate_only(zip_bytes)
        return result

    except Exception as e:
        logger.exception("Unexpected error validating bundle for org %s", org_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during validation: {str(e)}",
        )
    finally:
        await file.close()


@router.get(
    "/history",
    status_code=status.HTTP_200_OK,
    summary="List bundle import history",
)
async def list_history(
    org_id: str = Depends(require_org_id),
):
    """Get the history of all bundle imports for the current organization."""
    service = ImportService(org_id=org_id)
    return service.list_history()


@router.get(
    "/{bundle_id}/details",
    status_code=status.HTTP_200_OK,
    summary="Get bundle contents details",
)
async def get_bundle_details(
    bundle_id: str,
    org_id: str = Depends(require_org_id),
):
    """Fetch the list of agents, flows and skills included in a specific bundle."""
    service = ImportService(org_id=org_id)
    return service.get_details(bundle_id)


@router.delete(
    "/{bundle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a bundle",
)
async def delete_bundle(
    bundle_id: str,
    org_id: str = Depends(require_org_id),
):
    """
    Deactivate a bundle and all its associated components (soft-delete).
    This will mark them as inactive in the database and clear the in-memory cache.
    """
    service = ImportService(org_id=org_id)
    service.delete_bundle(bundle_id)
    return None


@router.post(
    "/export",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Export agents as FAP-Bundle v2 ZIP",
)
async def export_bundle(
    payload: ExportBundleRequest,
    org_id: str = Depends(require_org_id),
) -> Response:
    """
    Export agents (and optionally skills) as a downloadable FAP-Bundle v2 ZIP.

    The request body defines which agents and skills to include.
    The response is a ZIP file ready for import via POST /api/bundles/import.
    """
    for agent in payload.agents:
        soul = agent.soul_json or {}
        if not soul.get("goal"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"agent '{agent.role}': soul_json.goal required",
            )
        if not soul.get("backstory"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"agent '{agent.role}': soul_json.backstory required",
            )
        # Mitigación §258: goal/backstory muy cortos producen agentes de baja calidad.
        # Validación de longitud mínima 10 chars para prevenir datos insuficientes.
        if len(str(soul.get("goal", ""))) < 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"agent '{agent.role}': soul_json.goal must be at least 10 characters",
            )
        if len(str(soul.get("backstory", ""))) < 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"agent '{agent.role}': soul_json.backstory must be at least 10 characters",
            )

    try:
        service = ExportService(org_id=org_id)
        zip_bytes, filename = service.export(payload)
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.exception("Unexpected error exporting bundle for org %s", org_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during export: {str(e)}",
        )
