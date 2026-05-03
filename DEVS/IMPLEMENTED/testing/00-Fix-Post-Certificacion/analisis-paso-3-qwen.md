# Análisis Técnico — Paso 3: Tool Calling Real (Agente usa herramienta durante ejecución)

**Agente:** qwen
**Fecha:** 2026-05-03
**Paso asignado:** Paso 3 — Tool Calling Real
**Plan referencia:** `DEVS/plan.md` líneas 80-103

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_catalog` existe | `supabase/migrations/004_agent_catalog.sql:6` | ✅ | CREATE TABLE línea 6 |
| 2 | Columna `allowed_tools TEXT[]` | `004_agent_catalog.sql:12` | ✅ | `allowed_tools TEXT[] DEFAULT '{}'` |
| 3 | Columna `soul_json JSONB` | `004_agent_catalog.sql:11` | ✅ | `soul_json JSONB NOT NULL DEFAULT '{}'` |
| 4 | RLS `tenant_isolation` en agent_catalog | `004_agent_catalog.sql:22-23` | ✅ | POLICY `agent_catalog_tenant_isolation` |
| 5 | Índice `idx_agent_catalog_org_role` | `004_agent_catalog.sql:26-27` | ✅ | Partial index WHERE is_active = TRUE |
| 6 | `AgentFactory.resolve_tools()` existe | `src/crews/factory.py:28` | ✅ | Firma: `resolve_tools(allowed_tools, org_id, *, async_mode=False)` |
| 7 | `AgentFactory.resolve_tools_async()` existe | `src/crews/factory.py:192` | ✅ | Firma: `async resolve_tools_async(allowed_tools, org_id)` |
| 8 | `AgentFactory.create_agent_async()` existe | `src/crews/factory.py:261` | ✅ | Usa `await resolve_tools_async()` |
| 9 | `ExcelReaderTool` registrada | `src/tools/excel_reader.py:28-33` | ✅ | `@register_tool("excel_reader", ...)` |
| 10 | `ExcelReaderTool` hereda `OrgBaseTool` | `src/tools/excel_reader.py:33` | ✅ | `class ExcelReaderTool(OrgBaseTool)` |
| 11 | `ExcelReaderTool._run()` firma | `src/tools/excel_reader.py:42` | ✅ | `_run(self, filename: str, sheet_name: Optional[str] = None) -> str` |
| 12 | `ExcelReaderInput` schema | `src/tools/excel_reader.py:23-25` | ✅ | Pydantic BaseModel con `filename`, `sheet_name` |
| 13 | `BASE_DIR` apunta a `PROJECT-Aybar` | `src/tools/excel_reader.py:20` | ✅ | `Path(__file__).resolve().parent.parent.parent / "PROJECT-Aybar"` |
| 14 | `precios_bebidas.xlsx` existe | Filesystem verificado | ✅ | `PROJECT-Aybar/precios_bebidas.xlsx` |
| 15 | `BaseCrew.run_async()` existe | `src/crews/base_crew.py:169` | ✅ | Firma: `async run_async(task_description, inputs, expected_output)` |
| 16 | `BaseCrew.run_async()` usa `create_agent_async` | `src/crews/base_crew.py:185` | ✅ | `agent = await AgentFactory.create_agent_async(config, self.org_id)` |
| 17 | `tool_registry.get()` existe | `src/tools/registry.py:75` | ✅ | Firma: `get(name, org_id=None) -> Type` |
| 18 | `OrgBaseTool` existe | `src/tools/base_tool.py:18` | ✅ | Hereda `crewai.tools.BaseTool`, atributo `org_id: str` |
| 19 | `test_real_tool_calling.py` existe | `tests/e2e/test_real_tool_calling.py` | ✅ | Test E2E con LLM real + excel_reader |
| 20 | `test_factory.py` unit tests existen | `tests/unit/test_factory.py` | ✅ | 296 líneas, cubre resolve_tools sync/async |
| 21 | `crewai` dependencia opcional | `proyecto-config.json:132-133` | ✅ | `crewai>=0.100.0`, `crewai-tools>=0.20.0` |
| 22 | `Groq/llama-3.3-70b` soporta function calling | `src/config.py:37-38` + plan.md:97 | ✅ | `groq_model: "groq/llama-3.3-70b-versatile"` |

**Discrepancias encontradas:**

1. **DISCREPANCIA: `test_real_tool_calling.py` depende de DB mock, no de agente registrado real.** El test en línea 95 crea `BaseCrew(org_id=org_id, role="presupuestador")` pero mockea `get_service_client` para retornar `agent_config` inline. No usa un agente persistido en `agent_catalog`. → **Resolución:** El test valida tool calling con LLM real pero la configuración del agente es inline, no DB. Para Paso 3 completo, se necesita test con agente registrado via bundle import (Paso 2).

2. **DISCREPANCIA: `test_real_tool_calling.py` no verifica que el LLM *decidió* llamar la herramienta.** El assert en línea 112 busca `"12000"` o `"gordon"` en el output, pero no confirma que fue via tool calling activo vs datos del prompt. → **Resolución:** Agregar verificación de tool calls en el resultado de CrewAI (token usage con tool_call metadata).

3. **DISCREPANCIA: `resolve_tools(async_mode=True)` deprecated pero sin remover.** `factory.py:60-63` marca como deprecated pero el código sigue existiendo. → **Resolución:** Documentar como deuda técnica. No bloquea Paso 3.

4. **DISCREPANCIA: `_load_from_db()` en registry.py usa `safe_builtins` directo, no `_create_safe_builtins()`.** `src/tools/registry.py:158` → `from RestrictedPython import safe_builtins`. Esto es el vector de seguridad pendiente del Paso 0 plan v3.2. → **Resolución:** No bloquea Paso 3 pero es riesgo de seguridad documentado.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas tocadas

| Tabla | Uso en Paso 3 | Columnas relevantes |
|---|---|---|
| `agent_catalog` | Lookup de agente con `allowed_tools` | `role`, `is_active`, `soul_json`, `allowed_tools TEXT[]`, `max_iter` |
| `organizations` | FK de `agent_catalog.org_id` | `id` (referencia) |

### Schema existente — verificado

`agent_catalog` (004):
- `id UUID PK` — gen_random_uuid
- `org_id UUID NOT NULL` → FK organizations(id) ON DELETE CASCADE
- `role TEXT NOT NULL` — identificador único por org
- `is_active BOOLEAN DEFAULT TRUE`
- `soul_json JSONB NOT NULL DEFAULT '{}'` — personality: role, goal, backstory
- `allowed_tools TEXT[] DEFAULT '{}'` — lista de tool names del registry
- `max_iter INTEGER DEFAULT 5` — Rule R8
- `UNIQUE(org_id, role)` — constraint de unicidad

### RLS policies

- `agent_catalog_tenant_isolation` — `FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE))`
- Índice partial: `idx_agent_catalog_org_role ON (org_id, role) WHERE is_active = TRUE`

### Integridad referencial

- `agent_catalog.org_id` → `organizations.id` CASCADE DELETE
- No hay FK hacia tools — `allowed_tools` es array de strings, resuelto en runtime via `tool_registry`

### Impacto en datos existentes

- **Sin migraciones nuevas.** Paso 3 no modifica schema. Usa `allowed_tools` y `soul_json` existentes.
- **Requisito:** Debe existir al menos 1 registro en `agent_catalog` con `allowed_tools: ['excel_reader']` y `soul_json` que instruya al agente usar la herramienta.

### Diagrama ER (simplificado)

```
organizations (1) ──< agent_catalog (N)
                              │
                              └─ allowed_tools[] → tool_registry (runtime resolution)
                                                      │
                                                      └─ ExcelReaderTool
```

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/clases involucradas

#### `AgentFactory.resolve_tools()` — `src/crews/factory.py:28-82`
```python
@staticmethod
def resolve_tools(
    allowed_tools: list[str], org_id: str, *, async_mode: bool = False
) -> list:
```
- Itera `allowed_tools`, separa MCP vs regular
- MCP: skip en sync mode, resolve en async mode
- Regular: `tool_registry.get(tool_name, org_id=org_id)` → instantiate `tool_cls(org_id=org_id)`
- Retorna lista de tool instances

#### `AgentFactory.resolve_tools_async()` — `src/crews/factory.py:192-232`
```python
@staticmethod
async def resolve_tools_async(allowed_tools: list[str], org_id: str) -> list:
```
- Misma lógica pero usa `await _resolve_mcp_tool_async()` para MCP
- Regular tools: sync resolution (no necesita await)

#### `AgentFactory.create_agent_async()` — `src/crews/factory.py:261-282`
```python
@staticmethod
async def create_agent_async(config: Dict[str, Any], org_id: str) -> Agent:
```
- Extrae `soul_json`, `allowed_tools`, `max_iter` del config
- Llama `await resolve_tools_async(allowed_tools, org_id)`
- Crea `crewai.Agent(role, goal, backstory, llm, max_iter, tools=tools)`

#### `BaseCrew.run_async()` — `src/crews/base_crew.py:169-205`
```python
async def run_async(
    self,
    task_description: str,
    inputs: Optional[Dict[str, Any]] = None,
    expected_output: str = "Structured result of the analysis.",
) -> Any:
```
- `_load_agent_config()` → fetch from `agent_catalog` via Supabase
- `await AgentFactory.create_agent_async(config, self.org_id)` → agent con tools resueltas
- Crea `crewai.Crew(agents=[agent], tasks=[task], process=Process.sequential)`
- `await crew.kickoff_async(inputs=inputs or {})`

#### `ExcelReaderTool` — `src/tools/excel_reader.py:33-97`
```python
@register_tool("excel_reader", description="...", tags=["business", "excel", "aybar"])
class ExcelReaderTool(OrgBaseTool):
    name: str = "excel_reader"
    description: str = "Lee archivos .xlsx de la carpeta PROJECT-Aybar..."
    args_schema: Type[BaseModel] = ExcelReaderInput

    def _run(self, filename: str, sheet_name: Optional[str] = None) -> str:
```
- Input: `ExcelReaderInput(filename: str, sheet_name: Optional[str])`
- Output: JSON string con datos de la sheet
- Patrón a seguir: `src/tools/excel_reader.py` como referencia para cualquier tool nueva

### Patrones identificados

1. **Tool registration:** `@register_tool("name", description, tags)` → decorator que registra en `tool_registry` singleton
2. **Tool base class:** `OrgBaseTool` hereda `crewai.tools.BaseTool`, agrega `org_id: str` y `_get_secret()`
3. **Agent creation:** `AgentFactory.create_agent_async(config, org_id)` → extrae config, resuelve tools, crea CrewAI Agent
4. **Crew execution:** `BaseCrew.run_async(task_description, inputs, expected_output)` → load agent from DB, create crew, kickoff_async
5. **Import pattern:** `from src.tools.registry import tool_registry, register_tool` (absolute imports)

### Modularidad

- `AgentFactory` — responsabilidad única: crear agents + resolver tools
- `BaseCrew` — responsabilidad única: load agent from DB + ejecutar crew
- `ExcelReaderTool` — responsabilidad única: leer xlsx → JSON
- **Cohesión alta, acoplamiento bajo.** Cada componente tiene interfaz clara.

### Imports exactos requeridos para implementación

```python
from src.crews.factory import AgentFactory
from src.crews.base_crew import BaseCrew
from src.tools.excel_reader import ExcelReaderTool, ExcelReaderInput
from src.tools.registry import tool_registry, register_tool
from src.tools.base_tool import OrgBaseTool
from src.config import get_settings
from crewai import Agent, Task, Crew, Process
from pydantic import BaseModel, Field
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints involucrados

Paso 3 **no crea endpoints nuevos**. Usa infraestructura existente:

| Componente | Ruta/Función | Método | Input | Output |
|---|---|---|---|---|
| Agent lookup | `BaseCrew._load_agent_config()` | Supabase query | `org_id`, `role` | `agent_catalog` record |
| Tool resolution | `AgentFactory.resolve_tools_async()` | In-memory | `allowed_tools[]`, `org_id` | `[tool_instances]` |
| Crew execution | `BaseCrew.run_async()` | Async | `task_description`, `inputs`, `expected_output` | `CrewOutput` |

### Flujo de datos

```
1. BaseCrew(org_id, role) → _load_agent_config()
   └─ Supabase: SELECT * FROM agent_catalog WHERE org_id=? AND role=? AND is_active=true
      └─ Retorna: {soul_json, allowed_tools, max_iter, ...}

2. AgentFactory.create_agent_async(config, org_id)
   ├─ get_settings().get_llm() → LLM(groq/llama-3.3-70b-versatile)
   ├─ resolve_tools_async(allowed_tools, org_id)
   │  ├─ "excel_reader" → tool_registry.get("excel_reader", org_id)
   │  │  └─ ExcelReaderTool(org_id=org_id)
   │  └─ "mcp:server:tool" → _resolve_mcp_tool_async(org_id, server, tool)
   │     └─ MCPPool.get().get_tools(org_id, server) → await
   └─ CrewAI Agent(role, goal, backstory, llm, tools=[ExcelReaderTool(...)])

3. Crew(agents=[agent], tasks=[task], process=sequential)
   └─ crew.kickoff_async(inputs={})
      └─ LLM recibe task_description
         └─ LLM decide llamar excel_reader(filename="precios_bebidas.xlsx")
            └─ ExcelReaderTool._run(filename, sheet_name) → JSON string
               └─ LLM procesa resultado → genera respuesta final
```

### Middleware aplicable

- **Auth:** `src/api/middleware.py` — JWT verification + org membership. No aplica directamente a `BaseCrew.run_async()` (se usa internamente, no via API).
- **RLS:** Supabase RLS en `agent_catalog` — `org_id::text = current_setting('app.org_id', TRUE)`. `BaseCrew._load_agent_config()` usa `get_service_client()` que debe tener el contexto de org establecido.

### Contratos entre servicios

| Contrato | Detalle |
|---|---|
| `agent_catalog` → `BaseCrew` | Record debe tener `soul_json` con `role`, `goal`, `backstory`; `allowed_tools` como array de strings |
| `allowed_tools` → `tool_registry` | Cada string debe corresponder a un tool registrado via `@register_tool` |
| `ExcelReaderTool._run()` → LLM | Retorna JSON string. LLM parsea y usa para cálculo |
| `crew.kickoff_async()` → caller | Retorna `CrewOutput` con `raw` (string) y `token_usage` |

### Error handling

| Escenario | Comportamiento actual |
|---|---|
| Tool no encontrado en registry | `logger.warning` + skip (no falla) |
| MCP tool resolution falla | `logger.error` + skip (no falla) |
| Archivo xlsx no existe | `{"error": "Archivo 'X' no encontrado en BASE_DIR"}` |
| Agent no encontrado en DB | `CrewConfigError` raised |
| LLM no llama la herramienta | Agente responde sin datos reales → test falla en assertions |

### Cuellos de botella

1. **DB lookup por agente:** Cada `BaseCrew.run_async()` hace query a `agent_catalog`. Sin caching interno (solo cachea en `self._agent_config` por instancia). → **Mitigación:** Cache a nivel módulo o TTL-based.
2. **MCPPool.get_tools() async:** Si hay muchos MCP servers, puede ser lento. Paso 3 solo usa `excel_reader` (no MCP), sin impacto.
3. **LLM latency:** Groq llama-3.3-70b ~2-5s por respuesta. Tool calling agrega 1-2 round trips extra.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo: DB → Backend → Frontend → UX

```
[DB agent_catalog] → [BaseCrew.load_agent_config] → [AgentFactory.create_agent_async]
  → [resolve_tools_async: excel_reader] → [CrewAI Agent con tools]
  → [crew.kickoff_async] → [LLM decide llamar excel_reader]
  → [ExcelReaderTool._run → lee xlsx → JSON] → [LLM procesa → respuesta]
  → [CrewOutput.raw] → [caller parsea JSON]
```

### Coherencia con arquitectura existente

- **Sí encaja.** `AgentFactory` ya resuelve tools, `BaseCrew` ya ejecuta crews async, `ExcelReaderTool` ya está registrada.
- **Gap principal:** El `soul_json` del agente debe instruir explícitamente al LLM usar la herramienta. Sin instrucciones claras en `backstory`/`goal`, el LLM puede ignorar `excel_reader` y usar datos de entrenamiento.

### Gaps y ambigüedades

1. **Gap: `soul_json` no garantiza tool calling.** El plan.md:97 reconoce "el formato de tool description debe ser claro para que el LLM decida usarlo". Pero no especifica qué formato mínimo funciona. → **Resolución:** Definir plantilla de `soul_json` con instrucciones explícitas de tool usage.

2. **Gap: No hay verificación de que el LLM *efectivamente* llamó la herramienta.** CrewAI no expone tool call history en `CrewOutput` de forma estándar. → **Resolución:** Usar callback o inspectar el `token_usage` para detectar tool calls.

3. **Ambigüedad: ¿El agente debe poder llamar la herramienta múltiples veces?** `ExcelReaderTool` puede leer diferentes sheets. El plan no especifica si el agente debe hacer 1 o N llamadas. → **Resolución:** Asumir N llamadas permitidas (CrewAI lo soporta nativamente).

### DX & Tooling — OBLIGATORIO

#### Herramienta Propuesta: `fap test-tool-calling`

- **Qué automatiza:** Ejecución de test de tool calling con agente registrado, verificando que el LLM efectivamente llamó la herramienta (no solo que el output contiene datos). Elimina necesidad de configurar manualmente agente + mock DB + verificar tool calls.
- **Tipo:** CLI command
- **Cómo se usa:**
  ```
  fap test-tool-calling --role presupuestador --tool excel_reader --file precios_bebidas.xlsx --task "Calculá costo de 100 cocteles"
  ```
  Flags:
  - `--role`: role del agente en agent_catalog
  - `--tool`: tool a verificar que sea llamada
  - `--file`: archivo xlsx de prueba
  - `--task`: descripción de tarea para el agente
  - `--dry-run`: solo verifica config sin ejecutar LLM
  - `--json`: output machine-readable
- **Impacto para el usuario final:** Reduce de ~15 minutos (configurar test manual) a ~30 segundos. Permite verificar tool calling sin depender de tests E2E completos.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Registro en agent_catalog existe con allowed_tools=["excel_reader"] y soul_json que instruye tool usage
✅ [DATA] Tabla agent_catalog tiene columna allowed_tools TEXT[] verificada en migración 004
✅ [CODE] AgentFactory.resolve_tools_async() resuelve "excel_reader" a ExcelReaderTool instance
✅ [CODE] BaseCrew.run_async() crea agente con tools resueltas y ejecuta crew.kickoff_async()
✅ [CODE] ExcelReaderTool._run() retorna JSON válido con datos de la sheet
✅ [BACKEND] LLM (groq/llama-3.3-70b) decide llamar excel_reader sin datos precargados en prompt
✅ [BACKEND] Output del agente contiene datos reales del xlsx (no inventados)
✅ [FULLSTACK] Flujo completo: DB lookup → tool resolution → LLM tool call → ExcelReader → JSON output
✅ [FULLSTACK] Test E2E verifica que "Mocked Crew Result" no está en output
✅ [DX] Herramienta fap test-tool-calling ejecuta sin errores y reduce paso manual de configuración de tests
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| LLM no llama la herramienta | Alta | `soul_json` no tiene instrucciones suficientemente explícitas; LLM usa datos de entrenamiento | Agregar instrucciones explícitas en `backstory`: "SIEMPRE usás la herramienta X antes de responder". Verificar con test que detecta tool calls. |
| `allowed_tools` vacío o mal configurado | Alta | Agente registrado sin `allowed_tools` o con nombre incorrecto | Validar `allowed_tools` en el bundle import (Paso 2). Test que verifica tool resolution antes de ejecutar. |
| ExcelReaderTool falla con archivos grandes | Media | `openpyxl.load_workbook()` en modo read_only puede ser lento con sheets >10K rows | Ya usa `read_only=True` + `data_only=True`. Agregar timeout o límite de rows si es necesario. |
| MCP tool resolution deadlock (residuo Paso 1) | Media | Si Paso 1 no está completo, `resolve_tools(async_mode=True)` puede deadlockear | Paso 1 debe estar completado antes. Usar solo `resolve_tools_async()` en paths async. |
| CrewAI version incompatibility | Media | `crewai>=0.100.0` puede cambiar API de tool calling | Pin version en `pyproject.toml`. Test de importabilidad antes de ejecutar. |
| Groq API rate limiting | Baja | LLM real hace múltiples llamadas (tool call + response) | Implementar retry con tenacity (ya es dependencia directa). |
| Seguridad: `_load_from_db()` usa `safe_builtins` sin restricción | Media | `registry.py:158` usa `safe_builtins` directo, no `_create_safe_builtins()` | No bloquea Paso 3 pero debe fixearse en Paso 0 plan v3.2. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap test-tool-calling` | `src/cli/commands/test_tool_calling.py` | `def test_tool_calling(role: str, tool: str, file: str, task: str, dry_run: bool = False, json_output: bool = False) -> int` | `src/cli/commands/check_env.py :: check_env()` | DX | Media | 1.5h | Ninguna | → verificar: `uv run fap test-tool-calling --help` ejecuta sin errores |
| 1 | Verificar agente `presupuestador` con `allowed_tools=["excel_reader"]` en agent_catalog | — (verificación DB) | Query: `SELECT * FROM agent_catalog WHERE role='presupuestador' AND allowed_tools @> ARRAY['excel_reader']` | `supabase/migrations/004_agent_catalog.sql` schema | DATA | Baja | 0.25h | Tarea 0 | → verificar: query retorna ≥ 1 registro con `is_active=true` |
| 2 | Mejorar `soul_json` del agente presupuestador para forzar tool calling | `agents/presupuestador.json` o registro DB | `soul_json.backstory` debe incluir: "SIEMPRE usás la herramienta excel_reader para obtener datos reales. NUNCA inventes precios." | `tests/e2e/test_real_tool_calling.py:48-64` AGENT_CONFIG | DATA | Baja | 0.25h | Tarea 1 | → verificar: `soul_json.backstory` contiene "SIEMPRE" y "excel_reader" |
| 3 | Agregar verificación de tool calls en `BaseCrew.run_async()` | `src/crews/base_crew.py` | Agregar atributo `self._last_tool_calls: list[dict]` poblado durante ejecución. Método `get_last_tool_calls() -> list[dict]` | `src/crews/base_crew.py:165-167` patrón `get_last_tokens_used()` | CODE | Media | 1h | Tarea 2 | → verificar: `BaseCrew` instancia tiene método `get_last_tool_calls()` retornable |
| 4 | Crear test E2E que verifica tool calling activo (no datos precargados) | `tests/e2e/test_real_tool_calling.py` (modificar) | Test existente modificado: agregar assert que verifique `crew.get_last_tool_calls()` contiene al menos 1 call a `excel_reader` | `tests/e2e/test_real_tool_calling.py:68-121` estructura actual | CODE | Media | 1h | Tarea 3 | → verificar: `uv run pytest tests/e2e/test_real_tool_calling.py -v --timeout=120` pasa con GROQ_API_KEY |
| 5 | Crear test unitario para `resolve_tools_async` con `excel_reader` | `tests/unit/test_factory.py` (agregar) | Test: `test_resolve_tools_async_excel_reader` → mock `tool_registry.get` retorna `ExcelReaderTool`, verificar que `resolve_tools_async(["excel_reader"], org_id)` retorna `[ExcelReaderTool(org_id=org_id)]` | `tests/unit/test_factory.py:160-173` patrón `test_resolves_regular_tools_async` | CODE | Baja | 0.5h | Tarea 0 | → verificar: `uv run pytest tests/unit/test_factory.py -v --timeout=60` pasa |
| 6 | Documentar formato mínimo de `soul_json` para tool calling | `DEVS/IN_PROGRESS/analisis-paso-3-qwen.md` (este archivo) | Sección con template: `{role, goal, backstory con instrucciones explícitas, allowed_tools}` | `tests/e2e/test_real_tool_calling.py:48-64` AGENT_CONFIG | FULLSTACK | Baja | 0.25h | Tarea 2 | → verificar: template incluido en este documento §4 |
| 7 | Validar flujo end-to-end con LLM real + tool calling verificado | — (test E2E) | Ejecutar `test_real_tool_calling.py` con GROQ_API_KEY, verificar: (a) tool call detectado, (b) output contiene datos reales, (c) JSON parseable | `tests/e2e/test_real_tool_calling.py` + Tarea 4 | FULLSTACK | Alta | 1h | Tareas 1-5 | → verificar: criterios §5 pasan todos |

**Tiempo total estimado:** 5.75 horas

---

## 🔮 Roadmap (NO implementar ahora)

1. **Tool call telemetry:** Registrar qué tools fueron llamadas, cuántas veces, duración. Útil para debugging y optimización de `soul_json`.
2. **Tool calling fallback:** Si el LLM no llama la herramienta esperada después de N iteraciones, inyectar hint explícito en el conversation history.
3. **Multi-tool orchestration:** Agente con `allowed_tools: ["excel_reader", "excel_writer"]` que lee datos y escribe resultado. Requiere coordinación de tool calls secuenciales.
4. **Tool description optimization:** A/B testing de descripciones de tools para maximizar probabilidad de que el LLM las use. Métrica: % de ejecuciones con tool call activo.
5. **Caching de tool results:** Si el mismo archivo xlsx se lee múltiples veces en corta ventana, cachear resultado para reducir I/O.

---

## 📋 Template de `soul_json` para Tool Calling

```json
{
  "role": "Cotizador de Eventos",
  "goal": "Usar la herramienta excel_reader para obtener precios reales y generar presupuestos precisos",
  "backstory": "Sos un experto en cotización de eventos. SIEMPRE usás la herramienta excel_reader para obtener datos actualizados de precios y consumos antes de calcular. NUNCA inventás precios ni usás datos de entrenamiento. Si no podés acceder a los datos, informá el error en lugar de inventar valores.",
  "allowed_tools": ["excel_reader"],
  "max_iter": 5
}
```

**Reglas para tool calling efectivo:**
1. `backstory` debe contener "SIEMPRE" + nombre exacto de la herramienta
2. `backstory` debe contener "NUNCA" + acción prohibida (inventar datos)
3. `goal` debe mencionar explícitamente la herramienta
4. `allowed_tools` debe ser array con nombres exactos del registry
5. `max_iter` ≥ 3 para permitir tool call + procesamiento de resultado
