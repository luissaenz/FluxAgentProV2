import asyncio
import logging
import sys
from uuid import uuid4
from typing import Dict, Any
from unittest.mock import patch, AsyncMock

from src.db.session import get_service_client
from src.db.memory import save_memory, search_memory
from src.flows.multi_crew_flow import MultiCrewFlow
from src.flows.state import FlowStatus
from src.crews.base_crew import BaseCrew

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("validate_phase3_e2e")

async def validate_semantic_memory(org_id: str):
    logger.info("--- Validando MEMORIA SEMÁNTICA ---")
    
    # 1. Guardar memorias
    logger.info("Guardando fragmentos de memoria...")
    memories = [
        "El cliente prefiere recibir las facturas por email.",
        "La oficina central está en Madrid, calle Mayor 1.",
        "El horario de atención es de 9:00 a 18:00."
    ]
    for msg in memories:
        save_memory(org_id, msg, source_type="test")
        
    # 2. Buscar semánticamente
    logger.info("Buscando '¿Cómo contactar al cliente?'...")
    results = search_memory(org_id, "¿Cómo se envían los documentos?", min_similarity=0.1)
    
    logger.info(f"Resultados encontrados: {results}")
    assert len(results) > 0
    assert "email" in results[0].content.lower()
    logger.info(f"Mejor resultado: {results[0].content}")
    logger.info("Memoria semántica validada exitosamente.")

async def validate_multi_crew_flow(org_id: str):
    logger.info("--- Validando MULTI-CREW FLOW ---")
    flow = MultiCrewFlow(org_id=org_id)
    # Crew A simula que requiere Crew B enviando un bool
    input_data = {"monto": 500, "requires_crew_b": True}
    
    logger.info("Ejecutando MultiCrewFlow...")
    state = await flow.execute(input_data)
    
    # Verificar que pasó por Crew A y terminó en Crew B (o C)
    assert state.crew_a_output is not None
    assert state.status in [FlowStatus.COMPLETED, FlowStatus.AWAITING_APPROVAL]
    logger.info(f"MultiCrewFlow finalizado con estado: {state.status}")

async def seed_agent_catalog(org_id: str):
    logger.info("--- Seeding AGENT CATALOG ---")
    svc = get_service_client()
    agents = [
        {
            "org_id": org_id,
            "role": "analyst",
            "soul_json": {"role": "Analista", "goal": "Analizar datos de entrada", "backstory": "Experto en análisis"},
            "allowed_tools": [],
            "max_iter": 3
        },
        {
            "org_id": org_id,
            "role": "processor",
            "soul_json": {"role": "Procesador", "goal": "Procesar resultados", "backstory": "Experto en procesos"},
            "allowed_tools": [],
            "max_iter": 3
        },
        {
            "org_id": org_id,
            "role": "reviewer",
            "soul_json": {"role": "Revisor", "goal": "Revisar logs", "backstory": "Experto en calidad"},
            "allowed_tools": [],
            "max_iter": 3
        }
    ]
    for agent in agents:
        svc.table("agent_catalog").upsert(agent).execute()
    logger.info("Agent Catalog seeded.")

async def main():
    # Usar una org real o crear una de prueba
    org_id = str(uuid4())
    svc = get_service_client()
    svc.table("organizations").upsert({
        "id": org_id,
        "name": "Phase 3 Test Org",
        "slug": f"phase3-org-{org_id[:8]}"
    }).execute()

    try:
        # Parchar embed si no hay API Key para permitir validación DB (pgvector)
        from src.config import get_settings
        settings = get_settings()
        
        if not settings.openai_api_key:
            logger.warning("⚠️ OPENAI_API_KEY no encontrada. Usando DUMMY EMBEDDINGS (1536-dim).")
            dummy_vector = [0.1] * 1536
            patcher = patch("src.db.memory.embed", return_value=dummy_vector)
            patcher.start()
        
        # Parchar crews si no hay LLM keys suficientes para evitar fallos de red
        if not settings.groq_api_key and not settings.openai_api_key:
            logger.warning("⚠️ No se detectaron LLM keys (Groq/OpenAI). Usando MOCK CREW OUTPUTS.")
            mock_crew_run = patch("src.crews.base_crew.BaseCrew.run_async", 
                                 new_callable=AsyncMock, 
                                 return_value="Mock Result (No LLM)")
            mock_crew_run.start()

        # Seed catalog first
        await seed_agent_catalog(org_id)
        
        # Run validations
        await validate_semantic_memory(org_id)
        await validate_multi_crew_flow(org_id)
        
        logger.info("✅ FASE 3 VALIDADA E2E CON ÉXITO")
    except Exception as e:
        logger.error(f"❌ Error en validación E2E Fase 3: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
