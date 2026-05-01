# Análisis Final — Paso 1: Mejora de la Infraestructura de Herramientas

**Fecha:** 2026-04-30  
**Fase:** details4agents  
**Plan:** `DEVS/plan.md` — Paso 1  
**Unificado por:** Unificador (desde análisis de agente: oc)

---

## 0️⃣ Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| oc | ✅ (22 elementos) | 5 (D1-D5) | ✅ (`fap validate-tools`) | ✅ (archivos + líneas) | 4.2 |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| D1 | Plan asume `_resolve_tools` es el punto de resolución. Realidad: es **dead code** — `run()` nunca lo llama. La resolución real ocurre en `factory.py:create_agent()` | oc | ✅ `base_crew.py:113` llama `AgentFactory.create_agent()`, no `_resolve_tools` | Se implementa en `factory.py:create_agent()`. `_resolve_tools` se delega a factory o se elimina |
| D2 | Lógica de resolución de tools **duplicada** en `base_crew.py:78-88` y `factory.py:30-39` | oc | ✅ código idéntico en ambos archivos | Unificar en `factory.py` como método `resolve_tools()`. `base_crew._resolve_tools` delega a factory |
| D3 | `_resolve_tools` es sync; `MCPPool.get_tools()` es async | oc | ✅ `base_crew.py:78` sync vs `mcp_pool.py:77` async | Resolver MCP tools solo en path async (`run_async`). Path sync (`run`) solo resuelve tools regulares |
| D4 | `crewai-tools` es dependencia **opcional** pero `MCPServerAdapter` se importa dentro de `MCPPool.get_tools()` | oc | ✅ `pyproject.toml:43` — extras `crew` | Capturar `ImportError` en resolución MCP con mensaje claro. No mover a dependencia directa |
| D5 | No existe manejo de prefijo `mcp:` en `tool_registry.get()` ni en ninguna parte del código | oc | ✅ `registry.py:75` — sin parsing de prefijo | Implementar detección y parsing de `mcp:server:tool` en `factory.py:create_agent()` |

---

## 1️⃣ Resumen Ejecutivo

**Objetivo del paso:** Mejorar la infraestructura de herramientas para que `BaseCrew` y `AgentFactory` puedan resolver herramientas MCP (prefijo `mcp:server:tool`) además de las herramientas regulares del `tool_registry`. Esto permite que agentes generados por el Architect utilicen servidores MCP configurados en `org_mcp_servers`.

**Correcciones críticas al plan:**
1. El plan indica modificar `BaseCrew._resolve_tools` en `base_crew.py`. Este método es **dead code** — nunca se invoca desde `run()` ni `run_async()`. La resolución real ocurre en `AgentFactory.create_agent()` en `factory.py`.
2. El plan asume que `create_agent()` no soporta herramientas instanciadas. Realidad: ya crea instancias con `tool_cls(org_id=self.org_id)`.
3. Lógica de resolución duplicada entre `base_crew.py` y `factory.py` — requiere refactor antes de agregar MCP.

**Decisión DX:** Herramienta `fap validate-tools` — CLI que valida `allowed_tools` en bundles y configs de agentes, detectando tools inválidas, prefijos `mcp:` rotos y servidores MCP inexistentes antes de runtime.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Agente se crea/configura con `allowed_tools=["db_read", "mcp:file_server:list_files"]`
2. Agente se persiste en `agent_catalog` (columna `allowed_tools TEXT[]`)
3. Flow ejecuta `BaseCrew.run_async()` para ese agente
4. `AgentFactory.create_agent()` recibe config con `allowed_tools`
5. Para cada tool en `allowed_tools`:
   - Si tiene prefijo `mcp:` → parsear `server` y `tool_name` → llamar `MCPPool.get().get_tools(org_id, server)`
   - Si no tiene prefijo → `tool_registry.get(name)` → instanciar
6. Tools MCP se conectan vía `MCPServerAdapter` (command+args desde `org_mcp_servers`)
7. Todas las tools instanciadas se pasan a `Agent(tools=tools)` de CrewAI
8. Agente ejecuta normalmente — tools MCP funcionan igual que tools regulares

### Edge Cases MVP

| Caso | Comportamiento esperado |
|---|---|
| `mcp:` sin formato válido (ej: `mcp:server`) | Log warning, omitir tool, continuar |
| Servidor MCP no configurado en `org_mcp_servers` | `MCPConnectionError` con mensaje claro |
| `crewai-tools` no instalado | `ImportError` capturado → mensaje: "Instalar `pip install fluxagentpro-v2[crew]`" |
| Circuit breaker MCP abierto | `MCPConnectionError` con tiempo restante |
| Tool MCP no encontrada en listado del servidor | Log warning, omitir esa tool |
| `allowed_tools` vacío | Agente sin tools — válido |
| Path sync (`run()`) con tool MCP | Omitir MCP tools, resolver solo regulares (MCP requiere async) |

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### Archivo 1: `src/crews/factory.py`
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\src\crews\factory.py`
- **Tipo de cambio:** Modificación + Refactor
- **Descripción:** Centralizar toda la resolución de tools aquí. Agregar detección de prefijo `mcp:`, parsing, e integración con `MCPPool`. Eliminar duplicación.
- **Interfaces clave:**
  - `resolve_tools(allowed_tools: list[str], org_id: str) -> list` — nuevo método estático que reemplaza la lógica inline actual
  - `create_agent(config: dict, org_id: str) -> Agent` — modificado para usar `resolve_tools()`
- **Patrones a seguir:** Lazy import de `MCPPool` (como se hace con `MCPServerAdapter` en `mcp_pool.py:149`). Try/except para `ImportError`.

#### Archivo 2: `src/crews/base_crew.py`
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\src\crews\base_crew.py`
- **Tipo de cambio:** Modificación (delegación)
- **Descripción:** `_resolve_tools()` delega a `AgentFactory.resolve_tools()` en lugar de duplicar lógica. `run_async()` puede resolver MCP tools; `run()` solo tools regulares.
- **Interfaces clave:**
  - `_resolve_tools(allowed_tools: List[str]) -> list` — ahora delega a `AgentFactory.resolve_tools()`
- **Patrones a seguir:** Delegación a factory (como ya hace `run()` con `AgentFactory.create_agent()`).

#### Archivo 3: `src/cli/validate_tools.py` (nuevo)
- **Ruta real:** `D:\Develop\Personal\FluxAgentPro-v2\src\cli\validate_tools.py`
- **Tipo de cambio:** Creación
- **Descripción:** Comando CLI `fap validate-tools` que valida `allowed_tools` contra `tool_registry` y `org_mcp_servers`.
- **Interfaces clave:**
  - `validate_tools_command(bundle_path: str | None, agent_role: str | None, org_id: str | None)` — entry point Typer
- **Patrones a seguir:** Comandos CLI existentes en `src/cli/` (typer, `app.command()`).

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: fap validate-tools
- **Qué automatiza:** Validación de `allowed_tools` en manifests/agent configs.
  Detecta tools inválidas, prefijos `mcp:` rotos, servidores MCP inexistentes.
  Evita errores en runtime al verificar tools antes de ejecutar el agente.
- **Tipo:** CLI comando (Typer)
- **Ubicación:** D:\Develop\Personal\FluxAgentPro-v2\src\cli\validate_tools.py
- **Cómo se usa:**
  - `fap validate-tools --bundle ./my-bundle/manifest.json`
  - `fap validate-tools --agent-role analyst --org-id org_123`
  - `fap validate-tools --tool "mcp:file_server:list_files" --org-id org_123`
- **Impacto para el usuario final:** Detecta tools mal escritas o servidores MCP
  caídos antes de ejecutar el agente. Ahorra debugging en runtime.
- **El implementador DEBE usarla** para completar las tareas 1..N del paso.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **Resolución MCP en `factory.py`, no en `base_crew._resolve_tools`:** El plan indica modificar `_resolve_tools` pero es dead code. La resolución real ocurre en `AgentFactory.create_agent()` (`factory.py:30-39`). Se implementa ahí.

2. **Unificación de resolución en `factory.py`:** Eliminar duplicación entre `base_crew.py:78-88` y `factory.py:30-39`. Nuevo método `AgentFactory.resolve_tools()` como fuente única.

3. **MCP tools solo en path async:** `MCPPool.get_tools()` es async. `create_agent()` es sync. Solución: bifurcar — tools regulares se resuelven sync en ambos paths; MCP tools se resuelven solo en `run_async()`. Path sync (`run()`) omite MCP tools con warning.

4. **`crewai-tools` como dependencia opcional:** No se mueve a directa. Se captura `ImportError` con mensaje instructivo. Mantiene compatibilidad con instalaciones sin CrewAI.

5. **Parsing de `mcp:server:tool`:** Formato exacto: `mcp:{server_name}:{tool_name}`. Se split por `:` con max 2 splits. Si no tiene 3 partes, se loggea warning y se omite.

6. **Filtrado de tool específica:** `MCPPool.get_tools()` devuelve todas las tools del servidor. Se filtra por `tool_name` buscando atributo `name` en cada tool object.

7. **Backwards compatibility:** Tools sin prefijo `mcp:` siguen resolviéndose vía `tool_registry.get()` exactamente como antes.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [CODE] `AgentFactory.resolve_tools()` existe como método estático en factory.py
✅ [CODE] `AgentFactory.create_agent()` usa `resolve_tools()` (no lógica inline)
✅ [CODE] `resolve_tools()` detecta prefijo `mcp:` y parsea `server:tool_name`
✅ [CODE] Tools MCP se resuelven vía `MCPPool.get().get_tools(org_id, server)`
✅ [CODE] Tools sin `mcp:` se resuelven vía `tool_registry.get()` (backwards compat)
✅ [CODE] `_resolve_tools` en `base_crew.py` delega a `AgentFactory.resolve_tools()`
✅ [CODE] No hay duplicación de lógica de resolución entre archivos
✅ [DATA] `allowed_tools TEXT[]` acepta `mcp:server:tool` sin cambios de schema
✅ [BACKEND] MCPPool conecta a servidor MCP configurado en `org_mcp_servers`
✅ [BACKEND] Tool específica se filtra del listado MCP por nombre
✅ [FULLSTACK] Agente con `mcp:file_server:list_files` ejecuta tool MCP en `run_async()`
✅ [FULLSTACK] Si `crewai-tools` no instalado, falla graceful con mensaje claro
✅ [FULLSTACK] Si servidor MCP no existe, falla con `MCPConnectionError` manejado
✅ [FULLSTACK] Path sync (`run()`) omite MCP tools con warning
✅ [DX] `fap validate-tools` CLI ejecuta y detecta tools inválidas/prefijos rotos
```

**Funcionales:**
- [ ] Agente con tool MCP ejecuta correctamente vía `run_async()`
- [ ] Agente con tool regular funciona igual que antes (backwards compat)
- [ ] Agente con `mcp:` malformado omite tool con warning, no crashea
- [ ] `fap validate-tools` reporta tools válidas e inválidas correctamente

**Técnicos:**
- [ ] Tests unitarios pasan para `AgentFactory.resolve_tools()`
- [ ] Tests unitarios pasan para `base_crew._resolve_tools()` (delegación)
- [ ] No hay duplicación de lógica de resolución
- [ ] `ruff check src/ tests/` pasa sin errores

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** Implementar `fap validate-tools` CLI | Baja | 1h | Ninguna |
| 1 | Refactor: crear `AgentFactory.resolve_tools()` unificado + delegar desde `base_crew._resolve_tools` | Baja | 0.5h | Tarea 0 |
| 2 | Implementar detección y parsing de prefijo `mcp:` en `resolve_tools()` | Media | 1.5h | Tarea 1 |
| 3 | Integrar `MCPPool.get_tools()` en resolución MCP + filtrado por tool_name | Alta | 2h | Tarea 2 |
| 4 | Manejar sync/async: bifurcar resolución MCP solo en `run_async()` | Alta | 1.5h | Tarea 3 |
| 5 | Actualizar tests unitarios (`test_base_crew.py`) + agregar tests para `factory.py` | Media | 1.5h | Tareas 1-4 |
| 6 | Validar flujo end-to-end: agente con tool MCP ejecuta correctamente | Alta | 2h | Tareas 1-5 |
| **TOTAL** | | | **10h** | |

> [!IMPORTANT]
> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar la herramienta resultante para el resto del paso (dogfooding obligatorio).

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Implementador modifica `_resolve_tools` sin efecto (dead code) | Alta | Plan original apunta a línea equivocada | Este documento especifica `factory.py:create_agent()` como target real |
| sync/async mismatch en resolución MCP | Alta | `MCPPool.get_tools()` async vs `create_agent()` sync | Bifurcar: MCP solo en `run_async()`, sync omite con warning |
| `crewai-tools` no instalado → ImportError | Media | Dependencia opcional (extras `crew`) | Try/except con mensaje claro de instalación |
| Filtrado de tool específica del listado MCP | Media | `MCPPool.get_tools()` devuelve todas las tools | Parsear `mcp:server:tool_name` y filtrar por atributo `name` |
| Duplicación no eliminada completamente | Media | 2 copias de lógica de resolución | Refactor en Tarea 1 — unificar antes de agregar MCP |
| Circuit breaker MCP abierto bloquea herramientas | Baja | 5 fallos → 60s espera | Documentar. Usar `MCPPool.reset()` en tests |
| Tests existentes testean dead code | Baja | `test_base_crew.py` testea `_resolve_tools` no usado | Actualizar tests en Tarea 5 para testear `resolve_tools()` real |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Tool regular se resuelve correctamente | `allowed_tools=["noop"]` | `tool_registry.get("noop")` → instancia de `NoopTool` |
| TP-2 | Tool MCP se resuelve en path async | `allowed_tools=["mcp:file_server:list_files"]` en `run_async()` | `MCPPool.get_tools("file_server")` → filtra `list_files` → tool instanciada |
| TP-3 | Tool MCP se omite en path sync | `allowed_tools=["mcp:file_server:list_files"]` en `run()` | Warning loggeado, tool omitida, agente sin esa tool |
| TP-4 | Prefijo `mcp:` malformado | `allowed_tools=["mcp:server"]` | Warning loggeado, tool omitida, no crashea |
| TP-5 | Servidor MCP no configurado | `allowed_tools=["mcp:noexist:tool"]` | `MCPConnectionError` con mensaje claro |
| TP-6 | `crewai-tools` no instalado | `allowed_tools=["mcp:server:tool"]` sin paquete | `ImportError` capturado → mensaje de instalación |
| TP-7 | Herramienta `fap validate-tools` | `fap validate-tools --tool "mcp:file_server:list_files" --org-id org_123` | Reporte: tool válida si servidor existe, inválida si no |

Comando para ejecutar tests: `pytest tests/` / `pytest tests/unit/`
