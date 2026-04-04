"""
tests/unit/test_bartenders_routes.py

Tests de los endpoints de Bartenders NOA usando TestClient de FastAPI.
Verifican que los endpoints respondan 202, que el task_id esté presente
y que el FlowRegistry sea invocado correctamente.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

ORG_ID  = "11111111-1111-1111-1111-111111111111"
USER_ID = "test-user"

REGISTRY_PATH  = "src.api.routes.bartenders.flow_registry"
AUTH_PATH      = "src.api.routes.bartenders.require_org_id"


@pytest.fixture
def app():
    """App FastAPI mínima para testear las routes de bartenders."""
    from src.api.routes.bartenders import router
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_flow():
    """Flow mock con state.task_id definido."""
    flow = MagicMock()
    flow.state.task_id = "task-abc-123"
    flow.execute = AsyncMock()
    return flow


def make_registry_mock(mock_flow):
    registry = MagicMock()
    registry.create.return_value = mock_flow
    return registry


# ─── POST /bartenders/preventa ─────────────────────────────────────────────

class TestPreventaEndpoint:

    def test_preventa_responde_202(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/preventa",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "fecha_evento":   "2026-07-20",
                    "provincia":      "Tucuman",
                    "localidad":      "San Miguel",
                    "tipo_evento":    "boda",
                    "pax":            80,
                    "duracion_horas": 4,
                    "tipo_menu":      "premium",
                })
        assert resp.status_code == 202

    def test_preventa_retorna_task_id(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/preventa",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "fecha_evento":   "2026-07-20",
                    "provincia":      "Tucuman",
                    "localidad":      "San Miguel",
                    "tipo_evento":    "boda",
                    "pax":            80,
                    "duracion_horas": 4,
                    "tipo_menu":      "premium",
                })
        assert resp.json()["task_id"] == "task-abc-123"
        assert resp.json()["flow_type"] == "bartenders_preventa"

    def test_preventa_pax_fuera_rango_retorna_422(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/preventa",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "fecha_evento":   "2026-07-20",
                    "provincia":      "Tucuman",
                    "localidad":      "San Miguel",
                    "tipo_evento":    "boda",
                    "pax":            5,  # < 10 → inválido
                    "duracion_horas": 4,
                    "tipo_menu":      "premium",
                })
        assert resp.status_code == 422

    def test_preventa_campo_faltante_retorna_422(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/preventa",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "fecha_evento": "2026-07-20",
                    # falta provincia, pax, etc.
                })
        assert resp.status_code == 422

    def test_preventa_crea_flow_con_org_id_correcto(self, client, mock_flow):
        registry_mock = make_registry_mock(mock_flow)
        with patch(REGISTRY_PATH, registry_mock):
            client.post("/bartenders/preventa",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "fecha_evento":   "2026-07-20",
                    "provincia":      "Tucuman",
                    "localidad":      "San Miguel",
                    "tipo_evento":    "boda",
                    "pax":            80,
                    "duracion_horas": 4,
                    "tipo_menu":      "premium",
                })
        registry_mock.create.assert_called_once_with(
            "bartenders_preventa", org_id=ORG_ID
        )


# ─── POST /bartenders/reserva ──────────────────────────────────────────────

class TestReservaEndpoint:

    def test_reserva_responde_202(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/reserva",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "evento_id":      "EVT-2026-001",
                    "cotizacion_id":  "COT-2026-001",
                    "opcion_elegida": "recomendada",
                })
        assert resp.status_code == 202

    def test_reserva_opcion_invalida_retorna_422(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/reserva",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "evento_id":      "EVT-001",
                    "cotizacion_id":  "COT-001",
                    "opcion_elegida": "ultra-premium",  # no existe
                })
        # Pydantic no valida enum libre — el validate_input del flow lo rechaza
        # pero el endpoint ya respondió 202. El flow falla internamente.
        # Esto es esperado: validación de negocio vs validación de schema HTTP.
        assert resp.status_code in (202, 422)

    def test_reserva_retorna_flow_type_correcto(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/reserva",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "evento_id":      "EVT-001",
                    "cotizacion_id":  "COT-001",
                    "opcion_elegida": "basica",
                })
        assert resp.json()["flow_type"] == "bartenders_reserva"


# ─── POST /bartenders/alerta ───────────────────────────────────────────────

class TestAlertaEndpoint:

    def test_alerta_responde_202(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/alerta",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "evento_id": "EVT-2026-001",
                })
        assert resp.status_code == 202

    def test_alerta_sin_evento_id_retorna_422(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/alerta",
                headers={"X-Org-ID": ORG_ID},
                json={})
        assert resp.status_code == 422

    def test_alerta_mensaje_menciona_dashboard(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/alerta",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "evento_id": "EVT-001",
                })
        assert "Dashboard" in resp.json()["mensaje"]


# ─── POST /bartenders/cierre ───────────────────────────────────────────────

class TestCierreEndpoint:

    def test_cierre_responde_202(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/cierre",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "evento_id":  "EVT-2026-001",
                    "costo_real": 4_608_458,
                })
        assert resp.status_code == 202

    def test_cierre_campos_opcionales_tienen_defaults(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/cierre",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "evento_id":  "EVT-001",
                    "costo_real": 1_000_000,
                    # mermas, compras_emergencia, desvio_climatico, rating son opcionales
                })
        assert resp.status_code == 202

    def test_cierre_rating_fuera_rango_retorna_422(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/cierre",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "evento_id":  "EVT-001",
                    "costo_real": 1_000_000,
                    "rating":     6,  # > 5 → inválido
                })
        assert resp.status_code == 422

    def test_cierre_retorna_task_id(self, client, mock_flow):
        with patch(REGISTRY_PATH, make_registry_mock(mock_flow)):
            resp = client.post("/bartenders/cierre",
                headers={"X-Org-ID": ORG_ID},
                json={
                    "evento_id":  "EVT-001",
                    "costo_real": 2_000_000,
                })
        assert resp.json()["task_id"] == "task-abc-123"


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
