"""tests/manual_test_bundle_rpc.py — Manual integration test for the import_bundle_atomic RPC."""

import asyncio
import logging
import os
import sys
from uuid import uuid4

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.session import get_service_client, get_tenant_client
from src.services.bundle_schemas import BundleRPCPayload, BundleRPCResult

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("manual_test_bundle_rpc")


async def run_rpc_test():
    org_id = str(uuid4())
    logger.info(f"🚀 Iniciando prueba de RPC Atómico (Org: {org_id})")

    # 1. Crear organización de prueba
    svc = get_service_client()
    try:
        svc.table("organizations").upsert(
            {
                "id": org_id,
                "name": "Bundle Test Org",
                "slug": f"test-bundle-{org_id[:4]}",
            }
        ).execute()
    except Exception as e:
        logger.error(f"❌ Falló creación de organización: {e}")
        return

    # 2. Preparar Payload del Bundle
    payload = BundleRPCPayload(
        bundle_name="demo-bundle",
        bundle_hash="sha256:fakehash1234567890abcdef1234567890abcdef1234567890abcdef123",
        agents=[
            {
                "role": "analyst-test",
                "goal": "Test atomic import",
                "backstory": "Created by integration test",
                "allowed_tools": ["tool1", "tool2"],
                "max_iter": 5,
            }
        ],
        flows=[
            {
                "name": "Test Flow",
                "flow_type": "test_atomic_flow",
                "definition": {"steps": [{"id": 1, "name": "step1"}]},
            }
        ],
        skills={"atomic_skill.py": "def test(): return True"},
    )

    # 3. Invocar RPC vía TenantClient (simulando API)
    logger.info("📡 Invocando RPC import_bundle_atomic...")
    try:
        with get_tenant_client(org_id) as db:
            response = db.rpc(
                "import_bundle_atomic",
                {"p_org_id": org_id, "p_payload": payload.model_dump()},
            ).execute()

            result = BundleRPCResult(**response.data)

            if result.status == "success":
                logger.info(f"✅ RPC exitoso! Bundle ID: {result.bundle_id}")
                logger.info(
                    f"📊 Resumen: Agents={result.agents_count}, Flows={result.flows_count}, Skills={result.skills_count}"
                )
            else:
                logger.error(f"❌ RPC falló según respuesta: {result.error}")

    except Exception as e:
        logger.error(f"❌ Error crítico invocando RPC: {e}")
        logger.info(
            "💡 Asegúrate de que las migraciones 0026 y 0027 estén aplicadas en Supabase."
        )

    # 4. Verificar Atomicidad (Intento fallido a propósito)
    logger.info("🧪 Probando ATOMICIDAD (Forzando error de tipo en agente)...")
    bad_payload = payload.model_dump()
    bad_payload["agents"][0]["max_iter"] = (
        "NOT_AN_INTEGER"  # Esto debería fallar el cast en SQL
    )

    try:
        with get_tenant_client(org_id) as db:
            db.rpc(
                "import_bundle_atomic", {"p_org_id": org_id, "p_payload": bad_payload}
            ).execute()
            logger.error("❌ ERROR: El RPC no falló como se esperaba.")
    except Exception as e:
        logger.info(
            f"✅ ÉXITO: El RPC falló correctamente (Rollback esperado). Error: {str(e)[:50]}..."
        )

    logger.info("🏁 Prueba finalizada.")


if __name__ == "__main__":
    # Nota: Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en variables de entorno o .env
    asyncio.run(run_rpc_test())
