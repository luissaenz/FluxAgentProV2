# 🔍 ANÁLISIS TÉCNICO — PASO 1: PRERREQUISITOS (KILO)

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|-------------------|--------------|--------|-----------|
| 1 | Función `get_secret` existe en vault.py | `grep -n "def get_secret" src/db/vault.py` | ✅ | Línea 23-61, función síncrona definida |
| 2 | `get_secret_async` no existe aún | `grep -n "def get_secret_async" src/db/vault.py` | ❌ | 0 resultados |
| 3 | `get_secret_async` se importa en mcp_pool.py | `grep -rn "get_secret_async" src/tools/mcp_pool.py` | ✅ | Línea 26: import, línea 142: uso |
| 4 | `mcp>=1.0.0` no está en dependencias directas | `grep -n "mcp" pyproject.toml` | ❌ | Solo transitiva vía crewai-tools (opcional) |
| 5 | FlowRegistry.register acepta `description` | Inspección firma método register() | ❌ | Línea 47-52: parámetros depends_on, category; no description |
| 6 | FLOW_INPUT_SCHEMAS definido en routes/flows.py | `grep -n "FLOW_INPUT_SCHEMAS" src/api/routes/flows.py` | ✅ | Línea 70-130, dict global |
| 7 | FLOW_INPUT_SCHEMAS contiene schemas bartenders | `grep -A5 "bartenders_" src/api/routes/flows.py` | ✅ | 4 schemas: preventa, reserva, alerta, cierre |
| 8 | Referencias "bartenders" en codebase | `grep -rn "bartenders" src/ --exclude-dir=tests` | ✅ | 52 referencias en 9 archivos |
| 9 | Flows bartenders registrados en FlowRegistry | `grep -rn "@register_flow.*bartenders" src/` | ❌ | 0 resultados - no registrados |
| 10 | asyncio importado en vault.py | `grep -n "import asyncio" src/db/vault.py` | ❌ | No importado - código síncrono puro |
| 11 | crewai-tools en dependencias opcionales | `grep -A2 "crewai-tools" pyproject.toml` | ✅ | Línea 34: crewai-tools>=0.20.0 (transitiva mcp) |
| 12 | FlowRegistry.get_metadata retorna descripción | Inspección método get_metadata() | ❌ | Línea 96-99: retorna depends_on, category; no description |
| 13 | FLOW_INPUT_SCHEMAS importable sin circular | `grep -n "from.*flows" src/api/routes/flows.py` | ⚠️ | No importa de mcp; probablemente sin circular |
| 14 | Módulo src/mcp/ estructura base | `ls src/mcp/` | ✅ | __init__.py, sanitizer.py existen |
| 15 | flow_to_tool.py no existe | `ls src/mcp/flow_to_tool.py` | ❌ | Archivo no existe |
| 16 | server.py no existe | `ls src/mcp/server.py` | ❌ | Archivo no existe |
| 17 | config.py no existe | `ls src/mcp/config.py` | ❌ | Archivo no existe |
| 18 | tools.py no existe | `ls src/mcp/tools.py` | ❌ | Archivo no existe |

**Discrepancias encontradas:**
- **get_secret_async importado pero indefinido:** mcp_pool.py importa `get_secret_async` (línea 26) que no existe en vault.py. Esto causará ImportError al importar mcp_pool.py. Resolución: Implementar wrapper async en vault.py usando `asyncio.to_thread()`.
- **Dependencia mcp indirecta:** pyproject.toml no incluye `mcp>=1.0.0` como directa. Actualmente llega vía crewai-tools (opcional). Resolución: Agregar a `[project.dependencies]`.
- **FlowRegistry sin soporte description:** register() no acepta `description` parameter. get_metadata() no lo retorna. Resolución: Modificar register() para aceptar description opcional y almacenarlo en metadata.
- **Bartenders no desacoplados:** 52 referencias a "bartenders" en código core. Schemas FLOW_INPUT_SCHEMAS usan keys bartenders_*. Flows no registrados. Resolución: Renombrar a demo_ o eliminar según plan.

## 1. Diseño Funcional

### Happy Path Completo del Paso 1

1. **Desacoplamiento Bartenders:** Renombrar referencias bartenders → demo en código core (scheduler/jobs.py, FLOW_INPUT_SCHEMAS, imports). Mover tools domain-specific a src/tools/demo/. Verificar 0 referencias bartenders en core.
2. **Wrapper Async Vault:** Agregar `get_secret_async()` en vault.py usando `asyncio.to_thread(get_secret)`. Mantener síncrona existente intacta.
3. **Dependencia MCP Directa:** Agregar `mcp>=1.0.0` a pyproject.toml dependencies. Ejecutar uv sync.
4. **Enriquecimiento FlowRegistry:** Modificar `register()` para aceptar `description: str = ""`. Almacenar en metadata dict. Actualizar registros existentes con descriptions.
5. **Verificación Accesibilidad Schemas:** Confirmar import `from src.api.routes.flows import FLOW_INPUT_SCHEMAS` funciona sin circular dependency. Si hay circular, extraer a src/flows/input_schemas.py.
6. **Estructura MCP Base:** Crear src/mcp/__init__.py vacío, config.py con Pydantic settings, tools.py con definiciones Tool MCP estáticas (list_flows, list_agents, etc.).
7. **Flow-to-Tool Translator:** Crear flow_to_tool.py que combine FlowRegistry.get_metadata() + FLOW_INPUT_SCHEMAS para generar Tool objects MCP.
8. **Servidor MCP Stdio:** Crear server.py con entry point, handlers para tools/list y tools/call, integración con org_id vía CLI.
9. **Config Claude Desktop:** Generar claude_desktop_config.json con command apuntando a venv Python, args con --org-id, env con SUPABASE_*.
10. **Verificación E2E:** Arrancar servidor sin errores, conectar desde Claude Desktop, ejecutar tools y validar respuestas JSON válidas.

### Edge Cases Relevantes para MVP

- **Flow sin schema en FLOW_INPUT_SCHEMAS:** Generar tool con inputSchema vacío `{"type": "object", "properties": {}}` + warning log.
- **Secret inexistente en vault:** get_secret_async() debe propagar VaultError igual que síncrona.
- **Dependencia circular en import schemas:** Detectada en verificación 1.0.4; requiere extraer FLOW_INPUT_SCHEMAS a módulo compartido.
- **Flows registrados sin category/description:** Usar defaults (category=None, description="") en flow_to_tool.
- **Org sin flows registrados:** list_flows retorna lista vacía, no error.
- **MCP server sin --org-id:** Argumento requerido; error claro si faltante.

### Manejo de Errores

- **ImportError en mcp_pool.py:** Por get_secret_async faltante. Se resuelve implementando el wrapper.
- **ValidationError en Pydantic config:** Si MCP_ env vars malformadas. Server debe fallar fast con mensaje claro.
- **JSON-RPC errors:** Mapeo de excepciones Python a códigos estándar MCP (InvalidRequest, MethodNotFound, etc.).
- **VaultError en get_secret_async:** Propagar como CallToolResult error en respuesta MCP.
- **Timeout en tools/call:** No implementado en MVP; tools son rápidas (queries DB).

## 2. Diseño Técnico

### Componentes Nuevos

- **`get_secret_async()` (vault.py):** Función async que wrappea `get_secret()` con `asyncio.to_thread()`. Firma idéntica salvo async. No modifica síncrona existente.
- **Dependencia mcp (pyproject.toml):** `mcp>=1.0.0` en `[project.dependencies]`. Fijar versión para evitar breaking changes.
- **FlowRegistry.register() extendido:** Parámetro `description: str = ""` opcional. Almacena en self._metadata[flow_name]["description"].
- **Módulo src/mcp/:** Estructura completa con 8 archivos (config.py, server.py, tools.py, flow_to_tool.py, handlers.py, auth.py, exceptions.py, __init__.py).
- **FLOW_INPUT_SCHEMAS extraído (opcional):** Si circular dependency, mover dict a src/flows/input_schemas.py y importar desde ambos lugares.

### Interfaces (Inputs/Outputs)

- **get_secret_async(org_id: str, secret_name: str) → str:** Input: strings. Output: secret value. Errors: VaultError.
- **FlowRegistry.register(name, depends_on, category, description):** Input: strings/lists. Output: decorator function. Side effect: almacena metadata.
- **MCP Server CLI:** Input: --org-id <uuid>. Output: stdout JSON-RPC responses.
- **flow_to_tool.py:** Input: flow_name. Output: Tool MCP object con name, description, inputSchema.
- **tools.py:** Input: org_id. Output: lista de Tool objects estáticos + dinámicos.

### Modelos de Datos Nuevos

- **MCPConfig (Pydantic BaseSettings):** enabled: bool, transport: str, host/port: str/int, require_auth: bool, allowed_orgs: List[str], org_id: str, env_prefix: str.
- **Tool Definitions:** Objetos Tool MCP con name (str), description (str), inputSchema (dict JSON Schema).
- **CallToolResult:** content: List[TextContent], is_error: bool (interno MCP).

### Integraciones

- **Vault async:** get_secret_async() integra con Supabase service_role client existente.
- **FlowRegistry + Schemas:** flow_to_tool combina metadata registry + schemas estáticos.
- **MCP SDK:** Server usa mcp.Server con handlers async para tools/list y tools/call.
- **Claude Desktop:** Config JSON con command/args/env para lanzar server como proceso hijo.

### Coherencia con Estado de Fase

- **RLS patterns:** Nuevo código usará `current_org_id()::text` + service_role bypass (como en service_catalog).
- **Tool Registry:** Tools MCP usarán decorador `@register_tool` existente si aplicable.
- **HTTP client:** httpx.AsyncClient para requests async (como health_check.py).
- **Auditoría:** domain_events para logs de ejecución tools MCP.
- **Auth:** require_org_id para endpoints MCP si se agregan; verify_org_membership para autenticados.

## 3. Decisiones

- **Wrapper async con asyncio.to_thread():** Elegido sobre loop.run_in_executor() por simplicidad. No bloquea event loop, mantiene compatibilidad.
- **Dependencia mcp directa con version pin:** Evita breaking changes futuros. >=1.0.0,<2.0.0 para estabilidad.
- **Description opcional en register():** No rompe código existente (default ""). Mejora UX en descriptions automáticas.
- **Bartenders → demo en schemas:** Conserva funcionalidad mientras se desacopla. Facilita testing sin afectar lógica.
- **Stdio + SSE dual desde inicio:** Aunque Sprint 1 solo Stdio, estructura config soporta ambos transportes.
- **Org-id por CLI, no JWT:** Simplifica Sprint 1. Auth Bridge (JWT) en Sprint 3.
- **Tools estáticas + dinámicas:** Estáticas (list_flows) siempre presentes; dinámicas (execute_flow) solo cuando flows registrados.

## 4. Criterios de Aceptación

1. `import mcp` funciona sin instalar opcionales (crew).
2. `get_secret_async()` resuelve secretos correctamente (igual output que síncrona).
3. FlowRegistry.register() acepta description y get_metadata() lo retorna.
4. FLOW_INPUT_SCHEMAS importable desde src/mcp/ sin circular dependency.
5. 0 referencias "bartenders" en código core (excluyendo demo/, tests/).
6. `python -m src.mcp.server --org-id test --help` ejecuta sin errores.
7. MCP server expone ≥5 tools en tools/list (estáticas + flows registrados).
8. Claude Desktop conecta y muestra tools de FAP en chat.
9. `list_flows` retorna flows reales con metadata (category, depends_on).
10. `list_agents` query agent_catalog por org_id.
11. `get_agent_detail` retorna soul_json, skills, allowed_tools.
12. `get_server_time` retorna timestamp UTC válido.
13. `list_capabilities` retorna metadata server (version, org_id, transport).
14. Todas tools retornan TextContent JSON válido parseable.
15. No errores en logs Claude Desktop al ejecutar tools.

## 5. Riesgos

- **ImportError por get_secret_async faltante:** Probabilidad Alta, Impacto Alto. Mitigación: Implementar inmediatamente en 1.0.1.
- **Dependencia circular en FLOW_INPUT_SCHEMAS:** Probabilidad Media, Impacto Medio. Mitigación: Verificación 1.0.4 y extracción si necesario.
- **Breaking changes en MCP SDK:** Probabilidad Baja, Impacto Alto. Mitigación: Version pin >=1.0.0,<2.0.0.
- **Claude Desktop no detecta server:** Probabilidad Media, Impacto Alto. Mitigación: Verificar path Python, formato JSON config, logs.
- **Flows bartenders no registrados:** Probabilidad Media, Impacto Medio. Mitigación: Verificar que flows demo están registrados antes de testing.
- **Secrets no accesibles en proceso hijo:** Probabilidad Media, Impacto Alto. Mitigación: Configurar SUPABASE_* en env del config JSON.

## 6. Plan

| Tarea | Complejidad | Tiempo Estimado | Dependencias |
|-------|-------------|-----------------|-------------|
| 1.0.0.1 - Desacoplar bartenders del core | Media | 45min | - |
| 1.0.1 - Crear get_secret_async() | Baja | 20min | 1.0.0.1 |
| 1.0.2 - Agregar mcp>=1.0.0 directa | Baja | 10min | - |
| 1.0.3 - Enriquecer FlowRegistry.register() | Baja | 30min | - |
| 1.0.4 - Verificar accesibilidad FLOW_INPUT_SCHEMAS | Baja | 15min | - |
| 1.1.1 - Crear src/mcp/__init__.py | Baja | 5min | 1.0.1, 1.0.2 |
| 1.1.2 - Crear src/mcp/config.py | Baja | 20min | 1.1.1 |
| 1.1.3 - Crear src/mcp/tools.py | Media | 45min | 1.1.2 |
| 1.2.1 - Crear src/mcp/flow_to_tool.py | Media | 60min | 1.0.3, 1.0.4 |
| 1.3.1 - Crear src/mcp/server.py | Alta | 90min | 1.1.3, 1.2.1 |
| 1.4.1 - Configurar claude_desktop_config.json | Baja | 15min | 1.3.1 |
| 1.5.1 - Verificación server arranca | Baja | 10min | 1.3.1 |
| 1.5.2 - Verificación Claude conecta | Baja | 10min | 1.4.1 |
| 1.5.3 - Test list_flows funciona | Baja | 10min | 1.5.2 |
| 1.5.4 - Test list_agents funciona | Baja | 10min | 1.5.3 |
| 1.5.5 - Test get_agent_detail funciona | Baja | 10min | 1.5.4 |

**Estimación Total:** 4.5h  
**Estimación por Sub-paso:**  
- 1.0: 2h  
- 1.1: 1.25h  
- 1.2: 1h  
- 1.3: 1.5h  
- 1.4: 0.25h  
- 1.5: 0.5h  

## 🔮 Roadmap

- **Enriquecer descriptions:** Generar descriptions automáticas más inteligentes basadas en flow_type (ej: "Ejecutar workflow de preventa para bartenders").
- **Cache de tools:** Evitar regenerar Tool objects en cada tools/list si no cambiaron flows.
- **Health checks MCP:** Endpoint para verificar conectividad server sin Claude Desktop.
- **Logging estructurado:** Integrar structlog en server MCP para mejor debugging.
- **Config por org:** allowed_orgs en config para filtrar tools por organización.
- **Pre-requisitos para Sprint 3:** Auth Bridge requerirá middleware verify_org_membership en handlers MCP.