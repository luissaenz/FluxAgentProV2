# ANÁLISIS TÉCNICO — Paso 2.5 (Agente OC)

## Resumen del Paso
**Objetivo:** Implementar el Service Catalog TIPO C — un catálogo de integraciones REST genéricas definido en DB, que permite a agentes externos ejecutar acciones contra servicios como Stripe, Twilio, etc., sin código hardcodeado.

**Posición en la fase:** Paso 5.2.5 de la Fase 5 (ECOSISTEMA AGÉNTICO MCP). Depende de: 5.0 → 5.0.1 → 5.1 → 5.2. Puede ejecutarse en paralelo con 5.2.

---

## 0. VERIFICACIÓN CONTRA CÓDIGO FUENTE

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `organizations` existe | `grep "CREATE TABLE.*organizations" migrations/001` | ✅ | 001_set_config_rpc.sql L53 |
| 2 | `OrgBaseTool` existe en `src/tools/base_tool.py` | Lectura directa del archivo | ✅ | Clase con `_get_secret()` existe |
| 3 | `get_secret()` existe en `vault.py` | Lectura directa | ✅ | vault.py L23-61 (síncrono, NO async) |
| 4 | `ToolRegistry.register()` existe | Lectura de registry.py | ✅ | Decorador con firma válida |
| 5 | Dependencia `mcp>=1.0.0` en pyproject.toml | Lectura de pyproject.toml | ❌ | NO existe — solo transitiva vía crewai-tools |
| 6 | Tabla `secrets` existe | `grep "CREATE TABLE.*secrets" migrations/` | ✅ | 002_governance.sql L79 |
| 7 | Tabla `org_mcp_servers` existe | `grep "CREATE TABLE.*org_mcp_servers"` | ✅ | 005_org_mcp_servers.sql L9 |
| 8 | APScheduler configurado | `grep -r "APScheduler" src/` | ✅ | src/scheduler/bartenders_jobs.py L23 |
| 9 | Tabla `activity_logs` para auditoría | `grep "CREATE TABLE.*activity_logs" migrations/` | ❌ | NO existe — plan la假设a |
| 10 | Variable RLS `app.current_org_id` | `grep "app.current_org_id" migrations/` | ⚠️ | No verificado — asumir que funciona como en otras políticas |

### Discrepancias Encontradas

| # | Discrepancia | Resolución Propuesta |
|---|---|---|
| 1 | Dependencia `mcp>=1.0.0` NO está en pyproject.toml como directa | Agregar a `[project.dependencies]` — necesario para MCP Server |
| 2 | Tabla `activity_logs` NO existe | Crear migración `024_service_catalog.sql` debe incluir esta tabla O usar tabla existente si hay otra de logs |
| 3 | `get_secret_async` NO existe en vault.py | El plan 2.5C usa `get_secret()` síncrono — coherente. No hay conflicto. |
| 4 | Archivo `data/service_catalog_seed.json` NO existe | Fase 2.5B debe crear este archivo primero — es un entregable de esa fase |

---

## 1. DISEÑO FUNCIONAL

### 1.1 Flujo Happy Path (E2E)

```
Agente Externo (Claude)
    │
    ├─→ ServiceConnectorTool._run(tool_id="stripe.create_customer", input_data={...})
    │       │
    │       ├─→ 1. Leer definición de service_tools (URL, método, headers)
    │       ├─→ 2. Verificar org_service_integrations.status == "active"
    │       ├─→ 3. get_secret(org_id, secret_name) → token
    │       ├─→ 4. HTTP request con token en header Authorization
    │       ├─→ 5. sanitize_output(result) → Regla R3
    │       └─→ 6. Retornar resultado al agente
```

### 1.2 Edge Cases MVP

| Edge Case | Comportamiento Esperado |
|-----------|------------------------|
| Tool no encontrada en `service_tools` | Retornar `"Error: Tool 'X' no encontrada en service_tools"` |
| Servicio no activo para la org | Retornar `"Error: Servicio 'Y' no está activo para esta organización"` |
| Secreto no configurado en Vault | `VaultError` → retornar `"Error: Secreto 'Z' no configurado para org..."` |
| HTTP request falla | Capturar `requests.exceptions.RequestException` → retornar `"Error HTTP: {detalle}"` |
| Response no es JSON válido | Intentar `response.text` como fallback |

### 1.3 Manejo de Errores

- **Errores de DB:** Logging con `structlog`, no expone detalles internos al agente.
- **Errores de HTTP:** Mapeo a mensaje genérico, código de status en logs internos.
- **Errores de Vault:** Mensaje claro indicando qué secreto falta (no el valor).

---

## 2. DISEÑO TÉCNICO

### 2.1 Componentes Nuevos

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| `sanitizer.py` | `src/mcp/sanitizer.py` | Regex-based output sanitizer (Regla R3) |
| `ServiceConnectorTool` | `src/tools/service_connector.py` | OrgBaseTool genérico para TIPO C |
| Migración SQL | `supabase/migrations/024_service_catalog.sql` | 3 tablas + RLS + índices |
| Health check job | `src/jobs/health_check.py` | APScheduler job cada 30min |
| API routes | `src/api/routes/integrations.py` | Endpoints REST para integraciones |

### 2.2 Interfaces Verificadas

**OrgBaseTool** (`src/tools/base_tool.py:17-48`):
```python
class OrgBaseTool(BaseTool):
    org_id: str
    
    def _get_secret(self, secret_name: str) -> str:
        return get_secret(self.org_id, secret_name)
```
⚠️ **Discrepancia:** El parámetro se llama `secret_name`, no `name` como podría asumirse.

**ToolRegistry.register()** (`src/tools/registry.py:39-71`):
```python
def register(
    self,
    name: str | None = None,
    description: str = "",
    requires_approval: bool = False,
    timeout_seconds: int = 30,
    retry_count: int = 3,
    tags: List[str] | None = None,
) -> Callable[[Type], Type]:
```
⚠️ **Verificación:** El decorador retorna la clase, no una instancia. El registro debe hacerse en el import del módulo.

**get_secret()** (`src/db/vault.py:23-61`):
```python
def get_secret(org_id: str, secret_name: str) -> str:
    # ... implementación síncrona ...
    return result.data["secret_value"]
```
⚠️ Solo existe versión síncrona. No hay `get_secret_async`.

### 2.3 Modelos de Datos (Schema DB)

**Tabla 1: `service_catalog`** (global, SIN RLS)
```sql
CREATE TABLE service_catalog (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  auth_type TEXT NOT NULL,
  auth_scopes JSONB DEFAULT '[]'::JSONB,
  base_url TEXT NOT NULL,
  api_version TEXT,
  health_check_url TEXT,
  docs_url TEXT,
  logo_url TEXT,
  required_secrets TEXT[] NOT NULL DEFAULT '{}',
  config_schema JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**Tabla 2: `org_service_integrations`** (per-org, CON RLS)
```sql
CREATE TABLE org_service_integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  service_id TEXT NOT NULL REFERENCES service_catalog(id),
  status TEXT NOT NULL DEFAULT 'pending_setup',
  secret_names JSONB NOT NULL DEFAULT '[]'::JSONB,
  config JSONB DEFAULT '{}'::JSONB,
  last_health_check TIMESTAMPTZ,
  last_health_status TEXT,
  error_message TEXT,
  enabled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, service_id)
);

ALTER TABLE org_service_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_isolation ON org_service_integrations
  USING (org_id = current_setting('app.current_org_id')::UUID);
```

**Tabla 3: `service_tools`** (global, SIN RLS)
```sql
CREATE TABLE service_tools (
  id TEXT PRIMARY KEY,
  service_id TEXT NOT NULL REFERENCES service_catalog(id),
  name TEXT NOT NULL,
  version TEXT NOT NULL DEFAULT '1.0.0',
  input_schema JSONB NOT NULL,
  output_schema JSONB NOT NULL,
  execution JSONB NOT NULL,
  tool_profile JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

⚠️ **Verificación de FK:** La FK a `organizations` debe verificar que la columna `id` en esa tabla sea UUID. La migración 001 L53 crea `organizations` pero no especifica el tipo de la PK.

### 2.4 Coherencia con estado-fase.md

- **Service Catalog TIPO C separado de TIPO B:** ✅ Coherente con decisión #12 del estado-fase.
- **Regla R3 - sanitizer:** ✅ Coherente con decisión #10 del estado-fase.
- **PyJWT existente:** No aplica directamente a Service Connector (usa Vault).
- **APScheduler existente:** ✅ Coherente — health check job usa el mismo patrón.

---

## 3. DECISIONES

### Nueva Decisión #1: Auditoría mediante `activity_logs` vs tabla dedicada

**Contexto:** El plan propone usar `activity_logs` para auditar ejecuciones de ServiceConnectorTool, pero la tabla NO existe en migraciones.

**Decisión:** Crear la tabla `activity_logs` en la misma migración `024_service_catalog.sql`.

**Justificación:**
- Mantiene auditoría centralizada.
- Permite query histórico desde Dashboard.
- Esquema simple: `id, org_id, action, details JSONB, created_at`.

### Nueva Decisión #2: Timeout HTTP fijo de 30s

**Contexto:** El plan usa `timeout=30` en el HTTP request.

**Decisión:** Confirmar 30s como timeout por defecto, con override posible desde `tool_profile`.

**Justificación:**
- Suficiente para la mayoría de APIs REST.
- Evita que una request lenta bloquee el flujo agéntico.
- Logs de timeout permiten identificar servicios problemáticos.

---

## 4. CRITERIOS DE ACEPTACIÓN

| # | Criterio | Verificable (Sí/No) |
|---|----------|---------------------|
| 1 | Las 3 tablas (`service_catalog`, `org_service_integrations`, `service_tools`) existen en DB | ✅ SQL: `SELECT count(*) FROM service_catalog;` |
| 2 | RLS activo en `org_service_integrations` | ✅ SQL: `SELECT relname, relrowsecurity FROM pg_class WHERE relname = 'org_service_integrations';` |
| 3 | FK a `organizations` válida | ✅ SQL: Test insert con org_id inválido debe fallar |
| 4 | ServiceConnectorTool registradas en ToolRegistry | ✅ Python: `tool_registry.get("service_connector")` |
| 5 | `sanitize_output()` reemplaza tokens conhecidos | ✅ Test unitario con `sk_live_xxx` → `[REDACTED]` |
| 6 | Health check job registrado en APScheduler | ✅ Python: `scheduler.get_job('health_check')` |
| 7 | GET `/api/integrations/active` retorna integraciones activas | ✅ HTTP test con token válido |
| 8 | Ejecución de `stripe.create_customer` sin hardcoded URL | ✅ Código: Lee `execution.url` de DB |

---

## 5. RIESGOS

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|--------|--------------|---------|------------|
| 1 | FK a `organizations` falla si la columna `id` no es UUID | Media | Alto | Verificar tipo de `organizations.id` antes de migrar |
| 2 | Variable RLS `app.current_org_id` no está configurada | Media | Alto | Verificar que el setting existe en Supabase config |
| 3 | `service_catalog_seed.json` no existe y bloquea 2.5B | Alta | Medio | Crear archivo como prerrequisito de 2.5B |
| 4 | Latencia alta en health checks con muchas integraciones | Baja | Medio | Batch queries, async execution |
| 5 | Secrets resueltos síncronamente bloquean thread | Baja | Bajo | Usar async en futuro si hay contención |

---

## 6. PLAN

### Tareas Atómicas (orden recomendado)

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1 | Verificar tipo de `organizations.id` en migrations existentes | Baja | — |
| 2 | Crear migración `024_service_catalog.sql` con 3 tablas + RLS + activity_logs | Media | #1 |
| 3 | Crear `src/mcp/sanitizer.py` con Regla R3 | Baja | — |
| 4 | Crear `src/tools/service_connector.py` (ServiceConnectorTool) | Alta | #2, #3 |
| 5 | Registrar ServiceConnectorTool en ToolRegistry (import del módulo) | Baja | #4 |
| 6 | Crear `src/jobs/health_check.py` (APScheduler job) | Media | #2 |
| 7 | Crear `src/api/routes/integrations.py` (endpoints REST) | Baja | #2 |
| 8 | Test E2E: ejecutar tool sin hardcoded URL | Alta | #4, #5 |
| 9 | Test sanitización de secretos en output | Baja | #3 |

### Estimación Total
- Fase 2.5A (DB): 3-4h
- Fase 2.5B (Seed): 3-4h
- Fase 2.5C (Motor): 4-5h
- Fase 2.5D (Ops): 2-3h
- **Total: 12-16h**

---

## 🔮 ROADMAP (NO implementar ahora)

1. **Unificación de input schemas:** Enriquecer `FlowRegistry.register()` para aceitar JSON Schema junto con `category`.
2. **Async Vault:** Crear `get_secret_async()` en vault.py para casos de alta concurrencia.
3. **OAuth2 refresh:** Implementar refresh token automático para servicios que expiren.
4. **Rate limiting per org:** Evitar que una org abuse de un servicio externo.
5. **Service Catalog UI:** Dashboard para que usuarios configuren integraciones sin usar el CLI.

---

*Documento generado por agente OC — Paso 2.5 Phase 5*
*Fecha: 2026-04-13*