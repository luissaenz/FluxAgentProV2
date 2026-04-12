import asyncio
import os
from dotenv import load_dotenv
from src.db.session import get_service_client

async def verify_agent_enrichment():
    load_dotenv()
    db = get_service_client()
    
    # 1. Buscar un agente real en el sistema
    print("🔍 Buscando agentes en catalog...")
    agents = db.table("agent_catalog").select("id, role, org_id").limit(1).execute()
    
    if not agents.data:
        print("❌ No hay agentes en agent_catalog. ¿Se ejecutaron las migraciones?")
        return
        
    agent = agents.data[0]
    agent_id = agent['id']
    org_id = agent['org_id']
    role = agent['role']
    print(f"✅ Agente encontrado: {role} ({agent_id}) para Org {org_id}")
    
    # 2. Verificar si tiene metadata
    print(f"🔍 Buscando metadata para role '{role}'...")
    meta = db.table("agent_metadata").select("*").eq("org_id", org_id).eq("agent_role", role).execute()
    
    if meta.data:
        print(f"✅ Metadata encontrada: {meta.data[0]['display_name']}")
    else:
        print("ℹ️ No hay metadata personalizada (se usará fallback).")
        
    # 3. Llamar al router (simulado)
    # Importamos el router después de configurar el entorno
    from src.api.routes.agents import get_agent_detail
    
    print("🚀 Probando get_agent_detail...")
    try:
        response = await get_agent_detail(agent_id=agent_id, org_id=org_id)
        
        agent_resp = response.get("agent", {})
        print("\n📥 RESULTADO:")
        print(f"- Display Name: {agent_resp.get('display_name')}")
        print(f"- Soul: {agent_resp.get('soul_narrative')}")
        print(f"- Avatar: {agent_resp.get('avatar_url')}")
        
        # Validaciones
        assert "display_name" in agent_resp, "Falta display_name"
        assert "soul_narrative" in agent_resp, "Falta soul_narrative"
        print("\n✅ VALIDACIÓN EXITOSA: El backend entrega el SOUL del agente.")
        
    except Exception as e:
        print(f"❌ ERROR en el endpoint: {e}")

if __name__ == "__main__":
    asyncio.run(verify_agent_enrichment())
