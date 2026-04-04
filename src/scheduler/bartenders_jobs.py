"""
src/scheduler/bartenders_jobs.py

Jobs background de Bartenders NOA via APScheduler.

Jobs registrados:
    1. check_upcoming_events_climate  → diario 8AM
       Busca eventos confirmados en exactamente 7 días y dispara AlertaClimaFlow.

    2. update_prices_all_orgs         → lunes 7AM
       Agente 11: actualiza precios de bebidas para todas las orgs.

Integración en FastAPI:
    El scheduler arranca y para junto con el lifespan de FastAPI.
    Ver src/api/main.py para el wiring.

Notas de Fase 6:
    - El scheduler corre en el mismo proceso que FastAPI (AsyncIOScheduler).
    - Para Fase 7 con alta carga: migrar a Celery + Redis.
    - Los jobs usan service_role para leer orgs — no hay tenant activo.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date, timedelta
import structlog

logger = structlog.get_logger(__name__)

# Instancia global — se importa en main.py
scheduler = AsyncIOScheduler(timezone="America/Argentina/Tucuman")


# ─── Job 1: Alerta climática automática ───────────────────────────────────

@scheduler.scheduled_job(
    CronTrigger(hour=8, minute=0),
    id="check_climate_alerts",
    name="Verificar alertas climáticas T-7 días",
    misfire_grace_time=3600,  # si falla, puede correr hasta 1h después
)
async def check_upcoming_events_climate():
    """
    Busca eventos confirmados en exactamente 7 días y dispara AlertaClimaFlow
    para cada uno.

    Se ejecuta todos los días a las 8AM (hora Argentina).
    """
    from src.db.session import get_service_client
    from src.flows.registry import flow_registry

    target_date = date.today() + timedelta(days=7)
    logger.info("scheduler.climate_check.start", target_date=str(target_date))

    try:
        db = get_service_client()
        eventos = (
            db.table("eventos")
            .select("evento_id, org_id, provincia, fecha_evento")
            .eq("status", "confirmado")
            .eq("fecha_evento", target_date.isoformat())
            .execute()
            .data
        ) or []

        if not eventos:
            logger.info("scheduler.climate_check.no_eventos",
                        target_date=str(target_date))
            return

        logger.info("scheduler.climate_check.eventos_encontrados",
                    count=len(eventos), target_date=str(target_date))

        for evento in eventos:
            try:
                flow = flow_registry.create(
                    "bartenders_alerta",
                    org_id  = evento["org_id"],
                    user_id = "scheduler",
                )
                await flow.execute({"evento_id": evento["evento_id"]})

                logger.info("scheduler.climate_check.flow_iniciado",
                            evento_id = evento["evento_id"],
                            org_id    = evento["org_id"])

            except Exception as e:
                # Un evento fallido no detiene los demás
                logger.error("scheduler.climate_check.flow_error",
                             evento_id = evento["evento_id"],
                             error     = str(e))

    except Exception as e:
        logger.error("scheduler.climate_check.error", error=str(e))


# ─── Job 2: Actualización de precios (Agente 11) ──────────────────────────

@scheduler.scheduled_job(
    CronTrigger(day_of_week="mon", hour=7, minute=0),
    id="update_prices",
    name="Agente 11 — Actualizar precios de mercado",
    misfire_grace_time=7200,
)
async def update_prices_all_orgs():
    """
    Ejecuta el Agente 11 para todas las orgs que tienen Bartenders NOA activo.
    Se ejecuta todos los lunes a las 7AM.

    Fase 6: usa MOCK_PRECIOS_ACTUALIZADOS.
    Fase 7: reemplazar con scraping real en cierre_crews.py.
    """
    from src.db.session import get_service_client
    from src.crews.bartenders.cierre_crews import _actualizar_precios
    from src.connectors.supabase_connector import SupabaseMockConnector

    logger.info("scheduler.price_update.start")

    try:
        db = get_service_client()

        # Buscar orgs con bartenders configurados
        # (tienen al menos un bartender en bartenders_disponibles)
        orgs_result = (
            db.table("bartenders_disponibles")
            .select("org_id")
            .execute()
            .data
        ) or []

        # Deduplicar org_ids
        org_ids = list({r["org_id"] for r in orgs_result})

        if not org_ids:
            logger.info("scheduler.price_update.no_orgs")
            return

        logger.info("scheduler.price_update.orgs_encontradas",
                    count=len(org_ids))

        actualizados_total = 0
        ofertas_total      = 0

        for org_id in org_ids:
            try:
                connector = SupabaseMockConnector(
                    org_id  = org_id,
                    user_id = "scheduler",
                )
                resultado = _actualizar_precios(connector)

                actualizados_total += resultado["actualizados"]
                ofertas_total      += resultado["ofertas"]

                logger.info("scheduler.price_update.org_ok",
                            org_id     = org_id,
                            actualizados = resultado["actualizados"],
                            ofertas    = resultado["ofertas"])

            except Exception as e:
                logger.error("scheduler.price_update.org_error",
                             org_id = org_id, error = str(e))

        logger.info("scheduler.price_update.completado",
                    orgs          = len(org_ids),
                    actualizados  = actualizados_total,
                    ofertas       = ofertas_total)

    except Exception as e:
        logger.error("scheduler.price_update.error", error=str(e))
