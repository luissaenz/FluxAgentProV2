"""
src/api/routes/bartenders.py

Endpoints HTTP de Bartenders NOA.

Todos los flows corren en background (BackgroundTasks) — el endpoint
responde 202 inmediatamente con el task_id para que el cliente haga polling
via GET /tasks/{task_id} (endpoint existente de Fases 1-4).

Rutas:
    POST /bartenders/preventa   → PreventaFlow
    POST /bartenders/reserva    → ReservaFlow
    POST /bartenders/alerta     → AlertaClimaFlow (trigger manual para demo)
    POST /bartenders/cierre     → CierreFlow
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional
import structlog

from uuid import uuid4
from src.flows.registry import flow_registry
from ..middleware import require_org_id

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/bartenders", tags=["bartenders"])


# ─── Modelos de request ────────────────────────────────────────────────────

class PreventaRequest(BaseModel):
    fecha_evento:    str = Field(..., example="2026-07-20",
                                 description="Fecha del evento (YYYY-MM-DD)")
    provincia:       str = Field(..., example="Tucuman",
                                 description="Tucuman | Salta | Jujuy | Catamarca")
    localidad:       str = Field(..., example="San Miguel de Tucumán")
    tipo_evento:     str = Field(..., example="boda",
                                 description="boda | corporativo | fiesta | otro")
    pax:             int = Field(..., ge=10, le=500, example=150)
    duracion_horas:  int = Field(..., ge=1,  le=24,  example=5)
    tipo_menu:       str = Field(..., example="premium",
                                 description="basico | estandar | premium")
    restricciones:   Optional[str] = Field(None, example="Sin gluten para 5 personas")


class ReservaRequest(BaseModel):
    evento_id:      str = Field(..., example="EVT-2026-001")
    cotizacion_id:  str = Field(..., example="COT-2026-001")
    opcion_elegida: str = Field(..., example="recomendada",
                                description="basica | recomendada | premium")


class AlertaRequest(BaseModel):
    evento_id: str = Field(..., example="EVT-2026-001")


class CierreRequest(BaseModel):
    evento_id:           str  = Field(..., example="EVT-2026-001")
    costo_real:          int  = Field(..., example=4_608_458,
                                      description="Costo total real del evento en ARS")
    mermas:              int  = Field(0, example=250_000,
                                      description="Pérdidas por mermas en ARS")
    compras_emergencia:  int  = Field(0, example=220_000,
                                      description="Monto de compras de emergencia en ARS")
    desvio_climatico:    str  = Field("", example="+7°C vs histórico enero")
    rating:              Optional[int] = Field(None, ge=1, le=5, example=5,
                                               description="Calificación del cliente (1-5)")


# ─── Respuesta estándar ────────────────────────────────────────────────────

class FlowResponse(BaseModel):
    task_id:    str
    status:     str = "pending"
    flow_type:  str
    mensaje:    str


# ─── Endpoints ────────────────────────────────────────────────────────────

@router.post(
    "/preventa",
    response_model=FlowResponse,
    status_code=202,
    summary="Iniciar flow de preventa",
    description=(
        "Recibe los datos del evento y genera una cotización con 3 opciones de precio. "
        "Corre los Agentes 1 (requerimientos), 2 (clima), 3 (escandallo) y 4 (presupuesto). "
        "El resultado estará disponible en GET /tasks/{task_id} cuando status=completed."
    ),
)
async def preventa(
    request:          PreventaRequest,
    background_tasks: BackgroundTasks,
    org_id:           str = Depends(require_org_id),
):
    flow = flow_registry.create("bartenders_preventa", org_id=org_id)

    correlation_id = f"bartenders-preventa-{uuid4().hex[:6]}"
    await flow.create_task_record(request.model_dump(), correlation_id=correlation_id)

    background_tasks.add_task(
        flow.execute,
        request.model_dump(),
    )

    logger.info("bartenders.preventa.iniciado",
                org_id=org_id, pax=request.pax, tipo_menu=request.tipo_menu)

    return FlowResponse(
        task_id   = flow.state.task_id,
        flow_type = "bartenders_preventa",
        mensaje   = (
            f"Calculando escandallo para {request.pax} PAX en {request.provincia}. "
            f"Las 3 opciones de precio estarán listas en unos segundos."
        ),
    )


@router.post(
    "/reserva",
    response_model=FlowResponse,
    status_code=202,
    summary="Confirmar cotización y reservar",
    description=(
        "Confirma la opción de cotización elegida, reserva el stock físico "
        "y asigna el equipo de bartenders. "
        "Puede pausar con HITL si hay faltante de stock."
    ),
)
async def reserva(
    request:          ReservaRequest,
    background_tasks: BackgroundTasks,
    org_id:           str = Depends(require_org_id),
):
    flow = flow_registry.create("bartenders_reserva", org_id=org_id)

    correlation_id = f"bartenders-reserva-{uuid4().hex[:6]}"
    await flow.create_task_record(request.model_dump(), correlation_id=correlation_id)

    background_tasks.add_task(
        flow.execute,
        request.model_dump(),
    )

    logger.info("bartenders.reserva.iniciado",
                org_id=org_id, evento_id=request.evento_id)

    return FlowResponse(
        task_id   = flow.state.task_id,
        flow_type = "bartenders_reserva",
        mensaje   = (
            f"Reservando stock y asignando equipo para evento {request.evento_id}. "
            f"Si falta stock, aparecerá una aprobación pendiente en el Dashboard."
        ),
    )


@router.post(
    "/alerta",
    response_model=FlowResponse,
    status_code=202,
    summary="Trigger manual de alerta climática",
    description=(
        "Verifica el pronóstico meteorológico real para el evento. "
        "Si el desvío supera el 10%, genera una orden de compra de emergencia "
        "que requiere aprobación del Jefe (HITL). "
        "Normalmente lo dispara el scheduler automáticamente T-7 días antes del evento. "
        "Este endpoint permite el trigger manual para demo y testing."
    ),
)
async def alerta_clima(
    request:          AlertaRequest,
    background_tasks: BackgroundTasks,
    org_id:           str = Depends(require_org_id),
):
    flow = flow_registry.create("bartenders_alerta", org_id=org_id)

    correlation_id = f"bartenders-alerta-{uuid4().hex[:6]}"
    await flow.create_task_record(request.model_dump(), correlation_id=correlation_id)

    background_tasks.add_task(
        flow.execute,
        request.model_dump(),
    )

    logger.info("bartenders.alerta.iniciado",
                org_id=org_id, evento_id=request.evento_id)

    return FlowResponse(
        task_id   = flow.state.task_id,
        flow_type = "bartenders_alerta",
        mensaje   = (
            f"Verificando pronóstico climático para evento {request.evento_id}. "
            f"Si hay alerta roja, aparecerá una aprobación pendiente en el Dashboard."
        ),
    )


@router.post(
    "/cierre",
    response_model=FlowResponse,
    status_code=202,
    summary="Cerrar evento post-ejecución",
    description=(
        "Registra la auditoría de rentabilidad real y cierra el evento. "
        "Si el margen real es menor al 10%, pausa para revisión del Jefe (HITL). "
        "Programa el próximo contacto con el cliente para el mismo mes del año siguiente."
    ),
)
async def cierre(
    request:          CierreRequest,
    background_tasks: BackgroundTasks,
    org_id:           str = Depends(require_org_id),
):
    flow = flow_registry.create("bartenders_cierre", org_id=org_id)

    correlation_id = f"bartenders-cierre-{uuid4().hex[:6]}"
    await flow.create_task_record(request.model_dump(), correlation_id=correlation_id)

    background_tasks.add_task(
        flow.execute,
        request.model_dump(),
    )

    logger.info("bartenders.cierre.iniciado",
                org_id=org_id, evento_id=request.evento_id,
                costo_real=request.costo_real)

    return FlowResponse(
        task_id   = flow.state.task_id,
        flow_type = "bartenders_cierre",
        mensaje   = (
            f"Auditando rentabilidad del evento {request.evento_id}. "
            f"Si el margen es crítico (< 10%), aparecerá una aprobación pendiente."
        ),
    )
