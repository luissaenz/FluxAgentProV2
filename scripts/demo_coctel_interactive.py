"""
Demo interactiva de CoctelPro con pasos sincronizados.
Para validar el flujo completo con aprobaciones en tiempo real.

Uso:
  uv run python scripts/demo_coctel_interactive.py --token "JWT_TOKEN"
"""

import requests
import sys
import time
import argparse
from datetime import datetime

FASTAPI_URL = "http://localhost:8000"
COCTEL_PRO_ORG_ID = "6877612f-3768-44bf-b6e3-b2d1453c3de9"
JWT_TOKEN = None


def log(level: str, msg: str):
    """Log con timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {level:8} | {msg}")


def pause(msg: str = "Presiona ENTER para continuar..."):
    """Pausa no-bloqueante que muestra un mensaje."""
    print(f"\n{'='*70}")
    print(f"  {msg}")
    print(f"{'='*70}")
    try:
        input("  > ")
    except (EOFError, KeyboardInterrupt):
        print("\n  (Demo finalizada por el usuario)")
        sys.exit(0)


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
    """Dispara un flow via webhook."""
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
        log("✓", f"Flow disparado: {flow_type}")
        log("  ", f"correlation_id: {result.get('correlation_id')}")
        return result
    except Exception as e:
        log("✗", f"Error en flow: {e}")
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
    """Procesa una aprobación."""
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
        log("✓", f"Aprobación procesada: action={action}")
        return r.json()
    except Exception as e:
        log("✗", f"Error procesando: {e}")
        return None


def wait_for_approval(flow_type: str, org_id: str, max_wait: int = 30) -> dict | None:
    """Espera aprobación con output en vivo."""
    log("⏳", f"Esperando aprobación para '{flow_type}'...")
    for i in range(max_wait):
        approvals = get_pending_approvals(org_id)
        if approvals:
            for a in approvals:
                if a.get("flow_type") == flow_type and a.get("status") == "pending":
                    log("✓", f"Aprobación encontrada!")
                    log("  ", f"task_id: {a['task_id']}")
                    return a
        if (i + 1) % 5 == 0:
            log("⏳", f"Esperando... ({i+1}s / {max_wait}s)")
        time.sleep(1)
    log("✗", f"Timeout esperando aprobación")
    return None


def main():
    parser = argparse.ArgumentParser(description="Demo interactiva de CoctelPro")
    parser.add_argument("--token", type=str, required=True, help="JWT token válido")
    parser.add_argument("--org-id", type=str, help="UUID de la organización")
    args = parser.parse_args()

    global JWT_TOKEN
    JWT_TOKEN = args.token
    org_id = args.org_id or COCTEL_PRO_ORG_ID

    print()
    print("  ╔═══════════════════════════════════════════════════╗")
    print("  ║   DEMO INTERACTIVA: CoctelPro - FluxAgentPro v2   ║")
    print("  ╚═══════════════════════════════════════════════════╝")
    print()

    if not check_health():
        sys.exit(1)

    log("ℹ", f"Org ID: {org_id}")
    log("ℹ", f"Backend: {FASTAPI_URL}")
    print()

    # SETUP
    pause("1️⃣  Abrir Dashboard en http://localhost:3000")
    pause("2️⃣  Iniciar sesión con el usuario demo")
    pause("3️⃣  Seleccionar la organización CoctelPro")

    print()
    print()

    # COTIZACION FLOW
    pause("4️⃣  DISPARAR COTIZACIÓN: Cliente VIP, 80 pax, $500.000")

    log("▶", "Disparando cotizacion_flow...")
    result1 = trigger_flow("cotizacion_flow", {
        "evento": "Casamiento Rodriguez",
        "pax": 80,
        "presupuesto": 500000,
        "vip": True,
    }, org_id)

    if not result1:
        log("✗", "Flow falló. Abortando.")
        sys.exit(1)

    time.sleep(2)

    pause("5️⃣  Observar Kanban: card en 'Ejecutando' → 'HITL (Espera)'")

    log("▶", "Buscando aprobación pendiente...")
    approval1 = wait_for_approval("CotizacionFlow", org_id)

    if approval1:
        pause("6️⃣  Centro de Aprobaciones: Revisar payload de cotización")
        pause("7️⃣  APROBAR la cotización (o continuamos automáticamente)")

        log("▶", "Aprobando cotización...")
        process_approval(approval1["task_id"], "approve", "Cliente VIP, aprobado.", org_id)
        time.sleep(1)
    else:
        log("⚠ ", "No se encontró aprobación. Continuando...")

    pause("8️⃣  Observar Kanban: card pasó a 'Completado' en tiempo real")

    print()
    print()

    # COMPRAS FLOW
    pause("9️⃣  DISPARAR COMPRAS: Orden de insumos")

    log("▶", "Disparando compras_flow...")
    result2 = trigger_flow("compras_flow", {
        "insumos": [
            {"item": "Botellas de vodka", "cantidad": 30, "precio": 50},
            {"item": "Vasos", "cantidad": 80, "precio": 1},
            {"item": "Hielo (kg)", "cantidad": 8, "precio": 5},
        ],
    }, org_id)

    if not result2:
        log("✗", "Flow falló.")
        sys.exit(1)

    time.sleep(2)

    pause("🔟 Observar Kanban: card apareció en 'HITL (Espera)' (compras SIEMPRE requiere aprobación)")

    log("▶", "Buscando aprobación pendiente...")
    approval2 = wait_for_approval("ComprasFlow", org_id)

    if approval2:
        pause("1️⃣1️⃣  Centro de Aprobaciones: RECHAZAR esta compra")

        log("▶", "Rechazando compra...")
        process_approval(approval2["task_id"], "reject", "Necesitamos otro proveedor.", org_id)
        time.sleep(1)
    else:
        log("⚠ ", "No se encontró aprobación. Continuando...")

    pause("1️⃣2️⃣  Observar Kanban: card pasó a 'Rechazado'")

    pause("1️⃣3️⃣  Vista de Eventos: mostrar trail completo de ambos flows")

    print()
    print("  ╔═══════════════════════════════════════════════════╗")
    print("  ║                 DEMO COMPLETADA ✓                 ║")
    print("  ╚═══════════════════════════════════════════════════╝")
    print()
    print("  Resumen:")
    print("    ✓ cotizacion_flow: VIP 80pax → HITL → Aprobado → Completado")
    print("    ✓ compras_flow: Insumos → HITL → Rechazado")
    print("    ✓ Kanban actualizado en tiempo real")
    print("    ✓ Trail de eventos completo")
    print()


if __name__ == "__main__":
    main()
