import asyncio
import os
import logging
from dotenv import load_dotenv
from src.db.session import get_service_client

# Silenciar logs ruidosos
logging.getLogger("httpx").setLevel(logging.WARNING)

async def verify_agent_enrichment_robustness():
    load_dotenv()
    db = get_service_client()
    
    # 1. Obtener un agente real
    print("🔍 Consultando agente base en catalog...")
    agents = db.table("agent_catalog").select("id, role, org_id").limit(1).execute()
    
    if not agents.data:
        print("❌ Error: No hay agentes para probar.")
        return
        
    agent_data = agents.data[0]
    agent_id = agent_data['id']
    org_id = agent_data['org_id']
    role = agent_data['role']
    print(f"✅ Probando con Agente: {role} ({agent_id})")
    
    # 2. Probar el endpoint (que internamente consultará agent_metadata)
    # Si la tabla no existe (como sabemos), el try/except interno debe capturarlo.
    from src.api.routes.agents import get_agent_detail
    
    print("\n🚀 Llamando a get_agent_detail (Probando Robustez ante tabla inexistente)...")
    try:
        response = await get_agent_detail(agent_id=agent_id, org_id=org_id)
        
        agent_resp = response.get("agent", {})
        print("\n📥 RESPUESTA DEL ENDPOINT:")
        print(f"- Display Name (Fallback): {agent_resp.get('display_name')}")
        print(f"- Role: {agent_resp.get('role')}")
        
        # Validaciones de Robustez
        assert "display_name" in agent_resp, "Falta display_name incluso en fallback"
        assert agent_resp.get("display_name") is not None, "Display name no debería ser None"
        
        print("\n✅ VALIDACIÓN DE ROBUSTEZ EXITOSA:")
        print("El backend manejó correctamente la ausencia de la tabla 'agent_metadata' y aplicó los fallbacks.")
        
    except Exception as e:
        print(f"\n❌ FALLO DE ROBUSTEZ: El endpoint explotó al no encontrar la tabla.")
        print(f"Error: {e}")
        # Reraise to show traceback
        raise

if __name__ == "__main__":
    asyncio.run(verify_agent_enrichment_robustness())
