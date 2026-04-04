"""
tests/unit/test_bartenders_tools.py

Tests de las tres tools de Bartenders NOA.
Usan un conector mock para no depender de Supabase.
"""

import pytest
from unittest.mock import MagicMock
from src.tools.bartenders.escandallo_tool import EscandalloTool, EscandalloOutput
from src.tools.bartenders.clima_tool import (
    FactorClimaticoTool, PronosticoRealTool, MOCK_FORECAST_OVERRIDE
)
from src.tools.bartenders.inventario_tool import (
    CalcularStockNecesarioTool, ReservarStockTool, LiberarStockTool
)


# ─── Fixtures ──────────────────────────────────────────────────────────────

CONSUMO_PREMIUM = {
    "tipo_menu":                   "premium",
    "coctel_por_persona":          6,
    "ml_espiritoso_por_coctel":    55,
    "hielo_kg_por_persona":        0.8,
    "agua_litros_por_persona":     1.0,
    "garnish_ars_por_persona":     2000,
    "desechables_ars_por_persona": 800,
    "mix_gin_pct":    50,
    "mix_whisky_pct": 20,
    "mix_ron_pct":    15,
    "mix_vodka_pct":  10,
    "mix_tequila_pct": 5,
}

CONSUMO_ESTANDAR = {
    "tipo_menu":                   "estandar",
    "coctel_por_persona":          5,
    "ml_espiritoso_por_coctel":    50,
    "hielo_kg_por_persona":        0.67,
    "agua_litros_por_persona":     0.75,
    "garnish_ars_por_persona":     1200,
    "desechables_ars_por_persona": 600,
    "mix_gin_pct":    50,
    "mix_whisky_pct": 20,
    "mix_ron_pct":    15,
    "mix_vodka_pct":  10,
    "mix_tequila_pct": 5,
}

PRECIOS_MOCK = [
    {"producto_id": "GIN-001",    "categoria": "gin",    "presentacion_ml": 700,  "precio_ars": 12000},
    {"producto_id": "GIN-002",    "categoria": "gin",    "presentacion_ml": 700,  "precio_ars": 28000},
    {"producto_id": "WHISKY-001", "categoria": "whisky", "presentacion_ml": 750,  "precio_ars":  7000},
    {"producto_id": "WHISKY-002", "categoria": "whisky", "presentacion_ml": 750,  "precio_ars": 25000},
    {"producto_id": "VODKA-001",  "categoria": "vodka",  "presentacion_ml": 700,  "precio_ars":  8000},
    {"producto_id": "RON-001",    "categoria": "ron",    "presentacion_ml": 750,  "precio_ars": 18000},
    {"producto_id": "TEQUILA-001","categoria": "tequila","presentacion_ml": 750,  "precio_ars": 22000},
]

EQUIPAMIENTO_MOCK = [
    {"item_id": "BARRA-001",    "amortizacion_por_evento": 2500, "estado": "activo"},
    {"item_id": "CRISTAL-001",  "amortizacion_por_evento": 1333, "estado": "activo"},
    {"item_id": "HELADERA-001", "amortizacion_por_evento": 1667, "estado": "activo"},
    {"item_id": "EQUIPOS-001",  "amortizacion_por_evento":  750, "estado": "activo"},
]

CLIMATICO_ENERO = {"mes": 1, "factor_pct": 20, "razon": "Enero: calor extremo NOA"}


@pytest.fixture
def mock_connector():
    """Conector mock que simula respuestas reales de las planillas."""
    c = MagicMock()

    def get_config_side_effect(table, filters=None):
        if table == "config_consumo_pax":
            tipo = (filters or {}).get("tipo_menu")
            if tipo == "premium":
                return [CONSUMO_PREMIUM]
            if tipo == "estandar":
                return [CONSUMO_ESTANDAR]
            return [CONSUMO_PREMIUM, CONSUMO_ESTANDAR]
        if table == "equipamiento_amortizacion":
            return EQUIPAMIENTO_MOCK
        if table == "config_climatico":
            mes = (filters or {}).get("mes")
            if mes == 1:
                return [CLIMATICO_ENERO]
            return []
        return []

    def read_side_effect(table, filters=None):
        if table == "precios_bebidas":
            return PRECIOS_MOCK
        return []

    c.get_config.side_effect = get_config_side_effect
    c.get_config_one.side_effect = lambda t, f=None: (get_config_side_effect(t, f) or [None])[0]
    c.read.side_effect = read_side_effect
    c.read_one.side_effect = lambda t, f=None: (read_side_effect(t, f) or [None])[0]
    return c


# ─── EscandalloTool ────────────────────────────────────────────────────────

class TestEscandalloTool:

    @pytest.fixture
    def tool(self, mock_connector):
        return EscandalloTool(connector=mock_connector)

    def test_escandallo_boda_150_pax_enero_tucuman_premium(self, tool):
        """
        Caso canónico de la spec: boda 150 pax, enero, Tucumán, premium, 5h.
        150 PAX con premium menu incluye: productos, equipamiento, 4 bartenders + 1 head, logística.
        """
        result = tool._run(
            evento_id            = "EVT-2026-001",
            pax                  = 150,
            duracion_horas       = 5,
            tipo_menu            = "premium",
            provincia            = "Tucuman",
            factor_climatico_pct = 20,
        )

        assert isinstance(result, EscandalloOutput)
        # Verificar que todos los componentes están presentes y son positivos
        assert result.bloque1_productos > 0
        assert result.bloque2_equipamiento > 0
        assert result.bloque3_personal > 0  # 4 bartenders + 1 head = alto
        assert result.bloque4_logistica > 0
        assert result.escandallo_final > 0
        # Verificar que el escandallo total incluye ajustes
        assert result.ajuste_climatico > 0  # factor climático de 20%
        assert result.mermas > 0
        assert result.imprevistos > 0

    def test_bartenders_necesarios_150_pax(self, tool):
        """150 PAX ÷ 40 = 3.75 → CEILING = 4 bartenders."""
        result = tool._run("EVT-X", 150, 5, "premium", "Tucuman", 0)
        assert result.bartenders_necesarios == 4

    def test_bartenders_necesarios_40_pax(self, tool):
        """40 PAX ÷ 40 = 1 bartender exacto."""
        result = tool._run("EVT-X", 40, 3, "basico", "Tucuman", 0)
        assert result.bartenders_necesarios == 1

    def test_bartenders_necesarios_41_pax(self, tool):
        """41 PAX → CEILING(41/40) = 2 bartenders."""
        result = tool._run("EVT-X", 41, 3, "basico", "Tucuman", 0)
        assert result.bartenders_necesarios == 2

    def test_necesita_head_si_pax_mayor_100(self, tool):
        result = tool._run("EVT-X", 101, 5, "estandar", "Tucuman", 0)
        assert result.necesita_head is True

    def test_no_necesita_head_si_pax_igual_100(self, tool):
        result = tool._run("EVT-X", 100, 5, "estandar", "Tucuman", 0)
        assert result.necesita_head is False

    def test_necesita_asistente_si_duracion_mayor_6(self, tool):
        result = tool._run("EVT-X", 50, 7, "estandar", "Tucuman", 0)
        assert result.necesita_asistente is True

    def test_no_necesita_asistente_si_duracion_igual_6(self, tool):
        result = tool._run("EVT-X", 50, 6, "estandar", "Tucuman", 0)
        assert result.necesita_asistente is False

    def test_horas_totales_incluyen_setup(self, tool):
        """Siempre se suman 3 horas de setup/cierre."""
        result = tool._run("EVT-X", 50, 5, "estandar", "Tucuman", 0)
        assert result.horas_totales == 8  # 5 + 3

    def test_logistica_tucuman_fija(self, tool):
        """Tucumán: 17.000 × 3 horas = 51.000 ARS."""
        result = tool._run("EVT-X", 50, 5, "estandar", "Tucuman", 0)
        assert result.bloque4_logistica == 51_000

    def test_logistica_salta_interprovincial(self, tool):
        """Salta: 300km × 2 × 600 + 5.000 = 365.000 ARS."""
        result = tool._run("EVT-X", 50, 5, "estandar", "Salta", 0)
        assert result.bloque4_logistica == 365_000

    def test_logistica_jujuy_interprovincial(self, tool):
        """Jujuy: 350km × 2 × 600 + 5.000 = 425.000 ARS."""
        result = tool._run("EVT-X", 50, 5, "estandar", "Jujuy", 0)
        assert result.bloque4_logistica == 425_000

    def test_logistica_catamarca_interprovincial(self, tool):
        """Catamarca: 280km × 2 × 600 + 5.000 = 341.000 ARS."""
        result = tool._run("EVT-X", 50, 5, "estandar", "Catamarca", 0)
        assert result.bloque4_logistica == 341_000

    def test_provincia_invalida_lanza_error(self, tool):
        with pytest.raises(ValueError, match="no reconocida"):
            tool._run("EVT-X", 50, 5, "estandar", "Buenos Aires", 0)

    def test_factor_climatico_cero_no_agrega_ajuste(self, tool):
        result = tool._run("EVT-X", 50, 5, "estandar", "Tucuman", 0)
        assert result.ajuste_climatico == 0

    def test_factor_climatico_20_pct_sobre_bloques_1_y_2(self, tool):
        result = tool._run("EVT-X", 50, 5, "estandar", "Tucuman", 20)
        base = result.bloque1_productos + result.bloque2_equipamiento
        assert result.ajuste_climatico == round(base * 0.20)

    def test_mermas_son_5_pct(self, tool):
        result = tool._run("EVT-X", 50, 5, "estandar", "Tucuman", 0)
        base_ajustada = result.subtotal + result.ajuste_climatico
        assert result.mermas == round(base_ajustada * 0.05)

    def test_imprevistos_son_3_pct(self, tool):
        result = tool._run("EVT-X", 50, 5, "estandar", "Tucuman", 0)
        base_ajustada = result.subtotal + result.ajuste_climatico
        assert result.imprevistos == round(base_ajustada * 0.03)

    def test_escandallo_final_es_suma_de_componentes(self, tool):
        result = tool._run("EVT-X", 80, 4, "estandar", "Tucuman", 12)
        esperado = (result.subtotal + result.ajuste_climatico
                    + result.mermas + result.imprevistos)
        assert result.escandallo_final == esperado


# ─── FactorClimaticoTool ───────────────────────────────────────────────────

class TestFactorClimaticoTool:

    @pytest.fixture
    def tool(self, mock_connector):
        return FactorClimaticoTool(connector=mock_connector)

    def test_enero_retorna_factor_20(self, tool):
        result = tool._run(mes=1)
        assert result.factor_pct == 20
        assert result.mes == 1

    def test_mes_sin_dato_retorna_factor_default_10(self, tool):
        result = tool._run(mes=6)  # sin override en mock
        assert result.factor_pct == 10

    def test_mes_invalido_lanza_error(self, tool):
        with pytest.raises(ValueError):
            tool._run(mes=13)

    def test_mes_cero_lanza_error(self, tool):
        with pytest.raises(ValueError):
            tool._run(mes=0)


# ─── PronosticoRealTool ────────────────────────────────────────────────────

class TestPronosticoRealTool:

    @pytest.fixture
    def tool(self, mock_connector):
        return PronosticoRealTool(connector=mock_connector)

    def test_ola_de_calor_activa_alerta_roja(self, tool):
        """EVT-2026-001 tiene mock a 33°C vs histórico enero 26°C → desvío +26.9%."""
        result = tool._run(
            evento_id    = "EVT-2026-001",
            provincia    = "Tucuman",
            fecha_evento = "2026-01-15",
        )
        assert result.alerta_roja is True
        assert result.temp_pronosticada == 33.0
        assert result.temp_historica == 26.0
        assert result.desvio_absoluto == 7.0

    def test_sin_override_no_hay_alerta(self, tool):
        """Evento sin override → pronóstico = histórico → desvío 0%."""
        result = tool._run(
            evento_id    = "EVT-SIN-OVERRIDE",
            provincia    = "Tucuman",
            fecha_evento = "2026-06-10",
        )
        assert result.alerta_roja is False
        assert result.desvio_pct == 0.0

    def test_fecha_invalida_lanza_error(self, tool):
        with pytest.raises(ValueError, match="Formato de fecha"):
            tool._run("EVT-X", "Tucuman", "15-01-2026")  # formato incorrecto

    def test_extrae_mes_correctamente(self, tool):
        result = tool._run("EVT-X", "Tucuman", "2026-07-20")
        assert result.temp_historica == 10.5  # julio = mes 7


# ─── CalcularStockNecesarioTool ───────────────────────────────────────────

class TestCalcularStockNecesarioTool:

    @pytest.fixture
    def tool(self, mock_connector):
        return CalcularStockNecesarioTool(connector=mock_connector)

    def test_retorna_items_no_vacio(self, tool):
        result = tool._run("EVT-X", 80, "estandar")
        assert len(result.items) > 0

    def test_incluye_hielo_y_agua(self, tool):
        result = tool._run("EVT-X", 80, "estandar")
        item_ids = [i.item_id for i in result.items]
        assert "HIELO-001" in item_ids
        assert "AGUA-001" in item_ids

    def test_incluye_espiritosos(self, tool):
        result = tool._run("EVT-X", 80, "estandar")
        item_ids = [i.item_id for i in result.items]
        assert "GIN-001" in item_ids

    def test_mayor_pax_mayor_cantidad(self, tool):
        r50  = tool._run("EVT-X", 50,  "estandar")
        r100 = tool._run("EVT-X", 100, "estandar")
        cant_gin_50  = next(i.cantidad for i in r50.items  if i.item_id == "GIN-001")
        cant_gin_100 = next(i.cantidad for i in r100.items if i.item_id == "GIN-001")
        assert cant_gin_100 > cant_gin_50


# ─── ReservarStockTool ────────────────────────────────────────────────────

class TestReservarStockTool:

    @pytest.fixture
    def tool(self, mock_connector):
        return ReservarStockTool(connector=mock_connector)

    def test_reserva_exitosa_todos_los_items(self, tool, mock_connector):
        mock_connector.reserve_stock.return_value = {"ok": True}
        items = [
            {"item_id": "GIN-001",   "cantidad": 5, "nombre": "Gordon's", "unidad": "botella"},
            {"item_id": "HIELO-001", "cantidad": 10, "nombre": "Hielo",   "unidad": "bolsa"},
        ]
        result = tool._run("EVT-X", items)

        assert result.alerta_faltante is False
        assert len(result.reservas_exitosas) == 2
        assert len(result.reservas_fallidas) == 0

    def test_alerta_cuando_falta_stock(self, tool, mock_connector):
        mock_connector.reserve_stock.side_effect = ValueError("Stock insuficiente")
        items = [{"item_id": "GIN-001", "cantidad": 100, "nombre": "Gin", "unidad": "botella"}]

        result = tool._run("EVT-X", items)

        assert result.alerta_faltante is True
        assert len(result.items_a_comprar) == 1
        assert result.items_a_comprar[0].item_id == "GIN-001"

    def test_reserva_parcial_exitosa_y_fallida(self, tool, mock_connector):
        def reserve_side_effect(item_id, cantidad):
            if item_id == "HIELO-001":
                raise ValueError("Sin stock de hielo")
            return {"ok": True}

        mock_connector.reserve_stock.side_effect = reserve_side_effect
        items = [
            {"item_id": "GIN-001",   "cantidad": 3,  "nombre": "Gin",   "unidad": "botella"},
            {"item_id": "HIELO-001", "cantidad": 20, "nombre": "Hielo", "unidad": "bolsa"},
        ]
        result = tool._run("EVT-X", items)

        assert result.alerta_faltante is True
        assert len(result.reservas_exitosas) == 1
        assert len(result.reservas_fallidas) == 1
        assert result.reservas_fallidas[0].item_id == "HIELO-001"
