# Análisis Técnico — Paso 1.1: Refactorizar `/tickets/{id}/execute`

## 1. Diseño Funcional

### Happy Path
1. Usuario dispara `POST /tickets/{id}/execute`
2. Endpoint valida que ticket existe, tiene `flow_type`, y no está ya en ejecución
3. Cambia status del ticket a `in_progress`
4. Ejecuta el Flow asociado vía `execute_flow()`
5. Al completar exitosamente: vincula `task_id`, cambia status a `done`, setea `resolved_at`
6. Retorna `{ticket_id, task_id, status: "done"}`

### Edge Cases MVP
| Escenario | Comportamiento Actual |是否符合MVP |
|------------|------------------------|--------------|
| Ticket no existe | 404 Not Found | ✅ |
| Ticket sin `flow_type` | 400 Bad Request | ✅ |
| Ticket ya `in_progress` o `done` | 409 Conflict | ✅ |
| Flow no registrado en registry | 404 Not Found | ✅ |
| **Ejecución del Flow falla** | Captura excepción → status=`blocked`, error en `notes` | ✅ |
| `execute_flow()` retorna None | Trata como error | ✅ |

### Manejo de Errores
- **Error en ejecución del Flow:** 
  - Status cambia a `blocked`
  - Campo `notes` se actualiza con: `"Execution error: {detalle_excepción}"`
  - Retorna 500 con mensaje de error
  - Usuario puede reintentar tras resuelve el problema

---

## 2. Diseño Técnico

### Componentes Modificados
- **`src/api/routes/tickets.py`** — Endpoint `execute_ticket()` (líneas 209-301)

### Flujo de Datos
```
POST /tickets/{ticket_id}/execute
         ↓
requires org_id (middleware)
         ↓
get_ticket() → valida existencia
         ↓
validate flow_type y status
         ↓
update status = "in_progress"
         ↓
correlation_id = f"ticket-{ticket_id}"  ←YA se genera correctamente
         ↓
execute_flow(flow_type, org_id, input_data, correlation_id)
         ↓
[Éxito] → update task_id, status="done", resolved_at
[Error] → update status="blocked", notes=error
```

### Modelo de Datos Existente
- `tickets`: id, org_id, title, description, flow_type, priority, status, input_data, task_id, created_by, assigned_to, notes, created_at, updated_at, resolved_at
- `tasks`: id, org_id, flow_type, flow_id, status, payload, correlation_id, result, error, created_at, updated_at

### Interfaces
```python
# Endpoint
@router.post("/{ticket_id}/execute")
async def execute_ticket(ticket_id: str, org_id: str = Depends(require_org_id))

# Response (éxito)
{"ticket_id": str, "task_id": str, "status": "done"}

# Response (error HTTP)
{"detail": "Flow execution failed: {mensaje}"}
```

---

## 3. Decisiones

### Decisión 1: Captura de Excepciones en Ejecución
**Estado:** YA IMPLEMENTADO  
**Justificación:** Líneas 274-285 en `tickets.py` capturan cualquier excepción de `execute_flow()`, actualizan el ticket a status `blocked` con el mensaje de error en `notes`, y lanzan HTTPException 500.

### Decisión 2: Formato correlation_id
**Estado:** YA IMPLEMENTADO  
**Justificación:** Línea 263 genera `correlation_id = f"ticket-{ticket_id}"` propagándose correctamente a `BaseFlow.create_task_record()` → tabla `tasks`.campo `correlation_id`.

> ⚠️ **VERIFICACIÓN REQUERIDA:** En `base_flow.py:176`, el `correlation_id` seinserta en la tabla `tasks`. Confirmar que esto es correcto según requerimiento Paso 1.2.

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable Via |
|---|----------|-----------------|
| 1 | Si `execute_flow()` lanza excepción, ticket.status = `blocked` | Query DB: `SELECT status FROM tickets WHERE id='{id}'` |
| 2 | Si `execute_flow()` lanza excepción, ticket.notes contiene el error | Query DB: `SELECT notes FROM tickets WHERE id='{id}'` |
| 3 | Si ejecución exitosa, ticket.status = `done` y task_id populated | Query DB: `SELECT task_id, status FROM tickets WHERE id='{id}'` |
| 4 | correlation_id se propaga desde ticket hasta task | Query DB: `SELECT correlation_id FROM tasks WHERE id='{task_id}'` |
| 5 | Endpoint retorna 500 con detalle en body si falla | API call y verificar response |

---

## 5. Riesgos

### Riesgo 1: execute_flow() retorna None silenciosamente
**severidad:** Media  
**Descripción:** En `webhooks.py:126`, si `execute_flow()` falla, retorna `None` en lugar de lanzar. El código actual en `tickets.py:266` asume que `task_id` siempre tiene valor. Si retorna None, línea 291 intentará setear `task_id=None` lo cual puede ser problemático.  
**Mitigación:** Verificar `task_id` antes de actualizar. Si es None, mantener status `blocked` con nota de "Flow execution returned no task_id".

### Riesgo 2: Race condition en status
**severidad:** Baja  
**Descripción:** Dos llamadas concurrentes a `/execute` para el mismo ticket podrían ambas pasar la validación de status.  
**Mitigación:** Usar transacción con `SELECT FOR UPDATE` o verificar status dentro del update transaction. No crítico para MVP.

---

## 6. Plan

### Tareas Atómicas
| # | Tarea | Complejidad | Depende De |
|----|-------|------------|-----------|
| 1 | Verificar que código actual maneja excepciones correctamente | Baja | — |
| 2 | Añadir verificación de `task_id is None` antes de update | Baja | 1 |
| 3 | Test manual: crear ticket con flow_type inválido y ejecutar | Baja | 2 |
| 4 | Test manual: crear ticket con flow_type válido y verificar correlación | Baja | 2 |

> **NOTA:** Las tareas 1-2 son **verificaciones menores**. El código YA implementa los requisitos del Paso 1.1. Solo se necesita ajustes menores ( task_id=None).

### Estimación Total
**Complejidad:** Baja  
**Tiempo estimado:** 1 hora

---

## 🔮 Roadmap (NO implementar ahora)

### Mejora 1: Status intermedio "executed" (no solo "done")
- Actualmente si el Flow termina, el ticket pasa directamente a `done`
- Considerar status intermedio `completed` que indica Flow terminado pero no necessarily exitoso
- Requiere modificar lógica en `tickets.py:288`

### Mejora 2: Retry automático con backoff
- Si el Flow falla por error transitorio (conectividad, timeout), reintentar automáticamente
- Configurar `max_retries` en el ticket o en input_data

### Mejora 3: Notificación asíncrona al crear ticket
- Enviar email/Slack cuando un ticket se crea o cambia a blocked
- Requiere integración con sistema de notificaciones (futura fase E7)