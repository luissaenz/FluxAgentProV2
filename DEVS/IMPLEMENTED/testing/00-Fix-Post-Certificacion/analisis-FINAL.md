
# 🏛️ Análisis Unificado — Paso 3: Tool Calling Real

> **Fecha:** 2026-05-03
> **Fase:** Patch agents (progreso 3/5 pasos)
> **Paso:** 3 — Tool Calling Real (plan.md:80-103)
> **Fuente de verdad:** `proyecto-config.json` + código en `src/` + `tests/` + `supabase/migrations/`
> **Tiempo est. plan:** 3h → **Tiempo est. FINAL:** 4.5h

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---:|:---:|:---:|:---:|:---:|
| **kimi** | ✅ | 4 | ToolCallTracer | ✅ | 4.2 |
| **qwen** | ✅ | 4 | `fap test-tool-calling` | ✅ | 4.5 |
| **glm** | ✅ | 3 | `fap test-tool-call` | ✅ | **4.6** |
| **ds** | ✅ | 5 | `fap test-tool-calling` | ✅ | 3.8 |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | `openpyxl` no está en `[project.dependencies]` | **glm** | ✅ `pyproject.toml` — ausente | Agregar `openpyxl>=3.1.0` a direct deps. Dependencia transitiva via `crewai-tools` (opcional) = riesgo instalación sin extras |
| 2 | `test_real_tool_calling.py` NO verifica invocación real de tool — assert débil (`"12000" in raw`) | **kimi**, **qwen**, **ds** | ✅ `test_real_tool_calling.py:112` | Agregar interceptor/tracer que cuente calls a `excel_reader._run()`. Assert `calls >= 1` |
| 3 | `test_real_agent_pipeline.py` usa `allowed_tools: []` con precios hardcodeados | **ds** | ✅ `test_real_agent_pipeline.py:60,102-108` | Migrar a `allowed_tools: ["excel_reader"]`, remover precios hardcodeados del prompt |
| 4 | Plan.md Paso 2 refiere `name` en bundle JSON pero DB usa `role` | **glm** | ✅ `004_agent_catalog.sql:8` — columna `role`, no `name` | Bundle debe usar `role` como identificador. Plan.md desactualizado |
| 5 | `PresupuestoFlow` ya existe (plan Paso 5 dice "Crear") | **kimi** | ✅ `src/flows/presupuesto_flow.py:23` — `@register_flow("presupuesto")` | Paso 5 se redefine a validación/refactor, no crear duplicado |
| 6 | `test_real_tool_calling.py` mockea `crewai.Crew` + `crewai.Task` (patches líneas 76-77) | **glm** | ✅ `test_real_tool_calling.py:76-77` | Test actual mockea CrewAI = NO prueba tool calling real. Crear test NUEVO sin patches para LLM real |
| 7 | `ExcelReaderTool.description` no optimizada para LLM function calling | **kimi**, **qwen**, **ds** | ✅ `excel_reader.py:35-39` — descripción genérica | Agregar ejemplos concretos + instrucciones cuándo usar la tool |
| 8 | `registry.py:158` usa `safe_builtins` directo, no `_create_safe_builtins()` | **qwen** | ✅ `src/tools/registry.py:158` | Fix plan v3.2 Paso 0 pendiente. No bloquea Paso 3. Documentar como deuda |
| 9 | `data/seed/` no existe (plan Paso 2 espera bundle seed) | **kimi** | ✅ `glob` vacío en raíz | No bloquea Paso 3 (tests mockean `agent_catalog`). Seed requerido para producción |

---

## 1️⃣ Resumen Ejecutivo

**Objetivo:** Que el agente `presupuestador` llame activamente `ExcelReaderTool` durante `crew.kickoff_async()` para leer `precios_bebidas.xlsx` — en vez de recibir datos precargados en el prompt.

**Correcciones críticas al plan:**
1. `openpyxl` es dependencia implícita (transitiva via `crewai-tools`). Agregar a direct deps o falla sin extras.
2. `test_real_tool_calling.py` patchea `crewai.Crew` + `crewai.Task` — el test NO prueba tool calling real.
3. `PresupuestoFlow` ya existe y está registrado. Plan Paso 5 asume crearlo → corregir a "validar".
4. Plan.md Paso 2 refiere campo `name` que no existe en schema DB (`role` es el campo real).

**Decisión DX:** `fap test-tool-call` (fusión de propuestas qwen + glm) como comando CLI que verifica tool calling con/sin LLM real.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. `PresupuestoFlow.execute(input_data)` recibe evento con `tipo_evento`, `pax`, `fecha`
2. `validate_input()` pasa — campos requeridos presentes
3. `create_task_record()` persiste en `tasks` con status PENDING
4. `BaseCrew(org_id, role="presupuestador").run_async(task_description, inputs)`
5. `_load_agent_config()` consulta `agent_catalog` → `soul_json`, `allowed_tools: ["excel_reader"]`, `max_iter: 5`
6. `AgentFactory.create_agent_async(config, org_id)` → `resolve_tools_async(["excel_reader"], org_id)`
7. `tool_registry.get("excel_reader")` → `ExcelReaderTool(org_id=org_id)`
8. `crewai.Agent(role, goal, backstory, llm=groq/llama-3.3-70b, tools=[ExcelReaderTool(...)])`
9. `crew.kickoff_async()` → LLM recibe task + tool description
10. LLM **decide** llamar `excel_reader(filename="precios_bebidas.xlsx")`
11. `ExcelReaderTool._run()` lee .xlsx → retorna JSON con precios
12. JSON se inyecta en contexto LLM → LLM calcula presupuesto
13. Output JSON estructurado: `precio_botella`, `botellas_necesarias`, `costo_total`
14. `persist_state()` → snapshots + tasks COMPLETED

### Edge Cases MVP

| # | Edge Case | Comportamiento esperado |
|---|---|---|
| EC1 | LLM no llama la tool (alucina precios) | Test falla con `ToolCallTracer.calls == 0`. Prompt + description deben forzar calling |
| EC2 | Tool name no existe en registry | `logger.warning` + skip. Agent opera sin esa tool |
| EC3 | Archivo .xlsx no existe | `ExcelReaderTool._run()` retorna `{"error": "Archivo 'X' no encontrado"}` |
| EC4 | `agent_catalog` sin registro activo para role | `CrewConfigError` elevado |
| EC5 | `allowed_tools` vacío o `[]` | Agent creado sin tools — responde con datos de entrenamiento |
| EC6 | Groq API key ausente o rate limited | Test skip con `skipif(!GROQ_API_KEY)`. Tool calling sin LLM real no verificable |
| EC7 | Multi-sheet: LLM pide sheet inexistente | Tool retorna `{"error": "Sheet 'X' no encontrada"}` |

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

| # | Ruta real | Tipo | Descripción | Interfaces clave | Patrón |
|---|---|---|---|---|---|
| 0 | `src/cli/commands/tool_call_test.py` | **Creación** | CLI `fap test-tool-call` — verifica tool calling con/sin LLM real | `def run(agent_role: str, tool_name: str, file: str, task: str, dry_run: bool, json_output: bool)` | `src/cli/commands/check_env.py` |
| 1 | `pyproject.toml` | **Modificación** | Agregar `openpyxl>=3.1.0` a `[project.dependencies]` | línea: `"openpyxl>=3.1.0"` después de `"tenacity>=9.0.0"` | Dependencias existentes |
| 2 | `src/tools/excel_reader.py:35-39` | **Modificación** | Mejorar `description` para LLM function calling | `description: str` — incluir ejemplos + instrucciones de uso | `src/tools/service_connector.py:57` |
| 3 | `src/crews/base_crew.py` | **Modificación** | Agregar atributo `_last_tool_calls` poblado durante ejecución | `get_last_tool_calls() -> list[dict]` | Patrón `get_last_tokens_used()` línea 165-167 |
| 4 | `tests/e2e/test_tool_calling_real.py` | **Creación** | Test E2E sin patches de CrewAI/Task. Verifica tool calling con LLM real | `async def test_presupuestador_calls_excel_reader()` | `test_real_tool_calling.py` (pero sin patches) |
| 5 | `tests/e2e/test_real_tool_calling.py` | **Modificación** | Agregar `ToolCallTracer` y assert `calls >= 1` | Assert reemplaza `"12000" in raw` por `tracer.calls["excel_reader"] >= 1` | Patrón tracer en test |
| 6 | `tests/e2e/test_real_agent_pipeline.py` | **Modificación** | Migrar `allowed_tools: []` → `["excel_reader"]`, remover precios hardcodeados | Cambiar `AGENT_CONFIG` + prompt | `test_real_tool_calling.py::AGENT_CONFIG` |
| 7 | `tests/unit/test_factory.py` | **Modificación** | Agregar test unitario `resolve_tools_async` con `excel_reader` | `class TestExcelReaderResolution` | `tests/unit/test_factory.py:157-191` |

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap test-tool-call
- **Qué automatiza:** Verificación end-to-end de que un agente llama una herramienta durante ejecución real, con/sin LLM real. Elimina configuración manual de tests para validar tool calling.
- **Tipo:** CLI (comando fap)
- **Ubicación:** `src/cli/commands/tool_call_test.py` (desde `proyecto-config.json: paths.cli_commands`)
- **Cómo se usa:**
  ```
  fap test-tool-call --agent presupuestador --tool excel_reader --file precios_bebidas.xlsx --task "Calculá costo de 100 cocteles"
  ```
  Flags:
  - `--dry-run`: solo verifica config sin ejecutar LLM
  - `--json`: output machine-readable
  - `--llm`: forzar uso de LLM real (Groq)
- **Impacto para el usuario final:** Reduce de ~15 min (configurar test manual con mock DB + mock CrewAI + verificar output) a ~30 seg. Permite iterar tool descriptions sin consumir tokens.
- **El implementador DEBE usarla** para completar las tareas 1..N del paso.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Herramienta DX unificada:** `fap test-tool-call` seleccionada sobre `ToolCallTracer` (kimi) porque CLI da verificación invocable sin modificar código de test. `ToolCallTracer` se fusiona como utilidad interna de `base_crew.py` (atributo `_last_tool_calls`).

2. **`openpyxl` como dependencia directa:** No puede ser transitiva via `crewai-tools` (opcional). `ExcelReaderTool` y `ExcelWriterTool` la requieren. Si `crewai` no está instalado, tool calling se rompe silenciosamente.

3. **Test E2E sin patches de CrewAI:** El test existente (`test_real_tool_calling.py:76-77`) patchea `crewai.Crew` + `crewai.Task` anulando el motor CrewAI. Crear `test_tool_calling_real.py` sin patches para validar tool calling real.

4. **Tool calling verification via tracer:** `BaseCrew.get_last_tool_calls()` expone lista de tools invocadas. Similar a `get_last_tokens_used()` existente. Permite assert programático sin parsear output del LLM.

5. **Correcciones al plan:**
   - ⚠️ Plan dice `agents/presupuestador.json` con campo `name` pero DB `agent_catalog` usa `role`. Se implementa `role` como identificador.
   - ⚠️ Plan dice Paso 5 "Crear `PresupuestoFlow`" pero ya existe (`src/flows/presupuesto_flow.py:23`). Se redefine Paso 5 a validación.
   - ⚠️ Plan no menciona `openpyxl` como dependencia. Se agrega como directa.
   - ⚠️ Plan no contempla test de tool calling sin patches de CrewAI. Se agrega `test_tool_calling_real.py`.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA] Registro en agent_catalog con role='presupuestador' y allowed_tools=['excel_reader'] existe
✅ [DATA] soul_json del agente instruye explícitamente el uso de excel_reader
✅ [CODE] AgentFactory.resolve_tools_async(['excel_reader'], org_id) retorna instancia de ExcelReaderTool
✅ [CODE] BaseCrew.run_async() crea Agent con excel_reader en tools
✅ [CODE] openpyxl>=3.1.0 en [project.dependencies] — uv sync sin errores
✅ [BACKEND] LLM (groq/llama-3.3-70b) llama excel_reader activamente
✅ [BACKEND] Output del agente contiene datos reales del xlsx (no inventados)
✅ [FULLSTACK] test_tool_calling_real.py pasa sin patches de CrewAI (requiere GROQ_API_KEY)
✅ [FULLSTACK] test_real_tool_calling.py modificado verifica tracer.calls >= 1
✅ [FULLSTACK] test_real_agent_pipeline.py migrado: usa allowed_tools=["excel_reader"]
✅ [DX] fap test-tool-call ejecuta sin errores con --dry-run y --help
```

**Funcionales:**
- [ ] Agente `presupuestador` con `allowed_tools=["excel_reader"]` llama tool al ejecutar `BaseCrew.run_async()`
- [ ] Output contiene `costo_total`, `precio_botella`, `botellas_necesarias` (datos reales de sheet)

**Técnicos:**
- [ ] `resolve_tools_async(["excel_reader"], org_id)` retorna `[ExcelReaderTool(org_id=...)]`
- [ ] `BaseCrew.get_last_tool_calls()` retorna lista con ≥1 entry para `excel_reader`
- [ ] `fap test-tool-call --dry-run --agent presupuestador --tool excel_reader` → exit 0
- [ ] `uv sync` exitoso después de agregar `openpyxl`

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** `fap test-tool-call` — `src/cli/commands/tool_call_test.py` | Media | 1.5h | Ninguna |
| 1 | Agregar `openpyxl>=3.1.0` a `[project.dependencies]` en `pyproject.toml` | Baja | 0.2h | Ninguna |
| 2 | Mejorar `ExcelReaderTool.description` para LLM function calling | Baja | 0.3h | Tarea 0 |
| 3 | Agregar `get_last_tool_calls()` en `BaseCrew` (`src/crews/base_crew.py`) | Media | 1h | Tarea 2 |
| 4 | Crear `tests/e2e/test_tool_calling_real.py` (sin patches CrewAI) | Media | 1h | Tareas 0-3 |
| 5 | Modificar `test_real_tool_calling.py` con `ToolCallTracer` + assert `calls ≥ 1` | Baja | 0.5h | Tarea 3 |
| 6 | Migrar `test_real_agent_pipeline.py` a `allowed_tools: ["excel_reader"]` | Baja | 0.5h | Tarea 0 |
| 7 | Agregar test unitario `TestExcelReaderResolution` en `test_factory.py` | Baja | 0.5h | Tarea 0 |
| **TOTAL** | | | **4.5h** | |

> [!IMPORTANT]
> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar `fap test-tool-call` para el resto del paso (dogfooding obligatorio).

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| LLM no llama la tool (alucina precios) | **Alta** | `soul_json`/`description` poco explícitos. LLM usa datos entrenamiento en vez de tool | `ToolCallTracer` falla test si `calls == 0`. Reforzar `backstory`: "SIEMPRE usás excel_reader. NUNCA inventés" |
| CrewAI function calling incompatible con Groq | **Alta** | CrewAI ≥0.100 schema puede no mapear a Groq function calling | Test con LLM real inmediato (Tarea 4). Fallback: inyectar datos vía prompt como workaround |
| `openpyxl` ausente en runtime sin extras | **Alta** | `crewai-tools` no instalado → `openpyxl` no disponible | Tarea 1 (direct dep) elimina este riesgo |
| Groq API rate limiting / timeout | **Media** | Tests E2E con LLM real consumen tokens | Tests con `skipif(!GROQ_API_KEY)`. `tenacity` retry ya disponible |
| Test flakiness por LLM no determinista | **Media** | LLM responde diferente cada ejecución | Verificar presencia de datos clave (no output exacto). `tracer.calls >= 1` es determinista |
| `_load_from_db()` en `registry.py:158` sin `_create_safe_builtins()` | **Media** | Vector `__import__` sin restricción en carga de skills DB | Fix plan v3.2 Paso 0 pendiente. No bloquea Paso 3. Documentado como deuda |
| `BASE_DIR` hardcodeado en `excel_reader.py:20` | **Baja** | Path relativo frágil si archivo se mueve | Aceptable MVP. Roadmap: migrar a Google Sheets API |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Tool resolution: `resolve_tools_async(["excel_reader"], org_id)` | `org_id` UUID | `[ExcelReaderTool(org_id=org_id)]` — tipo y org_id correctos |
| TP-2 | Tool calling real: agente `presupuestador` con LLM real | `task_description` pidiendo leer `precios_bebidas.xlsx` | `tracer.calls["excel_reader"] >= 1` + output contiene datos de sheet |
| TP-3 | Tool calling sin patches CrewAI: `BaseCrew.run_async()` | `org_id`, `role="presupuestador"` con mock DB | `crew.kickoff_async()` ejecuta sin error, output tiene `costo_total` |
| TP-4 | Tool missing: `allowed_tools: ["tool_que_no_existe"]` | `org_id`, role cualquiera | `logger.warning` emitido, Agent creado sin tools, sin crash |
| TP-5 | `ExcelReaderTool._run()` con archivo inexistente | `filename="no_existe.xlsx"` | `{"error": "Archivo 'no_existe.xlsx' no encontrado en ..."}` |
| TP-6 | `ExcelReaderTool._run()` con sheet inexistente | `filename="precios_bebidas.xlsx"`, `sheet_name="NOEXISTE"` | `{"NOEXISTE": [{"error": "Sheet 'NOEXISTE' no encontrada"}]}` |
| TP-7 | `uv sync` con `openpyxl` agregado | `uv sync --all-extras` | Éxito sin errores. `python -c "import openpyxl"` exitoso |

Comando para ejecutar tests:
```bash
# Unitarios
uv run pytest tests/unit/test_factory.py::TestExcelReaderResolution -v

# E2E tool calling real (requiere GROQ_API_KEY)
uv run pytest tests/e2e/test_tool_calling_real.py -v

# Test migrado (requiere GROQ_API_KEY)
uv run pytest tests/e2e/test_real_agent_pipeline.py -v
```
