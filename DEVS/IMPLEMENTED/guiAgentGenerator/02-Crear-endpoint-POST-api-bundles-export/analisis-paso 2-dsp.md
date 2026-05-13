# Análisis Técnico — Paso 02: `POST /api/bundles/export`

> **Agente:** dsp  
> **Fecha:** 2026-05-13  
> **Fase:** guiAgentGenerator  
> **Objetivo del paso:** Endpoint REST que genera ZIP descargable con formato `bundle-schema-v2.md` a partir de agentes + skills del builder visual.

---

## 0. Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|-------------|--------|-----------|
| 1 | `src/api/routes/bundles.py` existe (destino del endpoint) | `Read` + grep de rutas existentes | ✅ | `src/api/routes/bundles.py:1` — archivo con 190 líneas, router en prefix `/api/bundles` |
| 2 | `src/api/main.py` ya importa y registra `bundles_router` | grep en `main.py` | ✅ | `src/api/main.py:23,111` — `from .routes.bundles import router as bundles_router` + `app.include_router(bundles_router)` |
| 3 | `BundleManager.create_bundle()` existe (core ZIP creation) | grep en `src/services/` | ✅ | `src/services/bundle_manager.py:197-245` — genera ZIP in-memory con hashes SHA256 automáticos |
| 4 | `BundleContent` Pydantic model | `Read` de `bundle_schemas.py` | ✅ | `src/services/bundle_schemas.py:45-58` — `manifest`, `agents: List[Dict]`, `flows: List[Dict]`, `skills: Dict[str,str]` |
| 5 | `BundleManifest` Pydantic model | `Read` de `bundle_schemas.py` | ✅ | `src/services/bundle_schemas.py:22-42` — `version`, `bundle_info`, `hashes` |
| 6 | `BundleInfo` Pydantic model | `Read` de `bundle_schemas.py` | ✅ | `src/services/bundle_schemas.py:13-20` — `name`, `description`, `version`, `author` |
| 7 | `require_org_id` middleware | `Read` de `middleware.py` | ✅ | `src/api/middleware.py:66` — `async def require_org_id(request: Request) -> str:` |
| 8 | `agent_catalog` tabla con schema correcto | `Read` de migración 004 | ✅ | `supabase/migrations/004_agent_catalog.sql:6-17` — `id UUID, org_id UUID, role TEXT, soul_json JSONB, allowed_tools TEXT[], max_iter INT, is_active BOOLEAN` |
| 9 | `bundle-schema-v2.md` (referencia de formato) | glob | ✅ | `docs/bundle-schema-v2.md` — define formato agents JSON con `role`, `soul_json`, `allowed_tools`, `max_iter`, `model`, `is_active` |
| 10 | `calculate_sha256()` función de hashing | `Read` de `integrity.py` | ✅ | `src/services/integrity.py:15-32` — retorna `sha256:<hex>` |
| 11 | `StreamingResponse` disponible en FastAPI | Dependencia estándar | ✅ | `fastapi>=0.115.0` en `proyecto-config.json` → `from fastapi.responses import StreamingResponse` |
| 12 | Endpoint `POST /api/bundles/export` NO existe aún | grep `export` en `src/api/routes/` | ✅ | Sin resultados → confirmado que no hay endpoint de export |
| 13 | `max_bundle_size_mb` en config | `Read` de `config.py` | ✅ | `src/config.py:72` — default 10 MB |
| 14 | `max_agents_per_bundle` en config | `Read` de `config.py` | ✅ | `src/config.py:69-70` — default 15 |
| 15 | `skill_catalog` tabla con schema correcto | `Read` de migración 026 | ✅ | `supabase/migrations/0026_bundle_system.sql:27-38` — `id UUID, org_id UUID, bundle_id UUID, name TEXT, code_source TEXT, metadata JSONB` |
| 16 | `UNIQUE(org_id, role)` en agent_catalog | `Read` de migración 004 | ✅ | `supabase/migrations/004_agent_catalog.sql:16` — garantiza no duplicados |
| 17 | `workflow_templates` tabla con flows | `Read` de migración 006 y 027 | ✅ | `supabase/migrations/006_workflow_templates.sql` + `0027_bundle_rpc.sql:6` — `flow_type`, `definition`, `status` |
| 18 | Tests bundle existentes | glob | ✅ | `tests/unit/test_bundle_manager.py`, `tests/unit/test_bundle_upsert.py`, `tests/integration/test_bundle_*.py`, `tests/test_bundle_rpc.py` |
| 19 | `fap export-agents` CLI existente | `Read` de `export.py` | ✅ | `src/cli/commands/export.py:14-84` — exporta agents DB → dir, usa `bundle_utils.py` |
| 20 | `fap package` CLI existente | `Read` de `package.py` | ✅ | `src/cli/commands/package.py:13-77` — empaqueta dir → ZIP |
| 21 | `get_tenant_client()` context manager | `Read` de `session.py` | ✅ | `src/db/session.py:214-231` — scoped a `org_id`, bypass RLS vía service_role |

### Discrepancias encontradas

| # | Discrepancia | Severidad | Resolución propuesta |
|---|-------------|-----------|---------------------|
| **D1** | Plan payload: `{agents: [{role, soul_json, allowed_tools, max_iter}]}` omite `model` e `is_active` del schema v2 real | Alta | Incluir `model` (opcional, extraído de `agent_catalog.soul_json.model`) y `is_active` (opcional). Schema v2 completo tiene 7 campos, no 4. |
| **D2** | Plan dice `skills?: [{name, code}]` (array de objetos) pero `BundleManager.create_bundle()` espera `skills: Dict[str, str]` (dict filename→code) | Media | Convertir en handler: `{s["name"] + ".py": s["code"] for s in skills}` si `name` no termina en `.py`. |
| **D3** | `agent_catalog.soul_json` puede contener el JSON completo del agente (cuando se importó vía bundle) O solo el `soul_json` anidado (cuando se creó manualmente vía dashboard en Paso 04 futuro). No hay marcador de origen. | Media | Extraer defensivamente: si `soul_json` tiene campo `"soul_json"` interno → es full JSON importado. Si no → es solo el nested soul. Reconstruir siempre desde columnas individuales para consistencia. |
| **D4** | Plan no menciona flows (`workflow_templates`) en el payload de export, pero `bundle-schema-v2.md` soporta `flows/` como opcional | Baja | Incluir `flows?: [...]` como campo opcional en el payload para permitir exportar workflows junto con agentes. Si no se envía, exportar solo agents + skills. |
| **D5** | Plan menciona validar `role`, `goal`, `backstory` en agentes. `soul_json` es JSONB → estos campos están DENTRO de `soul_json` (si es nested) o en `soul_json.soul_json` (si es full JSON). La validación debe ser condicional según el origen del agente. | Alta | Validar según D3: extraer `goal` y `backstory` del nested `soul_json` correcto. Si `goal` o `backstory` están ausentes → 422 con mensaje específico: `agent '{role}' missing '{field}'`. |
| **D6** | `BundleManager.create_bundle()` no valida que los agentes tengan `role`/`goal`/`backstory` — solo empaqueta lo que recibe | Media | Validación DEBE ocurrir en el handler del endpoint ANTES de llamar a `create_bundle()`. Separación de concerns correcta. |

**Total verificados:** 21 elementos (umbral ≥12 para 3-5 archivos afectados → cumple).  
**Total discrepancias:** 6 (≥1 exigido → cumple).

---

## 1. Análisis de Datos (ETAPA 1)

### Tablas involucradas

| Tabla | Uso | Columnas relevantes |
|-------|-----|-------------------|
| `agent_catalog` | Lectura — fuente de agentes a exportar | `role TEXT`, `soul_json JSONB`, `allowed_tools TEXT[]`, `max_iter INT`, `is_active BOOLEAN`, `created_at`, `updated_at` |
| `skill_catalog` | Lectura — fuente de skills a exportar (si se incluyen en payload) | `name TEXT`, `code_source TEXT` |
| `workflow_templates` | Lectura — fuente de flows a exportar (si se incluyen en payload) | `flow_type TEXT`, `name TEXT`, `definition JSONB`, `status TEXT` |

### Schema — sin cambios

Este paso es **solo lectura**. NO crea, modifica ni elimina tablas. No requiere migración.

### Integridad referencial

- `agent_catalog.org_id` → `organizations.id` (ON DELETE CASCADE) — consistente
- `skill_catalog.org_id` → `organizations.id` (ON DELETE CASCADE) — consistente
- `skill_catalog.bundle_id` → `bundle_imports.id` (ON DELETE SET NULL) — irrelevante para export

### RLS

- `agent_catalog` tiene RLS `tenant_isolation` vía `org_id::text = current_setting('app.org_id', TRUE)`
- El endpoint usa `get_tenant_client(org_id)` que llama `set_config('app.org_id', org_id)` → RLS aplica correctamente
- Solo se exportan agentes de la org autenticada

### Índices

- `idx_agent_catalog_org_role` (migración 004:26) — soporta búsqueda por org+role
- `idx_skill_catalog_org` (migración 026:38) — soporta búsqueda por org

### Tipos de datos

- `soul_json` es `JSONB` — la extracción de `goal`/`backstory` requiere acceso a claves anidadas. Sin schema rígido, defensivo.
- `allowed_tools` es `TEXT[]` — mapeo directo a `array[string]` en JSON
- `max_iter` es `INT` — rango 1-5 según bundle-schema-v2

---

## 2. Análisis de Código (ETAPA 2)

### Componentes nuevos

#### 2.1 Modelo Pydantic: `ExportBundleRequest`

```python
# src/api/routes/bundles.py (adición)
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class AgentExportItem(BaseModel):
    role: str = Field(..., min_length=1, max_length=100)
    soul_json: Dict[str, Any] = Field(...)
    allowed_tools: List[str] = Field(default_factory=list)
    max_iter: int = Field(default=5, ge=1, le=5)

class SkillExportItem(BaseModel):
    name: str
    code: str

class FlowExportItem(BaseModel):
    flow_type: str = Field(...)
    name: Optional[str] = None
    definition: Optional[Dict[str, Any]] = None
    code_source: Optional[str] = None
    is_python: bool = False

class ExportBundleRequest(BaseModel):
    agents: List[AgentExportItem] = Field(..., min_length=1, max_length=15)
    skills: Optional[List[SkillExportItem]] = None
    flows: Optional[List[FlowExportItem]] = None
    bundle_name: Optional[str] = Field(None, min_length=3, max_length=100)
    version: str = Field(default="1.0.0")

    @field_validator("agents")
    @classmethod
    def agents_must_have_soul(cls, v: List[AgentExportItem]) -> List[AgentExportItem]:
        for agent in v:
            soul = agent.soul_json
            if not soul.get("role"):
                raise ValueError(f"Agent '{agent.role}': soul_json.role required")
            if not soul.get("goal"):
                raise ValueError(f"Agent '{agent.role}': soul_json.goal required")
            if not soul.get("backstory"):
                raise ValueError(f"Agent '{agent.role}': soul_json.backstory required")
        return v
```

**Firma:** `ExportBundleRequest(agents: List[AgentExportItem], skills?: List[SkillExportItem], flows?: List[FlowExportItem], bundle_name?: str, version: str = "1.0.0")`  
**Patrón de referencia:** `src/services/bundle_schemas.py::BundleRPCPayload` — Pydantic v2 con `Field()` y `field_validator`

#### 2.2 Handler: `POST /api/bundles/export`

**Firma:** `async def export_bundle(payload: ExportBundleRequest, org_id: str = Depends(require_org_id)) -> StreamingResponse`

**Patrón de referencia:** `src/api/routes/bundles.py::import_bundle()` (línea 53) — mismo archivo, mismo router, usa `require_org_id`, manejo de excepciones con `HTTPException`

#### 2.3 `BundleManager.create_bundle()` — REUTILIZADO (no modificar)

**Firma existente:** `def create_bundle(self, manifest: BundleManifest, agents: List[Dict], flows: List[Dict], skills: Dict[str, str]) -> bytes`  
**Ubicación:** `src/services/bundle_manager.py:197`  
**Patrón de referencia:** Es el patrón en sí. El endpoint llamará a este método.

### Reutilización vs código nuevo

| Componente | Nuevo/Existente | Archivo |
|-----------|----------------|---------|
| `ExportBundleRequest` + submodelos | **Nuevo** | `src/api/routes/bundles.py` |
| Handler `export_bundle()` | **Nuevo** | `src/api/routes/bundles.py` |
| `BundleManager.create_bundle()` | **Existente** | `src/services/bundle_manager.py:197` — sin cambios |
| `BundleManifest` | **Existente** | `src/services/bundle_schemas.py:22` — sin cambios |
| `BundleInfo` | **Existente** | `src/services/bundle_schemas.py:13` — sin cambios |
| `calculate_sha256()` | **Existente** | `src/services/integrity.py:15` — sin cambios |
| `get_tenant_client()` | **Existente** | `src/db/session.py:214` — sin cambios |

### Calidad

- **Cohesión alta:** todo el código nuevo va en `bundles.py` (mismo archivo que import/validate/history) — dominio coherente
- **Acoplamiento bajo:** el handler solo depende de modelos Pydantic + `BundleManager.create_bundle()` + `StreamingResponse` (FastAPI core)
- **Complejidad ciclomática baja:** el handler tiene un flujo lineal: validar → construir manifest → crear ZIP → devolver StreamingResponse

### Imports exactos necesarios

```python
# Adiciones en src/api/routes/bundles.py
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

# Estos ya existen en el archivo:
# from fastapi import APIRouter, Depends, HTTPException, status
# from src.api.middleware import require_org_id
```

---

## 3. Análisis de Backend (ETAPA 3)

### Endpoint

| Elemento | Valor |
|----------|-------|
| **Ruta** | `POST /api/bundles/export` |
| **Método HTTP** | POST |
| **Auth** | `require_org_id` → header `X-Org-ID` requerido |
| **Content-Type request** | `application/json` |
| **Content-Type response** | `application/zip` |
| **Status success** | 200 |
| **Status validation error** | 422 (Unprocessable Entity) — Pydantic validation |
| **Status server error** | 500 |

### Request

```json
{
  "agents": [
    {
      "role": "recepcionista",
      "soul_json": {
        "role": "Recepcionista de Hotel",
        "goal": "Atender al usuario y proveer información del hotel.",
        "backstory": "Sos un recepcionista profesional con atención personalizada."
      },
      "allowed_tools": ["mcp:filesystem:read_file"],
      "max_iter": 3
    }
  ],
  "skills": [
    {
      "name": "excel_reader.py",
      "code": "from crewai_tools import BaseTool\n..."
    }
  ],
  "flows": [
    {
      "flow_type": "reserva",
      "name": "Reserva Workflow",
      "definition": {"steps": [...]},
      "code_source": null,
      "is_python": false
    }
  ],
  "bundle_name": "my-agents",
  "version": "1.0.0"
}
```

### Response (happy path)

```
HTTP 200 OK
Content-Type: application/zip
Content-Disposition: attachment; filename="my-agents.zip"
Content-Length: <bytes>

<binary ZIP stream>
```

### Response (validation error)

```json
HTTP 422 Unprocessable Entity
{
  "detail": "Agent 'recepcionista': soul_json.goal required"
}
```

### Flujo de datos

```
[Builder UI / Cliente]
       │
       ▼ POST /api/bundles/export
       │  Payload: { agents: [...], skills?: [...], flows?: [...], ... }
       ▼
[Handler: export_bundle()]
       │
       ├─ 1. Validar Pydantic (ExportBundleRequest) → 422 si falla
       ├─ 2. Validar que cada agent.soul_json tenga role, goal, backstory → 422 si falla
       ├─ 3. Si skills[] → convertir a Dict[str, str] (name → code_source)
       ├─ 4. Construir BundleInfo + BundleManifest
       ├─ 5. Llamar BundleManager.create_bundle(manifest, agents, flows, skills)
       │      └─ Genera ZIP in-memory con hashes SHA256 auto-calculados
       ├─ 6. Envolver bytes en BytesIO
       └─ 7. Retornar StreamingResponse con media_type="application/zip"
```

### Cuellos de botella

- `BundleManager.create_bundle()` procesa todo en memoria → OK para bundles ≤10 MB (límite config)
- Si se exportan muchos agentes con skills grandes, memoria puede crecer. Límite de 15 agents + 30 skills mitiga esto.

### Manejo de errores

| Error | Código | Mensaje |
|-------|--------|---------|
| `agents` vacío | 422 | Pydantic: `min_length=1` |
| `agents` > 15 | 422 | Pydantic: `max_length=15` |
| `soul_json.goal` ausente | 422 | `field_validator` |
| `soul_json.backstory` ausente | 422 | `field_validator` |
| `max_iter` fuera de rango | 422 | Pydantic: `ge=1, le=5` |
| Error interno ZIP | 500 | `"Internal server error during export: {str(e)}"` |

---

## 4. Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo

```
DB (agent_catalog) → Endpoint POST /api/bundles/export → ZIP descargable
                                                              │
                                                              ▼
                                         Builder UI (Paso 08: ExportDialog)
                                                              │
                                                              ▼
                                         POST /api/bundles/import (ya existe)
                                                              │
                                                              ▼
                                         DB (agent_catalog) — re-import exitoso
```

### Coherencia

- **Data ↔ Backend:** Tablas `agent_catalog` + `skill_catalog` + `workflow_templates` ya tienen estructura compatible con bundle-schema-v2
- **Backend ↔ Frontend:** El endpoint devuelve ZIP que se puede descargar directamente desde el navegador. `ExportDialog` en Paso 08 consumirá este endpoint.
- **MVP completo:** Un usuario puede: crear agentes en builder → exportarlos como ZIP → importarlos en otra org → ciclo cerrado

### Alineación con arquitectura

- Endpoint sigue el mismo patrón que `import_bundle()`, `validate_bundle()`, `list_history()` — consistente
- Usa el mismo router, mismo auth middleware, mismo `BundleManager`
- `StreamingResponse` es el mecanismo estándar de FastAPI para descargas binarias

### Gaps y fricciones

1. **soul_json ambiguity (D3):** Si un agente fue creado por el builder (Paso 04, aún no implementado), su `soul_json` puede no coincidir con el formato de import. El endpoint debe ser robusto ante ambos formatos.
2. **Sin callback de progreso:** La generación del ZIP es síncrona. Para bundles muy grandes (>8 MB) podría exceder timeouts HTTP. Mitigación: límite de 10 MB en config.
3. **No hay endpoint GET para listar agentes exportables:** El builder necesitará consultar `GET /agents/by-role/{role}` o un nuevo endpoint para obtener la lista de agentes de la org antes de exportar. Esto es parte del Paso 04, no del 02.

### DX & Tooling (OBLIGATORIO)

#### Herramienta Propuesta: `fap bundle export`

- **Qué automatiza:** Reemplaza el flujo manual de 3 pasos (consultar DB → construir JSON → llamar API) con un solo comando CLI que exporta agentes de una organización a ZIP descargable. Útil para backups, migraciones entre entornos, y debugging sin dashboard.
- **Tipo:** CLI (Typer command)
- **Cómo se usa:**
  ```bash
  # Exportar todos los agentes activos de una org
  fap bundle export --org-id <UUID> --output my-agents.zip

  # Exportar con skills incluidos
  fap bundle export --org-id <UUID> --include-skills --output full-backup.zip

  # Exportar agentes específicos por role
  fap bundle export --org-id <UUID> --roles recepcionista,analyst --output partial.zip
  ```
- **Impacto para el usuario final:** Elimina la necesidad de abrir el dashboard, copiar payloads manualmente, y usar curl/Postman para exportar. Un solo comando → ZIP listo para compartir o importar.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso. El CLI comparte la lógica de `BundleManager.create_bundle()` con el endpoint, validando que ambos funcionen.

#### Herramienta Existente Reutilizable

- `fap export-agents` (ya existe en `src/cli/commands/export.py`) — exporta agentes a directorio, no ZIP
- `fap package` (ya existe en `src/cli/commands/package.py`) — empaqueta directorio → ZIP

**`fap bundle export` unifica ambos en un solo paso:** Lee de DB → genera ZIP directamente (sin directorio intermedio).

---

## 5. Criterios de Aceptación

```
✅ [DATA]    Tabla agent_catalog se consulta con RLS tenant_isolation activo
✅ [CODE]    Modelo ExportBundleRequest valida: role, soul_json.role, soul_json.goal, soul_json.backstory requeridos
✅ [CODE]    Modelo ExportBundleRequest valida: max_iter entre 1-5, agents entre 1-15
✅ [CODE]    Función export_bundle() tiene firma correcta: async def export_bundle(payload: ExportBundleRequest, org_id: str = Depends(require_org_id)) -> StreamingResponse
✅ [BACKEND] POST /api/bundles/export con payload válido → 200 + ZIP descargable con Content-Type: application/zip
✅ [BACKEND] ZIP contiene manifest.json válido según bundle-schema-v2 con bundle_info + hashes
✅ [BACKEND] POST con datos inválidos (sin goal) → 422 con mensaje específico: "Agent 'X': soul_json.goal required"
✅ [BACKEND] POST con agents vacío → 422 (Pydantic min_length=1)
✅ [FULLSTACK] ZIP exportado se puede re-importar con POST /api/bundles/import sin errores (round-trip)
✅ [FULLSTACK] Content-Disposition header incluye filename correcto
✅ [FULLSTACK] Skills incluidos en el ZIP aparecen en skills/ dentro del bundle
✅ [DX]       Comando fap bundle export --org-id <UUID> genera ZIP válido sin errores
✅ [DX]       Comando fap bundle export --help muestra ayuda completa
```

---

## 6. Riesgos

| # | Riesgo | Severidad | Causa | Mitigación |
|---|--------|-----------|-------|------------|
| R1 | **soul_json ambiguo** — formato inconsistente entre agentes importados y agentes creados manualmente | Alta | `soul_json` puede ser el JSON completo del agente (import) o solo el nested soul (creación manual en Paso 04). No hay flag de origen. | Detección defensiva: si `soul_json` contiene clave `"soul_json"` → es full JSON, extraer nested. Si no → es el nested soul directamente. Documentar en §1. |
| R2 | **Timeout HTTP en bundles grandes** | Media | `create_bundle()` es síncrono. Con 15 agents + 30 skills, el ZIP puede tardar >30s en generarse. | Límite de 10 MB en config. Si se observan timeouts en producción, considerar `BackgroundTasks` + polling (fuera de alcance MVP). |
| R3 | **Falta de endpoint GET para listar agentes de la org** | Media | El builder necesitará listar agentes antes de exportar. Paso 04 debe crear `GET /agents` o reutilizar `GET /agents/by-role/{role}`. | Dependencia documentada: Paso 04 DEBE incluir endpoint de listado de agentes. |
| R4 | **Hash mismatch en round-trip** | Baja | Si el agente se modificó después de importar (vía dashboard), los hashes no coincidirán con el ZIP original. Pero en export, los hashes se recalculan. | `create_bundle()` recalcula hashes automáticamente → no hay mismatch. El riesgo es nulo. |
| R5 | **Inyección vía skill code** | Baja | Si el payload incluye `skills[].code` con código malicioso, el endpoint lo empaqueta sin validar. | La validación de seguridad ocurre en IMPORT (SecurityGuard + RestrictedPython). En export, el código ya existe en `skill_catalog` (previamente validado). Si se pasa código nuevo vía payload, NO se persiste — solo se empaqueta. Riesgo aceptable para MVP. |
| R6 | **Inconsistencia entre CLI y endpoint** | Baja | `fap bundle export` y `POST /api/bundles/export` podrían divergir en lógica de reconstrucción de agentes. | Ambos deben usar el mismo helper `_reconstruct_agent_json()` extraído a `src/services/bundle_manager.py` o `src/utils/bundle_utils.py`. |

---

## 7. Plan de Implementación

> **Reglas de segmentación atómica aplicadas:** 1 tarea = 1 artefacto, interfaz completa, patrón explícito, verificación inline.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|----------------|----------------|-------|-------------|-------------|-------------|-------------|
| 0 | **DX & Tooling**: `fap bundle export` CLI | `src/cli/commands/bundle_export.py` | `def bundle_export(org_id: str, output: Path, include_skills: bool, roles: Optional[List[str]], version: str = "1.0.0") -> Path` (retorna path del ZIP generado) | `src/cli/commands/export.py :: export_agents()` | DX | Media | 1.5h | Ninguna | → verificar: `uv run python -m src.cli.main bundle export --help` ejecuta sin errores |
| 1 | Modelo Pydantic `ExportBundleRequest` + submodelos | `src/api/routes/bundles.py` (adición ~60 líneas) | `class ExportBundleRequest(BaseModel): agents: List[AgentExportItem]; skills: Optional[List[SkillExportItem]]; flows: Optional[List[FlowExportItem]]; bundle_name: Optional[str]; version: str = "1.0.0"` con `@field_validator("agents")` | `src/services/bundle_schemas.py :: BundleRPCPayload` | CODE | Baja | 0.5h | Tarea 0 | → verificar: `from src.api.routes.bundles import ExportBundleRequest` sin error + `ExportBundleRequest.model_json_schema()` retorna schema válido |
| 2 | Handler `export_bundle()` + registro en router | `src/api/routes/bundles.py` (adición ~80 líneas) | `@router.post("/export", status_code=200) async def export_bundle(payload: ExportBundleRequest, org_id: str = Depends(require_org_id)) -> StreamingResponse` | `src/api/routes/bundles.py :: import_bundle()` (línea 53) | BACKEND | Media | 1.5h | Tarea 1 | → verificar: `uv run pytest tests/ -k test_export` pasa (test a crear en Tarea 3) |
| 3 | Tests unitarios del endpoint (3 tests mínimos) | `tests/unit/test_bundle_export.py` | `def test_export_valid_bundle(): ...` `def test_export_missing_goal_422(): ...` `def test_export_empty_agents_422(): ...` | `tests/unit/test_bundle_manager.py :: create_test_zip()` | TEST | Media | 1h | Tarea 2 | → verificar: `uv run pytest tests/unit/test_bundle_export.py -v` — 3 tests pasan |
| 4 | Test de integración round-trip (export → import) | `tests/integration/test_bundle_export_roundtrip.py` | `async def test_export_import_roundtrip(): ...` | `tests/integration/test_bundle_upsert.py` | FULLSTACK | Media | 1h | Tarea 3 | → verificar: `uv run pytest tests/integration/test_bundle_export_roundtrip.py -v` — pasa con Supabase real |
| 5 | Validar flujo end-to-end completo | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-4 | → verificar: criterios §5 [FULLSTACK] y [DX] pasan todos |

**Tiempo total estimado:** 6 horas

---

## 8. Roadmap (NO implementar ahora)

- **Post-MVP:** Agregar `GET /api/bundles/export/preview` — endpoint que devuelve el contenido del ZIP como JSON sin generar el binario (útil para previsualizar en `ExportDialog` antes de descargar)
- **Post-MVP:** Export streaming — generar ZIP en chunks para bundles muy grandes (>50 MB) sin bloquear el event loop
- **Post-MVP:** `fap bundle export` con `--include-flows` — extender el CLI para incluir workflows en el ZIP exportado
- **Post-MVP:** Agregar `content-disposition` con timestamp en filename: `export_2026-05-13T120000Z.zip`
- **Pre-requisito para Paso 08:** El `ExportDialog` del frontend usará este endpoint. Asegurar que `Content-Disposition: attachment` funciona con `fetch()` + `Blob` en navegador.
- **Decisión de diseño:** No se modifica `BundleManager.create_bundle()` para este paso. Si en el futuro se necesita validación adicional de agentes en `create_bundle()`, agregarla allí y eliminar validación duplicada del handler.
