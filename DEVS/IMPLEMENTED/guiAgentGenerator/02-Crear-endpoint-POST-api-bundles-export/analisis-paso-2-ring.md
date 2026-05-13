# 🧠 ANÁLISIS TÉCNICO — Paso 02: `POST /api/bundles/export` (ring)

> **Proyecto:** FluxAgentPro-v2  
> **Fase:** `guiAgentGenerator`  
> **Paso:** 02 — Crear endpoint `POST /api/bundles/export`  
> **Agente Analista:** ring  
> **Fecha:** 2026-05-13  

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Archivo `src/api/routes/bundles.py` existe | `ls src/api/routes/bundles.py` | ✅ | Archivo de 190 líneas con rutas CRUD de bundles: import, validate, history, details, delete |
| 2 | `BundleManager.create_bundle()` existe | `grep -n "def create_bundle" src/services/bundle_manager.py` | ✅ | Línea 197: método que genera ZIP en memoria a partir de `BundleManifest + agents + flows + skills` |
| 3 | Schema `BundleManifest` existe | `grep -n "class BundleManifest" src/services/bundle_schemas.py` | ✅ | Línea 22: `version`, `bundle_info`, `hashes` con validador de SHA256 |
| 4 | Schema `ExportRequest` NO existe | `grep -r "ExportRequest" src/` | ❌ | No existe ningún modelo Pydantic para el payload de exportación — debe crearse |
| 5 | Endpoint `POST /api/bundles/export` NO existe | `grep "export" src/api/routes/bundles.py` | ❌ | Solo existen `/import`, `/validate`, `/history`, `/{bundle_id}/details`, `/{bundle_id}` (DELETE) |
| 6 | `require_org_id` middleware disponible | `grep -n "require_org_id" src/api/middleware.py` | ✅ | Línea 66: FastAPI `Depends` que extrae header `X-Org-ID` |
| 7 | Tabla `agent_catalog` verificada | `cat supabase/migrations/004_agent_catalog.sql` | ✅ | Columnas: `id UUID`, `org_id UUID`, `role TEXT`, `soul_json JSONB`, `allowed_tools TEXT[]`, `max_iter INTEGER`, `is_active BOOLEAN` |
| 8 | Tabla `skill_catalog` verificada | `grep -n "skill_catalog" src/services/import_service.py` | ✅ | Referenciada en `get_details()` (línea 234), columnas: `id`, `org_id`, `name`, `code_source`, `bundle_id` |
| 9 | `StreamingResponse` disponible en FastAPI | `grep -r "StreamingResponse" src/api/routes/` | ⚠️ | No se usa actualmente en ninguna ruta — hay que importarlo desde `fastapi.responses` |
| 10 | `create_base_manifest()` en utils | `grep -n "def create_base_manifest" src/utils/bundle_utils.py` | ✅ | Línea 75: crea manifest v2.0 con `bundle_info` + `hashes` vacíos |
| 11 | `calculate_bundle_hashes()` en utils | `grep -n "def calculate_bundle_hashes" src/utils/bundle_utils.py` | ✅ | Línea 23: calcula SHA256 de todos los archivos en el bundle path |
| 12 | Ruta registrada en `main.py` | `grep "bundles" src/api/main.py` | ✅ | Línea 110: `app.include_router(bundles_router)` |

**Discrepancias encontradas:**

1. **`ExportRequest` schema no existe** → Debe crearse como modelo Pydantic en `bundle_schemas.py` antes del endpoint.
2. **Endpoint `POST /api/bundles/export` no existe** → Debe añadirse a `src/api/routes/bundles.py`.
3. **`StreamingResponse` no importado** → Falta import en `bundles.py`. El export endpoint lo necesita.
4. **No hay servicio de exportación dedicado** → `ImportService` existe pero no `ExportService`. Opción: crear `ExportService` o añadir lógica inline en el endpoint reutilizando `BundleManager.create_bundle()`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas involucradas

| Tabla | Migración | Columnas relevantes | Rol en el paso |
|---|---|---|---|
| `agent_catalog` | `004_agent_catalog.sql` | `id`, `org_id`, `role`, `soul_json`, `allowed_tools`, `max_iter`, `is_active` | Fuente de datos de agentes para exportar |
| `skill_catalog` | `0026_bundle_system.sql` | `id`, `org_id`, `name`, `code_source`, `bundle_id`, `is_active` | Fuente de datos de skills para exportar |
| `bundle_imports` | `0026_bundle_system.sql` | `id`, `org_id`, `bundle_name`, `version`, `imported_at` | Historial de imports (referencia para versionado) |

### Integridad referencial

- `agent_catalog.org_id` → `organizations.id` (FK)
- `skill_catalog.org_id` → `organizations.id` (FK)
- `agent_catalog` tiene RLS `tenant_isolation` (mig 004 + mig 025): `auth.role() = 'service_role' OR org_id::text = current_org_id()`
- `skill_catalog` tiene RLS similar — lectura pública dentro del tenant

### Schema de datos de exportación (a construir)

El payload de entrada del endpoint debe aceptar:
```
{
  agents: [{ role: str, soul_json: {...}, allowed_tools: [...], max_iter: int }],
  skills: [{ name: str, code: str }]  // opcional
}
```

La respuesta es un `StreamingResponse` con ZIP binario.

### Cambios de schema necesarios

**Ninguno.** No se modifica la DB — la exportación lee datos existentes y construye un ZIP en memoria. Sin migración requerida.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes nuevos a crear

#### 2.1 `ExportAgentRequest` — Schema Pydantic (nuevo)

**Archivo:** `src/services/bundle_schemas.py` (añadir al final)
**Qué:** Modelo Pydantic para validar cada agente en el payload de exportación.

```python
class ExportAgentRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=100)
    soul_json: dict = Field(default_factory=dict)
    allowed_tools: list[str] = Field(default_factory=list)
    max_iter: int = Field(default=5, ge=1, le=50)

    @field_validator("soul_json")
    @classmethod
    def validate_soul_json(cls, v: dict) -> dict:
        required_keys = {"role", "goal", "backstory"}
        missing = required_keys - v.keys()
        if missing:
            raise ValueError(f"soul_json missing required keys: {missing}")
        return v
```

**Patrón a seguir:** Identico a `BundleRPCPayload` y `BundleInfo` en el mismo archivo — Pydantic `BaseModel` con `Field` + `field_validator`.

#### 2.2 `ExportRequest` — Schema Pydantic (nuevo)

**Archivo:** `src/services/bundle_schemas.py`
**Qué:** Modelo Pydantic para el payload completo del endpoint.

```python
class ExportRequest(BaseModel):
    agents: list[ExportAgentRequest] = Field(..., min_length=1, max_length=15)
    skills: list[dict] | None = Field(default=None)
```

**Patrón a seguir:** `BundleContent` — contenedor con listas de agentes y skills.

#### 2.3 `ExportService` — Lógica de exportación (nuevo servicio)

**Archivo:** `src/services/export_service.py`
**Qué:** Servicio que orquesta la exportación: consulta DB, construye manifiesto, genera ZIP.

```python
class ExportService:
    def __init__(self, org_id: str):
        self.org_id = org_id
    
    def export(self, payload: ExportRequest) -> tuple[bytes, str]:
        # 1. Build manifest
        # 2. Prepare agents list from payload
        # 3. Prepare skills dict from payload
        # 4. Use BundleManager.create_bundle() to generate ZIP bytes
        # 5. Return (zip_bytes, filename)
```

**Patrón a seguir:** `ImportService` en `src/services/import_service.py` — inyecta `BundleManager`, delega la creación de ZIP.

**Firma exacta del método principal:**
```python
def export(self, payload: ExportRequest) -> tuple[bytes, str]
```
Retorna `(zip_bytes, filename)` donde `filename` = `f"{bundle_name}.zip"`.

#### 2.4 Endpoint `POST /api/bundles/export`

**Archivo:** `src/api/routes/bundles.py` (añadir nueva función)
**Qué:** Endpoint FastAPI que acepta `ExportRequest`, llama a `ExportService`, retorna `StreamingResponse`.

```python
@router.post(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export agents as ZIP bundle (FAP-Bundle v2)",
)
async def export_bundle(
    payload: ExportRequest,
    org_id: str = Depends(require_org_id),
) -> StreamingResponse:
```

**Patrón a seguir:** `import_bundle` en el mismo archivo — usa `Depends(require_org_id)`, delega a servicio, retorna respuesta HTTP.

**Imports adicionales necesarios:**
```python
from fastapi.responses import StreamingResponse
from src.services.export_service import ExportService
from src.services.bundle_schemas import ExportRequest
```

### Componentes reutilizables existentes

| Componente | Ubicación | Estado |
|---|---|---|
| `BundleManager.create_bundle()` | `src/services/bundle_manager.py:197` | ✅ Funcional — acepta `BundleManifest + agents + flows + skills` y retorna `bytes` |
| `BundleManifest` | `src/services/bundle_schemas.py:22` | ✅ Reutilizable — versión, bundle_info, hashes |
| `create_base_manifest()` | `src/utils/bundle_utils.py:75` | ✅ Utilidad para crear manifest base v2.0 |
| `calculate_bundle_hashes()` | `src/utils/bundle_utils.py:23` | ✅ Calcula hashes SHA256 de archivos en disco (no aplica aquí — el ZIP se genera en memoria) |
| `require_org_id` | `src/api/middleware.py:66` | ✅ Middleware de auth |
| `ImportService` | `src/services/import_service.py` | Patrón de servicio a seguir |

### Patrón de diseño para el endpoint

Siguiendo el patrón de `import_bundle` en `bundles.py`:
1. Validación de input vía Pydantic (el `ExportRequest` se valida automáticamente con FastAPI)
2. Delegación a servicio (`ExportService`)
3. Manejo de errores con `HTTPException`
4. Logging con `logger = logging.getLogger(__name__)`

### Decisión de diseño: Export vs DB Lookup

El plan indica que el payload contiene `agents: [{role, soul_json, ...}]`. Esto significa que los datos de los agentes vienen **del cuerpo de la request** (el formulario del builder los envía), no de una consulta a `agent_catalog`. Esto es consistente con:
- El formulario `AgentForm` (Paso 04) que aún no guarda en `agent_catalog` (solo lo hará al presionar "Save Agent")
- El canvas (Paso 07) que serializa el grafo en memoria antes de exportar
- El `ExportDialog` (Paso 08) que puede exportar sin haber guardado

**Consecuencia:** No se necesita query a `agent_catalog` ni `skill_catalog` en el endpoint. Los datos vienen completos en el request body.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoint a crear

| Método | Ruta | Input | Output | Auth |
|---|---|---|---|---|
| POST | `/api/bundles/export` | `ExportRequest` (JSON body) | `StreamingResponse` (application/zip) | `require_org_id` |

### Contrato del endpoint

**Request:**
```json
{
  "agents": [
    {
      "role": "string (1-100 chars)",
      "soul_json": {
        "role": "string",
        "goal": "string (REQUIRED)",
        "backstory": "string (REQUIRED)"
      },
      "allowed_tools": ["string[]"],
      "max_iter": "integer (1-50, default 5)"
    }
  ],
  "skills": [
    {
      "name": "string",
      "code": "string"
    }
  ]
}
```

**Response (éxito):**
- Status: `200 OK`
- Headers: `Content-Disposition: attachment; filename="bundle-name.zip"`
- Body: ZIP binario con estructura FAP-Bundle v2
- Content-Type: `application/zip`

**Response (error):**
- `422 Unprocessable Entity`: Payload inválido (validación Pydantic automática)
- `400 Bad Request`: Agentes sin role/goal/backstory (validación custom)

### Flujo de datos

```
Cliente (Dashboard)
  │
  ├─ POST /api/bundles/export
  │   ├─ FastAPI valida ExportRequest (Pydantic)
  │   ├─ require_org_id extrae X-Org-ID
  │   ├─ ExportService.export(payload)
  │   │   ├─ Construye BundleManifest con bundle_info + hashes placeholder
  │   │   ├─ Prepara agents list (serializa soul_json + metadata)
  │   │   ├─ Prepara skills dict
  │   │   ├─ BundleManager.create_bundle(manifest, agents, flows, skills)
  │   │   │   ├─ Genera ZIP en memoria (BytesIO)
  │   │   │   ├─ Añade agents/*.json
  │   │   │   ├─ Añade skills/*.py
  │   │   │   ├─ Calcula hashes SHA256
  │   │   │   └─ Añade manifest.json con hashes
  │   │   └─ Retorna (zip_bytes, filename)
  │   └─ StreamingResponse(zip_bytes, media_type="application/zip")
  │
  └─ El navegador descarga el ZIP automáticamente
```

### Manejo de errores

| Escenario | HTTP Status | Detalle |
|---|---|---|
| Payload malformado | 422 | FastAPI devuelve errores de validación Pydantic automáticamente |
| `soul_json` sin `goal` o `backstory` | 422 | Validador custom `ExportAgentRequest.validate_soul_json` |
| Lista de agents vacía | 422 | `Field(min_length=1)` |
| Error interno en generación ZIP | 500 | Logger.error + HTTPException |

### Integración con endpoints existentes

- **`POST /api/bundles/import`**: El ZIP generado por export debe ser re-importable por este endpoint sin modificaciones. El formato bundle-schema-v2 es el mismo.
- **`POST /api/bundles/validate`**: Se puede usar para pre-validar un bundle antes de exportar (opcional, no requerido en este paso).

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end completo

```
┌─────────────────────────────────────────────────────────────┐
│  Dashboard (Next.js)                                        │
│                                                             │
│  AgentForm.tsx  ──→  POST /api/bundles/export               │
│    (role, goal, backstory,                                  │
│     tools, max_iter, toggles)                               │
│                                                             │
│  CrewCanvas.tsx ──→  Serializa grafo → POST /api/bundles/export │
│    (agent nodes + task nodes + edges)                       │
│                                                             │
│  ExportDialog.tsx ←── StreamingResponse (ZIP) ←─────────────┘
│    (descarga automática + "Copy as JSON")
│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                          │
│                                                             │
│  bundles.py:export_bundle()                                 │
│    ├─ Validar ExportRequest (Pydantic)                      │
│    ├─ ExportService.export()                                │
│    │   ├─ Construir BundleManifest                          │
│    │   ├─ BundleManager.create_bundle() → ZIP bytes         │
│    │   └─ Retornar (bytes, filename)                        │
│    └─ StreamingResponse                                     │
│                                                             │
│  bundle_manager.py:create_bundle()                          │
│    ├─ Iterar agents → agents/{role}.json                    │
│    ├─ Iterar skills → skills/{name}.py                      │
│    ├─ Calcular SHA256 por archivo                           │
│    ├─ Generar manifest.json con hashes                      │
│    └─ Retornar ZIP como bytes                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Re-importación                                             │
│                                                             │
│  POST /api/bundles/import ←── ZIP generado por export       │
│    ├─ ImportService.process_bundle()                        │
│    │   ├─ BundleManager.process_zip()                       │
│    │   │   ├─ Verificar manifest.json                       │
│    │   │   ├─ Verificar hashes SHA256                       │
│    │   │   ├─ Parsear agents/*.json                         │
│    │   │   ├─ Parsear skills/*.py                           │
│    │   │   └─ Validar límites                               │
│    │   └─ import_bundle_atomic (RPC)                        │
│    └─ BundleRPCResult                                       │
└─────────────────────────────────────────────────────────────┘
```

### Consistencia y gaps

| Aspecto | Estado | Detalle |
|---|---|---|
| Formato bundle compatible con import | ✅ Coherente | Se reusa `BundleManager.create_bundle()` y `BundleManifest`, mismo formato que el import |
| Validaciones de agentes | ✅ Correcto | `role`, `goal`, `backstory` requeridos vía validador Pydantic |
| Límite de agents | ✅ Cubierto | `ExportRequest.agents` tiene `max_length=15` (coincide con `config.max_agents_per_bundle`) |
| Hashes en manifest | ⚠️ Gap menor | `create_bundle()` calcula hashes automáticamente — verificar que el hash se calcula sobre el contenido correcto de cada archivo |
| Nombre del bundle | ⚠️ Definir | El plan no especifica de dónde sale el `bundle_name` para el filename. Propuesta: aceptar campo opcional `name` en `ExportRequest`, default `"export_{timestamp}"` |

### Herramienta DX propuesta

```
### Herramienta Propuesta: `fap export-bundle`
- **Qué automatiza:** Genera un bundle ZIP desde la CLI exportando
  agentes de la base de datos, eliminando la necesidad de usar el
  dashboard para exportaciones manuales.
- **Tipo:** CLI command (Typer)
- **Cómo se usa:**
    fap export-bagents --org-id <org_uuid> [--roles role1,role2] [--output ./bundle.zip]
- **Impacto para el usuario final:** 
    El usuario puede exportar agentes desde CI/CD o scripts, sin
    depender de la UI. Útil para automatización de despliegues y
    migración entre instancias.
- **Prioridad:** Media (Puede implementarse después del endpoint,
  como Tarea 0 del siguiente paso)
```

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Verificación |
|---|---|---|
| ✅ [DATA] | Schema `ExportRequest` con `agents` (min 1, max 15) y `skills` (opcional) definido en `bundle_schemas.py` |
| ✅ [DATA] | Validador custom en `ExportAgentRequest` rechaza payload sin `role`, `goal`, o `backstory` |
| ✅ [CODE] | `ExportService.export(payload: ExportRequest) -> tuple[bytes, str]` implementado en `src/services/export_service.py` |
| ✅ [CODE] | Endpoint `POST /api/bundles/export` implementado en `src/api/routes/bundles.py` con `Depends(require_org_id)` |
| ✅ [BACKEND] | Endpoint retorna `StreamingResponse` con ZIP descargable (status 200, Content-Type application/zip) |
| ✅ [BACKEND] | Endpoint retorna 422 para payload inválido (validación Pydantic automática) |
| ✅ [BACKEND] | ZIP generado contiene `manifest.json` válido (bundle-schema-v2) + `agents/*.json` + `skills/*.py` |
| ✅ [BACKEND] | ZIP generado se puede re-importar con `POST /api/bundles/import` sin errores |
| ✅ [FULLSTACK] | El bundle exportado sigue el formato `bundle-schema-v2.md` exactamente |
| ✅ [DX] | `ExportService` reutiliza `BundleManager.create_bundle()` — sin duplicación de lógica ZIP |
| ✅ [DX] | CLI `fap export-bundle` propuesto como Tarea 0 del siguiente paso |

---

## 6️⃣ Riesgos

| # | Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|---|
| R1 | **Inconsistencia de formato** — El ZIP exportado no sea re-importable | Alta | Si el mapeo de datos entre `ExportRequest` y el formato esperado por `create_bundle()` tiene discrepancias | Escribir test E2E que exporte e importe el mismo ZIP en la misma ejecución de tests (criterio de aceptación en 5) |
| R2 | **Tamaño de ZIP sin límite** — Un request con 15 agents + skills grandes puede generar un ZIP > 50MB | Media | No hay validación de tamaño en el endpoint de export | Añadir validación de tamaño máximo del ZIP antes de retornar, consistente con `max_bundle_size_mb` de config |
| R3 | **Exposición de datos sensibles** — Exportar datos de otros tenants si la RLS falla | Alta | Si `require_org_id` no filtra correctamente o el servicio accede a datos sin tenant scope | Usar `get_tenant_client()` (no `get_service_client()`) dentro de `ExportService` para asegurar RLS |
| R4 | **Inyección en soul_json** — Contenido malicioso en `soul_json` que se almacene sin sanitizar | Media | Los datos vienen del frontend y se serializan directamente en JSON | Validar que `soul_json` no contenga claves peligrosas (`__import__`, `eval`, etc.) o limitar a un schema estricto |
| R5 | **Ruptura de contrato con import** — Cambios futuros en `bundle-schema-v2` rompan la compatibilidad | Baja | Sin test de ida y vuelta (export → import) | Mantener el test E2E de round-trip como test de regresión permanente |

---

## 7️⃣ Plan de Implementación

> **Reglas de segmentación atómica — OBLIGATORIAS:**
> 1. Una tarea = un artefacto
> 2. Interfaz completa en cada tarea
> 3. Patrón de referencia explícito
> 4. Verificación inline
> 5. Test de atomicidad

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap export-bundle` CLI | `src/cli/commands/export_bundle.py` | `def export_bundle(org_id: str, roles: Optional[list[str]], output: Path) -> None` | `src/cli/commands/export.py` — `export_agents()` | DX | Media | 1.5h | Ninguna | → verificar: `fap export-bundle --help` ejecuta sin errores |
| 1 | Crear schemas `ExportAgentRequest` y `ExportRequest` | `src/services/bundle_schemas.py` (añadir) | `class ExportAgentRequest(BaseModel): role, soul_json, allowed_tools, max_iter` + `class ExportRequest(BaseModel): agents, skills` | `BundleRPCPayload` en el mismo archivo | DATA | Baja | 0.5h | Ninguna | → verificar: `from src.services.bundle_schemas import ExportRequest` sin error |
| 2 | Crear `ExportService` | `src/services/export_service.py` (nuevo) | `def __init__(self, org_id: str)` + `def export(self, payload: ExportRequest) -> tuple[bytes, str]` | `ImportService` en `src/services/import_service.py` | CODE | Media | 1h | Tarea 1 | → verificar: `from src.services.export_service import ExportService` sin error |
| 3 | Crear endpoint `POST /api/bundles/export` | `src/api/routes/bundles.py` (añadir) | `async def export_bundle(payload: ExportRequest, org_id: str = Depends(require_org_id)) -> StreamingResponse` | `import_bundle` en el mismo archivo (línea 53) | BACKEND | Media | 1h | Tareas 1-2 | → verificar: request POST con JSON válido retorna 200 + ZIP |
| 4 | Validar flujo end-to-end (export → import) | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-3 | → verificar: ZIP exportado se importa con `ImportService.process_bundle()` sin errores |

**Tiempo total estimado:** 4.5 horas

### Detalle de implementación — Tarea 2: `ExportService.export()`

```python
def export(self, payload: ExportRequest) -> tuple[bytes, str]:
    # 1. Construir manifest
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bundle_name = f"export_{timestamp}"
    manifest = create_base_manifest(bundle_name)
    
    # 2. Preparar agents
    agents = []
    for a in payload.agents:
        agents.append({
            "role": a.role,
            "soul_json": a.soul_json,
            "allowed_tools": a.allowed_tools,
            "max_iter": a.max_iter,
        })
    
    # 3. Preparar skills
    skills = {}
    if payload.skills:
        for s in payload.skills:
            skills[s["name"]] = s["code"]
    
    # 4. Generar ZIP
    zip_bytes = self.bundle_manager.create_bundle(
        manifest=manifest,
        agents=agents,
        flows=[],  # Sin flows en export individual
        skills=skills,
    )
    
    return zip_bytes, f"{bundle_name}.zip"
```

### Detalle de implementación — Tarea 3: Endpoint

```python
@router.post(
    "/export",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Export agents as FAP-Bundle v2 ZIP",
)
async def export_bundle(
    payload: ExportRequest,
    org_id: str = Depends(require_org_id),
):
    service = ExportService(org_id=org_id)
    zip_bytes, filename = service.export(payload)
    
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
```

---

## 🔮 Roadmap (NO implementar ahora)

- **Paso 08** consumirá este endpoint desde `ExportDialog.tsx`
- Agregar opción "Export from DB" que consulte `agent_catalog` y `skill_catalog` en lugar de recibir datos en el body
- Soporte para exportar flows (hoy solo agents + skills)
- Compresión gzip adicional para bundles > 1MB
- Firma digital del bundle para verificar integridad post-descarga

---

## 🚫 Reglas de Oro cumplidas

- ✅ Análisis accionable y específico — solo Paso 02
- ✅ TODO verificado contra código fuente real
- ✅ Discrepancias documentadas (4 items en §0)
- ✅ Si algo no está definido → señalado con resolución concreta
- ✅ Nivel CTO exigente en rigor y profundidad
- ✅ Coherente con phase-state.md — no contradice decisiones previas
- ✅ TODO el paso cubierto (incluyendo sub-tareas de plan.md)
- ✅ Etapas secuenciales: data → code → backend → fullstack+DX
- ✅ ≥ 1 herramienta DX propuesta (`fap export-bundle`)
- ✅ Tareas atómicas: 1 tarea = 1 artefacto
- ✅ Interfaz exacta por tarea: sin inferencias posibles
- ✅ Patrón de referencia explícito: archivo + línea
- ✅ Verificación inline: comando o check concreto por tarea
- ✅ Suposiciones no verificadas: ≤ 2, marcadas ⚠️

---

*Análisis generado siguiendo `/DEVS/1_ANALISIS.md` v5.2 — Proceso de Análisis Técnico Unificado.*