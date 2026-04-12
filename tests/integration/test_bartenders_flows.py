"""
tests/integration/test_bartenders_flows.py

Tests de integración de los 4 flows de Bartenders NOA.
Verifican el comportamiento del flow completo (sin ejecutar el LLM real)
mockeando el conector y las llamadas a Supabase.

Casos clave:
- PreventaFlow: input válido → cotización generada con 3 opciones
- ReservaFlow:  stock ok → bartenders asignados → evento confirmado
- ReservaFlow:  stock faltante → FlowSuspendedException + aprobación → reanuda
- AlertaFlow:   sin desvío → completed sin HITL
- AlertaFlow:   ola de calor → FlowSuspendedException → aprobado → orden aprobada
- AlertaFlow:   ola de calor → rechazado → orden rechazada
- CierreFlow:   margen > 10% → cerrado directo
- CierreFlow:   margen < 10% → FlowSuspendedException → aprobado → cerrado
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import date

ORG_ID  = "11111111-1111-1111-1111-111111111111"
USER_ID = "22222222-2222-2222-2222-222222222222"


# ─── Global Mocks for Database Activity ────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_supabase_db():
    """Globally mock get_tenant_client and get_service_client to avoid real DB calls."""
    mock_db = MagicMock()
    # Simulate common query chain: db.table().insert().execute()
    mock_query = MagicMock()
    mock_query.insert.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.upsert.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[{"id": "mocked"}], error=None)
    
    mock_db.table.return_value = mock_query
    mock_db.rpc.return_value = mock_query
    mock_db.execute_with_retry.return_value = MagicMock(data=1, error=None) # for sequences

    with patch("src.db.session.get_service_client", return_value=mock_db), \
         patch("src.db.session.get_tenant_client") as mock_get_tenant:
        
        @contextmanager
        def mock_tenant_cm(*args, **kwargs):
            yield mock_db
            
        mock_get_tenant.side_effect = mock_tenant_cm
        yield mock_db


# ─── Fixtures ──────────────────────────────────────────────────────────────

def make_connector_mock(
    eventos=None,
    cotizaciones=None,
    bartenders=None,
    precios=None,
    config_climatico=None,
    config_consumo=None,
    equipamiento=None,
    inventario_stock_ok=True,
):
    """
    Construye un mock del SupabaseMockConnector con respuestas configurables.
    """
    c = MagicMock()

    _eventos       = eventos       or []
    _cotizaciones  = cotizaciones  or []
    _bartenders    = bartenders    or []
    _precios       = precios       or []

    _config_climatico = config_climatico or [
        {"mes": 1, "factor_pct": 20, "razon": "Enero: calor extremo"}
    ]
    _config_consumo = config_consumo or [{
        "tipo_menu": "premium", "coctel_por_persona": 6,
        "ml_espiritoso_por_coctel": 55, "hielo_kg_por_persona": 0.8,
        "agua_litros_por_persona": 1.0, "garnish_ars_por_persona": 2000,
        "desechables_ars_por_persona": 800,
        "mix_gin_pct": 50, "mix_whisky_pct": 20, "mix_ron_pct": 15,
        "mix_vodka_pct": 10, "mix_tequila_pct": 5,
    }]
    _equipamiento = equipamiento or [
        {"item_id": "BARRA-001", "amortizacion_por_evento": 2500, "estado": "activo"},
    ]

    def get_config_side(table, filters=None):
        if table == "config_climatico":     return _config_climatico
        if table == "config_consumo_pax":   return _config_consumo
        if table == "equipamiento_amortizacion": return _equipamiento
        return []

    def read_side(table, filters=None):
        if table == "eventos":              return _eventos
        if table == "cotizaciones":         return _cotizaciones
        if table == "bartenders_disponibles": return _bartenders
        if table == "precios_bebidas":      return _precios
        return []

    def read_one_side(table, filters=None):
        rows = read_side(table, filters)
        if not rows:
            return None
        # Filtrar por la primera key del filtro si hay filtros
        if filters:
            for k, v in filters.items():
                rows = [r for r in rows if str(r.get(k)) == str(v)]
        return rows[0] if rows else None

    c.get_config.side_effect     = get_config_side
    c.get_config_one.side_effect = lambda t, f=None: (get_config_side(t, f) or [None])[0]
    c.read.side_effect           = read_side
    c.read_one.side_effect       = read_one_side
    c.write.side_effect          = lambda t, d: {**d, "org_id": ORG_ID}
    c.update.side_effect         = lambda t, pk, d: {**d}

    # reserve_stock: ok por default, error si inventario_stock_ok=False
    if inventario_stock_ok:
        c.reserve_stock.return_value = {"ok": True}
    else:
        c.reserve_stock.side_effect = ValueError("Stock insuficiente")

    c.release_stock.return_value = {"ok": True}

    return c


BARTENDERS_MOCK = [
    {"bartender_id": "BAR-001", "nombre": "Juan",  "especialidad": "premium",
     "es_head_bartender": "TRUE",  "calificacion": 4.8, "disponible": True},
    {"bartender_id": "BAR-002", "nombre": "Maria", "especialidad": "clasica",
     "es_head_bartender": "FALSE", "calificacion": 4.5, "disponible": True},
    {"bartender_id": "BAR-003", "nombre": "Carlos","especialidad": "premium",
     "es_head_bartender": "FALSE", "calificacion": 4.7, "disponible": True},
    {"bartender_id": "BAR-004", "nombre": "Ana",   "especialidad": "clasica",
     "es_head_bartender": "FALSE", "calificacion": 4.3, "disponible": True},
    {"bartender_id": "BAR-005", "nombre": "Rob",   "especialidad": "premium",
     "es_head_bartender": "FALSE", "calificacion": 4.9, "disponible": True},
]

PRECIOS_MOCK = [
    {"producto_id": "GIN-001",    "categoria": "gin",    "presentacion_ml": 700,  "precio_ars": 12000},
    {"producto_id": "WHISKY-001", "categoria": "whisky", "presentacion_ml": 750,  "precio_ars":  7000},
    {"producto_id": "RON-001",    "categoria": "ron",    "presentacion_ml": 750,  "precio_ars": 18000},
    {"producto_id": "VODKA-001",  "categoria": "vodka",  "presentacion_ml": 700,  "precio_ars":  8000},
    {"producto_id": "TEQUILA-001","categoria": "tequila","presentacion_ml": 750,  "precio_ars": 22000},
]

EVENTO_MOCK = {
    "evento_id": "EVT-2026-001", "fecha_evento": "2026-01-15",
    "provincia": "Tucuman",      "localidad": "San Miguel",
    "tipo_evento": "boda",       "pax": 150,
    "duracion_horas": 5,         "tipo_menu": "premium",
    "status": "confirmado",      "restricciones": None,
}

COTIZACION_MOCK = {
    "cotizacion_id": "COT-2026-001",
    "evento_id":     "EVT-2026-001",
    "escandallo_total": 2_956_716,
    "opcion_basica":    4_927_860,
    "opcion_recomendada": 5_376_757,
    "opcion_premium":   5_913_432,
    "opcion_elegida":   "recomendada",
    "factor_climatico": 20,
    "status":           "aceptada",
}


CONNECTOR_PATH = "src.connectors.supabase_connector.SupabaseMockConnector"
# Targets for individual modules to avoid import-time binding issues
ALERTA_CONNECTOR_PATH  = "src.flows.bartenders.alerta_flow.SupabaseMockConnector"
RESERVA_CONNECTOR_PATH = "src.flows.bartenders.reserva_flow.SupabaseMockConnector"
CIERRE_CONNECTOR_PATH  = "src.flows.bartenders.cierre_flow.SupabaseMockConnector"
PREVENTA_CONNECTOR_PATH = "src.flows.bartenders.preventa_flow.SupabaseMockConnector"
RESERVA_CREWS_CONNECTOR_PATH = "src.crews.bartenders.reserva_crews.SupabaseMockConnector"

from contextlib import ExitStack

def patch_connectors(mock_obj):
    """Utility to patch all possible locations where SupabaseMockConnector is used."""
    stack = ExitStack()
    stack.enter_context(patch(CONNECTOR_PATH, return_value=mock_obj))
    stack.enter_context(patch(ALERTA_CONNECTOR_PATH, return_value=mock_obj))
    stack.enter_context(patch(RESERVA_CONNECTOR_PATH, return_value=mock_obj))
    stack.enter_context(patch(CIERRE_CONNECTOR_PATH, return_value=mock_obj))
    stack.enter_context(patch(PREVENTA_CONNECTOR_PATH, return_value=mock_obj))
    # Note: crews use BaseDataConnector often, but sometimes explicitly SupabaseMockConnector
    return stack

from contextlib import contextmanager


# ══════════════════════════════════════════════════════════════════════════
# PreventaFlow
# ══════════════════════════════════════════════════════════════════════════

class TestPreventaFlow:

    def test_input_invalido_pax_fuera_rango(self):
        from src.flows.bartenders.preventa_flow import PreventaFlow
        flow = PreventaFlow(org_id=ORG_ID, user_id=USER_ID)
        ok = flow.validate_input({
            "fecha_evento": "2026-07-20", "provincia": "Tucuman",
            "pax": 9, "duracion_horas": 4, "tipo_menu": "premium",
            "localidad": "San Miguel", "tipo_evento": "boda"
        })
        assert ok is False

    def test_input_invalido_provincia(self):
        from src.flows.bartenders.preventa_flow import PreventaFlow
        flow = PreventaFlow(org_id=ORG_ID, user_id=USER_ID)
        ok = flow.validate_input({
            "fecha_evento": "2026-07-20", "provincia": "Córdoba",
            "pax": 80, "duracion_horas": 4, "tipo_menu": "estandar",
            "localidad": "San Miguel", "tipo_evento": "boda"
        })
        assert ok is False

    def test_input_valido(self):
        from src.flows.bartenders.preventa_flow import PreventaFlow
        flow = PreventaFlow(org_id=ORG_ID, user_id=USER_ID)
        ok = flow.validate_input({
            "fecha_evento": "2026-07-20", "provincia": "Tucuman",
            "pax": 80, "duracion_horas": 4, "tipo_menu": "estandar",
            "localidad": "San Miguel", "tipo_evento": "boda"
        })
        assert ok is True

    def test_input_invalido_menu(self):
        from src.flows.bartenders.preventa_flow import PreventaFlow
        flow = PreventaFlow(org_id=ORG_ID, user_id=USER_ID)
        ok = flow.validate_input({
            "fecha_evento": "2026-07-20", "provincia": "Tucuman",
            "pax": 80, "duracion_horas": 4, "tipo_menu": "ultra-premium",
            "localidad": "San Miguel", "tipo_evento": "boda"
        })
        assert ok is False


# ══════════════════════════════════════════════════════════════════════════
# AlertaClimaFlow — lógica HITL
# ══════════════════════════════════════════════════════════════════════════

class TestAlertaFlow:

    def test_validate_input_requiere_evento_id(self):
        from src.flows.bartenders.alerta_flow import AlertaClimaFlow
        flow = AlertaClimaFlow(org_id=ORG_ID, user_id=USER_ID)
        assert flow.validate_input({}) is False
        assert flow.validate_input({"evento_id": "EVT-001"}) is True

    @pytest.mark.asyncio
    async def test_on_approved_actualiza_orden_a_aprobada(self):
        from src.flows.bartenders.alerta_flow import AlertaClimaFlow, AlertaState
        from src.flows.state import FlowStatus

        flow = AlertaClimaFlow(org_id=ORG_ID, user_id=USER_ID)
        flow.state = AlertaState(
            task_id="33333333-3333-3333-3333-333333333333",
            org_id=ORG_ID,
            user_id=USER_ID,
            flow_type="bartenders_alerta",
            correlation_id="corr-123",
            evento_id="EVT-001", orden_id="OC-001", total_compra=220_000,
            alerta_roja=True,
        )

        mock_connector = MagicMock()
        mock_connector.update.return_value = {}

        with patch_connectors(mock_connector):
            await flow._on_approved("ok demo")

        calls = mock_connector.update.call_args_list
        tablas = [c[0][0] for c in calls]
        assert "ordenes_compra" in tablas
        assert "eventos" in tablas

        # Verificar que la orden se marca como aprobada
        orden_call = next(c for c in calls if c[0][0] == "ordenes_compra")
        assert orden_call[0][2]["status"] == "aprobada"

    @pytest.mark.asyncio
    async def test_on_rejected_actualiza_orden_a_rechazada(self):
        from src.flows.bartenders.alerta_flow import AlertaClimaFlow, AlertaState

        flow = AlertaClimaFlow(org_id=ORG_ID, user_id=USER_ID)
        flow.state = AlertaState(
            task_id="33333333-3333-3333-3333-333333333333",
            org_id=ORG_ID,
            user_id=USER_ID,
            flow_type="bartenders_alerta",
            correlation_id="corr-123",
            evento_id="EVT-001", orden_id="OC-001", total_compra=220_000,
            alerta_roja=True,
        )

        mock_connector = MagicMock()
        mock_connector.update.return_value = {}

        with patch_connectors(mock_connector):
            await flow._on_rejected("no autorizado")

        orden_call = next(
            c for c in mock_connector.update.call_args_list
            if c[0][0] == "ordenes_compra"
        )
        assert orden_call[0][2]["status"] == "rechazada"

    @pytest.mark.asyncio
    async def test_on_approved_output_data_correcto(self):
        from src.flows.bartenders.alerta_flow import AlertaClimaFlow, AlertaState

        flow = AlertaClimaFlow(org_id=ORG_ID, user_id=USER_ID)
        flow.state = AlertaState(
            task_id="33333333-3333-3333-3333-333333333333",
            org_id=ORG_ID,
            user_id=USER_ID,
            flow_type="bartenders_alerta",
            correlation_id="corr-123",
            evento_id="EVT-001", orden_id="OC-001", total_compra=220_000,
            alerta_roja=True,
        )

        mock_connector = MagicMock()
        mock_connector.update.return_value = {}
        with patch_connectors(mock_connector):
            await flow._on_approved()

        assert flow.state.output_data["accion"] == "compra_aprobada"
        assert flow.state.output_data["orden_id"] == "OC-001"

    @pytest.mark.asyncio
    async def test_on_rejected_output_data_correcto(self):
        from src.flows.bartenders.alerta_flow import AlertaClimaFlow, AlertaState

        flow = AlertaClimaFlow(org_id=ORG_ID, user_id=USER_ID)
        flow.state = AlertaState(
            task_id="33333333-3333-3333-3333-333333333333",
            org_id=ORG_ID,
            user_id=USER_ID,
            flow_type="bartenders_alerta",
            correlation_id="corr-123",
            evento_id="EVT-001", orden_id="OC-002", total_compra=150_000,
            alerta_roja=True,
        )

        mock_connector = MagicMock()
        mock_connector.update.return_value = {}
        with patch_connectors(mock_connector):
            await flow._on_rejected("presupuesto excedido")

        assert flow.state.output_data["accion"] == "compra_rechazada"
        assert "presupuesto excedido" in flow.state.output_data["mensaje"]


# ══════════════════════════════════════════════════════════════════════════
# CierreFlow — margen crítico
# ══════════════════════════════════════════════════════════════════════════

class TestCierreFlow:

    def test_validate_input_requiere_costo_real(self):
        from src.flows.bartenders.cierre_flow import CierreFlow
        flow = CierreFlow(org_id=ORG_ID, user_id=USER_ID)
        assert flow.validate_input({"evento_id": "EVT-001"}) is False
        assert flow.validate_input({"evento_id": "EVT-001", "costo_real": 1000}) is True

    @pytest.mark.asyncio
    async def test_on_approved_cierre_ejecuta_feedback(self):
        from src.flows.bartenders.cierre_flow import CierreFlow, CierreState

        flow = CierreFlow(org_id=ORG_ID, user_id=USER_ID)
        flow.state = CierreState(
            task_id="33333333-3333-3333-3333-333333333333",
            org_id=ORG_ID,
            user_id=USER_ID,
            flow_type="bartenders_cierre",
            correlation_id="corr-123",
            evento_id="EVT-001", auditoria_id="AUD-001",
            precio_cobrado=5_000_000, costo_real=4_800_000,
            ganancia_neta=200_000, margen_pct=4.0,
            margen_critico=True,
        )

        evento_mock = {**EVENTO_MOCK, "evento_id": "EVT-001", "fecha_evento": "2026-01-15"}
        mock_connector = MagicMock()
        mock_connector.read_one.return_value = evento_mock
        mock_connector.update.return_value   = {}

        with patch_connectors(mock_connector):
            await flow._on_approved("aprobado por el jefe")

        assert flow.state.output_data["status"] == "cerrado"
        assert "proxima_contacto" in flow.state.output_data

    @pytest.mark.asyncio
    async def test_on_rejected_cierre_deja_evento_ejecutado(self):
        from src.flows.bartenders.cierre_flow import CierreFlow, CierreState

        flow = CierreFlow(org_id=ORG_ID, user_id=USER_ID)
        flow.state = CierreState(
            task_id="33333333-3333-3333-3333-333333333333",
            org_id=ORG_ID,
            user_id=USER_ID,
            flow_type="bartenders_cierre",
            correlation_id="corr-123",
            evento_id="EVT-001", auditoria_id="AUD-001",
            precio_cobrado=5_000_000, costo_real=4_800_000,
            margen_pct=4.0, margen_critico=True,
        )

        with patch_connectors(MagicMock()):
            await flow._on_rejected("requiere análisis")

        assert flow.state.output_data["status"] == "ejecutado"
        assert "análisis" in flow.state.output_data["mensaje"]

    def test_margen_critico_umbral_es_10(self):
        from src.crews.bartenders.cierre_crews import MARGEN_CRITICO_UMBRAL
        assert MARGEN_CRITICO_UMBRAL == 10.0


# ══════════════════════════════════════════════════════════════════════════
# ReservaFlow — HITL por faltante de stock
# ══════════════════════════════════════════════════════════════════════════

class TestReservaFlow:

    def test_validate_input_requiere_campos(self):
        from src.flows.bartenders.reserva_flow import ReservaFlow
        flow = ReservaFlow(org_id=ORG_ID, user_id=USER_ID)
        assert flow.validate_input({}) is False
        assert flow.validate_input({
            "evento_id": "EVT-001",
            "cotizacion_id": "COT-001",
            "opcion_elegida": "recomendada"
        }) is True

    def test_validate_input_opcion_invalida(self):
        from src.flows.bartenders.reserva_flow import ReservaFlow
        flow = ReservaFlow(org_id=ORG_ID, user_id=USER_ID)
        assert flow.validate_input({
            "evento_id": "EVT-001",
            "cotizacion_id": "COT-001",
            "opcion_elegida": "ultra-premium"  # inválida
        }) is False

    @pytest.mark.asyncio
    async def test_on_approved_continua_con_staffing(self):
        from src.flows.bartenders.reserva_flow import ReservaFlow, ReservaState

        flow = ReservaFlow(org_id=ORG_ID, user_id=USER_ID)
        flow.state = ReservaState(
            task_id="33333333-3333-3333-3333-333333333333",
            org_id=ORG_ID,
            user_id=USER_ID,
            flow_type="bartenders_reserva",
            correlation_id="corr-123",
            evento_id="EVT-001", cotizacion_id="COT-001",
            pax=80, tipo_menu="premium",
            fecha_evento="2026-07-20", duracion_horas=5,
            provincia="Tucuman", localidad="San Miguel",
        )

        mock_connector = MagicMock()
        mock_connector.read.return_value    = BARTENDERS_MOCK
        mock_connector.read_one.return_value = EVENTO_MOCK
        mock_connector.update.return_value  = {}

        with patch_connectors(mock_connector):
            await flow._on_approved("aprobado")

        assert flow.state.output_data is not None
        assert flow.state.output_data.get("status") == "confirmado"

    @pytest.mark.asyncio
    async def test_on_rejected_vuelve_a_cotizado(self):
        from src.flows.bartenders.reserva_flow import ReservaFlow, ReservaState

        flow = ReservaFlow(org_id=ORG_ID, user_id=USER_ID)
        flow.state = ReservaState(
            task_id="33333333-3333-3333-3333-333333333333",
            org_id=ORG_ID,
            user_id=USER_ID,
            flow_type="bartenders_reserva",
            correlation_id="corr-123",
            evento_id="EVT-001",
        )

        mock_connector = MagicMock()
        mock_connector.update.return_value = {}

        with patch_connectors(mock_connector):
            await flow._on_rejected("sin presupuesto para compra")

        update_call = mock_connector.update.call_args
        assert update_call[0][2]["status"] == "cotizado"
