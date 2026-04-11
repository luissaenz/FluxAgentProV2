# 🏛️ ANÁLISIS UNIFICADO (FINAL): Paso 1.1 - Hardening de Tickets (Backend)

Este documento representa la visión técnica definitiva y consolidada para la refactorización del endpoint de ejecución de tickets, integrando las mejores propuestas de diseño técnico y robustez.

---

## 1. Resumen Ejecutivo
El objetivo de este paso es transformar el endpoint `POST /tickets/{id}/execute` de una implementación básica a una robusta, capaz de gestionar fallos en el motor de ejecución de flows de forma transparente. Se asegura que el usuario tenga visibilidad total (estado `blocked` + descripción del error) y el sistema mantenga la trazabilidad (vínculo con `task_id` incluso en fallos).

## 2. Diseño Funcional Consolidado

### Happy Path Detallado
1. **Solicitud:** El cliente envía un POST a `/tickets/{ticket_id}/execute`.
2. **Pre-validación:** El sistema verifica:
   - Existencia del ticket.
   - Presencia de `flow_type`.
   - Estado compatible (`backlog`, `open`, `blocked`). Se permite reintentar desde `blocked`.
3. **Inicio:** Se actualiza el ticket a `in_progress`.
4. **Ejecución:** Se invoca a `execute_flow`.
5. **Cierre Exitoso:** 
   - Se recibe el `task_id`.
   - El ticket pasa a `done`.
   - Se vincula el `task_id` y se registra `resolved_at`.

### Manejo de Errores (Edge Cases)
- **Fallo del Motor (Excepción):** Si el flow falla durante su ciclo de vida, el ticket debe transicionar a **`blocked`**.
- **Notas de Error:** Se concatenará la información del error (tipo de excepción, mensaje y timestamp) al campo `notes`, **preservando** cualquier contenido previo existente.
- **Trazabilidad de Fallos:** Si el flow alcanzó a crear un registro en la tabla `tasks` antes de fallar, se vincula ese `task_id` al ticket aunque el estado sea `blocked`.

---

## 3. Diseño Técnico Definitivo

### Modificación Core: `execute_flow` (`src/api/routes/webhooks.py`)
Se modifica el contrato de retorno para proporcionar visibilidad al llamador (el endpoint de tickets):
- **Retorno:** Objeto `Dict` con las claves `task_id`, `error`, y `error_type`. 
- **Lógica:** Intenta capturar el `task_id` del estado del objeto `flow` incluso si ocurre una excepción en `_run_crew`.

### Refactor en `tickets.py`
Se implementa una función auxiliar `_update_ticket_on_failure` para centralizar la lógica de persistencia del error.

**Esquema de transición:**
```python
try:
    result = await execute_flow(...)
    if result["error"]:
         await _handle_blocked_ticket(ticket_id, result)
    else:
         await _handle_done_ticket(ticket_id, result["task_id"])
except Exception as infra_exc:
    # Error de infraestructura (DB, red, etc)
    await _handle_blocked_ticket(ticket_id, {"error": str(infra_exc), ...})
```

### Integración con EventStore
Se mantendrá la emisión automática de eventos de `flow.failed` (vía `BaseFlow`), pero el ticket servirá como el punto de entrada para que el usuario humano identifique el bloqueo.

---

## 4. Decisiones Tecnológicas
- **Preservación de Notas:** Se decide no sobrescribir el campo `notes` para no perder comentarios manuales de los analistas previos a la ejecución.
- **Formato del Error:** Se incluirá el nombre de la clase de la excepción (ej: `ValueError`) para facilitar el diagnóstico técnico rápido.

---

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] El ticket cambia a `done` tras una ejecución exitosa de un flow.
- [ ] El ticket cambia a `blocked` si el flow falla o el motor de ejecución reporta un error.
- [ ] El campo `notes` del ticket muestra los detalles del error incluyendo timestamp.

### Técnicos
- [ ] El `task_id` se vincula correctamente en la tabla `tickets` incluso si el estado final es `blocked`.
- [ ] El `correlation_id` con formato `ticket-{id}` aparece en la tabla `tasks` tras la ejecución.
- [ ] El endpoint devuelve un 500 explícito con detalle del error si la ejecución falla.

### Robustez
- [ ] Si `execute_flow` retorna `None` o un diccionario vacío, el sistema lo trata como fallo y marca `blocked`.
- [ ] Notas previas en el ticket no se borran al registrar un error de ejecución.

---

## 6. Plan de Implementación
1. **[Back-end]** Modificar `execute_flow` en `webhooks.py` para retornar el diccionario extendido. (Baja)
2. **[Back-end]** Implementar lógica de formateo y append en `notes` dentro de `tickets.py`. (Baja)
3. **[Back-end]** Refactorizar el router `/execute` para orquestar los estados finales según el retorno de `execute_flow`. (Media)
4. **[Validación]** Simular excepción en `BaseFlow` y verificar estado `blocked` en base de datos. (Baja)

---

## 7. Riesgos y Mitigaciones
- **Riesgo:** Incompatibilidad con el webhook trigger al cambiar el retorno de `execute_flow`. 
- **Mitigación:** El webhook actual usa `background_tasks.add_task` y no evalúa el retorno; el cambio es seguro.
- **Riesgo:** Campo `notes` muy saturado.
- **Mitigación:** Limitar el resumen del error a mensaje y tipo de excepción (sin full traceback largo por ahora).

---

## 8. Testing Mínimo Viable
1. Crear un ticket con un flow inexistente -> Debe dar ERROR 404 (validación previa).
2. Crear un ticket con un flow que fuerce un error de ejecución -> Ticket debe quedar `blocked` con nota de error.
3. Ejecutar ticket exitoso -> Ticket debe quedar `done` y con `task_id` correcto.

---

## 🔮 Roadmap (NO implementar ahora)
- Implementar una columna específica `last_error` en la tabla `tickets` para separar notas humanas de trazas técnicas.
- Botón de "Auto-retry" en el dashboard para tickets bloqueados.
- Notificaciones vía Webhooks salientes cuando un ticket cambia a `blocked`.
