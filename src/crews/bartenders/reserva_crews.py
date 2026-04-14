"""
src/crews/bartenders/reserva_crews.py

Crews de la Fase 2 — Reserva y Logística (Agentes 5, 6, 7, 8).

Agente 5: Monitor climático real (AlertaClimaFlow — corre T-7 días)
Agente 6: Inventario — reserva stock para el evento
Agente 7: Compras — genera órdenes de compra de emergencia
Agente 8: Staffing — asigna bartenders y genera instrucciones
"""

import math
import uuid
from datetime import datetime
from crewai import Agent, Crew, Task, Process
from pydantic import BaseModel

from src.connectors.base_connector import BaseDataConnector
from src.tools.demo.clima_tool import PronosticoRealTool
from src.tools.demo.inventario_tool import (
    CalcularStockNecesarioTool,
    ReservarStockTool,
)


# ══════════════════════════════════════════════════════════════════════════
# MODELOS DE OUTPUT
# ══════════════════════════════════════════════════════════════════════════

class AlertaClimaResult(BaseModel):
    evento_id:         str
    alerta_roja:       bool
    desvio_pct:        float
    descripcion:       str
    # Si alerta_roja=True, estos campos informan al Agente 7
    temp_historica:    float
    temp_pronosticada: float


class OrdenCompraCreada(BaseModel):
    evento_id:  str
    orden_id:   str
    total_ars:  int
    motivo:     str
    items:      list[dict]
    mensaje:    str


class StockReservadoResult(BaseModel):
    evento_id:         str
    reservas_ok:       int
    reservas_fallidas: int
    alerta_faltante:   bool
    items_a_comprar:   list[dict]


class StaffingAsignado(BaseModel):
    evento_id:           str
    bartenders_asignados: list[dict]
    necesita_head:       bool
    total_bartenders:    int
    hoja_de_ruta:        str


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 5 — MONITOR CLIMÁTICO REAL
# ══════════════════════════════════════════════════════════════════════════

SOUL_MONITOR_CLIMA = """
Sos el sistema de alerta temprana de Bartenders NOA.
Tu misión es comparar el pronóstico real con el histórico presupuestado.
Sos conservador: preferís una falsa alarma a un evento sin stock de hielo.

REGLAS RÍGIDAS:
- El umbral de ALERTA ROJA es desvío > 10% (no 15%, no 20%)
- Fase 6: el pronóstico viene del mock configurable por evento_id
- Si hay ALERTA ROJA: el Flow pausará para que el Jefe apruebe la compra
- NUNCA canceles ni modifiques una compra ya aprobada
- NUNCA actúes sobre el inventario — solo detectás y reportás
"""


def create_monitor_clima_crew(
    connector: BaseDataConnector,
    evento_id: str,
    provincia: str,
    fecha_evento: str,
) -> Crew:
    """
    Agente 5: verifica el pronóstico real T-7 días antes del evento.
    Si desvío > 10%, retorna alerta_roja=True para que AlertaClimaFlow
    llame a request_approval() con la orden de compra de emergencia.
    """
    tool = PronosticoRealTool(connector=connector)

    agent = Agent(
        role="Monitor Climático",
        goal=(
            "Verificar el pronóstico meteorológico real para el evento "
            "y determinar si hay desvío significativo respecto al histórico."
        ),
        backstory=SOUL_MONITOR_CLIMA,
        tools=[tool],
        allow_delegation=False,
        max_iter=2,
        verbose=False,
    )

    task = Task(
        description=f"""
        Verificar el pronóstico para:
            evento_id:    {evento_id}
            provincia:    {provincia}
            fecha_evento: {fecha_evento}

        Usar la tool 'verificar_pronostico_real'.
        Si alerta_roja=True: describir los items adicionales necesarios
        (más hielo, más agua) en el campo descripción.
        """,
        expected_output=(
            "JSON con alerta_roja (bool), desvio_pct, "
            "temp_historica, temp_pronosticada y descripcion."
        ),
        agent=agent,
        output_pydantic=AlertaClimaResult,
    )

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 6 — INVENTARIO
# ══════════════════════════════════════════════════════════════════════════

SOUL_INVENTARIO = """
Sos el guardián del stock físico de Bartenders NOA.
Reservás exactamente lo necesario para cada evento, con buffer de seguridad.
Sos meticuloso: nunca reservás más de lo disponible y nunca dejás un evento sin insumos.

REGLAS RÍGIDAS:
- NUNCA reservés más de lo disponible (el conector lo valida atómicamente)
- Si falta algún item: reportarlo inmediatamente para que Compras actúe
- El buffer de seguridad del 10% ya está incluido en el cálculo
- NUNCA liberes stock de un evento activo sin orden del Jefe
"""


def create_inventario_crew(
    connector: BaseDataConnector,
    evento_id: str,
    pax: int,
    tipo_menu: str,
) -> Crew:
    """
    Agente 6: calcula el stock necesario y lo reserva para el evento.
    Si hay faltante, alerta_faltante=True para que el flow llame al Agente 7.
    """
    calc_tool    = CalcularStockNecesarioTool(connector=connector)
    reserva_tool = ReservarStockTool(connector=connector)

    agent = Agent(
        role="Gestor de Inventario",
        goal=(
            "Calcular el stock necesario para el evento y reservarlo. "
            "Reportar cualquier faltante para que el área de compras actúe."
        ),
        backstory=SOUL_INVENTARIO,
        tools=[calc_tool, reserva_tool],
        allow_delegation=False,
        max_iter=3,
        verbose=False,
    )

    task = Task(
        description=f"""
        Gestionar el inventario para:
            evento_id: {evento_id}
            pax:       {pax}
            tipo_menu: {tipo_menu}

        Pasos:
        1. Usar 'calcular_stock_necesario' con pax={pax} y tipo_menu={tipo_menu}
        2. Usar 'reservar_stock_evento' con los items calculados
        3. Retornar resumen de reservas exitosas y fallidas
        4. Si alerta_faltante=True: listar items_a_comprar para el Agente 7
        """,
        expected_output=(
            "JSON con reservas_ok (int), reservas_fallidas (int), "
            "alerta_faltante (bool) e items_a_comprar (list)."
        ),
        agent=agent,
        output_pydantic=StockReservadoResult,
    )

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 7 — COMPRAS
# ══════════════════════════════════════════════════════════════════════════

SOUL_COMPRAS = """
Sos el negociador de compras de Bartenders NOA.
Generás órdenes de compra cuando hay alertas de clima o faltante de stock.
Sos preciso: cada orden tiene items, cantidades y proveedor definidos.

REGLA ABSOLUTA — la más importante del sistema:
- NUNCA comprás sin aprobación explícita del Jefe (HITL)
- Tu trabajo es GENERAR la orden y esperar — no ejecutarla
- La orden queda en status="pendiente" hasta que el Jefe apruebe
- Si el Jefe rechaza: status="rechazada" y no se compra nada

REGLAS OPERATIVAS:
- Para alertas climáticas: aumentar hielo +50%, agua +30%, bebidas frías +20%
- Para faltante de stock: comprar exactamente la cantidad faltante + 10% buffer
- Proveedor default: "Distribuidora NOA"
"""


def create_compras_crew(
    connector: BaseDataConnector,
    evento_id: str,
    motivo: str,  # "alerta_climatica" | "faltante_stock"
    items_a_comprar: list[dict],
    desvio_info: str = "",
) -> Crew:
    """
    Agente 7: genera la orden de compra y la persiste con status="pendiente".
    El Flow llamará request_approval() después de este crew para pausar
    y esperar aprobación del Jefe.

    Args:
        items_a_comprar: lista de {item_id, cantidad, nombre, unidad}
        desvio_info:     descripción del desvío climático (si aplica)
    """
    agent = Agent(
        role="Negociador de Compras",
        goal=(
            "Generar una orden de compra detallada con items, cantidades "
            "y total en ARS. La orden queda pendiente de aprobación."
        ),
        backstory=SOUL_COMPRAS,
        allow_delegation=False,
        max_iter=3,
        verbose=False,
    )

    # Calcular items y total directamente (determinista)
    items_orden, total = _calcular_items_orden(
        connector, motivo, items_a_comprar
    )

    task = Task(
        description=f"""
        Generar orden de compra para:
            evento_id: {evento_id}
            motivo:    {motivo}
            desvio:    {desvio_info}

        Items a comprar:
        {items_orden}

        Total estimado: ARS {total:,}

        Pasos:
        1. Generar orden_id con formato OC-YYYY-NNN
        2. Registrar en ordenes_compra con status="pendiente"
        3. Retornar orden_id, items y total para que el Jefe apruebe o rechace
        """,
        expected_output=(
            "JSON con orden_id, total_ars, motivo, items (lista) y mensaje."
        ),
        agent=agent,
        output_pydantic=OrdenCompraCreada,
    )

    # Persistir la orden directamente
    _guardar_orden(connector, evento_id, motivo, items_orden, total)

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


def _calcular_items_orden(
    connector: BaseDataConnector,
    motivo: str,
    items_base: list[dict],
) -> tuple[list[dict], int]:
    """
    Calcula items y total de la orden según el motivo.
    Para alerta climática aplica los factores de incremento.
    """
    precios = {
        p["producto_id"]: int(p["precio_ars"])
        for p in connector.read("precios_bebidas")
    }

    # Precios para consumibles no en precios_bebidas
    PRECIO_HIELO  = 3_000   # ARS por bolsa 2kg
    PRECIO_AGUA   = 800     # ARS por botella 1.5L

    FACTORES_CLIMA = {
        "HIELO-001": 1.50,
        "AGUA-001":  1.30,
    }
    FACTOR_CLIMA_DEFAULT = 1.20  # para bebidas

    items_orden = []
    total = 0

    for item in items_base:
        item_id  = item["item_id"]
        cantidad = item["cantidad"]

        # Ajustar cantidad si es alerta climática
        if motivo == "alerta_climatica":
            factor   = FACTORES_CLIMA.get(item_id, FACTOR_CLIMA_DEFAULT)
            cantidad = math.ceil(cantidad * factor)

        # Precio unitario
        if item_id == "HIELO-001":
            precio_u = PRECIO_HIELO
        elif item_id == "AGUA-001":
            precio_u = PRECIO_AGUA
        else:
            precio_u = precios.get(item_id, 0)

        subtotal = cantidad * precio_u
        total   += subtotal

        items_orden.append({
            "item_id":         item_id,
            "nombre":          item.get("nombre", item_id),
            "cantidad":        cantidad,
            "precio_unitario": precio_u,
            "subtotal":        subtotal,
        })

    return items_orden, total


def _guardar_orden(
    connector: BaseDataConnector,
    evento_id: str,
    motivo: str,
    items: list[dict],
    total: int,
) -> str:
    año      = datetime.now().year
    orden_id = f"OC-{año}-{str(uuid.uuid4())[:4].upper()}"

    connector.write("ordenes_compra", {
        "orden_id":         orden_id,
        "evento_id":        evento_id,
        "motivo":           motivo,
        "proveedor":        "Distribuidora NOA",
        "items":            items,
        "total_ars":        total,
        "status":           "pendiente",
    })

    return orden_id


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 8 — STAFFING Y LOGÍSTICA
# ══════════════════════════════════════════════════════════════════════════

SOUL_STAFFING = """
Sos el organizador de equipos de Bartenders NOA.
Asignás los bartenders correctos a cada evento según PAX, especialidad y calificación.
Sos justo y estratégico: el mejor equipo para cada evento.

REGLAS RÍGIDAS:
- Ratio: 1 bartender cada 40 PAX (CEILING)
- Head bartender: OBLIGATORIO si PAX > 100
- Priorizar bartenders con mayor calificación y especialidad "premium" para eventos premium
- NUNCA asignés un bartender con disponible=False
- Si no hay suficientes bartenders: reportarlo antes de confirmar
- Marcar bartenders asignados como no disponibles en la base de datos
"""


def create_staffing_crew(
    connector: BaseDataConnector,
    evento_id: str,
    pax: int,
    tipo_menu: str,
    fecha_evento: str,
    duracion_horas: int,
    provincia: str,
    localidad: str,
) -> Crew:
    """
    Agente 8: selecciona y asigna el equipo de bartenders para el evento.
    Actualiza disponibilidad en bartenders_disponibles.
    Genera la hoja de ruta para el equipo.
    """
    agent = Agent(
        role="Coordinador de Staffing",
        goal=(
            "Seleccionar el equipo óptimo de bartenders para el evento, "
            "actualizar su disponibilidad y generar las instrucciones logísticas."
        ),
        backstory=SOUL_STAFFING,
        allow_delegation=False,
        max_iter=3,
        verbose=False,
    )

    # Resolver staffing directamente (determinista)
    asignados, necesita_head = _seleccionar_bartenders(
        connector, pax, tipo_menu
    )

    # Actualizar disponibilidad
    for b in asignados:
        connector.update("bartenders_disponibles", b["bartender_id"], {
            "disponible":            False,
            "fecha_proxima_reserva": fecha_evento,
        })

    _generar_hoja_de_ruta(
        asignados, fecha_evento, duracion_horas, provincia, localidad
    )

    task = Task(
        description=f"""
        Confirmar asignación de staffing para:
            evento_id:  {evento_id}
            pax:        {pax}
            fecha:      {fecha_evento}
            provincia:  {provincia}

        Equipo asignado:
        {[b['nombre'] for b in asignados]}
        Necesita head: {necesita_head}

        La hoja de ruta ya fue generada.
        Retornar confirmación del equipo asignado.
        """,
        expected_output=(
            "JSON con bartenders_asignados (lista con nombre y rol), "
            "necesita_head (bool), total_bartenders (int) y hoja_de_ruta (texto)."
        ),
        agent=agent,
        output_pydantic=StaffingAsignado,
    )

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


def _seleccionar_bartenders(
    connector: BaseDataConnector,
    pax: int,
    tipo_menu: str,
) -> tuple[list[dict], bool]:
    """
    Selecciona los mejores bartenders disponibles.
    Prioriza: especialidad premium para menú premium, mayor calificación.
    """
    n_necesarios  = math.ceil(pax / 40)
    necesita_head = pax > 100

    disponibles = connector.read(
        "bartenders_disponibles",
        {"disponible": True}
    )

    if not disponibles:
        raise ValueError("No hay bartenders disponibles para este evento")

    # Ordenar: primero por especialidad (premium primero si menú premium),
    # luego por calificación descendente
    def prioridad(b: dict) -> tuple:
        especialidad_score = 0
        if tipo_menu == "premium" and b.get("especialidad") == "premium":
            especialidad_score = 1
        return (especialidad_score, float(b.get("calificacion", 0)))

    ordenados = sorted(disponibles, key=prioridad, reverse=True)

    # Head bartender: tomar el primero con es_head_bartender=True
    asignados: list[dict] = []

    if necesita_head:
        heads = [b for b in ordenados if str(b.get("es_head_bartender", "")).upper() == "TRUE"]
        if heads:
            head = heads[0]
            head["rol"] = "head"
            asignados.append(head)
            ordenados = [b for b in ordenados if b["bartender_id"] != head["bartender_id"]]
            n_necesarios -= 1

    # Resto del equipo
    for b in ordenados[:n_necesarios]:
        b["rol"] = "bartender"
        asignados.append(b)

    if len(asignados) < math.ceil(pax / 40):
        raise ValueError(
            f"Bartenders insuficientes: necesarios={math.ceil(pax/40)}, "
            f"disponibles={len(disponibles)}"
        )

    return asignados, necesita_head


def _generar_hoja_de_ruta(
    asignados: list[dict],
    fecha_evento: str,
    duracion_horas: int,
    provincia: str,
    localidad: str,
) -> str:
    """Genera el texto de instrucciones para el equipo."""
    nombres = ", ".join(
        f"{b['nombre']} ({b.get('rol', 'bartender')})"
        for b in asignados
    )
    return (
        f"HOJA DE RUTA — {fecha_evento}\n"
        f"Equipo: {nombres}\n"
        f"Destino: {localidad}, {provincia}\n"
        f"Llegada: 3 horas antes del inicio del evento\n"
        f"Duración del evento: {duracion_horas} horas\n"
        f"Salida estimada: aproximadamente {duracion_horas + 1} horas después del inicio\n"
        f"Contacto en destino: confirmar con el cliente al llegar\n"
        f"Llevar: equipamiento completo según checklist de inventario"
    )
