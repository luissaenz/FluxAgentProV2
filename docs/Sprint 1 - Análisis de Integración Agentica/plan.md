# Sprint 1: Prerrequisitos + MCP Server Básico — Definición Ampliada

**Objetivo:** Claude Desktop conectado a FAP, listando flows disponibles y consultando agentes.  
**Esfuerzo estimado:** 8-10h  
**Hito de salida:** Preguntar a Claude "¿Qué flows están disponibles en FAP?" y que invoque `list_flows()` retornando datos reales.  
**Referencia:** FAP-MCP-Analisis v3.3 §3, §4, §7, §8, §11 (Fase 0 + Fase 1)

---

## Contexto: Qué Existe Hoy vs Qué Falta

### Ya existe (verificar contra código con 0_CONTEXTO v2)

| Componente | Archivo | Relevancia para Sprint 1 |
|:---|:---|:---|
| FlowRegistry con flows registrados | `src/flows/registry.py` | Fuente de datos para `list_flows` |
| FLOW_INPUT_SCHEMAS | `src/api/routes/flows.py` (~L70-130) | JSON Schemas por flow_type — necesario para `flow_to_tool.py` |
| API REST con endpoints de flows | `src/api/routes/flows.py` | Patrones de auth y middleware a reutilizar |
| JWT auth middleware (PyJWT + JWKS) | `src/api/middleware.py` | Reutilizar para auth bridge MCP (Sprint 3, no Sprint 1) |
| MCPPool (cliente MCP) | `src/tools/mcp_pool.py` | FAP ya es CLIENTE MCP — ahora será también SERVIDOR |
| Vault + get_secret (síncrono) | `src/db/vault.py` | Base para `get_secret_async` |
| TenantClient con RLS | `src/db/session.py` | Aislamiento multi-tenant |
| Anthropic SDK ≥0.40.0 | `pyproject.toml` | Tiene helpers MCP built-in |

### No existe aún (lo que se crea en Sprint 1)

| Componente | Archivo a Crear | Propósito |
|:---|:---|:---|
| `get_secret_async()` | `src/db/vault.py` (modificar) | Wrapper async del síncrono — prerrequisito para MCP server async |
| Dependencia `mcp>=1.0.0` directa | `pyproject.toml` (modificar) | Actualmente solo transitiva vía crewai-tools (opcional) |
| Módulo `src/mcp/` completo | `src/mcp/__init__.py` | Nuevo directorio para todo el servidor MCP |
| MCP Server Stdio | `src/mcp/server.py` | Entry point que Claude Desktop ejecuta |
| Flow-to-Tool translator | `src/mcp/flow_to_tool.py` | Convierte FlowRegistry → Tool MCP con inputSchema |
| Tool definitions | `src/mcp/tools.py` | Definiciones estáticas de tools de sistema |
| MCP Config | `src/mcp/config.py` | Settings con env_prefix MCP_ |
| Claude Desktop config | `claude_desktop_config.json` | Configuración local para conectar |

---

## Paso 1.0: Prerrequisitos (Fase 0 del v3.3)

**Objetivo:** Dejar el terreno listo para que el MCP Server pueda crearse sin blockers.



### 1.0.0.1 — Desacoplar Bartenders NOA del core

T1: Renombrar src/scheduler/bartenders_jobs.py → src/scheduler/jobs.py (o extraer scheduler a src/scheduler/__init__.py como ya estaba planeado en el análisis FINAL). Actualizar los imports en src/api/main.py o donde se referencie.
T2: En FLOW_INPUT_SCHEMAS (flows.py:70-130), renombrar las keys bartenders_preventa → demo_preventa, bartenders_reserva → demo_reserva, bartenders_alerta → demo_alerta, bartenders_cierre → demo_cierre. O si preferís eliminarlos directamente (ya que los flows no están registrados en FlowRegistry y el Service Catalog va a manejar esto), dejar el dict vacío o con un solo schema de ejemplo genérico.
T3: Mover las tools domain-specific a src/tools/demo/: clima_tool.py, escandallo_tool.py, inventario_tool.py, y cualquier otra que sea específica de Bartenders NOA. Actualizar imports si los hay.
T4: Verificar que no queden referencias a "bartenders" en ningún archivo core (excluyendo data/, tests/, y documentación). Un grep -rn "bartenders" src/ --exclude-dir=demo debería retornar 0 resultados.


### 1.0.1 — Crear `get_secret_async()` en vault.py

**Por qué:** El MCP server es async (JSON-RPC sobre stdio es event-loop). `get_secret()` actual es síncrono. Necesitamos un wrapper que no bloquee el event loop. El MCPPool ya importa `get_secret_async` (que no existe) — esto cierra ese gap.

**Qué hacer:**
- Agregar función en `src/db/vault.py`
- Usa `asyncio.to_thread()` (Python 3.9+) o `loop.run_in_executor()`
- No modifica la función síncrona existente — solo agrega la async

**Verificación:** `await get_secret_async("test_org", "test_key")` retorna el mismo valor que `get_secret("test_org", "test_key")`.

**Esfuerzo:** 30min

### 1.0.2 — Agregar `mcp>=1.0.0` como dependencia directa

**Por qué:** Actualmente `mcp` solo llega como transitiva vía `crewai-tools` que es una dependencia OPCIONAL (`[crew]`). El MCP Server necesita `mcp` disponible siempre, no solo cuando crewai está instalado.

**Qué hacer:**
- Agregar `mcp>=1.0.0` a `[project.dependencies]` en `pyproject.toml`
- Ejecutar `uv sync` o `pip install -e .`
- Verificar que `from mcp.types import Tool, TextContent, CallToolResult` funciona

**Verificación:** `python -c "from mcp.types import Tool; print('OK')"` → OK.

**Esfuerzo:** 15min

### 1.0.3 — Enriquecer FlowRegistry.register() (opcional pero recomendado)

**Por qué:** `FlowRegistry.get_metadata()` solo retorna `{depends_on, category}`. Para generar tools MCP con buenas descriptions, necesitamos que el registro acepte `description`. Sin esto, `flow_to_tool.py` tiene que generar descriptions genéricas ("Ejecutar flow: Bartenders Preventa").

**Qué hacer:**
- Modificar `FlowRegistry.register()` para aceptar parámetro `description: str = ""`
- Almacenar en el metadata dict
- No rompe código existente (parámetro opcional con default)

**Alternativa si no se hace:** `flow_to_tool.py` genera descriptions automáticas basadas en el nombre del flow. Funciona pero es menos útil para el LLM.

**Verificación:** `flow_registry.get_metadata("bartenders_preventa")` retorna `{depends_on: [...], category: "...", description: "..."}`.

**Esfuerzo:** 1h (incluyendo actualizar los registros existentes con descriptions)

### 1.0.4 — Verificar accesibilidad de FLOW_INPUT_SCHEMAS

**Por qué:** `FLOW_INPUT_SCHEMAS` está definido dentro de `src/api/routes/flows.py`. `flow_to_tool.py` necesita importar esos schemas. Si hay dependencia circular (routes importa de flows, mcp importa de routes), hay que extraer los schemas a un módulo compartido.

**Qué hacer:**
- Intentar `from src.api.routes.flows import FLOW_INPUT_SCHEMAS` desde un script standalone
- Si hay dependencia circular: mover `FLOW_INPUT_SCHEMAS` a `src/flows/schemas.py` o `src/flows/input_schemas.py`
- Si no hay: dejar donde está

**Verificación:** `python -c "from src.api.routes.flows import FLOW_INPUT_SCHEMAS; print(len(FLOW_INPUT_SCHEMAS))"` → número de schemas sin error de import circular.

**Esfuerzo:** 30min (15min si no hay circular, 30min si hay que mover)

**Definition of Done Paso 1.0:** Los 4 prerrequisitos completados. `import mcp` funciona, `get_secret_async` existe, FlowRegistry acepta descriptions, FLOW_INPUT_SCHEMAS es importable desde fuera de routes.

---

## Paso 1.1: Módulo MCP — Estructura Base

**Objetivo:** Crear el directorio `src/mcp/` con la estructura definida en v3.3 §3.2.

### 1.1.1 — Crear `src/mcp/__init__.py`

**Qué:** Archivo init vacío (o con imports de conveniencia).

**Esfuerzo:** 5min

### 1.1.2 — Crear `src/mcp/config.py`

**Qué:** Configuración del servidor MCP con Pydantic BaseSettings.

**Campos (v3.3 §8):**
- `enabled: bool = True`
- `transport: str = "stdio"` (stdio | sse)
- `host: str = "127.0.0.1"` (solo SSE, no usado en Sprint 1)
- `port: int = 8765` (solo SSE, no usado en Sprint 1)
- `require_auth: bool = False` (Sprint 1 sin auth — auth es Sprint 3)
- `allowed_orgs: List[str] = []` (vacío = todas)
- `org_id: str = ""` (para modo Stdio, recibido vía CLI `--org-id`)
- `env_prefix = "MCP_"`

**Por qué `require_auth = False` en Sprint 1:** El objetivo es validar conectividad. Auth Bridge (JWT, membresía org) se implementa en Sprint 3. Para Sprint 1, el `--org-id` vía CLI es suficiente para identificar la sesión.

**Esfuerzo:** 30min

### 1.1.3 — Crear `src/mcp/tools.py` — Definiciones de tools estáticas

**Qué:** Las tools de sistema que no dependen de FlowRegistry. Son definiciones fijas que el servidor expone siempre.

**Tools para Sprint 1 (solo lectura, sin ejecución):**

| Tool MCP | Input Schema | Output | Qué hace |
|:---|:---|:---|:---|
| `list_flows` | `{}` | Lista de flows disponibles con categoría y dependencias | Llama `flow_registry.list_flows()` |
| `list_agents` | `{}` | Lista de agentes de la org | Query a `agent_catalog` filtrado por org_id |
| `get_agent_detail` | `{agent_id: str}` | Detalle del agente (soul_json, skills, allowed_tools) | Query a `agent_catalog` por ID |
| `get_server_time` | `{}` | Timestamp actual del servidor | `datetime.utcnow()` — tool de health check |
| `list_capabilities` | `{}` | Resumen de capacidades del servidor | Retorna versión, org_id, transport, tools count |

**Por qué estas 5 y no las de ejecución:** Sprint 1 valida conectividad y reflexión. Claude puede "ver" qué tiene FAP pero no ejecutar todavía. Las tools de ejecución (`execute_flow`, `approve_task`) van en Sprint 3.

**Formato de cada tool (MCP SDK):**

```python
Tool(
    name="list_flows",
    description="Lista todos los flujos de trabajo disponibles en FAP para esta organización, "
                "incluyendo categoría, dependencias entre flujos, y esquema de entrada.",
    inputSchema={
        "type": "object",
        "properties": {},
    }
)
```

**Esfuerzo:** 1h

---

## Paso 1.2: Flow-to-Tool Translator

**Objetivo:** Convertir cada flow registrado en FlowRegistry en una Tool MCP con su inputSchema.

### 1.2.1 — Crear `src/mcp/flow_to_tool.py`

**Qué:** Función que toma un flow_name y genera un objeto `Tool` MCP combinando dos fuentes de metadata (corrección v3.3 §3.4).

**Fuentes de datos:**
1. `FlowRegistry.get_metadata(flow_name)` → `{depends_on, category, description}`
2. `FLOW_INPUT_SCHEMAS[flow_name]` → JSON Schema de input (definido en routes/flows.py)

**Lógica:**
- Para cada flow registrado en FlowRegistry, generar un `Tool` MCP
- El `name` es el flow_name tal cual
- La `description` viene del metadata si está disponible (1.0.3), o se genera automáticamente
- El `inputSchema` viene de FLOW_INPUT_SCHEMAS; si no existe, schema vacío `{"type": "object", "properties": {}}`

**Output:** Lista de `Tool` MCP listos para enviar en respuesta a `tools/list`.

**Edge case:** Un flow está registrado en FlowRegistry pero no tiene entrada en FLOW_INPUT_SCHEMAS → tool se genera con schema vacío + warning en logs.

**Esfuerzo:** 1h

---

## Paso 1.3: MCP Server Stdio

**Objetivo:** El servidor que Claude Desktop ejecuta como proceso hijo.

### 1.3.1 — Crear `src/mcp/server.py`

**Qué:** Entry point principal del MCP server. Usa el SDK `mcp` para crear un servidor Stdio que:

1. Parsea CLI args (`--org-id`)
2. Inicializa MCPConfig
3. Registra las tools (estáticas de tools.py + dinámicas de flow_to_tool.py)
4. Registra los handlers para `tools/call`
5. Arranca el servidor Stdio

**Protocolo:** JSON-RPC 2.0 sobre stdin/stdout (estándar MCP).

**Handlers para Sprint 1:**

| Request | Handler | Qué retorna |
|:---|:---|:---|
| `tools/list` | Retorna todas las tools registradas | Lista de Tool objects |
| `tools/call` name=`list_flows` | Llama FlowRegistry | Lista de flows como TextContent |
| `tools/call` name=`list_agents` | Query agent_catalog | Lista de agentes como TextContent |
| `tools/call` name=`get_agent_detail` | Query agent_catalog por ID | Detalle como TextContent |
| `tools/call` name=`get_server_time` | datetime.utcnow() | Timestamp como TextContent |
| `tools/call` name=`list_capabilities` | Metadata del servidor | Capabilities como TextContent |

**Respuestas:** Todas retornan `CallToolResult` con `TextContent` (JSON serializado como string). Para Sprint 1 no hay ImageContent ni otros tipos.

**CLI:**
```bash
python -m src.mcp.server --org-id "uuid-de-la-org"
```

**Esfuerzo:** 2h

---

## Paso 1.4: Configuración de Claude Desktop

### 1.4.1 — Crear/actualizar `claude_desktop_config.json`

**Qué:** Configurar Claude Desktop para que lance el MCP server de FAP.

**Ubicación:**
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Contenido (v3.3 §7.2):**
```json
{
  "mcpServers": {
    "FluxAgentPro-V2": {
      "command": "<path-al-python-del-venv>",
      "args": ["-m", "src.mcp.server", "--org-id", "<ORG_UUID>"],
      "env": {
        "SUPABASE_URL": "https://xxx.supabase.co",
        "SUPABASE_SERVICE_KEY": "<key>"
      }
    }
  }
}
```

**Notas:**
- El path al Python debe ser el del `.venv` del proyecto
- `ANTHROPIC_API_KEY` NO es necesario para Sprint 1 (el server no llama a LLMs, solo expone tools)
- `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` SÍ son necesarios para queries a FlowRegistry y agent_catalog

**Esfuerzo:** 15min

---

## Paso 1.5: Verificación E2E

### 1.5.1 — Test manual: servidor arranca sin errores

```bash
python -m src.mcp.server --org-id test_org --help
# Debe mostrar opciones de configuración sin errores de import
```

### 1.5.2 — Test manual: Claude Desktop conecta

1. Reiniciar Claude Desktop
2. Verificar que el ícono de MCP tools aparece en el chat
3. Preguntar: "¿Qué herramientas tenés disponibles?"
4. Claude debe listar las tools de FAP

### 1.5.3 — Test funcional: `list_flows` retorna datos

Preguntar a Claude: "¿Qué flows están disponibles en FAP?"

**Esperado:** Claude invoca `list_flows` → retorna lista de flows registrados con nombres, categorías y dependencias.

### 1.5.4 — Test funcional: `list_agents` retorna datos

Preguntar a Claude: "¿Qué agentes tiene configurados esta organización?"

**Esperado:** Claude invoca `list_agents` → retorna lista de agentes de la org con roles y nombres.

### 1.5.5 — Test funcional: `get_agent_detail` con parámetro

Preguntar a Claude: "Dame los detalles del agente de Ventas"

**Esperado:** Claude identifica el agent_id, invoca `get_agent_detail` → retorna soul_json, skills, allowed_tools del agente.

**Esfuerzo total verificación:** 30min

---

## Archivos Creados/Modificados — Resumen

| Acción | Archivo | Paso |
|:---|:---|:---|
| ✏️ Modificar | `src/db/vault.py` | 1.0.1 — agregar `get_secret_async()` |
| ✏️ Modificar | `pyproject.toml` | 1.0.2 — agregar `mcp>=1.0.0` |
| ✏️ Modificar | `src/flows/registry.py` | 1.0.3 — aceptar `description` en register() |
| ⚠️ Posible | `src/flows/input_schemas.py` | 1.0.4 — solo si hay dependencia circular |
| 🆕 Crear | `src/mcp/__init__.py` | 1.1.1 |
| 🆕 Crear | `src/mcp/config.py` | 1.1.2 |
| 🆕 Crear | `src/mcp/tools.py` | 1.1.3 |
| 🆕 Crear | `src/mcp/flow_to_tool.py` | 1.2.1 |
| 🆕 Crear | `src/mcp/server.py` | 1.3.1 |
| ✏️ Modificar | `claude_desktop_config.json` | 1.4.1 |

**Total:** 4-5 archivos nuevos + 3-4 archivos modificados

---

## Criterios de Aceptación Sprint 1

| # | Criterio | Verificación |
|:---|:---|:---|
| CA1 | `import mcp` funciona sin instalar extras opcionales | `python -c "from mcp.types import Tool"` → sin error |
| CA2 | `get_secret_async()` resuelve secretos | Test unitario async |
| CA3 | `python -m src.mcp.server --org-id test --help` arranca sin error | CLI ejecutable |
| CA4 | Claude Desktop muestra tools de FAP | Verificación visual post-reinicio |
| CA5 | `tools/list` retorna ≥5 herramientas | Claude muestra list_flows, list_agents, get_agent_detail, get_server_time, list_capabilities |
| CA6 | `list_flows` retorna flows reales de FlowRegistry | Pregunta a Claude → datos correctos |
| CA7 | `list_agents` retorna agentes de la org | Pregunta a Claude → datos de agent_catalog |
| CA8 | `get_agent_detail` acepta agent_id y retorna detalle | Pregunta a Claude sobre un agente específico |
| CA9 | Respuestas son TextContent JSON válido | Parseable como JSON sin errores |
| CA10 | No hay errores en logs del servidor al ejecutar tools | `%APPDATA%\Claude\logs\` limpio |

---

## Riesgos Específicos del Sprint 1

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|:---|:---|:---|:---|:---|
| R1 | Dependencia circular al importar FLOW_INPUT_SCHEMAS | Media | Medio | Paso 1.0.4 verifica y extrae si necesario |
| R2 | SDK `mcp` tiene breaking changes entre versiones | Baja | Alto | Fijar versión `mcp>=1.0.0,<2.0.0` |
| R3 | Claude Desktop no detecta el server | Media | Alto | Verificar logs, path al Python, formato de config JSON |
| R4 | FlowRegistry vacío (no hay flows registrados) | Media | Medio | Verificar que los flows de Bartenders NOA están registrados |
| R5 | `agent_catalog` vacío o con schema diferente al esperado | Media | Medio | Verificar columnas reales contra migraciones en 0_CONTEXTO |
| R6 | `SUPABASE_SERVICE_KEY` no disponible en el env del proceso hijo | Media | Alto | Configurar explícitamente en `claude_desktop_config.json` → `env` |

---

## Lo Que NO Está en Sprint 1 (Explícitamente Excluido)

| Feature | Sprint |
|:---|:---|
| Auth Bridge (JWT verification) | Sprint 3 |
| `execute_flow` handler | Sprint 3 |
| `approve_task` / `reject_task` | Sprint 4 |
| SSE transport | Sprint 4 |
| Service Catalog TIPO C | Sprint 2 |
| Sanitizer / Regla R3 | Sprint 2 |
| Excepciones MCP → JSON-RPC | Sprint 3 |
| Inputs complejos (imágenes) | Sprint 4 |

---

## Proceso de Ejecución

Este sprint NO tiene análisis FINAL todavía. Debe pasar por el pipeline v2:

```
1. Ejecutar 0_CONTEXTO v2 → genera estado-fase.md verificado
2. Pasar Sprint 1 por 1_ANALISIS v2 (4 agentes)
3. Pasar por 2_UNIFICACION v2 → analisis-FINAL.md
4. Ejecutar 3_IMPLEMENTADOR v2 con el FINAL
5. Validar con 4_VALIDADOR v2
6. Corregir con 5_CORRECTOR v2 si necesario
```

El primer paso concreto es ejecutar 0_CONTEXTO v2 para generar el `estado-fase.md` actualizado que refleje el estado real del código antes de empezar el análisis.
