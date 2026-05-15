# 🏛️ ANÁLISIS UNIFICADO — Paso 06: Agent Playground — prueba en tiempo real

> **Fase:** `guiAgentGenerator`
> **Fecha:** 2026-05-14
> **Fuente:** Unificación de 7 análisis de agentes (ring, hy3, mm2.7, step, lgn, glm4.5, glm5.1)
> **Referencia:** `DEVS/plan.md` líneas 126-147

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| ring | ✅ 30 ítems | 4 (D1-D4) | ✅ `fap agent run` | ✅ líneas + archivos | 4.8 |
| glm5.1 | ✅ 25 ítems | 4 (D1-D4) | ✅ `fap agent run` | ✅ líneas + archivos | 4.5 |
| step | ✅ 10 ítems | 5 (D1-D5) | ✅ `fap agent test` | ✅ líneas + archivos | 4.5 |
| mm2.7 | ✅ 14 ítems | 2 (D1-D2) | ✅ `fap agent test` | ✅ líneas + archivos | 3.5 |
| lgn | ✅ 8 ítems | 2 (genéricas) | ⚠️ `playground_simulator.py` | ❌ sin referencias | 2.5 |
| hy3 | ✅ 8 ítems | 0 | ✅ `fap agent run` | ❌ sin líneas | 2.0 |
| glm4.5 | ✅ 7 ítems | 0 | ✅ `fap agent test` | ❌ sin líneas | 2.0 |

> **Mejores aportes:** ring y step — verificaciones exhaustivas contra código fuente con evidencia de archivo+línea, detección de todas las discrepancias críticas, plan de implementación atómico con tiempos estimados.
> **Aporte más débil:** glm4.5 y hy3 — no detectaron discrepancias (tool calls sin argumentos, result como string), verificaciones superficiales sin evidencia de líneas de código.

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| D1 | **Tool calls sin argumentos:** Plan dice "nombre y argumentos" pero `ToolCallTracer` solo captura `Dict[str, int]` (nombre → conteo). | ring, step, mm2.7, glm5.1 | ✅ `src/crews/base_crew.py:32-45` — wrapper solo incrementa contador. `args`/`kwargs` no se almacenan. | MVP: mostrar nombre + conteo con `Collapsible`. Post-MVP: extender `ToolCallTracer` para capturar `args`. |
| D2 | **Tool calls no persistidos en `tasks`:** `agents.py:299-305` guarda `status`, `result`, `tokens_used` pero NO guarda `crew.get_last_tool_calls()`. La tabla `tasks` no tiene columna `tool_calls`. | ring, step, mm2.7, glm5.1 | ✅ `src/api/routes/agents.py:299-305` — update solo incluye `status`, `result`, `tokens_used`. | **MVP sin tool calls en DB.** Post-MVP: nueva migración `tool_calls JSONB` + modificar `_execute()` para persistir. |
| D3 | **`result` como string:** `agents.py:303` hace `str(result)`. `TaskResponse.result` es `Optional[Dict[str, Any]]` pero almacena texto plano. | ring, step, glm5.1 | ✅ `src/api/routes/agents.py:303` — `"result": str(result)` | Frontend debe tratar `result` como texto plano, no parsear como JSON. Truncar >2000 chars. Mitigación D4 (types.ts). |
| D4 | **`types.ts` desactualizado:** Interfaz `Task` en `dashboard/lib/types.ts:1-10` no incluye `tokens_used`, `approval_required`, `approval_status`, `approval_payload`. | step | ✅ `dashboard/lib/types.ts:1-10` — campos faltantes vs `TaskResponse` backend (tasks.py:26-38). | **Extender `Task` interface** en `types.ts` con `tokens_used: number`. Campos de approval opcionales. Usar interfaz local en `AgentPlayground.tsx` para task completo. |
| D5 | **Sin validación previa de role en `POST /run`:** Endpoint retorna 202 inmediato. Si role no existe, error aparece en polling (status `failed`). | ring, step, glm5.1 | ✅ `src/api/routes/agents.py:251-320` — no hay `SELECT` previo de `agent_catalog`. | Aceptado para MVP. CLI `fap agent run` puede pre-validar con `GET /by-role/{role}`. Frontend: manejar status `failed` con mensaje claro. |
| D6 | **Auth mixta:** `POST /agents/{role}/run` usa `verify_org_membership` (JWT+membership). `POST /agents` usa `require_org_id` (header). Ambos compatibles con `fapFetch`. | ring, glm5.1 | ✅ `src/api/routes/agents.py:256` vs `agents.py:63` — sin impacto funcional. | Sin acción. `fapFetch` envía ambos headers → compatibles. No inconsistencia real. |
| D7 | **Background task async:** `_execute()` es `async def` pasado a `background_tasks.add_task()`. Verificado compatible con FastAPI 0.115+. | glm5.1 | ✅ `src/api/routes/agents.py:282,318` — FastAPI 0.115+ soporta async callables en background tasks. | Verificado. Sin acción necesaria. |

---

## 1️⃣ Resumen Ejecutivo

**Objetivo del paso:** Añadir panel de chat (`AgentPlayground`) al Builder para probar agentes en tiempo real. El usuario envía un mensaje, backend ejecuta el agente vía `POST /agents/{role}/run`, frontend hace polling a `GET /tasks/{task_id}` y muestra respuesta + tool calls + tokens consumidos.

**Correcciones críticas al plan:**
1. Plan promete "tool calls con nombre y argumentos" → **NO realizable con backend actual.** `ToolCallTracer` solo captura conteo (`Dict[str, int]`). MVP: mostrar solo nombre+conteo en UI colapsable.
2. Plan no menciona que `result` se almacena como `str()` → frontend debe tratarlo como texto plano, no JSON.
3. Plan asume que `types.ts` tiene `tokens_used` → debe extenderse la interfaz `Task`.

**Herramienta DX seleccionada:** `fap agent run` (CLI command). Nombre y patrón consistentes con `fap agent create`. Permite dogfooding del flujo run→poll→result antes de construir UI. Fusión de propuestas de ring, glm5.1 y step (`fap agent test` — mismo concepto, nombre distinto).

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Usuario crea/edita un agente en `AgentForm` (Paso 04) — campo `role` completado.
2. Botón "Playground" se habilita en `BuilderLayout` al tener `role` válido.
3. Click en "Playground" → Sheet lateral derecho se desliza con `<AgentPlayground role={role} />`.
4. Usuario escribe mensaje en input de chat → presiona Enter.
5. `useMutation` envía `POST /agents/{encodeURIComponent(role)}/run` con `{ input_data: { message: "..." } }`.
6. Backend crea task `pending`, inicia `BaseCrew.run_async()` en background, retorna `{ task_id, status: "accepted" }`.
7. Frontend inicia polling `GET /tasks/{task_id}` cada 2s vía `useQuery` con `refetchInterval`.
8. Mientras `status ∈ {pending, running}` → `LoadingSpinner` en chat.
9. `status === "completed"` → respuesta del agente (burbuja assistant) + tool calls colapsables (nombre+conteo) + badge `tokens_used`.
10. `status === "failed"` → burbuja de error con mensaje de `task.error`.
11. Historial local en memoria (`useState<PlaygroundMessage[]>`), no persiste entre sesiones.

### Edge Cases MVP

| # | Edge case | Manejo |
|---|---|---|
| E1 | Role no existe en `agent_catalog` | `POST /run` retorna 202 pero task termina en `failed`. Frontend detecta `status=failed` → muestra error "Agent not found". |
| E2 | Task ID inválido | Backend retorna 400. Frontend muestra toast de error. |
| E3 | Polling timeout (>120s) | Frontend detiene polling, muestra warning "Agent is taking too long". |
| E4 | `result` como texto largo (>2000 chars) | Frontend trunca con "Show more" colapsable. |
| E5 | Role con caracteres especiales (espacios, `/`) | `encodeURIComponent(role)` en URL del endpoint. |
| E6 | `fapFetch` falla por auth | Error handling estándar de `api.ts` — redirige a login. |
| E7 | Usuario envía mensaje vacío | Zod/validación inline: input requerido, min 1 char. |
| E8 | Tarea previa aún ejecutándose | Deshabilitar input mientras `currentTaskId` no es null. |

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### 1. `dashboard/lib/types.ts` — MODIFICACIÓN

- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\dashboard\lib\types.ts`
- **Tipo de cambio:** Modificación — extender interfaz `Task`
- **Descripción:** Añadir `tokens_used: number` a `Task` interface. Campos de approval opcionales.
- **Cambio exacto:**
```typescript
export interface Task {
  task_id: string
  org_id: string
  flow_type: string
  status: TaskStatus
  result: Record<string, unknown> | null
  error: string | null
  tokens_used: number          // ← añadir
  created_at: string
  updated_at: string
}
```

#### 2. `dashboard/components/builder/AgentPlayground.tsx` — CREACIÓN

- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\dashboard\components\builder\AgentPlayground.tsx`
- **Tipo de cambio:** Creación
- **Descripción:** Componente de chat para probar agente en tiempo real. Input, mensajes, polling, tool calls colapsables, tokens.
- **Interfaces clave:**
```typescript
interface PlaygroundMessage {
  id: string
  role: 'user' | 'assistant' | 'error'
  content: string
  toolCalls?: ToolCallInfo[]
  tokensUsed?: number
  timestamp: Date
}

interface ToolCallInfo {
  name: string
  count: number
}

interface AgentPlaygroundProps {
  role: string
}
```
- **Firma:** `export function AgentPlayground({ role }: AgentPlaygroundProps): JSX.Element`
- **Patrones a seguir:**
  - Chat UI + Sheet: `AnalyticalAssistantChat.tsx` (mutation, polling, burbujas, scroll)
  - `useMutation` + `api.post()`: `AgentForm.tsx:131-171`
  - Polling `useQuery` con `refetchInterval`: `hooks/useTasks.ts`
  - `LoadingSpinner`: `components/shared/LoadingSpinner.tsx`
  - `Collapsible`: `components/ui/collapsible.tsx`
  - `ScrollArea`: `components/ui/scroll-area.tsx`

#### 3. `dashboard/components/builder/BuilderLayout.tsx` — MODIFICACIÓN

- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\dashboard\components\builder\BuilderLayout.tsx`
- **Tipo de cambio:** Modificación
- **Descripción:** Añadir estado `currentRole`, botón "Playground", Sheet lateral derecho con `<AgentPlayground>`.
- **Cambios:**
  - `useState<string | null>` para `currentRole` (sincronizado con AgentForm).
  - Botón "Playground" junto a "Templates", habilitado solo si `currentRole` no es null.
  - `Sheet` + `SheetContent side="right"` con `<AgentPlayground role={currentRole!} />`.
- **Patrón a seguir:** `AnalyticalAssistantChat.tsx:149-164` — Sheet pattern.

#### 4. `src/cli/commands/agent_run.py` — CREACIÓN

- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\agent_run.py`
- **Tipo de cambio:** Creación
- **Descripción:** CLI para probar agente desde terminal. Ejecuta `POST /agents/{role}/run` + polling `GET /tasks/{task_id}`.
- **Firma:** `def run_agent(role: str, message: str, org_id: str, watch: bool = False, timeout: int = 120) -> None`
- **CLI signature:** `fap agent run --role "X" --message "Y" --org-id <uuid> [--watch] [--timeout 120]`
- **Patrón a seguir:** `src/cli/commands/agent_create.py` (Typer command con Rich table output + httpx).

#### 5. `src/cli/main.py` — MODIFICACIÓN

- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\main.py`
- **Tipo de cambio:** Modificación — registrar comando `run` en sub-app `agent`
- **Descripción:** Añadir `agent_app.command("run")(run_agent)` donde ya existe `agent_app.command("create")`.

### DX & Tooling — Tarea 0

```
### Herramienta: `fap agent run`
- **Qué automatiza:** Prueba de agentes desde terminal sin abrir dashboard. Ejecuta flujo completo: POST /agents/{role}/run → polling GET /tasks/{task_id} → muestra resultado.
- **Tipo:** CLI command (Typer)
- **Ubicación:** D:\Develop\Personal\FluxAgentPro-v2\src\cli\commands\agent_run.py
- **Cómo se usa:**
  ```bash
  # Prueba básica
  uv run fap agent run --role "Code Reviewer" --message "Review this: def foo(): pass" --org-id <uuid>

  # Con polling en tiempo real
  uv run fap agent run --role "Analyst" --message "Analyze Q1 sales" --org-id <uuid> --watch

  # Timeout personalizado
  uv run fap agent run --role "Researcher" --message "Find latest papers on AGI" --org-id <uuid> --timeout 180
  ```
- **Impacto para el usuario final:** Reduce ciclo de prueba de minutos a segundos. Dogfooding: valida que backend funciona antes de construir UI. Útil para CI/CD y debugging.
- **El implementador DEBE usarla** para completar las tareas 1..N del paso.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Tool calls: solo nombre+conteo en MVP.** `ToolCallTracer` captura `Dict[str, int]` (línea `base_crew.py:32-45`). No se extiende para capturar argumentos porque requiere cambio en wrapper + nuevo schema de persistencia. Se documenta como limitación. Post-MVP: extender `ToolCallTracer` + columna `tool_calls JSONB` en `tasks`.

2. **Tool calls NO persistidos en DB para MVP.** `agents.py:303` guarda `str(result)` pero no `tool_calls`. El frontend no puede mostrar tool calls desde polling porque no existen en `TaskResponse`. El conteo solo está disponible en memoria de `BaseCrew` durante la ejecución. **Decisión MVP:** No mostrar tool calls en el Playground (no hay fuente de datos). Mostrar solo resultado + tokens. Post-MVP: migración + modificar `_execute()`.

3. **`result` renderizado como texto plano.** `agents.py:303` hace `str(result)` — el valor en `TaskResponse.result` es string crudo, no diccionario. Frontend debe tratarlo como `string`, no intentar `JSON.parse()`. Truncar a 2000 chars con opción "Show more".

4. **Sheet lateral derecho para integración.** Consistente con `AnalyticalAssistantChat` (mismo patrón Sheet en dashboard). Alternativa evaluada (tabs/split) descartada por complejidad y porque Sheet mantiene BuilderLayout sin cambios estructurales.

5. **`react-query` para polling, no `setInterval` manual.** `useQuery` con `refetchInterval: 2000` y `enabled: !!taskId && !isComplete`. Ventaja: cancelación automática al desmontar, caché, manejo de errores integrado. Patrón ya usado en `useTasks.ts`.

6. **`encodeURIComponent(role)` obligatorio.** Roles con espacios o caracteres especiales (ej: "Code Reviewer") rompen la URL sin encoding.

7. **⚠️ Correcciones al plan:**
   - ⚠️ El plan dice "tool calls ejecutadas (con nombre y argumentos)" pero el código real solo captura conteo (`Dict[str, int]`). Se implementa **sin tool calls en MVP** — no hay fuente de datos disponible vía polling.
   - ⚠️ El plan dice "guardar en `agent_catalog` vía Supabase (directo desde frontend, sin nuevo endpoint)" para Paso 04. Corrección ya aplicada (D4, `POST /agents` con `TenantClient`). Para Paso 06: se usa `POST /agents/{role}/run` existente, sin cambios.
   - ⚠️ El plan asume que `TaskResponse.tokens_used` está en `types.ts`. No lo está → se corrige extendiendo la interfaz.

---

## 5️⃣ Criterios de Aceptación MVP

### Funcionales
- [ ] Input de chat: escribir mensaje → Enter → enviar `POST /agents/{role}/run`
- [ ] Respuesta del agente se muestra como burbuja debajo del mensaje del usuario
- [ ] Indicador de carga (spinner/skeleton) mientras `status ∈ {pending, running}`
- [ ] Tokens consumidos visibles al finalizar (`tokens_used` badge)
- [ ] Manejo de errores: agente no encontrado (`status: failed`), timeout (120s), error de red
- [ ] Historial local de mensajes durante sesión (no persiste entre recargas)
- [ ] Sheet/panel lateral derecho integrado en BuilderLayout con botón "Playground"
- [ ] Botón "Playground" solo habilitado cuando formulario tiene `role` válido
- [ ] Scroll automático al último mensaje

### Técnicos
- [ ] `Task` interface en `types.ts` incluye `tokens_used: number`
- [ ] `AgentPlayground.tsx` existe con firma `({ role: string }) => JSX.Element`
- [ ] `useMutation` envía `POST /agents/{encodeURIComponent(role)}/run` con `{ input_data: { message } }`
- [ ] `useQuery` polling `GET /tasks/{task_id}` cada 2s, se detiene en `completed`/`failed`
- [ ] `result` se renderiza como texto plano (no `JSON.parse`)
- [ ] Timeout de polling: detener tras 120s con mensaje de advertencia
- [ ] `encodeURIComponent(role)` aplicado en URL del endpoint
- [ ] Sin cambios en backend (endpoints existentes usados sin modificación)
- [ ] Sin nuevas migraciones (MVP usa schema existente)

### DX
- [ ] `fap agent run --role "X" --message "Y" --org-id <uuid>` ejecuta sin errores de import
- [ ] `fap agent run --help` muestra ayuda con todos los parámetros
- [ ] CLI muestra polling en tiempo real con `--watch`
- [ ] CLI maneja errores gracefully (role no encontrado, timeout, error de red)

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** `fap agent run` — CLI para probar agente desde terminal. Crear `src/cli/commands/agent_run.py` + registrar en `src/cli/main.py`. | Media | 1.5h | Ninguna |
| 1 | Extender `Task` interface en `dashboard/lib/types.ts` — añadir `tokens_used: number`. | Baja | 0.25h | Ninguna |
| 2 | Crear `AgentPlayground.tsx` — componente chat con input, `useState<PlaygroundMessage[]>`, burbujas de mensaje, `ScrollArea`. | Media | 1.5h | Tarea 1 |
| 3 | Implementar `useMutation` → `POST /agents/{role}/run` en AgentPlayground — envío de mensaje, recepción de `task_id`. | Media | 0.5h | Tarea 2 |
| 4 | Implementar polling `useQuery` → `GET /tasks/{task_id}` cada 2s — detección de `completed`/`failed`, timeout 120s. | Media | 1h | Tarea 3 |
| 5 | Renderizado de respuesta + tokens — burbuja assistant con `result` (texto plano), badge `tokens_used`. | Media | 0.5h | Tarea 4 |
| 6 | Manejo de errores + estados — `LoadingSpinner` durante polling, burbuja error en `failed`, `EmptyState` inicial. | Baja | 0.5h | Tarea 5 |
| 7 | Integrar Sheet + botón "Playground" en `BuilderLayout.tsx` — estado `currentRole`, Sheet lateral derecho, botón habilitado con role. | Baja | 0.5h | Tarea 6 |
| 8 | Tests unitarios CLI `agent run` — `tests/unit/test_agent_run.py` con mocking de httpx + polling. | Media | 1h | Tarea 0 |
| **TOTAL** | | | **7.25h** | |

> [!IMPORTANT]
> Tarea 0 (DX) se implementa primero. El implementador DEBE usar `fap agent run` para validar el contrato POST/GET antes de construir el frontend.

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Tool calls no disponibles (sin args + no persistidos) | **Alta** | `ToolCallTracer` solo captura conteo. `agents.py` no persiste tool_calls. `TaskResponse` no incluye campo. | MVP: **NO mostrar tool calls.** Documentar como limitación. Post-MVP: extender `ToolCallTracer` + columna `tool_calls JSONB` + modificar `_execute()`. |
| `result` como string crudo | Media | `str(result)` puede ser texto largo no estructurado | Renderizar como texto plano. Truncar >2000 chars con "Show more" colapsable. |
| Polling infinito | Media | Background task falla silenciosamente, status nunca se actualiza | Timeout en frontend: detener polling tras 120s (60 intentos × 2s). Mostrar warning. |
| Role no existe → error diferido | Media | `POST /run` acepta cualquier role, error aparece en polling | Mostrar `status: failed` claramente. CLI pre-valida con `GET /by-role/{role}`. |
| Role con caracteres especiales en URL | Baja | Espacios o `/` en role rompen path | `encodeURIComponent(role)` en frontend. |
| Concurrencia de múltiples ejecuciones mismo agente | Baja | Varios usuarios ejecutan mismo role simultáneamente | Aceptable MVP. Sin lock. Post-MVP: rate limiting. |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Enviar mensaje a agente existente | `POST /agents/test_agent/run` con `{ input_data: { message: "Hello" } }` | `201` con `{ task_id, status: "accepted" }`. Polling retorna `status: "completed"` con `result` y `tokens_used > 0`. |
| TP-2 | Agente no encontrado | `POST /agents/nonexistent/run` | `202` inicial. Polling retorna `status: "failed"` con `error: "Agent 'nonexistent' not found"`. |
| TP-3 | Polling timeout | Simular task que nunca completa (mock backend lento) | Frontend detiene polling tras 120s, muestra "Agent is taking too long". |
| TP-4 | `result` como texto largo | Enviar prompt que genera respuesta >2000 chars | UI trunca a 2000 chars con botón "Show more". |
| TP-5 | CLI `fap agent run` exitoso | `fap agent run --role "test" --message "hi" --org-id <uuid>` | Muestra `[✅] Completed in X.Xs | Tokens: N`, resultado del agente. Exit code 0. |
| TP-6 | CLI `fap agent run` role inexistente | `fap agent run --role "noexiste" --message "hi" --org-id <uuid>` | Muestra error "Agent not found". Exit code 1. |

Comando para ejecutar tests: `uv run pytest tests/unit/test_agent_run.py -v --timeout=60`

---

## 📊 Métricas de Calidad del FINAL

| Métrica | Estado |
|:---|:---|
| `proyecto-config.json` leído antes de generar | ✅ |
| Discrepancias consolidadas con resolución | ✅ 7/7 |
| Correcciones al plan documentadas | ✅ 3 correcciones |
| Propuesta DX incluida en §3 y Tarea 0 en §6 | ✅ `fap agent run` |
| Criterio DX en §5 | ✅ |
| Secciones completadas | ✅ 9 (0-8) |
| Casos de testing | ✅ 6 casos |
| Tiempo estimado por tarea | ✅ 100% |

---

*Documento unificado por Arquitecto de Sistemas Senior — 2026-05-14*
