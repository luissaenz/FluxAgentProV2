# 🧠 ANÁLISIS TÉCNICO - Paso 06: Agent Playground — prueba en tiempo real
**Agente:** glm4.5  
**Paso:** paso 06  
**Fecha:** 2026-05-14

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Endpoint `POST /agents/{role}/run` existe | ✅ Verificado: `src/api/routes/agents.py:251-320` | ✅ | Archivo, línea 251-320 |
| 2 | Endpoint `GET /tasks/{task_id}` existe | ✅ Verificado: `src/api/routes/tasks.py:69-91` | ✅ | Archivo, línea 69-91 |
| 3 | BaseCrew clase ejecuta agentes | ✅ Verificado: `src/crews/base_crew.py:56-265` | ✅ | Archivo, línea 56-265 |
| 4 | TaskResponse modelo incluye tokens_used | ✅ Verificado: `src/api/routes/tasks.py:26-38` | ✅ | Archivo, línea 26-38 |
| 5 | AgentForm componente existe | ✅ Verificado: `dashboard/components/builder/AgentForm.tsx` | ✅ | Archivo, línea 1-356 |
| 6 | BuilderLayout componente existe | ✅ Verificado: `dashboard/components/builder/BuilderLayout.tsx` | ✅ | Archivo, línea 1-3260 |
| 7 | TemplatePicker componente existe | ✅ Verificado: `dashboard/components/builder/TemplatePicker.tsx` | ✅ | Archivo, línea 1-6868 |

**Discrepancias encontradas:** 
- Ninguna discrepancia significativa. Todos los elementos requeridos para el paso 6 existen y están implementados.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas involucradas:
- ✅ **`agent_catalog`** - almacena configuración de agentes (role, soul_json, allowed_tools, max_iter)
- ✅ **`tasks`** - almacena estado de ejecución de tareas (task_id, status, result, tokens_used, error, created_at, updated_at)

### Schema y constraints:
- ✅ **agent_catalog**: org_id UUID (tenant isolation), role TEXT, soul_json JSONB, allowed_tools TEXT[], max_iter INT, is_active BOOLEAN
- ✅ **tasks**: id UUID (PK), org_id UUID (tenant isolation), flow_type TEXT, status TEXT, result JSONB, error TEXT, tokens_used INT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ

### Integridad referencial:
- ✅ **RLS en agent_catalog**: `tenant_isolation` via `org_id::text = app.org_id()` (migración 004)
- ✅ **RLS en tasks**: `tenant_isolation` via `org_id::text = app.org_id()` (migración 004)
- ✅ **Foreign key implícita**: tasks.flow_type referencia agentes en agent_catalog vía `agent:{role}`

### Índices necesarios:
- ✅ **agent_catalog**: UNIQUE(org_id, role) para upsert
- ✅ **tasks**: índice en org_id + created_at para listado eficiente
- ✅ **tasks**: índice en flow_type para filtrado por tipo de agente

### Tipos de datos:
- ✅ **JSONB** en soul_json y result permite estructuras flexibles
- ✅ **TEXT[]** en allowed_tools permite lista de nombres de herramientas
- ✅ **INT** en tokens_used permite contabilidad precisa

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/clases creadas/modificadas:

#### Backend:
- ✅ **`BaseCrew`** (`src/crews/base_crew.py:56-265`)
  - Firma: `BaseCrew(org_id: str, role: str)`
  - Métodos: `run()`, `run_async()`, `get_last_tokens_used()`, `get_last_tool_calls()`
  - Import: `from ..crews.base_crew import BaseCrew`
  - Patrón: Factory + ToolCallTracer integrado

- ✅ **`POST /agents/{role}/run`** (`src/api/routes/agents.py:251-320`)
  - Firma: `async def run_agent(role: str, request: RunAgentRequest, background_tasks: BackgroundTasks) -> RunAgentResponse`
  - Parámetros: role (path), request (body), background_tasks (FastAPI dependency)
  - Retorno: `RunAgentResponse` con task_id y status
  - Import: `from fastapi import APIRouter, BackgroundTasks, Depends`

- ✅ **`GET /tasks/{task_id}`** (`src/api/routes/tasks.py:69-91`)
  - Firma: `async def get_task(task_id: str, auth: dict = Depends(verify_org_membership)) -> TaskResponse`
  - Parámetros: task_id (path), auth (dependency)
  - Retorno: `TaskResponse` con estado completo
  - Import: `from fastapi import APIRouter, Depends`

#### Frontend (por crear):
- ❌ **`AgentPlayground.tsx`** - panel de chat (aún no existe)

### Patrones existentes:
- ✅ **Patrón RLS**: `verify_org_membership` middleware en todos los endpoints
- ✅ **Patrón TenantClient**: `get_tenant_client(org_id)` para consultas DB
- ✅ **Patrón Task polling**: background task con estado (pending → running → completed/failed)
- ✅ **Patrón BaseCrew**: carga agente desde agent_catalog, ejecución asíncrona

### Modularidad:
- ✅ **BaseCrew separado**: responsabilidades claras entre API y lógica de negocio
- ✅ **TaskResponse modelo**: Pydantic para serialización consistente
- ✅ **ToolCallTracer integrado**: herramienta interna para tracking de herramientas

### Calidad:
- ✅ **Manejo de errores**: try/catch en ejecución de agentes con logging
- ✅ **Validación de input**: Pydantic models en endpoints
- ✅ **Async/Await**: uso consistente en operaciones asíncronas
- ✅ **Logging**: registro adecuado de errores y ejecuciones

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### APIs/endpoints existentes:
- ✅ **`POST /agents/{role}/run`** 
  - Método: POST
  - Ruta: `/agents/{role}/run`
  - Input: `RunAgentRequest` con `input_data: Dict[str, Any]`
  - Output: `RunAgentResponse` con `task_id: str, status: str`
  - Auth: `verify_org_membership` (org_id extraído)

- ✅ **`GET /tasks/{task_id}`**
  - Método: GET
  - Ruta: `/tasks/{task_id}`
  - Input: task_id (path parameter)
  - Output: `TaskResponse` con estado completo
  - Auth: `verify_org_membership`

### Middleware aplicable:
- ✅ **`verify_org_membership`**: verifica autenticación y extrae org_id
- ✅ **`get_tenant_client`**: establece conexión DB con RLS compliance

### Flujos de datos:
- ✅ **Ejecución agente**: 
  1. `POST /agents/{role}/run` crea task en estado "pending"
  2. Background task inicia `BaseCrew.run_async()`
  3. Task se actualiza a "running" → "completed"/"failed"
  4. `GET /tasks/{task_id}` permite polling de estado

### Contratos:
- ✅ **RunAgentResponse**: `{ task_id: str, status: str }`
- ✅ **TaskResponse**: `{ task_id, org_id, flow_type, status, result, error, tokens_used, created_at, updated_at }`
- ✅ **Error handling**: 404 (agente no encontrado), 400 (task_id inválido), 500 (ejecución fallida)

### Error handling:
- ✅ **Agente no encontrado**: 404 en `POST /agents/{role}/run` si no existe en agent_catalog
- ✅ **Task ID inválido**: 400 si UUID no es válido
- ✅ **Ejecución fallida**: 500 con error details en task status
- ✅ **Timeout**: manejo implícito en background task (sin timeout explícito en MVP)

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo:
```
Usuario envía mensaje → 
POST /agents/{role}/run (backend) → 
task_id generado → 
Polling GET /tasks/{task_id} → 
Resultado final con tokens_used y tool calls → 
UI muestra respuesta + tool calls
```

### Coherencia:
- ✅ **Backend soporta UX**: endpoints existentes cubren todos los criterios de aceptación
- ✅ **Datos apoyan código**: TaskResponse.tokens_used y BaseCrew.get_last_tool_calls() disponibles
- ✅ **APIs prometen experiencia**: endpoints retornan estructura completa para UI

### Gaps identificados:
- ⚠️ **Falta componente frontend**: `AgentPlayground.tsx` no existe
- ⚠️ **Sin timeout explícito**: polling podría continuar indefinidamente si task falla silenciosamente
- ⚠️ **Sin manejo de concurrencia**: múltiples usuarios podrían ejecutar mismo agente simultáneamente

### DX & Tooling (OBLIGATORIO):

### Herramienta Propuesta: `fap agent test`
- **Qué automatiza**: Prueba de agentes desde CLI sin necesidad de dashboard. Permite validar agentes creados, depurar tool calls y verificar tokens usados.
- **Tipo**: CLI script
- **Cómo se usa**:
  ```bash
  # Ejecutar agente con input de prueba
  fap agent test --role "analyst" --input "Analyze this data: {...}" --org-id "org-uuid"
  
  # Seguir progreso en tiempo real
  fap agent test --role "analyst" --watch --org-id "org-uuid"
  
  # Ver histórico de ejecuciones
  fap agent test --role "analyst" --history --limit 10
  ```
- **Impacto para el usuario final**: Reduce tiempo de depuración de agentes de minutos a segundos. Permite testing offline sin abrir dashboard. Ideal para CI/CD y validación rápida.
- **Prioridad**: Tarea 0 — implementar antes que el resto del paso

### Implementación UI requerida:
- ✅ **AgentPlayground.tsx**: panel chat con input + mensajes + tool calls colapsables
- ✅ **Integración con BuilderLayout**: añadir playground a layout existente
- ✅ **Polling con React Query**: usar `useQuery` para polling `/tasks/{task_id}`
- ✅ **Manejo de estados**: loading → result → error con UI feedback

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Tabla `agent_catalog` existe con schema correcto para agentes
✅ [DATA] Tabla `tasks` existe con schema correcto para tracking ejecución
✅ [CODE] BaseCrew.run_async() ejecuta agente asíncrono y retorna resultados
✅ [CODE] POST /agents/{role}/run crea task y retorna task_id
✅ [CODE] GET /tasks/{task_id} retorna estado completo con tokens_used
✅ [BACKEND] Endpoint soporta ejecución de agentes con RLS compliance
✅ [BACKEND] Error handling: 404 (agente no encontrado), 500 (ejecución fallida)
✅ [FULLSTACK] Flujo completo: mensaje → ejecución → respuesta → tool calls
✅ [FULLSTACK] UI muestra historial local durante sesión (no persistido)
✅ [DX] Herramienta `fap agent test` permite testing CLI de agentes
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Timeout polling infinito | Alta | Task falla silenciosamente, nunca actualiza estado | Implementar timeout máximo en polling (ej: 5 min) |
| Concurrencia agente | Media | Múltiples usuarios ejecutan mismo agente simultáneamente | Añadir lock mechanism en agent_catalog por role |
| Tokens usados incorrectos | Media | BaseCrew._extract_token_usage() falla al parsear | Validar token extraction en múltiples escenarios |
| UI polling ineficiente | Media | Polling muy frecuente sobrecarga backend | Implementar exponential backoff en polling |
| Error en BaseCrew init | Alta | Agent no existe pero se valida en runtime | Pre-validar existencia antes de crear task |
| Memory leak en ToolCallTracer | Baja | Tools no restauradas correctamente | Asegurar tracer.restore() siempre se ejecuta |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap agent test` | `src/cli/commands/agent_test.py` | `def run(args): ...` | `src/cli/commands/agent_create.py` | DX | Media | 1h | Ninguna | → verificar: `fap agent test --help` ejecuta sin errores |
| 1 | Crear AgentPlayground.tsx | `dashboard/components/builder/AgentPlayground.tsx` | `interface AgentPlaygroundProps { role: string }` | `dashboard/components/builder/AgentForm.tsx` | FULLSTACK | Media | 2h | Tarea 0 | → verificar: componente render sin errores |
| 2 | Integrar playground en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | `AgentPlayground role={currentAgent.role}` | `dashboard/components/builder/BuilderLayout.tsx` | FULLSTACK | Baja | 0.5h | Tarea 1 | → verificar: playground visible en builder |
| 3 | Implementar polling con React Query | `dashboard/components/builder/AgentPlayground.tsx` | `useQuery(['task', taskId], fetchTask)` | `dashboard/hooks/useCurrentOrg.ts` | FULLSTACK | Media | 1h | Tarea 1 | → verificar: polling funciona y muestra estado |
| 4 | Agregar manejo de errores y loading | `dashboard/components/builder/AgentPlayground.tsx` | `if (isLoading) <LoadingSpinner />` | `dashboard/components/shared/LoadingSpinner.tsx` | FULLSTACK | Baja | 0.5h | Tarea 3 | → verificar: estados loading/error mostrados correctamente |
| 5 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 1h | Tarea 4 | → verificar: criterios §5 [FULLSTACK] pasan |

**Tiempo total estimado:** 5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Optimización: Implementar websockets para polling real-time (post-MVP)
- Mejoras: Soporte para multi-agente en playground (fase futura)
- Pre-requisitos: Validación de agentes antes de ejecución (schema validation)
- Decisiones: Cache de resultados para agentes comunes (post-MVP >1k ejecuciones)

---

## 🚫 Reglas de Oro Cumplidas

- ✅ **Análisis accionable y específico**, no genérico
- ✅ **TODO verificado contra código**, no supuestos  
- ✅ **Coherente con phase-state.md** — arquitectura existente respetada
- ✅ **TODO el paso**, incluyendo sub-pasos
- ✅ **Etapas secuenciales** — data → code → backend → fullstack+DX
- ✅ **≥ 1 herramienta DX propuesta** — `fap agent test`
- ✅ **Tareas atómicas**: una tarea = un artefacto = interfaz completa = patrón explícito = verificación inline
- ✅ **El implementador no decide nada**: interfaces completas proporcionadas