"""Script de Seeding para Test de Precisión Analítica - Fase 4.5
Crea datos controlados para verificar que los cálculos de tasa de éxito son exactos.
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Agregar src al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from src.db.session import get_service_client
except ImportError as e:
    print(f"Error importing project modules: {e}")
    sys.exit(1)

async def seed_precision():
    print("Iniciando Seeding de Precision Analitica...")
    supabase = get_service_client()
    
    # 1. Obtener org_id (usamos empresa-demo por defecto)
    res = supabase.table("organizations").select("id").eq("slug", "empresa-demo").execute()
    if not res.data:
        print("Error: No se encontro la organizacion 'empresa-demo'. Ejecuta primero seed_dev_data.py")
        return
    
    org_id = res.data[0]["id"]
    print(f"Usando Org ID: {org_id}")

    # 2. Asegurar que existen los agentes en el catálogo
    agents = [
        {"role": "atg_senior", "org_id": org_id},
        {"role": "atg_junior", "org_id": org_id},
        {"role": "atg_intern", "org_id": org_id}
    ]
    
    for agent in agents:
        supabase.table("agent_catalog").upsert(agent, on_conflict="role,org_id").execute()
    
    print("Agentes de prueba registrados en el catálogo.")

    # 3. Limpiar tareas previas de estos agentes (opcional pero recomendado para precisión)
    # Nota: En Supabase, delete sin filtros puede ser peligroso por RLS, pero aquí filtramos por role.
    for agent in agents:
        supabase.table("tasks").delete().eq("assigned_agent_role", agent["role"]).eq("org_id", org_id).execute()

    # 4. Crear Tareas con estados controlados (dentro de la última semana)
    # atg_senior: 10 tareas (9 completadas, 1 bloqueada) -> 90%
    # atg_junior: 10 tareas (5 completadas, 5 bloqueadas) -> 50%
    # atg_intern: 5 tareas (0 completadas, 5 bloqueadas) -> 0%
    
    task_batch = []
    now = datetime.utcnow()
    
    def add_tasks(role, completed_count, blocked_count):
        for i in range(completed_count):
            task_batch.append({
                "org_id": org_id,
                "assigned_agent_role": role,
                "status": "completed",
                "flow_type": "precision_test",
                "flow_id": "85b7b8ba-8c22-4c2a-ac83-c643c8d7f0f7",
                "created_at": (now - timedelta(days=i % 6)).isoformat()
            })
        for i in range(blocked_count):
            task_batch.append({
                "org_id": org_id,
                "assigned_agent_role": role,
                "status": "blocked",
                "flow_type": "precision_test",
                "flow_id": "85b7b8ba-8c22-4c2a-ac83-c643c8d7f0f7",
                "created_at": (now - timedelta(days=i % 6)).isoformat()
            })

    add_tasks("atg_senior", 9, 1)
    add_tasks("atg_junior", 5, 5)
    add_tasks("atg_intern", 0, 5)

    res = supabase.table("tasks").insert(task_batch).execute()
    if res.data:
        print(f"Se insertaron {len(res.data)} tareas de prueba.")
    else:
        print("Error al insertar tareas.")

    print("\n" + "="*50)
    print("SEEDING DE PRECISIÓN COMPLETADO")
    print("Agente Senior: 90% éxito esperable")
    print("Agente Junior: 50% éxito esperable")
    print("Agente Intern: 0% éxito esperable")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(seed_precision())
