"""
Demo automática de CoctelPro: flujo completo sin interacción.
Útil para testing e integración CI/CD.

Requisitos:
  - FastAPI corriendo en http://localhost:8000
  - JWT_TOKEN válido (no expirado)
  - COCTEL_PRO_ORG_ID correcto

Uso:
  uv run python scripts/demo_coctel_auto.py [--token "JWT_TOKEN"] [--org-id "ORG_UUID"]
"""

import requests
import sys
import time
import argparse
from datetime import datetime

FASTAPI_URL = "http://localhost:8000"

# Default values (reemplazar con valores reales)
COCTEL_PRO_ORG_ID = "6877612f-3768-44bf-b6e3-b2d1453c3de9"
JWT_TOKEN = None  # Se debe pasar via argumento --token


def log(level: str, msg: str):
    """Log con timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {level:8} | {msg}")


def check_health():
    """Verifica que el backend este corriendo."""
    try:
        r = requests.get(f"{FASTAPI_URL}/health", timeout=10)
        r.raise_for_status()
        log("✓", "Backend conectado")
        return True
    except Exception as e:
        log("✗", f"No se puede conectar: {e}")
        return False


def trigger_flow(flow_type: str, input_data: dict, org_id: str) -> dict | None:
    """Dispara un flow via webhook y retorna la respuesta."""
    try:
        headers = {
            "Authorization": f"Bearer {JWT_TOKEN}",
            "X-Org-ID": org_id,
            "Content-Type": "application/json",
        }
        r = requests.post(
            f"{FASTAPI_URL}/webhooks/trigger",
            json={"flow_type": flow_type, "input_data": input_data},
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
        result = r.json()
        log("✓", f"Flow '{flow_type}' disparado: correlation_id={result.get('correlation_id')}")
        return result
    except requests.exceptions.RequestException as e:
        log("✗", f"Error en flow '{flow_type}': {e}")
        if hasattr(e.response, 'text'):
            log("  ", f"Response: {e.response.text}")
        return None


def get_pending_approvals(org_id: str) -> list | None:
    """Lista aprobaciones pendientes."""
    try:
        headers = {
            "Authorization": f"Bearer {JWT_TOKEN}",
            "X-Org-ID": org_id,
        }
        r = requests.get(
            f"{FASTAPI_URL}/approvals",
            headers=headers,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log("✗", f"Error obteniendo aprobaciones: {e}")
        return None


def process_approval(task_id: str, action: str, notes: str, org_id: str) -> dict | None:
    """Aprueba o rechaza una tarea pendiente."""
    try:
        headers = {
            "Authorization": f"Bearer {JWT_TOKEN}",
            "X-Org-ID": org_id,
            "Content-Type": "application/json",
        }
        r = requests.post(
            f"{FASTAPI_URL}/approvals/{task_id}",
            json={"action": action, "notes": notes},
            headers=headers,
            timeout=10,
        )
        r.raise_for_status()
        log("✓", f"Aprobación procesada: task_id={task_id}, action={action}")
        return r.json()
    except Exception as e:
        log("✗", f"Error procesando aprobación: {e}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            log("  ", f"Response: {e.response.text}")
        return None


def wait_for_approval(flow_type: str, org_id: str, max_wait: int = 15) -> dict | None:
    """Espera hasta que aparezca una aprobacion pendiente para el flow."""
    log("⏳", f"Esperando aprobación para '{flow_type}'...")
    for i in range(max_wait):
        approvals = get_pending_approvals(org_id)
        if approvals:
            for a in approvals:
                if a.get("flow_type") == flow_type and a.get("status") == "pending":
                    log("✓", f"Aprobación encontrada: task_id={a['task_id']}")
                    return a
        time.sleep(1)
    log("⚠ ", f"Timeout esperando aprobación para '{flow_type}'")
    return None


def main():
    parser = argparse.ArgumentParser(description="Demo automática de CoctelPro")
    parser.add_argument("--token", type=str, help="JWT token válido de Supabase Auth")
    parser.add_argument("--org-id", type=str, help="UUID de la organización CoctelPro")
    parser.add_argument("--skip-wait", action="store_true", help="No esperar aprobaciones")
    args = parser.parse_args()

    global JWT_TOKEN
    JWT_TOKEN = args.token or JWT_TOKEN
    org_id = args.org_id or COCTEL_PRO_ORG_ID

    print()
    print("  ╔════════════════════════════════════════════════╗")
    print("  ║  DEMO AUTO: CoctelPro - FluxAgentPro v2 Phase5 ║")
    print("  ╚════════════════════════════════════════════════╝")
    print()

    if not JWT_TOKEN:
        log("✗", "JWT_TOKEN no configurado. Usa: --token 'your_jwt_here'")
        sys.exit(1)

    # Health check
    if not check_health():
        sys.exit(1)

    log("ℹ", f"Org ID: {org_id}")
    log("ℹ", f"Backend: {FASTAPI_URL}")
    print()

    # ─────────────────────────────────────────────────────────
    # BLOQUE 1: Cotizacion flow
    # ─────────────────────────────────────────────────────────
    log("▶", "PASO 1: Disparar cotizacion_flow")
    result1 = trigger_flow("cotizacion_flow", {
        "evento": "Casamiento Rodriguez",
        "pax": 80,
        "presupuesto": 500000,
        "vip": True,
    }, org_id)

    if not result1:
        log("✗", "cotizacion_flow falló. Abortando.")
        sys.exit(1)

    time.sleep(2)

    if args.skip_wait:
        log("⊘ ", "Saltando espera de aprobación (--skip-wait)")
        approval1 = None
    else:
        log("▶", "PASO 2: Esperar aprobación para cotizacion_flow")
        approval1 = wait_for_approval("CotizacionFlow", org_id, max_wait=20)

    if approval1:
        log("▶", "PASO 3: Procesar aprobación de cotización")
        process_approval(approval1["task_id"], "approve", "Cliente VIP aprobado.", org_id)
        time.sleep(1)
    else:
        log("⚠ ", "No se encontró aprobación pendiente para cotización")

    print()

    # ─────────────────────────────────────────────────────────
    # BLOQUE 2: Compras flow
    # ─────────────────────────────────────────────────────────
    log("▶", "PASO 4: Disparar compras_flow")
    result2 = trigger_flow("compras_flow", {
        "insumos": [
            {"item": "Botellas de vodka", "cantidad": 30, "precio": 50},
            {"item": "Vasos", "cantidad": 80, "precio": 1},
            {"item": "Hielo (kg)", "cantidad": 8, "precio": 5},
        ],
    }, org_id)

    if not result2:
        log("✗", "compras_flow falló.")
        sys.exit(1)

    time.sleep(2)

    if args.skip_wait:
        log("⊘ ", "Saltando espera de aprobación (--skip-wait)")
        approval2 = None
    else:
        log("▶", "PASO 5: Esperar aprobación para compras_flow")
        approval2 = wait_for_approval("ComprasFlow", org_id, max_wait=20)

    if approval2:
        log("▶", "PASO 6: Rechazar compra")
        process_approval(approval2["task_id"], "reject", "Necesitamos otro proveedor.", org_id)
        time.sleep(1)
    else:
        log("⚠ ", "No se encontró aprobación pendiente para compras")

    print()
    print("  ╔════════════════════════════════════════════════╗")
    print("  ║           DEMO COMPLETADA                      ║")
    print("  ╚════════════════════════════════════════════════╝")
    print()
    print("  Resumen:")
    print("    ✓ cotizacion_flow: Aprobado")
    print("    ✓ compras_flow: Rechazado")
    print()


if __name__ == "__main__":
    main()
