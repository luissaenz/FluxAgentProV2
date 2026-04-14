# 📋 ANÁLISIS TÉCNICO — Paso 1.2: Estandarización del correlation_id

**Agente:** oc  
**Paso:** 1.2  
**Fecha:** 2026-04-11

---

## 1. Diseño Funcional

### 1.1 Comprensión del Paso

**Problema que resuelve:** Garantizar trazabilidad cruzada entre un ticket y su task de ejecución asociada mediante un identificador correlativo único y consistente.

**Inputs:**
- `ticket_id`: UUID del ticket en la tabla `tickets`

**Outputs:**
- `correlation_id`: String formateado como `ticket-{ticket_id}` propagado a través de toda la cadena de ejecución

**Rol en la fase:** Este paso es decorativo en términos de implementación nueva, ya que el patrón está implementado desde el paso 1.1 ( hardening de execute). La sección de "hardening" del paso 1.1 incluyó la preservación del `task_id` en errores, lo cual requiere el `correlation_id` para funcionar.

### 1.2 Happy Path

```
1. Usuario ejecuta POST /tickets/{id}/execute
2. Router genera correlation_id = f"ticket-{ticket_id}"
3. Router pasa correlation_id a execute_flow()
4. execute_flow() pasa correlation_id a flow.execute()
5. BaseFlow.create_task_record() inserta correlation_id en tabla tasks
6. BaseFlowState inicializa con correlation_id
7. Eventos emitidos incluyen correlation_id para trazabilidad
```

### 1.3 Edge Cases

| Edge Case | Manejo Actual | ¿MVP? |
|----------|----------------|-------|
| Ticket no encontrado | 404 antes de generar correlation_id | ✓ |
| Flow no encontrado en registry | 500 con error en execute_flow | ✓ |
| Excepción antes de create_task_record | correlation_id no existe en task, pero sí en logs | ✓ |
| Re-ejecución de ticket blocked | Nuevo correlation_id se genera en cada ejecución | ✓ |

### 1.4 Manejo de Errores

- Si el ticket no existe → HTTP 404 (before correlation_id generation)
- Si flow no encontrado → HTTP 500, correlation_id = `ticket-{id}-error`
- Si create_task_record falla → task insertada sin correlation_id pero con tracing en logs

---

## 2. Diseño Técnico

### 2.1 Componentes Involucrados

| Componente | Archivo | Rol |
|------------|---------|-----|
| Router | `src/api/routes/tickets.py:320` | Genera `correlation_id = f"ticket-{ticket_id}"` |
| execute_flow helper | `src/api/routes/webhooks.py:108` | Recibe y pasa correlation_id |
| BaseFlow.execute | `src/flows/base_flow.py:100` | Acepta correlation_id opcional |
| BaseFlow.create_task_record | `src/flows/base_flow.py:176` | Inserta correlation_id en tabla tasks |
| BaseFlowState | `src/flows/state.py:49` | Almacena correlation_id |

### 2.2 Modelos de Datos

**Tabla `tasks`:**
- Campo existente: `correlation_id` (text, nullable)
- Este paso no añade nuevos campos

**Tabla `domain_events`:**
- Campo existente: `correlation_id` (text)
- Evento enthält correlation_id para cross-referencing

### 2.3 Contratos Existentes

**Coherencia verificada con `estado-fase.md`:**
- ✓ `tickets.py` genera el formato `ticket-{ticket_id}` — coherente con decisión de "Trazabilidad"
- ✓ `execute_flow` retorna `Dict[str, Any]` con task_id y error — coherente con contrato de "Preservación de notas"
- ✓ `correlation_id` se propaga a `domain_events` — coherente con "EventStore como fuente de verdad"

---

## 3. Decisiones

### Decisión 1: Formato del correlation_id

| Decisión | Justificación |
|----------|---------------|
| `ticket-{ticket_id}` | Prefijo explícito permite identificación rápida en logs y EventStore sin consultar tabla tickets. Formato simple pero unambiguous. |

**Validación:** El formato actuales `ticket-{uuid}`. Ejemplo: `ticket-abc123-def456`.

### Decisión 2: Propagación opcional

| Decisión | Justificación |
|----------|---------------|
| `correlation_id` es Optional en BaseFlow | Flows legacy (como `/flows` directo) pueden no tener ticket origen. El parámetro es opcional para backward compatibility. |

---

## 4. Criterios de Aceptación

| # | Criterio | Verificación |
|---|----------|--------------|
| CA-001 | correlation_id se genera en formato `ticket-{ticket_id}` | Inspect código línea 320 tickets.py |
| CA-002 | correlation_id se pasa a execute_flow() | Inspect línea 327 tickets.py |
| CA-003 | correlation_id se almacena en tabla tasks | Query: `SELECT correlation_id FROM tasks WHERE correlation_id LIKE 'ticket-%'` |
| CA-004 | correlation_id aparece en domain_events | Query: `SELECT correlation_id FROM domain_events WHERE correlation_id LIKE 'ticket-%'` |
| CA-005 | Re-ejecución de blocked ticket genera nuevo correlation_id | Cada ejecución crea nuevo task_id, correlation_id es único por ejecución |
| CA-006 | Fallo antes de create_task_record no rompre ejecución | Error handling en tickets.py líneas 330-340 |

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|-------|--------|------------|
|correlation_id null en tasks por excepción temprana | Baja trazabilidad en casos de infraestructura | Logs de servidor contienen correlation_id en mensaje de error |
|Confusión con flows manual (formato `manual-{flow_type}-{org_id}`) | Ninguno — son flujos diferentes | Formato prefijado diferencia claramente origen |

**Nivel de riesgo técnico:** BAJO — El patrón ya está implementado y funcional.

---

## 6. Plan

### Tareas Atómicas

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1.1 | Verificar que tickets.py genera formato correcto | Baja | Ninguna |
| 1.2 | Verificar que correlation_id llega a tasks | Baja | 1.1 |
| 1.3 | Verificar que correlation_id llega a domain_events | Baja | 1.2 |
| 1.4 | Test de re-ejecución de blocked ticket genera nuevo correlation_id | Media | 1.3 |

### Estimación Total

- **Complejidad:** Baja
- **Tiempo estimado:** 1-2 horas (validación mayormente)
- **Dependencias externas:** Ninguna

### Estado de Implementación

> [!IMPORTANT]
> Tras análisis del código existente, **el paso 1.2 YA ESTÁ IMPLEMENTADO** en el código base. El formato, generación y propagación del `correlation_id` funciona correctamente:
> - Tickets.py línea 320: genera `correlation_id = f"ticket-{ticket_id}"`
> - Passed via execute_flow → flow.execute → create_task_record → persist en tasks table
> - Eventos contienen correlation_id para trazabilidad cruzada

**Acción recomendada:** Ejecutar validación de criterios de aceptación para confirmar funcionamiento end-to-end.

---

## 🔮 Roadmap (NO implementar ahora)

### 5.1 Correlation ID Enrichment

**Descripción:** Añadir metadatos adicionales al correlation_id: `ticket-{ticket_id}-{timestamp}` para soportar re-ejecuciones con mismo ticket_id.

**Bloqueador actual:** Ninguno — es enhancement opcional.

### 5.2 UI de Correlation ID

**Descripción:** Exponer correlation_id en el UI del ticket para que usuarios puedan buscar en logs/traces.

**Bloqueador actual:** Dashboard ticket detail no muestra correlation_id actualmente.

### 5.3 Dashboard Integration

**Descripción:** Enlace directo desde ticket detail a task detail usando correlation_id.

**Bloqueador actual:** Ninguno — es feature de UX.

---

## 📎 Referencias

- `src/api/routes/tickets.py:320` — Generación correlation_id
- `src/api/routes/webhooks.py:108` — execute_flow signature
- `src/flows/base_flow.py:100` — BaseFlow.execute signature
- `src/flows/base_flow.py:176` — create_task_record
- `src/flows/state.py:49` — BaseFlowState.correlation_id
- `docs/estado-fase.md` — Contratos vigentes