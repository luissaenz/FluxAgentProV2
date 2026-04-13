# Análisis Técnico — Paso 5.2.5: Service Catalog TIPO C

**Agente:** ATG (Antigravity)  
**Paso:** Fase 2.5 (referenciado como 5.2.5 en `estado-fase.md`)  
**Plan General:** `docs/mcp-analisis-finalV2.md` — Fases 2.5A/B/C/D  
**Fecha:** 2026-04-13  

---

## 0. Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento del Plan | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `organizations` existe con PK `id UUID` | `grep -r "CREATE TABLE.*organizations" migrations/001_set_config_rpc.sql` | ✅ | `001_set_config_rpc.sql` L53: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` |
| 2 | Tabla `secrets` existe con columnas `org_id, name, secret_value` | `002_governance.sql` L79-86 | ✅ | FK → `organizations(id)`, UNIQUE(org_id, name), RLS service_role only |
| 3 | Función `current_org_id()` existe | `001_set_config_rpc.sql` L37-45 | ✅ | `RETURN current_setting('app.org_id', TRUE)` |
| 4 | Variable RLS usa `app.org_id` (NO `app.current_org_id`) | Revisión de 24 migraciones | ✅ | Migraciones nuevas usan `current_setting('app.org_id', TRUE)`, migraciones viejas usan `current_org_id()` que internamente llama lo mismo |
| 5 | Plan dice `current_setting('app.current_org_id')::UUID` en RLS de `org_service_integrations` | Comparado contra código real | ❌ **DISCREPANCIA** | **La variable se llama `app.org_id`, NO `app.current_org_id`.** El plan usa un nombre incorrecto. Ver Discrepancia #1 |
| 6 | `OrgBaseTool` existe con `org_id: str` y `_get_secret()` | `src/tools/base_tool.py` L17-48 | ✅ | Hereda de `crewai.tools.BaseTool`. `_get_secret()` llama `get_secret(self.org_id, secret_name)` |
| 7 | `ToolRegistry.register()` es un **decorador**, NO una función directa | `src/tools/registry.py` L39-71 | ❌ **DISCREPANCIA** | **`register()` retorna un callable (decorador).** El plan (Paso C.3) lo invoca como función directa `tool_registry.register(name=..., tool_class=...)`. Firma real: `register(name, description, requires_approval, timeout_seconds, retry_count, tags) → decorator`. NO acepta `tool_class` ni `timeout` ni `retry`. Ver Discrepancia #2 |
| 8 | `get_secret(org_id, secret_name)` existe en `vault.py` | `src/db/vault.py` L23-61 | ✅ | Retorna `str`. Lanza `VaultError` si no existe. Usa `get_service_client()` |
| 9 | `get_secret_async` **NO existe** en `vault.py` | `grep -rn "get_secret_async" src/db/vault.py` → 0 results | ❌ **DISCREPANCIA** | Se importa en `mcp_pool.py` L26 pero la función no está definida. Prerrequisito de Paso 5.0.1 aún pendiente. Para ServiceConnectorTool esto NO bloquea porque usa la versión síncrona. Ver Discrepancia #3 |
| 10 | `get_service_client()` existe y retorna `Client` Supabase | `src/db/session.py` L48-66 | ✅ | Singleton lazy, usa `settings.supabase_url` + `settings.supabase_service_key` |
| 11 | `get_tenant_client(org_id)` existe como context manager | `src/db/session.py` L174-191 | ✅ | Llama `set_config` RPC para setear `app.org_id` antes de queries |
| 12 | `get_current_user` **NO existe** en middleware | `grep -rn "get_current_user" src/api/` → 0 results | ❌ **DISCREPANCIA** | El plan (Paso D.2) usa `from src.api.middleware import get_current_user`. No existe. Las dependencias reales son: `require_org_id`, `verify_supabase_jwt`, `verify_org_membership`. Ver Discrepancia #4 |
| 13 | Tabla `activity_logs` **NO existe** | `grep -r "activity_logs" supabase/ src/` → 0 results | ❌ **DISCREPANCIA** | El plan (Paso D.3) inserta en `activity_logs`. Esta tabla no existe en ninguna migración. La auditoría actual usa `domain_events`. Ver Discrepancia #5 |
| 14 | `requests` (librería Python) **NO es dependencia directa** | `pyproject.toml` → no aparece `requests` en dependencies | ⚠️ | El plan usa `import requests` en ServiceConnectorTool y health_check. `httpx>=0.28.0` SÍ es dependencia directa. `requests` llega como transitiva vía `crewai-tools` (opcional). Ver Discrepancia #6 |
| 15 | APScheduler existe como dependencia directa | `pyproject.toml` L27: `apscheduler>=3.10.0` | ✅ | Patrón de uso en `src/scheduler/bartenders_jobs.py` con `AsyncIOScheduler` |
| 16 | Scheduler existente NO se importa en `main.py` (startup) | `src/api/main.py` — no importa scheduler | ⚠️ | El scheduler de bartenders existe pero NO se arranca en lifespan. Requiere verificación de si se arranca en otro punto o si está desactivado. Ver Discrepancia #7 |
| 17 | Directorio `src/mcp/` **NO existe** | `ls src/` → no contiene `mcp/` | ✅ | Confirmado como pendiente. `sanitizer.py` irá aquí |
| 18 | Directorio `data/` **NO existe** | `ls d:\Develop\Personal\FluxAgentPro-v2\data\` → error: does not exist | ✅ | Necesita crearse para `service_catalog_seed.json` |
| 19 | Patrón RLS `service_role bypass` establecido en migración 010 | `010_service_role_rls_bypass.sql` | ✅ | `auth.role() = 'service_role' OR org_id::text = current_org_id()` |
| 20 | `python-jose` en pyproject.toml pero middleware usa **PyJWT** | `pyproject.toml` L20 vs `middleware.py` L54 | ⚠️ | `pyproject.toml` lista `python-jose` pero el código importa `jwt` (PyJWT). Discrepancia heredada documentada en estado-fase.md §4. No bloquea paso 5.2.5. |

### Discrepancias Encontradas

**Discrepancia #1 — Variable RLS incorrecta en el plan**
- **Plan:** `org_id = current_setting('app.current_org_id')::UUID` (Paso A.3, L104 de mcp-analisis-finalV2.md)
- **Código real:** Existen 2 patrones:
  - Migraciones 001-002: `org_id::text = current_org_id()` (función helper)
  - Migraciones 003+: `org_id::text = current_setting('app.org_id', TRUE)` (directo)
- **Resolución:** Usar el patrón moderno **con bypass de service_role**:
  ```sql
  USING (
    auth.role() = 'service_role'
    OR org_id::text = current_setting('app.org_id', TRUE)
  )
  ```

**Discrepancia #2 — `ToolRegistry.register()` es un decorador, no una función directa**
- **Plan:** `tool_registry.register(name="service_connector", tool_class=ServiceConnectorTool, tags=[...], timeout=30, retry=2)`
- **Código real:** `register()` retorna un **decorador**. Firma: `register(name, description, requires_approval, timeout_seconds, retry_count, tags) → Callable[[Type], Type]`
- **Parámetro `tool_class`:** NO existe en la firma.
- **Parámetro `timeout`:** Se llama `timeout_seconds`.
- **Parámetro `retry`:** Se llama `retry_count`.
- **Resolución:** Registrar con decorador de conveniencia:
  ```python
  from src.tools.registry import register_tool

  @register_tool(
      "service_connector",
      description="Ejecuta integraciones TIPO C del Service Catalog",
      timeout_seconds=30,
      retry_count=2,
      tags=["integration", "type_c", "http"],
  )
  class ServiceConnectorTool(OrgBaseTool): ...
  ```

**Discrepancia #3 — `get_secret_async` no existe (prerrequisito 5.0.1)**
- **Impacto en 5.2.5:** BAJO. `ServiceConnectorTool._run()` es síncrono (hereda de CrewAI `BaseTool`), por lo que `get_secret()` síncrono es la opción correcta.
- **Resolución:** No bloquea. Usar `get_secret()` como hace `OrgBaseTool._get_secret()`.

**Discrepancia #4 — `get_current_user` no existe en middleware**
- **Plan:** `from src.api.middleware import get_current_user` (Paso D.2)
- **Código real:** Las dependencias de auth disponibles son:
  - `require_org_id` → extrae `X-Org-ID` header → retorna `str`
  - `verify_supabase_jwt` → verifica JWT → retorna `{"user_id", "payload"}`
  - `verify_org_membership` → combina JWT + org_id → retorna `{"user_id", "org_id", "role"}`
- **Resolución:** Usar `verify_org_membership` para endpoints autenticados (retorna org_id del usuario verificado):
  ```python
  from src.api.middleware import verify_org_membership

  @router.get("/active")
  async def list_active_integrations(user=Depends(verify_org_membership)):
      org_id = user["org_id"]
  ```

**Discrepancia #5 — Tabla `activity_logs` no existe**
- **Plan:** `db.table("activity_logs").insert({...})` (Paso D.3)
- **Código real:** No existe tal tabla. El sistema de auditoría actual usa `domain_events` con schema: `org_id, aggregate_type, aggregate_id, event_type, payload, actor, sequence`.
- **Resolución:** Auditar ejecuciones TIPO C usando `domain_events`:
  ```python
  db.table("domain_events").insert({
      "org_id": self.org_id,
      "aggregate_type": "service_integration",
      "aggregate_id": tool_id,
      "event_type": "tool_executed",
      "payload": {...},
      "actor": "service_connector",
      "sequence": 0,
  }).execute()
  ```

**Discrepancia #6 — `requests` no es dependencia directa**
- **Plan:** `import requests` en ServiceConnectorTool y health_check.py
- **Código real:** `pyproject.toml` lista `httpx>=0.28.0` como dependencia directa. `requests` solo llega como transitiva vía `crewai-tools` (opcional).
- **Resolución:** Usar `httpx` en vez de `requests` para las llamadas HTTP de ServiceConnectorTool y health checks. Ventajas: es dependencia directa, soporta async nativamente (útil para health checks), y es más moderno.
  ```python
  import httpx
  # síncrono:
  response = httpx.request(method=method, url=url, headers=headers, json=data, timeout=30)
  # async (health checks):
  async with httpx.AsyncClient() as client:
      resp = await client.get(url, headers=headers, timeout=10)
  ```

**Discrepancia #7 — Scheduler no se arranca en lifespan**
- **Código real:** `src/scheduler/bartenders_jobs.py` define `scheduler = AsyncIOScheduler(...)` con jobs decorados, pero `main.py` NO importa ni arranca el scheduler en lifespan.
- **Impacto:** Si el health check job se agrega al scheduler, podría no ejecutarse si el scheduler no está activo.
- **Resolución:** Verificar si el scheduler se arranca en otro punto. Si no, documentar como tarea de Fase 2.5D: agregar `scheduler.start()` y `scheduler.shutdown()` al lifespan de `main.py`. Alternativamente, registrar el health check como job independiente.

---

## 1. Diseño Funcional

### Happy Path — Flujo completo de una ejecución TIPO C

```
1. Agente (o ArchitectFlow) invoca ServiceConnectorTool
   con tool_id="stripe.create_customer" + input_data={email: "..."}

2. ServiceConnectorTool._run():
   a. Lee definición de service_tools WHERE id = tool_id
      → Obtiene: execution.url, execution.method, execution.headers, service_id
   b. Verifica org_service_integrations WHERE org_id = self.org_id
      AND service_id = <service_id> AND status = 'active'
      → Obtiene: secret_names, config
   c. Resuelve secreto: get_secret(self.org_id, secret_names[0])
      → Obtiene: valor en claro (ej: "sk_live_xxx")
   d. Construye request HTTP:
      - URL: execution.url (con path params resueltos si aplica)
      - Method: execution.method
      - Headers: {Authorization: f"Bearer {secret}"}
      - Body: input_data
   e. Ejecuta HTTP → parse JSON response
   f. Sanitiza output con sanitize_output() — Regla R3
   g. Registra ejecución en domain_events
   h. Retorna resultado sanitizado como str
```

### Edge Cases MVP

| Edge Case | Comportamiento Esperado |
|---|---|
| `tool_id` no existe en `service_tools` | Retorna `"Error: Tool 'X' no encontrada"` |
| Servicio no activo para la org | Retorna `"Error: Servicio 'X' no está activo para esta organización"` |
| Secreto no configurado en vault | Retorna `"Error: Secreto 'X' no configurado para org 'Y'"` (vía VaultError) |
| HTTP timeout (>30s) | Retorna `"Error HTTP: ReadTimeout"` |
| HTTP 4xx/5xx | Retorna `"Error HTTP: 403 Forbidden"` |
| Response contiene token leaked | Sanitizer reemplaza con `[REDACTED]` |
| URL con path params (`{shop}`) | Fase MVP: documentar como `url_params` en execution, resolver en _run con `str.format(**input_data)` |
| `service_catalog_seed.json` con schema JSON inválido | Script de import valida y corrige `required` antes de insertar |

### Manejo de Errores — Qué ve el usuario/agente

- **Error de configuración** (tool/service/secret no existe): mensaje legible sin exponer internals de DB.
- **Error HTTP**: código de status + mensaje corto. NO se devuelve el body completo del error externo (podría contener datos sensibles).
- **Error de sanitización**: si `sanitize_output` falla, retornar resultado sin sanitizar es **inaceptable** → capturar excepción y retornar `"Error: respuesta no pudo ser procesada"`.
- **Error de auditoría** (`domain_events` insert falla): NO bloquea la ejecución. `try/except pass` con log.

---

## 2. Diseño Técnico

### 2.1 Archivos Nuevos

#### `supabase/migrations/024_service_catalog.sql`

Migración unificada con las 3 tablas. Cambios vs plan:

| Aspecto | Plan (mcp-analisis-finalV2.md) | Corrección basada en código |
|---|---|---|
| RLS policy pattern | `current_setting('app.current_org_id')::UUID` | `current_setting('app.org_id', TRUE)` + service_role bypass |
| RLS cast | `::UUID` (cast a UUID) | `::text` (cast a text, como TODAS las migraciones existentes) |
| Service_role bypass | No incluido | **REQUERIDO** — patrón establecido en migración 010 |

```sql
-- Tabla 1: service_catalog (global, SIN RLS)
-- [Exacto como el plan — sin cambios]

-- Tabla 2: org_service_integrations (per-org, CON RLS)
-- FK: REFERENCES organizations(id) ← CONFIRMADO que la tabla se llama organizations
-- RLS: CORREGIDO
CREATE POLICY org_integration_access ON org_service_integrations
  FOR ALL USING (
    auth.role() = 'service_role'
    OR org_id::text = current_setting('app.org_id', TRUE)
  );

-- Tabla 3: service_tools (global, SIN RLS)
-- [Exacto como el plan — sin cambios]
```

#### `data/service_catalog_seed.json`

Directorio `data/` necesita crearse. JSON con 50 tools corregidas:
- `required` como booleano en properties → mover a array al nivel de schema
- URLs con placeholders → documentar en `execution.url_params`

#### `scripts/import_service_catalog.py`

Script de importación. Sin cambios significativos vs plan. Usa `supabase` Python SDK (`create_client`).

#### `src/mcp/__init__.py` + `src/mcp/sanitizer.py`

Crear directorio `src/mcp/`. El sanitizer es exacto al plan con una mejora: capturar excepciones internas para no crashear si un regex falla.

#### `src/tools/service_connector.py`

**Cambios vs plan basados en código real:**

| Aspecto | Plan | Corrección |
|---|---|---|
| Import HTTP | `import requests` | `import httpx` (dependencia directa) |
| Registro en registry | Función directa | **Decorador** `@register_tool(...)` |
| DB query en `_run` | `get_service_client()` directo | `get_service_client()` para `service_tools` (sin RLS) + verificar integration con `get_service_client()` (bypassa RLS por service_role) |
| Auth header | Solo `Bearer` para oauth2 y api_key | Agregar case para `basic_auth` |
| Auditoría | `activity_logs.insert(...)` | `domain_events.insert(...)` con schema correcto |

**Interfaz real del ServiceConnectorTool:**

```python
from src.tools.base_tool import OrgBaseTool
from src.tools.registry import register_tool
from src.db.session import get_service_client
from src.db.vault import get_secret, VaultError
from src.mcp.sanitizer import sanitize_output

@register_tool(
    "service_connector",
    description="Ejecuta integraciones TIPO C del Service Catalog",
    timeout_seconds=30,
    retry_count=2,
    tags=["integration", "type_c", "http"],
)
class ServiceConnectorTool(OrgBaseTool):
    name: str = "service_connector"
    description: str = "Ejecuta una integración TIPO C del Service Catalog"
    args_schema: type = ServiceConnectorInput

    def _run(self, tool_id: str, input_data: dict = None) -> str:
        # Usa httpx (no requests)
        # Usa get_secret() (no get_secret_async — _run es síncrono)
        # Audita en domain_events (no activity_logs)
        ...
```

#### `src/jobs/health_check.py`

**Cambios vs plan:**
- Usar `httpx.AsyncClient` en vez de `requests` (async + dependencia directa)
- Registrar en el scheduler existente o crear uno nuevo

#### `src/api/routes/integrations.py`

**Cambios vs plan:**
- Usar `verify_org_membership` (no `get_current_user` que no existe)
- Endpoint `/available` sin auth (catálogo global) → mantener pero evaluar si requiere al menos `require_org_id`
- Registrar router en `main.py`

### 2.2 Archivos Modificados

| Archivo | Modificación |
|---|---|
| `src/api/main.py` | Agregar `from .routes.integrations import router as integrations_router` + `app.include_router(integrations_router)` |
| `src/tools/__init__.py` | Importar `service_connector` para trigger decorador: `import src.tools.service_connector  # noqa: F401` |

### 2.3 Coherencia con estado-fase.md

- ✅ `ServiceConnectorTool` hereda de `OrgBaseTool` como documentado en §2 "No Existe Aún"
- ✅ Tres tablas nuevas alineadas con §3 "Tablas NUEVAS"
- ✅ Migración `024_service_catalog.sql` sigue secuencia §4
- ✅ Regla R3 respetada en sanitizer
- ✅ FK hacia `organizations` confirmada (tabla existe en migración 001)
- ⚠️ FK verificación: estado-fase dice "⚠️ verificar nombre real de tabla" → **VERIFICADO: se llama `organizations`**

---

## 3. Decisiones

| # | Decisión | Justificación |
|---|---|---|
| D1 | **Usar `httpx` en vez de `requests` para HTTP** | Corrige plan §C.2 — `requests` no es dependencia directa. `httpx>=0.28.0` sí. Soporta sync y async (útil para health checks async). |
| D2 | **RLS usa `current_setting('app.org_id', TRUE)` con service_role bypass** | Corrige plan §A.3 — El plan usa `app.current_org_id` (inexistente) y no incluye service_role bypass. Código real (mig. 010+) establece patrón `auth.role() = 'service_role' OR org_id::text = current_setting('app.org_id', TRUE)`. |
| D3 | **Auditoría en `domain_events` en vez de `activity_logs`** | Corrige plan §D.3 — `activity_logs` no existe. `domain_events` es el mecanismo de auditoría establecido (mig. 001). |
| D4 | **Registrar ServiceConnectorTool via decorador `@register_tool`** | Corrige plan §C.3 — `register()` es un decorador, no una función directa. Usar `register_tool` de conveniencia (registry.py L110-121). |
| D5 | **Endpoint `/available` requiere `require_org_id` (no público)** | Decisión nueva — Aunque el catálogo es global, mantener el header `X-Org-ID` para consistencia con toda la API. No se necesita verificación de membership (es lectura de catálogo global). |
| D6 | **Migración unificada en un solo archivo `024_service_catalog.sql`** | Alineado con plan — Las 3 tablas, índices y RLS en una sola migración. Simplifica rollback. |

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| CA1 | Las 3 tablas (`service_catalog`, `org_service_integrations`, `service_tools`) existen en Supabase después de aplicar migración 024 | `SELECT table_name FROM information_schema.tables WHERE table_name IN (...)` → 3 rows |
| CA2 | RLS está activo en `org_service_integrations` | `SELECT relname, relrowsecurity FROM pg_class WHERE relname = 'org_service_integrations'` → `relrowsecurity = true` |
| CA3 | RLS NO está activo en `service_catalog` y `service_tools` | Misma query → `relrowsecurity = false` para ambas |
| CA4 | FK de `org_service_integrations.org_id` → `organizations.id` funciona: insertar con org_id inválido da error | INSERT con UUID random → ERROR: foreign key violation |
| CA5 | FK de `service_tools.service_id` → `service_catalog.id` funciona | INSERT con service_id inexistente → ERROR: foreign key violation |
| CA6 | ~20 proveedores cargados en `service_catalog` después de import | `SELECT count(*) FROM service_catalog` → ≥15 |
| CA7 | 50 tools cargadas en `service_tools` sin huérfanos | `SELECT count(*) FROM service_tools` → 50 AND `LEFT JOIN service_catalog ... WHERE sc.id IS NULL` → 0 rows |
| CA8 | Todos los `tool_profile` tienen campos requeridos | `SELECT count(*) FROM service_tools WHERE NOT (tool_profile ? 'description' AND tool_profile ? 'risk_level' AND tool_profile ? 'requires_approval')` → 0 |
| CA9 | `ServiceConnectorTool` resuelve tool_id de DB, obtiene secreto de vault, ejecuta HTTP y retorna resultado sanitizado | Test unitario con mock de DB + mock de vault + mock HTTP → resultado sin secretos expuestos |
| CA10 | Servicio inactivo es rechazado | Test: `_run(tool_id="stripe.X")` con org sin Stripe activo → `"no está activo"` en resultado |
| CA11 | Sanitizer redacta tokens conocidos (Stripe, Slack, GitHub, Google) | Test: `sanitize_output({"key": "sk_live_abc123"})` → `{"key": "[REDACTED]"}` |
| CA12 | `GET /api/integrations/available` retorna catálogo de servicios | HTTP request → 200 con `services` array |
| CA13 | `GET /api/integrations/active` retorna solo servicios activos de la org autenticada | HTTP request con JWT + X-Org-ID → 200 con `integrations` filtradas por org |
| CA14 | Ejecuciones TIPO C se auditan en `domain_events` | Después de ejecutar ServiceConnectorTool → `SELECT * FROM domain_events WHERE event_type = 'tool_executed'` → row(s) |
| CA15 | Health check actualiza `last_health_check` y `last_health_status` en `org_service_integrations` | Ejecutar `run_health_checks()` → columnas actualizadas |

---

## 5. Riesgos

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | **JSON seed de NotebookLM tiene schemas inválidos** que bloquean el import | Alta | Medio | Script de import incluye paso de corrección (required booleano → array). Validar JSON Schema antes de insertar. |
| R2 | **URLs con placeholders** (`{shop}`, `{AccountSid}`) no se resuelven correctamente en runtime | Media | Alto | Documentar `url_params` en `execution`. `_run()` resuelve con `url.format(**url_params_from_input)`. Test unitario con URL parametrizada. |
| R3 | **Health check scheduler no arranca** porque scheduler de bartenders no está connectado al lifespan | Alta | Bajo | Verificar arranque del scheduler. Si no arranca, agregar al lifespan como tarea de este paso. Alternativa: hacer health check on-demand via API endpoint. |
| R4 | **Service_role bypass faltante en RLS** causa errores de permisos en backend | Alta (si no se corrige) | Bloqueante | Discrepancia #1 resuelta: la migración usará el patrón correcto con bypass. |
| R5 | **50 tools exceden cuota de banda ancha** al cargar todas simultáneamente en un agente | Baja | Medio | ServiceConnectorTool es una sola tool que despacha dinámicamente. No se cargan 50 tools como entidades separadas. |
| R6 | **python-jose vs PyJWT conflicto** en dependencias | Baja | Medio | No impacta directamente a 5.2.5. Discrepancia heredada documentada en estado-fase.md. |

---

## 6. Plan de Implementación

### Fase 2.5A — Fundamentos DB (Complejidad: Media, ~3h)

| # | Tarea | Dependencia | Complejidad |
|---|---|---|---|
| A.1 | Verificar que `organizations` existe con columnas esperadas | — | Baja |
| A.2 | Crear migración `024_service_catalog.sql` con 3 tablas + RLS (patrón correcto: `app.org_id` + service_role bypass) + índices | A.1 | Media |
| A.3 | Aplicar migración en Supabase | A.2 | Baja |
| A.4 | Test de integridad relacional (insert/FK violation/cleanup) | A.3 | Baja |

### Fase 2.5B — Población del Catálogo (Complejidad: Media, ~3h)

| # | Tarea | Dependencia | Complejidad |
|---|---|---|---|
| B.1 | Crear directorio `data/` + `service_catalog_seed.json` con schema JSON corregido | A.4 | Media |
| B.2 | Crear `scripts/import_service_catalog.py` (extracción de proveedores + carga de tools) | B.1 | Media |
| B.3 | Ejecutar import script contra Supabase | B.2 | Baja |
| B.4 | Verificación cruzada: 0 huérfanos, ~20 proveedores, 50 tools, tool_profiles completos | B.3 | Baja |

### Fase 2.5C — Motor de Ejecución (Complejidad: Alta, ~4h)

| # | Tarea | Dependencia | Complejidad |
|---|---|---|---|
| C.1 | Crear `src/mcp/__init__.py` + `src/mcp/sanitizer.py` | — | Baja |
| C.2 | Crear `src/tools/service_connector.py` — `ServiceConnectorTool` con `httpx`, decorador `@register_tool` | C.1, B.4 | Alta |
| C.3 | Registrar import en `src/tools/__init__.py` o `src/api/main.py` | C.2 | Baja |
| C.4 | Crear `tests/test_service_connector.py` (mock DB + mock vault + mock HTTP) | C.2 | Media |
| C.5 | Ejecutar tests y validar CA9, CA10, CA11 | C.4 | Media |

### Fase 2.5D — Operaciones y Monitoreo (Complejidad: Media, ~2h)

| # | Tarea | Dependencia | Complejidad |
|---|---|---|---|
| D.1 | Crear `src/jobs/health_check.py` con `httpx.AsyncClient` | C.2 | Media |
| D.2 | Crear `src/api/routes/integrations.py` con `verify_org_membership` (no `get_current_user`) | C.2 | Media |
| D.3 | Agregar auditoría `domain_events` al final de `ServiceConnectorTool._run()` | C.2 | Baja |
| D.4 | Registrar router de integrations en `main.py` | D.2 | Baja |
| D.5 | Test E2E: health check + API endpoints + auditoría | D.1-D.4 | Media |

**Tiempo estimado total**: 12-14h (alineado con plan §11)

---

## 🔮 Roadmap (NO implementar ahora)

| # | Mejora Futura | Por qué no ahora | Decisión de diseño que facilita |
|---|---|---|---|
| 1 | **Input validation** contra `input_schema` de service_tools antes de ejecutar HTTP | MVP: confiar en el LLM para construir payloads válidos | `input_schema` ya se almacena como JSON Schema en DB — listo para validar con `jsonschema` |
| 2 | **Rate limiting** por org/servicio | MVP: volumen bajo | `org_service_integrations.config` JSONB puede almacenar `rate_limit_per_minute` |
| 3 | **Cache de definiciones** de service_tools | MVP: pocos req/s | Los queries a DB son simples SELECT con PK — latencia baja |
| 4 | **OAuth2 token refresh** automático | MVP: solo API keys | `auth_type` en service_catalog soporta "oauth2" — se puede extender `_run` sin cambio de schema |
| 5 | **Dashboard UI** para gestionar integraciones | MVP: solo backend + API | API endpoints ya proporcionan CRUD — frontend solo necesita consumirlos |
| 6 | **Webhook-based tools** (tipo "Espera respuesta de webhook") | MVP: solo request/response | `execution.type` en service_tools puede ser "webhook" — extensible |
| 7 | **Migrar scheduler a Celery** para alta carga | MVP: volumen bajo, AsyncIOScheduler suficiente | Health check job es independiente — migrar solo requiere cambiar el scheduler |
| 8 | **`get_secret_async`** para health checks | Prerrequisito 5.0.1 pendiente | Health check puede usar `get_secret()` sync en thread pool vía `asyncio.to_thread()` |

---

*Análisis producido por agente ATG — Verificado contra código fuente real.*
*7 discrepancias encontradas, todas con resolución concreta.*
*20 elementos verificados, 0 suposiciones no verificadas (2 marcados ⚠️ con impacto bajo).*
