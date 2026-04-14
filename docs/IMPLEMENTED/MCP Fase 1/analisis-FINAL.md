# Análisis FINAL — Paso 5.2.5: Service Catalog TIPO C

**Proceso:** UNIFICACIÓN  
**Fuentes:** `analisis-atg.md`, `analisis-kilo.md`, `analisis-oc.md`, `analisis-qwen.md`  
**Contexto:** `docs/estado-fase.md` | `docs/mcp-analisis-finalV2.md`  
**Fecha:** 2026-04-13

---

## 0. Evaluación de Análisis y Verificaciones

### Tabla de Evaluación de Agentes

| Agente | Verificó código | §0 explícita | Discrepancias detectadas | Evidencia sólida (archivo+línea) | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| **ATG** | ✅ | ✅ (20 items) | 7 (todas con resolución) | ✅ Sí — cita archivo, línea, grep | **5** |
| **Qwen** | ✅ | ✅ (18 items) | 7 (D1-D6 con resolución) | ✅ Sí — cita archivo, línea | **4** |
| **Kilo** | ✅ | ✅ (10 items) | 5 (con resolución) | ⚠️ Parcial — menos detalle en evidencia | **3** |
| **OC** | ⚠️ Parcial | ✅ (10 items) | 4 (resoluciones incompletas) | ⚠️ Item #10 sin verificar, asume que funciona | **2** |

### Análisis de Confiabilidad

- **ATG (Score 5):** Verificación más exhaustiva (20 items). Detecta discrepancias críticas que otros omiten: `requests` vs `httpx` (#6), scheduler no arrancado en lifespan (#7), y documenta la existencia de `register_tool` como convenience decorator (L110-121 de registry.py). **Fuente primaria para resolución de conflictos.**
- **Qwen (Score 4):** Segunda verificación más completa (18 items). Detecta que `src/jobs/` no existe (Discrepancia D3 — única en proponerlo). Propone `structlog` como alternativa de auditoría pero es la opción correcta para MVP.
- **Kilo (Score 3):** Verificación correcta pero menos profunda. Coincide con ATG/Qwen en discrepancias principales (RLS, registry, activity_logs) pero con menos evidencia.
- **OC (Score 2):** El item #10 marca `app.current_org_id` como "⚠️ No verificado — asumir que funciona", cuando **la variable no existe**. La decisión de crear `activity_logs` como tabla nueva contradice la evidencia de `domain_events`. Sin embargo, el diseño funcional es sólido.

### Discrepancias Críticas Encontradas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | **RLS usa `app.current_org_id` (inexistente)** — Plan §A.3 L104 | ATG, Qwen, Kilo | ✅ `001_set_config_rpc.sql` L37-44: `current_org_id()` → `current_setting('app.org_id', TRUE)` | Usar patrón `auth.role() = 'service_role' OR org_id::text = current_org_id()` — consistente con migración 010 |
| 2 | **`ToolRegistry.register()` es decorador, no función** — Plan §C.3 no compila | ATG, Qwen, Kilo, OC | ✅ `registry.py` L39-71: retorna `Callable[[Type], Type]`. `register_tool` convenience en L110-121 | Usar `@register_tool(name=..., ...)` decorador de conveniencia |
| 3 | **`get_current_user` no existe en middleware** — Plan §D.2 | ATG, Qwen | ✅ `grep -rn "get_current_user" src/api/` → 0 results. Existen: `require_org_id` (L103), `verify_org_membership` (L356) | Usar `verify_org_membership` para endpoints autenticados, `require_org_id` para endpoints ligeros |
| 4 | **`activity_logs` no existe** — Plan §D.3 | ATG, Qwen, Kilo, OC | ✅ `grep -r "activity_logs" supabase/ src/` → 0 results. `domain_events` existe: `001_set_config_rpc.sql` L87-97 | Usar `domain_events` para auditoría (schema: `org_id, aggregate_type, aggregate_id, event_type, payload, actor, sequence`) |
| 5 | **`requests` no es dependencia directa** — Plan §C.2 | ATG, Qwen | ✅ `pyproject.toml` L23: `httpx>=0.28.0`. `requests` no aparece en dependencies | Usar `httpx` en vez de `requests` para HTTP (sync con `httpx.Client`, async con `httpx.AsyncClient`) |
| 6 | **`src/jobs/` no existe** — Plan §D.1 | Qwen | ✅ `list_dir src/` → no contiene `jobs/`. `src/scheduler/` sí existe con `bartenders_jobs.py` | Usar `src/scheduler/health_check.py` en vez de `src/jobs/health_check.py` |
| 7 | **RLS cast `::UUID` incorrecto** — Plan §A.3 L104 usa `::UUID` | ATG (Unificador verificó) | ✅ Todas las migraciones usan cast `::text`: `org_id::text = current_org_id()`. `current_org_id()` retorna `TEXT` | Cast a `::text`, NO `::UUID` |

### Correcciones al Plan General (`mcp-analisis-finalV2.md`)

1. **Corrige §A.3 (L103-104):** RLS policy debe usar `current_org_id()` con cast `::text` y bypass de `service_role`, NO `current_setting('app.current_org_id')::UUID`.
2. **Corrige §C.2 (L497):** Usar `httpx` en vez de `requests`.
3. **Corrige §C.3 (L521-531):** `tool_registry.register()` es decorador — usar `@register_tool()`.
4. **Corrige §D.1 (L579):** Ubicar health check en `src/scheduler/` en vez de `src/jobs/`.
5. **Corrige §D.2 (L649):** Usar `verify_org_membership` en vez de `get_current_user` inexistente.
6. **Corrige §D.3 (L694):** Auditar en `domain_events` en vez de `activity_logs` inexistente.

---

## 1. Resumen Ejecutivo

Este paso implementa el **Service Catalog TIPO C** — un catálogo de integraciones REST genéricas definidas en base de datos que permite a agentes externos (y al propio ArchitectFlow) ejecutar acciones contra servicios como Stripe, Twilio, GitHub, etc., sin código hardcodeado para cada proveedor.

El Service Catalog se compone de 3 tablas (`service_catalog`, `org_service_integrations`, `service_tools`), un script de importación para 50 tools pre-definidas, un `ServiceConnectorTool` genérico que lee definiciones de DB y ejecuta HTTP dinámicamente respetando la Regla R3 (secretos nunca llegan al LLM), y endpoints REST para consultar integraciones.

Este paso es el **5.2.5** de la Fase 5 (Ecosistema Agéntico MCP). Puede ejecutarse en paralelo con el paso 5.2. Requiere que la migración 024 sea la siguiente en la secuencia establecida (001-023 existentes).

**Correcciones al plan necesarias: 6.** El plan original (`mcp-analisis-finalV2.md`) tiene 6 discrepancias verificadas contra código fuente, todas resueltas en este documento. El implementador debe seguir este documento, NO el plan original para estos aspectos.

---

## 2. Diseño Funcional Consolidado

### 2.1 Happy Path — Flujo E2E de una ejecución TIPO C

*Fuente: ATG §1 (más detallado), complementado por Qwen §1 y OC §1.1.*

```
1. Agente (o ArchitectFlow) invoca ServiceConnectorTool
   con tool_id="stripe.create_customer" + input_data={"email": "test@test.com"}

2. ServiceConnectorTool._run():
   a. Lee definición de service_tools WHERE id = tool_id
      → JOIN service_catalog para obtener: auth_type, base_url
      → Obtiene: execution.url, execution.method, execution.headers, service_id
   b. Verifica org_service_integrations WHERE org_id = self.org_id
      AND service_id = <service_id> AND status = 'active'
      → Obtiene: secret_names, config
   c. Resuelve secreto: get_secret(self.org_id, secret_names[0])
      → Obtiene: valor en claro (ej: "sk_live_xxx")
   d. Construye request HTTP con httpx:
      - URL: execution.url (con path params resueltos si aplica)
      - Method: execution.method
      - Headers: {Authorization: f"Bearer {secret}"}
      - Body: input_data (para POST/PUT/PATCH) o params (para GET)
   e. Ejecuta HTTP → parse JSON response
   f. Sanitiza output con sanitize_output() — Regla R3
   g. Registra ejecución en domain_events (best-effort, no bloquea)
   h. Retorna resultado sanitizado como str
```

### 2.2 Edge Cases MVP

*Fuente: ATG §1 (más completo), complementado por Qwen §1 y OC §1.2.*

| Edge Case | Comportamiento Esperado |
|---|---|
| `tool_id` no existe en `service_tools` | Retorna `"Error: Tool 'X' no encontrada en service_tools"` |
| Servicio no activo para la org | Retorna `"Error: Servicio 'X' no está activo para esta organización"` |
| Secreto no configurado en vault | `VaultError` → Retorna `"Error: Secreto 'X' no configurado para org 'Y'"` |
| HTTP timeout (>30s) | Retorna `"Error HTTP: ReadTimeout"` |
| HTTP 4xx/5xx | Retorna `"Error HTTP: {status_code}"` (NO incluir body de error externo — podría contener datos sensibles) |
| Response contiene token leaked | Sanitizer reemplaza con `[REDACTED]` |
| URL con path params (`{shop}`) | Documentar como `url_params` en `execution`. `_run` resuelve con `url.format(**input_data)` en MVP |
| JSON seed con schemas inválidos | Script de import valida y corrige `required` booleano → array antes de insertar |
| Response no es JSON válido | Fallback a `response.text[:500]` |
| Sanitizer falla internamente | Retornar `"Error: respuesta no pudo ser procesada"` — **NUNCA** retornar output sin sanitizar |

### 2.3 Manejo de Errores — Qué ve el usuario/agente

*Fuente: ATG §1 (decisión de ATG sobre sanitizer superior).* 

- **Error de configuración** (tool/service/secret no existe): mensaje legible sin exponer internals de DB.
- **Error HTTP**: código de status + mensaje corto. NO se devuelve el body completo del error externo.
- **Error de sanitización**: si `sanitize_output` falla, retornar error genérico. Retornar resultado sin sanitizar es **inaceptable** (Regla R3).
- **Error de auditoría** (`domain_events` insert falla): NO bloquea la ejecución. `try/except pass` con log via `structlog`.

---

## 3. Diseño Técnico Definitivo

### 3.1 Archivos Nuevos

#### 3.1.1 `supabase/migrations/024_service_catalog.sql`

Migración unificada con las 3 tablas. **Correcciones vs plan basadas en código verificado:**

| Aspecto | Plan Original | Corrección (evidencia) |
|---|---|---|
| Variable RLS | `current_setting('app.current_org_id')::UUID` | `current_org_id()` — helper SQL (`001_set_config_rpc.sql` L37-44) |
| Cast RLS | `::UUID` | `::text` — todas las migraciones existentes usan cast a TEXT |
| Service_role bypass | No incluido | **REQUERIDO** — patrón de `010_service_role_rls_bypass.sql` L44-48 |

```sql
-- =============================================================
-- Migration 024: Service Catalog TIPO C
-- 3 tablas: service_catalog, org_service_integrations, service_tools
-- =============================================================

-- Tabla 1: service_catalog (global, SIN RLS)
CREATE TABLE IF NOT EXISTS service_catalog (
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

CREATE INDEX IF NOT EXISTS idx_service_catalog_category
  ON service_catalog(category);

-- Tabla 2: org_service_integrations (per-org, CON RLS)
CREATE TABLE IF NOT EXISTS org_service_integrations (
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

-- ⚠️ CORREGIDO: Patrón de mig. 010 con service_role bypass + current_org_id() text cast
CREATE POLICY org_integration_access ON org_service_integrations
  FOR ALL USING (
    auth.role() = 'service_role'
    OR org_id::text = current_org_id()
  );

CREATE INDEX IF NOT EXISTS idx_org_integrations_org
  ON org_service_integrations(org_id);
CREATE INDEX IF NOT EXISTS idx_org_integrations_status
  ON org_service_integrations(org_id, status);

-- Tabla 3: service_tools (global, SIN RLS)
CREATE TABLE IF NOT EXISTS service_tools (
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

CREATE INDEX IF NOT EXISTS idx_service_tools_service
  ON service_tools(service_id);
```

**Interfaces existentes usadas:**
- `organizations(id)` — `001_set_config_rpc.sql:53` — UUID PK ✅ VERIFICADO
- `current_org_id()` — `001_set_config_rpc.sql:37-44` — retorna TEXT ✅ VERIFICADO
- Patrón `auth.role() = 'service_role' OR org_id::text = current_org_id()` — `010_service_role_rls_bypass.sql:44-48` ✅ VERIFICADO

---

#### 3.1.2 `data/service_catalog_seed.json`

*Fuente: Plan §B.1 (sin cambios significativos). ATG detecta que `data/` no existe.*

- Directorio `data/` debe crearse.
- JSON con 50 tools generadas por NotebookLM.
- **Corrección de schemas requerida:** `required` como booleano en properties → mover a array al nivel de `input_schema` (JSON Schema Draft 7).
- URLs con placeholders → documentar en `execution.url_params`.

---

#### 3.1.3 `scripts/import_service_catalog.py`

*Fuente: Plan §B.2-B.4 (aceptado en esencia). Sin cambios significativos.*

- Lee `data/service_catalog_seed.json`.
- Extrae proveedores únicos → inserta en `service_catalog`.
- Convierte cada tool al schema de `service_tools` → inserta.
- Verifica integridad: 0 huérfanos, todos los `tool_profile` completos.
- Requiere `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` como env vars.

---

#### 3.1.4 `src/mcp/__init__.py` + `src/mcp/sanitizer.py`

*Fuente: Plan §C.1. ATG y Qwen coinciden completamente. Mejora de ATG: capturar excepciones internas.*

Crear directorio `src/mcp/`. El sanitizer garantiza Regla R3 como última línea de defensa:

```python
# src/mcp/sanitizer.py
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

SECRET_PATTERNS = [
    r'sk_live_[a-zA-Z0-9]+',           # Stripe live keys
    r'sk_test_[a-zA-Z0-9]+',           # Stripe test keys
    r'Bearer [a-zA-Z0-9\-._~+/]+=*',  # Bearer tokens
    r'Basic [a-zA-Z0-9+/]+=*',         # Basic auth
    r'xox[bpsa]-[a-zA-Z0-9\-]+',       # Slack tokens
    r'ghp_[a-zA-Z0-9]+',               # GitHub PATs
    r'AIza[a-zA-Z0-9\-_]+',            # Google API keys
]

def sanitize_output(data: Any) -> Any:
    """Elimina cualquier secreto filtrado en el output. Regla R3."""
    try:
        if isinstance(data, str):
            for pattern in SECRET_PATTERNS:
                data = re.sub(pattern, '[REDACTED]', data)
            return data
        elif isinstance(data, dict):
            return {k: sanitize_output(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [sanitize_output(item) for item in data]
        return data
    except Exception as e:
        logger.error("Sanitizer error: %s", e)
        return "[ERROR: output no pudo ser procesado]"
```

---

#### 3.1.5 `src/tools/service_connector.py`

*Fuente principal: ATG §2.1 (más correcciones vs plan). Complementado por Qwen §2.2 y OC §2.2.*

**Cambios vs plan basados en código real:**

| Aspecto | Plan | Corrección |
|---|---|---|
| HTTP library | `import requests` | `import httpx` — dependencia directa (`pyproject.toml` L23) |
| Registro | `tool_registry.register(name=..., tool_class=...)` | `@register_tool(name=..., ...)` — decorador (`registry.py` L110-121) |
| Auditoría | `activity_logs.insert(...)` | `domain_events.insert(...)` — schema: `org_id, aggregate_type, aggregate_id, event_type, payload, actor, sequence` |
| Auth para apis | Solo `Bearer` | Agregar case para `basic_auth` y `api_key` (header vs query param) |

**Interfaz definitiva (verificada contra código fuente):**

```python
# src/tools/service_connector.py
import httpx
import logging
import structlog
from typing import Type
from pydantic import BaseModel, Field

from src.tools.base_tool import OrgBaseTool          # base_tool.py L17
from src.tools.registry import register_tool          # registry.py L110
from src.db.session import get_service_client          # session.py L48
from src.db.vault import get_secret, VaultError        # vault.py L23, L18
from src.mcp.sanitizer import sanitize_output

logger = structlog.get_logger(__name__)


class ServiceConnectorInput(BaseModel):
    """Input genérico para ServiceConnectorTool."""
    tool_id: str = Field(description="ID de la tool (ej: stripe.create_customer)")
    input_data: dict = Field(default_factory=dict, description="Parámetros de la tool")


@register_tool(
    "service_connector",
    description="Ejecuta integraciones TIPO C del Service Catalog",
    timeout_seconds=30,
    retry_count=2,
    tags=["integration", "type_c", "http"],
)
class ServiceConnectorTool(OrgBaseTool):
    """Tool genérica que ejecuta cualquier integración TIPO C
    leyendo su definición de la tabla service_tools.

    Flujo (§10.5.4):
    1. Verificar que la org tiene el servicio activo
    2. Leer definición de la tool (execution, headers, url)
    3. Resolver secreto del Vault (Regla R3)
    4. Ejecutar HTTP con httpx
    5. Retornar resultado sanitizado
    """
    name: str = "service_connector"
    description: str = "Ejecuta una integración TIPO C del Service Catalog"
    args_schema: Type[BaseModel] = ServiceConnectorInput

    def _run(self, tool_id: str, input_data: dict = None) -> str:
        input_data = input_data or {}
        db = get_service_client()  # service_role, bypass RLS

        # 1. Obtener definición de la tool
        tool_result = (
            db.table("service_tools")
            .select("*, service_catalog!inner(id, auth_type, base_url)")
            .eq("id", tool_id)
            .single()
            .execute()
        )
        if not tool_result.data:
            return f"Error: Tool '{tool_id}' no encontrada en service_tools"

        tool_def = tool_result.data
        service_id = tool_def["service_id"]

        # 2. Verificar que la org tiene el servicio activo
        integration = (
            db.table("org_service_integrations")
            .select("*")
            .eq("org_id", self.org_id)
            .eq("service_id", service_id)
            .eq("status", "active")
            .maybe_single()
            .execute()
        )
        if not integration.data:
            return f"Error: Servicio '{service_id}' no está activo para esta organización"

        # 3. Resolver secreto (REGLA R3)
        secret_names = integration.data.get("secret_names", [])
        secret_value = None
        if secret_names:
            try:
                secret_value = get_secret(self.org_id, secret_names[0])
            except VaultError as e:
                return f"Error: {e}"

        # 4. Ejecutar HTTP con httpx
        execution = tool_def["execution"]
        url = execution["url"]
        method = execution.get("method", "POST").upper()
        headers = dict(execution.get("headers", {}))

        # Inyectar auth header según tipo
        if secret_value:
            auth_type = tool_def.get("service_catalog", {}).get("auth_type", "api_key")
            if auth_type == "oauth2":
                headers["Authorization"] = f"Bearer {secret_value}"
            elif auth_type == "basic_auth":
                import base64
                headers["Authorization"] = f"Basic {base64.b64encode(secret_value.encode()).decode()}"
            else:  # api_key (default)
                headers["Authorization"] = f"Bearer {secret_value}"

        response = None
        try:
            with httpx.Client(timeout=30) as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=input_data if method in ("POST", "PUT", "PATCH") else None,
                    params=input_data if method == "GET" else None,
                )
                response.raise_for_status()
                try:
                    result = response.json()
                except Exception:
                    result = response.text[:500]
        except httpx.HTTPStatusError as e:
            result = f"Error HTTP: {e.response.status_code}"
        except httpx.RequestError as e:
            result = f"Error HTTP: {str(e)}"

        # 5. Sanitizar output (REGLA R3 — última línea de defensa)
        sanitized = sanitize_output(result)

        # 6. Auditar en domain_events (best-effort)
        try:
            db.table("domain_events").insert({
                "org_id": self.org_id,
                "aggregate_type": "service_integration",
                "aggregate_id": tool_id,
                "event_type": "tool_executed",
                "payload": {
                    "tool_id": tool_id,
                    "service_id": service_id,
                    "http_status": response.status_code if response else None,
                    "success": response.is_success if response else False,
                },
                "actor": "service_connector",
                "sequence": 0,
            }).execute()
        except Exception:
            logger.warning("audit_failed", tool_id=tool_id)

        return str(sanitized)
```

**Interfaces existentes usadas:**
- `OrgBaseTool` — `base_tool.py` L17: hereda `crewai.tools.BaseTool`, tiene `org_id: str`, `_get_secret()`. ✅
- `register_tool` — `registry.py` L110-121: convenience decorator, params `name, description, timeout_seconds, retry_count, tags`. ✅
- `get_service_client()` — `session.py` L48-66: singleton lazy, service_role (bypass RLS). ✅
- `get_secret(org_id, secret_name)` — `vault.py` L23-61: síncrono, lanza `VaultError`. ✅
- `domain_events` — `001_set_config_rpc.sql` L87-97: schema `(id, org_id, aggregate_type, aggregate_id, event_type, payload, actor, sequence, created_at)`. ✅

---

#### 3.1.6 `src/scheduler/health_check.py`

*Fuente: Qwen §2.4 (mejor ubicación — `src/scheduler/` en vez de `src/jobs/`). ATG §2 para implementación.*

```python
# src/scheduler/health_check.py
import httpx
import logging
from datetime import datetime, timezone

from src.db.session import get_service_client
from src.db.vault import get_secret

logger = logging.getLogger(__name__)


async def run_health_checks():
    """Health check para integraciones activas con health_check_url definida."""
    db = get_service_client()

    integrations = (
        db.table("org_service_integrations")
        .select("*, service_catalog!inner(health_check_url, auth_type)")
        .eq("status", "active")
        .not_.is_("service_catalog.health_check_url", "null")
        .execute()
    )

    async with httpx.AsyncClient(timeout=10) as client:
        for integration in integrations.data:
            health_url = integration["service_catalog"]["health_check_url"]
            org_id = integration["org_id"]

            try:
                secret = None
                secret_names = integration.get("secret_names", [])
                if secret_names:
                    secret = get_secret(org_id, secret_names[0])

                headers = {}
                if secret:
                    headers["Authorization"] = f"Bearer {secret}"

                resp = await client.get(health_url, headers=headers)
                status = "ok" if resp.status_code < 400 else "error"
                error_msg = None if status == "ok" else f"HTTP {resp.status_code}"

            except Exception as e:
                status = "timeout" if "timeout" in str(e).lower() else "error"
                error_msg = str(e)[:200]

            db.table("org_service_integrations").update({
                "last_health_check": datetime.now(timezone.utc).isoformat(),
                "last_health_status": status,
                "error_message": error_msg,
            }).eq("id", integration["id"]).execute()
```

**Ubicación:** `src/scheduler/` — coherente con `bartenders_jobs.py` existente.

**Registro del job:** Agregar en el punto de arranque del scheduler (a determinar — ver Riesgo R3):
```python
scheduler.add_job(run_health_checks, 'interval', minutes=30, id='health_check')
```

> ⚠️ **Nota del Unificador:** El scheduler de `bartenders_jobs.py` usa `AsyncIOScheduler` pero NO se verifica que esté arrancado en `main.py`. El implementador debe verificar si el scheduler se arranca en algún punto y, si no, conectarlo al lifespan de FastAPI. Alternativamente, crear un endpoint on-demand `POST /api/integrations/health-check` como fallback.

---

#### 3.1.7 `src/api/routes/integrations.py`

*Fuente: Plan §D.2, corregido por ATG/Qwen. Decisión: usar `verify_org_membership` para `/active`, `require_org_id` para `/available`.*

```python
# src/api/routes/integrations.py
from fastapi import APIRouter, Depends
from src.api.middleware import require_org_id, verify_org_membership
from src.db.session import get_service_client

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/available")
async def list_available_services(org_id: str = Depends(require_org_id)):
    """Retorna el catálogo global de servicios (para Dashboard UI)."""
    db = get_service_client()
    result = db.table("service_catalog").select("*").execute()
    return {"services": result.data}


@router.get("/active")
async def list_active_integrations(user=Depends(verify_org_membership)):
    """Retorna las integraciones activas de la org del usuario autenticado."""
    org_id = user["org_id"]
    db = get_service_client()
    result = (
        db.table("org_service_integrations")
        .select("*, service_catalog(name, category, logo_url)")
        .eq("org_id", org_id)
        .eq("status", "active")
        .execute()
    )
    return {"integrations": result.data}


@router.get("/tools/{service_id}")
async def list_service_tools(service_id: str, org_id: str = Depends(require_org_id)):
    """Retorna las tools disponibles para un servicio."""
    db = get_service_client()
    result = (
        db.table("service_tools")
        .select("id, name, tool_profile")
        .eq("service_id", service_id)
        .execute()
    )
    return {"tools": result.data}
```

**Interfaces existentes usadas:**
- `require_org_id` — `middleware.py` L103-118: extrae `X-Org-ID` header. ✅
- `verify_org_membership` — `middleware.py` L356-412: verifica JWT + membresía org → retorna `{"user_id", "org_id", "role"}`. ✅

---

### 3.2 Archivos Modificados

| Archivo | Modificación | Por qué |
|---|---|---|
| `src/api/main.py` | Agregar `from src.api.routes.integrations import router as integrations_router` + `app.include_router(integrations_router)` | Registrar los nuevos endpoints |
| `src/tools/__init__.py` | Agregar `import src.tools.service_connector  # noqa: F401` | Trigger del decorador `@register_tool` para que la tool se registre al importar el módulo |

---

### 3.3 Coherencia con estado-fase.md

| Aspecto | Estado | Evidencia |
|---|---|---|
| `ServiceConnectorTool` hereda de `OrgBaseTool` | ✅ | estado-fase §2 "No Existe Aún" — ServiceConnectorTool. `base_tool.py` L17 ✅ |
| 3 tablas nuevas alineadas | ✅ | estado-fase §3 "Tablas NUEVAS" — exactamente las 3 definidas |
| Migración `024_service_catalog.sql` sigue secuencia | ✅ | estado-fase §4 — migraciones incrementales |
| Regla R3 respetada | ✅ | Sanitizer + Vault pattern |
| FK `organizations` confirmada | ✅ | estado-fase §3 dice "⚠️ verificar nombre" → **VERIFICADO: `organizations`** en migración 001 L53 |
| PyJWT (no python-jose) en middleware | ✅ | No impacta directamente este paso. `middleware.py` L54: `import jwt as pyjwt` |

---

## 4. Decisiones Tecnológicas

| # | Decisión | Justificación | Corrige Plan |
|---|---|---|---|
| D1 | **Usar `httpx` en vez de `requests`** | `httpx>=0.28.0` es dependencia directa (`pyproject.toml` L23). `requests` NO está en deps. `httpx` soporta sync (`Client`) y async (`AsyncClient`). Detectado por ATG, confirmado por Qwen. | ✅ Corrige plan §C.2 |
| D2 | **RLS: `auth.role() = 'service_role' OR org_id::text = current_org_id()`** | Patrón establecido en migración 010 (L44-48). El plan usa variable `app.current_org_id` que **no existe**; la real es `app.org_id` via helper `current_org_id()`. 4 de 4 agentes lo detectaron. | ✅ Corrige plan §A.3 |
| D3 | **Auditoría en `domain_events`** | `activity_logs` no existe en ninguna migración (0 results en grep). `domain_events` existe desde migración 001 (L87-97) con schema compatible. ATG propone schema de insert verificado. **OC propone crear `activity_logs` nueva — descartado por falta de evidencia de necesidad.** | ✅ Corrige plan §D.3 |
| D4 | **`@register_tool()` decorador** | `ToolRegistry.register()` es decorador (L39-71). `register_tool` es convenience (L110-121). El plan llama `register(tool_class=...)` — parámetro inexistente. 4 de 4 detectaron. | ✅ Corrige plan §C.3 |
| D5 | **`verify_org_membership` en endpoint `/active`** | `get_current_user` no existe. ATG documenta alternativas: `require_org_id`, `verify_supabase_jwt`, `verify_org_membership`. Para `/active` se necesita auth completa → `verify_org_membership`. | ✅ Corrige plan §D.2 |
| D6 | **Health check en `src/scheduler/`, NO `src/jobs/`** | `src/jobs/` no existe. `src/scheduler/` ya existe con `bartenders_jobs.py` y APScheduler. Detectado por Qwen (único). | ✅ Corrige plan §D.1 |
| D7 | **`ServiceConnectorTool._run()` es síncrono con `get_secret()`** | `_run()` hereda de CrewAI `BaseTool` (síncrono). `get_secret_async` no existe (prerrequisito 5.0.1 pendiente). No bloquea este paso. Todos los agentes coinciden. | No — coherente con plan |
| D8 | **Endpoint `/available` con `require_org_id`** | Aunque el catálogo es global, mantener `X-Org-ID` header para consistencia con toda la API REST existente. No se verifica membership (es lectura de catálogo global). Decisión propia del unificador apoyada en ATG D5. | Decisión nueva |

---

## 5. Criterios de Aceptación MVP ✅

### Funcionales

| # | Criterio | Cómo verificar |
|---|---|---|
| CA1 | **Las 3 tablas existen** | `SELECT table_name FROM information_schema.tables WHERE table_name IN ('service_catalog', 'org_service_integrations', 'service_tools')` → 3 rows |
| CA2 | **RLS activo en `org_service_integrations`** | `SELECT relname, relrowsecurity FROM pg_class WHERE relname = 'org_service_integrations'` → `relrowsecurity = true` |
| CA3 | **RLS NO activo en `service_catalog` y `service_tools`** | Misma query → `relrowsecurity = false` para ambas |
| CA4 | **FK `organizations` funciona** | `INSERT INTO org_service_integrations (org_id, service_id) VALUES (gen_random_uuid(), '_test')` → ERROR foreign key violation |
| CA5 | **~20 proveedores cargados** | `SELECT count(*) FROM service_catalog` → ≥15 |
| CA6 | **50 tools cargadas sin huérfanos** | `SELECT count(*) FROM service_tools` → 50 AND `SELECT st.id FROM service_tools st LEFT JOIN service_catalog sc ON st.service_id = sc.id WHERE sc.id IS NULL` → 0 rows |
| CA7 | **Todos los `tool_profile` completos** | `SELECT count(*) FROM service_tools WHERE NOT (tool_profile ? 'description' AND tool_profile ? 'risk_level' AND tool_profile ? 'requires_approval')` → 0 |

### Técnicos

| # | Criterio | Cómo verificar |
|---|---|---|
| CA8 | **`ServiceConnectorTool` resuelve tool de DB + secreto + HTTP + sanitiza** | Test unitario: mock DB + mock Vault + mock HTTP → resultado sin secretos expuestos |
| CA9 | **Servicio inactivo es rechazado** | Test: `_run(tool_id="stripe.X")` con org sin Stripe activo → string contiene `"no está activo"` |
| CA10 | **Sanitizer redacta tokens conocidos** | Test: `sanitize_output({"key": "sk_live_abc123"})` → `{"key": "[REDACTED]"}` |
| CA11 | **Tool registrada en ToolRegistry** | `from src.tools.registry import tool_registry; assert "service_connector" in tool_registry.list_tools()` |
| CA12 | **`GET /api/integrations/available`** retorna 200 | HTTP request con `X-Org-ID` header → 200 con `{"services": [...]}` |
| CA13 | **`GET /api/integrations/active`** retorna solo servicios de la org | HTTP request con JWT + `X-Org-ID` → 200 con `{"integrations": [...]}` filtradas |
| CA14 | **Ejecuciones auditadas en `domain_events`** | Después de ejecutar ServiceConnectorTool → `SELECT * FROM domain_events WHERE event_type = 'tool_executed' AND aggregate_type = 'service_integration'` → row(s) |

### Robustez

| # | Criterio | Cómo verificar |
|---|---|---|
| CA15 | **Si tool no existe, retorna error legible** | `_run(tool_id="no_existe")` → string contiene `"no encontrada"` |
| CA16 | **Si secreto falta, retorna error sin crashear** | `_run(tool_id="stripe.X")` con secreto inexistente → string contiene `"Error"`, no exception |
| CA17 | **Si auditoría falla, tool retorna resultado** | Mock `domain_events.insert()` para que falle → tool retorna resultado igualmente |
| CA18 | **Health check actualiza status** | Ejecutar `run_health_checks()` → `SELECT last_health_check, last_health_status FROM org_service_integrations` → columnas actualizadas |

---

## 6. Plan de Implementación

### Fase 2.5A — Fundamentos DB (Complejidad: Media, ~3h)

| # | Tarea | Dependencia | Complejidad | ⚠️ Requiere corrección vs plan |
|---|---|---|---|---|
| A.1 | Verificar que `organizations` existe con PK `id UUID` | — | Baja | No |
| A.2 | Crear migración `024_service_catalog.sql` con 3 tablas + RLS (patrón `current_org_id()` + service_role bypass) + índices | A.1 | Media | **Sí — RLS pattern, cast, bypass** |
| A.3 | Aplicar migración en Supabase | A.2 | Baja | No |
| A.4 | Test de integridad relacional (insert/FK violation/cleanup) | A.3 | Baja | No |

### Fase 2.5B — Población del Catálogo (Complejidad: Media, ~3h)

| # | Tarea | Dependencia | Complejidad | ⚠️ Requiere corrección vs plan |
|---|---|---|---|---|
| B.1 | Crear directorio `data/` + `service_catalog_seed.json` con schemas JSON corregidos | A.4 | Media | No |
| B.2 | Crear `scripts/import_service_catalog.py` (extract providers + extract tools + main) | B.1 | Media | No |
| B.3 | Ejecutar import script contra Supabase | B.2 | Baja | No |
| B.4 | Verificación cruzada: 0 huérfanos, ≥15 proveedores, 50 tools, tool_profiles completos | B.3 | Baja | No |

### Fase 2.5C — Motor de Ejecución (Complejidad: Alta, ~4h)

| # | Tarea | Dependencia | Complejidad | ⚠️ Requiere corrección vs plan |
|---|---|---|---|---|
| C.1 | Crear `src/mcp/__init__.py` + `src/mcp/sanitizer.py` | — | Baja | No |
| C.2 | Crear `src/tools/service_connector.py` — `ServiceConnectorTool` con `httpx`, `@register_tool`, auditoría en `domain_events` | C.1, B.4 | Alta | **Sí — httpx, decorador, domain_events** |
| C.3 | Registrar import en `src/tools/__init__.py` | C.2 | Baja | No |
| C.4 | Crear `tests/test_service_connector.py` (mock DB + mock vault + mock HTTP) | C.2 | Media | No |
| C.5 | Ejecutar tests y validar CA8, CA9, CA10, CA11, CA15, CA16, CA17 | C.4 | Media | No |

### Fase 2.5D — Operaciones y Monitoreo (Complejidad: Media, ~2.5h)

| # | Tarea | Dependencia | Complejidad | ⚠️ Requiere corrección vs plan |
|---|---|---|---|---|
| D.1 | Crear `src/scheduler/health_check.py` con `httpx.AsyncClient` | C.2 | Media | **Sí — ubicación `src/scheduler/`, httpx** |
| D.2 | Crear `src/api/routes/integrations.py` con `verify_org_membership` | C.2 | Media | **Sí — middleware correcto** |
| D.3 | Registrar router de integrations en `main.py` | D.2 | Baja | No |
| D.4 | Test E2E: health check + API endpoints + CA12, CA13, CA14, CA18 | D.1-D.3 | Media | No |

**Tiempo estimado total:** 12-14h

---

## 7. Riesgos y Mitigaciones

| # | Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | **JSON seed de NotebookLM tiene schemas inválidos** que bloquean el import | Alta | Medio | Script de import incluye paso de corrección (`required` booleano → array). Validar JSON Schema antes de insertar. |
| R2 | **URLs con placeholders** (`{shop}`, `{AccountSid}`) no se resuelven en runtime | Media | Alto | `_run()` resuelve con `url.format(**input_data)`. Test unitario con URL parametrizada obligatorio. |
| R3 | **Health check scheduler no arranca** porque scheduler de bartenders no está conectado al lifespan | Alta | Bajo | Verificar arranque del scheduler al implementar. Alternativa: endpoint on-demand `POST /api/integrations/health-check`. |
| R4 | **Service_role bypass faltante en RLS** causa errores de permisos en backend | Alta (si no se corrige) | Bloqueante | Discrepancia #1 resuelta: la migración usa el patrón correcto con bypass. |
| R5 | **Implementador copia plan sin aplicar correcciones** — las 6 correcciones documentadas aquí no se aplican | Media | Bloqueante | Este documento marca **"⚠️ Requiere corrección vs plan"** en cada tarea afectada. El implementador debe usar ESTE documento como fuente de verdad, NO `mcp-analisis-finalV2.md`. |
| R6 | **50 tools como una sola entrada sobrecargan contexto del LLM** | Baja | Medio | `ServiceConnectorTool` es una sola tool que despacha por `tool_id`. El LLM solo ve 1 tool, no 50 separadas. |

---

## 8. Testing Mínimo Viable

Alineado 1:1 con criterios de aceptación:

| Test | Cubre CA | Tipo |
|---|---|---|
| Migración 024 se ejecuta sin errores | CA1, CA2, CA3 | SQL |
| Insert con FK inválida falla | CA4 | SQL |
| Import script carga ≥15 proveedores, 50 tools, 0 huérfanos | CA5, CA6, CA7 | Script |
| `ServiceConnectorTool._run()` con mocks completos | CA8 | Unit |
| `_run()` rechaza servicio inactivo | CA9 | Unit |
| `sanitize_output()` con Stripe key → `[REDACTED]` | CA10 | Unit |
| Tool aparece en `tool_registry.list_tools()` | CA11 | Unit |
| `GET /api/integrations/available` retorna 200 | CA12 | HTTP |
| `GET /api/integrations/active` retorna integraciones filtradas | CA13 | HTTP |
| `domain_events` contiene audit record post-ejecución | CA14 | SQL |
| `_run()` con tool inexistente retorna error legible | CA15 | Unit |
| `_run()` con secreto faltante no crashea | CA16 | Unit |
| `_run()` retorna resultado aun si auditoría falla | CA17 | Unit |
| `run_health_checks()` actualiza status en DB | CA18 | Async |

---

## 9. 🔮 Roadmap (NO implementar ahora)

*Consolidado de los 4 análisis (ATG §Roadmap, Qwen §Roadmap, Kilo §Roadmap, OC §Roadmap).*

| # | Mejora Futura | Por qué no ahora | Decisión de diseño que facilita |
|---|---|---|---|
| 1 | **Input validation** contra `input_schema` de service_tools | MVP: confiar en el LLM para construir payloads válidos | `input_schema` ya almacenado como JSON Schema en DB |
| 2 | **Rate limiting** por org/servicio | MVP: volumen bajo | `org_service_integrations.config` JSONB puede almacenar `rate_limit_per_minute` |
| 3 | **Cache de definiciones** de service_tools | MVP: pocos req/s | SELECT con PK — latencia baja |
| 4 | **OAuth2 token refresh** automático | MVP: solo API keys | `auth_type` en service_catalog soporta "oauth2" — extensible sin cambio de schema |
| 5 | **Dashboard UI** para gestionar integraciones | MVP: solo backend + API | API endpoints ya proporcionan lectura — frontend solo necesita consumirlos |
| 6 | **`get_secret_async`** wrapper | Prerrequisito 5.0.1 pendiente — no bloquea 5.2.5 | Health check puede usar `asyncio.to_thread(get_secret, ...)` como workaround |
| 7 | **Tabla `activity_logs` dedicada** | MVP: `domain_events` + `structlog` suficiente | Schema de `domain_events` es extensible vía `payload` JSONB |
| 8 | **`mcp>=1.0.0` como dependencia directa** | Necesario para Fase 5.1, no para 5.2.5 | Service Catalog funciona sin ella |
| 9 | **Soporte multi-secret** por tool | MVP: 1 secret por integración | `secret_names` es JSONB array — extensible |
| 10 | **Migrar scheduler a Celery** | MVP: volumen bajo, APScheduler suficiente | Health check job independiente — migración trivial |

---

*Documento FINAL producido por proceso de UNIFICACIÓN.*
*4 análisis evaluados. 7 discrepancias del plan resueltas con evidencia de código fuente.*
*20+ elementos verificados contra migraciones 001-023 y código en `src/`.*
*6 correcciones al plan general documentadas y marcadas en el plan de implementación.*
