"""
src/crews/bartenders/preventa_crews.py

Crews de la Fase 1 — Preventa (Agentes 1, 2, 3, 4).
Orquestados por PreventaFlow en el orden: A1 → A2 → A3 → A4.

Reglas invariantes de todos los agentes:
    - allow_delegation = False  (nunca delegan a otro agente)
    - max_iter ≤ 3              (falla rápido si el LLM no converge)
    - output_pydantic           (salida tipada y validada)
    - El conector se inyecta — nunca importado directamente
"""

from crewai import Agent, Crew, Task, Process
from pydantic import BaseModel
from src.connectors.base_connector import BaseDataConnector
from src.tools.demo.escandallo_tool import EscandalloTool
from src.tools.demo.clima_tool import FactorClimaticoTool


# ══════════════════════════════════════════════════════════════════════════
# MODELOS DE OUTPUT
# ══════════════════════════════════════════════════════════════════════════

class EventoRegistrado(BaseModel):
    evento_id:      str
    status:         str = "nuevo"
    mensaje:        str


class FactorClimaticoResult(BaseModel):
    evento_id:      str
    mes:            int
    factor_pct:     int
    razon:          str


class EscandalloResult(BaseModel):
    evento_id:          str
    escandallo_final:   int
    bloque1_productos:  int
    bloque2_equipamiento: int
    bloque3_personal:   int
    bloque4_logistica:  int
    ajuste_climatico:   int
    mermas:             int
    imprevistos:        int
    bartenders_necesarios: int
    factor_climatico_aplicado: int


class CotizacionGenerada(BaseModel):
    evento_id:          str
    cotizacion_id:      str
    escandallo_total:   int
    opcion_basica:      int
    opcion_recomendada: int
    opcion_premium:     int
    factor_climatico:   int


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 1 — REQUERIMIENTOS
# ══════════════════════════════════════════════════════════════════════════

SOUL_REQUERIMIENTOS = """
Sos el primer punto de contacto de Bartenders NOA.
Tu trabajo es capturar y validar los datos del evento con precisión absoluta.
Sos meticuloso, detallista y no avanzás si los datos son ambiguos o incorrectos.

REGLAS RÍGIDAS — NUNCA las violes:
- NUNCA asumas una provincia si no está especificada
- NUNCA aceptes PAX fuera del rango 10-500
- NUNCA aceptes fechas en el pasado
- NUNCA uses tipo_menu que no sea: basico, estandar o premium
- Si falta cualquier dato obligatorio: detené y solicitalo

Provincias válidas: Tucuman, Salta, Jujuy, Catamarca
"""


def create_requerimientos_crew(
    connector: BaseDataConnector,
    input_data: dict,
) -> Crew:
    """
    Agente 1: valida input del evento y crea el registro en la tabla eventos.

    Input esperado en input_data:
        fecha_evento, provincia, localidad, tipo_evento,
        pax, duracion_horas, tipo_menu, restricciones (opcional)
    """
    from datetime import date

    agent = Agent(
        role="Analista de Requerimientos",
        goal=(
            "Validar todos los datos del evento recibidos, "
            "generar un evento_id único y registrar el evento en la base de datos."
        ),
        backstory=SOUL_REQUERIMIENTOS,
        allow_delegation=False,
        max_iter=3,
        verbose=False,
    )

    task = Task(
        description=f"""
        Validar y registrar el siguiente evento:

        Datos recibidos:
        {input_data}

        Pasos obligatorios:
        1. Verificar que fecha_evento no sea anterior a hoy ({date.today()})
        2. Verificar que pax esté entre 10 y 500
        3. Verificar que provincia sea una de: Tucuman, Salta, Jujuy, Catamarca
        4. Verificar que tipo_menu sea: basico, estandar o premium
        5. Generar evento_id con formato EVT-YYYY-NNN (ej: EVT-2026-002)
        6. Registrar el evento en la base de datos con status="nuevo"
        7. Retornar el evento_id generado y confirmación

        Si alguna validación falla: retornar el error específico en el campo "mensaje".
        """,
        expected_output=(
            "JSON con evento_id generado, status='nuevo' y "
            "mensaje de confirmación o error."
        ),
        agent=agent,
        output_pydantic=EventoRegistrado,
    )

    # Ejecutar el registro directamente (no depende del LLM para validación)
    _registrar_evento(connector, input_data)

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


def _registrar_evento(connector: BaseDataConnector, data: dict) -> dict:
    """Registro directo en DB. Separado del LLM para garantizar consistencia."""
    import uuid
    from datetime import datetime

    año = datetime.now().year
    # Generar ID secuencial simple para demo
    evento_id = f"EVT-{año}-{str(uuid.uuid4())[:4].upper()}"

    return connector.write("eventos", {
        "evento_id":      evento_id,
        "fecha_evento":   data["fecha_evento"],
        "provincia":      data["provincia"],
        "localidad":      data["localidad"],
        "tipo_evento":    data["tipo_evento"],
        "pax":            int(data["pax"]),
        "duracion_horas": int(data["duracion_horas"]),
        "tipo_menu":      data["tipo_menu"],
        "restricciones":  data.get("restricciones"),
        "status":         "nuevo",
    })


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 2 — METEOROLÓGICO HISTÓRICO
# ══════════════════════════════════════════════════════════════════════════

SOUL_METEOROLOGICO = """
Sos el analista climático de Bartenders NOA.
Consultás datos históricos de NOA para determinar el riesgo estacional del evento.
Sos frío, objetivo y basás todo en datos — nunca en intuición ni en estimaciones.

REGLAS RÍGIDAS:
- El factor climático viene EXCLUSIVAMENTE de la tabla config_climatico
- NUNCA inventés un factor — si no encontrás el mes, usá 10% como default
- Siempre incluí la razón del factor para transparencia con el Jefe
- El mes lo extraés de la fecha_evento (campo mes: 1-12)
"""


def create_meteorologico_crew(
    connector: BaseDataConnector,
    evento_id: str,
    fecha_evento: str,
    provincia: str,
) -> Crew:
    """
    Agente 2: determina el factor de riesgo climático histórico.
    Retorna factor_pct para que el Agente 3 lo use en el escandallo.
    """
    tool = FactorClimaticoTool(connector=connector)
    mes  = int(fecha_evento.split("-")[1])

    agent = Agent(
        role="Analista Climático NOA",
        goal=(
            "Determinar el factor de riesgo climático histórico "
            "para la fecha y provincia del evento."
        ),
        backstory=SOUL_METEOROLOGICO,
        tools=[tool],
        allow_delegation=False,
        max_iter=3,
        verbose=False,
    )

    task = Task(
        description=f"""
        Determinar el factor climático para:
            evento_id:    {evento_id}
            fecha_evento: {fecha_evento}
            mes:          {mes}
            provincia:    {provincia}

        Usar la tool 'obtener_factor_climatico' con mes={mes}.
        Retornar el factor_pct y la razón del ajuste.
        """,
        expected_output=(
            "JSON con evento_id, mes, factor_pct (entero) y razon (texto)."
        ),
        agent=agent,
        output_pydantic=FactorClimaticoResult,
    )

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 3 — CALCULADOR (ESCANDALLO)
# ══════════════════════════════════════════════════════════════════════════

SOUL_CALCULADOR = """
Sos el ingeniero financiero de Bartenders NOA.
Calculás el escandallo de costos con precisión matemática usando 4 bloques.
Cada número tiene una fuente — nunca estimás sin respaldo en tablas de datos.

REGLAS RÍGIDAS — son matemáticas, no negociables:
- Ratio bartenders: 1 cada 40 PAX (CEILING, nunca floor)
- Horas de setup/cierre: SIEMPRE +3 horas al costo de personal
- Mermas: SIEMPRE 5% sobre el subtotal ajustado
- Imprevistos: SIEMPRE 3% sobre el subtotal ajustado
- Factor climático: se aplica SOLO sobre Bloques 1 (productos) y 2 (equipamiento)
- Head bartender: obligatorio si PAX > 100
- Asistente: obligatorio si duración > 6 horas
"""


def create_calculador_crew(
    connector: BaseDataConnector,
    evento_id: str,
    pax: int,
    duracion_horas: int,
    tipo_menu: str,
    provincia: str,
    factor_climatico_pct: int,
) -> Crew:
    """
    Agente 3: calcula el escandallo completo de 4 bloques.
    Este es el cálculo determinista — no hay estimación del LLM en los números.
    """
    tool = EscandalloTool(connector=connector)

    agent = Agent(
        role="Calculador de Escandallos",
        goal=(
            "Calcular el costo base completo del evento usando la tool "
            "calcular_escandallo. Retornar el desglose por bloque."
        ),
        backstory=SOUL_CALCULADOR,
        tools=[tool],
        allow_delegation=False,
        max_iter=2,  # El cálculo es determinista — no necesita más de 2 intentos
        verbose=False,
    )

    task = Task(
        description=f"""
        Calcular el escandallo para:
            evento_id:            {evento_id}
            pax:                  {pax}
            duracion_horas:       {duracion_horas}
            tipo_menu:            {tipo_menu}
            provincia:            {provincia}
            factor_climatico_pct: {factor_climatico_pct}

        Usar la tool 'calcular_escandallo' con exactamente esos parámetros.
        NO modificar ningún valor — usarlos tal como están.
        Retornar el desglose completo por bloque.
        """,
        expected_output=(
            "JSON con escandallo_final y desglose por bloques "
            "(bloque1_productos, bloque2_equipamiento, bloque3_personal, "
            "bloque4_logistica, ajuste_climatico, mermas, imprevistos)."
        ),
        agent=agent,
        output_pydantic=EscandalloResult,
    )

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


# ══════════════════════════════════════════════════════════════════════════
# AGENTE 4 — PRESUPUESTADOR
# ══════════════════════════════════════════════════════════════════════════

SOUL_PRESUPUESTADOR = """
Sos el comercial de Bartenders NOA.
Convertís el escandallo técnico en 3 propuestas de precio para el cliente.
Sos transparente con los números pero estratégico en cómo los presentás.

REGLAS RÍGIDAS:
- Las 3 opciones usan márgenes EXACTOS de config_margenes: 40% / 45% / 50%
- Fórmula: precio = escandallo / (1 - margen_decimal)
- NUNCA modifiques los márgenes ni redondees a la baja
- La "recomendada" es SIEMPRE la del 45%
- NUNCA generes una cotización sin guardarla en la base de datos
"""

# Márgenes fijos (espejo de config_margenes en DB)
MARGENES = {
    "basica":      0.40,
    "recomendada": 0.45,
    "premium":     0.50,
}


def create_presupuestador_crew(
    connector: BaseDataConnector,
    evento_id: str,
    escandallo_total: int,
    factor_climatico: int,
) -> Crew:
    """
    Agente 4: genera las 3 opciones de cotización y las persiste en DB.
    El cálculo es aritmético — el LLM solo orquesta la generación del ID y
    la escritura en DB.
    """
    # Calcular las 3 opciones directamente (no delegamos aritmética al LLM)
    opciones = _calcular_opciones(escandallo_total)

    agent = Agent(
        role="Presupuestador Comercial",
        goal=(
            "Generar la cotización formal con 3 opciones de precio "
            "y persistirla en la base de datos."
        ),
        backstory=SOUL_PRESUPUESTADOR,
        allow_delegation=False,
        max_iter=3,
        verbose=False,
    )

    task = Task(
        description=f"""
        Generar y registrar la cotización para:
            evento_id:        {evento_id}
            escandallo_total: {escandallo_total}
            factor_climatico: {factor_climatico}

        Opciones calculadas (NO modificar):
            opcion_basica:      {opciones['basica']}
            opcion_recomendada: {opciones['recomendada']}
            opcion_premium:     {opciones['premium']}

        Pasos:
        1. Generar cotizacion_id con formato COT-YYYY-NNN
        2. Guardar en la tabla cotizaciones con status="generada"
        3. Actualizar el evento con cotizacion_id y status="cotizado"
        4. Retornar la cotizacion_id y las 3 opciones
        """,
        expected_output=(
            "JSON con cotizacion_id, escandallo_total y las 3 opciones "
            "(opcion_basica, opcion_recomendada, opcion_premium)."
        ),
        agent=agent,
        output_pydantic=CotizacionGenerada,
    )

    # Persistencia directa — separada del LLM
    _guardar_cotizacion(
        connector, evento_id, escandallo_total, opciones, factor_climatico
    )

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


def _calcular_opciones(escandallo: int) -> dict[str, int]:
    """Fórmula: precio = escandallo / (1 - margen). Resultado redondeado."""
    return {
        nombre: round(escandallo / (1 - margen))
        for nombre, margen in MARGENES.items()
    }


def _guardar_cotizacion(
    connector: BaseDataConnector,
    evento_id: str,
    escandallo_total: int,
    opciones: dict[str, int],
    factor_climatico: int,
) -> str:
    import uuid
    from datetime import datetime

    año = datetime.now().year
    cotizacion_id = f"COT-{año}-{str(uuid.uuid4())[:4].upper()}"

    connector.write("cotizaciones", {
        "cotizacion_id":     cotizacion_id,
        "evento_id":         evento_id,
        "escandallo_total":  escandallo_total,
        "opcion_basica":     opciones["basica"],
        "opcion_recomendada":opciones["recomendada"],
        "opcion_premium":    opciones["premium"],
        "factor_climatico":  factor_climatico,
        "status":            "generada",
    })

    connector.update("eventos", evento_id, {
        "cotizacion_id": cotizacion_id,
        "status":        "cotizado",
    })

    return cotizacion_id
