# Análisis Técnico — Fase 2.5: Service Catalog TIPO C

**Agente:** qwen  
**Fecha:** 2026-04-13  
**Paso:** Fase 2.5 (Service Catalog TIPO C)  
**Documento de referencia:** `docs/mcp-analisis-finalV2.md`  
**Contexto de fase:** `docs/estado-fase.md`

---

## 0. Verificación contra Código Fuente

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `organizations` existe | `grep -r "CREATE TABLE.*organizations" migrations/001` | ✅ | `001_set_config_rpc.sql:53` — `id UUID PRIMARY KEY`, `name TEXT`, `created_at TIMESTAMPTZ` |
| 2 | RLS usa `current_org_id()` o `current_setting('app.org_id')` | Revisión migraciones 001-023 | ✅ | Patrón mixto: algunas usan `current_org_id()` (helper SQL L37), otras `current_setting('app.org_id', TRUE)`. La nueva migración debe elegir uno. |
| 3 | FK `org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE` | Revisión 005, 004, 006, etc. | ✅ | Patrón consistente en todas las migraciones existentes |
| 4 | Tabla `activity_logs` existe | `grep -r "activity_logs" migrations/` | ❌ | **NO EXISTE**. Ninguna migración crea `activity_logs`. El plan asume que existe para audit logging (Paso D.3). |
| 5 | Función `get_service_client()` existe | `grep -rn "def get_service_client" src/db/session.py` | ✅ | `session.py:53` — retorna `Client` (service_role, bypass RLS) |
| 6 | Función `get_secret(org_id, secret_name)` existe | `grep -rn "def get_secret" src/db/vault.py` | ✅ | `vault.py:22` — versión **síncrona** solamente |
| 7 | `get_secret_async` existe | `grep -rn "def get_secret_async" src/db/vault.py` | ❌ | **NO EXISTE**. `mcp_pool.py:26` la importa pero no está definida. Prerrequisito 5.0.1 pendiente. |
| 8 | `OrgBaseTool` existe con `org_id: str` | `grep -rn "class OrgBaseTool" src/tools/base_tool.py` | ✅ | `base_tool.py:17` — hereda de `crewai.tools.BaseTool`, tiene `org_id: str` y `_get_secret()` |
| 9 | `ToolRegistry.register()` firma real | `grep -rn "def register" src/tools/registry.py` | ✅ | `registry.py:42` — decorador con params: `name`, `description`, `requires_approval`, `timeout_seconds`, `retry_count`, `tags`. **No acepta `tool_class` como parámetro posicional.** |
| 10 | `require_org_id` middleware existe | `grep -rn "def require_org_id" src/api/middleware.py` | ✅ | `middleware.py:100` — `async def require_org_id(x_org_id: str = Header(..., alias="X-Org-ID"))` |
| 11 | `verify_org_membership` existe | `grep -rn "def verify_org_membership" src/api/middleware.py` | ✅ | `middleware.py:276` — requiere `request`, `org_id = Depends(require_org_id)`, `user = Depends(verify_supabase_jwt)` |
| 12 | Directorio `src/jobs/` existe | `list_directory src/jobs` | ❌ | **NO EXISTE**. El plan propone `src/jobs/health_check.py` pero el directorio no existe. Existe `src/scheduler/` con `bartenders_jobs.py`. |
| 13 | APScheduler ya está en uso | `grep -rn "apscheduler\|Scheduler" src/` + `pyproject.toml` | ✅ | `pyproject.toml:26` — `"apscheduler>=3.10.0"` como dependencia directa. `src/scheduler/__init__.py` existe. |
| 14 | `requests` como dependencia | `grep "requests" pyproject.toml` | ❌ | **NO ESTÁ** en `pyproject.toml`. Solo `httpx>=0.28.0`. El plan usa `requests` en `ServiceConnectorTool` y `health_check.py`. |
| 15 | Tabla `secrets` con RLS service_role | `grep -rn "CREATE TABLE.*secrets" migrations/002` | ✅ | `002_governance.sql:79` — `org_id UUID`, `name TEXT`, `secret_value TEXT`. RLS: solo service_role puede SELECT/INSERT/UPDATE. |
| 16 | `FLOW_INPUT_SCHEMAS` existe | `grep -rn "FLOW_INPUT_SCHEMAS" src/api/routes/flows.py` | ✅ | `flows.py:70-130` — diccionario estático con schemas de 4 flows bartenders. |
| 17 | `mcp` como dependencia directa | `grep "mcp" pyproject.toml` | ❌ | **NO ESTÁ** como dep directa. Solo transitiva vía `crewai-tools` (optional). |
| 18 | `pyproject.toml` estructura | Lectura directa | ✅ | Usa `hatchling` build backend, `src` package, deps en formato PEP 621. |

### Discrepancias Encontradas

| # | Discrepancia | Impacto | Resolución Propuesta |
|---|---|---|---|
| D1 | **`activity_logs` NO existe** — el plan (Paso D.3) asume que existe | Alto — el audit logging no funcionará sin la tabla | **Opción A:** Crear tabla `activity_logs` como parte de la migración 024. **Opción B (recomendada para MVP):** Usar logging estructurada (`structlog`) en vez de tabla DB. El plan dice "registrar en `activity_logs`" pero esta tabla nunca se definió. Para MVP, loguear con `structlog` es suficiente y evita crear una tabla extra. |
| D2 | **`get_secret_async` NO existe** — importada en `mcp_pool.py` pero no definida en `vault.py` | Medio — es prerrequisito 5.0.1, no bloquea Fase 2.5 si usamos versión síncrona | `ServiceConnectorTool._run()` es síncrono (hereda de `OrgBaseTool._run()`), así que puede usar `get_secret()` síncrona sin problema. Marcar `get_secret_async` como dependencia externa para Fase 5.1. |
| D3 | **`src/jobs/` NO existe** — plan propone crear ahí health check | Bajo — el directorio `src/scheduler/` ya existe y usa APScheduler | Usar `src/scheduler/health_check.py` en vez de `src/jobs/`. Coherente con estructura existente. |
| D4 | **`requests` NO está en pyproject.toml** — plan usa `requests` en connector y health check | Medio — `import requests` fallará en runtime | El proyecto ya usa `httpx` (en pyproject.toml). **Resolver:** usar `httpx` en vez de `requests`. O agregar `requests` como dependencia. Recomendación: usar `httpx` (ya disponible, soporta sync con `httpx.Client`). |
| D5 | **`tool_registry.register()` firma** — el plan dice `tool_registry.register(name="x", tool_class=Y)` pero la firma real es un decorador | Medio — el código propuesto en Paso C.3 no compilaría | El `register()` es un decorador de clase, no una función que acepta `tool_class`. Resolver: envolver `ServiceConnectorTool` con `@register_tool(name="service_connector", ...)` en vez de llamar `.register()` como método. |
| D6 | **RLS pattern** — plan usa `current_setting('app.current_org_id')` pero el patrón existente usa `current_org_id()` o `current_setting('app.org_id', TRUE)` | Bajo — variable incorrecta en política RLS | Usar `current_org_id()` (helper function de migración 001) como patrón consistente con migraciones 005, 002_governance, 019. |

---

## 1. Diseño Funcional

### Happy Path

1. **Admin carga las 50 tools** → ejecuta `import_service_catalog.py` → 20 proveedores en `service_catalog`, 50 tools en `service_tools`.
2. **Org habilita un servicio** (ej: Stripe) → se crea registro en `org_service_integrations` con `status='active'`, secrets asociados.
3. **Agente (o usuario) ejecuta `service_connector`** → `tool_id="stripe.create_customer"`, `input_data={"email": "test@test.com"}`.
4. **ServiceConnectorTool:**
   - Lee definición de `service_tools` (URL, method, headers, execution).
   - Verifica que la org tiene el servicio activo en `org_service_integrations`.
   - Resuelve secreto del Vault (`stripe_api_key`).
   - Ejecuta HTTP call con `httpx`.
   - Sanitiza output (elimina cualquier secreto filtrado).
   - Retorna resultado al LLM.
5. **Health check** cada 30 min → valida `health_check_url` de servicios activos → actualiza `last_health_check`, `last_health_status`.

### Edge Cases (MVP)

| Edge Case | Comportamiento Esperado |
|---|---|
| Tool no existe en `service_tools` | Retorna `"Error: Tool 'X' no encontrada en service_tools"` |
| Servicio no está activo para la org | Retorna `"Error: Servicio 'X' no está activo para esta organización"` |
| Secreto no configurado en Vault | Retorna `"Error: Secreto 'X' no configurado"` (de `VaultError`) |
| HTTP timeout (>30s) | Retorna `"Error HTTP: Timeout"` |
| HTTP error (4xx/5xx) | Retorna `"Error HTTP: {status_code} - {response_text[:200]}"` |
| Output con secreto filtrado | Sanitizer reemplaza con `[REDACTED]` |
| Health check falla (timeout) | `last_health_status = "timeout"`, `status` no cambia (sigue activo) |

### Manejo de Errores — Vista del Usuario

- **Desde el LLM/Agente:** Recibe string con resultado o mensaje de error descriptivo. Nunca ve secretos.
- **Desde Dashboard:** API `/api/integrations/active` retorna lista con `last_health_status` para monitoring.
- **Logs:** `structlog` registra cada ejecución con `tool_id`, `org_id`, `http_status`, `duration_ms`.

---

## 2. Diseño Técnico

### 2.1 Migración SQL — `024_service_catalog.sql`

**3 tablas:**

| Tabla | RLS | Descripción |
|---|---|---|
| `service_catalog` | ❌ No | Catálogo global de proveedores (~20 rows) |
| `org_service_integrations` | ✅ Sí | Servicios habilitados per-org |
| `service_tools` | ❌ No | Definiciones de tools por proveedor (~50 rows) |

**Corrección al plan original (Discrepancia D6):**

```sql
-- Política RLS corregida:
CREATE POLICY org_isolation ON org_service_integrations
  USING (org_id::text = current_org_id());
-- En vez de: current_setting('app.current_org_id')::UUID (variable no existe)
```

**Corrección FK (si el nombre de tabla difiere):**
La tabla `organizations` existe confirmed en `001_set_config_rpc.sql:53`. FK usa `REFERENCES organizations(id)` sin prefijo `public.`. Coherente con migraciones 002-023.

### 2.2 ServiceConnectorTool

**Ubicación:** `src/tools/service_connector.py`

**Herencia:** `OrgBaseTool` (síncrono, `_run()` method)

**Dependencias internas:**
- `src.db.session.get_service_client` — para queries a DB
- `src.db.vault.get_secret` — versión síncrona (get_secret_async NO existe aún)
- `src.mcp.sanitizer.sanitize_output` — Regla R3
- `httpx` — en vez de `requests` (ya está en pyproject.toml)

**Input Schema:**
```python
class ServiceConnectorInput(BaseModel):
    tool_id: str = Field(description="ID de la tool (ej: stripe.create_customer)")
    input_data: dict = Field(default_factory=dict, description="Parámetros de la tool")
```

**Flujo interno (§10.5.4 del plan):**
1. Query `service_tools` JOIN `service_catalog` → obtiene `execution`, `auth_type`, `base_url`
2. Query `org_service_integrations` WHERE `org_id = self.org_id` AND `service_id = X` AND `status = 'active'`
3. `get_secret(org_id, secret_name)` → resuelve credencial
4. `httpx.Client().request(method, url, headers, json/params)` → ejecuta
5. `sanitize_output(response.json())` → limpia output
6. Return string del resultado

**Corrección al plan (Discrepancia D4):** Usar `httpx` en vez de `requests`:
```python
import httpx

with httpx.Client(timeout=30) as client:
    response = client.request(
        method=method,
        url=url,
        headers=headers,
        json=input_data if method in ("POST", "PUT", "PATCH") else None,
        params=input_data if method == "GET" else None,
    )
```

### 2.3 Output Sanitizer

**Ubicación:** `src/mcp/sanitizer.py`

**Función:** `sanitize_output(data: Any) -> Any`

**Patrones de regex:** 7 patrones de secretos conocidos (Stripe, Slack, GitHub, Google, Bearer, Basic).

**Comportamiento:** Recursivo sobre dicts y listas. Reemplaza matches con `[REDACTED]`.

### 2.4 Health Check

**Ubicación:** `src/scheduler/health_check.py` (NO `src/jobs/` — discrepancia D3)

**Función:** `async def run_health_checks()`

**Lógica:**
1. Query integraciones activas con `health_check_url` no null
2. Para cada una: GET al `health_check_url` con auth header si tiene secreto
3. Actualiza `last_health_check`, `last_health_status`, `error_message`
4. Si status = "error" → cambia `status` a "error"

**Registro en APScheduler:** Usar el scheduler existente en `src/scheduler/__init__.py`. Agregar:
```python
scheduler.add_job(run_health_checks, 'interval', minutes=30, id='health_check')
```

### 2.5 API Endpoints

**Ubicación:** `src/api/routes/integrations.py`

**3 endpoints:**

| Endpoint | Auth | Descripción |
|---|---|---|
| `GET /api/integrations/available` | Sin auth (catálogo global) | Lista `service_catalog` |
| `GET /api/integrations/active` | `require_org_id` | Integraciones activas de la org |
| `GET /api/integrations/tools/{service_id}` | Sin auth | Tools de un proveedor |

**Corrección al plan:** El endpoint `/active` debe usar `require_org_id` como dependencia, no `get_current_user` (que no existe con ese nombre). El middleware real es:
```python
@router.get("/active")
async def list_active_integrations(org_id: str = Depends(require_org_id)):
```

### 2.6 Script de Import

**Ubicación:** `scripts/import_service_catalog.py`

**Input:** `data/service_catalog_seed.json` (50 tools, ~20 proveedores)

**Lógica:**
1. Lee JSON seed
2. Extrae proveedores únicos → inserta en `service_catalog`
3. Convierte tools al schema de `service_tools` → inserta
4. Verifica integridad (0 huérfanos)

**Nota:** Requiere `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` como variables de entorno.

### 2.7 Modelos de Datos

**service_catalog:**
| Columna | Tipo | Nullable | Default |
|---|---|---|---|
| `id` | TEXT | PK | — |
| `name` | TEXT | NOT NULL | — |
| `category` | TEXT | NOT NULL | — |
| `auth_type` | TEXT | NOT NULL | — |
| `auth_scopes` | JSONB | NULL | `'[]'` |
| `base_url` | TEXT | NOT NULL | — |
| `api_version` | TEXT | NULL | — |
| `health_check_url` | TEXT | NULL | — |
| `docs_url` | TEXT | NULL | — |
| `logo_url` | TEXT | NULL | — |
| `required_secrets` | TEXT[] | NOT NULL | `'{}'` |
| `config_schema` | JSONB | NULL | `'{}'` |
| `created_at` | TIMESTAMPTZ | NULL | `now()` |

**org_service_integrations:**
| Columna | Tipo | Nullable | Default |
|---|---|---|---|
| `id` | UUID | PK | `gen_random_uuid()` |
| `org_id` | UUID | NOT NULL | — (FK → organizations) |
| `service_id` | TEXT | NOT NULL | — (FK → service_catalog) |
| `status` | TEXT | NOT NULL | `'pending_setup'` |
| `secret_names` | JSONB | NOT NULL | `'[]'` |
| `config` | JSONB | NULL | `'{}'` |
| `last_health_check` | TIMESTAMPTZ | NULL | — |
| `last_health_status` | TEXT | NULL | — |
| `error_message` | TEXT | NULL | — |
| `enabled_at` | TIMESTAMPTZ | NULL | — |
| `created_at` | TIMESTAMPTZ | NULL | `now()` |
| `updated_at` | TIMESTAMPTZ | NULL | `now()` |

**service_tools:**
| Columna | Tipo | Nullable | Default |
|---|---|---|---|
| `id` | TEXT | PK | — |
| `service_id` | TEXT | NOT NULL | — (FK → service_catalog) |
| `name` | TEXT | NOT NULL | — |
| `version` | TEXT | NOT NULL | `'1.0.0'` |
| `input_schema` | JSONB | NOT NULL | — |
| `output_schema` | JSONB | NOT NULL | — |
| `execution` | JSONB | NOT NULL | — |
| `tool_profile` | JSONB | NOT NULL | — |
| `created_at` | TIMESTAMPTZ | NULL | `now()` |

---

## 3. Decisiones

| # | Decisión | Justificación | Corrige Plan |
|---|---|---|---|
| D1 | Usar `httpx` en vez de `requests` | `httpx` ya está en `pyproject.toml`. Evita agregar dependencia nueva. API es casi idéntica para uso sync. | Sí — Plan §C.2 usa `requests`. Corregir a `httpx`. |
| D2 | Usar `src/scheduler/` en vez de `src/jobs/` | El directorio `src/jobs/` no existe. `src/scheduler/` ya existe con APScheduler configurado. | Sí — Plan §D.1 propone `src/jobs/health_check.py`. |
| D3 | Audit logging con `structlog` en vez de tabla `activity_logs` | La tabla `activity_logs` NO existe en ninguna migración. Para MVP, logging estructurado es suficiente. | Sí — Plan §D.3 asume `activity_logs` existente. |
| D4 | RLS policy usa `current_org_id()` | Patrón existente en migraciones 005, 002_governance, 019. El plan usa `current_setting('app.current_org_id')` que es una variable que no existe. | Sí — Plan §A.3 usa variable incorrecta. |
| D5 | Registro de tool con `@register_tool()` decorator | `ToolRegistry.register()` es un decorador, no un método que acepta `tool_class`. El plan propone `tool_registry.register(name="x", tool_class=Y)`. | Sí — Plan §C.3 tiene código que no compila. |
| D6 | API `/active` usa `require_org_id` | `get_current_user` no existe en middleware. El middleware real es `require_org_id` + `verify_org_membership`. | Sí — Plan §D.2 usa `get_current_user`. |
| D7 | `ServiceConnectorTool._run()` usa `get_secret()` síncrona | `get_secret_async` NO existe (prerrequisito 5.0.1 pendiente). `_run()` es síncrono por herencia de CrewAI BaseTool. | No — plan no especifica async vs sync, pero asume implícitamente que funciona. |

---

## 4. Criterios de Aceptación

- [ ] Migración `024_service_catalog.sql` se ejecuta sin errores en Supabase (3 tablas creadas, RLS activo en `org_service_integrations`, FKs válidas).
- [ ] `SELECT count(*) FROM service_tools` retorna ≥ 50 tras ejecutar script de import.
- [ ] `SELECT count(*) FROM service_catalog` retorna ≥ 20 tras ejecutar script de import.
- [ ] Query con JOIN `service_tools` → `service_catalog` → `org_service_integrations` no retorna huérfanos.
- [ ] `ServiceConnectorTool` se importa sin errores: `from src.tools.service_connector import ServiceConnectorTool`.
- [ ] `sanitize_output({"key": "sk_live_abc"})` retorna `{"key": "[REDACTED]"}`.
- [ ] Health check scheduler se registra sin error en APScheduler (`scheduler.get_job('health_check')` retorna el job).
- [ ] Endpoint `GET /api/integrations/active` retorna 200 con lista de integraciones (vacía si no hay activas).
- [ ] Tool registrada en `tool_registry`: `"service_connector" in tool_registry.list_tools()` retorna `True`.
- [ ] Test E2E: `ServiceConnectorTool(org_id="test")._run(tool_id="stripe.create_customer", input_data={})` retorna mensaje de error legible (no crash).

---

## 5. Riesgos

| Riesgo | Impacto | Probabilidad | Mitigación |
|---|---|---|---|
| **JSON seed mal formado** (50 tools con schemas inválidos) | Alto — import falla o tools no ejecutables | Media | Validar cada `input_schema` contra JSON Schema Draft 7 antes de insertar. Script de import debe tener `jsonschema.validate()`. |
| **`httpx` no funciona bien en modo sync** | Medio — HTTP calls fallan | Baja | `httpx.Client()` soporta sync nativamente. Testear con un mock server antes de deploy. |
| **RLS bloquea queries de ServiceConnectorTool** | Alto — tool no puede leer integraciones | Media | `ServiceConnectorTool` usa `get_service_client()` (service_role, bypass RLS). No necesita RLS. |
| **Secretos hardcodeados en `SECRET_PATTERNS` no cubren todos los casos** | Medio — fuga de secretos al LLM | Baja | Patrones cubren los 7 tipos más comunes. Agregar log warning si sanitizer detecta string que parece secreto pero no matchea patrón. |
| **Health checkScheduler causa race condition con queries concurrentes** | Bajo — status inconsistente temporal | Baja | APScheduler usa `max_instances=1` por default para jobs con mismo ID. Updates son atómicos. |
| **FK a `organizations` falla si tabla tiene otro nombre** | Alto — migración 024 falla | Muy baja | Verificación A.1 confirma nombre. Todas las migraciones 001-023 usan `organizations` sin prefijo. |
| **`tool_registry.register()` como decorador vs llamada directa** | Medio — tool no se registra | Media (si no se corrige) | Usar `@register_tool(name="service_connector", ...)` decorador en la clase. Ver sección 3, decisión D5. |

---

## 6. Plan de Implementación

### Tarea 6.1: Migración SQL (2.5A)
**Complejidad:** Media  
**Dependencias:** Ninguna  
**Archivos:** `supabase/migrations/024_service_catalog.sql`

1. Verificar nombre de tabla `organizations` (Paso A.1 del plan).
2. Crear `service_catalog` (sin RLS, con índices).
3. Crear `org_service_integrations` (con RLS `current_org_id()`, índices, FKs).
4. Crear `service_tools` (sin RLS, con índices).
5. Ejecutar migración en Supabase → validar sin errores.
6. Test FK inválida → debe fallar.

### Tarea 6.2: Script de Import (2.5B)
**Complejidad:** Media  
**Dependencias:** 6.1  
**Archivos:** `data/service_catalog_seed.json`, `scripts/import_service_catalog.py`

1. Preparar JSON seed (corregir `required` booleano → array, documentar URL params).
2. Script: extraer proveedores únicos → `service_catalog`.
3. Script: convertir e insertar 50 tools → `service_tools`.
4. Ejecutar script con env vars → validar counts (≥20 providers, ≥50 tools).
5. Verificación cruzada: 0 huérfanos, todos los `tool_profile` completos.

### Tarea 6.3: Output Sanitizer (2.5C — parte 1)
**Complejidad:** Baja  
**Dependencias:** Ninguna  
**Archivos:** `src/mcp/sanitizer.py`

1. Crear `src/mcp/` directorio + `__init__.py`.
2. Implementar `sanitize_output()` con 7 patrones de regex.
3. Test unitario: dict con Stripe key → `[REDACTED]`.

### Tarea 6.4: ServiceConnectorTool (2.5C — parte 2)
**Complejidad:** Alta  
**Dependencias:** 6.1, 6.3  
**Archivos:** `src/tools/service_connector.py`

1. Crear clase `ServiceConnectorTool(OrgBaseTool)` con `_run()` síncrono.
2. Implementar flujo: DB lookup → verify active → resolve secret → httpx call → sanitize.
3. Manejo de errores en cada paso (tool no encontrada, servicio inactivo, HTTP error).
4. Decorar con `@register_tool(name="service_connector", tags=["integration", "type_c", "http"], timeout_seconds=30, retry_count=2)`.
5. Test unitario con mock DB + mock Vault.

### Tarea 6.5: Health Check Scheduler (2.5D — parte 1)
**Complejidad:** Media  
**Dependencias:** 6.1  
**Archivos:** `src/scheduler/health_check.py`

1. Crear `src/scheduler/health_check.py` con `async def run_health_checks()`.
2. Query integraciones activas → HTTP GET health URL → actualizar status.
3. Registrar job en APScheduler existente.
4. Test: verificar que job se crea (`scheduler.get_job('health_check')`).

### Tarea 6.6: API Endpoints (2.5D — parte 2)
**Complejidad:** Baja  
**Dependencias:** 6.1  
**Archivos:** `src/api/routes/integrations.py`

1. Crear 3 endpoints: `/available`, `/active`, `/tools/{service_id}`.
2. `/active` usa `require_org_id` como dependencia.
3. Importar router en `src/api/routes/__init__.py` o donde se registren los routers.

### Tarea 6.7: Audit Logging (2.5D — parte 3)
**Complejidad:** Baja  
**Dependencias:** 6.4  
**Archivos:** `src/tools/service_connector.py` (modificar)

1. Agregar `structlog` al final de `ServiceConnectorTool._run()`.
2. Log: `tool_id`, `service_id`, `http_status`, `success`, `duration_ms`.
3. No bloquear ejecución por fallo de logging (try/except).

### Tarea 6.8: Tests E2E
**Complejidad:** Media  
**Dependencias:** 6.4, 6.5, 6.6  
**Archivos:** `tests/test_service_connector.py`

1. Test: `ServiceConnectorTool` lee definición de DB correctamente.
2. Test: bloquea servicio inactivo.
3. Test: sanitizer atrapa secretos.
4. Test: health check actualiza status.

---

## 🔮 Roadmap (NO implementar ahora)

| Mejora | Descripción | Por qué no en MVP |
|---|---|---|
| **Tabla `activity_logs`** | Crear tabla dedicada para auditoría de ejecuciones | MVP puede funcionar con structlog. Tabla requiere diseño de schema, retención, indexing. |
| **`get_secret_async`** | Wrapper async para `get_secret()` | Necesario para MCP pool (5.0.1), pero `ServiceConnectorTool` es síncrono y funciona con versión sync. |
| **`mcp>=1.0.0` como dep directa** | Agregar en pyproject.toml | Necesario para servidor MCP (Fase 5.1), pero Service Catalog funciona sin ello. |
| **Unificar `FLOW_INPUT_SCHEMAS` en `FlowRegistry`** | Mover schemas estáticos al registry | Mejora de arquitectura, no bloquea MVP. Requiere refactor de `FlowRegistry.register()`. |
| **Dashboard UI para habilitar servicios** | UI para crear registros en `org_service_integrations` | MVP puede usar SQL directo o script. UI requiere frontend, auth, forms. |
| **Approval flow para activar servicios** | HITL para aprobar activación de integraciones | MVP asume activación directa. Approval requiere extensión de `pending_approvals`. |
| **ServiceConnectorTool con retry inteligente** | Retry con backoff para 5xx, no para 4xx | MVP retry simple (2 intentos). Backoff requiere configuración por tool. |
| **Health check con métricas Prometheus** | Exportar health status como métricas | MVP con logs es suficiente. Prometheus requiere infraestructura adicional. |
| **Soporte para múltiples secrets por tool** | Algunas tools necesitan 2+ secretos (API key + webhook secret) | MVP asume 1 secret por integración. Soporte multi-secret requiere cambio en schema de resolución. |
| **Configuración de URL params dinámicos** | URLs con `{shop}`, `{AccountSid}` que se resuelven desde `input_data` | El plan documenta esto como `url_params` en `execution`. Resolver requiere parsing de URL template. MVP puede hardcodear URLs sin placeholders. |

---

*Análisis completado por qwen — Fase 2.5 Service Catalog TIPO C*  
*2026-04-13 — Verificado contra código fuente real (migraciones 001-023, src/db, src/tools, src/api, pyproject.toml)*  
*7 discrepancias identificadas y resueltas basadas en evidencia del código.*
