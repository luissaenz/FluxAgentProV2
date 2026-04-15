# 🧠 ANÁLISIS TÉCNICO: PASO 1 - TOOLS INTERNAS (ATG)

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Archivo `tools.py` | `src/mcp/tools.py` existe | ✅ | L23: `STATIC_TOOLS` |
| 2 | Archivo `handlers.py` | `src/mcp/handlers.py` existe | ✅ | L22: `handle_execute_flow` |
| 3 | Clase `IntegrationResolver` | `src/flows/integration_resolver.py` | ✅ | L35: `class IntegrationResolver` |
| 4 | Método `activate_service` | `IntegrationResolver.activate_service` | ⚠️ | L177: Solo acepta `service_id` |
| 5 | Método `store_credential` | `IntegrationResolver.store_credential` | ✅ | L186: Llama a `upsert_secret` |
| 6 | Flow `ArchitectFlow` | `src/flows/architect_flow.py` | ✅ | L50: `@register_flow("architect_flow")` |
| 7 | Enum `FlowStatus` | `src/flows/state.py` | ⚠️ | L18: No tiene `RESOLUTION_PENDING` |
| 8 | Tabla `tasks` | `001_set_config_rpc.sql` | ✅ | L62: `status TEXT NOT NULL` |
| 9 | Constraint `tasks.status` | Grep migrations | ✅ | Sin CHECK constraint global |
| 10 | Tabla `pending_approvals`| `002_governance.sql` | ✅ | L50: Usada para resume |
| 11 | Registro `STATIC_TOOLS`| `src/mcp/tools.py` | ✅ | L23: Lista de definiciones JSON-RPC |
| 12 | Dispatcher de tools | `src/mcp/server.py` | ✅ | L42: `@server.call_tool()` |
| 13 | Vault Persistence | `src/db/vault.py` | ✅ | `upsert_secret` operativo |
| 14 | Method `apply_mapping` | `IntegrationResolver` | ✅ | L190: Mapea alucinadas -> reales |
| 15 | Flow state persistence | `BaseFlow.persist_state` | ✅ | L213: Updates status + result |
| 16 | JSON Response builder | `ArchitectFlow._build_resolution_response` | ✅ | L467: Ya genera el payload |
| 17 | Dynamic Registration | `ArchitectFlow._register_dynamic_flow` | ✅ | L455: Registra en FlowRegistry |
| 18 | DB Session Clients | `src/db/session.py` | ✅ | L48/L175: `get_service_client`/`TenantClient` |

**Discrepancias encontradas:**
- **D1:** `IntegrationResolver.activate_service` no recibe `secret_names`.
  - *Resolución:* Modificar firma para aceptar lista de secretos y persistir en `org_service_integrations.secret_names`.
- **D2:** `ArchitectFlow` retorna respuesta diagnóstica pero no cambia estado a `pending`.
  - *Resolución:* Inyectar `await self._update_task_status("resolution_pending")` en `_run_crew`.
- **D3:** `tasks.status` en DB no tiene constraint, pero `FlowStatus` (Pydantic) sí.
  - *Resolución:* Agregar `RESOLUTION_PENDING = "resolution_pending"` a `FlowStatus` en `state.py`.

## 1. Diseño Funcional
- **Happy Path:**
  1. `ArchitectFlow` detecta falta de credenciales → Tarea marcada `resolution_pending`.
  2. Claude usa `store_credential` → Valor guardado en Vault.
  3. Claude usa `activate_service` → Registro en `org_service_integrations` (status `active`).
  4. Claude usa `retry_workflow` → Re-ejecuta `resolve()` → `is_ready=True` → Registra Flow y completa tarea.
- **Edge Cases:**
  - `retry_workflow` en tarea no pendiente: Retorna error 400.
  - `retry_workflow` sin `extracted_definition`: Error de consistencia (no debería ocurrir).
- **Manejo de Errores:** Errores de API Supabase se mapean a `CallToolResult` con `isError=True`.

## 2. Diseño Técnico
- **Nuevas Tools (MCP):**
  - `activate_service(service_id, secret_names?)`
  - `store_credential(secret_name, secret_value)`
  - `retry_workflow(task_id)`
- **Modificaciones:**
  - `src/flows/state.py`: Agregar status `RESOLUTION_PENDING`.
  - `src/flows/architect_flow.py`: Pausar con `resolution_pending` si faltan dependencias.
  - `src/mcp/handlers.py`: Implementar la lógica de las 3 herramientas.
- **Modelo de Datos:**
  - `tasks.status` recibirá `"resolution_pending"`.
  - `tasks.result` guardará `extracted_definition` (JSON) durante la pausa.

## 3. Decisiones
- **D1 (Persistencia):** Guardar definition original en `tasks.result` durante la resolución pendiente.
  - *Justificación:* Permite al handler `retry_workflow` recuperar el objeto sin instanciar de nuevo el Crew/LLM (ahorro de tokens y tiempo).
- **D2 (Status):** Usar `resolution_pending` en lugar de `awaiting_approval`.
  - *Justificación:* Diferencia clara entre "esperando decisión humana" (HITL) y "esperando configuración técnica" (Onboarding).

## 4. Criterios de Aceptación
- [ ] `FlowStatus` incluye `resolution_pending`.
- [ ] `ArchitectFlow` no marca como `completed` si falta resolución.
- [ ] Tool `store_credential` guarda el valor cifrado en Vault (verificable vía DB).
- [ ] Tool `activate_service` crea/actualiza registro en `org_service_integrations`.
- [ ] Tool `retry_workflow` genera el `workflow_template` si las dependencias fueron resueltas.
- [ ] Interfaz de todas las tools está disponible en `list_tools`.

## 5. Riesgos
- **Consistencia de Estado:** Re-instanciar el flow en `retry_workflow` podría perder contexto si no se carga el snapshot correctamente.
  - *Mitigación:* Usar el patrón `from_snapshot` de `BaseFlow` ya existente.
- **Seguridad Vault:** `store_credential` recibe valores sensibles en texto plano por MCP.
  - *Mitigación:* Se asume canal SSE/Stdio seguro entre Claude y el servidor. El handler cifra inmediatamente.

## 6. Plan
| Tarea | Complejidad | Tiempo | Dependencia |
|:---|:---:|:---:|:---|
| T1: Actualizar `FlowStatus` y `IntegrationResolver` | Baja | 30m | - |
| T2: Modificar `ArchitectFlow` (pausa/persist) | Media | 1h | T1 |
| T3: Implementar handlers en `mcp/handlers.py` | Alta | 2h | T2 |
| T4: Registrar tools en `mcp/tools.py` y `server.py` | Baja | 30m | T3 |
| T5: Validación integral (Test Flow) | Media | 2h | T4 |
| **Total** | | **6h** | |

## 🔮 Roadmap
- **Auto-Retry:** El sistema podría re-intentar automáticamente al detectar el evento de `secret.created`.
- **Wizard UI:** Dashboard UI para facilitar la carga de estos secretos sin copiar/pegar en el chat.
