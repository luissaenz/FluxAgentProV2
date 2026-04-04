"""
src/crews/bartenders/cierre_crews.py

Crews de la Fase 3 — Cierre y Background (Agentes 9, 10, 11).

Agente 9:  Auditoría post-evento — rentabilidad real y lecciones
Agente 10: Feedback y nurturing — encuesta, retención, próximo contacto
Agente 11: Monitor de precios — job background semanal (mock en Fase 6)
"""

import uuid
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from crewai import Agent, Crew, Task, Process
from pydantic import BaseModel, Field
from typing import Any

from src.connectors.base_connector import BaseDataConnector


# ══════════════════════════════════════════════════════════════════════════
# MODELOS DE OUTPUT
# ══════════════════════════════════════════════════════════════════════════

class AuditoriaResult(BaseModel):
    auditoria_id:    str
    evento_id:       str
    precio_cobrado:  int
    costo_real:      int
    ganancia_neta:   int
    margen_pct:      float
    margen_critico:  bool = Field(
        ...,
        description="True si margen < 10% — requiere revisión del Jefe (HITL)"
    )
    leccion:         str


class FeedbackResult(BaseModel):
    evento_id:        str
    proxima_contacto: str  # fecha YYYY-MM-DD
    mensaje_enviado:  str
    descuento_ofrecido: int  # porcentaje


class PreciosActualizados(BaseModel):
    productos_actualizados: int
    ofertas_detectadas:     int
    resumen:                str


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 9 — AUDITORÍA POST-EVENTO
# ══════════════════════════════════════════════════════════════════════════

SOUL_AUDITORIA = """
Sos el contador de Bartenders NOA.
Auditás la rentabilidad real de cada evento comparando costos presupuestados vs reales.
Sos objetivo y riguroso — los números no mienten y las lecciones se aprenden.

REGLAS RÍGIDAS:
- ganancia_neta = precio_cobrado - costo_real (columna generada en DB)
- margen_pct = (ganancia_neta / precio_cobrado) × 100
- Si margen_pct < 10%: marcar como margen_critico=True para HITL del Jefe
- La lección debe ser accionable: qué hacer diferente en el próximo evento similar
- NUNCA cerrar un evento sin registrar la auditoría
"""

MARGEN_CRITICO_UMBRAL = 10.0  # % — si el margen real es menor a esto, HITL


def create_auditoria_crew(
    connector: BaseDataConnector,
    evento_id: str,
    costo_real: int,
    mermas: int,
    compras_emergencia: int,
    desvio_climatico: str,
) -> Crew:
    """
    Agente 9: audita la rentabilidad real post-evento.

    Si margen < 10%, el CierreFlow llamará request_approval()
    para que el Jefe revise antes de cerrar el evento.
    """
    agent = Agent(
        role="Auditor Financiero",
        goal=(
            "Calcular la rentabilidad real del evento, registrar la auditoría "
            "y extraer una lección aprendida para futuros eventos similares."
        ),
        backstory=SOUL_AUDITORIA,
        allow_delegation=False,
        max_iter=3,
        verbose=False,
    )

    # Obtener precio cobrado desde cotizaciones
    cotizacion = connector.read_one("cotizaciones", {"evento_id": evento_id})
    if not cotizacion:
        raise ValueError(f"No se encontró cotización para evento {evento_id}")

    opcion_elegida = cotizacion.get("opcion_elegida", "recomendada")
    precio_cobrado = int(cotizacion.get(f"opcion_{opcion_elegida}", 0))
    ganancia_neta  = precio_cobrado - costo_real
    margen_pct     = round((ganancia_neta / precio_cobrado) * 100, 2) if precio_cobrado > 0 else 0
    margen_critico = margen_pct < MARGEN_CRITICO_UMBRAL

    task = Task(
        description=f"""
        Auditar el evento {evento_id}:
            precio_cobrado:     ARS {precio_cobrado:,}
            costo_real:         ARS {costo_real:,}
            mermas:             ARS {mermas:,}
            compras_emergencia: ARS {compras_emergencia:,}
            ganancia_neta:      ARS {ganancia_neta:,}
            margen_pct:         {margen_pct}%
            desvio_climatico:   {desvio_climatico}
            margen_critico:     {margen_critico}

        Pasos:
        1. Registrar auditoría en la base de datos
        2. Generar lección aprendida (1-2 oraciones, accionable)
        3. Actualizar evento con status="ejecutado"
        4. Si margen_critico=True: indicarlo claramente en el output
        """,
        expected_output=(
            "JSON con auditoria_id, ganancia_neta, margen_pct, "
            "margen_critico (bool) y leccion (texto accionable)."
        ),
        agent=agent,
        output_pydantic=AuditoriaResult,
    )

    # Persistir auditoría directamente
    auditoria_id = _guardar_auditoria(
        connector, evento_id, precio_cobrado, costo_real,
        margen_pct, mermas, compras_emergencia, desvio_climatico
    )

    # Actualizar status del evento
    connector.update("eventos", evento_id, {"status": "ejecutado"})

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


def _guardar_auditoria(
    connector: BaseDataConnector,
    evento_id: str,
    precio_cobrado: int,
    costo_real: int,
    margen_pct: float,
    mermas: int,
    compras_emergencia: int,
    desvio_climatico: str,
) -> str:
    año          = datetime.now().year
    auditoria_id = f"AUD-{año}-{str(uuid.uuid4())[:4].upper()}"

    connector.write("auditorias", {
        "auditoria_id":       auditoria_id,
        "evento_id":          evento_id,
        "precio_cobrado":     precio_cobrado,
        "costo_real":         costo_real,
        "margen_pct":         margen_pct,
        "mermas":             mermas,
        "compras_emergencia": compras_emergencia,
        "desvio_climatico":   desvio_climatico,
        "fecha_cierre":       date.today().isoformat(),
    })

    return auditoria_id


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 10 — FEEDBACK Y NURTURING
# ══════════════════════════════════════════════════════════════════════════

SOUL_FEEDBACK = """
Sos el embajador de Bartenders NOA.
Cuidás la relación con el cliente después del evento para generar fidelidad.
Sos cálido, profesional y orientado al largo plazo.

REGLAS RÍGIDAS:
- proxima_contacto: SIEMPRE el mismo mes del año siguiente
  (si el evento fue en enero 2026 → contactar enero 2027)
- Descuento estándar: 10% para próximo evento
- El mensaje de seguimiento debe mencionar algo específico del evento
- NUNCA envíes un mensaje genérico — personalizá con datos del evento
"""


def create_feedback_crew(
    connector: BaseDataConnector,
    evento_id: str,
    rating: int | None = None,
) -> Crew:
    """
    Agente 10: gestiona el cierre relacional del evento.
    Registra el próximo contacto y genera el mensaje de seguimiento.
    """
    agent = Agent(
        role="Embajador de Clientes",
        goal=(
            "Generar el mensaje de seguimiento personalizado para el cliente, "
            "programar el próximo contacto y actualizar el registro del evento."
        ),
        backstory=SOUL_FEEDBACK,
        allow_delegation=False,
        max_iter=3,
        verbose=False,
    )

    # Calcular próximo contacto: mismo mes, año siguiente
    evento = connector.read_one("eventos", {"evento_id": evento_id})
    if not evento:
        raise ValueError(f"Evento {evento_id} no encontrado")

    fecha_evento     = datetime.strptime(str(evento["fecha_evento"]), "%Y-%m-%d").date()
    proxima_contacto = (fecha_evento + relativedelta(years=1)).isoformat()

    task = Task(
        description=f"""
        Generar seguimiento post-evento para:
            evento_id:   {evento_id}
            tipo_evento: {evento.get('tipo_evento')}
            pax:         {evento.get('pax')}
            provincia:   {evento.get('provincia')}
            rating:      {rating or 'no registrado'}

        Próximo contacto calculado: {proxima_contacto}
        Descuento a ofrecer: 10%

        Pasos:
        1. Redactar mensaje de seguimiento personalizado (2-3 oraciones)
           mencionando el tipo de evento y la cantidad de personas
        2. Actualizar evento con proxima_contacto={proxima_contacto}
        3. Si hay rating: actualizar campo rating en eventos
        4. Marcar evento como status="cerrado"
        """,
        expected_output=(
            "JSON con proxima_contacto (fecha), mensaje_enviado (texto) "
            "y descuento_ofrecido (int)."
        ),
        agent=agent,
        output_pydantic=FeedbackResult,
    )

    # Persistir datos directamente
    update_data: dict = {
        "proxima_contacto": proxima_contacto,
        "status":           "cerrado",
    }
    if rating is not None:
        update_data["rating"] = rating

    connector.update("eventos", evento_id, update_data)

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 11 — MONITOR DE PRECIOS (JOB BACKGROUND)
# ══════════════════════════════════════════════════════════════════════════

SOUL_MONITOR_PRECIOS = """
Sos el cazador de ofertas de Bartenders NOA.
Monitoreás los precios de bebidas en el mercado NOA y actualizás la base de datos.
Sos sistemático y preciso — cada actualización tiene fuente y fecha.

REGLAS RÍGIDAS:
- Fase 6: los precios vienen del mock MOCK_PRECIOS_ACTUALIZADOS (configurable)
- Fase 7: reemplazar con scraping real de Carrefour, Día, Mayorista X
- Una oferta es: precio actual < precio_base_referencia × 0.85 (ahorro > 15%)
- Siempre registrar en historial_precios antes de actualizar precios_bebidas
- Si precio subió > 20% vs referencia: alertar en el resumen
"""

# Mock de precios actualizados para Fase 6
# Estructura: { producto_id: { precio_ars, fuente } }
MOCK_PRECIOS_ACTUALIZADOS: dict[str, dict] = {
    "GIN-001":    {"precio_ars": 11_500, "fuente": "Carrefour Tucuman"},
    "GIN-002":    {"precio_ars": 27_500, "fuente": "Mayorista X"},
    "WHISKY-001": {"precio_ars":  6_800, "fuente": "Dia Tucuman"},
    "WHISKY-002": {"precio_ars": 24_000, "fuente": "Mayorista X"},
    "VODKA-001":  {"precio_ars":  7_500, "fuente": "Carrefour Tucuman"},
    "RON-001":    {"precio_ars": 17_000, "fuente": "Mayorista X"},
    "TEQUILA-001":{"precio_ars": 21_000, "fuente": "Mayorista X"},
}

UMBRAL_OFERTA_PCT = 15.0   # % de descuento vs precio_base para marcar como oferta
UMBRAL_ALERTA_SUBIDA = 20.0  # % de suba vs precio_base para alertar


def create_monitor_precios_crew(connector: BaseDataConnector) -> Crew:
    """
    Agente 11: actualiza precios y registra historial.
    Se ejecuta semanalmente via APScheduler — no está asociado a ningún evento.

    Fase 6: usa MOCK_PRECIOS_ACTUALIZADOS.
    Fase 7: reemplazar _fetch_precios_mercado() con scraping real.
    """
    agent = Agent(
        role="Monitor de Precios de Mercado",
        goal=(
            "Actualizar los precios de bebidas en la base de datos "
            "con los valores actuales del mercado NOA. "
            "Identificar ofertas y alertar sobre subidas significativas."
        ),
        backstory=SOUL_MONITOR_PRECIOS,
        allow_delegation=False,
        max_iter=2,
        verbose=False,
    )

    # Ejecutar actualización directamente (determinista en Fase 6)
    resultado = _actualizar_precios(connector)

    task = Task(
        description=f"""
        Confirmar actualización de precios completada:
            Productos actualizados: {resultado['actualizados']}
            Ofertas detectadas:     {resultado['ofertas']}
            Alertas de subida:      {resultado['alertas']}

        Generar resumen ejecutivo para el Jefe.
        """,
        expected_output=(
            "JSON con productos_actualizados (int), "
            "ofertas_detectadas (int) y resumen (texto)."
        ),
        agent=agent,
        output_pydantic=PreciosActualizados,
    )

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


def _actualizar_precios(connector: BaseDataConnector) -> dict:
    """
    Fase 6: actualiza precios desde el mock.
    Fase 7: reemplazar MOCK_PRECIOS_ACTUALIZADOS con scraping.
    """
    precios_actuales = {
        p["producto_id"]: p
        for p in connector.read("precios_bebidas")
    }

    actualizados = 0
    ofertas      = 0
    alertas      = 0
    hoy          = date.today().isoformat()

    for producto_id, nuevo in MOCK_PRECIOS_ACTUALIZADOS.items():
        actual = precios_actuales.get(producto_id)
        if not actual:
            continue

        precio_nuevo    = nuevo["precio_ars"]
        precio_anterior = int(actual["precio_ars"])
        precio_base     = int(actual.get("precio_base_referencia") or precio_anterior)

        variacion_pct = round(
            (precio_nuevo - precio_anterior) / precio_anterior * 100, 2
        )

        # Registrar en historial antes de actualizar
        connector.write("historial_precios", {
            "producto_id":  producto_id,
            "precio_ars":   precio_nuevo,
            "fuente":       nuevo["fuente"],
            "variacion_pct":variacion_pct,
            "fecha":        hoy,
        })

        # Determinar si es oferta
        es_oferta = precio_nuevo < precio_base * (1 - UMBRAL_OFERTA_PCT / 100)
        if es_oferta:
            ofertas += 1

        # Detectar subida significativa
        subida = precio_nuevo > precio_base * (1 + UMBRAL_ALERTA_SUBIDA / 100)
        if subida:
            alertas += 1

        # Actualizar precio actual
        connector.update("precios_bebidas", producto_id, {
            "precio_ars":          precio_nuevo,
            "fuente":              nuevo["fuente"],
            "fecha_actualizacion": hoy,
            "es_oferta":           es_oferta,
        })

        actualizados += 1

    return {
        "actualizados": actualizados,
        "ofertas":      ofertas,
        "alertas":      alertas,
    }
