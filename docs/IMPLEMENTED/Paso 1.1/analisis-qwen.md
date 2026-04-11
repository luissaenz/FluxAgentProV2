# Análisis Técnico — Paso 1.1: Refactorizar `POST /tickets/{id}/execute`

**Agente:** qwen  
**Fecha:** 2026-04-11  
**Alcance:** Únicamente el endpoint `POST /tickets/{id}/execute` en `src/api/routes/tickets.py`

---

## 1. Diseño Funcional

### 1.1 Problema que resuelve

El endpoint actual ya tiene un bloque `try/except` básico que captura errores genéricos del flow y marca el ticket como `blocked`. Sin embargo, el análisis del código revela **deficiencias concretas** que impiden considerar este manejo de errores como robusto para producción:

1. **Captura excesivamente genérica**: El `except Exception as exc` atrapa TODO, incluyendo errores que no son del motor de ejecución (ej: errores de base de datos al actualizar el ticket, errores de red, etc.). Esto hace imposible distinguir entre "el flow falló" y "la infraestructura falló".
2. **Notas sobrescritas sin contexto**: Si el ticket ya tenía notas previas, el error las sobrescribe sin preservar el historial.
3. **No registra el tipo de excepción**: Solo guarda `str(exc)`, perdiendo el tipo de excepción que es información valiosa para debugging.
4. **Falta validación del estado post-ejecución**: Si `execute_flow` retorna `None` (caso posible según su firma), el endpoint continúa como si todo estuviera bien y marca el ticket como `done` con `task_id=None`.
5. **Doble escritura de estado**: Si el flow falla DENTRO de `execute_flow` pero la excepción es capturada internamente por `with_error_handling` en `BaseFlow`, el flow ya marcó su estado como `FAILED` en la tabla `tasks`, pero el endpoint no tiene visibilidad de esto — solo ve el `task_id` retornado.

### 1.2 Happy Path

1. Cliente envía `POST /tickets/{id}/execute` con header `X-Org-ID`.
2. Endpoint verifica que el ticket existe, tiene `flow_type` y su estado permite ejecución (`backlog`).
3. Cambia el status del ticket a `in_progress`.
4. Invoca `execute_flow(flow_type, org_id, input_data, correlation_id)`.
5. `execute_flow`:
   - Instancia el flow desde el registry.
   - Llama `flow.execute(input_data, correlation_id)`.
   - El flow crea el task record, ejecuta el crew, persiste el estado.
   - Retorna `task_id` (el ID real asignado en `create_task_record`).
6. Endpoint recibe `task_id`, actualiza el ticket: `task_id`, `status=done`, `resolved_at`.
7. Retorna `{ticket_id, task_id, status: "done"}`.

### 1.3 Edge Cases Relevantes para MVP

| Escenario | Comportamiento actual | Comportamiento esperado |
|-----------|----------------------|------------------------|
| `execute_flow` retorna `None` (error interno capturado en `_run_crew`) | El endpoint asigna `task_id=None` al ticket y lo marca `done` | El ticket debe marcarse `blocked` con nota descriptiva |
| Flow lanza excepción ANTES de crear task record | Se captura, ticket se marca `blocked` | Correcto, pero la nota debe incluir tipo de excepción y stack trace resumido |
| Flow lanza excepción DESPUÉS de crear task record | Se captura, ticket se marca `blocked`, pero el task ya existe con status `failed` | El ticket debe vincularse al `task_id` existente Y marcarse `blocked` |
| Error de DB al actualizar ticket post-ejecución | No se captura — genera 500 no manejado | Capturar explícitamente y retornar error 500 con mensaje claro |
| Ticket con notas previas | Las notas se sobrescriben | Las notas previas deben preservarse con append del nuevo error |
| Flow_type no registrado en registry | Se valida antes de ejecutar (404) | Correcto — ya implementado |

### 1.4 Manejo de Errores — Qué ve el usuario

| Error | HTTP Status | Body de respuesta |
|-------|------------|-------------------|
| Ticket no encontrado | 404 | `{"detail": "Ticket not found"}` |
| Sin flow_type | 400 | `{"detail": "Ticket has no flow_type to execute"}` |
| Ya en ejecución / completado | 409 | `{"detail": "Ticket is already {status}"}` |
| Flow no registrado | 404 | `{"detail": "Flow type '{flow_type}' not found"}` |
| Error de ejecución del flow | 500 | `{"detail": "Flow execution failed: {mensaje}"}` |
| Error interno de infraestructura | 500 | `{"detail": "Internal server error: {mensaje}"}` |

---

## 2. Diseño Técnico

### 2.1 Componentes involucrados

| Componente | Archivo | Rol |
|-----------|---------|-----|
| `execute_ticket` endpoint | `src/api/routes/tickets.py` | Orquestador de la ejecución del ticket |
| `execute_flow` función | `src/api/routes/webhooks.py` | Wrapper de ejecución asíncrona de flows |
| `BaseFlow.execute()` | `src/flows/base_flow.py` | Lifecycle completo del flow con `with_error_handling` |
| `with_error_handling` decorator | `src/flows/base_flow.py` | Captura excepciones, marca state como FAILED, persiste, re-lanza |
| `BaseFlowState.fail()` | `src/flows/state.py` | Transición de estado a FAILED |

### 2.2 Interfaces — Inputs/Outputs

#### Input del endpoint
```
POST /tickets/{ticket_id}/execute
Headers: X-Org-ID: <string>
Body: ninguno
```

#### Output en éxito
```json
{
  "ticket_id": "uuid",
  "task_id": "uuid",
  "status": "done"
}
```

#### Output en error de ejecución
```json
{
  "detail": "Flow execution failed: <mensaje>"
}
```
El ticket queda en DB con:
- `status = "blocked"`
- `notes = "Execution error: [<TipoExcepción>] <mensaje>\n<stack_trace_resumido>"`
- `task_id = "<task_id_si_se_alcanzo_a_crear>"` (puede ser null)

### 2.3 Modelo de datos — extensiones

No se requieren cambios al schema de `tickets`. El campo `notes` (TEXT) ya existe y es suficiente.

**Convención de formato para `notes` en caso de error:**
```
[<timestamp UTC>] Execution failed: <ExceptionType>: <message>
Task ID: <task_id o "N/A">
Traceback (last 3 lines): <resumen de las últimas 3 líneas del stack trace>
```

Esto es viable porque `notes` es TEXT y no tiene límite de longitud práctico en Postgres.

### 2.4 Flujo de ejecución con manejo de errores refactorizado

```
POST /tickets/{id}/execute
  │
  ├─ 1. Validar ticket existe, tiene flow_type, status permite ejecución
  │
  ├─ 2. PATCH ticket → status=in_progress
  │
  ├─ 3. try:
  │       task_id = await execute_flow(...)
  │
  │       # Post-validación: execute_flow puede retornar None
  │       if task_id is None:
  │           → PATCH ticket → status=blocked, notes="Execution returned None..."
  │           → HTTP 500
  │
  │   except Exception as exc:
  │       → Obtener task_id del state del flow si está disponible
  │       → PATCH ticket → status=blocked, notes=formatted_error(exc)
  │       → HTTP 500
  │
  └─ 4. PATCH ticket → task_id, status=done, resolved_at
```

### 2.5 Función auxiliar de formateo de error

Se debe crear una función privada en el módulo `tickets.py`:

```python
def _format_error_notes(exc: Exception, task_id: Optional[str] = None) -> str:
    """Format error information for ticket notes with timestamp and context."""
    import traceback
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    exc_type = type(exc).__name__
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    # Últimas 3 líneas relevantes del traceback
    tb_summary = "".join(tb_lines[-3:]).strip().replace("\n", " | ")
    
    parts = [
        f"[{ts}] Execution failed: {exc_type}: {str(exc)}",
        f"Task ID: {task_id or 'N/A'}",
    ]
    if tb_summary:
        parts.append(f"Traceback: {tb_summary}")
    return "\n".join(parts)
```

---

## 3. Decisiones

### D1: Preservar notas previas con append vs. sobrescribir
**Decisión:** Append con separador visual.  
**Justificación:** Un ticket puede haber tenido notas manuales de un operador antes de la ejecución. Sobrescribir destruye información. Se usará el formato:
```
<notas previas si existen>

---
[<timestamp>] Execution failed: ...
```
Si `notes` era `null` o vacío, solo se escribe el error.

### D2: No re-lanzar HTTPException tras marcar como blocked
**Decisión actual:** El código actual hace `raise HTTPException(...)` DESPUÉS de marcar el ticket como `blocked`.  
**Decisión:** Mantener este comportamiento. El cliente debe recibir un 500 explícito. El ticket queda como evidencia del fallo en la base de datos.

### D3: Obtener task_id del flow state en caso de error
**Decisión:** Si el flow ya creó el task record antes de fallar, el `task_id` debe vincularse al ticket incluso si el flow falló.  
**Justificación:** Esto permite trazabilidad completa — el ticket apunta al task que intentó ejecutar, y el task tiene el estado `failed` con el error detallado en su propia tabla.

**Problema:** `execute_flow` actualmente no expone el `task_id` si falla, porque retorna `None` en su `except`.  
**Resolución:** Se necesita que `execute_flow` retorne una tupla `(task_id_or_none, error_or_none)` O que el endpoint tenga acceso al state del flow tras el fallo.

**Opción seleccionada:** Modificar mínimamente `execute_flow` para que en lugar de retornar `Optional[str]`, retorne un `Dict[str, Any]` con `{"task_id": ..., "error": ...}`. Esto es un cambio en `webhooks.py` que está dentro del alcance porque es el motor de ejecución que este endpoint consume.

**Refactor de `execute_flow` en `webhooks.py`:**

```python
async def execute_flow(...) -> Dict[str, Any]:
    try:
        flow_class = flow_registry.get(flow_type)
        flow = flow_class(org_id=org_id)
        result_state = await flow.execute(input_data, correlation_id)
        task_id = result_state.task_id if result_state else None
        
        if callback_url:
            await _send_callback(callback_url, result_state)
        
        return {"task_id": task_id, "error": None}
    except Exception as exc:
        logger.error("Background flow execution failed: %s", exc)
        # Intentar obtener task_id si el flow alcanzó a crearlo
        task_id = getattr(getattr(flow, 'state', None), 'task_id', None)
        return {"task_id": task_id, "error": str(exc), "error_type": type(exc).__name__}
```

### D4: No agregar logging adicional significativo
**Decisión:** El logging actual con `logger.error` en `with_error_handling` y en `execute_flow` es suficiente. No agregar logs redundantes en el endpoint.

---

## 4. Criterios de Aceptación

- [ ] Si el flow se ejecuta exitosamente, el ticket queda con `status=done`, `task_id` vinculado y `resolved_at` establecido.
- [ ] Si el flow lanza una excepción, el ticket queda con `status=blocked` y `notes` contiene: timestamp, tipo de excepción, mensaje y task_id (si aplica).
- [ ] Si `execute_flow` retorna sin task_id (None), el ticket se marca `blocked` con nota "Execution returned None".
- [ ] Si el ticket tenía notas previas, estas se preservan y el error se agrega debajo con separador.
- [ ] Si el flow ya creó el task record antes de fallar, el ticket vincula ese `task_id` aunque quede `blocked`.
- [ ] El endpoint retorna HTTP 500 con `detail` descriptivo en todos los casos de error de ejecución.
- [ ] El endpoint NO modifica el archivo `webhooks.py` de forma que rompa el webhook trigger existente (`POST /webhooks/trigger`).
- [ ] No se introduce ningún cambio de schema de base de datos.

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Cambiar la firma de `execute_flow` rompe `POST /webhooks/trigger` | Media | Alto | El webhook endpoint usa `background_tasks.add_task()` y no utiliza el valor de retorno de `execute_flow`. El cambio de `Optional[str]` a `Dict` es transparente para ese caller. Verificar en implementación. |
| El traceback puede ser muy largo para el campo `notes` | Baja | Medio | Limitar a últimas 3 líneas del traceback como se definió en D1. |
| Concurrencia: dos requests simultáneas al mismo ticket | Media | Alto | El estado `in_progress` ya actúa como lock — si un segundo request llega, el check `if ticket.get("status") in ("in_progress", "done")` lo rechaza con 409. Mantener esta validación. |
| El flow falla silenciosamente (captura excepción internamente pero no re-lanza) | Baja | Medio | `with_error_handling` en `BaseFlow` siempre re-lanza con `raise`. Si algún flow custom no usa el decorator, el `execute_flow` tiene su propio `except` como red de seguridad. |

---

## 6. Plan de Implementación

### Tareas atómicas

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1 | Crear función `_format_error_notes(exc, task_id, prev_notes)` en `tickets.py` | Baja | Ninguna |
| 2 | Refactorizar `execute_flow` en `webhooks.py` para retornar `Dict[str, Any]` con `task_id`, `error`, `error_type` | Media | Ninguna |
| 3 | Actualizar el caller en `POST /webhooks/trigger` para que ignore el nuevo formato de retorno (no lo usa) | Baja | Tarea 2 |
| 4 | Refactorizar bloque `try/except` en `execute_ticket`: usar nuevo retorno de `execute_flow`, validar `task_id is not None`, formatear notas con `_format_error_notes` | Media | Tareas 1, 2 |
| 5 | Agregar bloque `try/except` interno para errores de DB al actualizar el ticket post-ejecución | Baja | Tarea 4 |
| 6 | Ejecutar tests existentes (si hay) y validar manualmente con un flow que falle | Media | Tarea 5 |

### Orden recomendado

```
T1 → T2 → T3 → T4 → T5 → T6
```

T1 y T2 pueden hacerse en paralelo. T3 depende de T2. T4 depende de T1, T2 y T3.

---

## 🔮 Roadmap (NO implementar ahora)

- **Reintento automático de tickets bloqueados:** Agregar botón "Retry" en la UI que re-intente la ejecución del flow, limpiando notas previas o marcándolas como "reintentado".
- **Categorización automática de errores:** Distinguir entre errores de infraestructura (DB, red) y errores de lógica del flow para manejarlos de forma diferenciada.
- **Alerting proactivo:** Si un ticket queda `blocked`, disparar notificación al admin de la org.
- **Timeout de ejecución:** Si un flow tarda más de X segundos, marcar el ticket como `blocked` con timeout error. Actualmente no hay timeout configurado en `execute_flow`.
- **Eventos de ticket:** Emitir eventos de dominio (`ticket.execution_started`, `ticket.execution_failed`, `ticket.completed`) al EventStore para trazabilidad completa en transcripts futuros.
- **Correlation_id en tickets:** Vincular explícitamente el `correlation_id` al ticket para búsqueda cruzada en logs (mencionado en paso 1.2 — no bloquear esa implementación).