# 📊 ANÁLISIS TÉCNICO - Paso 6: Agent Playground

**Agente:** lgn  
**Fecha:** 2026-05-14  
**Paso:** 6 - Agent Playground — prueba en tiempo real

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Endpoint `POST /agents/{role}/run` existe | ✅ grep en src/api/routes/agents.py | ✅ | agents.py:251-320 |
| 2 | Endpoint `GET /tasks/{task_id}` existe | ✅ grep en src/api/routes/tasks.py | ✅ | tasks.py:69-91 |
| 3 | TaskResponse tiene tokens_used | ✅ grep en tasks.py | ✅ | tasks.py:33 |
| 4 | ToolCallTracer trackea herramientas | ✅ grep en src/crews/base_crew.py | ✅ | base_crew.py:23-49 |
| 5 | BaseCrew.run_async() implementado | ✅ grep en base_crew.py | ✅ | base_crew.py:215-258 |
| 6 | api client en frontend existe | ✅ grep en dashboard/lib/api.ts | ✅ | api.ts:54-77 |
| 7 | BuilderLayout con AgentForm/TemplatePicker | ✅ grep en dashboard/components/builder/ | ✅ | BuilderLayout.tsx |
| 8 | useQuery hook disponible | ✅ grep en dashboard (TanStack) | ✅ | AgentForm.tsx:113-121 |

**Discrepancias encontradas:**
- ⚠️ El plan menciona `TaskResponse.tokens_used` pero en el frontend no hay ejemplo de polling implementado aún
- ⚠️ No existe `AgentPlayground.tsx` — debe crearse desde cero

---

## 1️⃣ Análisis de Datos (ETAPA 1)

- **Schema:** No se requieren cambios de schema. La tabla `tasks` ya existe con los campos necesarios.
- **Integridad referencial:** Los task records se crean con `org_id` vía `verify_org_membership` middleware.
- **RLS policies:** El endpoint `/tasks/{task_id}` usa `verify_org_membership` que aplica RLS automáticamente.
- **Índices necesarios:** La tabla `tasks` ya tiene índices para `id` y `org_id`.
- **Tipos de datos:** `tokens_used` es `int` default 0 — compatible con lo esperado.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes backend relevantes:

**`POST /agents/{role}/run` — src/api/routes/agents.py:251-320**
```python
async def run_agent(
    role: str,
    request: RunAgentRequest,  # { input_data: Dict }
    background_tasks: BackgroundTasks,
    auth: dict = Depends(verify_org_membership),
) -> RunAgentResponse  # { task_id: str, status: str }
```
- Crea task en estado `pending`
- Ejecuta en background con `BaseCrew.run_async()`
- Retorna `task_id` para polling

**`GET /tasks/{task_id}` — src/api/routes/tasks.py:69-91**
```python
async def get_task(task_id: str, auth: dict = Depends(verify_org_membership)) -> TaskResponse
```
- Retorna: `task_id`, `status`, `result`, `error`, `tokens_used`
- Validación UUID incluida

### Patrón a seguir para el playground:
- `dashboard/components/builder/AgentForm.tsx` — patrón de formulario con react-hook-form
- `dashboard/lib/api.ts` — patrón api.get/post para llamadas backend

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints existentes:

| Endpoint | Método | Auth | Payload | Respuesta |
|---|---|---|---|---|
| `/agents/{role}/run` | POST | `verify_org_membership` | `{input_data: {...}}` | `{task_id, status}` |
| `/tasks/{task_id}` | GET | `verify_org_membership` | - | `{task_id, status, result, error, tokens_used}` |

### Flujo de datos:
1. Frontend llama `POST /agents/{role}/run` con `input_data: { message: string }`
2. Backend crea task `pending` → ejecuta agente en background → actualiza a `completed`
3. Frontend hace polling a `GET /tasks/{task_id}` hasta que `status === 'completed'`
4. Frontend muestra `result`, `tokens_used`, y tool calls

### Error handling:
- 404: Agente no encontrado (role no existe en agent_catalog)
- 400: task_id inválido (UUID)
- `status: failed` en task con `error` field

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo:
```
User types message → AgentForm → api.post('/agents/{role}/run') 
→ Backend creates task + runs agent → Polling GET /tasks/{task_id}
→ Status: pending → running → completed
→ Display: response text + tool calls + tokens_used
```

### Herramienta Propuesta: `scripts/playground_simulator.py`
- **Qué automatiza:** Simula requests de playground para testing sin UI
- **Tipo:** script Python
- **Cómo se usa:** `uv run python scripts/playground_simulator.py --role "analyst" --message "test"`
- **Impacto para el usuario final:** Permite testear el flujo de playground via CLI antes de usar UI

### Gaps identificados:
- ❌ No hay componente `AgentPlayground.tsx` existente
- ❌ El backend no expone tool_calls individuales — solo el conteo en `BaseCrew.get_last_tool_calls()`
- ⚠️ Necesario agregar campo `tool_calls` al task result para mostrar en playground

---

## 5️⃣ Criterios de Aceptación

- ✅ [DATA] Tabla `tasks` existe con `tokens_used` columna
- ✅ [CODE] Endpoint `POST /agents/{role}/run` crea task y retorna task_id
- ✅ [BACKEND] Endpoint `GET /tasks/{task_id}` retorna status y result
- ✅ [FULLSTACK] `AgentPlayground.tsx` muestra chat con historial local
- ✅ [DX] `ToolCallTracer` captura tool invocations en backend

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Polling infinito si task falla | Media | Timeout sin error handling | Implementar max retries + timeout visual |
| Tool calls no disponibles en response | Alta | Solo `_last_tool_calls` en memoria | Agregar campo `tool_calls` a task record |
| Race condition en polling | Baja | Múltiples requests simultáneos | Debounce polling, cancelar requests previos |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | DX: Simulador playground | `scripts/playground_simulator.py` | `def main(role, message): ...` | — | DX | Baja | 0.5h | Ninguna | → verificar: `uv run scripts/playground_simulator.py --help` |
| 1 | Modificar tasks schema | `supabase/migrations/00N_alter_tasks_tool_calls.sql` | Añadir columna `tool_calls JSONB` | `supabase/migrations/004_agent_catalog.sql` | DATA | Baja | 0.5h | Ninguna | → verificar: migración aplica sin errores |
| 2 | Actualizar endpoint tasks | `src/api/routes/tasks.py` | Incluir `tool_calls` en TaskResponse | `tasks.py :: _task_to_response` | BACKEND | Media | 1h | Tarea 1 | → verificar: `uv run pytest tests/unit/test_tasks.py` |
| 3 | Actualizar run_agent | `src/api/routes/agents.py` | Guardar tool_calls en task record | `agents.py :: _execute` | BACKEND | Media | 1h | Tarea 2 | → verificar: `curl -X POST /agents/test/run` funciona |
| 4 | Crear AgentPlayground | `dashboard/components/builder/AgentPlayground.tsx` | `function AgentPlayground({ role }: { role: string })` | `AgentForm.tsx` + `api.ts` | FULLSTACK | Alta | 2h | Tareas 1-3 | → verificar: Storybook renderiza sin errores |
| 5 | Integrar en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | Añadir tabs o botón para playground | `BuilderLayout.tsx` | FULLSTACK | Baja | 0.5h | Tarea 4 | → verificar: E2E test pasa |

**Tiempo total estimado:** 5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- WebSocket en lugar de polling para resultados en tiempo real
- Historial persistente de playground sessions
- Exportar conversación como JSON
- Compatibilidad con crew multi-agente (no solo single agent)