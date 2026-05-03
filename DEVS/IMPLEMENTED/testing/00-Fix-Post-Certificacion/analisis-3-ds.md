# Análisis Técnico — Paso 3: Tool Calling Real

**Agente:** ds  
**Fecha:** 2026-05-03  
**Paso:** 3 — Tool Calling Real (Agente usa herramienta durante ejecución)  
**Plan:** `DEVS/plan.md:80-102`  
**Estimación plan:** 3h  

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `AgentFactory.create_agent_async()` existe con firma `(config: Dict[str, Any], org_id: str) -> Agent` | grep en `src/crews/factory.py` | ✅ | `factory.py:260-282` — `async def create_agent_async(config, org_id)` |
| 2 | `resolve_tools_async()` resuelve `excel_reader` desde `tool_registry.get()` | grep en `src/crews/factory.py` | ✅ | `factory.py:224-226` — `tool_cls = tool_registry.get(tool_name, org_id=org_id)` + `tool_cls(org_id=org_id)` |
| 3 | `ExcelReaderTool` registrado via `@register_tool("excel_reader")` | grep en `src/tools/excel_reader.py` | ✅ | `excel_reader.py:28-32` — decorador con `description`, `tags` |
| 4 | `ExcelReaderTool` hereda de `OrgBaseTool(BaseTool)` | grep en `src/tools/excel_reader.py` | ✅ | `excel_reader.py:33` — `class ExcelReaderTool(OrgBaseTool)` |
| 5 | CrewAI Agent recibe tools en su lista | grep en `src/crews/factory.py` | ✅ | `factory.py:281` — `tools=tools` en constructor `Agent(...)` |
| 6 | `test_real_tool_calling.py` existe con `allowed_tools: ["excel_reader"]` | grep en `tests/e2e/` | ✅ | `test_real_tool_calling.py:60` — `"allowed_tools": ["excel_reader"]` |
| 7 | `test_real_agent_pipeline.py` usa `allowed_tools: []` (datos precargados) | grep en `tests/e2e/` | ✅ | `test_real_agent_pipeline.py:60` — `"allowed_tools": []` + precios hardcodeados en prompt (líneas 102-108) |
| 8 | `BaseCrew.run_async()` llama `AgentFactory.create_agent_async()` | grep en `src/crews/base_crew.py` | ✅ | `base_crew.py:185` — `agent = await AgentFactory.create_agent_async(config, self.org_id)` |
| 9 | `PresupuestoFlow._run_crew()` referencia `excel_reader` en prompt | grep en `src/flows/presupuesto_flow.py` | ✅ | `presupuesto_flow.py:44-61` — instructs agent to use `excel_reader` tool |
| 10 | `PresupuestoFlow` agente config permite `allowed_tools: ["excel_reader"]` | grep en `tests/e2e/test_presupuesto_flow.py` | ✅ | `test_presupuesto_flow.py:55` — `"allowed_tools": ["excel_reader"]` |
| 11 | `ExcelReaderTool.args_schema` = `ExcelReaderInput` (Pydantic) | grep en `excel_reader.py` | ✅ | `excel_reader.py:40` — `args_schema: Type[BaseModel] = ExcelReaderInput` |
| 12 | `ExcelReaderTool._run()` acepta `filename: str` y `sheet_name: Optional[str]` | grep en `excel_reader.py` | ✅ | `excel_reader.py:42` — `def _run(self, filename: str, sheet_name: Optional[str] = None)` |
| 13 | `precios_bebidas.xlsx` existe en `PROJECT-Aybar/` | glob | ✅ | `PROJECT-Aybar/precios_bebidas.xlsx` presente |
| 14 | `config_consumo_pax.xlsx` existe en `PROJECT-Aybar/` | glob | ✅ | `PROJECT-Aybar/config_consumo_pax.xlsx` presente |
| 15 | Test `test_agent_uses_excel_reader_tool` verifica tool data en output | grep en `test_real_tool_calling.py` | ✅ | `test_real_tool_calling.py:112` — `assert "12000" in raw or "gordon" in raw.lower()` |

### Discrepancias encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | `test_real_agent_pipeline.py` (línea 60) usa `allowed_tools: []` con precios hardcodeados en prompt. Plan dice que los tests "pasan datos precargados" — esto es el estado PRE-Paso 3. | Reemplazar con `allowed_tools: ["excel_reader"]` y remover precios hardcodeados del prompt. El agente debe leer `precios_bebidas.xlsx` via tool. |
| D2 | `test_real_agent_pipeline.py` (línea 51-63) tiene `soul_json` que NO menciona `excel_reader` ni el uso de herramientas. | Actualizar `soul_json.goal` y `backstory` para forzar uso de tool (similar a `test_real_tool_calling.py:53-58`). |
| D3 | `test_real_tool_calling.py` (línea 95) usa `BaseCrew.run_async()` pero el path pasa por `_load_agent_config()` que requiere DB mock (`get_service_client`). El test parcha `base_crew.get_service_client` pero NO parcha `base_crew.get_service_client` explícitamente — usa el fixture del conftest? Revisar: el test NO usa `mock_service_client` fixture, parcha directamente `base_crew.get_service_client`. | El parche directo en línea 92 es correcto pero frágil. Usar `mock_service_client` fixture del conftest es más mantenible. |
| D4 | `test_real_agent_pipeline.py` y `test_real_tool_calling.py` son funcionalmente duplicados en propósito (ambos prueban BaseCrew con LLM real). El plan no especifica si uno reemplaza al otro o ambos deben coexistir. | Clarificar: `test_real_tool_calling.py` es el test DEL Paso 3. `test_real_agent_pipeline.py` debe migrarse al nuevo patrón o eliminarse. |
| D5 | `ExcelReaderTool` description actual (línea 35-39) es genérica. No especifica que el LLM DEBE llamarla para obtener datos. CrewAI function calling depende de tool description para que el LLM decida invocar. | Mejorar tool description para que el LLM entienda cuándo debe llamarla. |

---

## 1️⃣ Análisis de Datos

### Schema involucrado
- **Ningún cambio de schema.** Paso 3 es puramente de código + tests. El tool `excel_reader` ya lee archivos .xlsx locales.

### Archivos de datos existentes
- `PROJECT-Aybar/precios_bebidas.xlsx` — precios de bebidas para cotización
- `PROJECT-Aybar/config_consumo_pax.xlsx` — configuración de consumo por PAX

### Impacto en datos existentes
- Sin impacto. Los .xlsx son read-only para `ExcelReaderTool`.

### Puntos clave
- ✅ No se requieren migraciones ni cambios de schema
- ✅ RLS no aplica (tools locales)
- ✅ Sin índices ni constraints nuevos

---

## 2️⃣ Análisis de Código

### Funciones/clases existentes tocadas

#### `AgentFactory.create_agent_async()` — `src/crews/factory.py:260-282`
```python
@staticmethod
async def create_agent_async(config: Dict[str, Any], org_id: str) -> Agent
```
- **Parámetros:** `config` (dict con `soul_json`, `allowed_tools`, etc.), `org_id`
- **Retorno:** `crewai.Agent`
- **Ya resuelve tools correctamente:** línea 270-271
- **Cambio necesario:** Ninguno. Ya soporta `allowed_tools` correctamente.

#### `AgentFactory.resolve_tools_async()` — `src/crews/factory.py:192-232`
```python
@staticmethod
async def resolve_tools_async(allowed_tools: list[str], org_id: str) -> list
```
- **Ya resuelve `excel_reader`:** línea 224-226
- **Patrón:** obtiene clase del registry, instancia con `org_id`
- **Cambio necesario:** Ninguno.

#### `ExcelReaderTool` — `src/tools/excel_reader.py:33-97`
```python
class ExcelReaderTool(OrgBaseTool):
    name: str = "excel_reader"
    description: str = "Lee archivos .xlsx de la carpeta PROJECT-Aybar..."
    args_schema: Type[BaseModel] = ExcelReaderInput

    def _run(self, filename: str, sheet_name: Optional[str] = None) -> str:
```
- **Patrón:** Sigue `OrgBaseTool(BaseTool)` con Pydantic input schema
- **Cambio necesario:** Optimizar `description` para LLM function calling (ver §Discrepancias)

### Patrones existentes
- **Tool registration pattern:** `@register_tool("name", ...)` decorador en clase
- **Tool base class pattern:** `OrgBaseTool(BaseTool)` con `_run()` implementado
- **Factory pattern:** `AgentFactory.resolve_tools_async()` como punto central de resolución

### Calidad / Modularidad
- ✅ Resolución centralizada en `AgentFactory` — single source of truth
- ✅ Tools independientes del agente — desacoplamiento correcto
- ❌ `ExcelReaderTool.description` no está optimizada para LLM function calling

### Imports exactos necesarios
```python
# Ya existentes en factory.py
from src.tools.registry import tool_registry

# Ya existentes en excel_reader.py
from src.tools.base_tool import OrgBaseTool
from src.tools.registry import register_tool
```

---

## 3️⃣ Análisis de Backend

### Endpoints
- **Ningún endpoint nuevo.** Paso 3 es puramente de agentes/tools.
- `PresupuestoFlow._run_crew()` usa `BaseCrew.run_async()` que resuelve tools y ejecuta crew.

### Middleware
- No aplica. Tools se ejecutan localmente sin HTTP.

### Flujo de datos
```
AgentFactory.create_agent_async()
  → resolve_tools_async(["excel_reader"], org_id)
    → tool_registry.get("excel_reader", org_id=org_id) → ExcelReaderTool class
    → ExcelReaderTool(org_id=org_id) → instancia
  → Agent(tools=[ExcelReaderTool(org_id=xxx)])
    → crew.kickoff_async()
      → LLM decide llamar excel_reader(filename="precios_bebidas.xlsx")
        → ExcelReaderTool._run() lee .xlsx → JSON
        → resultado inyectado en contexto LLM
      → LLM genera respuesta final con datos reales
```

### Contratos
- ✅ `allowed_tools` en config del agente → tools resueltas e instanciadas
- ✅ Cada tool recibe `org_id` en constructor
- ✅ CrewAI maneja function calling automáticamente

### Error handling
- ✅ `resolve_tools_async()` captura `ValueError` si tool no está en registry (línea 228-230)
- ✅ `ExcelReaderTool._run()` retorna `{"error": ...}` en JSON si archivo no existe
- ❌ CrewAI no propaga errores de tool calling al LLM de forma explícita — depende del modelo

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo end-to-end
```
Usuario → PresupuestoFlow.execute()
  → BaseCrew.run_async()
    → AgentFactory.create_agent_async()
      → resolve_tools_async(["excel_reader"])
        → tool_registry.get("excel_reader") → clase
        → ExcelReaderTool(org_id=xxx) → instancia
    → CrewAI Agent(tools=[ExcelReaderTool])
    → crew.kickoff_async()
      → LLM (Groq/llama-3.3-70b) recibe tool description
      → LLM decide: "necesito precio de Gordon's Pink"
      → LLM genera function call: excel_reader(filename="precios_bebidas.xlsx")
      → CrewAI ejecuta _run() → JSON con precios
      → Resultado vuelve al LLM como contexto
      → LLM genera respuesta final con cálculo
    → Output: JSON con presupuesto
```

### Coherencia
- ✅ `test_real_tool_calling.py` ya implementa el flujo completo
- ✅ `PresupuestoFlow._run_crew()` instructs agente a usar tool
- ✅ Tool description + LLM function calling habilitan decisión autónoma del LLM

### Gaps
1. **D1** — `test_real_agent_pipeline.py` no migrado al nuevo patrón
2. **D5** — `ExcelReaderTool.description` no optimizada para function calling
3. **Gap de tool calling confiable:** CrewAI con Groq/llama-3.3-70b debe soportar function calling. No hay test que verifique esto sin LLM real.
4. **Falta test de multi-herramienta:** El plan dice que el agente debe decidir llamar `excel_reader` según necesidad. Solo hay test para un escenario.

### DX & Tooling

```
### Herramienta Propuesta: fap test-tool-calling
- **Qué automatiza:** Verifica localmente que la tool description de ExcelReaderTool genera function calls válidas en formato CrewAI, sin necesidad de LLM real ni Groq API key.
- **Tipo:** script / comando CLI
- **Cómo se usa:**
  ```
  fap test-tool-calling --tool excel_reader
  ```
  Genera un schema de function calling simulado, valida que CrewAI lo parsea correctamente, y verifica que `_run()` responde con JSON válido para archivos .xlsx existentes.
- **Impacto para el usuario final:** Elimina la dependencia de GROQ_API_KEY para validar que el tool calling funciona. Reduce tiempo de feedback de "ejecutar test E2E con LLM real" (~30s) a "ejecutar verificación local" (~1s). Permite iterar tool descriptions sin consumir tokens.
- **Prioridad:** Tarea 0 — implementar antes que modificar tests existentes
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] AgentFactory.resolve_tools_async() resuelve "excel_reader" → ExcelReaderTool(org_id=xxx) instancia
✅ [CODE] CrewAI Agent recibe ExcelReaderTool en su lista de tools
✅ [BACKEND] AgentFactory.create_agent_async() retorna Agent con tools≠[] cuando allowed_tools=["excel_reader"]
✅ [FULLSTACK] test_real_tool_calling.py pasa: LLM real llama excel_reader y output contiene datos de sheet
✅ [FULLSTACK] test_real_agent_pipeline.py migrado: usa allowed_tools=["excel_reader"] en lugar de precios hardcodeados
✅ [FULLSTACK] PresupuestoFlow._run_crew() con LLM real + tool calling produce presupuesto con datos reales
✅ [DX] Herramienta fap test-tool-calling verifica schema de function calling localmente sin LLM real
✅ [DATA] Sin cambios de schema — ExcelReaderTool funciona con .xlsx existentes
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| CrewAI function calling no funciona con Groq/llama-3.3-70b | Alta | CrewAI ≥0.100 puede tener bugs de integración con Groq. No hay test unitario que valide el parsing de function calls sin LLM real. | Agregar test con mock de CrewAI que verifique que el tool es pasado al Agent. En `test_real_tool_calling.py`, verificar que Crew recibe tools en constructor. |
| Tool description no induce al LLM a llamar la herramienta | Media | Si el LLM no entiende cuándo debe llamar `excel_reader`, responde con datos inventados (alucinación). | Mejorar `ExcelReaderTool.description` con ejemplos concretos de cuándo usarla. Agregar instrucciones en `soul_json.backstory`. |
| `test_real_agent_pipeline.py` obsoleto perpetúa el viejo patrón | Media | Si nadie migra este test, futuros desarrolladores copian el patrón de datos hardcodeados en vez de tool calling real. | Migrar a `allowed_tools: ["excel_reader"]` como parte de este paso. Marcar test con `@pytest.mark.real_llm`. |
| Faltan archivos .xlsx para pruebas de multi-herramienta | Baja | Solo `precios_bebidas.xlsx` y `config_consumo_pax.xlsx` existen. Si el agente necesita otras sheets, falla silenciosamente. | Verificar existencia de todos los .xlsx referenciados. Agregar test que verifique `ExcelReaderTool._run()` con cada archivo. |
| Sin test de fallo de tool calling | Baja | Si el archivo no existe o la tool falla, CrewAI no informa el error al LLM de forma confiable. | Agregar test que verifique comportamiento del agente cuando tool retorna error. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling:** Crear `fap test-tool-calling` | `src/cli/commands/tool_calling_check.py` | `def run(tool_name: str) -> None` — simula function call schema, valida `_run()` con archivos reales | `src/cli/commands/security_audit.py :: run()` | DX | Media | 1h | Ninguna | → verificar: `uv run python -m src.cli.main test-tool-calling --tool excel_reader` retorna schema válido |
| 1 | Migrar `test_real_agent_pipeline.py` a tool calling real | `tests/e2e/test_real_agent_pipeline.py` | Cambiar `allowed_tools: []` → `["excel_reader"]`, remover precios hardcodeados del prompt, actualizar `soul_json` | `tests/e2e/test_real_tool_calling.py :: AGENT_CONFIG` | CODE | Baja | 0.5h | Tarea 0 | → verificar: `uv run pytest tests/e2e/test_real_agent_pipeline.py -v` pasa (requiere GROQ_API_KEY) |
| 2 | Mejorar `ExcelReaderTool.description` para LLM function calling | `src/tools/excel_reader.py` | Actualizar `description` con ejemplos concretos: cuándo usarla, qué archivos leer, qué datos retorna | `src/tools/excel_reader.py:35-39` (reemplazar descripción genérica) | CODE | Baja | 0.25h | Tarea 0 | → verificar: Tool description contiene ejemplos de uso y formato de retorno |
| 3 | Verificar test existente `test_real_tool_calling.py` pasa con LLM real | `tests/e2e/test_real_tool_calling.py` | Sin cambios de código. Ejecutar y verificar que LLM real llama `excel_reader` y output contiene datos de sheet | — | BACKEND | Baja | 0.25h | Tarea 1, 2 | → verificar: `uv run pytest tests/e2e/test_real_tool_calling.py -v` pasa |
| 4 | Validar flujo end-to-end `PresupuestoFlow` con tool calling | `tests/e2e/test_presupuesto_flow.py` | Verificar que `test_execute_with_real_llm` corre con `allowed_tools: ["excel_reader"]` y datos reales | — | FULLSTACK | Baja | 0.5h | Tareas 1-3 | → verificar: `uv run pytest tests/e2e/test_presupuesto_flow.py::TestPresupuestoFlow::test_execute_with_real_llm -v` pasa |

**Tiempo total estimado:** 2.5 horas (vs 3h plan original — ahorro porque `resolve_tools_async` ya implementado)

### Dependencias entre tareas
```
Tarea 0 (DX tool) ──┬──→ Tarea 1 (migrar test pipeline)
                     └──→ Tarea 2 (mejorar description) ──→ Tarea 3 (verificar test existente) ──→ Tarea 4 (validar E2E)
```

---

## 🔮 Roadmap

- **Test de multi-herramienta:** Agregar test donde agente debe llamar `excel_reader` con `filename="precios_bebidas.xlsx"` Y `filename="config_consumo_pax.xlsx"` en同一 ejecución.
- **Validación de function calling sin LLM real:** Integrar `fap test-tool-calling` en CI para verificar tool descriptions sin consumir tokens.
- **Rate limiting de tools:** Si el agente llama la tool muchas veces, puede degradar performance. Agregar cache de resultados de `ExcelReaderTool._run()` para archivos no modificados.
- **Integración Google Sheets API:** Cuando `ExcelReaderTool` soporte sheets remotas, tool calling requerirá auth. Preparar `OrgBaseTool._get_secret()` para ese flujo.

---

## 📊 Métricas de Calidad

| Métrica | Estado |
|---|---|
| `proyecto-config.json` leído antes de explorar | ✅ |
| Elementos verificados (§0) | 15 ≥ 12 (3-5 archivos afectados) |
| Discrepancias detectadas | 5 ≥ 1 (código existente) |
| Secciones completadas | 8 (0-7) |
| Etapas cubiertas | 4 (data, code, backend, fullstack+DX) |
| Criterios de aceptación | 6 (≥ 1 por sub-paso) |
| Riesgos identificados | 5 (≥ 3) |
| Tareas atómicas (1 artefacto por tarea) | 100% |
| Interfaz exacta por tarea | 100% |
| Patrón de referencia explícito por tarea | 100% |
| Verificación inline por tarea | 100% |
| Propuesta DX / Tooling | 1 herramienta concreta (fap test-tool-calling) |
| Estimación de tiempo | 2.5h total, por tarea desglosada |
