# 🧠 Análisis Técnico — Paso 3: Tool Calling Real (Agente usa herramienta durante ejecución)

> **Agente:** glm | **Paso:** 3 | **Fecha:** 2026-05-03

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `ExcelReaderTool` existe y está registrado | `@register_tool("excel_reader")` en `src/tools/excel_reader.py:28` | ✅ | Registro con decorador, hereda `OrgBaseTool`, args_schema `ExcelReaderInput` |
| 2 | `tool_registry.get("excel_reader", org_id=...)` resuelve la clase | `ToolRegistry.get()` en `src/tools/registry.py:75-120`, lookup en `_tools` dict → `_load_from_db` → `_load_from_filesystem` | ✅ | 3 niveles de resolución. ExcelReaderTool se registra en import |
| 3 | `AgentFactory.resolve_tools(["excel_reader"], org_id)` funciona | `src/crews/factory.py:73-81` — rama `else` (no-mcp) llama `tool_registry.get()` → instancía con `org_id` | ✅ | Verificado en `test_factory.py:25-35` (TestResolveTools) |
| 4 | `AgentFactory.create_agent_async()` existe y es async | `src/crews/factory.py:261-282` — `async def create_agent_async(config, org_id) -> Agent` | ✅ | Llama `await resolve_tools_async()` |
| 5 | `BaseCrew.run_async()` usa `create_agent_async` | `src/crews/base_crew.py:169-205` — `await AgentFactory.create_agent_async(config, self.org_id)` | ✅ | Línea 185 |
| 6 | `BaseCrew` carga config desde `agent_catalog` | `src/crews/base_crew.py:43-75` — `_load_agent_config()` consulta DB por `org_id` + `role` + `is_active` | ✅ | Query: `svc.table("agent_catalog").select("*").eq("org_id",...).eq("role",...).eq("is_active", True).maybe_single()` |
| 7 | Tabla `agent_catalog` existe con columnas correctas | Migración `004_agent_catalog.sql` — columnas: `id, org_id, role, is_active, soul_json, allowed_tools, max_iter, created_at, updated_at` | ✅ | RLS policy `agent_catalog_tenant_isolation`, índice `idx_agent_catalog_org_role` |
| 8 | `PresupuestoFlow` existe y está registrado como `"presupuesto"` | `src/flows/presupuesto_flow.py:23` — `@register_flow("presupuesto", category="business")` | ✅ | Importa `excel_reader` al inicio (línea 16) para asegurar registro |
| 9 | `PresupuestoFlow._run_crew()` usa `BaseCrew(role="presupuestador")` | `src/flows/presupuesto_flow.py:44` — `crew = BaseCrew(self.org_id, role="presupuestador")` | ✅ | Prompt instruye al LLM usar `excel_reader` |
| 10 | `config.py` → `get_llm()` soporta Groq | `src/config.py:41-56` — `get_llm()` retorna `LLM(model=self.groq_model, api_key=self.groq_api_key)` cuando `llm_provider == "groq"` | ✅ | Default `groq/llama-3.3-70b-versatile` |
| 11 | `PROJECT-Aybar/precios_bebidas.xlsx` existe | Archivo encontrado en `PROJECT-Aybar/precios_bebidas.xlsx` | ✅ | 11 archivos .xlsx en total |
| 12 | `PROJECT-Aybar/config_consumo_pax.xlsx` existe | Archivo encontrado en `PROJECT-Aybar/config_consumo_pax.xlsx` | ✅ | Referenciado en prompt de PresupuestoFlow |
| 13 | `ExcelReaderTool._run()` recibe `filename` y `sheet_name` | `src/tools/excel_reader.py:42` — `_run(self, filename: str, sheet_name: Optional[str] = None) -> str` | ✅ | `args_schema: ExcelReaderInput` con `Field(description=...)` |
| 14 | Test E2E `test_real_tool_calling.py` existe | `tests/e2e/test_real_tool_calling.py` — 121 líneas | ✅ | Usa `BaseCrew.run_async()` con mock DB, patches CrewAI |
| 15 | `test_factory.py` cubre `resolve_tools()`, `resolve_tools_async()`, `_resolve_mcp_tool_async()` | `tests/unit/test_factory.py` — 296 líneas, 4 clases de test | ✅ | Cubre sync, async, MCP, errores |
| 16 | `org_id` en `agent_catalog` columna `allowed_tools` tipo `text[]` | Migración `004_agent_catalog.sql:12` — `allowed_tools TEXT[] DEFAULT '{}'` | ✅ | Array de strings |
| 17 | `ExcelReaderTool.BASE_DIR` apunta a `PROJECT-Aybar` | `src/tools/excel_reader.py:20` — `BASE_DIR = Path(__file__).resolve().parent.parent.parent / "PROJECT-Aybar"` | ✅ | Path relativo desde `src/tools/` |
| 18 | `crewai.Agent` acepta `tools` como list | CrewAI API: `Agent(tools=[...])` — estándar CrewAI | ✅ | Verificado en `factory.py:249-258` |
| 19 | `OrgBaseTool` hereda de `crewai.tools.BaseTool` | `src/tools/base_tool.py:18` — `class OrgBaseTool(BaseTool)` | ✅ | CrewAI compatible |
| 20 | Columna `name` no existe en `agent_catalog` | Migración `004_agent_catalog.sql` — columnas: `id, org_id, role, is_active, soul_json, allowed_tools, max_iter` | ❌ | Plan paso 2 menciona `agents/presupuestador.json` con campo `name` que NO coincide con schema DB. DB usa `role` como identificador. |
| 21 | `PresupuestoFlow` hardcodea `role="presupuestador"` | `src/flows/presupuesto_flow.py:44` | ✅ | Debe existir registro en `agent_catalog` con ese role |
| 22 | `step_test_tool_calling.py` NO existe en `scripts/` | Glob no encontrado | ⚠️ | No hay script DX para verificar tool calling |
| 23 | `openpyxl` está en dependencias | No aparece en `pyproject.toml` deps directas | ❌ | `ExcelReaderTool` importa `openpyxl` (línea 14) pero NO está en dependencias directas de `pyproject.toml`. Probablemente dependencia transitiva de `crewai-tools`. |
| 24 | test_real_tool_calling usa `is_active` en config mock | `tests/e2e/test_real_tool_calling.py:63` — `"is_active": True` en AGENT_CONFIG | ✅ | Pero mock de DB retorna config directamente, no consulta .eq("is_active", True) |

**Discrepancias encontradas:**

1. **❌ `openpyxl` no está en dependencias directas** — `ExcelReaderTool` lo importa pero no está en `[project.dependencies]` de `pyproject.toml`. Si `crewai-tools` no está instalado (es opcional), `openpyxl` no existirá. Resolución: Agregar `openpyxl>=3.1.0` a dependencias directas.

2. **❌ Plan Paso 2 refiere `name` en `agents/presupuestador.json`** pero DB `agent_catalog` usa `role` como campo identificador, no `name`. La columna `name` no existe en migración 004. Resolución: El JSON del bundle debe usar `role` (no `name`) para el campo identificador del agente.

3. **⚠️ Test `test_real_tool_calling.py` patchea `crewai.Crew` y `crewai.Task`** (líneas 76-77) — Esto mockea el motor CrewAI. Para tool calling REAL, el LLM necesita interactuar con la tool. Los patches eliminan CrewAI real. Resolución: Crear nuevo test E2E que NO patchee CrewAI para verificar que el LLM llama `excel_reader`.

---

## 1️⃣ Análisis de Datos

### Schema actual — `agent_catalog` (migración 004)

```sql
CREATE TABLE agent_catalog (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role          TEXT NOT NULL,          -- identificador del agente
    is_active     BOOLEAN DEFAULT TRUE,
    soul_json     JSONB NOT NULL DEFAULT '{}', -- personality: role, goal, backstory
    allowed_tools TEXT[] DEFAULT '{}',    -- ["excel_reader", ...]
    max_iter      INTEGER DEFAULT 5,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, role)
);
```

### Cambios de schema necesarios

- **No se requieren migraciones nuevas.** `agent_catalog` ya tiene `allowed_tools TEXT[]` y `soul_json JSONB`. El paso 3 usa la infraestructura existente.

### Integridad referencial

- `agent_catalog.org_id` → `organizations.id` (FK con CASCADE)
- `org_mcp_servers.org_id` (para MCP tools, no aplica a este paso)
- RLS: `agent_catalog_tenant_isolation` usando `app.org_id()`

### Datos necesarios en `agent_catalog`

Registro con:
- `role = 'presupuestador'`
- `soul_json` con `role`, `goal`, `backstory` que instruyan explícitamente el uso de `excel_reader`
- `allowed_tools = '{excel_reader}'`
- `is_active = true`
- `max_iter = 5`

### Índices

- `idx_agent_catalog_org_role` ya existe — cubre lookup `(org_id, role) WHERE is_active = TRUE`

---

## 2️⃣ Análisis de Código

### Funciones/clases nuevas o modificadas

Ninguna función NUEVA se requiere. El paso 3 es de **integración y verificación** — todo el plumbing ya existe:

| Componente | Archivo | Firma | Rol en paso 3 |
|---|---|---|---|
| `ExcelReaderTool` | `src/tools/excel_reader.py:33` | `class ExcelReaderTool(OrgBaseTool)` con `_run(filename, sheet_name) -> str` | Tool que el LLM debe llamar activamente |
| `AgentFactory.create_agent_async()` | `src/crews/factory.py:261` | `async def create_agent_async(config: Dict[str,Any], org_id: str) -> Agent` | Resuelve tools y crea Agent CrewAI |
| `AgentFactory.resolve_tools_async()` | `src/crews/factory.py:192` | `async def resolve_tools_async(allowed_tools: list[str], org_id: str) -> list` | Resuelve `["excel_reader"]` → `[ExcelReaderTool(org_id=xxx)]` |
| `BaseCrew.run_async()` | `src/crews/base_crew.py:169` | `async def run_async(task_description, inputs, expected_output) -> Any` | Ejecuta crew asyncamente |
| `PresupuestoFlow._run_crew()` | `src/flows/presupuesto_flow.py:43` | `async def _run_crew() -> Dict[str,Any]` | Orquesta el flujo de presupuesto |

### Patrones: se siguen los existentes

- `@register_tool` para registro de tools → patrón establecido ✓
- `@register_flow` para registro de flows → patrón establecido ✓
- `BaseCrew(role=X)` → lookup en `agent_catalog` → `AgentFactory.create_agent_async()` → `resolve_tools_async()` → cadena completa ✓
- `OrgBaseTool` con `org_id` + `args_schema` → patrón establecido ✓

### Modularidad

- **Alta cohesión:** cada componente tiene responsabilidad única
- **Bajo acoplamiento:** `BaseCrew` no conoce la tool específica, `AgentFactory` resuelve por nombre
- **Reutilización:** `ExcelReaderTool` está registrado globalmente, cualquier agente puede usarlo si `allowed_tools` lo incluye

### Imports exactos

```python
# factory.py (línea 9)
from src.tools.registry import tool_registry

# excel_reader.py (líneas 17-18)
from src.tools.base_tool import OrgBaseTool
from src.tools.registry import register_tool

# presupuesto_flow.py (líneas 13-17)
from src.crews.base_crew import BaseCrew
from src.flows.base_flow import BaseFlow
import src.tools.excel_reader  # fuerza registro
from src.flows.registry import register_flow
```

### Problemas de calidad identificados

1. **`ExcelReaderTool._run()` retorna JSON string** — CrewAI tools deberían retornar strings. ✔ Correcto.
2. **`BASE_DIR` hardcodeado** (`src/tools/excel_reader.py:20`) — Path relativo frágil si se mueve el archivo. ⚠️ Aceptable para MVP.
3. **Test E2E existente (`test_real_tool_calling.py`) mockea CrewAI** — No prueba tool calling real. Necesita test nuevo sin patches de Crew/Task.

---

## 3️⃣ Análisis de Backend

### Endpoints existentes (no se modifican)

| Endpoint | Método | Descripción |
|---|---|---|
| `POST /api/webhooks/trigger` | POST 202 | Dispara flow via webhook |
| `POST /api/flows/{flow_type}/run` | POST 202 | Ejecuta flow por nombre |
| `GET /api/flows/available` | GET 200 | Lista flows disponibles |

### Flujo de datos para tool calling real

```
POST /api/webhooks/trigger
  {flow_type: "presupuesto", input_data: {tipo_evento, pax, fecha, provincia}}
    ↓
  WebhookTriggerRequest → validate_input() → create_task_record()
    ↓
  Background task: execute_flow_instance()
    ↓
  PresupuestoFlow.execute(input_data)
    ↓
  BaseCrew(org_id, role="presupuestador").run_async(task_description, inputs)
    ↓
  _load_agent_config() → SELECT * FROM agent_catalog WHERE role='presupuestador'
    ↓
  AgentFactory.create_agent_async(config, org_id)
    ↓
  resolve_tools_async(["excel_reader"], org_id)
    ↓
  tool_registry.get("excel_reader", org_id=...) → ExcelReaderTool(org_id=...)
    ↓
  Agent(tools=[excel_reader_instance], ...)
    ↓
  crew.kickoff_async(inputs=...)
    ↓
  [LLM decide llamar excel_reader] → ExcelReaderTool._run(filename, sheet_name)
    ↓
  Resultado inyectado en contexto del LLM
    ↓
  LLM genera presupuesto con datos reales
```

### Middleware aplicable

- `require_org_id` — extrae org_id del JWT para RLS
- Auth: JWT middleware verifica membresía en org

### Contrato del endpoint de trigger

```
POST /api/webhooks/trigger
Headers: Authorization: Bearer <JWT>
Body: {flow_type: "presupuesto", input_data: {tipo_evento: "boda", pax: 100, fecha: "2026-03-15", provincia: "Tucumán"}}
Response 202: {task_id: UUID, correlation_id: str, status: "accepted"}
```

### Error handling

| Caso | Código | Mensaje |
|---|---|---|
| Flow no existe | 400 | `Flow 'presupuesto' not found. Available: [...]` |
| Input inválido | 400 | `Input validation failed` |
| Agente no encontrado en DB | 500 | `CrewConfigError: No active agent with role 'presupuestador'` |
| Tool no encontrado en registry | warning | Tool skipped, agent corre sin la tool |
| LLM no llama tool | N/A | Respuesta probablemente incorrecta (sin datos reales) |

### Punto crítico: LLM debe decidir llamar la tool

El desafío central del paso 3 NO es técnico (plumbing ya funciona) sino de **prompt engineering**. El LLM (llama-3.3-70b-versatile via Groq) debe:

1. Ver `excel_reader` en su lista de tools
2. Decidir activamente llamarla con los argumentos correctos
3. Usar el resultado para generar la respuesta

Esto depende de:
- Claridad del `description` del tool (`ExcelReaderTool.description`)
- Claridad del `soul_json.goal` y `soul_json.backstory`
- Claridad del `task_description` en el prompt
- Función calling support del modelo (llama-3.3-70b lo soporta vía Groq)

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo completo: DB → Backend → Frontend → UX

```
[DB: agent_catalog]
  ↓ (role='presupuestador', allowed_tools=['excel_reader'], soul_json)
[Backend: BaseCrew._load_agent_config()]
  ↓
[Backend: AgentFactory.create_agent_async()]
  ↓ (resolve_tools_async → excel_reader)
[Backend: crew.kickoff_async()]
  ↓ (LLM llama excel_reader → lee .xlsx → obtiene datos reales)
[Backend: PresupuestoFlow._run_crew() retorna resultado]
  ↓
[DB: state.complete() → persist_state() → snapshots + tasks]
  ↓
[API: GET /api/tasks/{task_id} → resultado JSON]
  ↓
[Frontend: Muestra presupuesto estructurado]
```

### Coherencia

- ✅ `agent_catalog.allowed_tools TEXT[]` soporta `["excel_reader"]`
- ✅ `tool_registry.get("excel_reader")` resuelve correctamente la clase
- ✅ `AgentFactory.resolve_tools_async()` maneja tools regulares y MCP
- ✅ `BaseCrew.run_async()` ejecuta vía `kickoff_async()`
- ⚠️ `PresupuestoFlow._run_crew()` hardcodea el prompt — no usa template dinámico

### Alineación con arquitectura

- Plan dice "El agente tiene `allowed_tools: ['excel_reader']` en su config" → ✅ `agent_catalog.allowed_tools` ya lo soporta
- Plan dice "AgentFactory.create_agent_async() resuelve el tool" → ✅ Funciona
- Plan dice "CrewAI Agent recibe el tool en su lista" → ✅ `Agent(tools=tools)` en factory.py:273
- Plan dice "Durante crew.kickoff_async(), el LLM decide llamar excel_reader" → ✅ Flujo correcto
- Plan dice "El resultado del tool se inyecta en el contexto del LLM" → ✅ CrewAI maneja esto internamente

### Gaps

1. **No hay seed data en código** — El paso 2 (registrar agente) debe crear el registro en `agent_catalog`. Sin ese registro, `BaseCrew._load_agent_config()` lanza `CrewConfigError`.
2. **No hay verificación de que `openpyxl` esté instalado** — Es dependencia implícita.
3. **El test E2E existente mockea CrewAI** — No verifica tool calling real.
4. **No hay forma de verificar que el LLM efectivamente llamó la tool** sin inspeccionar el output.

### Herramienta DX Propuesta

```
### Herramienta Propuesta: fap test-tool-call
- **Qué automatiza:** Verificación end-to-end de que un agente llama una herramienta durante ejecución real, sin mocks de CrewAI
- **Tipo:** CLI (comando fap)
- **Cómo se usa:** `fap test-tool-call --agent presupuestador --tool excel_reader --input '{"filename":"precios_bebidas.xlsx"}'`
- **Impacto para el usuario final:** Elimina la necesidad de crear tests manuales ad-hoc para verificar tool calling. Ejecuta el agente con LLM real o mockeado, verifica que la respuesta contiene datos de la tool.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Registro en agent_catalog con role='presupuestador' y allowed_tools=['excel_reader'] existe
✅ [DATA] soul_json del agente instruye explícitamente el uso de excel_reader
✅ [CODE] ExcelReaderTool registrado en tool_registry importando src.tools.excel_reader
✅ [CODE] AgentFactory.resolve_tools_async(['excel_reader'], org_id) retorna instancia de ExcelReaderTool
✅ [CODE] BaseCrew(org_id, 'presupuestador').run_async() crea Agent con excel_reader en tools
✅ [BACKEND] POST /api/webhooks/trigger con flow_type='presupuesto' dispra PresupuestoFlow
✅ [BACKEND] PresupuestoFlow._run_crew() ejecuta agente con LLM real (Groq)
✅ [BACKEND] LLM llama activamente excel_reader durante ejecución (no datos precargados)
✅ [BACKEND] Response contiene datos reales de PROJECT-Aybar/*.xlsx (no inventados)
✅ [FULLSTACK] Flujo completo DB → Agent → Tool → LLM → Output funciona sin mocks
✅ [FULLSTACK] Tool calling funciona con CrewAI sin patches de Crew/Task
✅ [DX] Herramienta fap test-tool-call ejecuta sin errores
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| LLM no llama la tool | Alta | Prompt poco claro o modelo no soporta function calling consistentemente | `soul_json` y `task_description` deben ser explícitos. Test con Groq `llama-3.3-70b-versatile`. Fallback: aumentar `max_iter` |
| `openpyxl` no instalado | Alta | Dependencia implícita, no está en `pyproject.toml` deps directas | Agregar `openpyxl>=3.1.0` a `[project.dependencies]` |
| Registro de agente no existe en DB | Alta | Paso 2 (registrar agente) es prerequisito. Sin registro, `CrewConfigError` | Seed script o verificación en test setup |
| `allowed_tools` vacío en config del agente | Media | Si seed data no incluye `allowed_tools` o es `[]`, agent no recibe tools | Validación en seed data |
| Rate limiting de Groq API | Media | Tests con LLM real consumen tokens y pueden hittear rate limits | Tests E2E con `@pytest.mark.real_llm` y skipif sin API key |
| Test flakiness por LLM no determinista | Media | LLM puede responder diferente cada vez | Verificar presencia de datos clave (no output exacto). Usar assertions flexibles |
| `BASE_DIR` hardcodeado en excel_reader | Baja | Path relativo puede romperse si se mueve archivo | Aceptable para MVP. Riesgo futuro |
| CrewAI tool description no suficientemente clara | Media | Formato de description influye en si el LLM decide usar la tool | Revisar y mejorar `ExcelReaderTool.description` con ejemplo de uso |

---

## 7️⃣ Plan de Implementación

> **Reglas de segmentación atómica:**
> 1. Una tarea = un artefacto
> 2. Interfaz completa en la tarea
> 3. Patrón de referencia explícito
> 4. Verificación inline
> 5. Implementador no decide nada

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: crear `fap test-tool-call`** | `src/cli/commands/tool_call_test.py` | `def test_tool_call(agent_role: str, tool_name: str, input_data: dict, llm: bool = False) -> dict` con retorno `{"tool_called": bool, "output": str, "tool_args": dict\|None}` | `src/cli/commands/check_env.py` (CLI Typer pattern) | DX | Media | 1h | Ninguna | → verificar: `fap test-tool-call --help` ejecuta sin errores |
| 1 | Agregar `openpyxl` a dependencias directas | `pyproject.toml` | Agregar `"openpyxl>=3.1.0"` en `[project.dependencies]` después de `"tenacity>=9.0.0"` | Dependencias existentes en `pyproject.toml` | CODE | Baja | 0.2h | Ninguna | → verificar: `uv sync` sin errores + `python -c "import openpyxl"` exitoso |
| 2 | Mejorar `ExcelReaderTool.description` para orientar al LLM | `src/tools/excel_reader.py:35-38` | `description: str = "Lee archivos .xlsx de la carpeta PROJECT-Aybar. Recibe filename (ej: 'precios_bebidas.xlsx') y opcionalmente sheet_name. Retorna datos como JSON estructurado donde keys son cabeceras de columnas. USAR ESTA TOOL para obtener datos reales antes de calcular presupuestos."` | `src/tools/service_connector.py:57` (patrón de descripción detallada) | CODE | Baja | 0.3h | Ninguna | → verificar: `python -c "from src.tools.excel_reader import ExcelReaderTool; print(ExcelReaderTool.description)"` muestra descripción mejorada |
| 3 | Mejorar `soul_json` del agente presupuestador | Seed data SQL o script | `soul_json = {"role": "Cotizador de Eventos", "goal": "Usar la herramienta excel_reader para obtener precios y datos reales de archivos Excel, y generar presupuestos detallados. SIEMPRE llamar excel_reader ANTES de calcular.", "backstory": "Sos un experto en cotización de eventos. Tu PRIMERA acción es SIEMPRE llamar la herramienta excel_reader para obtener datos reales de precios y consumos. Nunca inventás precios ni usás datos de entrenamiento."}` | Patrón existente en `test_real_tool_calling.py:51-63` (AGENT_CONFIG.soul_json) | DATA/CODE | Baja | 0.3h | Ninguna | → verificar: JSON válido, `goal` y `backstory` mencionan `excel_reader` explícitamente |
| 4 | Refinar prompt en `PresupuestoFlow._run_crew()` | `src/flows/presupuesto_flow.py:53-62` | Modificar `task` para instruir más explícitamente el uso de la tool: incluir `"PASO 1: Llamá a la herramienta excel_reader con filename='precios_bebidas.xlsx'"` | Prompt actual en `presupuesto_flow.py:53-62` | CODE | Baja | 0.3h | Tarea 2, 3 | → verificar: `python -c "from src.flows.presupuesto_flow import PresupuestoFlow; print(PresupuestoFlow._run_crew.__doc__)"` — o mejor, verificar string de task en fuente |
| 5 | Crear test E2E de tool calling real (sin mock de Crew) | `tests/e2e/test_tool_calling_real.py` | `async def test_presupuestador_calls_excel_reader()`: crear mock de agent_catalog, instanciar `BaseCrew(org_id, role="presupuestador")`, ejecutar `run_async()` con LLM real (Groq), verificar que output contiene datos de `precios_bebidas.xlsx`. Skipif sin GROQ_API_KEY. | `tests/e2e/test_real_tool_calling.py` (patrón de test con skipif) | BACKEND | Media | 1h | Tareas 1-4 | → verificar: `uv run pytest tests/e2e/test_tool_calling_real.py -v -m real_llm` con GROQ_API_KEY set |
| 6 | Crear test unitario: `resolve_tools_async` con `excel_reader` | `tests/unit/test_factory.py` (agregar clase) | `class TestExcelReaderResolution: async def test_resolve_excel_reader_async(self, sample_org_id)`: mockear `tool_registry.get("excel_reader", org_id=...)` retornando `ExcelReaderTool`, verificar que `resolve_tools_async(["excel_reader"], org_id)` retorna lista con instancia | `tests/unit/test_factory.py:157-191` (TestResolveToolsAsync existente) | BACKEND | Baja | 0.5h | Tarea 1 | → verificar: `uv run pytest tests/unit/test_factory.py::TestExcelReaderResolution -v` pasa |
| 7 | Validar flujo end-to-end: PresupuestoFlow con tool calling | — | — | — | FULLSTACK | Media | 0.5h | Tareas 1-6 | → verificar: criterios §5 [FULLSTACK] pasan todos + `fap test-tool-call --agent presupuestador --tool excel_reader` funciona |

**Tiempo total estimado:** 4.1 horas

> **NOTA:** La implementación real del paso 3 es principalmente **verificación + ajustes** (prompt, descripciones, tests). El plumbing ya existe. El riesgo principal es que el LLM no llame la tool consistentemente.

---

## 🔮 Roadmap (NO implementar ahora)

- **Caching de tool results** — `ExcelReaderTool` lee el archivo cada vez. Cache por filename+sheet_name con TTL reduciría latencia.
- **Error handling robusto en ExcelReaderTool** — Retry en archivos corruptos, validación de filename (path traversal).
- **Tool calling observability** — Log cada llamada a tool con timestamp, args, resultado, duración. Integrar con `domain_events`.
- **Template de prompt dinámico** — `PresupuestoFlow` hardcodea el prompt. Extracción a template con Jinja2 permitiría personalización.
- **Validación de output del LLM** — Respuesta JSON del presupuesto debería validarse contra schema (Pydantic model).
- **`openpyxl` write support** — Preparar para Paso 6 (ExcelWriterTool) — compartir BASE_DIR y patrones.
- **Métricas de tool calling** — Contador de llamadas, latencia, tasa de éxito por tool. Integrar con `flow_metrics`.

---

## 🚫 Reglas de Oro — Verificación

- ✅ Análisis accionable y específico
- ✅ TODO verificado contra código (24 elementos, 3 discrepancias)
- ✅ Discrepancias señaladas con resolución concreta
- ✅ Código gana sobre plan (plan dice `name`, DB usa `role`)
- ✅ Nivel CTO exigente
- ✅ Coherente con `phase-state.md`
- ✅ TODO el paso cubierto (5 sub-puntos del plan)
- ✅ Etapas secuenciales: data → code → backend → fullstack+DX
- ✅ DX propuesta: `fap test-tool-call`
- ✅ Tareas atómicas (1 artefacto cada una)
- ✅ Interfaces completas para cada tarea
- ✅ Patrón de referencia explícito
- ✅ Verificación inline por tarea