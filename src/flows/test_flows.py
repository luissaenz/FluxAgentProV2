"""Test flows for E2E lifecycle validation (Paso 1.5).

- SuccessTestFlow: Always completes successfully with a deterministic result.
- FailTestFlow: Always raises an exception to trigger error handling.
"""

from __future__ import annotations

from typing import Dict, Any
import logging

from .base_flow import BaseFlow
from .registry import register_flow

logger = logging.getLogger(__name__)


@register_flow("success_test_flow")
class SuccessTestFlow(BaseFlow):
    """Flow que siempre completa exitosamente para validar el ciclo de éxito.

    Valida: ticket → in_progress → done con task_id vinculado.
    """

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return True

    async def _run_crew(self) -> Dict[str, Any]:
        logger.info("SuccessTestFlow._run_crew executing — simulating success")
        return {
            "status": "ok",
            "message": "SuccessTestFlow completed successfully",
            "test_marker": "e2e-success",
        }


@register_flow("fail_test_flow")
class FailTestFlow(BaseFlow):
    """Flow que siempre falla para validar el manejo de errores.

    Valida: ticket → in_progress → blocked con notas de error preservadas.
    """

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return True

    async def _run_crew(self) -> Dict[str, Any]:
        logger.error("FailTestFlow._run_crew — simulating intentional failure")
        raise RuntimeError("FailTestFlow: error intencional para validación E2E")
