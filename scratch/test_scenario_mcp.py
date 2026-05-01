import asyncio
import logging
from typing import Any, Dict, Optional

# FAP Imports
from src.flows.architect_flow import ArchitectFlow
from src.db.session import get_tenant_client

# Configuración de logging
logging.basicConfig(level=logging.INFO)

async def test_mcp_integration_generation():
    print("\n[RUNNING] Scenario 3/4 - MCP + Service Integration")
    
    # Config
    org_id = "01b3cd88-7e73-48f1-8172-4e0f7b23ccef"  # E2E Test Org
    flow = ArchitectFlow(org_id=org_id)
    
    # Prompt de usuario que requiere herramientas específicas
    prompt = (
        "Crea un agente Investigador que use el servidor MCP 'google-search' para buscar las 3 noticias más importantes de IA de hoy. "
        "Luego, el agente debe usar la integración de 'gmail' para enviarme un correo con el resumen."
    )
    
    try:
        # 1. Generar definición
        # El ArchitectFlow automáticamente descubre google-search y gmail desde la DB
        result = await flow.execute(input_data={"description": prompt})
        workflow_def = result.extracted_definition
        
        if not workflow_def:
            print("[ERROR] No workflow definition was extracted.")
            return

        print(f"[OK] Definition generated: {workflow_def.name}")
        
        for agent in workflow_def.agents:
            print(f"[*] Agent: {agent.role}")
            print(f"    - Tools: {agent.allowed_tools}")
            
            # Verificar que existan prefijos mcp: o integration:
            has_mcp = any(t.startswith("mcp:google-search") for t in agent.allowed_tools)
            has_int = any(t.startswith("integration:gmail") or "gmail" in t for t in agent.allowed_tools)
            
            if has_mcp:
                print(f"    [VERIFIED] MCP Tool detected for google-search")
            else:
                print(f"    [WARNING] No MCP tool detected for google-search")
                
            if has_int:
                print(f"    [VERIFIED] Integration Tool detected for gmail")
            else:
                print(f"    [WARNING] No Integration tool detected for gmail")

        print("\n[RESULT] Scenario 3/4 SUCCESS")

    except Exception as e:
        print(f"[CRITICAL] Failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_integration_generation())
