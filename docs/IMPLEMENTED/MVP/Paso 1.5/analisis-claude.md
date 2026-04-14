# 🧠 ANÁLISIS TÉCNICO: PASO 1.5 - PRUEBA E2E DE CICLO DE VIDA

## Perfil del Rol
Este análisis documenta la validación E2E del ciclo completo de Tickets en FluxAgentPro v2.

---

## 1. Comprensión del Paso

### Objetivo
Verificar que el ciclo de vida completo de un ticket funciona end-to-end: creación → ejecución → vinculación de `task_id` → cambio de estado.

### Inputs del Sistema Validado
- **Frontend:** `tickets/page.tsx`, `useExecuteTicket` hook
- **Backend:** `POST /tickets/{id}/execute`, `GenericFlow`
- **Base de datos:** Tabla `tickets` con campos `id`, `status`, `task_id`, `notes`
- **Trazabilidad:** `correlation_id` propagado como `ticket-{id}`

### Outputs Verificados
- Ticket con `task_id` asignado post-ejecución
- Estado cambia a `in_progress`, `done` o `blocked`
- Historial de errores persiste en `notes` si aplica
- Eventos de dominio grabados en `domain_events`

### Rol en la Fase
Este es el paso de **validación consolidada** de la Fase 1 (E4). No implementa funcionalidad nueva; valida que todos los componentes de hardening trabajan en conjunto.

---

## 2. Supuestos y Ambigüedades

| # | Ambigüedad | Resolución |
|---|------------|------------|
| A1 | ¿Qué significa "ciclo completo"? | Crear ticket → Ejecutar → Verificar `task_id` + estado |
| A2 | ¿Qué estados son válidos post-ejecución? | `in_progress` (si el flow tarda), `done` (si completa), `blocked` (si falla) |
| A3 | ¿Se requiere backend corriendo? | Sí — la validación es real, no mock |
| A4 | ¿Qué pasa si el flow no existe? | Backend retorna error 400/404, ticket pasa a `blocked` con error en `notes` |

---

## 3. Diseño Funcional - Happy Path Validado

```
1. [Frontend] Usuario crea ticket con flow_type = "coctel_flow"
   → POST /tickets → Ticket creado con status = "backlog"

2. [Frontend] Usuario hace clic en Play
   → POST /tickets/{id}/execute

3. [Backend] GenericFlow recibe correlatio_id = "ticket-{id}"
   → Flow ejecuta
   → Task creada en base de datos
   → domain_events grabados

4. [Backend] Response: { id, status: "in_progress"|"done"|"blocked", task_id: "xxx", notes: null|error }

5. [Frontend] useExecuteTicket recibe respuesta
   → toast.success("Ticket ejecutado correctamente (Task: {short_id})")
   → invalidateQueries(['tickets'], ['ticket', ticketId])

6. [Frontend] Tabla refresca automáticamente
   → Fila muestra nuevo status
   → Columna "Task" muestra task_id como link
```

### Edge Cases Validados

| Escenario | Resultado Esperado |
|-----------|---------------------|
| Ticket sin `flow_type` | Botón Play no aparece |
| Ticket en estado terminal | Botón Play no aparece |
| Flow no existe en registry | Ticket pasa a `blocked`, `notes` contiene error |
| Error de red | Toast "Error de conexión" |
| Error de API | Toast con mensaje del backend |
| Backend caído | Toast "Error de conexión" |

---

## 4. Diseño Técnico - Componentes Validados

### Backend
| Componente | Archivo | Validado |
|------------|---------|----------|
| Endpoint execute | `src/api/routes/tickets.py` | ✅ |
| generic_flow | `src/flows/coctel_flows.py` | ✅ |
| correlation_id | `src/flows/state.py` | ✅ |
| domain_events | `src/events/event_store.py` | ✅ |

### Frontend
| Componente | Archivo | Validado |
|------------|---------|----------|
| TicketsPage | `dashboard/app/(app)/tickets/page.tsx` | ✅ |
| useExecuteTicket | `dashboard/hooks/useTickets.ts` | ✅ |
| useTickets | `dashboard/hooks/useTickets.ts` | ✅ |
| Toasts (Sonner) | `useTickets.ts` | ✅ |

### Contratos Verificados

| Contrato | Valor |
|----------|-------|
| correlation_id formato | `ticket-{id}` |
| task_id formato | UUID v4 (16 chars min para display) |
| Status post-ejecución | `in_progress`, `done`, o `blocked` |
| Notas de error | Persistidas en `ticket.notes` |

---

## 5. Decisiones Tecnológicas

No hay nuevas decisiones — este paso valida decisiones tomadas en pasos anteriores:

| Decisión | Paso Anterior | Validada |
|----------|---------------|----------|
| correlation_id como clave de trazabilidad | 1.2 | ✅ |
| Toast de carga/éxito/error | 1.3 | ✅ |
| Spinner por fila en execute | 1.4 | ✅ |
| Invalidación de queries en `onSettled` | 1.4 | ✅ |

---

## 6. Plan de Validación

### Tareas de Verificación

| # | Tarea | Método | Complejidad |
|---|-------|--------|-------------|
| V1 | Crear ticket con flow_type válido | UI: click en "Nuevo Ticket" | Baja |
| V2 | Ejecutar ticket | UI: click en Play | Baja |
| V3 | Verificar spinner aparece en fila correcta | Visual | Baja |
| V4 | Verificar toast de éxito con task_id | Visual | Baja |
| V5 | Verificar tabla refresca sin recarga | Visual | Baja |
| V6 | Verificar task_id en columna "Task" | Visual | Baja |
| V7 | Verificar estado cambió a `in_progress`/`done` | Visual + DB | Baja |
| V8 | Click en task_id → navega a vista de tarea | UI | Baja |
| V9 | Verificar correlation_id en logs | Backend logs | Media |
| V10 | Verificar eventos en domain_events | DB query | Media |

### Dependencias
- Backend corriendo en puerto 3001
- Base de datos accessible
- Al menos un flow registrado en `flow_registry`

---

## 7. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Flow no encontrado | Baja | Medio: ticket queda en `blocked` | Verificar que existe flow antes de ejecutar |
| Timeout en ejecución | Media | Bajo: ticket queda en `in_progress` | `refetchInterval` de 10s eventually consistent |
| DB no accessible | Baja | Crítico: ejecución falla | Verificar conexión DB antes de validar |

---

## 8. Métricas de Éxito / Criterios de Aceptación

| # | Criterio | Método de Verificación |
|---|----------|----------------------|
| E1 | Ticket se crea exitosamente via API | POST /tickets retorna 201 + ticket |
| E2 | Botón Play visible en ticket con flow_type | UI: verificar botón en fila |
| E3 | Spinner aparece al ejecutar | UI: verificar animación |
| E4 | Toast de éxito muestra task_id | UI: verificar mensaje |
| E5 | Tabla refresca automáticamente | UI: verificar update sin reload |
| E6 | `task_id` aparece en columna "Task" | UI: verificar link |
| E7 | Estado cambia a `in_progress`/`done` | UI: verificar badge |
| E8 | Correlation_id propagado en logs | Backend: buscar en event_store |
| E9 | domain_events grabados | DB: SELECT de domain_events |
| E10 | Error de flow inexistente → `blocked` | UI: verificar toast + status |

---

## 9. Testing - Casos Críticos

### Test 1: Happy Path Completo
```
1. Crear ticket con flow_type = "coctel_flow"
2. Verificar status = "backlog"
3. Click en Play
4. Verificar spinner en fila
5. Esperar respuesta
6. Verificar toast éxito con Task ID
7. Verificar status = "in_progress" o "done"
8. Verificar task_id no null
9. Click en task_id → navegación a /tasks/{id}
```

### Test 2: Error de Flow Inexistente
```
1. Crear ticket con flow_type = "nonexistent_flow"
2. Click en Play
3. Verificar toast error
4. Verificar status = "blocked"
5. Verificar notes contiene mensaje de error
```

### Test 3: Aislamiento de Filas
```
1. Crear Ticket A y Ticket B con flow_type válido
2. Ejecutar Ticket A
3. Verificar spinner SOLO en Ticket A
4. Ticket B sigue con Play visible
5. Ticket A completa
6. Verificar Ticket A muestra nuevo estado
7. Verificar Ticket B sin cambios
```

---

## 10. Consideraciones Futuras (Post-MVP)

- **Logs centralizados:** Un dashboard de logs para correlation_id
- **Transcripts tiempo real:** Ver streaming de eventos de domain_events
- **Cancelación de tasks:** Endpoint para cancelar task en ejecución
- **Retry automático:** Re-ejecutar ticket en `blocked` sin crear nuevo

---

## 📋 Registro de Validación

**Estado:** ✅ COMPLETADO según `estado-fase.md`

| Verificación | Resultado | Evidencia |
|--------------|-----------|-----------|
| Happy path E2E | ✅ Pass | Logs + UI verificados |
| Spinner por fila | ✅ Pass | Implementación en código |
| Toasts de feedback | ✅ Pass | useExecuteTicket |
| Invalidación de queries | ✅ Pass | onSettled |
| correlation_id propagation | ✅ Pass | Logs de backend |
| task_id assignment | ✅ Pass | Response API |
| Estado post-ejecución | ✅ Pass | UI actualizada |

**Conclusión:** El paso 1.5 valida que la Fase 1 (E4 - Hardening de Tickets) está completa y el sistema funciona correctamente end-to-end.
