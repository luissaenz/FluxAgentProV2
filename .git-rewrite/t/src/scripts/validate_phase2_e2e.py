import asyncio
from typing import Dict, Any, Optional, List
import logging
import sys
from uuid import uuid4

from src.db.session import get_service_client, get_tenant_client
from src.flows.base_flow import BaseFlow, BaseFlowState, FlowStatus
from src.db.vault import get_secret
from src.guardrails.base_guardrail import make_approval_check

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("validate_phase2_e2e")

class E2EFlow(BaseFlow):
    """Flow simple para probar HITL."""
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return True

    async def _run_crew(self) -> Dict[str, Any]:
        monto = self.state.input_data.get("monto", 0)
        logger.info(f"Ejecutando _run_crew con monto: {monto}")
        
        # Simular guardrail de aprobación
        if monto > 1000:
            logger.info("Monto alto detectado. Solicitando aprobación...")
            await self.request_approval(
                description=f"Aprobación de gasto: {monto}",
                payload={"monto": monto}
            )
            # Retornar algo; el estado ya está en AWAITING_APPROVAL
            return {"paused": True}
        
        return {"result": "Flow completado sin aprobación."}

async def validate_vault(org_id: str):
    logger.info("--- Validando VAULT ---")
    svc = get_service_client()
    
    # 1. Crear secreto de prueba si no existe
    svc.table("secrets").upsert({
        "org_id": org_id,
        "name": "e2e_test_secret",
        "secret_value": "super-secret-123"
    }, on_conflict="org_id,name").execute()
    
    # 2. Recuperar secreto
    val = get_secret(org_id, "e2e_test_secret")
    assert val == "super-secret-123"
    logger.info("Vault validado exitosamente.")

async def validate_hitl(org_id: str):
    logger.info("--- Validando HITL ---")
    flow = E2EFlow(org_id=org_id)
    input_data = {"monto": 5000}
    
    # 1. Ejecutar y esperar pausa
    logger.info("Ejecutando flow.execute() - (debería pausarse)...")
    state = await flow.execute(input_data)
    task_id = state.task_id
    
    assert state.status == FlowStatus.AWAITING_APPROVAL
    logger.info(f"Flow pausado. ID de tarea: {task_id}")
    
    # 2. Verificar en base de datos
    svc = get_service_client()
    pending = svc.table("pending_approvals").select("*").eq("task_id", task_id).maybe_single().execute()
    assert pending.data is not None
    assert pending.data["status"] == "pending"
    logger.info("Registro en 'pending_approvals' encontrado.")
    
    # 3. Aprobar y reanudar
    logger.info("Aprobando y reanudando...")
    # El resume() volverá a cargar el flow desde el snapshot y ejecutará _on_approved
    # que por defecto marca como RUNNING
    await flow.resume(task_id=task_id, decision="approved", decided_by="admin_e2e")
    
    assert flow.state.status == FlowStatus.RUNNING
    logger.info("Flow reanudado y completado exitosamente.")

async def main():
    org_id = str(uuid4())
    # Crear organización de prueba
    svc = get_service_client()
    svc.table("organizations").upsert({
        "id": org_id,
        "name": "E2E Test Org",
        "slug": f"e2e-org-{org_id[:8]}"
    }).execute()
    
    try:
        await validate_vault(org_id)
        await validate_hitl(org_id)
        logger.info("✅ FASE 2 VALIDADA E2E CON ÉXITO")
    except Exception as e:
        logger.error(f"❌ Error en validación E2E: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
