# 📋 ANÁLISIS TÉCNICO — Paso 1: MCPRegistryClient (Agente OC)

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `org_mcp_servers` existe | `grep "CREATE TABLE.*org_mcp_servers" migrations/005*` | ✅ | `migrations/005_org_mcp_servers.sql:9` |
| 2 | Tabla `service_catalog` existe | `grep "CREATE TABLE.*service_catalog" migrations/024*` | ✅ | `migrations/024_service_catalog.sql:8` |
| 3 | Tabla `service_tools` existe | `grep "CREATE TABLE.*service_tools" migrations/024*` | ✅ | `migrations/024_service_catalog.sql:59` |
| 4 | Columnas `org_mcp_servers`: id, org_id, name, command, args, secret_name, is_active | Lectura migración 005 | ✅ | `migrations/005_org_mcp_servers.sql:9-18` |
| 5 | Columnas `service_catalog`: id, name, category, auth_type, base_url, required_secrets | Lectura migración 024 | ✅ | `migrations/024_service_catalog.sql:8-22` |
| 6 | Columnas `service_tools`: id, service_id, name, input_schema, output_schema, execution, tool_profile | Lectura migración 024 | ✅ | `migrations/024_service_catalog.sql:59-68` |
| 7 | IntegrationResolver.resolve() retorna ResolutionResult con not_found | `src/flows/integration_resolver.py:21-27` | ✅ | `ResolutionResult` tiene campo `not_found: List[str]` |
| 8 | architect_flow.py tiene `_build_resolution_response()` | `src/flows/architect_flow.py:429` | ✅ | Retorna status `"resolution_required"` |
| 9 | httpx disponible en dependencies | `pyproject.toml:23` | ✅ | `"httpx>=0.28.0"` |
| 10 | src/mcp/registry_client.py NO existe | `ls src/mcp/*.py` | ✅ | Archivo NO existe — correcto según plan ("NUEVO") |
| 11 | IntegrationResolver tiene método apply_mapping() | `src/flows/integration_resolver.py:190` | ✅ | `apply_mapping(workflow_def, mapping)` |
| 12 | RLS en org_mcp_servers | `migrations/005_org_mcp_servers.sql:22-26` | ✅ | Política con `current_org_id()` |
| 13 | RLS en org_service_integrations | `migrations/024_service_catalog.sql:44-51` | ✅ | Patrón con service_role bypass |
| 14 | Dependencia `httpx` para requests HTTP | `pyproject.toml` | ✅ | Ya existe en proyecto |
| 15 | Patrón de Import en código existente | Buscar patterns de insert/upsert en DB | ✅ | `architect_flow.py:396` usa upsert con on_conflict |

**Discrepancias encontradas:**

1. ❌ **El plan asume import_as_type_b usa `is_active: False`**, pero la migración 005 tiene `is_active BOOLEAN DEFAULT TRUE`. **Resolución:** Usar valor explícito `False` al importar para forzar configuración manual, coherente con el plan.

2. ⚠️ **El plan no especifica qué hacer si el servidor tiene URL SSE vs command/args.** El código de MCP pool existente debe soportar ambos. **Verificar en implementación.**

3. ⚠️ **No hay validación de formato de URL del registry externo** - riesgo de SSL/tls. **Mitigación:** Usar httpx con verify=True por defecto.

---

## 1. Diseño Funcional

### 1.1 Happy Path

```
1. Usuario describe workflow: "Crear proceso de reservas con Google Calendar"
2. ArchitectAgent genera definition con tool_hint: "calendar_create_event"
3. IntegrationResolver.resolve() retorna not_found: ["calendar_create_event"]
4. architect_flow._build_resolution_response() retorna status: "resolution_required"
   con not_found: ["calendar_create_event"]
5. [NUEVO] Sistema pregunta al usuario: "¿Busco integraciones externas?"
6. Usuario confirma → MCPRegistryClient.search("calendar")
7. Registry retorna: [{"name": "Google Calendar MCP", "description": "..."}]
8. Sistema muestra opciones al usuario
9. Usuario elige instalar "Google Calendar MCP" como TIPO B
10. MCPRegistryClient.import_as_type_b(server, org_id)
    → Inserta en org_mcp_servers con is_active=False
11. Re-ejecutar resolve() → ahora matchea con server tools existentes
12. Workflow se persiste exitosamente
```

### 1.2 Edge Cases

| Escenario | Manejo |
|---|---|
| Registry no retorna resultados | Retornar mensaje: "No encontré integraciones externas. ¿Tenés la URL del servidor MCP?" |
| Usuario rechaza instalación | Retornar al estado anterior con mensaje de que debe configurar manualmente |
| Error HTTP al consultar registry | Timeout 10s → retornar error gracefully, no bloquear workflow |
| Server importado ya existe (mismo name+org) | Usar upsert con on_conflict, actualizar en lugar de duplicar |
| tool no tiene match en service_tools post-import | Importar como TYPE C (service_tools) en lugar de TYPE B |

### 1.3 Error Handling

- **Timeout de red:** 10 segundos, retry no implementado para MVP (simplificar)
- **JSON inválido del registry:** Loguear error, retornar lista vacía
- **Credenciales faltantes post-import:** El servidor importado queda `is_active=False`, usuario debe configurar manualmente antes de activar

---

## 2. Diseño Técnico

### 2.1 Componentes

**Nuevo:**
- `src/mcp/registry_client.py` — clase `MCPRegistryClient` + dataclass `MCPServerInfo`

**Modificado:**
- `src/flows/architect_flow.py` — agregar lógica post-resolver para invocar registry

### 2.2 Interfaz MCPServerInfo (dataclass)

```python
@dataclass
class MCPServerInfo:
    name: str                           # "Google Sheets MCP"
    source: str                         # "github_registry" | "mcpmarket" | "manual"
    url: str                            # URL del repo o endpoint SSE
    command: str | None                 # "npx" | "python" | None (si es SSE)
    args: list[str] | None              # ["-y", "@modelcontextprotocol/server-google-sheets"]
    tools: list[dict] = field(default_factory=list)
    description: str = ""
    auth_required: bool = False
    install_instructions: str = ""
```

### 2.3 Interfaz MCPRegistryClient

```python
class MCPRegistryClient:
    async def search(self, query: str) -> list[MCPServerInfo]:
        """Busca en GitHub MCP Registry. Retorna max 5 resultados."""
        
    async def discover_tools(self, server: MCPServerInfo) -> list[dict]:
        """Parsea README del repo para extraer tools (MVP). No ejecuta servidor."""
        
    async def import_as_type_b(self, server: MCPServerInfo, org_id: str) -> str:
        """Inserta en org_mcp_servers. Retorna ID."""
        
    async def import_as_type_c(self, server: MCPServerInfo, org_id: str) -> list[str]:
        """Inserta en service_catalog + service_tools. Retorna lista de tool_ids."""
```

### 2.4 Integración en ArchitectFlow

Ubicación sugerida: después de línea 143 en `architect_flow.py`, cuando `resolution.not_found` no está vacío:

```python
# En architect_flow.py — después de _build_resolution_response
if resolution.not_found and user_asked_for_external_search:
    registry = MCPRegistryClient()
    discovered = {}
    for tool_hint in resolution.not_found:
        search_query = tool_hint.replace("_", " ").split(".")[0]
        results = await registry.search(search_query)
        if results:
            discovered[tool_hint] = results
    
    if discovered:
        return {
            "status": "external_integrations_found",
            "discovered": discovered,  # Opciones para UI
            "message": "Encontré estas integraciones externas...",
        }
```

### 2.5 Modelos de Datos

**org_mcp_servers (existente):**
| Columna | Tipo | Uso en import |
|---|---|---|
| id | UUID | PK |
| org_id | UUID | FK organizations |
| name | TEXT | server.name |
| command | TEXT | server.command o "npx" |
| args | JSONB | server.args o [] |
| secret_name | TEXT | Nullable |
| is_active | BOOLEAN | **FALSE** (requiere config manual) |

**service_catalog (existente, si TYPE C):**
| Columna | Valor en import |
|---|---|
| id | server.name.lower().replace(" ", "_") |
| name | server.name |
| category | "external_mcp" |
| auth_type | "api_key" si server.auth_required else "none" |
| base_url | server.url |

**service_tools (existente, si TYPE C):**
| Columna | Valor en import |
|---|---|
| id | f"{service_id}.{tool['name']}" |
| service_id | service_id |
| name | tool['name'] |
| input_schema | tool.get('inputSchema', {}) |
| execution | {"type": "mcp", "server": server.name} |
| tool_profile | {"description": tool['description'], "risk_level": "medium", "requires_approval": False} |

---

## 3. Decisiones

| Decisión | Justificación |
|---|---|
| **discover_tools() parsea README, no ejecuta servidor** | Seguridad: ejecutar servidores MCP externos requiere instalar dependencias (npx, pip), riesgo de código arbitrario. MVP: solo parsear docs. |
| **Import como TYPE B por defecto** | org_mcp_servers ya existe y MCPPool sabe conectar. TYPE C requiere más lógica de parsing de schemas. |
| **is_active=False al importar** | Forzar configuración manual de credenciales antes de activación. Coherente con plan. |
| **Solo GitHub MCP Registry para MVP** | Fuente oficial, API JSON estable. mcpmarket/smithery son roadmap. |
| **Usuario elige qué instalar** | No auto-importar sin consentimiento. Más transparente, evita carga innecesaria. |
| **Timeout 10s para HTTP** | Balance entre responsividad y dar tiempo a registry externo. |
| **Máx 5 resultados por search** | Evitar overwhelmar al usuario con opciones. |

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| 1 | MCPRegistryClient.search("google") retorna lista de MCPServerInfo | ✅ |
| 2 | import_as_type_b() inserta fila en org_mcp_servers con is_active=False | ✅ |
| 3 | import_as_type_c() inserta en service_catalog y service_tools | ✅ |
| 4 | discover_tools() retorna lista de tools sin ejecutar servidor | ✅ |
| 5 | Timeout de HTTP no excede 10 segundos | ✅ |
| 6 | Error de red no lanza excepción no manejada | ✅ |
| 7 | Duplicado de servidor (mismo name+org) hace upsert, no insert duplicado | ✅ |
| 8 | IntegrationResolver re-resuelve correctamente después de import | ✅ |
| 9 | architect_flow retorna opciones al usuario cuando hay matches externos | ✅ |
| 10 | Kata de test: integración end-to-end con mock de registry | ✅ |

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| **Registry externo no disponible (downtime)** | Medio | Timeout 10s, fallback a mensaje "No se pudo buscar, configurá manualmente" |
| **Formato de respuesta del registry cambia** | Alto | Versionar el endpoint esperado, validar schema antes de parsear |
| **Inyección de comandos maliciosos vía args** | Crítico | **NO** ejecutar servidor externo en discover_tools (MVP). Sanitizar args en import. |
| **Conflicto con servidor existente (mismo name)** | Bajo | Usar upsert con on_conflict="org_id,name" |
| **No hay tools disponibles post-import (TYPE B)** | Medio | TYPE B requiere que el servidor tenga tools listables. Advertir al usuario. |
| **Usuario importa servidor que no funciona** | Medio | is_active=False por defecto, requiere verificación manual |
| **Pasos futuros no pueden usar estas tools por falta de schema** | Medio | TYPE C storea input_schema parseado del README; suficiente para MVP |
| **Ralentización de architect_flow por llamada HTTP** | Bajo | Solo si usuario confirma búsqueda, no automático |

---

## 6. Plan

| # | Tarea | Complejidad | Tiempo | Dependencias |
|---|---|---|---|---|
| 1 | Crear `src/mcp/registry_client.py` con MCPServerInfo + MCPRegistryClient | Alta | 30min | Ninguna |
| 2 | Implementar `search()` contra GitHub MCP Registry | Media | 1h | Endpoint registry |
| 3 | Implementar `discover_tools()` — parseo de README (regex o BeautifulSoup) | Alta | 2h | httpx, beautifulsoup4 (ya en .venv) |
| 4 | Implementar `import_as_type_b()` con upsert | Baja | 30min | Tabla org_mcp_servers |
| 5 | Implementar `import_as_type_c()` con upsert | Media | 45min | Tablas service_catalog, service_tools |
| 6 | Modificar `architect_flow.py` — agregar flujo de búsqueda externa | Media | 1h | IntegrationResolver existente |
| 7 | Tests unitarios: mock de httpx + mock de DB | Alta | 1.5h | pytest, pytest-asyncio |
| 8 | Tests de integración: flow completo con mock registry | Alta | 1.5h | - |
| | **TOTAL** | | **~7.5h** | |

### Orden recomendado

1. Primero 1-5: Crear registry_client.py con todas las funcionalidades
2. Luego 6: Integrar en architect_flow
3. Luego 7-8: Tests

---

## 🔮 Roadmap (NO implementar ahora)

| Item | Descripción | Pre-requisito |
|---|---|---|
| **mcpmarket.com support** | Agregar fuente de descubrimiento adicional | search() actual funcionando |
| **Ejecución real de servidores MCP** | En lugar de parsear README, ejecutar servidor y hacer tools/list | Soporte de instalación de dependencias (npx/pip) |
| **Auto-activación post-config** | Después de que usuario configura credenciales, marcar is_active=True | UI de configuración de integraciones |
| **Streaming de tools** | Descubrimiento progresivo mientras usuario escribe | - |
| **Caché local de registry** | Evitar calls repetidos al registry externo | TTL cache ~1 hora |
| **Verificación de salud post-import** | Health check automático del servidor importado | MCP Pool con capacidad de health check |
