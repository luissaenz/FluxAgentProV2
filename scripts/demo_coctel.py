"""
Demo de CoctelPro: flujo completo de cotizacion -> compra -> rechazo.
Duracion: 12-15 minutos.

Requisitos:
  - FastAPI corriendo en http://localhost:8000
  - Dashboard corriendo en http://localhost:3000
  - Org CoctelPro creada en Supabase con un usuario demo
  - Variables COCTEL_PRO_ORG_ID y JWT_TOKEN configuradas abajo

Uso:
  uv run python scripts/demo_coctel.py
"""

import requests
import sys
import time

FASTAPI_URL = "http://localhost:8000"
COCTEL_PRO_ORG_ID = "6877612f-3768-44bf-b6e3-b2d1453c3de9"  # Reemplazar con UUID real
JWT_TOKEN = "eyJhbGciOiJFUzI1NiIsImtpZCI6ImE3ZTk4NTBjLWM4MDctNGY5MS1hMTFhLWI3Nzc5NDJjMmQxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3RtbG90d250cHRtaWx5Y3Z0Zm9vLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJkNjMwZWViYS0xNWU5LTRlOWItYjA1My1lNjE2OTU2ZGFiNzgiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzc1MTgzODg4LCJpYXQiOjE3NzUxODAyODgsImVtYWlsIjoiYWRtaW5AY29jdGVscHJvLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzc1MTgwMjg4fV0sInNlc3Npb25faWQiOiIyMjgyMzdkZi04NzZiLTQ5ZjEtODRlOC01MzllMzU4Y2I5MDMiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.rKoKX-3AQpa2RsEYqgXFwWwu8w4KeWO9TLFqzR-tZXxfkrSF9lznF1pvEN9t9IRmr3OIrlAhjGIVUJznLzQwNg"      # Reemplazar con JWT real de Supabase Auth

HEADERS = {
    "Authorization": f"Bearer {JWT_TOKEN}",
    "X-Org-ID": "6877612f-3768-44bf-b6e3-b2d1453c3de9",
    "Content-Type": "application/json",
}


def step(msg: str):
    """Pausa interactiva entre pasos de la demo."""
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")
    input("  Presiona ENTER para continuar...")


def check_health():
    """Verifica que el backend este corriendo."""
    try:
        r = requests.get(f"{FASTAPI_URL}/health", timeout=15)
        r.raise_for_status()
        print(f"  Backend OK: {r.json()}")
    except Exception as e:
        print(f"  ERROR: No se puede conectar al backend: {e}")
        print(f"  Asegurate de que FastAPI este corriendo en {FASTAPI_URL}")
        sys.exit(1)


def trigger_flow(flow_type: str, input_data: dict) -> dict:
    """Dispara un flow via webhook y retorna la respuesta."""
    r = requests.post(
        f"{FASTAPI_URL}/webhooks/trigger",
        json={"flow_type": flow_type, "input_data": input_data},
        headers=HEADERS,
    )
    r.raise_for_status()
    return r.json()


def process_approval(task_id: str, action: str, notes: str) -> dict:
    """Aprueba o rechaza una tarea pendiente."""
    r = requests.post(
        f"{FASTAPI_URL}/approvals/{task_id}",
        json={"action": action, "notes": notes},
        headers=HEADERS,
    )
    r.raise_for_status()
    return r.json()


def get_pending_approvals() -> list:
    """Lista aprobaciones pendientes."""
    r = requests.get(
        f"{FASTAPI_URL}/approvals",
        headers=HEADERS,
    )
    r.raise_for_status()
    return r.json()


def wait_for_approval(flow_type: str, max_wait: int = 15) -> dict | None:
    """Espera hasta que aparezca una aprobacion pendiente para el flow."""
    print(f"  Esperando aprobacion pendiente para {flow_type}...")
    for i in range(max_wait):
        approvals = get_pending_approvals()
        for a in approvals:
            if a.get("flow_type") == flow_type and a.get("status") == "pending":
                print(f"  Encontrada: task_id={a['task_id']}")
                return a
        time.sleep(1)
    print(f"  AVISO: No se encontro aprobacion pendiente despues de {max_wait}s")
    return None


def main():
    print()
    print("  ============================================")
    print("  DEMO CoctelPro - FluxAgentPro v2 (Fase 5)")
    print("  ============================================")
    print()

    # Paso 0: Health check
    print("  Verificando conexion al backend...")
    check_health()

    # --- BLOQUE 1: Setup visual ---
    step("1. Abrir Dashboard en http://localhost:3000")
    step("2. Iniciar sesion con el usuario demo")
    step("3. Seleccionar la organizacion CoctelPro en el selector")

    # --- BLOQUE 2: Cotizacion flow ---
    step("4. Disparar cotizacion_flow (cliente VIP, 80 pax, $500.000)")

    result = trigger_flow("cotizacion_flow", {
        "evento": "Casamiento Rodriguez",
        "pax": 80,
        "presupuesto": 500000,
        "vip": True,
    })
    print(f"  Flow aceptado: correlation_id={result['correlation_id']}")

    step("5. Mirar el Kanban: deberia aparecer una card en 'Ejecutando' y luego pasar a 'HITL (Espera)'")

    # Esperar a que aparezca la aprobacion
    approval = wait_for_approval("CotizacionFlow")
    if not approval:
        print("  No se encontro aprobacion. Verifica que el flow se ejecuto correctamente.")
        step("Continuar de todas formas?")

    step("6. Ir al Centro de Aprobaciones y revisar el payload de la cotizacion")

    # --- BLOQUE 3: Aprobar cotizacion ---
    step("7. Aprobar la cotizacion (hacer click en 'Aprobar' o esperar que se ejecute aqui)")

    if approval:
        result = process_approval(approval["task_id"], "approve", "Cliente VIP, aprobado.")
        print(f"  Cotizacion aprobada: {result}")
    else:
        print("  Saltando aprobacion automatica (no se encontro pending_approval)")

    step("8. Mirar el Kanban: la task deberia pasar a 'Completado' en tiempo real")

    # --- BLOQUE 4: Compras flow ---
    step("9. Disparar compras_flow (orden de compra con insumos)")

    result = trigger_flow("compras_flow", {
        "insumos": [
            {"item": "Botellas de vodka", "cantidad": 30, "precio": 50},
            {"item": "Vasos", "cantidad": 80, "precio": 1},
            {"item": "Hielo (kg)", "cantidad": 8, "precio": 5},
        ],
    })
    print(f"  Flow aceptado: correlation_id={result['correlation_id']}")

    step("10. Mirar el Kanban: nueva card deberia aparecer en 'HITL (Espera)' (compras SIEMPRE requiere aprobacion)")

    approval2 = wait_for_approval("ComprasFlow")
    if not approval2:
        print("  No se encontro aprobacion para compras.")
        step("Continuar de todas formas?")

    # --- BLOQUE 5: Rechazar compra ---
    step("11. Ir al Centro de Aprobaciones y RECHAZAR esta compra")

    if approval2:
        result = process_approval(approval2["task_id"], "reject", "Necesitamos otro proveedor.")
        print(f"  Compra rechazada: {result}")
    else:
        print("  Saltando rechazo automatico (no se encontro pending_approval)")

    step("12. Mirar el Kanban: la card deberia pasar a 'Rechazado'")

    # --- BLOQUE 6: Log de eventos ---
    step("13. Abrir la vista 'Eventos' y mostrar el trail completo de ambos flows")

    print()
    print("  ============================================")
    print("  DEMO COMPLETADA!")
    print("  ============================================")
    print()
    print("  Resumen:")
    print("    - cotizacion_flow: VIP, 80 pax -> HITL -> Aprobado")
    print("    - compras_flow: Orden de insumos -> HITL -> Rechazado")
    print("    - Kanban actualizado en tiempo real")
    print("    - Trail de eventos completo visible")
    print()


if __name__ == "__main__":
    main()
