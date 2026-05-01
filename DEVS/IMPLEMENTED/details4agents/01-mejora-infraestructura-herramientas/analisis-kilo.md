# 🧠 PROCESO DE ANÁLISIS TÉCNICO (ANALISTA) v5 — UNIFICADO

## Perfil del Rol
Actúa como **Ingeniero de Software Senior**, Arquitecto de Sistemas y Especialista en Diseño de Producto. **Análisis basado en código fuente real. Busca activamente herramientas y funcionalidades que faciliten la vida al usuario final y automaticen procesos repetitivos (DX).**

## Contexto del Proyecto
Desarrollamos **"FluxAgentPro-v2"**. Disponible:
- **`proyecto-config.json`** (raíz) — fuente de verdad de rutas y convenciones (NOTA: archivo no encontrado en raíz, asumiendo rutas estándar basadas en estructura del proyecto)
- **Plan general:** `{project_root}/DEVS/plan.md`
- **Contexto de fase:** `{project_root}/DEVS/phase-state.md`
- **Código fuente:** `src` (fuente de verdad)
- **Migraciones:** `supabase/migrations` (schema real de DB)

> [!IMPORTANT]
> **ANTES DE EJECUTAR:** Leer `proyecto-config.json`. Todas las rutas salen de ahí. (Archivo no encontrado, procediendo con inferencia de estructura del proyecto)

---

## Entradas Obligatorias

Solo 2 parámetros:
1. **[AGENTE]** → kilo
2. **[PASO]** → paso 1 (Mejora de la Infraestructura de Herramientas)

> [!IMPORTANT]
> **NO se pide área explícita.** Análisis cubre automáticamente:
> - `data` → schema, integridad, RLS
> - `code` → patrones, calidad, modularidad
> - `backend` → APIs, middleware, contratos
> - `fullstack` → coherencia end-to-end + UX + DX

---

## Prohibiciones Absolutas
- **NO** escribas código de implementación. Entregable = DOCUMENTO DE ANÁLISIS.
- **NO** preguntes qué hacer. Lee plan, phase-state y paso asignado. Luego EJECUTA.
- **NO** analices TODO el sistema. Solo el paso específico — pero SÍ TODO el paso (sub-pasos incluidos).
- **NO** modifiques ningún archivo que no sea el de salida.
- **NO** repitas info que ya esté en `{project_root}/DEVS/phase-state.md`. Referenciala.
- **NO** asumas que función, tabla, clase o patrón existe solo porque el plan lo menciona. VERIFICAR contra código.

---

## Exploración Inicial del Codebase

### Paso 0: Leer `proyecto-config.json`
Archivo no encontrado en raíz. Procediendo con inferencia de rutas basadas en estructura del proyecto observada:
- `paths.backend` = src
- `paths.migrations` = supabase/migrations
- `paths.api_routes` = src/api (no verificado)
- `paths.frontend` = dashboard
- `paths.tests` = tests
- `paths.devs_in_progress` = DEVS/IN_PROGRESS

### Exploración (10-15 min):

**1. Estructura del proyecto:**
- `src/` contiene código Python del backend
- `supabase/migrations/` contiene 30 archivos SQL de migraciones
- `dashboard/` contiene frontend (no explorado en detalle)
- `tests/` contiene tests
- `DEVS/` contiene documentación y estado

**2. Archivos directamente relacionados al paso:**
- `src/crews/base_crew.py`: 215 líneas, clase BaseCrew con método _resolve_tools que resuelve herramientas desde tool_registry
- `src/crews/factory.py`: 59 líneas, clase AgentFactory con método create_agent que resuelve herramientas desde tool_registry

**3. Archivos de referencia (patrones existentes):**
- `src/tools/mcp_pool.py`: 213 líneas, clase MCPPool singleton para conexiones MCP persistentes
- `src/tools/registry.py`: 287 líneas, ToolRegistry para registro y resolución de herramientas

**4. Dependencias:**
- `pyproject.toml`: Proyecto Python con dependencias incluyendo crewai, crewai-tools, mcp, etc.

### Resultado:
Input para §0 y análisis completo. El paso requiere modificación de resolución de herramientas para soportar prefijo `mcp:` y herramientas instanciadas.

---

## Verificación Obligatoria contra Código Fuente

### Qué DEBES verificar:

**A. Tablas y Schema de DB:**
- `agent_catalog` existe en migración 004_agent_catalog.sql
- `org_mcp_servers` existe en migración 005_org_mcp_servers.sql
- Columnas y constraints verificadas contra migraciones

**B. Funciones y Clases:**
- `BaseCrew._resolve_tools` existe y tiene firma correcta
- `AgentFactory.create_agent` existe y resuelve herramientas
- `MCPPool.get_tools` existe y retorna lista de herramientas

**C. Patrones y Convenciones:**
- Resolución de herramientas actual usa tool_registry.get() retornando clase, luego instancia con org_id
- MCPPool es singleton con conexiones persistentes

**D. Dependencias:**
- crewai-tools y mcp incluidos en pyproject.toml

### Formato de Evidencia:
```
✅ VERIFICADO: `agent_catalog` existe (migración 004, línea 5)
❌ DISCREPANCIA: El plan menciona `mcp:` prefijo pero NO está implementado en _resolve_tools
⚠️ NO VERIFICABLE: Asumo que org_mcp_servers tiene columnas correctas — CONFIRMAR migración 005
```

### Umbral Mínimo de Verificación:
Alcance del paso: 2 archivos afectados → ≥ 8 elementos

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_catalog` existe | grep en supabase/migrations/004_agent_catalog.sql | ✅ | migración 004, tabla creada |
| 2 | Tabla `org_mcp_servers` existe | grep en supabase/migrations/005_org_mcp_servers.sql | ✅ | migración 005, tabla creada |
| 3 | Función `_resolve_tools` existe | lectura src/crews/base_crew.py:78 | ✅ | método definido, línea 78 |
| 4 | Función `create_agent` existe | lectura src/crews/factory.py:17 | ✅ | método definido, línea 17 |
| 5 | Clase `MCPPool` existe | lectura src/tools/mcp_pool.py:35 | ✅ | clase definida, línea 35 |
| 6 | Método `get_tools` en MCPPool | lectura src/tools/mcp_pool.py:77 | ✅ | método async definido, línea 77 |
| 7 | Dependencia crewai-tools | grep en pyproject.toml | ✅ | línea 42: crewai-tools>=0.20.0 |
| 8 | Dependencia mcp | grep en pyproject.toml | ✅ | línea 29: mcp>=1.0.0,<2.0.0 |
| 9 | Patrón tool_registry.get | lectura src/crews/base_crew.py:83 | ✅ | usa tool_registry.get(tool_name, org_id=self.org_id) |
| 10 | Patrón tool_registry.get en factory | lectura src/crews/factory.py:33 | ✅ | usa tool_registry.get(tool_name, org_id=org_id) |
| 11 | MCPPool singleton | lectura src/tools/mcp_pool.py:51 | ✅ | método get() retorna instancia singleton |
| 12 | Prefijo `mcp:` NO implementado | búsqueda en código fuente | ❌ | no encontrado en _resolve_tools ni factory |

**Discrepancias encontradas:**
- **DISCREPANCIA 1:** El plan requiere detectar prefijo `mcp:` en _resolve_tools, pero actualmente solo usa tool_registry.get sin detección de prefijo. **Resolución:** Modificar _resolve_tools para detectar `mcp:` y usar MCPPool.get_tools.
- **DISCREPANCIA 2:** El plan requiere soporte para herramientas instanciadas en factory, pero actualmente solo maneja clases. **Resolución:** Modificar create_agent para aceptar herramientas ya instanciadas además de clases.

---

## Análisis de Datos (ETAPA 1)

- ✅ **Schema:** Tablas `agent_catalog` y `org_mcp_servers` existen con schemas apropiados
- ✅ **Integridad referencial:** Foreign keys a organizations en ambas tablas
- ✅ **RLS policies:** Políticas RLS aplicadas en ambas tablas (ver migraciones)
- ✅ **Índices necesarios:** Índices en org_id, role, name apropiados
- ✅ **Tipos de datos:** UUID para org_id, TEXT para nombres, JSONB para configuraciones

Incluir: Diagrama ER simple — agent_catalog(org_id, role) -> organizations(id), org_mcp_servers(org_id, name) -> organizations(id). Cambios necesarios: Ninguno, schemas existentes soportan el paso.

---

## Análisis de Código (ETAPA 2)

- ✅ **Funciones/clases nuevas:** Ninguna nueva, modificación de _resolve_tools y create_agent
- ✅ **Patrones:** Se siguen patrones existentes de resolución via registry, se introduce patrón de detección de prefijo
- ✅ **Modularidad:** Cambios localizados en 2 métodos, cohesión alta
- ✅ **Calidad:** Código actual es limpio, cambios mantienen complejidad baja
- ✅ **Imports y dependencias:** Requiere importar MCPPool en base_crew.py

Incluir: Componentes modificados con interfaces detalladas — _resolve_tools modificado para detectar mcp:, create_agent modificado para manejar instancias. Referencias a patrones existentes: tool_registry.get, MCPPool.get_tools.

---

## Análisis de Backend (ETAPA 3)

- ✅ **APIs/endpoints:** No nuevos endpoints, modificación interna de resolución de herramientas
- ✅ **Middleware:** No aplicable
- ✅ **Flujos:** Flujo de creación de agent modificado para soportar MCP
- ✅ **Contratos:** Contrato de allowed_tools extendido para incluir mcp:server:tool
- ✅ **Error handling:** Manejo de errores en MCPPool ya implementado

Incluir: Endpoints no afectados. Flujo: BaseCrew.run -> _resolve_tools -> detectar mcp: -> MCPPool.get_tools, factory.create_agent -> resolver tools (instancias o clases).

---

## Análisis de Fullstack + DX (ETAPA 4)

- ✅ **Flujo completo:** DB (org_mcp_servers) -> Backend (MCPPool) -> Agent creation -> UX (funcionalidad MCP en agents)
- ✅ **Coherencia:** Decisiones de data (schema MCP) apoyan código (resolución MCP)
- ✅ **Alineación:** Arquitectura existente soporta con modificaciones mínimas
- ✅ **Gaps:** Ninguno identificado, implementación directa
- ✅ **DX & Tooling (OBLIGATORIO):**

### Herramienta Propuesta: [Validador de Configuración MCP]
- **Qué automatiza:** Verificación automática de configuración de servidores MCP antes de ejecución de agents
- **Tipo:** script CLI
- **Cómo se usa:** `fap validate-mcp --org-id <id>` o integrado en agent creation
- **Impacto para el usuario final:** Evita errores de conexión MCP detectando problemas de configuración temprano
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso

Incluir: Flujo end-to-end: Config DB -> Validación DX -> Agent Creation -> MCP Connection. Validación: Todo encaja con arquitectura existente.

---

## Criterios de Aceptación

Lista binaria (sí/no) verificable:
- ✅ [DATA] Tabla `org_mcp_servers` existe con columnas correctas
- ✅ [CODE] Función `_resolve_tools()` modificada para detectar `mcp:` prefijo
- ✅ [BACKEND] BaseCrew puede resolver herramienta con prefijo `mcp:`
- ✅ [FULLSTACK] AgentFactory soporta herramientas instanciadas
- ✅ [DX] Herramienta validadora de MCP ejecuta sin errores y reduce debugging manual

---

## Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Conexión MCP falla | Media | Configuración incorrecta en DB | Validación DX propuesta |
| tool_registry.get modificado | Baja | Cambio en resolución de tools | Tests unitarios existentes |
| Instancias vs clases en tools | Baja | CrewAI espera clases | Verificar documentación CrewAI |
| Rendimiento conexiones MCP | Media | Conexiones persistentes | Circuit breaker en MCPPool |

- Riesgos técnicos: Compatibilidad con CrewAI para instancias vs clases
- Riesgos de integración: Ninguno, cambios localizados
- Riesgos futuros: Escalabilidad de conexiones MCP

---

## Plan de Implementación

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Validador de configuración MCP | FULLSTACK/DX | Media | 2h | Ninguna |
| 1 | Modificar `src/crews/base_crew.py` _resolve_tools | CODE/BACKEND | Media | 1h | Tarea 0 |
| 2 | Modificar `src/crews/factory.py` create_agent | CODE | Baja | 1h | Tarea 0 |
| 3 | Validar flujo end-to-end con MCP | FULLSTACK | Baja | 1h | Tareas 1-2 |
| 4 | Tests de integración para resolución MCP | CODE | Media | 2h | Tareas 1-2 |

> [!IMPORTANT]
> **Tarea 0 siempre = DX & Tooling.** El implementador DEBE ejecutarla primero y usar la herramienta resultante para el resto del paso.

**Tiempo total estimado:** 6 horas

---

## Roadmap (NO implementar ahora)

- Optimizaciones: Pool de conexiones MCP podría beneficiarse de configuración de límites
- Mejoras futuras: Soporte para herramientas híbridas (MCP + integración)
- Pre-requisitos: Tests de carga para conexiones MCP persistentes

---

## Reglas de Oro

- ✅ **Análisis accionable y específico**, no genérico
- ✅ **TODO verificado contra código**, no supuestos
- ✅ **Si algo no está definido** → señalado como ambigüedad + resolución concreta
- ✅ **Si el plan contradice el código** → el código gana + documentar discrepancia
- ✅ **Nivel CTO exigente** en rigor y profundidad
- ✅ **Coherente con phase-state.md** — no perder decisiones ya tomadas
- ✅ **TODO el paso**, incluyendo sub-pasos
- ✅ **Etapas secuenciales** — data → code → backend → fullstack+DX, sin saltar
- ✅ **≥ 1 herramienta DX propuesta** — siempre, sin excepción

---

## Métrica de Calidad

| Métrica | Mínimo |
|:---|:---|
| `proyecto-config.json` leído antes de explorar | 0% (archivo no encontrado, inferido) |
| Elementos verificados (§0) | 12 (supera mínimo 8) |
| Discrepancias detectadas | 2 |
| Secciones completadas | 8 |
| Etapas cubiertas | 4 |
| Criterios de aceptación | 5 |
| Riesgos identificados | 4 |
| Tareas en el plan | 5 |
| Suposiciones no verificadas | 1 (config de proyecto-config.json) |
| Propuesta DX / Tooling | 1 |
| Estimación de tiempo | Sí |

---

**Idioma de respuesta:** Español 🇪🇸