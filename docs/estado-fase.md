# 🗺️ ESTADO DE FASE: FASE 3 - REAL-TIME RUN TRANSCRIPTS 🏗️

## 1. Resumen de Fase
- **Objetivo:** Implementar transparencia total en la ejecución de tareas de IA mediante el streaming de eventos en tiempo real (transcripts), permitiendo supervisar pensamientos de agentes y salidas de herramientas al instante.
- **Fase Anterior:** Fase 2 - Agent Panel 2.0 [FINALIZADA ✅]
- **Pasos de la Fase 3:**
    1. **3.1 [DB]:** Habilitar Supabase Realtime para la tabla `domain_events`. [COMPLETADO ✅]
    2. **3.2 [Backend]:** Refinar endpoint de Transcripts (Snapshot inicial + Sync metadata). [COMPLETADO ✅]
    3. **3.3 [Frontend]:** Crear componente `TranscriptTimeline.tsx` (Animaciones premium). [PRÓXIMO 🎯]
    4. **3.4 [Frontend]:** Integración en Vista de Tarea (`Live Transcript`).
    5. **3.5 [Validación]:** Test de Latencia (< 1s entre evento y visualización).

## 2. Estado Actual del Proyecto
- **Implementado y Funcional:**
    - **Snapshot de Transcripts (Paso 3.2):** Endpoint `GET /transcripts/{task_id}` optimizado. Entrega un historial filtrado con metadatos de sincronización (`last_sequence`) para permitir un hand-off perfecto hacia el cliente de Realtime. Validados estados terminales y aislamiento multi-tenant.
    - **Habilitación de Realtime (Paso 3.1):** Configuración de `REPLICA IDENTITY FULL` en la tabla `domain_events`. Validación automatizada mediante script `test_3_1_realtime.py`.
    - **Aislamiento Multi-tenant SOUL (Paso 2.5):** Verificación completa del aislamiento de identidad narrativa. Script automatizado `LAST/test_2_5_isolation.py` valida la seguridad en API y RLS.
    - **Agent Panel 2.0 (Fase 2):** Identidad narrativa (SOUL) y gestión de capacidades (Tools) integradas y funcionales en UI premium.
    - **Hardening de Tickets (Fase 1):** Ciclo de vida gestionado, persistencia de errores y trazabilidad vía `correlation_id`.

- **Parcialmente Implementado:**
    - **Timeline Frontend (Step 3.3):** El backend está listo para servir el snapshot. La siguiente tarea es implementar la visualización dinámica y la suscripción al stream de eventos.

## 3. Contratos Técnicos Vigentes
- **Transcript API (`GET /transcripts/{task_id}`):**
    - Payload: `{ task_id, status, is_running, sync: { last_sequence, has_more }, events: [...] }`
    - Filtro por defecto: `flow_step`, `agent_thought`, `tool_output`.
- **Realtime Infrastructure:**
    - `REPLICA IDENTITY FULL`: Configurada en `domain_events` para asegurar payloads completos en el stream.
    - RPC `debug_realtime_config()`: Herramienta de diagnóstico para salud de la publicación.
- **Seguridad y Aislamiento:**
    - Uso obligatorio de `TenantClient` (context manager) para garantizar multi-tenancy en consultas de eventos.
    - Filtrado de `tasks` por `id` y `org_id` antes de exponer eventos asociados.
- **Modelos y APIs Fase 2:**
    - `agent_metadata`: Identidad visual, display_name y soul_narrative.
    - `GET /agents/{id}/detail`: Contrato enriquecido con SOUL.

## 4. Decisiones de Arquitectura Tomadas
- **Hand-off Sincronizado:** El backend provee `last_sequence` en el snapshot. El frontend se suscribe a Realtime y descarta eventos filtrados con secuencia menor o igual a este valor para evitar saltos o duplicados.
- **IsRunning Derivado:** El estado de ejecución se calcula en el endpoint comparando el status actual contra un conjunto de `TERMINAL_STATES` (`done`, `failed`, `cancelled`, `blocked`).
- **Truncamiento Preventivo:** Uso de `limit + 1` en consultas de eventos para detectar `has_more` y manejar grandes volúmenes de eventos sin degradar performance.
- **Protocolo de Validación Rigurosa:** Empleo de scripts `test_3_x_*.py` en el directorio `LAST/` para asegurar que cada hito técnico cumple los 10 criterios de aceptación del MVP.

## 5. Registro de Pasos Completados (Fase 3 Progress)

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 3.2 | ✅ | `src/api/routes/transcripts.py`, `LAST/test_3_2_transcripts.py` | Snapshot Sync Logic | Implementación de streaming hand-off validada. |
| 3.1 | ✅ | `022_enable_realtime_events.sql` | `REPLICA IDENTITY FULL` | Realtime habilitado para domain_events. |
| 2.5 | ✅ | `test_2_5_isolation.py` | Seguridad Verificable | Validado Aislamiento Multi-tenant. |
| 2.4 | ✅ | `AgentToolsCard.tsx` | Transparencia Operativa | Mapeo de herramientas a descripciones legibles. |
| 2.3 | ✅ | `AgentPersonalityCard.tsx` | Identidad Visual | Estilo tipográfico diferenciado. |
| 2.2 | ✅ | `src/api/routes/agents.py` | Enriquecimiento API | LEFT JOIN con agent_metadata. |
| 2.1 | ✅ | `supabase/migrations/020...` | Esquema SOUL | Tabla con RLS por org_id. |

## 6. Criterios Generales de Aceptación MVP
- Los transcripts deben aparecer en la UI en tiempo real sin recarga de página.
- El desfase entre la base de datos y la UI debe ser imperceptible (< 1 segundo).
- La visualización debe diferenciar claramente entre: pensamientos, acciones y resultados de herramientas.

---
*Documento actualizado por el protocolo CONTEXTO de Antigravity tras la finalización exitosa del Paso 3.2.*


