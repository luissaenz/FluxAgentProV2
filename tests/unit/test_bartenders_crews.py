"""
tests/unit/test_bartenders_crews.py

Tests de los crews de Bartenders NOA.
Verifican la lógica determinista (cálculos, persistencia)
sin ejecutar el LLM — los Crew se testean solo en integración.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import date

# ─── Helpers de crews (funciones deterministas) ────────────────────────────
from src.crews.bartenders.preventa_crews import (
    _calcular_opciones,
    _registrar_evento,
    MARGENES,
)
from src.crews.bartenders.reserva_crews import (
    _calcular_items_orden,
    _seleccionar_bartenders,
    _generar_hoja_de_ruta,
)
from src.crews.bartenders.cierre_crews import (
    _guardar_auditoria,
    _actualizar_precios,
    MARGEN_CRITICO_UMBRAL,
    MOCK_PRECIOS_ACTUALIZADOS,
)

ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def mock_connector():
    c = MagicMock()
    c.write.side_effect = lambda table, data: {**data, "org_id": ORG_ID}
    c.update.side_effect = lambda table, pk, data: {**data}
    c.read.return_value = []
    c.read_one.return_value = None
    c.get_config.return_value = []
    c.get_config_one.return_value = None
    return c


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 4: Cálculo de opciones de cotización
# ══════════════════════════════════════════════════════════════════════════

class TestCalcularOpciones:

    def test_formula_margen_40(self):
        """precio = escandallo / (1 - 0.40) = escandallo / 0.60"""
        opciones = _calcular_opciones(2_956_716)
        assert opciones["basica"] == round(2_956_716 / 0.60)

    def test_formula_margen_45(self):
        """precio = escandallo / (1 - 0.45) = escandallo / 0.55"""
        opciones = _calcular_opciones(2_956_716)
        assert opciones["recomendada"] == round(2_956_716 / 0.55)

    def test_formula_margen_50(self):
        """precio = escandallo / (1 - 0.50) = escandallo / 0.50"""
        opciones = _calcular_opciones(2_956_716)
        assert opciones["premium"] == round(2_956_716 / 0.50)

    def test_caso_canonico_spec(self):
        """
        Caso de la spec: escandallo 2.956.716
        → recomendada = 2.956.716 / 0.55 ≈ 5.375.847
        """
        opciones = _calcular_opciones(2_956_716)
        # Verificar contra la fórmula exacta
        assert opciones["recomendada"] == round(2_956_716 / 0.55)

    def test_opciones_en_orden_ascendente(self):
        opciones = _calcular_opciones(1_000_000)
        assert opciones["basica"] < opciones["recomendada"] < opciones["premium"]

    def test_tres_margenes_definidos(self):
        assert set(MARGENES.keys()) == {"basica", "recomendada", "premium"}
        assert MARGENES["basica"]      == 0.40
        assert MARGENES["recomendada"] == 0.45
        assert MARGENES["premium"]     == 0.50


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 1: Registro de evento
# ══════════════════════════════════════════════════════════════════════════

class TestRegistrarEvento:

    def test_inyecta_status_nuevo(self, mock_connector):
        _registrar_evento(mock_connector, {
            "fecha_evento":   "2026-07-20",
            "provincia":      "Tucuman",
            "localidad":      "San Miguel",
            "tipo_evento":    "corporativo",
            "pax":            60,
            "duracion_horas": 4,
            "tipo_menu":      "estandar",
        })
        args = mock_connector.write.call_args
        assert args[0][1]["status"] == "nuevo"

    def test_genera_evento_id(self, mock_connector):
        _registrar_evento(mock_connector, {
            "fecha_evento":   "2026-07-20",
            "provincia":      "Tucuman",
            "localidad":      "San Miguel",
            "tipo_evento":    "corporativo",
            "pax":            60,
            "duracion_horas": 4,
            "tipo_menu":      "estandar",
        })
        args = mock_connector.write.call_args
        evento_id = args[0][1]["evento_id"]
        assert evento_id.startswith("EVT-")

    def test_convierte_pax_a_int(self, mock_connector):
        _registrar_evento(mock_connector, {
            "fecha_evento":   "2026-07-20",
            "provincia":      "Tucuman",
            "localidad":      "San Miguel",
            "tipo_evento":    "corporativo",
            "pax":            "80",  # string — debe convertirse
            "duracion_horas": "4",
            "tipo_menu":      "estandar",
        })
        args = mock_connector.write.call_args
        assert isinstance(args[0][1]["pax"], int)
        assert args[0][1]["pax"] == 80


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 7: Cálculo de orden de compra
# ══════════════════════════════════════════════════════════════════════════

PRECIOS_MOCK = [
    {"producto_id": "GIN-001",    "precio_ars": 12000},
    {"producto_id": "WHISKY-001", "precio_ars":  7000},
]


class TestCalcularItemsOrden:

    @pytest.fixture
    def connector_con_precios(self, mock_connector):
        mock_connector.read.return_value = PRECIOS_MOCK
        return mock_connector

    def test_faltante_stock_no_modifica_cantidad(self, connector_con_precios):
        items = [{"item_id": "GIN-001", "cantidad": 5, "nombre": "Gin", "unidad": "botella"}]
        items_orden, total = _calcular_items_orden(
            connector_con_precios, "faltante_stock", items
        )
        assert items_orden[0]["cantidad"] == 5

    def test_alerta_climatica_incrementa_hielo_50pct(self, connector_con_precios):
        items = [{"item_id": "HIELO-001", "cantidad": 10, "nombre": "Hielo", "unidad": "bolsa"}]
        items_orden, _ = _calcular_items_orden(
            connector_con_precios, "alerta_climatica", items
        )
        import math
        assert items_orden[0]["cantidad"] == math.ceil(10 * 1.50)

    def test_alerta_climatica_incrementa_agua_30pct(self, connector_con_precios):
        items = [{"item_id": "AGUA-001", "cantidad": 20, "nombre": "Agua", "unidad": "botella"}]
        items_orden, _ = _calcular_items_orden(
            connector_con_precios, "alerta_climatica", items
        )
        import math
        assert items_orden[0]["cantidad"] == math.ceil(20 * 1.30)

    def test_total_es_suma_de_subtotales(self, connector_con_precios):
        items = [
            {"item_id": "GIN-001",   "cantidad": 3, "nombre": "Gin",   "unidad": "botella"},
            {"item_id": "HIELO-001", "cantidad": 5, "nombre": "Hielo", "unidad": "bolsa"},
        ]
        items_orden, total = _calcular_items_orden(
            connector_con_precios, "faltante_stock", items
        )
        esperado = sum(i["subtotal"] for i in items_orden)
        assert total == esperado


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 8: Selección de bartenders
# ══════════════════════════════════════════════════════════════════════════

BARTENDERS_MOCK = [
    {"bartender_id": "BAR-001", "nombre": "Juan",    "especialidad": "premium", "es_head_bartender": "TRUE",  "calificacion": 4.8, "disponible": True},
    {"bartender_id": "BAR-002", "nombre": "Maria",   "especialidad": "clasica", "es_head_bartender": "FALSE", "calificacion": 4.5, "disponible": True},
    {"bartender_id": "BAR-003", "nombre": "Carlos",  "especialidad": "premium", "es_head_bartender": "FALSE", "calificacion": 4.7, "disponible": True},
    {"bartender_id": "BAR-004", "nombre": "Ana",     "especialidad": "clasica", "es_head_bartender": "FALSE", "calificacion": 4.3, "disponible": True},
    {"bartender_id": "BAR-005", "nombre": "Roberto", "especialidad": "premium", "es_head_bartender": "FALSE", "calificacion": 4.9, "disponible": True},
]


class TestSeleccionarBartenders:

    @pytest.fixture
    def connector_con_bartenders(self, mock_connector):
        mock_connector.read.return_value = BARTENDERS_MOCK
        return mock_connector

    def test_40_pax_necesita_1_bartender(self, connector_con_bartenders):
        asignados, _ = _seleccionar_bartenders(connector_con_bartenders, 40, "estandar")
        assert len(asignados) == 1

    def test_41_pax_necesita_2_bartenders(self, connector_con_bartenders):
        asignados, _ = _seleccionar_bartenders(connector_con_bartenders, 41, "estandar")
        assert len(asignados) == 2

    def test_150_pax_necesita_4_bartenders(self, connector_con_bartenders):
        asignados, _ = _seleccionar_bartenders(connector_con_bartenders, 150, "premium")
        # 4 regulares + 1 head = 5 total, pero necesita_head se suma aparte
        assert len(asignados) >= 4

    def test_mas_de_100_pax_asigna_head(self, connector_con_bartenders):
        asignados, necesita_head = _seleccionar_bartenders(
            connector_con_bartenders, 101, "premium"
        )
        assert necesita_head is True
        roles = [b.get("rol") for b in asignados]
        assert "head" in roles

    def test_100_pax_no_necesita_head(self, connector_con_bartenders):
        asignados, necesita_head = _seleccionar_bartenders(
            connector_con_bartenders, 100, "estandar"
        )
        assert necesita_head is False

    def test_sin_bartenders_disponibles_lanza_error(self, mock_connector):
        mock_connector.read.return_value = []
        with pytest.raises(ValueError, match="No hay bartenders disponibles"):
            _seleccionar_bartenders(mock_connector, 50, "estandar")

    def test_genera_hoja_de_ruta(self):
        hoja = _generar_hoja_de_ruta(
            [{"nombre": "Juan", "rol": "head"}],
            "2026-07-20", 5, "Tucuman", "San Miguel"
        )
        assert "Juan" in hoja
        assert "2026-07-20" in hoja
        assert "Tucuman" in hoja


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 9: Auditoría — margen crítico
# ══════════════════════════════════════════════════════════════════════════

class TestAuditoria:

    def test_margen_critico_umbral_es_10(self):
        assert MARGEN_CRITICO_UMBRAL == 10.0

    def test_guarda_auditoria_en_db(self, mock_connector):
        _guardar_auditoria(
            mock_connector,
            evento_id      = "EVT-001",
            precio_cobrado = 5_376_757,
            costo_real     = 4_608_458,
            margen_pct     = 14.3,
            mermas         = 250_000,
            compras_emergencia = 220_000,
            desvio_climatico = "+7C",
        )
        mock_connector.write.assert_called_once()
        args = mock_connector.write.call_args[0]
        assert args[0] == "auditorias"
        assert args[1]["evento_id"] == "EVT-001"
        assert args[1]["precio_cobrado"] == 5_376_757

    def test_auditoria_id_formato(self, mock_connector):
        _guardar_auditoria(
            mock_connector, "EVT-001", 1000, 800, 20.0, 0, 0, ""
        )
        args = mock_connector.write.call_args[0]
        assert args[1]["auditoria_id"].startswith("AUD-")


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 11: Monitor de precios
# ══════════════════════════════════════════════════════════════════════════

class TestMonitorPrecios:

    @pytest.fixture
    def connector_precios(self, mock_connector):
        mock_connector.read.return_value = [
            {"producto_id": "GIN-001",    "precio_ars": 12000, "precio_base_referencia": 14000, "es_oferta": False},
            {"producto_id": "WHISKY-001", "precio_ars":  7000, "precio_base_referencia":  8000, "es_oferta": False},
        ]
        return mock_connector

    def test_actualiza_productos_en_mock(self, connector_precios):
        resultado = _actualizar_precios(connector_precios)
        # Solo actualiza los que están en el mock Y en precios_bebidas
        assert resultado["actualizados"] == 2

    def test_registra_historial_antes_de_actualizar(self, connector_precios):
        _actualizar_precios(connector_precios)
        tablas_escritas = [
            call[0][0] for call in connector_precios.write.call_args_list
        ]
        # Debe haber escrituras en historial_precios
        assert "historial_precios" in tablas_escritas

    def test_detecta_oferta_correctamente(self, mock_connector):
        # GIN-001: nuevo=9000, base=14000 → ahorro=35.7% > 15% → es_oferta
        mock_connector.read.return_value = [
            {"producto_id": "GIN-001", "precio_ars": 12000,
             "precio_base_referencia": 14000, "es_oferta": False},
        ]
        # Parchear el mock para que GIN tenga precio muy bajo
        import src.crews.bartenders.cierre_crews as m
        original = m.MOCK_PRECIOS_ACTUALIZADOS.copy()
        m.MOCK_PRECIOS_ACTUALIZADOS["GIN-001"] = {"precio_ars": 9000, "fuente": "Test"}

        resultado = _actualizar_precios(mock_connector)

        m.MOCK_PRECIOS_ACTUALIZADOS.update(original)
        assert resultado["ofertas"] >= 1
