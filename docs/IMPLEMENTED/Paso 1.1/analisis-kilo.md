# Análisis Técnico - Paso 1.1: Refactorización del Endpoint `POST /tickets/{id}/execute`

## 1. Diseño Funcional

### Happy Path
1. Usuario solicita ejecución de un ticket válido con `flow_type` asignado.
2. Sistema valida que el ticket existe, tiene `flow_type`, y no está en estado `in_progress` o `done`.
3. Ticket cambia a estado `in_progress`.
4. Se instancia el flow correspondiente y se ejecuta con `input_data` del ticket y `correlation_id = "ticket-{ticket_id}"`.
5. Flow completa exitosamente: ticket actualiza a `done`, vincula `task_id`, registra `resolved_at`.
6. Retorna respuesta con `ticket_id`, `task_id`, `status = "done"`.

### Edge Cases Relevantes para MVP
- **Ticket sin flow_type**: Error 400 "Ticket has no flow_type to execute".
- **Flow no registrado**: Error 404 "Flow type not found".
- **Ticket ya en ejecución**: Error 409 "Ticket is already in_progress/done".
- **Flow requiere aprobación HITL**: Flow pausa en `awaiting_approval`, ticket permanece `in_progress` hasta reanudación externa.
- **Ejecución falla por validación de input**: Flow lanza `ValueError`, ticket marca `blocked` con error en `notes`.
- **Ejecución falla por error en crew**: Excepción genérica, ticket marca `blocked` con error en `notes`.

### Manejo de Errores
- **Errores de validación previa**: HTTP 400/404/409 con mensaje descriptivo, sin modificar ticket.
- **Errores durante ejecución**: Capturar `Exception` del motor de flows, actualizar ticket a `blocked` con `notes = "Execution error: {str(exc)}"`, retornar HTTP 500 con detalle del error.

## 2. Diseño Técnico

### Componentes Nuevos o Modificaciones
- **Modificación al endpoint `POST /tickets/{id}/execute`**:
  - Reemplazar llamada a `execute_flow()` por instanciación directa del flow y llamada a `flow.execute()`.
  - Agregar manejo de excepciones post-instanciación para distinguir errores de setup vs. ejecución.

### Interfaces (Inputs/Outputs de Cada Componente)
- **Input del endpoint**: `ticket_id` (path), `org_id` (header).
- **Output del endpoint**: `{"ticket_id": str, "task_id": str, "status": str}`.
- **Interacción con BaseFlow**:
  - `flow = flow_registry.get(flow_type)(org_id=org_id)`
  - `state = await flow.execute(input_data, correlation_id)`
  - `task_id = state.task_id`

### Modelos de Datos Nuevos o Extensiones
- Sin cambios: utiliza modelos existentes `tickets`, `tasks`, `snapshots`, `domain_events`.

### Integraciones
- **Flow Registry**: Obtener clase de flow por `flow_type`.
- **BaseFlow**: Ejecutar lifecycle completo, manejar HITL si aplica.
- **EventStore**: Emisión automática de eventos durante ejecución (heredado de BaseFlow).

## 3. Decisiones

- **Ejecución síncrona vs. asíncrona**: Mantener ejecución síncrona en endpoint para respuesta inmediata, delegando async al flow interno. Evita complejidad de polling/status checks.
- **Propagación de correlation_id**: Usar `ticket-{ticket_id}` para trazabilidad end-to-end, consistente con contratos existentes.
- **Manejo de excepciones**: Capturar `Exception` amplia para robustez, pero distinguir entre errores de setup (pre-ejecución) y ejecución (post-setup) para logging granular.
- **Estado blocked vs. failed**: Usar `blocked` para errores recuperables (e.g., input inválido), permitiendo reintento manual. `failed` reservado para fallos irrecuperables.

## 4. Criterios de Aceptación
- El endpoint acepta POST a `/tickets/{id}/execute` con ticket válido y retorna 200 con task_id si ejecución exitosa.
- Si flow no existe, retorna 404 sin modificar ticket.
- Si ticket ya en progreso, retorna 409 sin modificar ticket.
- Si ejecución falla por cualquier Exception, ticket actualiza a `blocked`, campo `notes` incluye "Execution error: {mensaje}", y endpoint retorna 500.
- Tras éxito, ticket.status = "done", task_id vinculado, resolved_at establecido.
- Correlation_id "ticket-{ticket_id}" se propaga correctamente al flow y eventos.
- Flujos HITL pausan correctamente sin marcar ticket como done/blocked hasta resolución.

## 5. Riesgos
- **Cambios en BaseFlow.execute**: Si futuro refactor modifica retorno de execute(), ajustar asignación de task_id. Mitigación: tests unitarios de endpoint.
- **Excepciones no manejadas**: Imports faltantes o errores de DB en setup podrían no capturarse. Mitigación: testing exhaustivo de edge cases.
- **Impacto en webhooks**: Modificar execute_flow() podría afectar POST /webhooks/trigger si usado en background. Mitigación: mantener execute_flow() para webhooks, usar ejecución directa solo en tickets.
- **Rendimiento en flows largos**: Ejecución síncrona podría timeout en flows complejos. Mitigación: monitorear tiempos, considerar async background si >30s.

## 6. Plan
1. **Modificar endpoint en `src/api/routes/tickets.py`**: Reemplazar `execute_flow()` con instanciación directa de flow y `await flow.execute()`. Estimación: Baja (2-3 líneas de cambio).
2. **Agregar try-except post-instanciación**: Capturar excepciones de flow.execute(), actualizar ticket a blocked con notes. Estimación: Baja.
3. **Actualizar imports**: Agregar import de flow_registry si no presente. Estimación: Baja.
4. **Testing manual**: Crear ticket, ejecutar flow exitoso, verificar done/task_id. Estimación: Media (15 min).
5. **Testing de errores**: Simular fallo de flow (e.g., input inválido), verificar blocked/notes. Estimación: Media.

### Dependencias
- Depende de BaseFlow.execute() funcionando correctamente (ya validado en Fase 8 Baseline).
- No bloquea otros pasos; puede implementarse en paralelo con UI de tickets.

## 🔮 Roadmap
- **Reintentos automáticos**: Lógica para reintentar executions fallidas en blocked, con exponential backoff.
- **Notificaciones push**: WebSockets para actualizar UI en tiempo real durante ejecución.
- **Queueing asíncrono**: Para flows muy largos, delegar a background worker y retornar task_id inmediato.
- **Métricas de ejecución**: Integrar con sistema de métricas para tracking de success/failure rates por flow_type.</content>
<parameter name="filePath">D:\Develop\Personal\FluxAgentPro-v2\LAST\analisis-kilo.md