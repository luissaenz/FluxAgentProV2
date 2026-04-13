# 🧠 ANÁLISIS TÉCNICO: Paso 1.5 - Prueba E2E de Ciclo de Vida

## Perfil del Rol
Ingeniero de Software Senior validando la integración end-to-end del sistema de tickets.

---

## 1. Comprensión del Paso

### Objetivo
Validar que el ciclo completo de un ticket funciona: **Crear → Ejecutar → Vincular task_id → Cambiar estado**.

### Contexto (Referenciar `estado-fase.md`)
- Fase 1 (E4) completada: hardening de tickets
- Pasos 1.1-1.4 implementados y funcionando
- Este paso es **validación**, no implementación nueva

### Inputs del Sistema
- Frontend: `tickets/page.tsx`, `useExecuteTicket` hook
- Backend: `POST /tickets/{id}/execute`, `GenericFlow`
- DB: Tabla `tickets` con campos `id`, `status`, `task_id`, `notes`

### Outputs Verificados
- Ticket con `task_id` asignado post-ejecución
- Estado cambia a `in_progress` / `done` / `blocked`
- Errores persistidos en `notes`
- Eventos de dominio grabados en `domain_events`

---

## 2. Supuestos y Ambigüedades

| # | Ambigüedad | Resolución |
|---|------------|------------|
| A1 | ¿Qué constituye "ciclo completo"? | Crear → Ejecutar → Verificar task_id + estado |
| A2 | ¿Estados válidos post-ejecución? | `in_progress`, `done`, `blocked` |
| A3 | ¿Backend requerido? | Sí, validación real |
| A4 | ¿Flow no existe? | Ticket pasa a `blocked` con error en `notes` |

---

## 3. Diseño Funcional

### Happy Path Validado
```
1. Usuario crea ticket → POST /tickets → status = "backlog"
2. Usuario hace click en Play → POST /tickets/{id}/execute
3. Backend ejecuta GenericFlow → Crea task → Graba domain_events
4. Response: { id, status, task_id, notes }
5. Frontend: toast.success → invalidate queries
6. UI refresca: nuevo status + task_id como link
```

### Edge Cases MVP

| Escenario | Resultado |
|-----------|-----------|
| Ticket sin flow_type | Botón Play no visible |
| Ticket en estado terminal | Botón Play no visible |
| Flow no existe | `blocked` + error en `notes` |
| Error de red | Toast "Error de conexión" |
| Error de API | Toast con mensaje del backend |

---

## 4. Diseño Técnico

### Componentes Involucrados

| Capa | Archivo | Rol |
|------|---------|-----|
| Backend | `src/api/routes/tickets.py` | Endpoint execute |
| Backend | `src/flows/cocket_flows.py` | GenericFlow |
| Backend | `src/flows/state.py` | correlation_id |
| Backend | `src/events/event_store.py` | domain_events |
| Frontend | `tickets/page.tsx` | Lista de tickets |
| Frontend | `hooks/useTickets.ts` | useExecuteTicket |

### Contratos Verificados

| Campo | Formato |
|-------|---------|
| correlation_id | `ticket-{id}` |
| task_id | UUID v4 |
| Status | `in_progress`, `done`, `blocked` |
| Notas error | Persistidas en `ticket.notes` |

---

## 5. Decisiones

Este paso **valida** decisiones de pasos anteriores:

| Decisión | Paso | Validada |
|----------|------|----------|
| correlation_id como clave de trazabilidad | 1.2 | ✅ |
| Toasts de carga/éxito/error | 1.3 | ✅ |
| Spinner por fila en execute | 1.4 | ✅ |
| Invalidación de queries | 1.4 | ✅ |

---

## 6. Criterios de Aceptación

| # | Criterio | Verificable |
|---|----------|-------------|
| C1 | Ticket se crea exitosamente | POST /tickets retorna 201 |
| C2 | Botón Play visible en ticket con flow_type | UI |
| C3 | Spinner aparece al ejecutar | UI |
| C4 | Toast de éxito muestra task_id | UI |
| C5 | Tabla refresca automáticamente | UI |
| C6 | task_id aparece en columna "Task" | UI |
| C7 | Estado cambia a `in_progress`/`done` | UI |
| C8 | Correlation_id propagado en logs | Backend logs |
| C9 | domain_events grabados | DB query |
| C10 | Error → `blocked` + notes | UI + DB |

---

## 7. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Flow no encontrado | Baja | Medio | Verificar flow existe antes |
| Timeout ejecución | Media | Bajo | refetchInterval 10s |
| DB no accesible | Baja | Crítico | Verificar conexión |

---

## 8. Plan de Validación

| # | Tarea | Complejidad |
|---|-------|-------------|
| V1 | Crear ticket con flow_type válido | Baja |
| V2 | Ejecutar ticket | Baja |
| V3 | Verificar spinner en fila correcta | Baja |
| V4 | Verificar toast éxito | Baja |
| V5 | Verificar refresco automático | Baja |
| V6 | Verificar task_id como link | Baja |
| V7 | Verificar cambio de estado | Baja |
| V8 | Navegar a vista de tarea | Baja |
| V9 | Verificar correlation_id en logs | Media |
| V10 | Verificar domain_events | Media |

---

## 9. Testing - Casos Críticos

### Test 1: Happy Path
```
1. Crear ticket con flow_type = "coctell_flow"
2. Verificar status = "backlog"
3. Click Play
4. Verificar spinner
5. Esperar respuesta
6. Verificar toast éxito
7. Verificar status = "in_progress" o "done"
8. Verificar task_id no null
9. Click task_id → /tasks/{id}
```

### Test 2: Error de Flow Inexistente
```
1. Crear ticket con flow_type = "inexistente"
2. Click Play
3. Verificar toast error
4. Verificar status = "blocked"
5. Verificar notes contiene error
```

### Test 3: Aislamiento de Filas
```
1. Crear Ticket A y B
2. Ejecutar Ticket A
3. Verificar spinner SOLO en A
4. A completa, B sin cambios
```

---

## 10. Consideraciones Futuras

- Dashboard de logs por correlation_id
- Transcripts tiempo real
- Cancelación de tasks
- Retry automático para tickets en `blocked`

---

## 📋 Registro

**Estado:** ✅ COMPLETADO según `estado-fase.md`

| Verificación | Resultado |
|--------------|-----------|
| Happy path E2E | ✅ Pass |
| Spinner por fila | ✅ Pass |
| Toasts de feedback | ✅ Pass |
| Invalidación queries | ✅ Pass |
| correlation_id propagation | ✅ Pass |
| task_id assignment | ✅ Pass |
| Estado post-ejecución | ✅ Pass |

**Conclusión:** Paso 1.5 valida que la Fase 1 (E4) está completa y el sistema funciona end-to-end.