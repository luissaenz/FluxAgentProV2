# 🗺️ Plan de Implementación: Generación Avanzada de Agentes (Fase V)

Este plan detalla los cambios necesarios para habilitar la generación de agentes con integraciones (Tipo C), soporte MCP (Stdio/SSE) y workflows multi-agente dinámicos.

---

## 1. Análisis de Impacto y Cambios

### A. ArchitectFlow (Generador)
- **Prompt Engineering**: Actualizar el `system_prompt` para que el arquitecto reconozca:
    - Convención `mcp:{server}:{tool}` para herramientas de Model Context Protocol.
    - Uso de `service_connector` para integraciones basadas en HTTP/Catalog.
    - Orquestación secuencial en `steps` para multi-agentes.
- **Validación**: Ajustar `WorkflowDefinition` para permitir los nuevos formatos de herramientas.

### B. Infraestructura de Ejecución (BaseCrew & AgentFactory)
- **Bridging MCP**: Modificar `BaseCrew._resolve_tools` para detectar el prefijo `mcp:` y utilizar `MCPPool` para instanciar las herramientas de CrewAI dinámicamente.
- **Inyección de Integraciones**: Asegurar que `AgentFactory` pueda configurar la `ServiceConnectorTool` con el `org_id` y `tool_id` correctos.

### C. Registro de Workflows (DynamicWorkflow)
- **Pasaje de Contexto**: Refinar cómo los resultados del `Paso N` se inyectan en el `Paso N+1` dentro de `DynamicWorkflow._run_crew`.
- **Manejo de Aprobaciones**: Validar que `requires_approval` genere las entradas correctas en la tabla `snapshots` para el flujo de HITL.

---

## 2. Plan de Acción (Paso a Paso)

### Paso 1: Mejora de la Infraestructura de Herramientas
1.  **Modificar `src/crews/base_crew.py`**:
    - Importar `MCPPool`.
    - Actualizar `_resolve_tools` para manejar herramientas MCP.
2.  **Modificar `src/crews/factory.py`**:
    - Asegurar que la creación de agentes soporte herramientas instanciadas (no solo clases).

### Paso 2: Upgrade del Cerebro (ArchitectFlow)
1.  **Actualizar `src/flows/architect_flow.py`**:
    - Expandir el bloque de instrucciones del agente `Workflow Architect`.
    - Proporcionar ejemplos de cómo definir herramientas MCP e Integraciones.
    - Asegurar que el output JSON siga el schema `WorkflowDefinition` con las nuevas capacidades.

### Paso 3: Validación y Pruebas (La "Suite de los 6 Escenarios")
1.  **Escenario 1 (Simple)**: Agente "Greeter".
2.  **Escenario 2 (Integración)**: Agente "Slack Notifier" usando `service_connector`.
3.  **Escenario 3 (MCP)**: Agente "File Manager" usando un servidor MCP local.
4.  **Escenario 4 (Híbrido)**: Agente que busca en Google (MCP) y notifica por CRM (Integración).
5.  **Escenario 5 (Multi-Agente)**: Flujo Investigador -> Escritor -> Corrector.
6.  **Escenario 6 (Full Stack)**: Flujo complejo con todas las capacidades anteriores.

### Paso 4: Documentación y Cierre
1.  Actualizar `DEVS/phase-state.md` con los nuevos "Contratos Técnicos".
2.  Realizar la certificación de la Fase V.

---

## 3. Criterios de Aceptación
- [ ] El `ArchitectFlow` genera JSONs válidos para los 6 escenarios propuestos.
- [ ] Los bundles generados se importan sin errores en la base de datos.
- [ ] La `BaseCrew` es capaz de resolver una herramienta con prefijo `mcp:` consultando el `MCPPool`.
- [ ] El `DynamicWorkflow` ejecuta múltiples pasos secuenciales pasando el contexto entre ellos.

---

**Estado:** 📅 Pendiente de Inicio (Esperando aprobación del plan)
**Responsable:** Antigravity (Context Architect)
