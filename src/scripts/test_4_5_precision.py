"""Test de Certificación de Precisión Analítica - Fase 4.5
Valida que el sistema retorne datos exactos comparados con el Golden Set.
"""

import sys
import os
import asyncio
import json

# Agregar src al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from src.crews.analytical_crew import AnalyticalCrew
    from src.db.session import get_service_client
except ImportError as e:
    print(f"Error importing project modules: {e}")
    sys.exit(1)

async def test_precision_certification():
    print("=" * 60)
    print("CERTIFICACION DE PRECISION ANALITICA - PASO 4.5")
    print("=" * 60)

    # 1. Obtener org_id de test
    supabase = get_service_client()
    res = supabase.table("organizations").select("id").eq("slug", "empresa-demo").execute()
    if not res.data:
        print("Error: Ejecuta primero seed_dev_data.py")
        return
    org_id = res.data[0]["id"]

    crew = AnalyticalCrew(org_id=org_id)
    
    # 2. Ejecutar la "Golden Question"
    question = "¿Cuál es el agente con mayor tasa de éxito en la última semana?"
    print(f"\nPreguntando: {question}")
    
    try:
        result = await crew.ask(question=question)
    except Exception as e:
        print(f"Fallo critico en el crew: {e}")
        return

    # 3. Validaciones Estructurales
    print("\nVerificando Estructura...")
    assert result["query_type"] == "agent_success_rate", f"Query incorrecta: {result['query_type']}"
    assert "data" in result
    assert "summary" in result
    print("Estructura correcta.")

    # 4. Validaciones de Precisión Numérica (Basadas en seed_precision_data.py)
    print("\nVerificando Precision Numerica (Golden Truth)...")
    data = result["data"]
    
    # Buscamos a atg_senior en la lista (debería ser el primero por éxito)
    lead_agent = data[0] if data else None
    
    if not lead_agent:
        print("No se recibieron datos de agentes.")
        return

    print(f"Lider detectado: {lead_agent['role']} con {lead_agent['success_rate']}%")

    # Verificación estricta: atg_senior debe tener 90.0%
    senior_data = next((item for item in data if item["role"] == "atg_senior"), None)
    junior_data = next((item for item in data if item["role"] == "atg_junior"), None)
    
    errors = []
    
    if not senior_data or senior_data["success_rate"] != 90.0:
        errors.append(f"Senior success rate incorrecto. Esperado: 90.0, Recibido: {senior_data['success_rate'] if senior_data else 'None'}")
    
    if not junior_data or junior_data["success_rate"] != 50.0:
        errors.append(f"Junior success rate incorrecto. Esperado: 50.0, Recibido: {junior_data['success_rate'] if junior_data else 'None'}")

    if errors:
        for err in errors:
            print(f"Error: {err}")
        print("\nCERTIFICACION FALLIDA: Los datos no coinciden con la BD.")
    else:
        print("Todos los agentes tienen la tasa de exito exacta esperada.")
        
        # 5. Validación Narrativa (Resumen)
        print("\nVerificando Sintesis Narrativa...")
        summary = result["summary"].lower()
        if "atg_senior" in summary and "90" in summary:
            print("El resumen menciona correctamente al lider y su porcentaje.")
        else:
            print(f"Advertencia: El resumen podria ser mas preciso. Recibido: {result['summary']}")

        print("\nCERTIFICACION EXITOSA: La Capa de Inteligencia es PRECISA.")

if __name__ == "__main__":
    asyncio.run(test_precision_certification())
