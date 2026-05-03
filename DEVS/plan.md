# Plan: Agentes Reales Productivos

> **Objetivo:** Llevar agentes de presupuesto desde tests offline hasta producción (registrados, ejecutables via API/CLI, con tool calling real y flows formales).
> **Origen:** Sesión de pruebas con datos reales Aybar (11 sheets, Groq LLM, tests multi-agente).
> **Estado:** ⏳ PENDIENTE

---

## Dependencias Entre Pasos

```
Paso 1 (fix deadlock MCP) ──┐
                             ├──→ Paso 4 (Flow.execute real) ──→ Paso 5 (flow registrado)
Paso 2 (registrar agente) ──┘
           │
Paso 3 (tool calling) ──────┘

Paso 6 (ExcelWriter) ──→ standalone, paralelo a todo
```

---

## Paso 1: Fix Deadlock en MCP Resolution Async

**Archivo:** `src/crews/factory.py`
**Estimación:** 1h
**Bloqueante para:** Paso 4, 5

### Problema
`_resolve_mcp_tool()` usa `asyncio.run_coroutine_threadsafe(coro, loop).result()` que deadlockea cuando se ejecuta desde el mismo event loop (contexto async).

### Solución
Agregar `resolve_tools_async()` y `_resolve_mcp_tool_async()` que usen `await` en vez de `run_coroutine_threadsafe`. `create_agent_async()` pasa a ser async y usa la variante async.

### Cambios
| Archivo | Cambio |
|---------|--------|
| `src/crews/factory.py` | Agregar `resolve_tools_async()` y `_resolve_mcp_tool_async()`. `create_agent_async()` → `async def` y llama `await resolve_tools_async()` |
| `src/crews/base_crew.py` | `run_async()` ya tiene `await AgentFactory.create_agent_async()` — sin cambios |

### Tests
- `tests/unit/test_factory.py`: agregar test para `resolve_tools_async` con MCP mock
- `tests/e2e/test_exec_agent_mcp.py`: remover parche `_resolve_mcp_tool` → test usa resolución async real

### Criterios
- [ ] Flow async con MCP tools completa sin deadlock
- [ ] Flow sync con MCP tools skipea (comportamiento actual)
- [ ] Tests existentes de factory pasan sin modificación

---

## Paso 2: Registrar Agente Presupuestador en el Sistema

**Archivos:** `data/seed/` (nuevo bundle), API
**Estimación:** 2h
**Bloqueante para:** Paso 4, 5

### Qué hacer
1. Crear bundle ZIP con agente `presupuestador` + `excel_reader` tool
2. Crear definición de agente en `agents/presupuestador.json` con `soul_json`, `allowed_tools: ["excel_reader"]`
3. Importar bundle via API `POST /api/bundles/import`
4. Verificar agente visible en `agent_catalog`

### Bundle structure
```
presupuesto-bundle/
├── manifest.json
├── agents/
│   └── presupuestador.json   # role, goal, backstory, allowed_tools
└── skills/
    └── excel_reader.py        # opcional — el tool ya está registrado en sistema
```

### Tests
- Test E2E: bundle import → HTTP 201 → agente en agent_catalog
- Test E2E: consultar agente via API → datos correctos

---

## Paso 3: Tool Calling Real (Agente usa herramienta durante ejecución)

**Archivo:** `src/crews/factory.py` (opcional), tests
**Estimación:** 3h
**Bloqueante para:** Paso 4, 5

### Qué hacer
Hoy los tests pasan datos precargados al prompt. El agente no llama `excel_reader` activamente — recibe los datos como contexto.

Para tool calling real:
1. El agente tiene `allowed_tools: ["excel_reader"]` en su config
2. `AgentFactory.create_agent_async()` resuelve el tool → `ExcelReaderTool(org_id=xxx)`
3. CrewAI Agent recibe el tool en su lista
4. Durante `crew.kickoff_async()`, el LLM decide llamar `excel_reader` según necesidad
5. El resultado del tool se inyecta en el contexto del LLM

### Desafío
CrewAI tool calling requiere que el LLM soporte function calling. Groq con llama-3.3-70b lo soporta. Pero el formato de tool description debe ser claro para que el LLM decida usarlo.

### Tests
- Test con LLM real: agente con `excel_reader` tool que DEBE llamarlo para responder
- Verificar que la respuesta incluye datos de la sheet (no precargados)

---

## Paso 4: Flow.execute() con LLM Real

**Archivo:** Tests E2E
**Estimación:** 2h
**Depende de:** Paso 1 + Paso 2 + Paso 3

### Qué hacer
Ejecutar pipeline completo: `Flow.execute()` → `BaseFlow._run_crew()` → `BaseCrew.run_async()` → LLM real → output.

Similar a `test_real_agent_pipeline.py` pero pasando por `BaseFlow.execute()` que agrega:
- `create_task_record()` → persistencia en DB
- State transitions → PENDING → RUNNING → COMPLETED
- Event emission → flow.created, flow.completed
- `persist_state()` → snapshots + tasks update

### Tests
- Flow.execute() con LLM real + tool excel_reader
- Verificar state transitions + event emission + output

---

## Paso 5: Flow de Presupuesto Registrado Formalmente

**Archivo:** `src/flows/presupuesto_flow.py`
**Estimación:** 2h
**Depende de:** Paso 4

### Qué hacer
1. Crear `PresupuestoFlow(BaseFlow)` con `@register_flow("presupuesto")`
2. `validate_input()` verifica: tipo_evento, pax, fecha, provincia
3. `_run_crew()` ejecuta agente `presupuestador` con datos del input
4. Output: quote estructurada en JSON

### Tests
- Flow registrado en `flow_registry`
- POST `/api/webhooks/trigger` con flow_type="presupuesto"
- GET `/api/tasks/{task_id}` → status COMPLETED + output
- Test multi-turn: ejecutar flow, verificar output en DB

---

## Paso 6: ExcelWriterTool (Escribir Presupuesto a .xlsx)

**Archivo:** `src/tools/excel_writer.py`
**Estimación:** 2h
**Paralelo a:** todo lo demás

### Qué hacer
1. Crear `ExcelWriterTool(OrgBaseTool)` con `@register_tool("excel_writer")`
2. Input: filename, sheet_name, data (JSON array)
3. Output: escribe .xlsx en PROJECT-Aybar/
4. Integración futura: reemplazar por Google Sheets API

### Tests
- Unit: escribir + leer roundtrip
- Unit: append vs overwrite
- Unit: validación de datos (estructura JSON consistente)

---

## Resumen de Estimación

| Paso | Tiempo | Depende de |
|------|--------|------------|
| 1 — Fix deadlock MCP | 1h | — |
| 2 — Registrar agente | 2h | — |
| 3 — Tool calling real | 3h | 1, 2 |
| 4 — Flow.execute real | 2h | 1, 2, 3 |
| 5 — Flow registrado | 2h | 4 |
| 6 — ExcelWriter | 2h | — |
| **Total** | **~12h** | |
