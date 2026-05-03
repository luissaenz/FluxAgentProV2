# Análisis Técnico — Paso 3: Tool Calling Real

> **Agente:** kimi  
> **Paso:** 3 (Tool Calling Real)  
> **Fecha:** 2026-05-03  
> **Fuente de verdad:** código fuente en `src/`, migraciones en `supabase/migrations/`, tests en `tests/`

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|--------------|--------|-----------|
| 1 | Tabla `agent_catalog` existe | Migración 004 | ✅ | `004_agent_catalog.sql:6` |
| 2 | Columna `allowed_tools` es `text[]` | Migración 004 | ✅ | `004_agent_catalog.sql:12` |
| 3 | `ExcelReaderTool` registrado en `tool_registry` | Decorador `@register_tool` | ✅ | `src/tools/excel_reader.py:28` |
| 4 | Import trigger en `src/tools/__init__.py` | `import src.tools.excel_reader` | ✅ | `src/tools/__init__.py:4` |
| 5 | `AgentFactory.resolve_tools_async()` resuelve regular tools | Bucle `tool_registry.get()` + instanciación | ✅ | `src/crews/factory.py:224` |
| 6 | `AgentFactory.create_agent_async()` llama `resolve_tools_async()` | `tools = await resolve_tools_async(...)` | ✅ | `src/crews/factory.py:271` |
| 7 | `BaseCrew.run_async()` usa `create_agent_async()` | `agent = await AgentFactory.create_agent_async(...)` | ✅ | `src/crews/base_crew.py:185` |
| 8 | `PROJECT-Aybar/precios_bebidas.xlsx` existe | Listado de directorio | ✅ | `bash: PROJECT-Aybar/precios_bebidas.xlsx` |
| 9 | Test `test_real_tool_calling.py` existe y configura `allowed_tools` | Archivo + dict `AGENT_CONFIG` | ✅ | `tests/e2e/test_real_tool_calling.py:60` |
| 10 | Test restaura clases reales de CrewAI | `patch("crewai.Crew", _REAL_CREW)` | ✅ | `tests/e2e/test_real_tool_calling.py:76-77` |
| 11 | `ExcelReaderTool` hereda `OrgBaseTool` | Declaración de clase | ✅ | `src/tools/base_tool.py:18` |
| 12 | `Agent` recibe lista `tools` en constructor | Parámetro `tools=tools` | ✅ | `src/crews/factory.py:257` |
| 13 | `PresupuestoFlow` ya existe en `src/flows/` | Archivo presente | ❌ | `src/flows/presupuesto_flow.py` — plan Paso 5 dice "Crear" |
| 14 | `proyecto-config.json` fase desactualizada | `phase_name: "testing"` vs `phase-state.md` | ❌ | `proyecto-config.json:137-138` |
| 15 | Directorio `data/seed/` no existe | `glob` vacío | ❌ | Plan Paso 2 espera bundle seed |
| 16 | `test_real_tool_calling.py` no distingue tool call de alucinación | Assert débil (`"12000" in raw`) | ❌ | `tests/e2e/test_real_tool_calling.py:112` |

**Discrepancias encontradas:**

1. **Config de fase stale (`proyecto-config.json`)**
   - **Problema:** `phase_name` sigue como `"testing"` y `phase_completed: true`, pero `phase-state.md` indica fase `"Patch agents"` en progreso (3/5 pasos).
   - **Resolución:** Actualizar `proyecto-config.json` con `phase_name: "patch_agents"`, `current_step: "03-Tool-Calling-Real"`, `steps_completed: 3` (o dejar para paso de cierre).

2. **`PresupuestoFlow` existe antes de lo planificado**
   - **Problema:** `src/flows/presupuesto_flow.py` ya está implementado y registrado (`@register_flow("presupuesto")`). El plan Paso 5 indica "Crear `PresupuestoFlow`".
   - **Resolución:** Paso 5 pasa de "crear" a "validar/refactorar". No modificar `presupuesto_flow.py` en este paso.

3. **`data/seed/` ausente**
   - **Problema:** El plan Paso 2 requiere crear bundle seed en `data/seed/`. El directorio no existe.
   - **Resolución:** Paso 3 no está bloqueado porque `test_real_tool_calling.py` mockea `agent_catalog`. Sin embargo, para producción real se requiere completar Paso 2 antes.

4. **Test de tool calling no prueba invocación real**
   - **Problema:** `test_real_tool_calling.py` solo verifica que el output contenga `"12000"` o `"gordon"`. El LLM podría alucinar esos valores sin llamar la herramienta.
   - **Resolución:** Agregar interceptor de llamadas a `_run()` (DX ToolCallTracer) y assertear `calls >= 1`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema
- **Tabla tocada:** `agent_catalog` (lectura).
- **Columna relevante:** `allowed_tools text[] DEFAULT '{}'`. Almacena nombres de herramientas en formato libre (soft reference al `tool_registry`).
- **No se requieren cambios de schema** para este paso.

### Integridad Referencial
- `agent_catalog.org_id` → `organizations.id` (`ON DELETE CASCADE`).
- `allowed_tools` **no tiene FK** hacia `skill_catalog` ni `tool_registry`. Riesgo de nombre desfasado.

### RLS
- Política `agent_catalog_tenant_isolation` (`org_id::text = current_setting('app.org_id', TRUE)`).
- BaseCrew carga config vía `get_service_client()` (service-role), por lo que RLS no aplica en el backend. El aislamiento depende del query explícito `.eq("org_id", self.org_id)`.

### Índices
- `idx_agent_catalog_org_role` sobre `(org_id, role)` filtrado `is_active = TRUE`. Suficiente.

### Tipos de Datos
- `soul_json JSONB`: personalidad del agente.
- `allowed_tools text[]`: lista de strings. Sin validación de existencia en DB.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/Clases involucradas

| Función/Clase | Archivo | Firma | Rol en el paso |
|---------------|---------|-------|----------------|
| `AgentFactory.resolve_tools_async()` | `src/crews/factory.py` | `async def resolve_tools_async(allowed_tools: list[str], org_id: str) -> list` | Resuelve nombres a instancias de tools, incluyendo `excel_reader`. |
| `AgentFactory.create_agent_async()` | `src/crews/factory.py` | `async def create_agent_async(config: Dict[str, Any], org_id: str) -> Agent` | Crea CrewAI Agent con `tools` ya resueltos. |
| `BaseCrew.run_async()` | `src/crews/base_crew.py` | `async def run_async(...)` | Orquesta: carga config → crea agente → ejecuta crew. |
| `ExcelReaderTool._run()` | `src/tools/excel_reader.py` | `def _run(self, filename: str, sheet_name: Optional[str] = None) -> str` | Lógica de lectura Excel. Retorna JSON string. |
| `ToolRegistry.get()` | `src/tools/registry.py` | `def get(self, name: str, org_id: str \| None = None) -> Type` | Lookup de clase por nombre; fallback a DB/filesystem. |

### Patrones
- **Resolución centralizada:** `AgentFactory` es el único punto de resolución de tools (sync y async). Consistente con decisiones de arquitectura de Fase V.
- **Registry singleton:** `tool_registry` global. `ExcelReaderTool` se registra al importar `src.tools.excel_reader` (trigger vía `src/tools/__init__.py`).
- **Async-first para MCP:** `resolve_tools_async()` usa `await` para MCP y sync para regulares. Para `excel_reader` (regular) no hay diferencia funcional entre sync/async.

### Modularidad
- **Cohesión alta:** Cada clase tiene responsabilidad única (Factory → creación, BaseCrew → ejecución, ExcelReaderTool → I/O).
- **Acoplamiento bajo:** BaseCrew no conoce `ExcelReaderTool`; solo conoce `AgentFactory`.

### Calidad
- `ExcelReaderTool._run()` tiene complejidad ciclomática moderada (header detection, null filtering). Aceptable para MVP.
- No hay duplicación de código de resolución de tools.

### Imports
- `src/crews/factory.py` importa `src.tools.registry.tool_registry`.
- `src/crews/base_crew.py` importa `src.crews.factory.AgentFactory` (lazy inside métodos).
- `src/tools/excel_reader.py` importa `src.tools.base_tool.OrgBaseTool` y `src.tools.registry.register_tool`.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### APIs / Endpoints
- **No se crean ni modifican endpoints** en este paso. El tool calling ocurre dentro de `BaseCrew.run_async()`, invocado desde flows.

### Middleware
- **Auth:** JWT + org isolation (`src/api/middleware.py`). Fuera de alcance directo del paso, pero los tests E2E mockean el cliente Supabase.

### Flujo de Datos

```
DB (agent_catalog)
  ↓ _load_agent_config()
BaseCrew
  ↓ run_async()
AgentFactory.create_agent_async(config, org_id)
  ↓ await resolve_tools_async(allowed_tools, org_id)
    ↓ tool_registry.get("excel_reader", org_id=org_id)
      ↓ ExcelReaderTool  (ya en memoria por import en __init__.py)
    ↓ ExcelReaderTool(org_id=org_id)  → instancia con org_id
  ↓ Agent(tools=[excel_reader_instance, ...])
  ↓ crew.kickoff_async(inputs={})
    ↓ LLM decide llamar tool
      ↓ excel_reader._run(filename="precios_bebidas.xlsx")
        ↓ lectura disco PROJECT-Aybar/
      ↓ resultado JSON → contexto LLM
    ↓ LLM genera respuesta final
```

### Contratos
- **Entrada a Factory:** `config["allowed_tools"]` es `list[str]`.
- **Salida de Factory:** `list` de instancias de `BaseTool` (CrewAI).
- **Contrato de ExcelReaderTool:** input `filename` (str), output JSON string.
- **Error handling:** Si tool no existe en registry → warning log + skipped. Si `excel_reader` no está registrado → Agent se crea sin esa tool (silencioso).

### Problemas de Auth/Authz
- `ExcelReaderTool` no valida que `org_id` tenga permiso sobre el archivo `PROJECT-Aybar/*.xlsx`. Acceso al filesystem es global. Riesgo: cualquier org puede leer cualquier archivo si el LLM construye el path (aunque `BASE_DIR` es fijo y no usa `org_id`).

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo End-to-End
1. Usuario (o webhook) invoca `Flow.execute()` (ej. `PresupuestoFlow`).
2. `validate_input()` verifica campos mínimos.
3. `BaseCrew.run_async()` carga agente `presupuestador` con `allowed_tools: ["excel_reader"]`.
4. CrewAI + Groq reciben el task prompt con instrucción explícita de usar `excel_reader`.
5. LLM decide invocar `excel_reader` con `filename="precios_bebidas.xlsx"`.
6. Tool retorna JSON con precios reales.
7. LLM calcula presupuesto y devuelve JSON estructurado.
8. Flow marca estado `COMPLETED` y persiste en `tasks` + `snapshots`.

### Coherencia
- ✅ Decisiones de data (`agent_catalog.allowed_tools`) soportan el código (`resolve_tools_async`).
- ✅ Backend (`BaseCrew`) soporta la experiencia de usuario (ejecución async sin deadlock gracias a Paso 1).
- ⚠️ Gaps:
  - No hay forma de saber (desde UX o logs estructurados) si el agente realmente usó la herramienta.
  - `PresupuestoFlow` ya existe; si el plan asume que no, podría haber duplicación de esfuerzo.

### DX & Tooling (OBLIGATORIO)

```markdown
### Herramienta Propuesta: ToolCallTracer
- **Qué automatiza:** Verificación de que el agente invocó realmente una herramienta durante la ejecución, en lugar de alucinar la respuesta.
- **Tipo:** utilidad de test + decorador opcional.
- **Cómo se usa:**
  ```python
  from src.testing.tool_tracer import ToolCallTracer
  tracer = ToolCallTracer()
  wrapped = tracer.wrap(excel_reader)
  # pasar wrapped al agente o monkeypatchar en test
  assert tracer.calls["excel_reader"] >= 1
  ```
  o vía pytest: `pytest tests/e2e/test_real_tool_calling.py --trace-tools`
- **Impacto para el usuario final:** El desarrollador/dejó de revisar manualmente logs para confirmar que el agente usó datos reales. Reduce tiempo de debug en 80%.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso.
```

---

## 5️⃣ Criterios de Aceptación

- ✅ [DATA] Tabla `agent_catalog` existe con `allowed_tools text[]` y RLS activo.
- ✅ [CODE] `AgentFactory.resolve_tools_async(["excel_reader"], org_id)` retorna lista con instancia de `ExcelReaderTool`.
- ✅ [CODE] `AgentFactory.create_agent_async()` pasa `tools` resueltos al constructor `Agent(..., tools=tools)`.
- ✅ [CODE] `ExcelReaderTool._run("precios_bebidas.xlsx")` retorna JSON válido con datos del archivo.
- ✅ [BACKEND] `BaseCrew.run_async()` ejecuta sin deadlock (prerrequisito Paso 1 verificado).
- ✅ [BACKEND] `crew.kickoff_async()` no lanza excepción cuando recibe `excel_reader` en su lista de tools.
- ✅ [FULLSTACK] `test_real_tool_calling.py` pasa con LLM real (skipif cuando no hay `GROQ_API_KEY`).
- ✅ [FULLSTACK] Output del agente contiene datos reales del Excel (no precargados en el prompt).
- ✅ [DX] `ToolCallTracer` captura al menos 1 invocación a `excel_reader` durante la ejecución del test E2E.

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| LLM alucina precios sin llamar tool | Alta | Prompt no es lo suficientemente imperativo; tool description poco persuasiva para function calling. | Reforzar descripción de `ExcelReaderTool`; usar `ToolCallTracer` para detectar y fallar el test si no hay invocación. |
| Groq + CrewAI function calling incompatible | Media | CrewAI tool schema puede no mapear correctamente a Groq function calling. | Test con LLM real inmediatamente. Si falla, evaluar fallback a prompt-engineering (inyectar datos vía contexto como workaround). |
| Paso 2 (registrar agente) no completado | Media | No hay seed bundle real ni `presupuestador` en DB de producción. Step 3 tests usan mock. | Completar Paso 2 antes de deploy, o asegurar que el test E2E de Paso 3 sea la validación de facto del agente registrado. |
| ExcelReaderTool accede a filesystem global | Baja | `BASE_DIR` es fijo y no filtra por `org_id`. | Aceptable para MVP local. Roadmap: migrar a Google Sheets API o path por org. |
| PresupuestoFlow ya existe | Baja | Colisión con plan Paso 5. | Paso 5 se redefine como validación/refactor. No crear duplicado. |

---

## 7️⃣ Plan de Implementación

> **Reglas de segmentación atómica:** Una tarea = un artefacto = interfaz completa = patrón explícito = verificación inline.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|-----------------|-----------------|-------|-------------|-------------|--------------|--------------|
| 0 | **DX: ToolCallTracer** | `src/testing/tool_tracer.py` + fixture en `tests/conftest.py` | `class ToolCallTracer: def wrap(self, tool: BaseTool) -> BaseTool; property calls: dict[str, int]` | Decoradores de mock en `tests/conftest.py` | DX | Baja | 0.5h | Ninguna | `uv run pytest tests/unit/test_tool_tracer.py -v` pasa |
| 1 | Optimizar descripción ExcelReaderTool | `src/tools/excel_reader.py` | `description: str` (más explícita, indica cuándo y por qué llamar) | `src/tools/base_tool.py` (`SendMessageTool.description`) | CODE | Baja | 0.5h | Tarea 0 | `uv run ruff check src/tools/excel_reader.py` pasa; revisión manual de claridad |
| 2 | Reforzar test E2E tool calling real | `tests/e2e/test_real_tool_calling.py` | `async def test_agent_uses_excel_reader_tool()` + assert `tracer.calls["excel_reader"] >= 1` | `tests/e2e/test_real_agent_pipeline.py` (patrón de restauración de CrewAI real + mock DB) | BACKEND | Media | 1h | Tareas 0, 1 | `uv run pytest tests/e2e/test_real_tool_calling.py -v` pasa (requiere `GROQ_API_KEY`) |
| 3 | Agregar test unitario de resolución | `tests/unit/test_factory.py` | `async def test_resolve_excel_reader_tool()` verifica tipo y `org_id` | `tests/unit/test_factory.py` (`TestResolveToolsAsync`) | CODE | Baja | 0.5h | Ninguna | `uv run pytest tests/unit/test_factory.py::TestResolveToolsAsync -v` pasa |
| 4 | Validar E2E PresupuestoFlow con tool | `tests/e2e/test_presupuesto_flow.py` | `async def test_execute_with_real_llm()` ya existe; agregar tracer + assert de invocación | `tests/e2e/test_presupuesto_flow.py` existente | FULLSTACK | Media | 0.5h | Tareas 0–2 | Criterios §5 [FULLSTACK] y [DX] pasan todos |

**Tiempo total estimado:** 3 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Migrar `ExcelReaderTool` de filesystem local a Google Sheets API (sin cambiar interfaz del agente).
- Agregar telemetría estructurada de tool calls (tabla `tool_invocations` con `task_id`, `tool_name`, `args`, `duration_ms`).
- Validación estricta de `allowed_tools` contra `skill_catalog` (FK o trigger) para evitar nombres huérfanos.
- Soporte para tool calling con múltiples herramientas en paralelo (CrewAI ya lo soporta, pero no testeado con Groq).
- Unificar `proyecto-config.json` con `phase-state.md` al cerrar fase "Patch agents".

---

## 🚫 Reglas de Oro Aplicadas

- ✅ Análisis accionable y específico al paso 3 (no genérico).
- ✅ TODO verificado contra código real (16 elementos en §0).
- ✅ Discrepancias documentadas con resolución concreta (4 discrepancias).
- ✅ Etapas secuenciales respetadas: data → code → backend → fullstack+DX.
- ✅ ≥ 1 herramienta DX propuesta (`ToolCallTracer`).
- ✅ Tareas atómicas con interfaz exacta, patrón explícito y verificación inline.
- ✅ El implementador no decide diseño: cada tarea especifica firma, archivo a copiar y comando de verificación.
- ✅ Coherente con `phase-state.md` (se referencian decisiones previas sin repetirlas).

---

**Idioma:** Español 🇪🇸  
**Formato:** Markdown estándar (no unificado con otros agentes).
