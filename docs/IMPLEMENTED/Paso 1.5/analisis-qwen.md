# 🧠 ANÁLISIS TÉCNICO: PASO 1.5 — PRUEBA E2E DE CICLO DE VIDA

**Fecha:** 2026-04-11
**Agente:** qwen
**Paso:** 1.5 (Fase 1 - Hardening de Tickets)
**Alcance:** Validación end-to-end del ciclo completo Ticket → Flow → Task

---

## 1. Diseño Funcional

### 1.1 Qué es este paso

Paso 1.5 es la **validación integradora** de toda la Fase 1. No construye funcionalidad nueva — verifica que los pasos 1.1–1.4 funcionan juntos como un ciclo completo y coherente.

El mvp-Definition dice:
> *"Crear un ticket → Ejecutar → Verificar que el `task_id` se vincula correctamente y el estado cambia a `done`/`blocked`."*

### 1.2 Happy Path E2E

| # | Acción | Resultado esperado | Responsable |
|---|--------|--------------------|-------------|
| 1 | `POST /tickets` con `title`, `flow_type="generic_flow"`, `input_data={"text": "test"}` | 201, ticket creado con `status: "backlog"` | Backend (CRUD existente) |
| 2 | `POST /tickets/{id}/execute` | 200, response con `status: "done"`, `task_id` vinculado | Backend (Paso 1.1) |
| 3 | `GET /tickets/{id}` | Ticket con `status: "done"`, `task_id` != null, `resolved_at` != null | Backend (CRUD) |
| 4 | `GET /tasks/{task_id}` | Task existe, `status: "completed"`, `correlation_id: "ticket-{id}"` | Backend (Paso 1.2) |
| 5 | UI: Dashboard muestra ticket con `task_id` clickeable y estado `done` | Tabla reflejando el nuevo estado sin recarga manual | Frontend (Pasos 1.3, 1.4) |

### 1.3 Path de Error (blocked)

| # | Acción | Resultado esperado |
|---|--------|--------------------|
| 1 | `POST /tickets` con `flow_type` válido pero cuyo execution fuerza error | 201, ticket creado |
| 2 | `POST /tickets/{id}/execute` | 500, response con `detail.status: "blocked"`, `detail.error` descriptivo |
| 3 | `GET /tickets/{id}` | Ticket con `status: "blocked"`, `notes` contiene el error con timestamp y tipo |
| 4 | `task_id` puede estar vinculado o no (depende de si el flow llegó a crear task antes de fallar) |

### 1.4 Edge Cases MVP

| Escenario | Comportamiento esperado | Ya cubierto por |
|-----------|------------------------|-----------------|
| Ticket sin `flow_type` | `POST /execute` → 400 "Ticket has no flow_type" | Paso 1.1, test `test_execute_ticket_no_flow_type` |
| Flow inexistente en registry | `POST /execute` → 404 "Flow type not found" | Paso 1.1, test `test_execute_ticket_not_found` |
| Ticket ya `in_progress` | `POST /execute` → 409 "Ticket is already in_progress" | Paso 1.1, test `test_execute_ticket_already_in_progress` |
| Ticket ya `done` | `POST /execute` → 409 "Ticket is already done" | Paso 1.1, test `test_execute_ticket_already_done` |
| Error de infraestructura | `POST /execute` → 500, ticket `blocked` con nota | Paso 1.1, test `test_500_on_infrastructure_error` |
| Ejecución desde UI (doble click) | Solo 1 request llega al backend (disabled global) | Paso 1.4, `disabled={executeTicket.isPending}` |

### 1.5 Lo que NO es este paso

- **No** es un test automatizado nuevo. Los tests de integración (`test_tickets_execute.py`) ya cubren los escenarios con mocks.
- **No** es un test E2E contra infraestructura real (Supabase). Eso es un script de validación manual o semi-automatizada.
- **No** requiere código de producción nuevo. Es un **procedimiento de validación**.

---

## 2. Diseño Técnico

### 2.1 Componentes Involucrados

Este paso es un **procedimiento de verificación**, no un componente de software. Los artefactos que intervienen son:

| Artefacto | Rol en la validación |
|-----------|---------------------|
| `POST /tickets` | Creación del ticket de prueba |
| `POST /tickets/{id}/execute` | Disparo del flow |
| `GET /tickets/{id}` | Verificación del estado final |
| `GET /tasks/{task_id}` | Verificación del task vinculado y correlation_id |
| `dashboard/app/(app)/tickets/page.tsx` | Verificación visual del spinner, toast, y refresco |
| `dashboard/hooks/useTickets.ts` | Verificación de invalidación de caché y toasts |
| `tests/integration/test_tickets_execute.py` | Evidencia de que los tests de integración pasan |
| `src/flows/base_flow.py` | Verificación de que `correlation_id` se propaga |

### 2.2 Procedimiento de Validación E2E

La validación se estructura en **3 niveles**, de menor a mayor integración:

#### Nivel 1: Tests de Integración (automatizado, ya existe)

```
make test test-args='tests/integration/test_tickets_execute.py'
```

- Cubre: validación de input, success → done, failure → blocked, infrastructure errors, correlation_id format, notes preservation.
- **Estado:** Ya implementado. 17 tests en `test_tickets_execute.py`.
- **Qué verificar:** Que todos pasen sin errores.

#### Nivel 2: Tests E2E con TestClient (automatizado, ya existe)

```
make test test-args='tests/e2e/test_webhook_to_completion.py'
```

- Cubre: webhook trigger → task lifecycle con la app real (mocked infra).
- **Estado:** Ya implementado.
- **Gap:** No cubre el camino de tickets → execute → done. Cubre webhooks → tasks.

#### Nivel 3: Validación E2E Real (semi-automatizada, requiere infraestructura)

Este es el **gap principal** del paso 1.5. Se necesita verificar el ciclo completo con infraestructura real (Supabase). Hay dos opciones:

**Opción A — Script de validación standalone (recomendada):**
Crear `src/scripts/validate_phase1_e2e.py` que:
1. Se conecta a Supabase real (lee `.env`).
2. Crea un ticket vía `POST /tickets`.
3. Lo ejecuta vía `POST /tickets/{id}/execute`.
4. Poll `GET /tickets/{id}` hasta que `status` sea `done` o `blocked` (timeout 60s).
5. Si `done`: verifica `task_id` y consulta `GET /tasks/{task_id}` para confirmar `correlation_id`.
6. Si `blocked`: verifica que `notes` contiene información del error.
7. Imprime resumen de resultados (PASS/FAIL por checkpoint).

**Opción B — Checklist manual ejecutado por humano:**
Documento con pasos manuales para ejecutar contra la app corriendo.

**Decisión:** Implementar **Opción A** (script) como artefacto de validación. Es reutilizable, documentable en CI, y produce evidencia concreta. Es el estándar del proyecto (ya existen `validate_phase2_e2e.py` y `validate_phase3_e2e.py`).

### 2.3 Diseño del Script `validate_phase1_e2e.py`

```
src/scripts/validate_phase1_e2e.py
```

**Estructura lógica:**

1. **Setup:**
   - Lee `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` del `.env`.
   - Crea sesión de auth para obtener token.
   - Verifica conexión con Supabase.

2. **Test Suite 1 — Happy Path (Ticket → Done):**
   - `POST /tickets` con `flow_type: "generic_flow"`, `input_data: {"text": "E2E validation test"}`.
   - Captura `ticket_id`.
   - `POST /tickets/{ticket_id}/execute`.
   - Poll `GET /tickets/{ticket_id}` cada 2s, max 60s.
   - **Checkpoint H1:** `status == "done"`.
   - **Checkpoint H2:** `task_id` is not null.
   - **Checkpoint H3:** `GET /tasks/{task_id}` retorna task con `correlation_id == "ticket-{ticket_id}"`.
   - **Checkpoint H4:** `resolved_at` is not null.

3. **Test Suite 2 — Error Path (Ticket → Blocked):**
   - `POST /tickets` con `flow_type: "generic_flow"`.
   - `POST /tickets/{ticket_id}/execute`.
   - **Checkpoint E1:** Response 500 con `detail.status == "blocked"`.
   - **Checkpoint E2:** `GET /tickets/{ticket_id}` retorna `status == "blocked"`.
   - **Checkpoint E3:** `notes` contiene referencia al error.

4. **Test Suite 3 — Frontend Smoke Test (opcional, si app está corriendo):**
   - Verifica que `dashboard` está accesible en `http://localhost:3000`.
   - Si sí: imprime instrucciones manuales para verificar UI (spinner, toast, refresco).

5. **Cleanup:**
   - No elimina los tickets creados (quedan como evidencia de la validación).
   - Imprime IDs de tickets creados para referencia.

6. **Output:**
   - Formato: `[PASS]` / `[FAIL]` por checkpoint.
   - Resumen final: `X/Y checkpoints passed`.
   - Exit code 0 si todo pasa, 1 si algún checkpoint falla.

### 2.4 Qué NO implementa el script

- No crea flujos nuevos (usa `generic_flow` que ya existe).
- No modifica la base de datos fuera de los endpoints públicos.
- No requiere migraciones nuevas.
- No testa la UI programáticamente (eso sería un test de Playwright/Cypress — fuera de scope MVP).

---

## 3. Decisiones

### D1: Script semi-automatizado vs test pytest puro

**Decisión:** Crear `src/scripts/validate_phase1_e2e.py` como script standalone (patrón consistente con `validate_phase2_e2e.py` y `validate_phase3_e2e.py`).

**Justificación:**
- Los tests de integración ya cubren el camino con mocks.
- Este paso necesita infraestructura real para ser una verdadera validación E2E.
- Los scripts de validación de fases 2 y 3 ya siguen este patrón.
- Permite ejecución ad-hoc sin necesidad de un pipeline CI/CD.

**Trade-off:** Requiere `.env` configurado y Supabase accesible. No es adecuado para CI sin infraestructura de test.

### D2: No crear tests pytest E2E nuevos

**Decisión:** NO ampliar `tests/e2e/test_webhook_to_completion.py` con tests de tickets.

**Justificación:**
- Los tests E2E de pytest usan `TestClient` con mocks — ya están cubiertos por `test_tickets_execute.py`.
- El valor de Paso 1.5 es la validación contra infraestructura real, no contra mocks.
- Agregar tests E2E reales a pytest requeriría fixtures de infraestructura que no existen.

### D3: Polling en vez de WebSockets/Realtime

**Decisión:** El script usa polling HTTP cada 2s con timeout de 60s.

**Justificación:**
- Supabase Realtime requeriría suscripción WebSocket — complejidad innecesaria para una validación puntual.
- El `refetchInterval: 10_000` del frontend ya confirma que polling es suficiente para este MVP.
- 60s de timeout es generoso para `generic_flow` (típicamente completa en <15s).

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|----------|-------------|
| A1 | Los tests de integración de tickets pasan todos (`test_tickets_execute.py`) | `make test test-args='tests/integration/test_tickets_execute.py'` → 0 failures |
| A2 | El script `validate_phase1_e2e.py` existe en `src/scripts/` | File exists |
| A3 | El script valida el happy path: ticket creado → ejecutado → `done` con `task_id` | Output: `[PASS]` en checkpoints H1-H4 |
| A4 | El script valida el error path: ticket ejecutado → `blocked` con nota de error | Output: `[PASS]` en checkpoints E1-E3 |
| A5 | El script valida `correlation_id` con formato `ticket-{id}` en la task creada | Output: `[PASS]` en checkpoint H3 |
| A6 | El script produce resumen ejecutable con exit code correcto | Exit code 0 si todo pasa, 1 si falla |
| A7 | No se introduce código de producción nuevo | Solo `src/scripts/validate_phase1_e2e.py` creado |

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Supabase no accesible al ejecutar el script | Media | Alto: validación bloqueada | El script detecta error temprano con mensaje claro ("No se puede conectar a Supabase. Verifique .env") |
| `generic_flow` no registrado al iniciar la app | Baja | Alto: no se puede ejecutar | El script verifica registro del flow antes de empezar. Si no existe, sugiere `make server` primero |
| Timeout de 60s insuficiente para flow complejo | Baja | Medio: false negative | Aumentar a 120s si es necesario. `generic_flow` típico completa en <15s |
| Tests de integración fallan por mocks desactualizados | Baja | Medio: validación Nivel 1 bloqueada | Ejecutar `make test` primero. Si fallan, es issue de mocks, no del flujo real |
| Script crea tickets duplicados en ejecuciones múltiples | Media | Bajo: ruido en la DB | El script prefija el título con timestamp: `E2E-VALIDATION-{timestamp}` para identificación fácil |

---

## 6. Plan

| # | Tarea | Complejidad | Dependencias | Notas |
|---|-------|-------------|--------------|-------|
| 1 | Ejecutar `make test test-args='tests/integration/test_tickets_execute.py'` y confirmar que todos pasan | Baja | Ninguna | Validación Nivel 1 — ya debería pasar |
| 2 | Crear `src/scripts/validate_phase1_e2e.py` con happy path (H1-H4) | Media | App corriendo, Supabase accesible | Script standalone, patrón de fases 2/3 |
| 3 | Agregar error path (E1-E3) al script | Media | Tarea 1 completada | Requiere flow que falle — se puede simular con input_data malformado |
| 4 | Agregar validación de `correlation_id` (H3) | Baja | Paso 1.2 completado | `GET /tasks/{task_id}` y verificar campo |
| 5 | Agregar resumen y exit codes | Baja | Tareas 2-4 | Formato `[PASS]`/`[FAIL]`, exit code 0/1 |
| 6 | Ejecutar script contra app real y documentar resultado | Baja | Tarea 5, app corriendo | Ejecución real como evidencia de validación |

**Orden recomendado:** 1 → 2 → 3 → 4 → 5 → 6

**Dependencias externas:**
- App corriendo (`make server`) para endpoints disponibles.
- Supabase accesible (`.env` configurado).
- `generic_flow` registrado en el registry.

---

## 🔮 Roadmap (NO implementar ahora)

### Automatización en CI/CD
| Mejora | Descripción | Bloqueador actual |
|--------|-------------|-------------------|
| **GitHub Actions E2E** | Ejecutar `validate_phase1_e2e.py` en pipeline con Supabase de staging | Necesita infraestructura de staging |
| **Playwright/Cypress tests** | Tests E2E reales del frontend (spinner, toasts, refresco) | Setup de browser automation, tiempo de ejecución |
| **Contract testing** | Verificar que API contracts no se rompan entre frontend y backend | Herramienta de contract testing (Pact, etc.) |

### Validación Avanzada
| Mejora | Descripción | Fase destino |
|--------|-------------|--------------|
| **Validación de toasts en UI** | Verificar que toasts de éxito/error aparecen | Fase 2+ |
| **Validación de Refresco automático** | Confirmar que la tabla se actualiza sin reload manual | Fase 2+ |
| **Test de carga del endpoint** | Verificar que `/execute` soporta N ejecuciones concurrentes | Fase 3+ |

### Decisiones de Diseño para Futuro
- El script de validación es **agnóstico del flow** — se puede reutilizar para validar cualquier flow, no solo `generic_flow`.
- El patrón de polling es compatible con futuras suscripciones de Supabase Realtime (Fase 3).
- Los checkpoints del script pueden convertirse en **assertions de CI** cuando haya infraestructura de staging.
