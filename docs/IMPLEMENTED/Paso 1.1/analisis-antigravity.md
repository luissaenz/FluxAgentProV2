# 🧠 ANÁLISIS TÉCNICO: Paso 1.1 - Hardening de Tickets (Backend)

**Agente:** antigravity
**Contexto:** MVP FluxAgentPro v2 — Fase 1 (Hardening de Tickets)

---

## 1. Diseño Funcional

### Happy Path Detallado
1. El usuario solicita la ejecución de un ticket vía `POST /tickets/{id}/execute`.
2. El sistema valida que el ticket exista, tenga un `flow_type` válido y no esté ya `in_progress` o `done`.
3. El estado del ticket cambia a `in_progress`.
4. Se invoca el motor de ejecución (`execute_flow`).
5. La ejecución es exitosa:
    - Se recibe un `task_id`.
    - El estado del ticket cambia a `done`.
    - Se registra la fecha de resolución (`resolved_at`).
    - Se vincula el `task_id` al ticket.

### Edge Cases (MVP)
- **Fallo de Inicialización:** El `flow_type` está registrado pero falla al instanciarse (ej. configuración corrupta).
- **Fallo de Validación:** El `input_data` del ticket no cumple el esquema del flow.
- **Fallo de Ejecución (Síncrono/Inmediato):** El flow falla antes de generar un `task_id` persistente.

### Manejo de Errores
- Cuando cualquier excepción ocurre en el proceso de ejecución, el ticket debe transicionar al estado **`blocked`**.
- El usuario verá un error 500 en la API, pero al consultar el ticket en el dashboard, verá el estado `blocked` y una descripción del error en el campo `notes` para poder corregir el input o el flow y reintentar.

---

## 2. Diseño Técnico

### Componentes Afectados
- **`src/api/routes/tickets.py`:** Refactorización del método `execute_ticket`.
- **`src/api/routes/webhooks.py`:** (Opcional pero recomendado) Ajuste en `execute_flow` para no silenciar errores cuando se llama de forma determinista.

### Modificaciones en `tickets.py`
Se rediseñará el bloque de ejecución para asegurar la atomicidad de las transiciones:

1. **Pre-check:** Validaciones de estado actual (ya existente).
2. **Transición 1:** Update a `status='in_progress'`.
3. **Bloque Try/Except:**
    - Llamada a `execute_flow`.
    - Si `execute_flow` retorna `None` o lanza excepción:
        - Catch del error.
        - **Transición 2 (Error):** Update a `status='blocked'`, `notes='Error: {mensaje_error}'`.
        - Re-raise o raise `HTTPException(500)`.
4. **Transición 2 (Éxito):** Update a `status='done'`, vincular `task_id`.

### Modelo de Datos
- Se utilizará el campo `notes` existente en la tabla `tickets` para persistir la traza del error.
- Se respeta el contrato definido en `docs/estado-fase.md`.

---

## 3. Decisiones

1. **Persistencia del Error en `notes`:** Se decide usar el campo `notes` en lugar de crear uno nuevo para minimizar cambios en el esquema de base de datos durante el Hardening, aprovechando que es un campo de texto libre ya presente.
2. **Propagación de Excepciones:** Se forzará la captura de excepciones en el router de tickets. Si `execute_flow` no se modifica para lanzar excepciones, se tratará el retorno de `None` como un fallo crítico que dispara el estado `blocked`.

---

## 4. Criterios de Aceptación

- [ ] **CA1:** Al ocurrir un error en el flow (ej. `ValueError` por input inválido), el ticket en DB tiene `status = 'blocked'`.
- [ ] **CA2:** El campo `notes` del ticket contiene el mensaje exacto de la excepción capturada.
- [ ] **CA3:** Si el flow se ejecuta correctamente, el ticket tiene `status = 'done'` y un `task_id` no nulo.
- [ ] **CA4:** Un ticket en estado `blocked` puede ser ejecutado nuevamente (el router debe permitir la transición desde `blocked` a `in_progress`).

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
| :--- | :--- | :--- |
| **Silent Failures en `execute_flow`** | Alto | Modificar `execute_flow` para que lance excepciones o validar estrictamente el `task_id` retornado. |
| **Race Conditions** | Medio | El ticket ya implementa un check de estado previo, pero se debe asegurar que el update a `in_progress` ocurra antes de la llamada pesada. |

---

## 6. Plan

1. **Investigación Final (Baja):** Confirmar si `execute_flow` puede ser modificado sin afectar negativamente a `/webhooks/trigger`.
2. **Refactorización de `execute_ticket` (Media):** 
    - Implementar el estado `blocked` en el catch.
    - Asegurar que `notes` se limpie o actualice en cada intento.
3. **Pruebas de Integración (Media):**
    - Mockear un fallo en un Flow conocido.
    - Verificar transiciones en Supabase/Postgres.

---

### 🔮 Roadmap (NO implementar ahora)
- Implementar un historial de errores (`ticket_events`) en lugar de sobrescribir `notes`.
- Sistema de reintentos automáticos para errores transitorios de red.
