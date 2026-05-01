# Análisis Técnico — Paso 1: Mejora de la Infraestructura de Herramientas

**Agente:** oc  
**Fecha:** 2026-04-30  
**Plan:** `DEVS/plan.md` — Paso 1  
**Fase:** details4agents  

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `BaseCrew` clase existe | `src/crews/base_crew.py:27` | ✅ | Clase `BaseCrew` línea 27 |
| 2 | `BaseCrew._resolve_tools()` existe | `src/crews/base_crew.py:78` | ✅ | Método definido línea 78, firma `(self, allowed_tools: List[str]) -> list` |
| 3 | `_resolve_tools()` es llamado desde `run()` o `run_async()` | — | ❌ **DISCREPANCIA** | `run()` (L113) llama `AgentFactory.create_agent()`, NO `_resolve_tools`. El método es dead code. Sólo referenciado en tests (`test_base_crew.py:143-192`) |
| 4 | `AgentFactory` clase existe | `src/crews/factory.py:14` | ✅ | Clase `AgentFactory` línea 14 |
| 5 | `AgentFactory.create_agent()` existe | `src/crews/factory.py:18` | ✅ | Método `create_agent(config, org_id)` línea 18 |
| 6 | `create_agent()` resuelve tools como instancias | `src/crews/factory.py:30-39` | ✅ | Ya crea `tool_cls(org_id=self.org_id)` (instancias, no clases) |
| 7 | `MCPPool` clase existe | `src/tools/mcp_pool.py:35` | ✅ | Clase `MCPPool` con patrón singleton línea 42 |
| 8 | `MCPPool.get_tools()` firma | `src/tools/mcp_pool.py:77` | ✅ | `async get_tools(org_id, server_name, timeout=30, max_retries=3) -> list` |
| 9 | `MCPPool.get_tools()` es async | línea 77 | ⚠️ | `_resolve_tools` es sync → mismatch de sync/async |
| 10 | `MCPPool` importable desde `src.tools.mcp_pool` | — | ✅ | Ruta de import: `from src.tools.mcp_pool import MCPPool` |
| 11 | `crewai-tools` es dependencia directa | `pyproject.toml:43` | ⚠️ | `crewai-tools>=0.20.0` es **opcional** (extras `crew`), no directa |
| 12 | Tabla `agent_catalog` tiene columna `allowed_tools` | `supabase/migrations/004_agent_catalog.sql:12` | ✅ | `allowed_tools TEXT[] DEFAULT '{}'` |
| 13 | Tabla `org_mcp_servers` existe | `supabase/migrations/005_org_mcp_servers.sql:9` | ✅ | Columnas: id, org_id, name, command, args, secret_name, is_active |
| 14 | `ServiceConnectorTool` registrada en `tool_registry` | `src/tools/service_connector.py:37` | ✅ | `@register_tool("service_connector")` línea 37 |
| 15 | Tool resolution duplicada | `factory.py:31-39` vs `base_crew.py:79-87` | ❌ **DISCREPANCIA** | Misma lógica duplicada en 2 lugares. Plan sólo menciona modificar `_resolve_tools` (dead code) |
| 16 | `tool_registry.get()` acepta `mcp:` prefijo | `src/tools/registry.py:75` | ❌ | No hay manejo para prefijo `mcp:`. Llamaría a `_load_from_db` o filesystem fallback |
| 17 | Tests unitarios para `_resolve_tools` existen | `tests/unit/test_base_crew.py:142-192` | ✅ | Clase `TestToolResolution` con 3 tests |
| 18 | `test_base_crew.py` usa `sample_org_id` fixture | `tests/unit/test_base_crew.py:27` | ✅ | Fixture definida en conftest (import implícito) |
| 19 | Convención `mcp:{server}:{tool}` documentada en system prompt | `src/flows/architect_flow.py:217-265` | ❌ | No hay mención de `mcp:` convención en prompt actual. Plan la agrega en Paso 2 |
| 20 | `BaseCrew.run()` usa `Process.sequential` | `src/crews/base_crew.py:124` | ✅ | Proceso secuencial línea 124 |
| 21 | `BaseCrew` usa `allow_delegation=False` | `src/crews/factory.py:46` | ✅ | Regla R2 |
| 22 | `BaseCrew` usa `max_iter` desde config | `src/crews/factory.py:49` | ✅ | `max_iter=config.get("max_iter", 5)` — Regla R8 |

### Discrepancias encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | Plan asume `_resolve_tools` es el punto de resolución. Realidad: es **dead code** — `run()` nunca lo llama | Modificar `factory.py:create_agent()` en su lugar, o inyectar `_resolve_tools` en el flujo `run()` |
| D2 | Lógica de resolución de tools **duplicada** idénticamente en `base_crew.py:78-88` y `factory.py:30-39` | Refactorizar: eliminar duplicación, unificar en un solo método (ej: mover a `factory.py` y que `base_crew._resolve_tools` delegue) |
| D3 | `_resolve_tools` es sync; `MCPPool.get_tools()` es async | Necesario bifurcar en sync path (no-MCP) vs async path (MCP) o crear wrapper sync para MCPPool |
| D4 | `crewai-tools` es dependencia **opcional** pero `MCPServerAdapter` se importa dentro de `MCPPool.get_tools()` | Si no está instalado, cualquier tool MCP falla con `ImportError`. Considerar try/except o mover a dependencia directa |
| D5 | No existe manejo de `mcp:` prefijo en `tool_registry.get()` ni en ninguna parte del código | El plan asume que `mcp:server:tool` es un formato válido en `allowed_tools`, pero no hay parsing implementado |

---

## 1️⃣ Análisis de Datos

### Tablas Afectadas
| Tabla | Migración | Uso | Cambio Requerido |
|---|---|---|---|
| `agent_catalog` | `004_agent_catalog.sql` | Almacena `allowed_tools TEXT[]` — los nombres de tool pueden incluir `mcp:` prefijo | **Ninguno** — `TEXT[]` acepta cualquier string, incluyendo `mcp:server:tool` |
| `org_mcp_servers` | `005_org_mcp_servers.sql` | Configura servidores MCP por org | **Ninguno** — ya existe con schema correcto |

### Schema actual vs requerido
- `agent_catalog.allowed_tools` → tipo `TEXT[]` → compatible con formato `mcp:{server}:{tool}`
- `org_mcp_servers` → tipo `command TEXT, args JSONB` → compatible con `StdioServerParameters`

### Integridad referencial
- `agent_catalog.org_id` → FK a `organizations(id)` ✅
- `org_mcp_servers.org_id` → FK a `organizations(id)` ✅

### RLS
- `agent_catalog`: POLICY `tenant_isolation` via `app.org_id` ✅
- `org_mcp_servers`: POLICY `tenant_isolation_org_mcp_servers` via `current_org_id()` ✅

### Conclusión de Datos
No requiere cambios de schema. `allowed_tools TEXT[]` ya soporta el formato `mcp:server:tool` como string. El `org_mcp_servers` ya tiene command/args/secret_name para conexión MCP. RLS existente aísla correctamente por tenant.

---

## 2️⃣ Análisis de Código

### Archivos objetivo

**1. `src/crews/base_crew.py` (215 líneas)**
- Clase `BaseCrew`
- Métodos públicos: `run()`, `run_async()`, `get_last_tokens_used()`, `kickoff_async()`
- Métodos privados: `_load_agent_config()`, `_resolve_tools()`, `_extract_token_usage()`
- Patrón: instancia `AgentFactory.create_agent()`, crea Crew/Task, ejecuta `kickoff()`
- 🔴 `_resolve_tools()` (L78-88) es código muerto — nunca invocado desde `run()` o `run_async()`
- `run()` (L90-133): sync, llama `AgentFactory.create_agent()` directamente
- `run_async()` (L172-208): async, llama `AgentFactory.create_agent()` directamente
- **Problema**: plan pide modificar `_resolve_tools`, pero el cambio real debe ir en `factory.py` O en el flujo de llamada de `run()`

**2. `src/crews/factory.py` (59 líneas)**
- Clase `AgentFactory` con 2 métodos estáticos
- `create_agent()` (L18-50): resuelve tools desde `allowed_tools` vía `tool_registry.get()`, crea instancias `tool_cls(org_id=self.org_id)`, pasa `tools=tools` a `Agent()`
- `create_task()` (L53-59): simple wrapper
- **Ya soporta herramientas instanciadas** — el plan asume que no, pero `tools.append(tool_cls(org_id=self.org_id))` ya son instancias
- Importa: `from src.tools.registry import tool_registry`

**3. `src/tools/mcp_pool.py` (213 líneas)**
- Clase `MCPPool` — singleton, conexiones persistentes
- `get_tools(org_id, server_name)` → async, retorna lista de tool objects de CrewAI
- Circuit breaker: 5 fallos → 60s de espera
- Auto-reconnect con tenacity (exponential backoff)
- Importa `MCPServerAdapter` de `crewai_tools` dentro del método (lazy import)

### Patrón de resolución actual
```
allowed_tools: ["fetch_url", "db_read"]
  → tool_registry.get("fetch_url", org_id=org_id)
  → devuelve clase → instancia con org_id
```

### Patrón requerido
```
allowed_tools: ["fetch_url", "mcp:file_server:list_files"]
  → detectar prefijo "mcp:"
  → parsear "mcp:{server}:{tool}"
  → MCPPool.get_tools(org_id, "file_server")
  → filtrar tool específica del listado
```

### Duplicación crítica
`base_crew.py:79-87` y `factory.py:31-39` tienen IDENTICA lógica de resolución:
```python
for tool_name in allowed_tools:
    try:
        tool_cls = tool_registry.get(tool_name, org_id=org_id)
        tools.append(tool_cls(org_id=org_id))
    except ValueError:
        logger.warning(...)
```

Refactor necesario: unificar en un solo método (ej: en `factory.py` como `resolve_tools()`) y delegar desde `base_crew`.

### Imports
- `base_crew.py` ya importa `from src.tools.registry import tool_registry`
- `factory.py` ya importa `from src.tools.registry import tool_registry`
- Para MCPPool: `from src.tools.mcp_pool import MCPPool`
- `MCPServerAdapter`: import lazy dentro de `MCPPool.get_tools()` — opcional

---

## 3️⃣ Análisis de Backend

### Endpoints existentes (no se modifican en este paso)
| Ruta | Archivo | Método | Propósito |
|---|---|---|---|
| `POST /api/webhooks/{org_id}/{flow_type}` | `routes/webhooks.py` | POST | Ejecuta flow dinámico vía DynamicWorkflow |
| `GET /api/agents` | `routes/agents.py` | GET | Lista agentes del catálogo |

### Middleware
- `src/api/middleware.py`: JWT validation + org_id injection
- No requiere cambios — auth ya está desacoplada

### Flujo de resolución de tools (post-cambio)
```
AgentFactory.create_agent()
  ↓
allowed_tools: ["mcp:file_server:list_files", "db_read"]
  ↓ ¿prefijo "mcp:"?
  ├── Sí → MCPPool.get().get_tools(org_id, server_name="file_server")
  │         → MCPServerAdapter conecta vía StdioServerParameters
  │         → retorna lista tools → filtrar "list_files"
  │         → agregar tool instanciada
  └── No → tool_registry.get(name) → instanciar
```

### Problema sync/async
- `MCPPool.get_tools()` es async (usa `asyncio`, `run_in_executor`)
- `AgentFactory.create_agent()` es sync
- Opciones:
  - A. Hacer `create_agent()` async → requeriría refactor de `run()` y `run_async()`
  - B. Sincronizar MCPPool con `asyncio.run()` → peligroso si event loop ya corre
  - C. **Recomendado**: resolver MCP tools SOLO en path async (`run_async`), dejar tools regulares en path sync (`run`)

### Contrato de MCPPool.get_tools()
```
Input:  org_id (str), server_name (str), timeout (int=30), max_retries (int=3)
Output: list[Tool]  — objetos tool de CrewAI listos para usar
Errors: MCPConnectionError (circuit breaker abierto, timeout, conexión fallida)
```

---

## 4️⃣ Análisis de Fullstack + DX

### Flujo End-to-End (post-implementación)
```
1. User crea agente vía POST /api/agents con allowed_tools=["mcp:file_server:list_files"]
2. Agente se guarda en agent_catalog con allowed_tools como TEXT[] 
3. Flow ejecuta BaseCrew.run_async() para ese agente
4. create_agent() detecta "mcp:" → llama MCPPool.get_tools()
5. MCPPool conecta vía StdioServerParameters (command+args desde org_mcp_servers)
6. MCPServerAdapter devuelve tools → se inyectan en CrewAI Agent
7. Agent ejecuta tool MCP como cualquier otra herramienta
```

### Coherencia
- ✅ `allowed_tools TEXT[]` ya soporta strings arbitrarios
- ✅ `org_mcp_servers` ya tiene schema para conexión
- ✅ `MCPPool` singleton ya implementa circuit breaker + reconexión
- ✅ `crewai-tools` (dependencia opcional) provee `MCPServerAdapter` necesario

### Gaps
| Gap | Descripción |
|---|---|
| G1 | No hay test unitario para resolución de tools MCP |
| G2 | No hay integración test entre `MCPPool` y `AgentFactory` |
| G3 | `_resolve_tools` en `base_crew.py` es dead code y confunde |
| G4 | `allowed_tools` no tiene validación de formato `mcp:server:tool` en frontend ni backend |
| G5 | No hay mecanismo para filtrar tools específicas del listado devuelto por MCPPool |
| G6 | `factory.py` no tiene test — `test_base_crew.py` testea `_resolve_tools` (dead code) pero no `create_agent` |

### DX & Tooling

```
### Herramienta Propuesta: fap validate-tools
- **Qué automatiza:** Validación de `allowed_tools` en manifests/agent configs.
  Detecta tools inválidas, `mcp:` prefijos rotos, servidores MCP inexistentes.
- **Tipo:** CLI comando
- **Cómo se usa:** `fap validate-tools --bundle ./my-bundle/manifest.json`
  o `fap validate-tools --agent-role analyst --org-id org_123`
- **Impacto para usuario final:** Evita errores en runtime — detecta tools mal
  escritas o servidores MCP caídos antes de ejecutar el agente.
- **Prioridad:** Tarea 0 — implementar antes del resto
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] `AgentFactory.create_agent()` detecta prefijo `mcp:` en allowed_tools
✅ [CODE] Tools con `mcp:server:tool` se resuelven vía `MCPPool.get_tools()`
✅ [CODE] Tools sin prefijo `mcp:` siguen resolviéndose vía `tool_registry` (backwards compat)
✅ [CODE] Tool instances se pasan correctamente a `Agent()` de CrewAI
✅ [CODE] Lógica de resolución de tools unificada (no duplicada)
✅ [CODE] `_resolve_tools` en `base_crew.py` delegada o reemplazada por factory
✅ [DATA] `allowed_tools TEXT[]` acepta `mcp:server:tool` sin cambios de schema
✅ [BACKEND] MCPPool conecta exitosamente a servidor MCP configurado en `org_mcp_servers`
✅ [FULLSTACK] Agente con `mcp:file_server:list_files` ejecuta tool MCP en runtime
✅ [FULLSTACK] Si `crewai-tools` no está instalado, falla graceful con mensaje claro
✅ [FULLSTACK] Si servidor MCP no existe, falla con `MCPConnectionError` manejado
✅ [DX] `fap validate-tools` identifica tools inválidas y `mcp:` prefijos rotos
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `_resolve_tools` dead code no detectado y se modifica sin efecto | **Alta** | Plan asume línea de código equivocada | Verificar que `factory.py:create_agent()` es el target real. Refactor para que `_resolve_tools` delegue a factory |
| sync/async mismatch en resolución MCP | **Alta** | `MCPPool.get_tools()` es async, `create_agent()` es sync | Resolver MCP tools solo en `run_async()` o crear wrapper sync con `asyncio.run()` en thread separado |
| `crewai-tools` no instalado → ImportError en runtime | **Media** | Dependencia opcional (extras `crew`) | Capturar `ImportError` en resolución MCP con mensaje claro: "Instalar con: pip install fluxagentpro-v2[crew]" |
| Filtrado de tool específica del listado MCP | **Media** | `MCPPool.get_tools()` devuelve todas las tools del servidor | Parsear `mcp:server:tool_name` y filtrar por nombre. Si no se encuentra, log advertencia |
| Duplicación de lógica -> mantenibilidad futura | **Media** | 2 copias idénticas de resolución de tools | Refactorizar en este paso — mover resolución a `factory.py` y delegar |
| Circuit breaker MCP abierto → bloquea herramientas | **Baja** | 5 fallos consecutivos → 60s de espera | Documentar comportamiento. Usar `MCPPool.reset()` en tests |
| Tests existentes testean dead code | **Baja** | `test_base_crew.py` testea `_resolve_tools` que no se usa | Actualizar tests para testear `AgentFactory.create_agent()` o `run()` real |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX Tooling**: Implementar `fap validate-tools` CLI | DX/FULLSTACK | Baja | 1h | Ninguna |
| 1 | Refactor: unificar resolución de tools en `factory.py` + delegar desde `base_crew._resolve_tools` | CODE | Baja | 0.5h | Tarea 0 (para validación) |
| 2 | Implementar detección de prefijo `mcp:` en `factory.py:create_agent()` | CODE/BACKEND | Media | 1.5h | Tarea 1 |
| 3 | Integrar `MCPPool.get_tools()` en resolución MCP | CODE/BACKEND | Alta | 2h | Tarea 2 |
| 4 | Manejar sync/async: bifurcar resolución MCP solo en `run_async()` | CODE/BACKEND | Alta | 1.5h | Tarea 3 |
| 5 | Actualizar tests unitarios (`test_base_crew.py`) y agregar test para `factory.py:create_agent()` | CODE | Media | 1.5h | Tareas 1-4 |
| 6 | Validar flujo end-to-end: agente con tool MCP ejecuta correctamente | FULLSTACK | Alta | 2h | Tareas 1-5 |

**Tiempo total estimado:** 10 horas

### Orden de Tareas
```
Tarea 0 (DX) ─> Tarea 1 (Refactor) ─> Tarea 2 (mcp: detección) ─> Tarea 3 (MCPPool)
     └──> Tarea 4 (sync/async) ─> Tarea 5 (tests) ─> Tarea 6 (E2E)
```

---

## 🔮 Roadmap

### Mejoras futuras
- Validación de schema `mcp:server:tool` en frontend al crear/editar agentes
- Auto-completado de servidores MCP disponibles por org en UI
- Health check periódico de conexiones MCP vía `MCPPool`
- Dashboard de tools MCP activas por organización

### Decisiones de diseño para preservar
- `tool_registry` sigue siendo el path default para tools no-MCP
- `MCPPool` singleton con circuit breaker — no reemplazar
- `AgentFactory.create_agent()` como punto único de creación de agentes
- `Process.sequential` se mantiene (Rule R1)
