"""
src/tools/bartenders/inventario_tool.py

Tools para gestionar el stock físico del evento.

Tres tools separadas con responsabilidades claras:

1. CalcularStockNecesarioTool:
   Dado un evento (PAX, tipo_menu), calcula cuántas unidades
   de cada producto se necesitan. No toca el inventario.

2. ReservarStockTool:
   Reserva los items calculados. Llama a la RPC atómica del conector.
   Si falta algún item, retorna alerta para que el Agente 7 compre.

3. LiberarStockTool:
   Libera reservas cuando un evento se cancela.
"""

from typing import Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from src.connectors.base_connector import BaseDataConnector
import math


# ─── Modelos ───────────────────────────────────────────────────────────────

class ItemNecesario(BaseModel):
    item_id:    str
    nombre:     str
    cantidad:   int
    unidad:     str


class StockNecesarioOutput(BaseModel):
    evento_id:   str
    pax:         int
    tipo_menu:   str
    items:       list[ItemNecesario]


class ReservaResultado(BaseModel):
    item_id:    str
    cantidad:   int
    ok:         bool
    mensaje:    str


class ReservarStockOutput(BaseModel):
    evento_id:            str
    reservas_exitosas:    list[ReservaResultado]
    reservas_fallidas:    list[ReservaResultado]
    alerta_faltante:      bool = Field(
        ...,
        description="True si hay items sin stock — Agente 7 debe comprar"
    )
    items_a_comprar:      list[ItemNecesario] = Field(
        default_factory=list,
        description="Items que faltan y deben comprarse"
    )


class LiberarStockOutput(BaseModel):
    evento_id:  str
    liberados:  list[ReservaResultado]


# ─── Factores de conversión para calcular stock ────────────────────────────
# Cuántas botellas se necesitan por litro de espirituoso consumido

ML_POR_BOTELLA: dict[str, int] = {
    "gin":     700,
    "whisky":  750,
    "ron":     750,
    "vodka":   700,
    "tequila": 750,
}

# item_id en inventario para cada categoría de bebida
ITEM_ID_POR_CATEGORIA: dict[str, str] = {
    "gin":     "GIN-001",
    "whisky":  "WHISKY-001",
    "ron":     "RON-001",
    "vodka":   "VODKA-001",
    "tequila": "TEQUILA-001",
}

# Hielo: bolsas de 2kg
ML_POR_BOLSA_HIELO = 2000  # 2 kg = 2000g ≈ 2L volumen

# Agua: botellas de 1.5L
LITROS_POR_BOTELLA_AGUA = 1.5

# Buffer de seguridad: reservar 10% extra
BUFFER_SEGURIDAD = 1.10


# ─── Tool 1: Calcular Stock Necesario ─────────────────────────────────────

class CalcularStockNecesarioTool(BaseTool):
    name: str = "calcular_stock_necesario"
    description: str = (
        "Calcula la cantidad exacta de cada producto necesaria para un evento, "
        "según PAX y tipo de menú. No modifica el inventario. "
        "Incluye un buffer de seguridad del 10%."
    )

    connector: Any  # BaseDataConnector

    def _run(
        self,
        evento_id:  str,
        pax:        int,
        tipo_menu:  str,
    ) -> StockNecesarioOutput:

        consumo = self.connector.get_config_one(
            "config_consumo_pax", {"tipo_menu": tipo_menu}
        )
        if not consumo:
            raise ValueError(f"tipo_menu '{tipo_menu}' no encontrado")

        items: list[ItemNecesario] = []

        # ── Espirituosos ────────────────────────────────────────────────
        cocteles_totales = pax * int(consumo["coctel_por_persona"])
        ml_total = cocteles_totales * int(consumo["ml_espiritoso_por_coctel"])

        mix = {
            "gin":     int(consumo["mix_gin_pct"])    / 100,
            "whisky":  int(consumo["mix_whisky_pct"]) / 100,
            "ron":     int(consumo["mix_ron_pct"])    / 100,
            "vodka":   int(consumo["mix_vodka_pct"])  / 100,
            "tequila": int(consumo["mix_tequila_pct"])/ 100,
        }

        for categoria, proporcion in mix.items():
            if proporcion == 0:
                continue
            ml_categoria = ml_total * proporcion
            ml_por_bot   = ML_POR_BOTELLA.get(categoria, 750)
            botellas     = math.ceil(ml_categoria / ml_por_bot * BUFFER_SEGURIDAD)
            item_id      = ITEM_ID_POR_CATEGORIA.get(categoria, categoria.upper() + "-001")

            items.append(ItemNecesario(
                item_id  = item_id,
                nombre   = f"{categoria.capitalize()} (botellas)",
                cantidad = botellas,
                unidad   = "botella",
            ))

        # ── Hielo ────────────────────────────────────────────────────────
        kg_hielo_total  = pax * float(consumo["hielo_kg_por_persona"])
        bolsas_hielo    = math.ceil(kg_hielo_total / 2 * BUFFER_SEGURIDAD)  # bolsas 2kg
        items.append(ItemNecesario(
            item_id  = "HIELO-001",
            nombre   = "Hielo 2kg",
            cantidad = bolsas_hielo,
            unidad   = "bolsa",
        ))

        # ── Agua ─────────────────────────────────────────────────────────
        litros_agua  = pax * float(consumo["agua_litros_por_persona"])
        botellas_agua = math.ceil(litros_agua / LITROS_POR_BOTELLA_AGUA * BUFFER_SEGURIDAD)
        items.append(ItemNecesario(
            item_id  = "AGUA-001",
            nombre   = "Agua mineral 1.5L",
            cantidad = botellas_agua,
            unidad   = "botella",
        ))

        return StockNecesarioOutput(
            evento_id = evento_id,
            pax       = pax,
            tipo_menu = tipo_menu,
            items     = items,
        )


# ─── Tool 2: Reservar Stock ───────────────────────────────────────────────

class ReservarStockTool(BaseTool):
    name: str = "reservar_stock_evento"
    description: str = (
        "Reserva el stock físico necesario para un evento. "
        "Si algún item no tiene suficiente stock, lo marca en items_a_comprar "
        "y activa alerta_faltante=True para que el Agente 7 genere una orden de compra. "
        "Nunca falla silenciosamente: siempre informa qué pudo reservar y qué no."
    )

    connector: Any  # BaseDataConnector

    def _run(
        self,
        evento_id: str,
        items:     list[dict],   # lista de {item_id, cantidad, nombre, unidad}
    ) -> ReservarStockOutput:

        exitosas:  list[ReservaResultado] = []
        fallidas:  list[ReservaResultado] = []
        a_comprar: list[ItemNecesario]    = []

        for item in items:
            item_id  = item["item_id"]
            cantidad = item["cantidad"]

            try:
                self.connector.reserve_stock(item_id, cantidad)
                exitosas.append(ReservaResultado(
                    item_id  = item_id,
                    cantidad = cantidad,
                    ok       = True,
                    mensaje  = f"Reservadas {cantidad} unidades de {item_id}",
                ))
            except ValueError as e:
                fallidas.append(ReservaResultado(
                    item_id  = item_id,
                    cantidad = cantidad,
                    ok       = False,
                    mensaje  = str(e),
                ))
                a_comprar.append(ItemNecesario(
                    item_id  = item_id,
                    nombre   = item.get("nombre", item_id),
                    cantidad = cantidad,
                    unidad   = item.get("unidad", "unidad"),
                ))

        return ReservarStockOutput(
            evento_id         = evento_id,
            reservas_exitosas = exitosas,
            reservas_fallidas = fallidas,
            alerta_faltante   = len(fallidas) > 0,
            items_a_comprar   = a_comprar,
        )


# ─── Tool 3: Liberar Stock ────────────────────────────────────────────────

class LiberarStockTool(BaseTool):
    name: str = "liberar_stock_evento"
    description: str = (
        "Libera el stock reservado para un evento cancelado. "
        "Debe llamarse siempre que un evento cambie a status 'cancelado'. "
        "Retorna la lista de items liberados."
    )

    connector: Any  # BaseDataConnector

    def _run(
        self,
        evento_id: str,
        items:     list[dict],  # misma estructura que ReservarStockTool
    ) -> LiberarStockOutput:

        liberados: list[ReservaResultado] = []

        for item in items:
            item_id  = item["item_id"]
            cantidad = item["cantidad"]

            try:
                self.connector.release_stock(item_id, cantidad)
                liberados.append(ReservaResultado(
                    item_id  = item_id,
                    cantidad = cantidad,
                    ok       = True,
                    mensaje  = f"Liberadas {cantidad} unidades de {item_id}",
                ))
            except Exception as e:
                liberados.append(ReservaResultado(
                    item_id  = item_id,
                    cantidad = cantidad,
                    ok       = False,
                    mensaje  = f"Error al liberar: {e}",
                ))

        return LiberarStockOutput(
            evento_id = evento_id,
            liberados = liberados,
        )
