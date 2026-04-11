# 🏛️ ANÁLISIS FINAL: Paso 1.2 — Estandarización del correlation_id

## 1. Resumen Ejecutivo
Este paso consolida la trazabilidad de extremo a extremo en FluxAgentPro v2. Aunque el `correlation_id` ya se propaga en flujos de tickets, carece de una estandarización total en todas las fuentes de entrada y de una persistencia eficiente en la capa de eventos. 

El objetivo es transformar el `correlation_id` de una simple etiqueta informativa en la tabla `tasks` a un metadato de primer nivel indexado en `domain_events`. Esto permitirá que el futuro sistema de **Run Transcripts (E6)** recupere toda la "línea de pensamiento" de un ticket con una única consulta de alto rendimiento, vinculando múltiples intentos de ejecución (tasks) bajo un mismo hilo conductor.

## 2. Diseño Funcional Consolidado
Se define que CADA ejecución en el sistema debe tener un `correlation_id` con prefijo semántico.

### Happy Path: Orígenes y Formatos
- **Tickets:** Prefijo `ticket-{uuid}` (Origen: `src/api/routes/tickets.py`).
- **Webhooks:** Prefijo `webhook-{uuid}` (Origen: `src/api/routes/webhooks.py`).
- **Chat/Architect:** Prefijo `chat-{conversation_id}` (Origen: `src/api/routes/chat.py`).
- **Manual (Dev/Swagger):** Prefijo `manual-{flow_type}-{org_id[:8]}-{short_uuid}` para evitar colisiones en ejecuciones rápidas (Origen: `src/api/routes/flows.py`).

### Manejo de Edge Cases
- **Re-ejecución:** Si un ticket `blocked` se re-lanza, mantiene su `correlation_id` original pero genera un nuevo `task_id`. Esto permite agrupar todos los intentos fallidos y exitosos de una misma solicitud.
- **Falta de ID:** Si un `BaseFlow` se instancia sin ID, se generará uno con prefijo `internal-` y se emitirá un `logger.warning`.

## 3. Diseño Técnico Definitivo

### 3.1 Infraestructura de Datos (SQL)
Se añade la columna directamente a la tabla de eventos para evitar JOINs costosos durante el streaming de transcripts.
- **Tabla:** `domain_events`
- **Cambio:** Agregar columna `correlation_id` (TEXT, nullable).
- **Índice:** `idx_domain_events_correlation` sobre `(org_id, correlation_id)`.

### 3.2 Componentes Core (Python)
- **`src/events/store.py`**: Actualizar `DomainEvent` y `EventStore` para aceptar y persistir el `correlation_id` en la nueva columna de Postgres.
- **`src/flows/base_flow.py`**: Refactorizar `emit_event` para que extraiga automáticamente el `correlation_id` de `self.state` e inyecte el valor en el `EventStore`. 
- **`src/flows/state.py`**: Mantener `correlation_id` como obligatorio en el estado inicial del flujo.

### 3.3 Refactorización de Routers
- Estandarizar la generación de IDs en todos los puntos de entrada utilizando los prefijos definidos en la sección 2.

## 4. Decisiones Consolidadas
- **D1: Columna en Domain Events (Antigravity):** Se elige sobre la propuesta de Claude de "no hacer nada". La trazabilidad vía `tasks` requiere JOINs que degradan la experiencia de "Real-time Transcript". La persistencia directa en eventos es la decisión arquitectónica correcta para escalabilidad.
- **D2: Unicidad en Manual Flows (Qwen):** Se adopta el sufijo de UUID corto para ejecuciones manuales. Previene colisiones que identificamos como riesgo latente en el código actual de `flows.py`.
- **D3: Prefijos Semánticos:** Se descartan los UUIDs puros a favor de formatos legibles (human-readable) para facilitar el debugging en logs de producción.

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] Al ejecutar un ticket, todos los eventos de pensamiento (`agent_thought`) y acción en la DB comparten el prefijo `ticket-`.
- [ ] Ejecuciones manuales concurrentes del mismo flow generan `correlation_id` distintos.
- [ ] El `correlation_id` de un webhook es visible en la respuesta del API.

### Técnicos
- [ ] La tabla `domain_events` tiene la columna `correlation_id` y el índice correspondiente.
- [ ] El `EventStore` persiste exitosamente el campo sin errores de tipo.
- [ ] No hay regresiones: ejecuciones sin correlation_id (legacy) siguen funcionando (columna nullable).

### Robustez
- [ ] Si el `BaseFlow` recibe `None`, se registra un `warning` en Sentry/Logs pero la tarea se crea exitosamente.

## 6. Plan de Implementación
1. **Paso A [DB]:** Migración `021_add_event_correlation.sql`. (Complejidad: Baja).
2. **Paso B [Core]:** Actualización de `EventStore` y `DomainEvent`. (Complejidad: Media).
3. **Paso C [Flows]:** Inyección automática en `BaseFlow.emit_event`. (Complejidad: Baja).
4. **Paso D [API]:** Refactor de prefijos en `webhooks.py`, `flows.py` y `chat.py`. (Complejidad: Baja).
5. **Paso E [Test]:** Ejecutar suite de integración y verificar persistencia en `domain_events`.

## 7. Riesgos y Mitigaciones
- **Riesgo:** Volumen de datos en el nuevo índice de `domain_events`.
- **Mitigación:** El índice es compuesto `(org_id, correlation_id)`, lo que aprovecha el particionamiento lógico de Supabase por organización.
