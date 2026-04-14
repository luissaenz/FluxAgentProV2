# 🧠 ANÁLISIS TÉCNICO: Paso 1.2 - Estandarización del `correlation_id`

**Agente:** qwen
**Contexto:** MVP FluxAgentPro v2 — Fase 1 (Hardening de Tickets)

---

## 1. Diseño Funcional

### Problema
El `correlation_id` es el hilo conductor que permite trazar una ejecución desde su origen (un ticket, un webhook, una ejecución manual) hasta su resultado en la tabla `tasks` y los `domain_events`. Actualmente:

- **`tickets.py`** genera el `correlation_id` con formato `ticket-{id}` (línea 320).
- **`webhooks.py`** genera un UUID aleatorio como `correlation_id`.
- **`flows.py`** (ejecución manual) genera `manual-{flow_type}-{org_id}`.
- El `correlation_id` se pasa a `execute_flow()` y de ahí a `BaseFlow.execute()`, que lo almacena en `BaseFlowState.correlation_id` y lo persiste en la tabla `tasks`.

**Sin embargo**, no existe garantía de que:
1. El formato del `correlation_id` sea consistente y predecible para cada origen.
2. El `correlation_id` del ticket se vincule correctamente al `task_id` creado por el flow.
3. Se pueda rastrear un ticket hasta todas sus tareas re-ejecutadas (un ticket puede fallar y re-ejecutarse, generando múltiples `task_id` pero un solo `correlation_id`).

### Happy Path Detallado
1. El usuario ejecuta un ticket vía `POST /tickets/{id}/execute`.
2. Se genera `correlation_id = f"ticket-{ticket_id}"`.
3. Se llama a `execute_flow()` con este `correlation_id`.
4. `BaseFlow.create_task_record()` inserta la fila en `tasks` con el `correlation_id` recibido.
5. Cualquier evento emitido durante la ejecución (vía `EventStore`) incluye implícitamente el `aggregate_id = task_id`, que puede cruzarse con `tasks.correlation_id`.
6. El operador puede consultar todas las tareas de un ticket haciendo `SELECT * FROM tasks WHERE correlation_id = 'ticket-{id}'`.

### Edge Cases (MVP)
- **Re-ejecución de ticket blocked:** Si un ticket se re-ejecuta, se genera un **nuevo** `task_id` pero se reutiliza el **mismo** `correlation_id`. Esto es correcto y deseable: permite ver el historial de intentos.
- **Ejecución directa vía `/flows/execute`:** No tiene ticket padre, por lo que el `correlation_id` usa formato `manual-{flow_type}-{org_id}`. No hay `ticket_id` que vincular, pero el formato es predecible.
- **Webhooks:** Cada webhook genera un UUID como `correlation_id`. No hay ticket padre. El formato es opaco pero trazable si se almacena la relación en un sistema externo.

### Manejo de Errores
- Si el `correlation_id` no se propaga correctamente (ej. `None`), la tarea se crea sin `correlation_id`. Esto no es un error fatal, pero rompe la trazabilidad. El análisis recomienda **validar explícitamente** que el `correlation_id` no sea `None` antes de crear la tarea.

---

## 2. Diseño Técnico

### Componentes Afectados
- **`src/api/routes/tickets.py`:** Ya genera `correlation_id = f"ticket-{ticket_id}"`. ✅ Correcto.
- **`src/api/routes/webhooks.py`:** Genera UUID. ✅ Aceptable para triggers externos.
- **`src/api/routes/flows.py`:** Genera `manual-{flow_type}-{org_id}`. ⚠️ Puede colisionar si se ejecuta el mismo flow múltiples veces para la misma org en corto tiempo.
- **`src/flows/base_flow.py`:** `create_task_record()` recibe `correlation_id` y lo persiste. ✅ Correcto.
- **`src/flows/state.py`:** `BaseFlowState.correlation_id` existe como campo. ✅ Correcto.

### Problema Identificado: `flows.py` — Colisión de `correlation_id`

En `src/api/routes/flows.py` (línea 151):
```python
correlation_id = f"manual-{flow_type}-{org_id}"
```

Este formato **no es único** si el mismo usuario ejecuta el mismo flow dos veces en rápida sucesión. Dos tareas tendrían el mismo `correlation_id`, haciendo imposible distinguirlas.

**Propuesta de resolución:** Sufijar con timestamp o UUID corto:
```python
correlation_id = f"manual-{flow_type}-{org_id[:8]}-{uuid4().hex[:6]}"
```

### Verificación del Contrato `correlation_id` en el Pipeline

| Origen | Formato Actual | ¿Único? | ¿Trazable? | Acción |
|--------|---------------|---------|------------|--------|
| Ticket | `ticket-{id}` | ✅ Sí (UUID) | ✅ Sí (1:1 con ticket) | Ninguna |
| Webhook | `{uuid4}` | ✅ Sí (UUID) | ✅ Sí (si se loguea) | Ninguna |
| Manual | `manual-{type}-{org}` | ❌ No | ⚠️ Parcial | **Agregar sufijo único** |

### Modelo de Datos
No se requieren cambios. La tabla `tasks` ya tiene columna `correlation_id` (texto nullable).

### Interfaces (Inputs/Outputs)

**`execute_flow()` signature actual:**
```python
async def execute_flow(
    flow_type: str,
    org_id: str,
    input_data: Dict[str, Any],
    correlation_id: str,
    callback_url: Optional[str] = None,
) -> Dict[str, Any]:
```
✅ `correlation_id` es `str` (no `Optional`). Correcto.

**`BaseFlow.execute()` signature actual:**
```python
async def execute(
    self,
    input_data: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> BaseFlowState:
```
⚠️ Aquí `correlation_id` es `Optional`. Esto es aceptable porque `BaseFlow` es una clase base que puede ser instanciada fuera del contexto de un router. Sin embargo, `create_task_record()` acepta `None` y lo persiste como tal.

**Propuesta:** Agregar un warning log si `correlation_id` es `None` en `create_task_record()`, para facilitar debugging en desarrollos futuros.

---

## 3. Decisiones

1. **Formato de `correlation_id` para ejecución manual:** Se cambiará de `manual-{flow_type}-{org_id}` a `manual-{flow_type}-{org_id[:8]}-{uuid4().hex[:6]}` para garantizar unicidad. **Justificación:** Sin el sufijo, ejecuciones simultáneas del mismo flow generan correlaciones colisionantes, imposibilitando el debugging y la auditoría.

2. **Logging de `correlation_id = None`:** Se agregará un `logger.warning` en `create_task_record()` si el `correlation_id` es `None`. **Justificación:** Es un síntoma de que alguien está instanciando un flow fuera del patrón establecido. Detectarlo temprano evita deuda de trazabilidad.

3. **No se crea tabla de correlaciones:** Para el MVP, la columna `correlation_id` en `tasks` es suficiente. Un sistema de correlaciones explícito (tabla `ticket_task_correlations`) queda para el roadmap.

---

## 4. Criterios de Aceptación

- [ ] **CA1:** El `correlation_id` generado en `tickets.py` tiene formato `ticket-{uuid}` y se persiste correctamente en `tasks.correlation_id`.
- [ ] **CA2:** El `correlation_id` generado en `flows.py` es único incluso para ejecuciones simultáneas del mismo flow y org.
- [ ] **CA3:** Un query `SELECT id, status FROM tasks WHERE correlation_id = 'ticket-{id}'` devuelve todas las ejecuciones (intentos) de ese ticket.
- [ ] **CA4:** Si `correlation_id` es `None` al crear una tarea, se emite un log de warning con el contexto del flow y org.
- [ ] **CA5:** El `correlation_id` del webhook trigger se retorna en la respuesta `WebhookTriggerResponse` y puede usarse para rastrear la tarea.

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
| :--- | :--- | :--- |
| **Colisión de `correlation_id` en ejecución manual** | Medio | Agregar sufijo UUID corto (decisión #1). |
| **`correlation_id = None` silencioso** | Bajo | Agregar warning log (decisión #2). |
| **Confusión entre `task_id` y `correlation_id`** | Bajo | Documentar la diferencia: `task_id` es único por ejecución, `correlation_id` agrupa reintentos del mismo origen. |

---

## 6. Plan

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1 | Modificar `flows.py` para generar `correlation_id` único con sufijo UUID | Baja | Ninguna |
| 2 | Agregar `logger.warning` en `create_task_record()` si `correlation_id` es `None` | Baja | Ninguna |
| 3 | Verificar que todos los callers de `execute_flow` pasan `correlation_id` no vacío | Baja | Ninguna |
| 4 | Prueba manual: ejecutar ticket, verificar `tasks.correlation_id = 'ticket-{id}'` | Baja | Tareas 1-3 |
| 5 | Prueba manual: ejecutar flow manual 2 veces, verificar `correlation_id` distinto | Baja | Tareas 1-3 |

**Estimación total:** Baja (3-5 cambios de código puntuales + verificación).

---

### 🔮 Roadmap (NO implementar ahora)

- **Tabla `correlation_chains`:** Para vincular explícitamente `correlation_id` con metadatos del origen (usuario, endpoint, timestamp, IP).
- **Propagación a `domain_events`:** Incluir `correlation_id` como campo en los eventos del EventStore para trazabilidad directa sin necesidad de JOIN con `tasks`.
- **Distributed tracing:** Integrar con sistemas como OpenTelemetry, usando `correlation_id` como `traceparent`.
- **Validación estricta:** Lanzar excepción si `correlation_id` es `None` en producción (no solo warning).
