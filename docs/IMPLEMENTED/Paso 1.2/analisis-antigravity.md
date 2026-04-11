# 🧠 ANÁLISIS TÉCNICO: Paso 1.2 — Estandarización del correlation_id

## 1. Diseño Funcional
El objetivo es garantizar que cada acción realizada por el sistema agentino pueda ser rastreada hasta su origen (Ticket, Webhook, Chat Conversacional o Ejecución Manual) de forma unívoca y eficiente.

### Happy Path: Trazabilidad Extrema
1.  **Origen:** Una solicitud entra vía `POST /tickets/{id}/execute`.
2.  **Identificación:** El router genera un `correlation_id` con el formato `ticket-{id_ticket}`.
3.  **Propagación:** El ID viaja al `BaseFlow`, se guarda en la tabla `tasks` y se inyecta en el `BaseFlowState`.
4.  **Emisión de Eventos:** Cada vez que el flujo o un agente realiza una acción (ej. `agent_thought`, `tool_use`, `flow.completed`), el evento guardado en la tabla `domain_events` marca explícitamente ese `correlation_id`.
5.  **Consulta (Transcript):** El frontend puede solicitar el transcript completo de "todo lo relacionado con el ticket X" consultando `domain_events` por `correlation_id`, obteniendo una visión holística que sobrevive a reintentos o sub-tareas.

### Casos de Borde y Formatos Estandarizados
Se definen los siguientes prefijos obligatorios para el `correlation_id`:
-   **Tickets:** `ticket-{uuid}` (Ej: `ticket-550e8400-e29b...`)
-   **Webhooks:** `webhook-{uuid}`
-   **Chat (Architect):** `chat-{conversation_id}`
-   **Manual (Swagger/Dev):** `manual-{uuid}`

### Manejo de Errores
-   Si el `correlation_id` llega nulo al `BaseFlow` (no debería ocurrir con la estandarización), se generará uno por defecto con prefijo `internal-` para no romper la integridad de la base de datos, pero se marcará un warning en logs.

---

## 2. Diseño Técnico

### 2.1. Esquema de Base de Datos
Se requiere una migración para extender la tabla `domain_events`, permitiendo consultas de rendimiento O(1) o O(log n) por trazabilidad:
-   **Tabla:** `domain_events`
-   **Nueva Columna:** `correlation_id` (TEXT, nullable para retrocompatibilidad inicial).
-   **Índice:** `idx_domain_events_correlation` sobre `(org_id, correlation_id)`.

### 2.2. Componentes Core (Python)

#### `EventStore` (`src/events/store.py`)
-   Actualizar la dataclass `DomainEvent` para incluir el atributo `correlation_id`.
-   Modificar `append()` y `append_sync()` para aceptar este campo. El método `flush()` debe incluirlo en la inserción masiva.

#### `BaseFlow` (`src/flows/base_flow.py`)
-   El método `emit_event` debe extraer automáticamente el `correlation_id` de `self.state` y pasarlo al `EventStore`. Esto garantiza que los desarrolladores de flows no tengan que preocuparse por la trazabilidad manualmente.

### 2.3. Routers (API)
-   **`src/api/routes/webhooks.py`**: Cambiar la generación de `correlation_id = str(uuid4())` por `f"webhook-{uuid4()}"`.
-   **`src/api/routes/flows.py`**: Cambiar el formato manual (`manual-{flow_type}-{org_id}`) por `f"manual-{uuid4()}"` para evitar colisiones si se ejecutan dos veces el mismo flow para el mismo org en el mismo milisegundo.
-   **`src/api/routes/chat.py`**: Prefijar el `conversation_id` con `chat-`.

---

## 3. Decisiones

### D1: Columna vs Payload en `domain_events`
Se decide usar una **columna dedicada** en lugar de meter el `correlation_id` dentro del JSON de `payload`. 
-   *Justificación:* Facilita enormemente el filtrado y agregación en SQL (especialmente para el futuro motor de analítica y el componente `TranscriptTimeline.tsx`) sin penalizar el performance por parseo de JSON.

### D2: Prefijos Humanos
Se opta por prefijos (`ticket-`, `webhook-`, etc.) sobre IDs puros.
-   *Justificación:* Mejora radicalmente la experiencia de depuración (debugging) para los desarrolladores al inspeccionar tablas de eventos o logs de `structlog`.

---

## 4. Criterios de Aceptación
-   [X] **Migración:** La tabla `domain_events` cuenta con la columna `correlation_id` indexada.
-   [X] **Propagación:** Al ejecutar un ticket, la fila correspondiente en `tasks` y todas sus filas relacionadas en `domain_events` comparten el mismo `correlation_id` (iniciado con `ticket-`).
-   [X] **Estandarización Routers:** `webhooks/trigger` genera IDs con prefijo `webhook-`.
-   [X] **Contrato de EventStore:** La clase `EventStore` permite persistir el `correlation_id` sin necesidad de incluirlo manualmente en cada llamada a `append`.
-   [X] **Retrocompatibilidad:** Eventos antiguos (sin `correlation_id`) siguen siendo legibles por la API de transcripts.

---

## 5. Riesgos

### R1: Migración de datos existentes
-   *Impacto:* Bajo (es MVP).
-   *Mitigación:* La columna será `NULLABLE`. Se puede realizar un script de limpieza posterior que vincule `tasks.correlation_id` con `domain_events.correlation_id` basándose en `aggregate_id`.

### R2: Inconsistencia en Sub-flows
-   *Impacto:* Medio.
-   *Mitigación:* Si un flow dispara otro, el `BaseFlow` debe heredar el `correlation_id` del padre. Esto se validará específicamente en el paso de implementación.

---

## 6. Plan de Implementación

1.  **DB (Alta):** Crear y ejecutar migración `021_domain_events_correlation.sql`.
2.  **CORE (Media):** Refactorizar `DomainEvent` y `EventStore` en `src/events/store.py` para soportar la nueva columna.
3.  **CORE (Baja):** Actualizar `BaseFlow.emit_event` para inyección automática desde el estado.
4.  **API (Baja):** Actualizar routers `webhooks.py`, `flows.py` y `chat.py` con los nuevos formatos de prefijo.
5.  **Validación:** Prueba técnica cruzada lanzando ejecuciones desde las 4 fuentes y verificando la consistencia en DB.
