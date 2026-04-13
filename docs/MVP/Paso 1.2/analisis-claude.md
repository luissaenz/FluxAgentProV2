# ANÁLISIS — Paso 1.2: Estandarización del `correlation_id`
**Agente:** claude
**Fecha:** 2026-04-11

---

## 1. Resumen

El paso 1.2 requiere asegurar que el `correlation_id` con formato `ticket-{id}` se propague correctamente desde el router de tickets hasta el `BaseFlow` para trazabilidad cruzada en la tabla `tasks`.

**Hallazgo clave:** Este paso ya se encuentra **IMPLEMENTADO Y VALIDADO** como consecuencia del paso 1.1 (hardening de `/execute`). La validación `LAST/validacion.md` confirma que el `correlation_id` se propaga correctamente con tests en `tests/integration/test_tickets_execute.py:384`.

---

## 2. Análisis Técnico Actual

### Flujo de datos verificado

```
tickets.py:320  →  correlation_id = f"ticket-{ticket_id}"
                       ↓
tickets.py:323  →  execute_flow(correlation_id=correlation_id, ...)
                       ↓
webhooks.py:125 →  flow.execute(input_data, correlation_id)
                       ↓
base_flow.py:176 →  INSERT INTO tasks { ..., correlation_id: correlation_id }
```

### Contrato verificado

| Componente | Rol |
|---|---|
| `tickets.py:320` | Genera `correlation_id = f"ticket-{ticket_id}"` |
| `execute_flow` (webhooks.py:108) | Recibe `correlation_id: str` y lo pasa a `flow.execute` |
| `BaseFlow.execute` (base_flow.py:100) | Recibe `correlation_id` y lo inyecta en el state |
| `create_task_record` (base_flow.py:162-176) | Inserta `correlation_id` en columna `tasks.correlation_id` |
| `MultiCrewFlow.create_task_record` (multi_crew_flow.py:60-82) | Override equivalente con el mismo patrón |

### Formato confirmado

El formato `ticket-{ticket_id}` donde `ticket_id` es un UUID (ej: `ticket-550e8400-e29b-41d4-a716-446655440000`) es consistente con:
- La convención de correlation_id del sistema (formatos `manual-{flow_type}-{org_id}` en flows.py, `ticket-{ticket_id}` en tickets)
- El índice existente `idx_tasks_correlation` en la migración `001_set_config_rpc.sql:134`

---

## 3. Criterios de Aceptación

| # | Criterio | Estado | Evidencia |
|---|----------|--------|-----------|
| 1 | El `correlation_id` con formato `ticket-{id}` se genera en `POST /tickets/{id}/execute` | ✅ Cumple | `tickets.py:320`: `correlation_id = f"ticket-{ticket_id}"` |
| 2 | El `correlation_id` se pasa a `execute_flow` como parámetro | ✅ Cumple | `tickets.py:323-327`: pasa `correlation_id=correlation_id` |
| 3 | El `correlation_id` se inserta en la columna `tasks.correlation_id` | ✅ Cumple | `base_flow.py:176`: `"correlation_id": correlation_id` |
| 4 | El formato es `ticket-{ticket_id}` con el UUID del ticket | ✅ Cumple | Test `test_correlation_id_uses_ticket_format` en `test_tickets_execute.py:384-430` |

---

## 4. Decisiones

- **D1:** El `correlation_id` se genera en el endpoint `/execute` y no en `execute_flow`, para que el router tenga control sobre el formato. Esto permite que diferentes entrypoints (tickets, webhooks directos, etc.) usen formatos diferentes (`ticket-{id}` vs UUID random).
- **D2:** Se reutiliza el mismo `correlation_id` para toda la traza: desde la creación del ticket hasta la fila en `tasks`. No se genera un correlation_id nuevo dentro del flow.

---

## 5. Estado de Implementación

**CONCLUSIÓN: PASO COMPLETADO**

El paso 1.2 no requiere implementación adicional. Fue cubiertos durante la implementación del paso 1.1 y validado con 17 tests (incluyendo `test_correlation_id_uses_ticket_format`).

### Evidencia de validación

Test `tests/integration/test_tickets_execute.py:384-430`:
```python
def test_correlation_id_uses_ticket_format(
    self, client, mock_tenant_client, sample_org_id
):
    """correlation_id se pasa como ticket-{id} a execute_flow."""
    ...
    call_kwargs = mock_execute.call_args[1]
    assert call_kwargs["correlation_id"] == f"ticket-{ticket_id}"
```

---

## 6. Riesgos

- **R1:** Si un ticket se re-ejecuta (desde estado `blocked`), se genera un nuevo `task_id` pero el `correlation_id` sigue siendo `ticket-{ticket_id}`. Esto puede causar múltiples filas en `tasks` con el mismo `correlation_id`. **Mitigación:** El correlation_id sirve para trazabilidad, no para uniqueness. Múltiples tasks con el mismo correlation_id permiten rastrear todas las tentativas de un ticket.

---

## 7. Roadmap (NO implementar ahora)

- Considerar agregar un campo `attempt_number` a la tabla `tasks` para distinguir tentativas de re-ejecución.
- Indexar `tasks.correlation_id` por `ticket_id` parcial (去掉 el prefijo `ticket-`) si se necesitan consultas por `ticket_id` directo.

---

## 8. Nota para el proceso

El paso 1.2 es un sub-producto del paso 1.1. La propagación correcta del `correlation_id` fue una consecuencia natural de usar el mismo en `execute_flow`. No requiere trabajo adicional. El registro en `estado-fase.md` ya refleja esta decisión (sección 4, decisión "Contrato de execute_flow").