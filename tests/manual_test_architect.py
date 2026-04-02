import asyncio
import logging
import sys
import os
from uuid import uuid4

# Añadir el directorio raíz al path
sys.path.append(os.getcwd())

from src.flows.architect_flow import ArchitectFlow
from src.flows.state import FlowStatus
from src.flows.registry import flow_registry
from src.db.session import get_service_client

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("manual_test_architect")

async def run_architect_demo():
    print("\n" + "="*60)
    print("🚀 INICIANDO DEMOSTRACIÓN DE FASE 4: ARCHITECT FLOW")
    print("="*60)

    # 1. Configurar datos de prueba
    # Usamos una organización de prueba (debe existir en la DB)
    org_id = "c63290a1-32df-46e3-9ddd-266ea72b8721"
    user_id = "00000000-0000-0000-0000-000000000001"
    
    # Prompt en lenguaje natural para generar un workflow
    prompt = """
    Crea un workflow llamado 'Validador de Contenido' para una agencia de marketing.
    1. Un agente 'Redactor' genera un post de LinkedIn sobre IA.
    2. Un agente 'Editor' revisa el post y le da un puntaje del 1 al 10.
    3. Si el puntaje es mayor a 8, el post se considera aprobado.
    """

    print(f"\n📝 PROMPT: {prompt}")
    
    # 2. Instanciar y ejecutar ArchitectFlow
    flow = ArchitectFlow(org_id=org_id, user_id=user_id)
    
    print("\n⚙️ Ejecutando ArchitectFlow...")
    try:
        state = await flow.execute(input_data={
            "description": prompt,
            "conversation_id": str(uuid4())
        })
        
        # 3. Mostrar resultados
        print("\n" + "="*60)
        print("📊 RESULTADO DE LA GENERACIÓN")
        print("="*60)
        print(f"ID de Tarea:    {state.task_id}")
        print(f"Estado Final:   {state.status}")
        
        if state.status == FlowStatus.COMPLETED:
            output = state.output_data
            flow_type = output.get("flow_type")
            template_id = output.get("template_id")
            
            print(f"Flow Generado:  {flow_type}")
            print(f"Template ID:    {template_id}")
            print(f"Agentes:        {', '.join(output.get('agents_created', []))}")
            print(f"Mensaje:        {output.get('message')}")
            
            # 4. Verificar registro dinámico
            is_registered = flow_type in flow_registry._flows
            print(f"¿Registrado en FLOW_REGISTRY?: {'✅ SÍ' if is_registered else '❌ NO'}")
            
            # 5. Limpieza (opcional - borrar de DB para no ensuciar)
            # Para esta demo lo dejamos persistido para inspección manual si se desea
            
            print("\n✅ FASE 4 (ARCHITECT) VALIDADA CON ÉXITO")
        else:
            print(f"\n❌ El flow falló con error: {state.error}")
            
    except Exception as e:
        logger.error(f"Error durante la ejecución: {e}", exc_info=True)
        print(f"\n❌ Error fatal: {e}")

if __name__ == "__main__":
    asyncio.run(run_architect_demo())
