# 🏛️ ANÁLISIS TÉCNICO UNIFICADO: Sprint 3 — Handlers Productivos

## 0. Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Evidencia sólida | Score (1-5) |
|:---|:---:|:---:|:---|:---:|
| atg | ✅ | 3 | ✅ (L#, archivos) | 4 |
| kilo | ✅ | 1 | ✅ (grep, paths) | 4 |
| oc | ✅ | 3 | ✅ (L#, archivos) | 4 |
| qwen | ✅ | 6 | ✅ (L#, extractos) | 5 |

### Discrepancias Críticas y Resoluciones

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | Plan usa `PyJWT` vs `python-jose` | qwen, oc, atg | ✅ `pyproject.toml` L20 | Usar `python-jose` para generación de tokens (Bridge). El middleware usa `PyJWT` para verificación (verificado en `middleware.py` L54), pero `python-jose` es la única dependencia de Auth declarada. |
| 2 | Endpoint `create_workflow` ausente | kilo, qwen | ✅ `api/routes/workflows.py` | Implementar `create_workflow` como un wrapper que instancia y ejecuta `ArchitectFlow` directamente. |
| 3 | `execute_flow` de webhooks no portable | qwen | ✅ `api/routes/webhooks.py` L92 | Los handlers MCP deben instanciar flows vía `flow_registry.get()` para evitar dependencia de `BackgroundTasks` de FastAPI. |
| 4 | Tabla `pending_approvals` en duda | oc (duda), qwen (confirmó) | ✅ `002_governance.sql` L50 | La tabla EXISTE. Confirmada evidencia física en migración 002. |
| 5 | `FLOW_INPUT_SCHEMAS` vacío | qwen | ✅ `api/routes/flows.py` L74 | Los handlers deben manejar `input_data` como un dict genérico hasta que los flows registren schemas Pydantic explícitos. |
| 6 | Rutas Windows en el plan | atg, qwen | ✅ Workspace Linux | Ignorar `D:\...` y usar rutas relativas al workspace `/home/daniel/develop/...`. |

### Correcciones al Plan General
- **§3.67 (Auth Bridge):** Debe usar `python-jose` para codificar tokens internos.
- **§3.69 (Tools nuevas):** No son tools aisladas; `execute_flow` se integra como el motor de ejecución para las tools dinámicas inyectadas por `flow_to_tool.py`.

---

## 1. Resumen Ejecutivo
Implementación de la lógica de ejecución productiva para que Claude Desktop actúe como un operador real de FluxAgentPro v2. Se transiciona de un servidor MCP con "placeholders" a uno capaz de instanciar flows, gestionar tareas persistentes en DB, y manejar pausas para aprobación humana (HITL).

Este paso es el corazón del Sprint 3 y habilita la utilidad real del LLM sobre el ecosistema de agentes. Se han corregido 6 puntos críticos del plan original basándose en inspección de código fuente.

---

## 2. Diseño Funcional Consolidado

### Happy Paths
1. **Ejecución de Flow (`execute_flow`):**
   - Claude envía `flow_type` e `input_data`.
   - El sistema valida existencia en `FlowRegistry`.
   - Se crea una tarea en estado `running`.
   - Se ejecuta el flow y se retorna un `task_id` junto con el resultado inmediato (si es rápido) o estado `pending`.
2. **Consulta de Tarea (`get_task`):**
   - Claude consulta por un `task_id` previo.
   - El sistema devuelve el estado actual (`completed`, `failed`, `pending_approval`) y el resultado final sanitizado.
3. **Gestión HITL (`approve_task` / `reject_task`):**
   - Si un flow se detiene (pide aprobación), Claude puede aprobar o rechazar la tarea.
   - El sistema reanuda el flow pausado usando el motor de snapshots de `BaseFlow`.

### Edge Cases MVP
- **Flow Inexistente:** Retorna error JSON-RPC -32602 indicando la lista de flows disponibles.
- **Input Malformado:** Captura de excepciones de validación de `BaseFlow` y mapeo a error claro para el LLM.
- **Timeouts:** Los flows largos retornan un `task_id` para que Claude realice polling con `get_task`, evitando bloquear el transporte Stdio.

---

## 3. Diseño Técnico Definitivo

### Componentes de Software

- **`src/mcp/handlers.py`**: Orquestador de ejecución.
  - `handle_execute_flow`: Instancia flows desde `FlowRegistry`.
  - `handle_get_task`: Consulta tabla `tasks` con bypass de RLS (`get_service_client`).
  - `handle_approvals`: Gestiona `pending_approvals` y llama a `flow.resume()`.
- **`src/mcp/auth.py`**: Bridge de identidad.
  - Genera tokens JWT (HS256) usando `python-jose` para comunicaciones internas.
- **`src/mcp/exceptions.py`**: Mapeador central de errores.
  - Convierte excepciones Python (ValueError, DBError) a códigos JSON-RPC (-32602, -32603).

### Interfaces de Tools MCP

| Tool | Argumentos | Retorno |
|:---|:---|:---|
| `execute_flow` | `flow_type`, `input_data` | `task_id`, `status`, `result` |
| `get_task` | `task_id` | `status`, `result`, `error` |
| `approve_task` | `task_id`, `notes` | `status`, `message` |
| `reject_task` | `task_id`, `reason` | `status`, `message` |
| `create_workflow`| `description` | `task_id`, `flow_type` |

### Integración y Verificación de Código Existente
- **Base:** Todos los handlers invocarán `sanitize_output()` de `src/mcp/sanitizer.py`.
- **DB:** Se usará `get_service_client()` de `src/db/session.py` L44 para que el servidor MCP centralizado no sea bloqueado por RLS restrictivos de usuarios.
- **Flows:** Se instanciarán vía `flow_registry.get(name)` de `src/flows/registry.py`.

---

## 4. Decisiones Tecnológicas

- **Unificación JWT:** Se usará `python-jose` para la lógica de **codificación** de nuevos tokens en el bridge, manteniendo coherencia con el `pyproject.toml`.
- **Ejecución Directa:** Se descarta el uso del endpoint de webhooks para ejecución; se favorece la instanciación directa del motor de flows para mayor robustez en entornos sin FastAPI activo (Stdio).
- **Sanitización R3 Ubícua:** Cada handler es responsable de pasar su `output_data` por el sanitizador antes de retornarlo al transporte MCP.

---

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] Claude puede ejecutar el flow `generic_flow` y ver el resultado.
- [ ] Claude puede recuperar el resultado de un `task_id` generado previamente.
- [ ] Un flow pausado por HITL se reanuda correctamente al llamar a `approve_task`.
- [ ] La herramienta `create_workflow` genera un nuevo template consultable en la DB.

### Técnicos
- [ ] Las rutas en `src/mcp/` no contienen código de implementación "placeholder".
- [ ] Los errores de base de datos se reportan con código JSON-RPC -32603 (Internal Error).
- [ ] Los outputs nunca contienen secretos (verificado por `sanitize_output`).

### Robustez
- [ ] El servidor MCP no se cierra ante una excepción no controlada en un flow.
- [ ] El `correlation_id` generado por MCP incluye el prefijo `mcp-`.

---

## 6. Plan de Implementación

1. **Setup de Errores (T1):** Crear `src/mcp/exceptions.py`. Mapear excepciones comunes a códigos JSON-RPC.
2. **Identity Bridge (T2):** Crear `src/mcp/auth.py`. Implementar generación de tokens con `python-jose`.
3. **Motor de Handlers (T3):** Crear `src/mcp/handlers.py`. Implementar `handle_execute_flow` y `handle_get_task`.
4. **HITL & Workflows (T4):** Implementar `handle_approve_task` y el wrapper para `create_workflow` (ArchitectFlow).
5. **Registro de Tools (T5):** Actualizar `src/mcp/tools.py` para registrar las 5 nuevas tools y conectar los handlers.
6. **Validación (T6):** Ejecutar suite de pruebas unitarias sobre handlers y manual vía Claude Desktop con `org_id` real.

---

## 7. Riesgos y Mitigaciones

- **Riesgo:** El implementador copia lógica del plan original que usa `BackgroundTasks`. 
  - **Mitigación:** Este documento prohíbe explícitamente el uso de `api/routes/webhooks.py` para la ejecución MCP.
- **Riesgo:** Timeouts en transporte Stdio por flows lentos.
  - **Mitigación:** Los handlers deben retornar estado `pending` + `task_id` si la ejecución excede 5 segundos.

---

## 8. 🔮 Roadmap (NO implementar ahora)
- **SSE Transport:** Habilitar comunicación bidireccional asíncrona (Sprint 4).
- **Paginación de Tools:** Soporte para >200 tools dinámicas sin penalización en el arranque del servidor.
