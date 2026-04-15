# Análisis Técnico: MCPRegistryClient — Definición

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `org_mcp_servers` existe | `grep -r "CREATE TABLE.*org_mcp_servers" supabase/migrations/` | ✅ | supabase/migrations/005_org_mcp_servers.sql:9, columnas: id, org_id, name, command, args, secret_name, is_active |
| 2 | Tabla `service_catalog` existe | `grep -r "CREATE TABLE.*service_catalog" supabase/migrations/` | ✅ | supabase/migrations/024_service_catalog.sql:8, columnas: id, name, category, auth_type, base_url, required_secrets, etc. |
| 3 | Tabla `service_tools` existe | `grep -r "CREATE TABLE.*service_tools" supabase/migrations/` | ✅ | supabase/migrations/024_service_catalog.sql:58, columnas: id, service_id, name, input_schema, output_schema, execution |
| 4 | `httpx` disponible en dependencias | `grep "httpx" pyproject.toml` | ✅ | pyproject.toml:23, "httpx>=0.28.0" |
| 5 | MCPPool maneja conexiones a `org_mcp_servers` | `grep -A5 "org_mcp_servers" src/tools/mcp_pool.py` | ✅ | src/tools/mcp_pool.py:122-132, query a org_mcp_servers para config |
| 6 | IntegrationResolver retorna `not_found` en ResolutionResult | `grep "not_found" src/flows/integration_resolver.py` | ✅ | src/flows/integration_resolver.py:25, campo not_found en ResolutionResult |
| 7 | ArchitectFlow procesa `not_found` en post-resolver | `grep -A10 "_build_resolution_response" src/flows/architect_flow.py` | ✅ | src/flows/architect_flow.py:429-463, construye respuesta para not_found |
| 8 | `src/mcp/registry_client.py` no existe | `ls src/mcp/registry_client.py` | ✅ | No existe, será archivo nuevo |
| 9 | GitHub MCP Registry API accesible | `curl -s https://registry.modelcontextprotocol.io/v0.1/servers | head -c 100` | ✅ | Respuesta JSON con servidores |
| 10 | `get_service_client()` disponible para queries | `grep "get_service_client" src/db/session.py` | ✅ | src/db/session.py: función exportada |
| 11 | `upsert_secret` en vault para credenciales | `grep "upsert_secret" src/db/vault.py` | ✅ | src/db/vault.py: función definida |
| 12 | Patrón de dataclass para MCPServerInfo | Comparar con dataclasses existentes | ✅ | src/flows/integration_resolver.py:20 usa @dataclass para ResolutionResult |
| 13 | ArquitectFlow puede ser modificado post-resolver | `grep -A5 "resolution.is_ready" src/flows/architect_flow.py` | ✅ | src/flows/architect_flow.py:141-143, lógica condicional para not_found |
| 14 | `MCPServerAdapter` de crewai-tools disponible | `grep "MCPServerAdapter" src/tools/mcp_pool.py` | ✅ | src/tools/mcp_pool.py:149, import exitoso |
| 15 | Políticas RLS en tablas permiten inserts | `grep "service_role" supabase/migrations/024_service_catalog.sql` | ✅ | supabase/migrations/024_service_catalog.sql:46-51, bypass para service_role |
| 16 | `org_service_integrations` para activación TIPO C | `grep "org_service_integrations" supabase/migrations/024_service_catalog.sql` | ✅ | supabase/migrations/024_service_catalog.sql:27, tabla definida |

**Discrepancias encontradas:**

- ✅ VERIFICADO: Todas las tablas y dependencias del plan existen y coinciden con las interfaces reales.
- ❌ DISCREPANCIA: El plan menciona "discover_tools() — parseo de README/docs (no ejecución)" para MVP, pero no especifica cómo parsear README sin ejecutar. Necesita implementación concreta.
- ⚠️ NO VERIFICABLE: La API de GitHub MCP Registry puede cambiar; asumir estabilidad según documentación oficial.

## 1. Diseño Funcional

El paso implementa un mecanismo de "descubrimiento externo" de integraciones MCP cuando el resolver interno no encuentra tools alucinadas. El flujo funcional es:

1. **Trigger**: IntegrationResolver.detecta tools no encontradas (not_found: ["custom_erp_read"])
2. **Búsqueda**: MCPRegistryClient.search("custom_erp") consulta registros externos (GitHub MCP Registry)
3. **Descubrimiento**: Si encuentra servidores, extrae tools vía discover_tools() (parseo de docs para MVP)
4. **Importación**: Usuario elige servidor → importa como TIPO B (org_mcp_servers) o TIPO C (service_catalog + service_tools)
5. **Re-resolución**: Re-ejecuta resolve() → ahora encuentra las tools → workflow se crea exitosamente

**Happy Path:**
- Usuario describe workflow con "leer datos de ERP custom"
- Architect genera tools: ["custom_erp_read"]
- Resolver: not_found=["custom_erp_read"]
- RegistryClient encuentra "Custom ERP MCP Server" en registry
- Usuario confirma importación
- Servidor importado como TIPO B, is_active=False
- Re-resolve encuentra tool → workflow creado

**Edge Cases:**
- Búsqueda no encuentra nada: "No encontré servidores para 'custom_erp'. ¿Tienes URL manual?"
- Múltiples resultados: Presenta lista numerada para selección
- Servidor requiere auth: Importa con auth_required=True, solicita credenciales post-import
- Error de conexión al registry: Fallback a búsqueda manual

**Manejo de Errores:**
- Timeout en registry: "Error conectando al registro externo. Reintenta o proporciona URL manual."
- JSON inválido del registry: Loggea error, retorna lista vacía
- Parseo de README falla: Usa descripción del registry como fallback

## 2. Diseño Técnico

### Componentes Nuevos
- **MCPServerInfo** (dataclass): Modelo para servidores descubiertos
- **MCPRegistryClient** (clase): Lógica de búsqueda y importación

### Interfaces
- `MCPRegistryClient.search(query: str) -> list[MCPServerInfo]`
- `MCPRegistryClient.discover_tools(server: MCPServerInfo) -> list[dict]`
- `MCPRegistryClient.import_as_type_b(server, org_id) -> str`
- `MCPRegistryClient.import_as_type_c(server, org_id) -> list[str]`

### Modelos de Datos
- **TIPO B**: Inserta en `org_mcp_servers` con is_active=False
- **TIPO C**: Crea provider en `service_catalog`, tools en `service_tools` con execution.type="mcp"

### Integración en ArquitectFlow
Modificación en `_run_crew()` post-resolver:
```python
if not resolution.is_ready and resolution.not_found:
    registry = MCPRegistryClient()
    discovered = await registry.search_for_not_found(resolution.not_found)
    if discovered:
        return self._build_discovery_response(discovered, resolution)
```

### Dependencias
- httpx: Para HTTP requests al registry
- mcp: Para tipos de tool definitions
- crewai-tools: Ya usado en MCPPool

## 3. Decisiones

- **Decisión 1:** discover_tools() parsea README/docs sin ejecutar servidor para MVP — reduce riesgos de seguridad y dependencias.
- **Decisión 2:** Import como TIPO B por defecto — MCPPool ya maneja conexiones a org_mcp_servers, más simple que TIPO C.
- **Decisión 3:** Usuario debe confirmar importación — evita llamadas automáticas a registros externos.
- **Decisión 4:** Servidores importados inactivos por defecto — requieren configuración manual antes de uso.
- **Decisión 5:** Solo GitHub MCP Registry para MVP — fuente oficial, API estable.

## 4. Criterios de Aceptación

- MCPRegistryClient puede buscar "google_sheets" y retornar al menos 1 servidor de GitHub Registry
- discover_tools() parsea correctamente una URL de repo y extrae lista de tools del README
- import_as_type_b() inserta fila en org_mcp_servers con is_active=False
- import_as_type_c() crea provider en service_catalog y tools en service_tools
- ArquitectFlow integra búsqueda externa post-resolver sin romper flujo existente
- IntegrationResolver no se modifica (como especificado en plan)
- Tools importadas son detectables por resolve() en re-ejecución

## 5. Riesgos

- **Riesgo Técnico:** API de GitHub Registry cambia formato — mitigación: wrapper con validación de respuesta
- **Riesgo de Seguridad:** Parseo de READMEs externos podría contener código malicioso — mitigación: solo texto, no ejecución
- **Riesgo de Integración:** Conflictos con futuras expansiones de service_catalog — mitigación: usar category="external_mcp"
- **Riesgo de Rendimiento:** Llamadas HTTP a registry agregan latencia — mitigación: timeout de 10s, cache opcional futuro
- **Riesgo de Usuario:** Sobrecarga de opciones si muchos resultados — mitigación: limitar a top 5, permitir búsqueda refinada

## 6. Plan

- **Tarea 1:** Crear MCPServerInfo dataclass + MCPRegistryClient clase base — 30min (Baja)
- **Tarea 2:** Implementar search() contra GitHub MCP Registry con httpx — 1.5h (Media)
- **Tarea 3:** Implementar discover_tools() — parseo de README/docs sin ejecución — 2h (Media)
- **Tarea 4:** Implementar import_as_type_b() e import_as_type_c() — 1h (Media)
- **Tarea 5:** Modificar ArquitectFlow para integrar búsqueda externa post-resolver — 1h (Media)
- **Tarea 6:** Tests unitarios para RegistryClient + mocks de HTTP/DB — 1.5h (Media)
- **Total estimado:** 7.5h

## 🔮 Roadmap
- Expansión a mcpmarket.com y smithery.ai como fuentes adicionales
- Cache local de resultados de búsqueda para reducir latencia
- Auto-activación de servidores importados con wizard de configuración
- Soporte para servidores SSE además de Stdio
- Verificación de compatibilidad de versiones MCP