# Análisis Unificado: Integración de FluxAgentPro (FAP) con Claude vía Model Context Protocol (MCP)

## Introducción
Este documento unifica los análisis de agentes Kilo y ATG para identificar elementos faltantes y proponer implementaciones para conectar FluxAgentPro-v2 con agentes externos como Claude mediante MCP. El objetivo es transformar FAP en un sistema agéntico operable por LLMs externos, respetando las restricciones de CLAUDE.md (código CrewAI protegido).

## Estado Actual de la Infraestructura
- **Backend:** FastAPI con rutas para webhooks, tareas, flujos, agentes, etc. Autenticación JWT Supabase con soporte multitenant (RLS). Flujos dinámicos registrados vía FlowRegistry. Soporte múltiple LLM (incluyendo Claude/Anthropic).
- **Frontend:** Next.js dashboard interactivo.
- **Código Protegido (No Modificar):** `src/crews/`, `src/flows/multi_crew_flow.py`, tests relacionados con CrewAI.
- **Código Permitido:** `src/api/`, `src/flows/base_flow.py`, `src/flows/registry.py`, `src/flows/coctel_flows.py`, `src/flows/state.py`, `src/db/`, `src/events/`, `src/services/`, etc.
- **Limitaciones para Agentes Externos:**
  | Componente | Rol Actual | Limitación |
  | :--- | :--- | :--- |
  | MCP Pool | Cliente | Consume herramientas externas pero no se expone a sí mismo. |
  | FlowRegistry | Catálogo Interno | No tiene interfaz de descubrimiento compatible con MCP. |
  | TenantClient | Aislamiento RLS | Requiere inyección explícita de `org_id` en cada sesión. |
  | BaseFlow | Orquestador | Validación manual; falta definición de esquemas JSON tipados. |

## Elementos Faltantes (Roadmap de Implementación)
1. **Servidor MCP (Entry Point):** Binario/script (ej. `src/mcp/server.py`) implementando servidor MCP.
   - Transporte Stdio: Para integración local con Claude Desktop.
   - Transporte SSE: Para agentes web/dashboards externos.
2. **Traductor de Herramientas (Flow-to-Tool):** Módulo que convierte FlowRegistry en herramientas MCP.
   - Descubrimiento dinámico: Escanear flows registrados.
   - Generación de esquemas: Mapear argumentos de flows a parámetros MCP usando Pydantic.
   - Metadatos: Descripciones claras para LLMs.
3. **Puente de Ejecución Multitenant (`mcp_bridge.py`):** Controlador de orquestación.
   - Captura de contexto: Recibir `org_id` (variable entorno o comando inicial).
   - Instanciación de Flow: Crear instancia correcta según nombre de herramienta.
   - Manejo de resultados: Formatear output como `TextContent` o `ImageContent` MCP.
4. **Migración a Esquemas Tipados:** Usar Pydantic en flows para auto-generar JSON Schemas requeridos por MCP.
5. **Configuración MCP:** Extender `src/config.py` con campos como `mcp_server_url`, flags para habilitar MCP.
6. **Integración con Claude:** Configurar Claude (Desktop/API) para conectar al MCP server; usar `anthropic_api_key` existente.
7. **Autenticación Segura:** Validar JWT Supabase en MCP server para acceso autorizado.
8. **Integración con Dashboard:** Endpoint SSE en Next.js para configuración/visualización MCP.

## Propuestas de Implementación
- **Ubicación:** Crear `src/mcp/` para módulos MCP (server.py, tools.py, bridge.py).
- **SDK MCP:** Usar `@modelcontextprotocol/sdk` para servidor; herramientas llaman a `src/api/routes/` para reutilizar lógica.
- **Ejemplo de Herramienta:** `ejecutar_flujo(org_id, flow_name, input_data)` valida auth y ejecuta flow.
- **Lifespan en FastAPI:** Extender `src/api/main.py` para iniciar MCP server junto con la app.
- **Pruebas:** Ejecutar MCP server localmente; configurar Claude Desktop.
- **Compatibilidad:** Asegurar integración sin modificar código protegido; usar flows permitidos.

## Desafíos y Decisiones Pendientes
- **Gestión de Identidad (Auth):** FAP es multi-empresa.
  - **Decisión Recomendada:** Opción A - Sesión MCP por organización (argumento CLI para seguridad).
  - Alternativa: Herramienta `switch_organization` si se requiere dinamismo.
- **Modo de Ejecución:**
  - **Síncrono:** Agente espera fin de flow (flows rápidos).
  - **Asíncrono:** Devolver `task_id`; agente monitorea estado (ideal para HITL).
- **Seguridad:** Evitar exposición de datos sensibles; validar tokens en cada llamada MCP.
- **Escalabilidad:** Manejar múltiples sesiones MCP concurrentes.

## Conclusión
Esta integración permitirá a Claude operar FAP como agente externo, expandiendo el sistema agéntico. Implementar incrementalmente: servidor MCP básico primero, luego herramientas y autenticación. Verificar con pruebas HITL y flujos existentes.

*Análisis unificado generado por agentes Kilo y ATG - FAP v2 Fase Arquitectura Agéntica.*