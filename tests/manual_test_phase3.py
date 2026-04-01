import asyncio
import logging
import sys
from uuid import uuid4
from typing import Dict, Any
from unittest.mock import patch, AsyncMock

# Add src to path
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.session import get_service_client
from src.flows.multi_crew_flow import MultiCrewFlow
from src.flows.state import FlowStatus
from src.config import get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("manual_test_phase3")

async def mock_crew_side_effect(task_description: str, inputs: Dict[str, Any] = None, expected_output: str = None):
    logger.info(f"🎭 Mocking for task: {task_description[:30]}...")
    if "initial analysis" in task_description.lower():
        return '{"requires_crew_b": true, "analysis": "High risk transaction detected"}'
    elif "process" in task_description.lower():
        return '{"monto": 75000, "status": "flagged_for_approval"}'
    elif "review" in task_description.lower():
        return '{"summary": "Alternative path review complete"}'
    return "Generic Mock Output"

async def run_demonstration():
    org_id = str(uuid4())
    user_id = str(uuid4())
    
    logger.info(f"🚀 Creando entorno para demostración (Org: {org_id[:8]})")
    
    # 1. Preparar base de datos (Org)
    svc = get_service_client()
    svc.table("organizations").upsert({
        "id": org_id,
        "name": "Phase 3 Demo Org",
        "slug": f"demo-org-{org_id[:4]}"
    }).execute()
    
    # 2. Mocking de dependencias externas (LLM y Embeddings)
    settings = get_settings()
    
    # Mock Embeddings
    dummy_vector = [0.1] * 1536
    embed_patcher = patch("src.db.memory.embed", return_value=dummy_vector)
    embed_patcher.start()
    
    # Mock Crews (Orquestación determinista)
    crew_patcher = patch("src.crews.base_crew.BaseCrew.run_async", side_effect=mock_crew_side_effect)
    crew_patcher.start()
    
    # 3. Ejecutar el flujo
    logger.info("🏗️ Instanciando MultiCrewFlow...")
    flow = MultiCrewFlow(org_id=org_id, user_id=user_id)
    
    input_data = {
        "monto": 75000, 
        "descripcion": "Transferencia internacional urgente",
        "requires_crew_b": True # Forzamos ruta B
    }
    
    logger.info("🔥 Iniciando ejecución del Flow Orchestrator...")
    state = await flow.execute(input_data)
    
    print("\n" + "═"*60)
    print("📊 RESULTADO FINAL DE LA ORQUESTACIÓN")
    print("═"*60)
    print(f"ID del Flow:    {state.task_id}")
    print(f"Estado Final:   {state.status}")
    print(f"Salida Crew A:  {state.crew_a_output}")
    print(f"Salida Crew B:  {state.crew_b_output}")
    print(f"Salida Crew C:  {state.crew_c_output}")
    
    if state.status == FlowStatus.AWAITING_APPROVAL:
        print("\n⚠️  EL FLUJO SE HA PAUSADO CORRECTAMENTE PARA APROBACIÓN HUMANA (HITL)")
        print(f"   Razón: Monto {state.crew_b_output.get('monto')} excede el límite automático.")
    
    print("═"*60)
    
    # Clean up patches
    embed_patcher.stop()
    crew_patcher.stop()

if __name__ == "__main__":
    asyncio.run(run_demonstration())
