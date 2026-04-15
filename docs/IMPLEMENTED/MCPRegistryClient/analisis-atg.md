# 🧠 ANÁLISIS TÉCNICO: PASO 1 - MCPRegistryClient

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Directorio `src/mcp/` | `ls src/mcp/` | ✅ | Existe, contiene `server.py`, `tools.py`, etc. |
| 2 | Archivo `src/flows/architect_flow.py` | `ls src/flows/` | ✅ | Existe y es funcional. |
| 3 | Clase `ResolutionResult` con `not_found` | `cat src/flows/integration_resolver.py` | ✅ | Definida en línea 19. |
| 4 | Tabla `org_mcp_servers` | `cat supabase/migrations/005_...` | ✅ | Existe. Columnas: `name`, `command`, `args`, `is_active`. |
| 5 | Tabla `service_catalog` | `cat supabase/migrations/024_...` | ✅ | Existe. Columnas: `id`, `name`, `category`, `auth_type`, `base_url`. |
| 6 | Tabla `service_tools` | `cat supabase/migrations/024_...` | ✅ | Existe. Columnas: `id`, `service_id`, `name`, `input_schema`, `execution`, `tool_profile`. |
| 7 | Función `get_service_client` | `grep -r "get_service_client" src/` | ✅ | `src/db/session.py:48`. |
| 8 | Dependencia `httpx` | `cat pyproject.toml` | ✅ | `httpx>=0.28.0` presente. |
| 9 | Método `_build_resolution_response` | `cat src/flows/architect_flow.py` | ✅ | Línea 377, listo para inyección de lógica. |
| 10 | WorkflowDefinition | `cat src/flows/architect_flow.py` | ✅ | Importado y usado para validación de JSON. |
| 11 | `org_service_integrations` | `cat supabase/migrations/024_...` | ✅ | Necesaria para `import_as_type_c` (activación). |
| 12 | Pattern matching en `IntegrationResolver` | `cat src/flows/integration_resolver.py` | ✅ | Filtra por 0.6/0.7 ratio. `not_found` se llena correctamente. |

**Discrepancias encontradas:**
1. **Firma de `import_as_type_c`**: El plan propone `execution: {"type": "mcp", "server": server.name}`. Sin embargo, en `service_tools` (Migración 024) la columna `execution` es `JSONB`. El esquema real debe seguir el patrón de otros conectores si existen.
   - *Resolución*: Mantener el formato propuesto pero asegurar que `input_schema` y `output_schema` sean objetos vacíos si no se descubren.
2. **Path de `get_service_client`**: El plan asume que está disponible globalmente. 
   - *Resolución*: Importar explícitamente desde `src.db.session`.
3. **Manejo de `not_found` en `ArchitectFlow`**: El flujo actual retorna inmediatamente en `_build_resolution_response`.
   - *Resolución*: Modificar el flujo principal para que, si hay `not_found`, invoque a `MCPRegistryClient` antes de llamar a `_build_resolution_response`.

## 1. Diseño Funcional
- **Búsqueda Externa**: Cuando `IntegrationResolver` no encuentra una tool, se extrae el prefijo (ej: `google_sheets` de `google_sheets_read`) y se consulta el GitHub MCP Registry.
- **Descubrimiento Seguro (MVP)**: No se ejecuta el servidor. Se parsea la metadata del repo (Markdown/JSON) para extraer nombres de tools y descripciones.
- **Confirmación de Usuario**: El sistema propone integraciones encontradas. El usuario debe confirmar la "instalación".
- **Estado Inicial**: Los servidores importados (Tipo B) se crean como `is_active: False`. Las integraciones Tipo C se crean en `pending_setup`.

## 2. Diseño Técnico
- **Nuevo Componente**: `src/mcp/registry_client.py`.
  - Clase `MCPRegistryClient` con métodos `search`, `discover_tools`, `import_as_type_b`, `import_as_type_c`.
- **Modificación**: `src/flows/architect_flow.py`.
  - Inyectar búsqueda en el punto donde `resolution.not_found` es detectado.
  - Nuevo mensaje de respuesta: `external_integrations_found`.

## 3. Decisiones
1. **Parseo vs Ejecución**: Se decide parsear el README/metadata en lugar de ejecutar el servidor Stdio para evitar vulnerabilidades de ejecución de código arbitrario durante el descubrimiento.
2. **GitHub Registry como Única Fuente**: Centraliza el descubrimiento en la fuente oficial de MCP para garantizar estabilidad del esquema JSON.
3. **Importación Silente pero Inactiva**: Se inserta el registro en DB pero no se marca como activo para forzar al administrador a revisar la configuración (credenciales, etc.) en el dashboard.

## 4. Criterios de Aceptación
- [ ] `MCPRegistryClient.search()` retorna resultados válidos desde el registro de GitHub.
- [ ] `discover_tools()` extrae al menos el nombre de la tool desde la descripción del servidor.
- [ ] `import_as_type_b` crea un registro correcto en `org_mcp_servers` con `is_active=False`.
- [ ] `import_as_type_c` crea una entrada en `service_catalog` y `service_tools`.
- [ ] `ArchitectFlow` incluye la sección `discovered` en su respuesta cuando hay matches externos.

## 5. Riesgos
- **Rate Limit de GitHub API**: La consulta al registro podría ser limitada si hay muchas peticiones. Mitigación: Uso de cache local o timeouts agresivos.
- **Formato inconsistente de README**: El descubrimiento por parseo puede fallar si el repo no sigue convenciones. Mitigación: `discover_tools` debe ser resiliente y retornar lista vacía si no detecta patrón.

## 6. Plan
| Tarea | Complejidad | Tiempo | Dependencias |
|---|---|---|---|
| Crear `src/mcp/registry_client.py` y `MCPServerInfo` | Baja | 1h | Ninguna |
| Implementar `search()` (HTTPX + GitHub API) | Media | 2h | `httpx` |
| Implementar `discover_tools()` (Regex/Parsing) | Media | 2h | `search()` |
| Implementar lógica de importación (Type B/C) | Media | 1.5h | DB Schama |
| Integración en `ArchitectFlow` | Media | 1h | `MCPRegistryClient` |
| **Total** | | **7.5h** | |

## Sección Final: 🔮 Roadmap
- Integración con Smithery.ai y MCPMarket.com.
- Ejecución en Sandbox (Docker/Wasm) para descubrimiento real via `tools/list` (handshake completo).
- Auto-configuración de secretos si el servidor MCP provee un esquema de configuración compatible con el Vault de LUMIS.
