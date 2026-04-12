# Análisis Técnico - Paso 1.5: Prueba E2E de ciclo de vida

## 1. Diseño Funcional

### Happy Path
1. Usuario crea un ticket vía API con `flow_type` válido (ej: "generic_flow") y datos de entrada
2. Sistema valida el `flow_type` y crea el ticket en estado "backlog"
3. Usuario ejecuta el ticket mediante POST /tickets/{id}/execute
4. Sistema valida el ticket (existe, tiene flow_type, no está en ejecución)
5. Sistema cambia el estado a "in_progress" temporalmente
6. Flow se ejecuta exitosamente, retornando `task_id` válido
7. Sistema actualiza el ticket: estado "done", `task_id` vinculado, `resolved_at` establecido
8. Respuesta incluye el objeto `TicketResponse` completo con cambios reflejados

### Edge Cases Relevantes para MVP
- **Ejecución falla por error en flow:** Flow retorna error, ticket queda "blocked" con `task_id` vinculado y notas de error appendeadas
- **Flow retorna resultado vacío:** Se trata como error, ticket "blocked" con mensaje "Unknown error"
- **Múltiples ejecuciones simultáneas:** Sistema previene con validación de estado (409 si ya in_progress)
- **Ticket con input_data vacío:** Auto-mapping para GenericFlow usa title/description como "text"

### Manejo de Errores
- **Error en creación de ticket:** Test falla inmediatamente (no se puede continuar)
- **Error de infraestructura en ejecución:** Ticket queda "blocked", error logged en notas, respuesta 500 con detalle
- **Flow no encontrado:** Validación previa impide ejecución (400 en create, pero test debe usar flow válido)
- **Ticket no encontrado en execute:** 404, test verifica manejo correcto

## 2. Diseño Técnico

### Componentes Nuevos o Modificaciones
- **Nuevo archivo de test:** `tests/e2e/test_ticket_lifecycle.py`
  - Clase `TestTicketLifecycle` con métodos de prueba
  - Usa `TestClient` con `httpx.ASGITransport` para ejecución in-process de background tasks
- **Fixture de app:** Similar a `test_webhook_to_completion.py`, pero incluyendo router de tickets

### Interfaces (Inputs/Outputs)
- **Input (Create):** `TicketCreate` con title, description, flow_type, input_data
- **Input (Execute):** Solo ticket_id en URL
- **Output (Create):** `TicketResponse` con id generado, status="backlog"
- **Output (Execute):** `TicketResponse` con status="done"/"blocked", task_id presente

### Modelos de Datos
- Sin cambios en modelos existentes (`TicketCreate`, `TicketResponse`)
- Usa tabla `tickets` existente con campos validados en estado-fase.md

### Integraciones
- **Endpoint POST /tickets:** Creación de ticket con validación de flow_type
- **Endpoint POST /tickets/{id}/execute:** Ejecución con manejo completo de estados
- **Flow Registry:** Mock para garantizar flows disponibles en test
- **Event Store:** Mock opcional si se necesita verificar eventos (no crítico para MVP)

## 3. Decisiones

- **Framework de testing:** Seguir patrón de `test_webhook_to_completion.py` con TestClient y httpx.ASGITransport para E2E API
- **Flows de prueba:** Mock de `flow_registry` con "success_flow" y "failing_flow" para controlar resultados
- **Verificación de estado:** Check directo en respuesta de execute (no GET adicional) para simplicidad
- **Correlation ID:** Verificar que se pasa como "ticket-{id}" al flow (consistente con Paso 1.2)
- **Task ID format:** Esperar UUID válido (no asumir formato específico)
- **Input data mapping:** Probar auto-mapping para GenericFlow cuando falta "text"

## 4. Criterios de Aceptación
- El ticket se crea exitosamente (201) con ID único y status="backlog"
- La ejecución exitosa retorna (200) con status="done", task_id no vacío y resolved_at presente
- La ejecución fallida retorna (500) con status="blocked", task_id presente y notas con error
- El task_id es un string no vacío en ambos casos de éxito y error
- El estado se persiste correctamente en base de datos (verifiable via GET posterior si necesario)
- El correlation_id se propaga correctamente al flow execution
- No hay race conditions: múltiples executes simultáneos en mismo ticket fallan apropiadamente

## 5. Riesgos

### Riesgos Concretos del Paso
- **Test timeout por flow que no termina:** Si el flow mock no retorna, test se cuelga
  - **Mitigación:** Usar AsyncMock con side_effect inmediato, timeout en TestClient

- **Inconsistencia en mocks:** DB mocks no reflejan updates reales del endpoint
  - **Mitigación:** Usar fixtures consistentes de test_tickets_execute.py, verificar llamadas de update

- **Dependencia de infraestructura:** Test requiere DB connection y flow registry operativo
  - **Mitigación:** Ejecutar en entorno de CI con dependencias mocked apropiadamente

- **Falsos positivos:** Test pasa pero estado real no se actualiza
  - **Mitigación:** Verificar tanto respuesta como estado en DB (GET después de execute)

## 6. Plan

1. **Crear estructura básica de test (Baja complejidad)**
   - Copiar patrón de test_webhook_to_completion.py
   - Añadir fixtures para ticket_app con routers incluidos
   - Crear test básico de create + execute + assert

2. **Implementar happy path (Media complejidad)**
   - Mock flow_registry con success_flow que retorna task_id
   - Probar flujo completo: create → execute → verificar done + task_id
   - Verificar auto-mapping de input_data

3. **Añadir escenarios de error (Media complejidad)**
   - Mock failing_flow que retorna error
   - Verificar blocked + task_id + notas de error
   - Probar edge cases: empty result, None result

4. **Verificar criterios de aceptación (Baja complejidad)**
   - Añadir asserts específicos para cada criterio
   - Probar correlation_id propagation
   - Verificar formato de task_id (UUID válido)

5. **Testing y validación manual (Baja complejidad)**
   - Ejecutar test en aislamiento
   - Verificar logs de ejecución
   - Confirmar que no rompe tests existentes

## 🔮 Roadmap

### Optimizaciones
- **Test con UI real:** Extender a Playwright para E2E full-stack (frontend + API)
- **Paralelización:** Ejecutar múltiples lifecycles en paralelo para performance
- **Test data factories:** Crear helpers para generar tickets de prueba con variaciones

### Mejoras
- **Integration con event store:** Verificar eventos de domain publicados durante ejecución
- **Performance asserts:** Medir tiempo de ejecución y alertar si > threshold
- **Cleanup automático:** Eliminar tickets de test después de ejecución

### Features Futuras
- **Multi-tenant verification:** Test que tickets de diferentes orgs no interfieran
- **Real-time validation:** Verificar transcripts en tiempo real durante ejecución (post E6)
- **Bulk lifecycle tests:** Crear y ejecutar múltiples tickets en batch
- **Load testing:** Simular alta concurrencia de ticket lifecycles

Decisiones tomadas pensando en roadmap:
- Arquitectura de test permite fácil extensión a UI testing (mismos endpoints)
- Verificación de task_id facilita integración con future transcript validation
- Mocks de flows permiten testing de diferentes tipos sin infraestructura real