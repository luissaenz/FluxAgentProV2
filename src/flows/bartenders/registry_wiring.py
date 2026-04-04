"""
src/flows/bartenders/registry_wiring.py

Registro de los flows de Bartenders NOA en el FlowRegistry global.

Cómo usar:
    Importar este módulo en src/api/main.py durante el startup:

        from src.flows.bartenders.registry_wiring import register_bartenders_flows
        register_bartenders_flows()

Los flows se registran con sus nombres canónicos que coinciden con
los flow_type usados en los webhooks y en el scheduler.
"""

from src.flows.registry import flow_registry
from src.flows.bartenders.preventa_flow import PreventaFlow
from src.flows.bartenders.reserva_flow  import ReservaFlow
from src.flows.bartenders.alerta_flow   import AlertaClimaFlow
from src.flows.bartenders.cierre_flow   import CierreFlow


def register_bartenders_flows() -> None:
    """Registra los 4 flows de Bartenders NOA en el FlowRegistry."""
    flow_registry.register("bartenders_preventa", PreventaFlow)
    flow_registry.register("bartenders_reserva",  ReservaFlow)
    flow_registry.register("bartenders_alerta",   AlertaClimaFlow)
    flow_registry.register("bartenders_cierre",   CierreFlow)


# ─── Diff de main.py ──────────────────────────────────────────────────────
#
# Aplicar los siguientes cambios a src/api/main.py existente:
#
# 1. Importar el registro de flows y el scheduler:
#
#   from src.flows.bartenders.registry_wiring import register_bartenders_flows
#   from src.scheduler.bartenders_jobs import scheduler
#   from src.api.routes.bartenders import router as bartenders_router
#
# 2. En el lifespan, arrancar/parar el scheduler y registrar flows:
#
#   @asynccontextmanager
#   async def lifespan(app: FastAPI):
#       # ── Startup ──────────────────────────────────────────────────
#       register_bartenders_flows()           # ← NUEVO
#       scheduler.start()                     # ← NUEVO
#
#       # Recovery de tasks zombies (ya existía)
#       await recover_orphaned_tasks()
#
#       yield
#
#       # ── Shutdown ─────────────────────────────────────────────────
#       scheduler.shutdown(wait=False)        # ← NUEVO
#
# 3. Registrar el router de bartenders:
#
#   app.include_router(bartenders_router)     # ← NUEVO
#
# El archivo main.py completo queda así (solo las líneas relevantes):
# ─────────────────────────────────────────────────────────────────────────

MAIN_PY_PATCH = '''
# ── Imports nuevos (agregar a los existentes) ────────────────────────────
from contextlib import asynccontextmanager
from src.flows.bartenders.registry_wiring import register_bartenders_flows
from src.scheduler.bartenders_jobs import scheduler
from src.api.routes.bartenders import router as bartenders_router


# ── Lifespan actualizado ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    register_bartenders_flows()
    scheduler.start()
    await recover_orphaned_tasks()   # existente
    yield
    # Shutdown
    scheduler.shutdown(wait=False)


# ── Router registrado ────────────────────────────────────────────────────
app.include_router(bartenders_router)
'''
