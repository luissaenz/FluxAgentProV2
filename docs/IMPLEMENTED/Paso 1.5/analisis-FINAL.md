# 🏛️ ANÁLISIS FINAL: PASO 1.5 - PRUEBA E2E DE CICLO DE VIDA (TICKETS)

## 1. Resumen Ejecutivo
Este paso constituye el hito de cierre de la **Fase 1 (Hardening de Tickets)**. Su objetivo es realizar una validación técnica y funcional rigurosa del ciclo completo de una solicitud, desde su entrada en el sistema hasta la persistencia de resultados y la generación de trazas de auditoría. 

Se busca certificar que las mejoras de robustez (Paso 1.1), trazabilidad (Paso 1.2) y feedback visual (Pasos 1.3 y 1.4) operan armónicamente, garantizando que FluxAgentPro no solo ejecute tareas, sino que sea un sistema gestionable y transparente.

## 2. Diseño Funcional Consolidado
- **Flujo Principal (Happy Path)**:
    1. **Entrada**: El usuario selecciona o crea un ticket con un `flow_type` registrado.
    2. **Disparo**: Al presionar "Ejecutar", la UI entra en estado `isExecuting` (spinner activo, fila pulsando).
    3. **Background**: El motor dispara el Flow propagando el `correlation_id`.
    4. **Cierre**: Tras el éxito, el ticket recibe el `task_id`, cambia su estado a `done` y la UI se refresca reactivamente.
- **Manejo de Robustez (Error Path)**:
    - Si el Flow falla (excepción o error lógico), el ticket debe quedar en estado `blocked`.
    - Se debe verificar que las `notes` del ticket no se sobrescriban, sino que se anexen con el stack trace o mensaje de error formateado con timestamp.
- **Edge Cases MVP**:
    - Ejecución de tickets cuya organización no tiene flows habilitados (Error 404/400).
    - Refresco de la tabla durante una ejecución larga (el estado debe persistir).

## 3. Diseño Técnico Definitivo
- **Arquitectura de Validación**:
    - **Capa de Transporte**: Inspección de headers `X-Task-Correlation-ID` en las peticiones API.
    - **Capa de Persistencia**: Verificación de integridad referencial entre `tickets.task_id` y `tasks.id`.
    - **Capa de Auditoría**: Análisis de la tabla `domain_events` filtrando por `correlation_id`.
- **Contratos Verificados**:
    - `POST /tickets/{id}/execute` -> Debe devolver el objeto `TicketResponse` completo en caso de éxito.
    - Formato de Trazabilidad: `ticket-{uuid}`.
- **Integración con Componentes**:
    - Se valida la interacción delegada entre `BaseFlow` y `EventStore` para el registro automático de eventos sin acoplamiento manual en cada flow.

## 4. Decisiones Tecnológicas
- **Validación Manual-Asistida**: Se opta por una validación manual documentada para el MVP, verificando los efectos secundarios en DB directamente, dado que la infraestructura de testing automatizado (Playwright/Cypress) queda para el roadmap.
- **Estado Reactivo**: Se confirma el uso de invalidación de queries de TanStack Query como mecanismo de sincronización, descartando WebSockets por ahora para mantener la simplicidad del MVP.

## 5. Criterios de Aceptación MVP ✅

### Funcionales
1. **Flujo Completo**: El usuario puede ejecutar un ticket y este llega al estado final (`done`/`blocked`) sin recarga manual. [ ]
2. **Vinculación**: El `task_id` es visible en la lista de tickets y permite navegar a la vista de tarea. [ ]
3. **Persistencia de Errores**: En caso de fallo, el motivo del error es visible en el campo de Notas del ticket. [ ]

### Técnicos
4. **Trazabilidad DB**: La columna `correlation_id` en la tabla `tasks` contiene el ID del ticket con prefijo `ticket-`. [ ]
5. **Eventos de Dominio**: Existe al menos un evento `flow.created` y `flow.completed` en `domain_events` con el `correlation_id` correcto. [ ]
6. **Integridad de Headers**: El backend propaga el correlation ID en los logs de ejecución. [ ]

### Robustez
7. **Feedback Proactivo**: Durante la ejecución, el botón muestra spinner y se bloquean las acciones de edición/eliminación. [ ]
8. **Recuperación**: Fallos en la red durante la ejecución no dejan al ticket atrapado en `in_progress` (el polling/refetch resuelve el estado final). [ ]

## 6. Plan de Implementación
1. **Tarea 1**: Configurar Escenario de Prueba (Crear Flows `Success_Test` y `Fail_Test`). (Baja)
2. **Tarea 2**: Ejecución de Ciclo de Éxito y Verificación de DB (Tasks/Events). (Media)
3. **Tarea 3**: Ejecución de Ciclo de Error y Verificación de Notas/Bloqueo. (Baja)
4. **Tarea 4**: Prueba de Interrupción (Cerrar pestaña durante ejecución y re-entrar). (Media)

## 7. Riesgos y Mitigaciones
- **Desconexión de EventStore**: Si el evento no se flashea, perdemos trazabilidad.
    - *Mitigación*: `BaseFlow` usa `EventStore.flush()` explícito antes de terminar.
- **Inconsistencia de Status**: Carrera en el cambio de estado de `in_progress` a `done`.
    - *Mitigación*: Se utiliza la respuesta directa del endpoint `/execute` para actualizar la UI antes del refetch de fondo.

## 8. Testing Mínimo Viable
- Generar un ticket → Ejecutarlo → Consultar `SELECT status, task_id FROM tickets WHERE id = ...`
- Provocar un error en el motor → Verificar `notes` del ticket.
- Click en el Task ID en el Dashboard → Debe cargar `tasks/[id]/page.tsx`.

## 9. 🔮 Roadmap (NO implementar ahora)
- **CI Assertions**: Integración de estas validaciones en el pipeline de GitHub Actions.
- **Log Stream**: Visualización del stream de logs del agente directamente en el detalle del ticket.
- **Batch Operations**: Ejecución masiva de tickets del backlog.
