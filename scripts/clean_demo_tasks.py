"""
Script para limpiar las tareas de la demo
"""
import os
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

COCTEL_PRO_ORG_ID = "6877612f-3768-44bf-b6e3-b2d1453c3de9"

# Primero obtener las tareas de CoctelPro
print(f"📋 Buscando tareas de CoctelPro ({COCTEL_PRO_ORG_ID})...")
tasks = sb.table("tasks").select("id").eq("org_id", COCTEL_PRO_ORG_ID).execute()
task_ids = [t["id"] for t in (tasks.data or [])]

if task_ids:
    # Eliminar en orden de dependencias
    print(f"🗑️  Eliminando pending_approvals...")
    sb.table("pending_approvals").delete().eq("org_id", COCTEL_PRO_ORG_ID).execute()

    print(f"🗑️  Eliminando {len(task_ids)} snapshots...")
    for task_id in task_ids:
        sb.table("snapshots").delete().eq("task_id", task_id).execute()

    print(f"🗑️  Eliminando domain_events...")
    for task_id in task_ids:
        sb.table("domain_events").delete().eq("aggregate_id", task_id).execute()

    # Finalmente eliminar las tareas
    print(f"🗑️  Eliminando tareas...")
    result = sb.table("tasks").delete().eq("org_id", COCTEL_PRO_ORG_ID).execute()
    print(f"✅ {len(result.data) if result.data else len(task_ids)} tareas eliminadas")
else:
    print("ℹ️  No hay tareas para eliminar")

print("\n🎉 Kanban limpio! Ahora puedes disparar la demo nuevamente.")
