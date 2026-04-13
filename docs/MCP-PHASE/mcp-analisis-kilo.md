# Análisis Exhaustivo del Proyecto FluxAgentPro-v2 para Integración con Claude vía MCP

## Estructura Actual del Proyecto
- **Backend:** FastAPI con rutas para webhooks, tareas, flujos, agentes, etc. Autenticación JWT Supabase. Flujos dinámicos registrados vía decorators. Soporte múltiple LLM (incluyendo Claude/Anthropic).
- **Frontend:** Next.js con dashboard interactivo.
- **Código Protegido (No Modificar):** `src/crews/`, `src/flows/multi_crew_flow.py`, `tests/` relacionados con CrewAI.
- **Código Permitido:** `src/api/`, `src/flows/base_flow.py`, `src/flows/registry.py`, `src/flows/coctel_flows.py`, `src/flows/state.py`, `src/db/`, `src/events/`, `src/services/`, etc.

## MCP (Model Context Protocol)
- Protocolo abierto de Anthropic para conectar agentes AI con herramientas externas.
- Claude soporta MCP nativamente; permite acceso a herramientas vía servidores MCP (ej. ejecutar flujos, consultar DB).
- Arquitectura: MCP Servers exponen herramientas; MCP Clients (como Claude) las consumen.

## Elementos Faltantes para Integración con Claude vía MCP
1. **MCP Server:** Servidor que exponga APIs del sistema como herramientas MCP (ej. `ejecutar_flujo`, `consultar_estado_tarea`, `listar_flujos_disponibles`).
2. **Herramientas MCP Específicas:** Llamadas a endpoints existentes en `src/api/routes/` (flujos, tareas, agentes).
3. **Configuración MCP:** Extender `src/config.py` para incluir URLs/endpoints MCP si es remoto; o ejecutar localmente.
4. **Integración con Claude:** Configurar Claude (Desktop/API) para conectar al MCP server; usar `anthropic_api_key` existente.
5. **Autenticación Segura:** Asegurar que el MCP server valide JWT de Supabase para acceso autorizado.
6. **Transporte MCP:** Soporte para HTTP/SSE (recomendado para producción) o stdio (local).

## Propuestas de Implementación (Siguiendo CLAUDE.md)
- Crear `src/mcp/server.py`: Usar `@modelcontextprotocol/sdk` para definir servidor MCP con herramientas que llamen a `src/api/routes/`.
- Agregar `src/mcp/tools.py`: Implementar herramientas como `ejecutar_flujo(org_id, flow_name, input_data)` que valide auth y llame a API.
- Extender `src/api/main.py`: Incluir lifespan para iniciar MCP server junto con FastAPI.
- Actualizar `src/config.py`: Agregar campos opcionales como `mcp_server_url` o flags para habilitar MCP.
- Para pruebas: Ejecutar MCP server localmente y configurar Claude Desktop para conectarlo.
- Verificación: Asegurar compatibilidad con CrewAI sin modificar código protegido; usar flujos permitidos para integración.

Esto permitiría a Claude interactuar directamente con FluxAgentPro-v2 como un agente externo, expandiendo el sistema agéntico sin violar restricciones.