"""
src/tools/bartenders/escandallo_tool.py

Cálculo del escandallo de costos en 4 bloques.
Es la tool más crítica del sistema: determina el precio base de todo evento.

IMPORTANTE: Esta tool es 100% determinista.
Mismos inputs → mismo output siempre. No hay LLM en el cálculo.
El agente la llama con los parámetros del evento y recibe el desglose completo.

Fórmula completa:
    Escandallo = (B1 + B2 + B3 + B4)
               + AjusteClimático (sobre B1+B2)
               + Mermas 5%
               + Imprevistos 3%

Distancias NOA (km ida):
    Tucumán → Salta:     300 km
    Tucumán → Jujuy:     350 km
    Tucumán → Catamarca: 280 km
    Tucumán (local):       0 km
"""

import math
from typing import Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from src.connectors.base_connector import BaseDataConnector


# ─── Modelos de input/output ───────────────────────────────────────────────

class EscandalloInput(BaseModel):
    evento_id:            str   = Field(..., description="ID del evento")
    pax:                  int   = Field(..., ge=10, le=500, description="Cantidad de personas")
    duracion_horas:       int   = Field(..., ge=1, le=24, description="Duración del evento en horas")
    tipo_menu:            str   = Field(..., description="basico | estandar | premium")
    provincia:            str   = Field(..., description="Tucuman | Salta | Jujuy | Catamarca")
    factor_climatico_pct: int   = Field(..., ge=0, description="Factor climático del Agente 2 (%)")


class EscandalloOutput(BaseModel):
    evento_id:              str
    # Bloques
    bloque1_productos:      int = Field(..., description="Bebidas + hielo + garnish + desechables")
    bloque2_equipamiento:   int = Field(..., description="Amortización de equipamiento")
    bloque3_personal:       int = Field(..., description="Bartenders + head + asistente × horas")
    bloque4_logistica:      int = Field(..., description="Flete y logística según provincia")
    subtotal:               int
    # Ajustes
    ajuste_climatico:       int = Field(..., description="Factor climático sobre B1+B2")
    mermas:                 int = Field(..., description="5% sobre subtotal ajustado")
    imprevistos:            int = Field(..., description="3% sobre subtotal ajustado")
    escandallo_final:       int = Field(..., description="Costo base total del evento")
    # Detalle de personal
    bartenders_necesarios:  int
    necesita_head:          bool
    necesita_asistente:     bool
    horas_totales:          int  = Field(..., description="Duración + 3h setup/cierre")
    factor_climatico_aplicado: int


# ─── Constantes ────────────────────────────────────────────────────────────

RATIO_PAX_POR_BARTENDER = 40          # 1 bartender cada 40 PAX
TARIFA_BARTENDER_REGULAR = 35_000     # ARS/hora
TARIFA_HEAD_BARTENDER    = 50_000     # ARS/hora
TARIFA_ASISTENTE         = 28_000     # ARS/hora
HORAS_SETUP_CIERRE       = 3          # horas fijas de preparación y desmontaje
PAX_MINIMO_HEAD          = 100        # PAX a partir del cual se requiere head
HORAS_MINIMO_ASISTENTE   = 6          # duración a partir de la cual se requiere asistente

COSTO_LOGISTICA_TUCUMAN_POR_HORA = 17_000
HORAS_MINIMO_LOGISTICA_LOCAL     = 3
COSTO_KM_INTERPROVINCIAL         = 600    # ARS por km
COSTO_PEAJES                     = 5_000  # ARS fijo para viajes interprovinciales

DISTANCIAS_KM: dict[str, int] = {
    "Tucuman":   0,
    "Salta":     300,
    "Jujuy":     350,
    "Catamarca": 280,
}

PCT_MERMAS      = 0.05
PCT_IMPREVISTOS = 0.03

PRECIO_HIELO_POR_KG  = 750   # ARS
PRECIO_AGUA_POR_LITRO = 400  # ARS


# ─── Tool ──────────────────────────────────────────────────────────────────

class EscandalloTool(BaseTool):
    name: str = "calcular_escandallo"
    description: str = (
        "Calcula el escandallo de costos completo para un evento en 4 bloques: "
        "productos, equipamiento, personal y logística. "
        "Aplica factor climático, mermas (5%) e imprevistos (3%). "
        "Retorna el costo base (escandallo_final) que el Agente 4 usará para cotizar."
    )

    connector: Any  # BaseDataConnector — Any para compatibilidad con Pydantic de CrewAI

    def _run(
        self,
        evento_id:            str,
        pax:                  int,
        duracion_horas:       int,
        tipo_menu:            str,
        provincia:            str,
        factor_climatico_pct: int,
    ) -> EscandalloOutput:

        # ── Leer configuraciones ─────────────────────────────────────────
        consumo = self._get_consumo(tipo_menu)
        precios = self._get_precios_indexados()
        equipamiento = self.connector.get_config("equipamiento_amortizacion")

        # ── BLOQUE 1: Productos ──────────────────────────────────────────
        bloque1 = self._calcular_bloque_productos(pax, consumo, precios)

        # ── BLOQUE 2: Equipamiento ───────────────────────────────────────
        bloque2 = self._calcular_bloque_equipamiento(equipamiento)

        # ── BLOQUE 3: Personal ───────────────────────────────────────────
        bloque3, n_bartenders, necesita_head, necesita_asistente, horas_totales = \
            self._calcular_bloque_personal(pax, duracion_horas)

        # ── BLOQUE 4: Logística ──────────────────────────────────────────
        bloque4 = self._calcular_bloque_logistica(provincia)

        # ── Ajustes finales ──────────────────────────────────────────────
        subtotal        = bloque1 + bloque2 + bloque3 + bloque4
        base_climatica  = bloque1 + bloque2  # el ajuste solo aplica sobre B1+B2
        ajuste_climatico = round(base_climatica * factor_climatico_pct / 100)
        base_ajustada   = subtotal + ajuste_climatico
        mermas          = round(base_ajustada * PCT_MERMAS)
        imprevistos     = round(base_ajustada * PCT_IMPREVISTOS)
        escandallo_final = base_ajustada + mermas + imprevistos

        return EscandalloOutput(
            evento_id              = evento_id,
            bloque1_productos      = bloque1,
            bloque2_equipamiento   = bloque2,
            bloque3_personal       = bloque3,
            bloque4_logistica      = bloque4,
            subtotal               = subtotal,
            ajuste_climatico       = ajuste_climatico,
            mermas                 = mermas,
            imprevistos            = imprevistos,
            escandallo_final       = escandallo_final,
            bartenders_necesarios  = n_bartenders,
            necesita_head          = necesita_head,
            necesita_asistente     = necesita_asistente,
            horas_totales          = horas_totales,
            factor_climatico_aplicado = factor_climatico_pct,
        )

    # ─── Bloque 1: Productos ────────────────────────────────────────────

    def _calcular_bloque_productos(
        self,
        pax:     int,
        consumo: dict,
        precios: dict[str, list[dict]],
    ) -> int:
        cocteles_totales = pax * int(consumo["coctel_por_persona"])
        ml_total         = cocteles_totales * int(consumo["ml_espiritoso_por_coctel"])

        mix = {
            "gin":     int(consumo["mix_gin_pct"])    / 100,
            "whisky":  int(consumo["mix_whisky_pct"]) / 100,
            "ron":     int(consumo["mix_ron_pct"])    / 100,
            "vodka":   int(consumo["mix_vodka_pct"])  / 100,
            "tequila": int(consumo["mix_tequila_pct"])/ 100,
        }

        # Precio promedio ponderado por categoría (ARS por ml)
        precio_por_ml: dict[str, float] = {}
        for cat in mix:
            productos_cat = precios.get(cat, [])
            if productos_cat:
                precio_por_ml[cat] = sum(
                    int(p["precio_ars"]) / int(p["presentacion_ml"])
                    for p in productos_cat
                ) / len(productos_cat)
            else:
                precio_por_ml[cat] = 0.0

        bebidas_alc = sum(
            ml_total * mix[cat] * precio_por_ml[cat]
            for cat in mix
        )

        bebidas_no_alc = (
            pax
            * float(consumo["agua_litros_por_persona"])
            * PRECIO_AGUA_POR_LITRO
        )

        hielo = (
            pax
            * float(consumo["hielo_kg_por_persona"])
            * PRECIO_HIELO_POR_KG
        )

        garnish     = pax * int(consumo["garnish_ars_por_persona"])
        desechables = pax * int(consumo["desechables_ars_por_persona"])

        return round(bebidas_alc + bebidas_no_alc + hielo + garnish + desechables)

    # ─── Bloque 2: Equipamiento ─────────────────────────────────────────

    def _calcular_bloque_equipamiento(self, equipamiento: list[dict]) -> int:
        return round(sum(
            float(e["amortizacion_por_evento"])
            for e in equipamiento
            if e.get("estado") == "activo"
        ))

    # ─── Bloque 3: Personal ─────────────────────────────────────────────

    def _calcular_bloque_personal(
        self,
        pax:            int,
        duracion_horas: int,
    ) -> tuple[int, int, bool, bool, int]:
        n_bartenders       = math.ceil(pax / RATIO_PAX_POR_BARTENDER)
        necesita_head      = pax > PAX_MINIMO_HEAD
        necesita_asistente = duracion_horas > HORAS_MINIMO_ASISTENTE
        horas_totales      = duracion_horas + HORAS_SETUP_CIERRE

        costo = n_bartenders * TARIFA_BARTENDER_REGULAR * horas_totales
        if necesita_head:
            costo += TARIFA_HEAD_BARTENDER * horas_totales
        if necesita_asistente:
            costo += TARIFA_ASISTENTE * horas_totales

        return round(costo), n_bartenders, necesita_head, necesita_asistente, horas_totales

    # ─── Bloque 4: Logística ────────────────────────────────────────────

    def _calcular_bloque_logistica(self, provincia: str) -> int:
        km = DISTANCIAS_KM.get(provincia)
        if km is None:
            raise ValueError(
                f"Provincia '{provincia}' no reconocida. "
                f"Válidas: {list(DISTANCIAS_KM.keys())}"
            )

        if km == 0:
            # Tucumán: cobro mínimo por horas de flete local
            return COSTO_LOGISTICA_TUCUMAN_POR_HORA * HORAS_MINIMO_LOGISTICA_LOCAL
        else:
            # Interprovincial: km ida+vuelta × tarifa + peajes fijos
            return (km * 2 * COSTO_KM_INTERPROVINCIAL) + COSTO_PEAJES

    # ─── Helpers ────────────────────────────────────────────────────────

    def _get_consumo(self, tipo_menu: str) -> dict:
        consumo = self.connector.get_config_one(
            "config_consumo_pax",
            {"tipo_menu": tipo_menu}
        )
        if not consumo:
            raise ValueError(
                f"tipo_menu '{tipo_menu}' no encontrado en config_consumo_pax. "
                f"Válidos: basico | estandar | premium"
            )
        return consumo

    def _get_precios_indexados(self) -> dict[str, list[dict]]:
        """Retorna precios agrupados por categoría para calcular promedio ponderado."""
        todos = self.connector.read("precios_bebidas")
        indexado: dict[str, list[dict]] = {}
        for p in todos:
            cat = p["categoria"]
            indexado.setdefault(cat, []).append(p)
        return indexado
