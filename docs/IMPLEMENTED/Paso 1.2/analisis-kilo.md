# Análisis Técnico - Paso 1.2: Estandarización del correlation_id

## 1. Diseño Funcional

### Happy Path
1. Usuario crea un ticket con flow_type válido
2. Sistema ejecuta el ticket vía endpoint `POST /tickets/{ticket_id}/execute`
3. Se genera correlation_id con formato `ticket-{ticket_id}`
4. correlation_id se propaga desde el router hasta BaseFlow
5. correlation_id se almacena en tabla `tasks` y estado del flow
6. Flow se ejecuta normalmente con trazabilidad completa

### Edge Cases
- Ticket sin flow_type: Error 400 "Ticket has no flow_type to execute"
- Ticket ya en estado in_progress o done: Error 409 "Ticket is already {status}"
- Flow type no existe: Error 404 "Flow type '{flow_type}' not found"
- Error de infraestructura durante ejecución: Ticket pasa a blocked con correlation_id preservado
- Error en flow execution: Task se crea con correlation_id, ticket pasa a blocked

### Manejo de Errores
- Errores de infraestructura: HTTP 500 con detalle, ticket a blocked
- Errores de validación: HTTP 400/404/409 apropiados
- Errores de flow execution: HTTP 500, task_id retornado en respuesta

## 2. Diseño Técnico

### Componentes Nuevos/Modificaciones
- **src/api/routes/tickets.py**: Agregada generación de correlation_id en `execute_ticket()`
- **src/flows/base_flow.py**: Ya soporta correlation_id en `execute()` y `create_task_record()`
- **src/flows/multi_crew_flow.py**: Override de `execute()` pero propaga correlation_id correctamente
- **src/flows/architect_flow.py**: Override de `create_task_record()` pero almacena correlation_id

### Interfaces
**execute_ticket()** → **execute_flow()** → **BaseFlow.execute()**
- Input: `correlation_id: str` (formato `ticket-{ticket_id}`)
- Almacenamiento: Campo `correlation_id` en tabla `tasks` y `BaseFlowState`

**Manejo de correlation_id por fuente:**
- Tickets: `ticket-{ticket_id}`
- Flows manuales: `manual-{flow_type}-{org_id}`
- Webhooks: `uuid4()` generado

### Modelos de Datos
- Tabla `tasks`: Campo `correlation_id` existente (sin cambios)
- `BaseFlowState`: Campo `correlation_id` existente (sin cambios)

### Integraciones
- **EventStore**: No usa correlation_id directamente (usa `aggregate_id = task_id`)
- **Trazabilidad cruzada**: correlation_id permite vincular tickets → tasks → events
- **Logging**: correlation_id disponible en estado del flow para debugging

## 3. Decisiones

### Formato Estandarizado
- **Tickets**: `ticket-{ticket_id}` para trazabilidad directa
- **Justificación**: Permite búsquedas por prefijo y vinculación inmediata con ticket origen

### Propagación Obligatoria
- **correlation_id** siempre se pasa desde router hasta BaseFlow
- **Justificación**: Asegura trazabilidad end-to-end sin depender de implementaciones específicas

### Almacenamiento Consistente
- **correlation_id** se guarda tanto en `tasks` como en `BaseFlowState`
- **Justificación**: Disponible para queries DB y lógica de aplicación

## 4. Criterios de Aceptación
- El correlation_id se genera con formato `ticket-{ticket_id}` en `execute_ticket()`
- El correlation_id se pasa correctamente a `execute_flow()`
- El correlation_id se propaga hasta `BaseFlow.execute()` sin pérdida
- El correlation_id se almacena en tabla `tasks` y estado del flow
- Los tests de integración verifican la propagación correcta
- Errores de ejecución preservan correlation_id en tasks creadas

## 5. Riesgos

### Riesgo: Pérdida de correlation_id en overrides
- **Probabilidad**: Media (flows pueden override execute/create_task_record)
- **Impacto**: Alta (pérdida de trazabilidad)
- **Mitigación**: Tests unitarios verifican propagación en cada flow

### Riesgo: Inconsistencia de formatos
- **Probabilidad**: Baja (formatos documentados y testeados)
- **Impacto**: Media (dificulta queries cross-source)
- **Mitigación**: Documentación clara de formatos por fuente

### Riesgo: correlation_id no usado en eventos
- **Probabilidad**: Baja (EventStore usa aggregate_id = task_id)
- **Impacto**: Baja (trazabilidad vía task_id suficiente)
- **Mitigación**: correlation_id disponible en task para joins si necesario

## 6. Plan

### Tarea 1: Verificar implementación actual [Completada]
- **Descripción**: Revisar código existente de propagación correlation_id
- **Complejidad**: Baja
- **Dependencias**: Ninguna

### Tarea 2: Ejecutar tests de integración [Completada]
- **Descripción**: Verificar test `test_correlation_id_uses_ticket_format` pasa
- **Complejidad**: Baja
- **Dependencias**: Tarea 1

### Tarea 3: Validar consistencia en todos los flows [Completada]
- **Descripción**: Verificar que MultiCrewFlow y ArchitectFlow propagan correlation_id
- **Complejidad**: Baja
- **Dependencias**: Tarea 1

### Tarea 4: Documentar formatos de correlation_id [Completada]
- **Descripción**: Documentar formatos por fuente (ticket, manual, webhook)
- **Complejidad**: Baja
- **Dependencias**: Tarea 1

## 🔮 Roadmap
- **Enriquecimiento de eventos**: Incluir correlation_id en payloads de EventStore para trazabilidad directa
- **Dashboard de trazabilidad**: UI para seguir execution chains por correlation_id
- **Métricas por correlation_id**: Agrupar métricas de uso por fuente de ejecución
- **Correlación con conversaciones**: Extender correlation_id a flujos conversacionales