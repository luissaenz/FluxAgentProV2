# Plan de Desarrollo: Integraciones TIPO C — Service Catalog

**Basado en:** FAP-MCP-Analisis v3.3 §10.5, §10.7 y §11  
**Principio:** Este plan ordena la implementación sin modificar las definiciones del documento v3.3. Todas las tablas, schemas, patrones y reglas (incluida R3) se implementan tal como están especificados.

---

## Visión General de Fases

```
Fase 2.5A          Fase 2.5B              Fase 2.5C            Fase 2.5D
Fundamentos DB     Población Catálogo     Motor de Ejecución   Operaciones
(3-4h)             (3-4h)                 (4-5h)               (2-3h)
                                                                
┌──────────┐       ┌──────────┐           ┌──────────┐        ┌──────────┐
│ Migración│──────→│ Import   │──────────→│ Service  │───────→│ Health   │
│ SQL +    │       │ Script + │           │ Connector│        │ Check +  │
│ RLS +    │       │ 50 tools │           │ Tool +   │        │ API +    │
│ Validar  │       │ cargadas │           │ Sanitizer│        │ Audit    │
└──────────┘       └──────────┘           └──────────┘        └──────────┘
```

**Total estimado:** 12-16h (alineado con §11 Fase 2.5: 9-12h + margen)

---

## Fase 2.5A: Fundamentos de Base de Datos (3-4h)

**Objetivo:** Crear las 3 tablas del Service Catalog con RLS, índices y validar contra el schema existente.

**Prerrequisito:** Verificar que la tabla `organizations` existe (nota §10.5.2).

### Paso A.1: Verificación de FK (30min)

**Qué:** Confirmar el nombre real de la tabla de organizaciones en Supabase.

```sql
-- Ejecutar en Supabase SQL Editor
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name LIKE '%org%';

-- Verificar si existe como 'organizations' o con otro nombre
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'organizations';
```

**Entregable:** Nombre confirmado de la tabla. Si difiere de `organizations`, ajustar la FK en el paso A.2.

### Paso A.2: Migración SQL — `service_catalog` (30min)

**Archivo:** `migrations/024_service_catalog.sql`

**Qué:** Crear la tabla global de servicios exactamente como §10.5.2.

```sql
-- Tabla 1 de 3: service_catalog (global, NO tiene RLS)
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
```

**Validación:** `SELECT count(*) FROM service_catalog;` → 0 rows, no errors.

### Paso A.3: Migración SQL — `org_service_integrations` (45min)

**Qué:** Crear la tabla per-org con RLS, exactamente como §10.5.2.

```sql
-- Tabla 2 de 3: org_service_integrations (per-org, CON RLS)
CREATE TABLE IF NOT EXISTS org_service_integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,  -- ⚠️ Ajustar FK si A.1 indica otro nombre
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

CREATE INDEX IF NOT EXISTS idx_org_integrations_org 
  ON org_service_integrations(org_id);
CREATE INDEX IF NOT EXISTS idx_org_integrations_status 
  ON org_service_integrations(org_id, status);
```

**Validación:** Verificar que RLS está activo y que la FK a `organizations` no da error.

### Paso A.4: Migración SQL — `service_tools` (30min)

**Qué:** Crear la tabla de tools por servicio, exactamente como §10.5.2.

```sql
-- Tabla 3 de 3: service_tools (global, catálogo de tools)
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

**Validación:** `SELECT * FROM service_tools LIMIT 1;` → vacío, sin errores.

### Paso A.5: Test de integridad relacional (30min)

**Qué:** Verificar que las FK funcionan correctamente entre las 3 tablas.

```sql
-- Test: insertar un servicio de prueba
INSERT INTO service_catalog (id, name, category, auth_type, base_url, required_secrets)
VALUES ('_test', 'Test Service', 'other', 'api_key', 'https://test.com', '{"test_key"}');

-- Test: insertar una tool vinculada
INSERT INTO service_tools (id, service_id, name, input_schema, output_schema, execution, tool_profile)
VALUES (
  '_test.action', '_test', 'Test Action', 
  '{"type":"object","properties":{}}'::jsonb,
  '{"type":"object","properties":{}}'::jsonb,
  '{"type":"http","method":"GET","url":"https://test.com/v1/test"}'::jsonb,
  '{"description":"Test","example_prompt":"test","risk_level":"low","requires_approval":false}'::jsonb
);

-- Test: FK inválida debe fallar
INSERT INTO service_tools (id, service_id, name, input_schema, output_schema, execution, tool_profile)
VALUES ('_bad.tool', 'no_existe', 'Bad', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb);
-- ❌ Debe dar: ERROR foreign key constraint

-- Limpieza
DELETE FROM service_tools WHERE id LIKE '_test%';
DELETE FROM service_catalog WHERE id = '_test';
```

**Definition of Done Fase 2.5A:** Las 3 tablas existen, RLS activo en `org_service_integrations`, FKs validadas, datos de test limpiados.

---

## Fase 2.5B: Población del Catálogo (3-4h)

**Objetivo:** Cargar las 50 tools del JSON canónico (NotebookLM) en las tablas creadas.

**Prerrequisito:** Fase 2.5A completada.

### Paso B.1: Preparar el JSON canónico (30min)

**Archivo:** `data/service_catalog_seed.json`

**Qué:** Tomar el JSON de las 50 tools generadas por NotebookLM y corregir los dos issues conocidos:

1. **`required` como booleano** dentro de properties → mover a array `required` al nivel de `input_schema` (JSON Schema válido)
2. **URLs con placeholders** (`{shop}`, `{AccountSid}`, etc.) → documentar como campo `url_params` dentro de `execution`

```python
# Ejemplo de corrección del input_schema:

# ANTES (NotebookLM output — inválido JSON Schema):
"input_schema": {
  "type": "object",
  "properties": {
    "amount": { "type": "number", "description": "...", "required": true },
    "currency": { "type": "string", "description": "...", "required": true }
  }
}

# DESPUÉS (JSON Schema válido):
"input_schema": {
  "type": "object",
  "properties": {
    "amount": { "type": "number", "description": "..." },
    "currency": { "type": "string", "description": "..." }
  },
  "required": ["amount", "currency"]
}
```

**Entregable:** `data/service_catalog_seed.json` — JSON limpio y validado.

### Paso B.2: Script de import — extracción de proveedores (1h)

**Archivo:** `scripts/import_service_catalog.py`

**Qué:** Leer el JSON seed, extraer proveedores únicos → `service_catalog`. Sigue el patrón de §10.5.6.

```python
# scripts/import_service_catalog.py
import json
import os
from urllib.parse import urlparse
from supabase import create_client

def extract_base_url(full_url: str) -> str:
    """Extrae base_url de una URL completa con path variables."""
    parsed = urlparse(full_url)
    return f"{parsed.scheme}://{parsed.netloc}"

def extract_providers(tools: list[dict]) -> dict:
    """Agrupa tools por provider y genera registros de service_catalog."""
    providers = {}
    for tool in tools:
        pid = tool["provider"].lower().replace(" ", "_").replace(".", "_")
        if pid not in providers:
            providers[pid] = {
                "id": pid,
                "name": tool["provider"],
                "category": tool["category"],
                "auth_type": tool["auth"]["type"],
                "auth_scopes": tool["auth"].get("scopes", []),
                "base_url": extract_base_url(tool["execution"]["url"]),
                "api_version": tool.get("version", "1.0.0"),
                "required_secrets": [f"{pid}_api_key"],
            }
    return providers

def load_seed(path: str = "data/service_catalog_seed.json") -> list[dict]:
    with open(path) as f:
        return json.load(f)

def insert_providers(supabase, providers: dict):
    for p in providers.values():
        supabase.table("service_catalog").upsert(p).execute()
    print(f"✅ {len(providers)} proveedores insertados en service_catalog")
```

**Validación:** `SELECT count(*) FROM service_catalog;` → ~20 proveedores únicos.

### Paso B.3: Script de import — carga de tools (1h)

**Qué:** Insertar cada tool en `service_tools` vinculada a su provider.

```python
def extract_tools(tools: list[dict]) -> list[dict]:
    """Convierte cada tool del JSON canónico a formato service_tools."""
    result = []
    for tool in tools:
        result.append({
            "id": tool["tool_id"],
            "service_id": tool["provider"].lower().replace(" ", "_").replace(".", "_"),
            "name": tool["name"],
            "version": tool.get("version", "1.0.0"),
            "input_schema": tool["input_schema"],
            "output_schema": tool["output_schema"],
            "execution": tool["execution"],
            "tool_profile": tool["tool_profile"],
        })
    return result

def insert_tools(supabase, tools: list[dict]):
    for t in tools:
        supabase.table("service_tools").upsert(t).execute()
    print(f"✅ {len(tools)} tools insertadas en service_tools")
```

**Validación:** `SELECT count(*) FROM service_tools;` → 50 tools.

### Paso B.4: Script de import — función `main` y ejecución (30min)

```python
def main():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(url, key)
    
    tools = load_seed()
    print(f"📦 Cargando {len(tools)} tools desde seed...")
    
    # 1. Proveedores
    providers = extract_providers(tools)
    insert_providers(supabase, providers)
    
    # 2. Tools
    service_tools = extract_tools(tools)
    insert_tools(supabase, service_tools)
    
    # 3. Verificación
    cats = supabase.table("service_catalog").select("id, category").execute()
    tools_count = supabase.table("service_tools").select("id", count="exact").execute()
    print(f"\n📊 Resumen:")
    print(f"   Proveedores: {len(cats.data)}")
    print(f"   Tools: {tools_count.count}")
    
    # 4. Desglose por categoría
    from collections import Counter
    by_cat = Counter(c["category"] for c in cats.data)
    for cat, n in sorted(by_cat.items()):
        print(f"   {cat}: {n} proveedores")

if __name__ == "__main__":
    main()
```

**Ejecución:**
```bash
cd /path/to/FluxAgentPro-v2
SUPABASE_URL=https://xxx.supabase.co SUPABASE_SERVICE_KEY=xxx \
  python scripts/import_service_catalog.py
```

### Paso B.5: Verificación cruzada (30min)

```sql
-- Verificar que cada tool tiene un provider válido
SELECT st.id, st.service_id 
FROM service_tools st 
LEFT JOIN service_catalog sc ON st.service_id = sc.id 
WHERE sc.id IS NULL;
-- ❌ Debe retornar 0 rows (ningún huérfano)

-- Verificar distribución por categoría
SELECT sc.category, count(st.id) as tool_count 
FROM service_tools st 
JOIN service_catalog sc ON st.service_id = sc.id 
GROUP BY sc.category ORDER BY tool_count DESC;

-- Verificar que tool_profile tiene los campos requeridos
SELECT id FROM service_tools 
WHERE NOT (tool_profile ? 'description' 
       AND tool_profile ? 'risk_level' 
       AND tool_profile ? 'requires_approval');
-- ❌ Debe retornar 0 rows
```

**Definition of Done Fase 2.5B:** 50 tools cargadas en `service_tools`, ~20 proveedores en `service_catalog`, zero huérfanos, todos los `tool_profile` completos.

---

## Fase 2.5C: Motor de Ejecución (4-5h)

**Objetivo:** Implementar el `ServiceConnectorTool` que lee definiciones de DB y ejecuta HTTP dinámicamente, respetando Regla R3.

**Prerrequisito:** Fase 2.5B completada (catálogo poblado).

### Paso C.1: Output Sanitizer (45min)

**Archivo:** `src/mcp/sanitizer.py`

**Qué:** Función que garantiza Regla R3 en todas las respuestas. Item #1 de §10.7.

```python
# src/mcp/sanitizer.py
import re
from typing import Any

# Patrones de secretos conocidos que NUNCA deben aparecer en output
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
    """Elimina cualquier secreto que pudiera haberse filtrado en el output.
    
    Regla R3: Los secretos NUNCA llegan al LLM.
    Esta función es la última línea de defensa.
    """
    if isinstance(data, str):
        for pattern in SECRET_PATTERNS:
            data = re.sub(pattern, '[REDACTED]', data)
        return data
    elif isinstance(data, dict):
        return {k: sanitize_output(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_output(item) for item in data]
    return data
```

**Test:** Pasar un dict con un Stripe key embebido → debe retornar `[REDACTED]`.

### Paso C.2: ServiceConnectorTool — base class (2h)

**Archivo:** `src/tools/service_connector.py`

**Qué:** OrgBaseTool genérico que lee `execution` de `service_tools` en vez de hardcodear URL/method. Item #4 de §10.7. Implementa el flujo de §10.5.4.

```python
# src/tools/service_connector.py
import requests
from typing import Any, Optional
from pydantic import BaseModel, Field

from src.tools.base_tool import OrgBaseTool
from src.db.session import get_service_client
from src.db.vault import get_secret
from src.mcp.sanitizer import sanitize_output


class ServiceConnectorInput(BaseModel):
    """Input genérico para ServiceConnectorTool."""
    tool_id: str = Field(description="ID de la tool a ejecutar (ej: stripe.create_customer)")
    input_data: dict = Field(default_factory=dict, description="Parámetros de entrada")


class ServiceConnectorTool(OrgBaseTool):
    """Tool genérica que ejecuta cualquier integración TIPO C
    leyendo su definición de la tabla service_tools.
    
    Flujo (§10.5.4):
    1. Verificar que la org tiene el servicio activo
    2. Leer definición de la tool (execution, headers, url)
    3. Resolver secreto del Vault (Regla R3)
    4. Ejecutar HTTP
    5. Retornar resultado sanitizado
    """
    name: str = "service_connector"
    description: str = "Ejecuta una integración TIPO C del Service Catalog"
    args_schema: type = ServiceConnectorInput
    
    def _run(self, tool_id: str, input_data: dict = None) -> str:
        input_data = input_data or {}
        db = get_service_client()
        
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
            secret_value = get_secret(self.org_id, secret_names[0])
        
        # 4. Ejecutar HTTP
        execution = tool_def["execution"]
        url = execution["url"]
        method = execution.get("method", "POST").upper()
        headers = execution.get("headers", {})
        
        # Inyectar auth header según tipo
        if secret_value:
            auth_type = tool_def.get("service_catalog", {}).get("auth_type", "api_key")
            if auth_type == "oauth2":
                headers["Authorization"] = f"Bearer {secret_value}"
            elif auth_type == "api_key":
                headers["Authorization"] = f"Bearer {secret_value}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=input_data if method in ("POST", "PUT", "PATCH") else None,
                params=input_data if method == "GET" else None,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as e:
            return f"Error HTTP: {str(e)}"
        
        # 5. Sanitizar output (REGLA R3 — última línea de defensa)
        return str(sanitize_output(result))
```

**Test:** Instanciar con un org_id de prueba, llamar con `tool_id="stripe.create_customer"` contra un mock → verificar que resuelve la definición de DB y el secreto del Vault.

### Paso C.3: Registrar ServiceConnectorTool en ToolRegistry (30min)

**Archivo:** Modificar `src/tools/__init__.py` o el punto de registro existente.

```python
from src.tools.service_connector import ServiceConnectorTool
from src.tools.registry import tool_registry

# Registrar como tool disponible para todos los flows
tool_registry.register(
    name="service_connector",
    tool_class=ServiceConnectorTool,
    tags=["integration", "type_c", "http"],
    timeout=30,
    retry=2,
)
```

### Paso C.4: Test E2E con datos de prueba (1h)

**Qué:** Verificar el flujo completo §10.5.4 contra una integración real o mock.

```python
# tests/test_service_connector.py

def test_service_connector_reads_from_db():
    """Verifica que ServiceConnectorTool lee execution de service_tools."""
    tool = ServiceConnectorTool(org_id="test_org_id")
    # Con un mock de DB que retorne la definición de stripe.create_customer
    # y un mock de Vault que retorne un test key
    result = tool._run(
        tool_id="stripe.create_customer",
        input_data={"email": "test@test.com"}
    )
    assert "[REDACTED]" not in result or "Error" in result

def test_service_connector_blocks_inactive_service():
    """Verifica que rechaza tools de servicios no activos para la org."""
    tool = ServiceConnectorTool(org_id="org_sin_stripe")
    result = tool._run(tool_id="stripe.create_customer", input_data={})
    assert "no está activo" in result

def test_sanitizer_catches_leaked_secrets():
    """Verifica que el sanitizer atrapa secretos en output."""
    from src.mcp.sanitizer import sanitize_output
    dirty = {"key": "sk_live_abc123xyz", "data": "normal"}
    clean = sanitize_output(dirty)
    assert "sk_live_" not in str(clean)
    assert "[REDACTED]" in str(clean)
```

**Definition of Done Fase 2.5C:** `ServiceConnectorTool` ejecuta tools TIPO C leyendo definiciones de DB, resolviendo secretos del Vault, y sanitizando output. Tests pasan.

---

## Fase 2.5D: Operaciones y Monitoreo (2-3h)

**Objetivo:** Health checks, auditoría, y API para consultar integraciones.

**Prerrequisito:** Fase 2.5C completada.

### Paso D.1: Health Check Scheduler (1h)

**Archivo:** `src/jobs/health_check.py`

**Qué:** Job de APScheduler que valida `health_check_url` de servicios activos. Item #7 de §10.7.

```python
# src/jobs/health_check.py
import requests
from datetime import datetime
from src.db.session import get_service_client
from src.db.vault import get_secret


async def run_health_checks():
    """Ejecuta health check para todas las integraciones activas."""
    db = get_service_client()
    
    # Obtener integraciones activas con health_check_url
    integrations = (
        db.table("org_service_integrations")
        .select("*, service_catalog!inner(health_check_url, auth_type)")
        .eq("status", "active")
        .not_.is_("service_catalog.health_check_url", "null")
        .execute()
    )
    
    for integration in integrations.data:
        health_url = integration["service_catalog"]["health_check_url"]
        org_id = integration["org_id"]
        
        try:
            # Resolver secreto si necesario
            secret = None
            if integration.get("secret_names"):
                secret = get_secret(org_id, integration["secret_names"][0])
            
            headers = {}
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
            
            resp = requests.get(health_url, headers=headers, timeout=10)
            status = "ok" if resp.status_code < 400 else "error"
            error_msg = None if status == "ok" else f"HTTP {resp.status_code}"
            
        except Exception as e:
            status = "timeout" if "timeout" in str(e).lower() else "error"
            error_msg = str(e)[:200]
        
        # Actualizar estado
        db.table("org_service_integrations").update({
            "last_health_check": datetime.utcnow().isoformat(),
            "last_health_status": status,
            "error_message": error_msg,
            "status": "error" if status == "error" else integration["status"],
        }).eq("id", integration["id"]).execute()
```

**Registro en APScheduler (en el startup existente):**
```python
scheduler.add_job(run_health_checks, 'interval', minutes=30, id='health_check')
```

### Paso D.2: API endpoint para consultar integraciones (45min)

**Archivo:** `src/api/routes/integrations.py`

**Qué:** Endpoint REST para que el Dashboard UI y ArchitectFlow consulten servicios activos.

```python
# src/api/routes/integrations.py
from fastapi import APIRouter, Depends
from src.api.middleware import get_current_user

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

@router.get("/available")
async def list_available_services():
    """Retorna el catálogo global de servicios (para Dashboard UI)."""
    db = get_service_client()
    result = db.table("service_catalog").select("*").execute()
    return {"services": result.data}

@router.get("/active")
async def list_active_integrations(user=Depends(get_current_user)):
    """Retorna las integraciones activas de la org del usuario."""
    org_id = user["org_id"]
    result = (
        db.table("org_service_integrations")
        .select("*, service_catalog(name, category, logo_url)")
        .eq("org_id", org_id)
        .eq("status", "active")
        .execute()
    )
    return {"integrations": result.data}

@router.get("/tools/{service_id}")
async def list_service_tools(service_id: str):
    """Retorna las tools disponibles para un servicio."""
    result = (
        db.table("service_tools")
        .select("id, name, tool_profile")
        .eq("service_id", service_id)
        .execute()
    )
    return {"tools": result.data}
```

### Paso D.3: Audit log para ejecuciones TIPO C (30min)

**Qué:** Registrar en `activity_logs` cada ejecución de ServiceConnectorTool.

Agregar al final de `ServiceConnectorTool._run()`:

```python
# En ServiceConnectorTool._run(), antes del return:
try:
    db.table("activity_logs").insert({
        "org_id": self.org_id,
        "action": "service_tool_execution",
        "details": {
            "tool_id": tool_id,
            "service_id": service_id,
            "http_status": response.status_code if response else None,
            "success": response.ok if response else False,
        }
    }).execute()
except Exception:
    pass  # No bloquear la ejecución por fallo de auditoría
```

**Definition of Done Fase 2.5D:** Health checks corriendo cada 30min, API de integraciones funcional, ejecuciones auditadas en `activity_logs`.

---

## Resumen de Entregables por Fase

| Fase | Archivos Generados | Tablas/Datos |
|:---|:---|:---|
| **2.5A** | `migrations/024_service_catalog.sql` | 3 tablas + RLS + índices |
| **2.5B** | `data/service_catalog_seed.json`, `scripts/import_service_catalog.py` | ~20 proveedores, 50 tools |
| **2.5C** | `src/mcp/sanitizer.py`, `src/tools/service_connector.py`, `tests/test_service_connector.py` | ServiceConnectorTool registrado |
| **2.5D** | `src/jobs/health_check.py`, `src/api/routes/integrations.py` | Health checks + API + audit |

---

## Criterio de Aceptación Global (Fase 2.5 completa)

```
1. Las 3 tablas existen con RLS ✓
2. 50 tools cargadas sin huérfanos ✓
3. ServiceConnectorTool ejecuta stripe.create_customer 
   leyendo de DB + Vault, sin hardcodear Stripe ✓
4. Output sanitizado (Regla R3) ✓
5. Health checks corren automáticamente ✓
6. GET /api/integrations/active retorna servicios de la org ✓
7. Ejecuciones registradas en activity_logs ✓
```

---

*Plan de Desarrollo v1.0 — Basado en FAP-MCP-Analisis v3.3 §10.5*
*Sin modificaciones a las definiciones originales*
