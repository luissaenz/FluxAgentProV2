import asyncio
import os
import sys

# Añadir el root al path para poder importar src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.bundle_manager import BundleManager, BundleManifest
from src.services.import_service import ImportService

SYSTEM_ORG_ID = "00000000-0000-0000-0000-000000000000"

async def seed_architect_bundle():
    """
    Crea e importa el bundle de sistema del ArchitectFlow.
    Esto permite que el Architect sea 'desacoplado' del core.
    """
    print("🚀 Iniciando seeding de ArchitectFlow como System Bundle...")

    # 1. Preparar el código del flujo
    flow_path = "src/flows/architect_flow.py"
    if not os.path.exists(flow_path):
        print(f"❌ Error: No se encontró {flow_path}")
        return

    with open(flow_path, "r", encoding="utf-8") as f:
        flow_code = f.read()

    # 2. Definir el manifiesto
    manifest = BundleManifest(
        name="ArchitectFlow Core",
        version="2.0.0",
        description="FAP System Architect - Capaz de generar nuevos bundles.",
        author="FAP-CORE", # CRÍTICO: Esto activa el modo privilegiado
        flows=["architect_flow"],
        agents=["Workflow Architect"],
        skills=[]
    )

    # 3. Crear el agente que necesita el architect (definido en architect_flow.py)
    # Nota: El ArchitectFlow usa un agente internamente, pero aquí definimos
    # la metadata para el bundle si fuera necesario.
    architect_agent = {
        "role": "Workflow Architect",
        "goal": "Analizar la descripción NL y producir una definición de workflow válida.",
        "backstory": "Eres un arquitecto de sistemas especializado en transformar requisitos en workflows.",
        "model": "gpt-4o", # O el default
        "max_iter": 5
    }

    # 4. Generar el ZIP usando BundleManager
    bm = BundleManager(org_id=SYSTEM_ORG_ID)
    bundle_bytes = bm.create_bundle(
        manifest=manifest,
        agents=[architect_agent],
        flows=[{
            "flow_type": "architect_flow",
            "is_python": True,
            "code_source": flow_code
        }],
        skills={}
    )

    import_service = ImportService(SYSTEM_ORG_ID)

    print(f"📦 Importando bundle '{manifest.name}' para org '{SYSTEM_ORG_ID}'...")
    try:
        result = await import_service.import_bundle(bundle_bytes)
        print(f"✅ Bundle importado con éxito: {result['bundle_id']}")
        print(f"✅ Flujos registrados: {result['flows']}")
    except Exception as e:
        print(f"❌ Error durante la importación: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(seed_architect_bundle())
