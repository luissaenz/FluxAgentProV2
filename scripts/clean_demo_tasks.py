"""
Script para limpiar las tareas de la demo
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path to import from src
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.session import get_tenant_client

COCTEL_PRO_ORG_ID = "6877612f-3768-44bf-b6e3-b2d1453c3de9"

# Primero obtener las tareas de CoctelPro
print(f"📋 Buscando tareas de CoctelPro ({COCTEL_PRO_ORG_ID})...")

with get_tenant_client(COCTEL_PRO_ORG_ID) as db:
    tasks = db.execute_with_retry(db.table("tasks").select("id").eq("org_id", COCTEL_PRO_ORG_ID))
    task_ids = [t["id"] for t in (tasks.data or [])]

    if task_ids:
        # Eliminar en orden de dependencias
        print(f"🗑️  Eliminando pending_approvals...")
        db.execute_with_retry(db.table("pending_approvals").delete().eq("org_id", COCTEL_PRO_ORG_ID))

        print(f"🗑️  Eliminando {len(task_ids)} snapshots...")
        for task_id in task_ids:
            db.execute_with_retry(db.table("snapshots").delete().eq("task_id", task_id))

        print(f"🗑️  Eliminando domain_events...")
        for task_id in task_ids:
            db.execute_with_retry(db.table("domain_events").delete().eq("aggregate_id", task_id))

        # Finalmente eliminar las tareas
        print(f"🗑️  Eliminando tareas...")
        result = db.execute_with_retry(db.table("tasks").delete().eq("org_id", COCTEL_PRO_ORG_ID))
        print(f"✅ {len(result.data) if result.data else len(task_ids)} tareas eliminadas")
    else:
        print("ℹ️  No hay tareas para eliminar")

print("\n🎉 Kanban limpio! Ahora puedes disparar la demo nuevamente.")
