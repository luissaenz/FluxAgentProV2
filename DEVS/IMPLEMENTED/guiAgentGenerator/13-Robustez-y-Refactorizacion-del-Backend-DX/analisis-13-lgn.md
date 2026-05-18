# Análisis Técnico - Paso 13: Robustez y Refactorización del Backend (DX)

**AGENTE:** lgn  
**PASO:** 13  
**Fase:** guiAgentGenerator  
**Prioridad:** Media  

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `AgentResponse.created_at` tipado | `src/api/routes/agents.py:35` | ❌ | Campo es `str | None = None` (opcional), no obligatorio |
| 2 | Endpoints tools MCP existen | `src/api/routes/tools.py` | ✅ | `GET /api/tools/available` implementado con `source` filter |
| 3 | `_fetch_mcp_tools` usa `asyncio.new_event_loop` | `src/cli/commands/tools_list.py:141-147` | ❌ | Crea nuevo event loop en cada llamada — ineficiente |
| 4 | `_fetch_mcp_tools` backend usa MCPPool singleton | `src/api/routes/tools.py:121-124` | ✅ | `MCPPool.get()` reutiliza conexión |
| 5 | Error handling templates 503 | `src/api/routes/templates.py:66-67` | ✅ | `HTTPException(503, "Database unavailable")` implementado |
| 6 | CLI `agent_run.py` usa `httpx.Client` (sync) | `src/cli/commands/agent_run.py:89` | ❌ | No usa `httpx.AsyncClient` — inconsistente con backend async |
| 7 | CLI `crew.py` usa `httpx.Client` (sync) | `src/cli/commands/crew.py:178` | ❌ | Mismo problema de inconsistencia sync/async |
| 8 | `typer.Option` con emojis | `src/cli/commands/*.py` | ⚠️ | Emojis presentes en help text, pueden romper terminals |
| 9 | Constantes de bundle en schemas | `src/services/bundle_schemas.py` | ✅ | `AgentExportItem`, `ExportBundleRequest` centralizados |
| 10 | Validación `soul_json` campos requeridos | `src/api/routes/agents.py:102` | ⚠️ | Plan menciona validar `role`, `goal`, `backstory` antes de empaquetar |

### Discrepancias encontradas

1. **`AgentResponse.created_at` no es obligatorio** (ID-015): El plan indica cambiar a obligatorio, pero actualmente es `str | None = None`. La columna `created_at` existe en `agent_catalog` (ver migración 004) pero el modelo permite None.

2. **`httpx.AsyncClient` no migrado a CLI** (ID-033, ID-039): Los comandos `agent_run.py` y `crew.py` usan `httpx.Client` (sync) en lugar de `httpx.AsyncClient`, inconsistente con el backend async.

3. **`asyncio.new_event_loop` ineficiente** (ID-003, ID-004): `tools_list.py` crea nuevo event loop en cada llamada. El backend usa `MCPPool.get()` singleton correctamente.

4. **Emojis en typer.Option** (ID-011, ID-012): Algunos comandos usan emojis en help text que pueden no renderizar bien en terminals sin Unicode.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema de base de datos relevante

| Tabla | Columnas clave | Migración | RLS |
|---|---|---|---|
| `agent_catalog` | `id UUID, org_id UUID, role TEXT, soul_json JSONB, allowed_tools TEXT[], max_iter INTEGER, created_at TIMESTAMPTZ, is_active BOOLEAN` | `004_agent_catalog.sql` | `tenant_isolation` vía `org_id` |
| `agent_templates` | `id UUID, name TEXT, category TEXT, soul_json JSONB, suggested_tools TEXT[]` | `030_agent_templates.sql` | Lectura pública, escritura system |
| `org_mcp_servers` | `id UUID, org_id UUID, name TEXT, is_active BOOLEAN` | `005_org_mcp_servers.sql` | `tenant_isolation` |

### Integridad referencial
- Los agentes referencian organización vía `org_id` (FK implícita)
- `agent_templates.soul_json` contiene estructura validada por Pydantic

### Tipos de datos problemáticos
- `created_at` en `AgentResponse` es opcional cuando la DB siempre lo genera (DEFAULT `now()`)

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/Clases a analizar

| Archivo | Función | Firma actual | Firma requerida |
|---|---|---|---|
| `src/api/routes/agents.py:28-35` | `AgentResponse` | `created_at: str \| None = None` | `created_at: str` (obligatorio) |
| `src/cli/commands/agent_run.py:89` | `httpx.Client` | `with httpx.Client(timeout=15) as client:` | `with httpx.AsyncClient(timeout=15) as client:` |
| `src/cli/commands/crew.py:178` | `httpx.Client` | `with httpx.Client(timeout=15) as client:` | `with httpx.AsyncClient(timeout=15) as client:` |
| `src/cli/commands/tools_list.py:141-147` | `asyncio.new_event_loop()` | Crea nuevo loop | Reusar loop existente |

### Patrones existentes
- Backend usa `async def` con `httpx.AsyncClient`
- CLI usa `httpx.Client` (sync) con `with` statement
- MCPPool singleton en backend: `MCPPool.get()`
- MCPPool en CLI: misma llamada async pero con nuevo loop

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints relevantes

| Ruta | Método | Archivo | Estado |
|---|---|---|---|
| `/api/tools/available` | GET | `src/api/routes/tools.py` | ✅ Implementado con filtro `?source=` |
| `/api/templates` | GET | `src/api/routes/templates.py` | ✅ 503 manejado correctamente |
| `/agents/{role}/run` | POST | `src/api/routes/agents.py` | ✅ Devuelve task_id para polling |
| `/api/bundles/export` | POST | `src/api/routes/bundles.py` | ✅ StreamingResponse ZIP |

### Error handling
- ✅ Templates: `HTTPException(503, "Database unavailable")` (líneas 67, 88)
- ✅ Tools: Graceful degradation cuando MCP falla (líneas 102-104)

### Flujos de datos
```
CLI (sync httpx) → API (async FastAPI) → Supabase
```
Inconsistencia: CLI sync vs Backend async.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo verificado
- ✅ Builder → `/api/tools/available` → tools list
- ✅ Builder → `/api/templates` → template picker
- ✅ Playground → `/agents/{role}/run` → polling → `/tasks/{id}`
- ✅ ExportDialog → `/api/bundles/export` → ZIP download

### Herramienta DX Propuesta: `fap backend diagnose`

- **Qué automatiza:** Diagnóstico de salud del backend: conectividad DB, disponibilidad de MCP servers, latencia de endpoints críticos.
- **Tipo:** CLI command
- **Cómo se usa:** `fap backend diagnose --org-id <uuid>`
- **Impacto:** Elimina verificación manual de 5 puntos de salud con un solo comando.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso.

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Campo `created_at` en AgentResponse es obligatorio (no Optional)
✅ [CODE] CLI migra a `httpx.AsyncClient` para consistencia con backend
✅ [BACKEND] Endpoints manejan HTTP 503 correctamente (templates ya lo hace)
✅ [FULLSTACK] `fap backend diagnose` ejecuta sin errores y reporta estado
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Ruptura de tipos en frontend | Media | Cambiar `created_at` a obligatorio rompe compatibilidad | Versionar API o usar default value |
| AsyncClient en CLI puede romper conexión pooling | Baja | Cambio de sync a async en httpx | Test E2E de todos los comandos CLI |
| `asyncio.new_event_loop` en tools_list | Media | Performance degradada con múltiples llamadas | Usar `asyncio.get_event_loop()` singleton |
| Emojis en terminals legacy | Baja | Algunos servidores no soportan Unicode | Sanitizar help text, usar texto plano |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | DX Tooling: `fap backend diagnose` | `src/cli/commands/backend_diagnose.py` | `def diagnose(org_id: str, json_output: bool = False) -> None` | `src/cli/commands/doctor_builder.py` | DX | Media | 1h | Ninguna | → verificar: `fap backend diagnose --org-id <uuid>` sin errores |
| 1 | Strict Typing: AgentResponse.created_at | `src/api/routes/agents.py:35` | `created_at: str` (quitar `| None = None`) | `AgentResponse` | CODE | Baja | 0.25h | Tarea 0 (test de compatibilidad) | → verificar: `uv run pytest tests/unit/test_agents.py` pasa |
| 2 | Async Migration: agent_run.py | `src/cli/commands/agent_run.py` | Cambiar `httpx.Client` → `httpx.AsyncClient`, usar `async with` | `src/api/main.py` async handlers | CODE | Media | 1h | Tarea 1 | → verificar: `fap agent run --role test --message hi` funciona |
| 3 | Async Migration: crew.py | `src/cli/commands/crew.py` | Cambiar `httpx.Client` → `httpx.AsyncClient` | `agent_run.py` patrón | CODE | Media | 1h | Tarea 2 | → verificar: `fap crew save --name test` funciona |
| 4 | Performance: tools_list.py event loop | `src/cli/commands/tools_list.py:141-147` | Reusar loop existente con `asyncio.get_running_loop()` o manejar singleton | Backend `MCPPool.get()` singleton | CODE | Media | 0.5h | Tarea 3 | → verificar: `fap tools list` sin warning de loop |
| 5 | Error Handling: doc alignment | `src/api/routes/tools.py` | Asegurar `HTTPException(503)` para DB fallos en todos endpoints | `templates.py` patrón | BACKEND | Baja | 0.25h | Tarea 4 | → verificar: `uv run pytest tests/unit/test_tools.py` pasa |
| 6 | CLI Polish: emojis en typer.Option | `src/cli/commands/*.py` | Eliminar emojis de help text | `templates_seed.py` (sin emojis) | CODE | Baja | 0.5h | Tarea 5 | → verificar: `tsc --noEmit` sin errores |
| 7 | Code Sync: constantes bundle | `src/services/bundle_schemas.py` | Importar constantes de validación desde aquí | Ya centralizado | CODE | Baja | 0.25h | Tarea 6 | → verificar: `fap bundle validate-payload` usa constantes |

**Tiempo total estimado:** 5.5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Cache de tools MCP con TTL para reducir llamadas repetidas
- Métricas de performance en `fap backend diagnose` (latencia percentiles)
- Migración completa de CLI a Typer native async support cuando esté disponible