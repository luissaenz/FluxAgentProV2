"""src/api/routes/bundles.py — Endpoint for bundle imports."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from src.api.middleware import require_org_id
from src.services.bundle_manager import BundleError
from src.services.bundle_schemas import BundleRPCResult
from src.services.import_service import ImportService
from src.services.security_guard import SecurityError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bundles", tags=["Bundles"])


@router.post(
    "/import",
    response_model=BundleRPCResult,
    status_code=status.HTTP_201_CREATED,
    summary="Import a ZIP bundle (Agents, Flows, Skills)",
)
async def import_bundle(
    file: UploadFile = File(...),
    org_id: str = Depends(require_org_id),
):
    """
    Upload a ZIP bundle to import agents, workflows, and skills atomically.

    The ZIP must contain a 'manifest.json' and follow the expected folder structure.
    All operations are performed within a single database transaction.
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
        result = service.process_bundle(zip_bytes)

        if result.status == "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Atomic import failed: {result.error}",
            )

        return result

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
