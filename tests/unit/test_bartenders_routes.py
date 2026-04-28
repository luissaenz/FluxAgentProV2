"""
tests/unit/test_bartenders_routes.py

Tests de los endpoints de Bartenders NOA usando TestClient de FastAPI.
Verifican que los endpoints respondan 202, que el task_id esté presente
y que el FlowRegistry sea invocado correctamente.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Mock apscheduler since it might not be in the test environment
class MockScheduler:
    def __init__(self, *args, **kwargs): pass
    def scheduled_job(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

class MockCronTrigger:
    def __init__(self, *args, **kwargs): pass

mock_apscheduler_asyncio = MagicMock()
mock_apscheduler_asyncio.AsyncIOScheduler = MockScheduler
mock_apscheduler_cron = MagicMock()
mock_apscheduler_cron.CronTrigger = MockCronTrigger

sys.modules['apscheduler'] = MagicMock()
sys.modules['apscheduler.schedulers'] = MagicMock()
sys.modules['apscheduler.schedulers.asyncio'] = mock_apscheduler_asyncio
sys.modules['apscheduler.triggers'] = MagicMock()
sys.modules['apscheduler.triggers.cron'] = mock_apscheduler_cron

ORG_ID  = "11111111-1111-1111-1111-111111111111"
USER_ID = "test-user"

# ─── Scheduler jobs ────────────────────────────────────────────────────────

class TestSchedulerJobs:

    @pytest.mark.asyncio
    async def test_check_climate_no_eventos(self):
        """Si no hay eventos en 7 días, el job termina sin disparar flows."""
        from src.scheduler.bartenders_jobs import check_upcoming_events_climate

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value\
            .eq.return_value.eq.return_value.execute.return_value\
            .data = []

        with patch("src.db.session.get_service_client",
                   return_value=mock_db), \
             patch("src.flows.registry.flow_registry") as mock_reg:
            await check_upcoming_events_climate()

        mock_reg.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_climate_un_evento_dispara_flow(self):
        """Si hay 1 evento en 7 días, se dispara AlertaClimaFlow."""
        from src.scheduler.bartenders_jobs import check_upcoming_events_climate

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value\
            .eq.return_value.eq.return_value.execute.return_value\
            .data = [{"evento_id": "EVT-001", "org_id": ORG_ID}]

        mock_flow = MagicMock()
        mock_flow.execute = AsyncMock()

        with patch("src.db.session.get_service_client",
                   return_value=mock_db), \
             patch("src.flows.registry.flow_registry") as mock_reg:
            mock_reg.create.return_value = mock_flow
            await check_upcoming_events_climate()

        mock_reg.create.assert_called_once_with(
            "bartenders_alerta",
            org_id  = ORG_ID,
            user_id = "scheduler",
        )
        mock_flow.execute.assert_called_once_with({"evento_id": "EVT-001"})

    @pytest.mark.asyncio
    async def test_check_climate_error_en_un_evento_no_detiene_otros(self):
        """Un error en un evento no detiene el procesamiento de los demás."""
        from src.scheduler.bartenders_jobs import check_upcoming_events_climate

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value\
            .eq.return_value.eq.return_value.execute.return_value\
            .data = [
                {"evento_id": "EVT-001", "org_id": ORG_ID},
                {"evento_id": "EVT-002", "org_id": ORG_ID},
            ]

        call_count = 0
        async def execute_side_effect(input_data):
            nonlocal call_count
            call_count += 1
            if input_data["evento_id"] == "EVT-001":
                raise Exception("Error simulado")

        mock_flow = MagicMock()
        mock_flow.execute = execute_side_effect

        with patch("src.db.session.get_service_client",
                   return_value=mock_db), \
             patch("src.flows.registry.flow_registry") as mock_reg:
            mock_reg.create.return_value = mock_flow
            await check_upcoming_events_climate()

        # Ambos flows fueron intentados
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_update_prices_sin_orgs(self):
        """Si no hay orgs con bartenders, el job termina sin actualizar."""
        from src.scheduler.bartenders_jobs import update_prices_all_orgs

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value\
            .execute.return_value.data = []

        with patch("src.db.session.get_service_client",
                   return_value=mock_db), \
             patch("src.crews.bartenders.cierre_crews._actualizar_precios") as mock_act:
            await update_prices_all_orgs()

        mock_act.assert_not_called()
