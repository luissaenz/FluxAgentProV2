# 🧠 ANÁLISIS TÉCNICO — [atg] — Paso 1: Mejora de la Infraestructura de Herramientas

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `src/crews/base_crew.py` existe | `ls src/crews` | ✅ | `src/crews/base_crew.py` |
| 2 | `src/crews/factory.py` existe | `ls src/crews` | ✅ | `src/crews/factory.py` |
| 3 | `src/tools/mcp_pool.py` existe | `ls src/tools` | ✅ | `src/tools/mcp_pool.py` |
| 4 | `MCPPool` clase existe | `cat src/tools/mcp_pool.py` | ✅ | Línea 35 |
| 5 | `org_mcp_servers` tabla existe | `ls supabase/migrations` | ✅ | `005_org_mcp_servers.sql` |
| 6 | `AgentFactory.create_agent` es sync | `cat src/crews/factory.py` | ✅ | Línea 18 |
| 7 | `BaseCrew.run` es sync | `cat src/crews/base_crew.py` | ✅ | Línea 90 |
| 8 | `BaseCrew._resolve_tools` existe | `cat src/crews/base_crew.py` | ✅ | Línea 78 (pero no se usa en `run`) |

**Discrepancias encontradas:**

1.  **Desajuste Async/Sync**: `MCPPool.get_tools` es `async`, pero `AgentFactory.create_agent` y `BaseCrew.run` son `sync`. No se puede llamar a un método async desde uno sync sin bloquear el loop o usar `asyncio.run`.
    - **Resolución**: Convertir `AgentFactory.create_agent` y `BaseCrew.run` en métodos `async`. Esto es coherente con el roadmap de agentes avanzados que requieren E/S no bloqueante para MCP y APIs externas.
2.  **Redundancia de Resolución**: `BaseCrew` tiene un método `_resolve_tools` que no se utiliza, mientras que `AgentFactory.create_agent` implementa su propia lógica de resolución de herramientas.
    - **Resolución**: Unificar la lógica de resolución en `AgentFactory` o hacer que `BaseCrew` pase las herramientas ya resueltas a la factory. Se optará por potenciar `AgentFactory`.
3.  **Formato de Herramientas MCP**: El plan menciona el formato `mcp:{server}:{tool}`, pero `MCPPool.get_tools` devuelve una lista completa de herramientas de un servidor.
    - **Resolución**: Implementar un filtro en la resolución para extraer solo la herramienta específica solicitada del adaptador MCP.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ **Schema**: La tabla `org_mcp_servers` ya existe (Migración 005). Define la conexión a servidores externos.
- ✅ **RLS policies**: Existe la política `tenant_isolation_org_mcp_servers` que asegura que una org solo vea sus propios servidores.
- ✅ **Integridad referencial**: `org_id` está correctamente vinculado a `organizations`.
- ✅ **Tipos de datos**: `args` es `JSONB`, lo cual es flexible para diferentes comandos (node, python, npx).

---

## 2️⃣ Análisis de Código (ETAPA 2)

- ✅ **Funciones/clases nuevas**:
    - `AgentFactory.create_agent` pasará a ser `async`.
    - Nueva lógica en la resolución de herramientas para detectar el prefijo `mcp:`.
- ✅ **Patrones**: Se mantiene el uso de `crewai.Agent`. Se introduce la inyección de herramientas instanciadas dinámicamente en lugar de solo clases.
- ✅ **Modularidad**: La lógica de MCP permanece encapsulada en `MCPPool`. La factory solo consume el pool.
- ✅ **Imports**:
    - En `base_crew.py`: `from ..tools.mcp_pool import MCPPool`.
    - En `factory.py`: `from src.tools.mcp_pool import MCPPool`.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ **Middleware**: No hay cambios en middleware, pero la resolución de herramientas requiere un `org_id` válido, el cual es provisto por el contexto de ejecución.
- ✅ **Flujos**:
    1. `BaseCrew` recibe `org_id` y `role`.
    2. Carga config de la DB.
    3. Llama a `AgentFactory.create_agent(async)`.
    4. La factory itera sobre `allowed_tools`.
    5. Si el nombre empieza con `mcp:`, divide en `server` y `tool_name`.
    6. Llama a `MCPPool.get().get_tools(org_id, server)`.
    7. Filtra la herramienta por nombre y la añade a la lista.
- ✅ **Error handling**: Si un servidor MCP falla, el `MCPPool` ya tiene circuit breaker y reintentos. La factory debe loguear si una herramienta específica no se encuentra en el servidor.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- ✅ **Alineación**: El plan es realizable, pero la transición a async es crítica para no degradar el performance del servidor FastAPI al conectar con servidores MCP externos.
- ✅ **DX & Tooling (OBLIGATORIO):**

### Herramienta Propuesta: `fap mcp-probe`
- **Qué automatiza**: La verificación manual de que un servidor MCP configurado en la base de datos es accesible y responde correctamente con la lista de herramientas esperada.
- **Tipo**: Comando CLI (añadido a `src/cli/main.py`).
- **Cómo se usa**: `uv run fap mcp-probe --org <org_id> --server <server_name>`
- **Impacto para el usuario final**: El desarrollador/admin puede diagnosticar problemas de conexión (errores de comando, permisos de node/python, etc.) sin tener que disparar un workflow completo de agentes.
- **Prioridad**: Tarea 0.

---

## 5️⃣ Criterios de Aceptación

- ✅ [CODE] `AgentFactory.create_agent` es una corrutina (`async def`).
- ✅ [CODE] `BaseCrew.run` es una corrutina (`async def`).
- ✅ [CODE] La resolución de herramientas en `AgentFactory` maneja el prefijo `mcp:server_name:tool_name`.
- ✅ [CODE] Se inyectan instancias de herramientas (objects) en el constructor de `Agent`.
- ✅ [DX] El comando `fap mcp-probe` está implementado y lista las herramientas de un servidor MCP exitosamente.

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Bloqueo de Event Loop | Media | Uso de `asyncio.run` o llamadas sync a `MCPPool`. | Asegurar que toda la cadena de llamadas sea `async`. |
| Incompatibilidad de Herramientas | Alta | Herramientas MCP no compatibles con el formato de CrewAI. | `MCPPool` ya usa `MCPServerAdapter` de `crewai-tools`, lo que minimiza el riesgo. |
| Timeouts en cascada | Media | Servidor MCP lento retrasa la creación del agente. | Implementar timeouts agresivos en la Factory adicionales a los del Pool. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Implementar `src/cli/mcp_commands.py` y `mcp-probe` | FULLSTACK/DX | Media | 1.5h | Ninguna |
| 1 | Refactorizar `AgentFactory.create_agent` a async + Soporte `mcp:` | CODE | Alta | 2h | Tarea 0 |
| 2 | Refactorizar `BaseCrew.run` y `run_async` para usar la nueva factory | CODE | Media | 1h | Tarea 1 |
| 3 | Eliminar `BaseCrew._resolve_tools` (redundante) | CODE | Baja | 0.5h | Tarea 2 |
| 4 | Validar con test unitario de resolución de herramientas MCP | FULLSTACK | Media | 1h | Tareas 1-2 |

**Tiempo total estimado:** 6 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Caché de Herramientas**: Cachear no solo la conexión al servidor MCP, sino las instancias de herramientas resueltas para evitar el overhead de filtrado en cada creación de agente.
- **Soporte SSE**: Expandir `MCPPool` para soportar transporte SSE (actualmente enfocado en Stdio).
- **Auto-Discovery**: Herramienta CLI que escanee el filesystem en busca de servidores MCP y sugiera la configuración para la DB.
