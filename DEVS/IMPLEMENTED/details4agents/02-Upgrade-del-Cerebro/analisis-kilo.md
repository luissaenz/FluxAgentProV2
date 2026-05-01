# 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|--------------|--------|-----------|
| 1 | Archivo `src/flows/architect_flow.py` existe | glob en src/flows | ✅ | arquitect_flow.py presente |
| 2 | Clase `ArchitectFlow` existe | grep class ArchitectFlow | ✅ | línea 51 |
| 3 | Método `_execute_architect_agent` existe | grep def _execute_architect_agent | ✅ | línea 190 |
| 4 | Task description incluye schema WorkflowDefinition | read líneas 216-267 | ✅ | líneas 224-255 |
| 5 | WorkflowDefinition soporta `allowed_tools` como list[str] | read AgentDefinition | ✅ | línea 21 |
| 6 | AgentFactory resuelve prefijo `mcp:` | read factory.py _parse_mcp_prefix | ✅ | línea 18 |
| 7 | ServiceConnectorTool registrado como `service_connector` | grep @register_tool service_connector | ✅ | línea 37 |
| 8 | MCPPool existe para resolver tools MCP | read factory.py _resolve_mcp_tool | ✅ | línea 83 |
| 9 | Prompt actual no menciona `mcp:` ni `service_connector` | grep en task description | ❌ | no encontrado |
| 10 | Tabla `org_mcp_servers` existe | read migración 005 | ✅ | línea 9 |
| 11 | Tabla `service_tools` existe | read migración 024 | ✅ | línea X |
| 12 | allowed_tools no tiene validadores restrictivos | read AgentDefinition field_validator | ✅ | ninguno para allowed_tools |

**Discrepancias encontradas:**

- El prompt del agente Architect no incluye instrucciones ni ejemplos para definir herramientas MCP (prefijo `mcp:`) o integraciones (`service_connector` en allowed_tools), lo que requiere actualización según el paso 2 del plan.
- WorkflowDefinition ya soporta las nuevas capacidades sin cambios necesarios en el schema.

---

# 1️⃣ Análisis de Datos (ETAPA 1)

No hay cambios en schema de DB requeridos. Las tablas existentes (`org_mcp_servers`, `service_tools`) ya soportan MCP e integraciones. El schema de WorkflowDefinition permite `allowed_tools` con cualquier string, incluyendo `mcp:server:tool` y `service_connector`.

- ✅ Schema: WorkflowDefinition ya incluye `allowed_tools: list[str]`
- ✅ Integridad referencial: No aplica cambios
- ✅ RLS policies: Ya aplicables en tablas MCP e integraciones
- ✅ Índices necesarios: Ya existen en migraciones
- ✅ Tipos de datos: Sin problemas o incompatibilidades

---

# 2️⃣ Análisis de Código (ETAPA 2)

Modificar el método `_execute_architect_agent` en `architect_flow.py` para expandir el task description con ejemplos de herramientas MCP e integraciones.

- ✅ Funciones/clases nuevas: Ninguna
- ✅ Patrones: Se mantiene el patrón existente de task description
- ✅ Modularidad: Cambio localizado en un método
- ✅ Calidad: Sin cambios en complejidad ciclomática
- ✅ Imports y dependencias: Sin nuevos

---

# 3️⃣ Análisis de Backend (ETAPA 3)

No hay cambios en endpoints ni middleware. El flujo de ejecución del ArchitectFlow permanece igual: genera JSON, valida con WorkflowDefinition, crea bundle.

- ✅ APIs/endpoints: Sin cambios
- ✅ Middleware: Sin cambios
- ✅ Flujos: Sin cambios
- ✅ Contratos: Sin cambios
- ✅ Error handling: Sin cambios

---

# 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

El cambio es coherente con la arquitectura. El Architect ahora generará workflows que usan herramientas MCP e integraciones, resueltas por AgentFactory.

- ✅ Flujo completo: DB → Architect → JSON válido → Bundle
- ✅ Coherencia: Decisiones apoyan el plan de Fase V
- ✅ Alineación: Plan realizable con código existente
- ✅ Gaps: Ninguno identificado
- ✅ **DX & Tooling (OBLIGATORIO):**

### Herramienta Propuesta: validate_architect_prompt
- **Qué automatiza:** Verifica que el system prompt del Architect incluye ejemplos válidos de allowed_tools para MCP e integraciones, y sugiere actualizaciones si faltan.
- **Tipo:** script
- **Cómo se usa:** python scripts/validate_architect_prompt.py --check
- **Impacto para el usuario final:** Reduce errores al actualizar el prompt manualmente, asegurando que el Architect reconozca las nuevas capacidades.
- **Prioridad:** Tarea 0 — implementar antes de modificar el prompt

---

# 5️⃣ Criterios de Aceptación

Lista binaria (sí/no) verificable:
- ✅ [DATA] WorkflowDefinition permite allowed_tools con strings arbitrarias
- ✅ [CODE] Método _execute_architect_agent actualizado con ejemplos en task description
- ✅ [BACKEND] ArchitectFlow ejecuta sin errores con nuevos ejemplos
- ✅ [FULLSTACK] Workflows generados incluyen mcp: y service_connector en allowed_tools
- ✅ [DX] Herramienta validate_architect_prompt ejecuta sin errores y detecta prompts incompletos

---

# 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| Prompt demasiado largo causa truncamiento por LLM | Media | Agregar muchos ejemplos | Mantener ejemplos concisos, validar con pruebas |
| Ejemplos incorrectos en prompt | Baja | Errores de sintaxis en mcp: o service_connector | Usar la herramienta DX para validar ejemplos contra AgentFactory |
| AgentFactory no resuelve tools nuevas | Baja | Dependencias opcionales faltantes | Verificar imports en runtime |

---

# 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|-------|----------|-------------|-------------|-------------|
| 0 | **DX & Tooling**: Implementar validate_architect_prompt | FULLSTACK/DX | Media | 1h | Ninguna |
| 1 | Actualizar task description en _execute_architect_agent con ejemplos de mcp: y service_connector | CODE | Baja | 30m | Tarea 0 |

**Tiempo total estimado:** 1.5 horas

---

# 🔮 Roadmap (NO implementar ahora)

- Integración de ejemplos dinámicos en el prompt basados en herramientas registradas en runtime.
- Validación automática del JSON generado contra herramientas disponibles.
- Expansión del schema para tipos específicos de tools (mcp, integration, etc.) para mejor validación.