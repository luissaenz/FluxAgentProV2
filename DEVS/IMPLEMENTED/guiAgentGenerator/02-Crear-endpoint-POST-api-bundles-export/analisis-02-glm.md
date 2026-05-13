# 🧠 Análisis Técnico — Paso 02: Crear endpoint `POST /api/bundles/export`

> **Agente:** glm | **Paso:** 02 | **Fase:** guiAgentGenerator

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|-------------|--------|-----------|
| 1 | Tabla `agent_catalog` existe | grep migraciones | ✅ VERIFICADO | `004_agent_catalog.sql:6` — `id UUID, org_id UUID, role TEXT, soul_json JSONB, allowed_tools TEXT[], max_iter INT, bundle_id UUID, is_active BOOLEAN` |
| 2 | Tabla `bundle_imports` existe | grep migraciones | ✅ VERIFICADO | `0026_bundle_system.sql:13` — `id UUID, org_id UUID, bundle_name TEXT, bundle_hash TEXT, status TEXT, version TEXT, is_active BOOLEAN` |
| 3 | Tabla `skill_catalog` existe | grep migraciones | ✅ VERIFICADO | `0026_bundle_system.sql:27` — `id UUID, org_id UUID, bundle_id UUID, name TEXT, code_source TEXT, metadata JSONB` |
| 4 | Tabla `workflow_templates` existe | grep migraciones | ✅ VERIFICADO | `006_workflow_templates.sql:6` — con `bundle_id UUID` agregado en `0027_bundle_rpc.sql:5` |
| 5 | RPC `import_bundle_atomic` existe | grep migraciones | ✅ VERIFICADO | `0027_bundle_rpc.sql:10` + actualizada en `0028_roadmap_features.sql:21` |
| 6 | `BundleManager.create_bundle()` existe | grep código | ✅ VERIFICADO | `src/services/bundle_manager.py:197` — Recibe `manifest, agents, flows, skills` → retorna `bytes` ZIP |
| 7 | `BundleManifest` modelo Pydantic existe | grep código | ✅ VERIFICADO | `src/services/bundle_schemas.py:22` — `version: str = "2.0"`, `bundle_info: Optional[BundleInfo]`, `hashes: Dict[str, str]` |
| 8 | `BundleInfo` modelo existe | grep código | ✅ VERIFICADO | `src/services/bundle_schemas.py:13` — `name: str`, `description: Optional[str]`, `version: str`, `author: Optional[str]` |
| 9 | `bundle-schema-v2.md` existe | grep docs | ✅ VERIFICADO | `docs/bundle-schema-v2.md` — Define estructura completa del bundle |
| 10 | Router de bundles existe en `src/api/routes/bundles.py` | grep código | ✅ VERIFICADO | Linea 22: `router = APIRouter(prefix="/api/bundles", tags=["Bundles"])`. Ya tiene `/import`, `/validate`, `/history`, `/{bundle_id}/details`, `/{bundle_id}` DELETE |
| 11 | Router de bundles registrado en `main.py` | grep código | ✅ VERIFICADO | `src/api/main.py:23,110` — Import y `include_router(bundles_router)` |
| 12 | `require_org_id` middleware existe | grep código | ✅ VERIFICADO | `src/api/middleware.py:66` — `async def require_org_id(...)` |
| 13 | `IntegrityService` / `calculate_sha256` existe | grep código | ✅ VERIFICADO | `src/services/integrity.py:15` — `calculate_sha256(data: bytes | io.BytesIO) -> str` |
| 14 | `StreamingResponse` usada en el proyecto | grep código | ❌ DISCREPANCIA | NO existe `from fastapi.responses import StreamingResponse` en nigún archivo del proyecto. El plan dice "Devolver StreamingResponse con ZIP" pero nunca se ha usado. |
| 15 | CLI `fap export-agents` existe | grep código | ✅ VERIFICADO | `src/cli/commands/export.py` — Ya exporta agentes a directorio, NO a ZIP por API |
| 16 | CLI `fap package` existe | grep código | ✅ VERIFICADO | `src/cli/commands/package.py` — Crea ZIP desde directorio |
| 17 | `ImportService(org_id)` recibe org_id | grep código | ✅ VERIFICADO | `src/services/import_service.py:29` — Constructor con `self.org_id` |
| 18 | `AgentCatalog` tiene campo `soul_json` | grep código | ✅ VERIFICADO | `004_agent_catalog.sql:12` — `soul_json JSONB NOT NULL DEFAULT '{}'` |
| 19 | RLS `agent_catalog_tenant_isolation` existe | grep código | ✅ VERIFICADO | `004_agent_catalog.sql:22-23` — Poliva RLS con `org_id::text = current_setting(...)` |
| 20 | `get_tenant_client(org_id)` patron usado | grep código | ✅ VERIFICADO | `src/db/session.py:214` — Context manager con RLS |
| 21 | `get_service_client()` patron usado | grep código | ✅ VERIFICADO | `src/db/session.py:55` — Service-role client, bypass RLS |
| 22 | Campo `role` en `agent_catalog` es UNIQUE por org | grep código | ✅ VERIFICADO | `004_agent_catalog.sql:17` — `UNIQUE(org_id, role)` |
| 23 | `max_agents_per_bundle` en settings | grep código | ✅ VERIFICADO | `src/config.py:69` — `max_agents_per_bundle: int = Field(15, ...)` |
| 24 | `max_bundle_size_mb` en settings | grep código | ✅ VERIFICADO | `src/config.py:72` — `max_bundle_size_mb: int = Field(10, ...)` |

### Discrepancias encontradas:

**D1 — `StreamingResponse` no usada en el proyecto:** El plan dice "Devolver StreamingResponse con ZIP para descarga directa". Ningún endpoint existente usa `StreamingResponse`. El patrón actual es leer ZIP bytes en memoria y devolver como `Response` con `media_type="application/zip"`. `BundleManager.create_bundle()` ya retorna `bytes`, lo cual es ideal para `Response(content=zip_bytes, media_type="application/zip")`. **Resolución:** Usar `fastapi.responses.Response` directamente en vez de `StreamingResponse` — ZIP se genera en-memoria, no hay stream. Si en futuro se necesitan bundles >50MB, cambiar a StreamingResponse con generator.

**D2 — El plan dice "Validar que los agentes tengan `role`, `goal`, `backstory` antes de empaquetar" pero la estructura real de `agent_catalog` usa `soul_json` como JSONB que contiene `role`, `goal`, `backstory`:** La columna `role` es top-level en la tabla, pero `goal` y `backstory` están dentro de `soul_json`. La validación debe verificar que `soul_json` contenga esos campos o que el payload del request los provea. **Resolución:** Validar que cada agente en el payload tenga `role` (str), y que bien el agente tenga `goal` y `backstory` en nivel top-level del JSON, o bien `soul_json.goal` y `soul_json.backstory`. Alinear con `bundle-schema-v2.md` que define la estructura de agente con `soul_json` anidado.

**D3 — El plan dice "Aceptar payload: `{ agents: [{role, soul_json, allowed_tools, max_iter}], skills?: [{name, code}] }`". Pero `skills` en el import real es `Dict[str, str]` (filename → code), no `Array<{name, code}>`:** `BundleRPCPayload.skills` es `Dict[str, str]` (filename → source_code) y `BundleManager.create_bundle` espera `skills: Dict[str, str]`. **Resolución:** El payload del export endpoint debe alinearse con lo que `create_bundle` espera. Skills como `Dict[str, str]` (nombre_archivo → código_fuente), no como array de objetos.

**D4 — `ExportService` no existe:** No hay servicio de export en el backend. `CLI export.py` existe pero lee de DB y escribe a filesystem, no genera ZIP via API. `BundleManager.create_bundle()` sí existe y genera ZIP desde datos en memoria, pero es usado internamente. **Resolución:** Crear `ExportService` en `src/services/export_service.py` que orqueste: (1) leer agents/skills de DB, (2) validar payload, (3) llamar `BundleManager.create_bundle()`, (4) retornar bytes. El endpoint solo orquesta HTTP.

**D5 — El plan asume que el endpoint permite especificar agentes por role y que se leen de la DB:** Para exportar, se necesita leer `agent_catalog` para org_id dado, obtener los agentes solicitados y construir el payload. Esto requiere `get_tenant_client(org_id)` para respetar RLS. **Resolución:** Confirmado, se usa `get_tenant_client(org_id)` como patrón existente.

**D6 — No existe endpoint para leer `skill_catalog` por org:** El import lee skills del ZIP, pero no hay endpoint GET para listar skills de una org. Para export, el export service leerá skills directamente de DB via `get_tenant_client`. **Resolución:** El ExportService leerá skills de DB via Supabase client directo, no necesita endpoint separado.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas involucradas

| Tabla | Operación | Columnas relevantes |
|-------|-----------|---------------------|
| `agent_catalog` | READ (filtrar por org_id + roles) | `id, org_id, role, soul_json, allowed_tools, max_iter, is_active, bundle_id` |
| `skill_catalog` | READ (filtrar por org_id + names) | `id, org_id, name, code_source, metadata, bundle_id, is_active` |
| `workflow_templates` | READ (filtrar por org_id + flow_types, si se incluyen flows) | `id, org_id, name, flow_type, definition, code_source, is_python, bundle_id, status` |
| `bundle_imports` | WRITE (crear registro de exportación) | `id, org_id, bundle_name, bundle_hash, status, version, is_active` |

### Schema para agents en export

Según `agent_catalog` migración y `bundle-schema-v2.md`:

```
agent_catalog → JSON de export:
  role (top-level) → agent.role
  soul_json (JSONB) → {
    role: "visible name",
    goal: "...",
    backstory: "...",
    rules: [...],
  }
  allowed_tools (TEXT[]) → agent.allowed_tools
  max_iter (INT) → agent.max_iter
```

### Integridad referencial

- `agent_catalog.org_id → organizations.id` — RLS filtra automáticamente
- `skill_catalog.org_id → organizations.id` — RLS filtra automáticamente
- `workflow_templates.org_id → organizations.id` — RLS filtra automáticamente
- UNIQUE constraint `(org_id, role)` en agent_catalog — evita duplicados

### RLS policies aplicables

- `agent_catalog_tenant_isolation` — `org_id::text = current_setting('app.org_id', TRUE)`
- `skill_catalog_tenant_isolation` — idem
- `bundle_imports_tenant_isolation` — idem

Para lectura en export, se usa `get_tenant_client(org_id)` que setea `app.org_id` en sesión PostgreSQL, cumpliendo RLS.

### Índices necesarios

Ya existen:
- `idx_agent_catalog_org_role` en `(org_id, role) WHERE is_active = TRUE` — ✅ cubre query de lectura por org+role
- `idx_skill_catalog_org` en `(org_id)` — ✅ cubre query de skills por org
- `idx_workflow_templates_org_flow_type` en `(org_id, flow_type)` — ✅ cubre query de flows por org

No se necesitan índices nuevos.

### Tipos de datos

- `soul_json` es `JSONB` — se serializa como dict en Python
- `allowed_tools` es `TEXT[]` — se serializa como list en Python, pero Supabase client retorna como list
- `max_iter` es `INTEGER DEFAULT 5` — safe

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Funciones/clases nuevas

#### `ExportService` (nuevo, `src/services/export_service.py`)

```python
class ExportService:
    def __init__(self, org_id: str):
        self.org_id = org_id
        self.bundle_manager = BundleManager(org_id=org_id)

    def export_bundle(self, payload: ExportRequest) -> bytes:
        """Orquesta la exportación: validar payload → leer datos → generar ZIP."""
        ...

    def _validate_agents(self, agents: List[Dict]) -> None:
        """Validar que cada agente tenga role, goal, backstory."""
        ...

    def _read_agents_from_db(self, roles: List[str]) -> List[Dict]:
        """Leer agentes de agent_catalog filtrando por roles."""
        ...

    def _read_skills_from_db(self, skill_names: List[str]) -> Dict[str, str]:
        """Leer skills de skill_catalog filtrando por nombres."""
        ...

    def _build_manifest(self, name: str, version: str, author: str) -> BundleManifest:
        """Crear BundleManifest con info del bundle."""
        ...
```

#### `ExportRequest` (nuevo, en `src/services/bundle_schemas.py`)

```python
class ExportRequest(BaseModel):
    """Payload para exportar agentes como bundle ZIP."""
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    version: str = Field(default="1.0.0")
    author: Optional[str] = Field(default="user")
    agents: List[AgentExportItem]
    skills: Optional[List[str]] = Field(default=None, description="Lista de nombres de skills a incluir. Vacío = todas")
```

#### `AgentExportItem` (nuevo, en `src/services/bundle_schemas.py`)

```python
class AgentExportItem(BaseModel):
    """Agente individual en el payload de export."""
    role: str = Field(..., min_length=1, max_length=100)
    soul_json: Optional[Dict[str, Any]] = None  # Si None, se lee de agent_catalog
    goal: Optional[str] = None  # Se usa si soul_json no está
    backstory: Optional[str] = None  # Se usa si soul_json no está
    allowed_tools: Optional[List[str]] = Field(default_factory=list)
    max_iter: Optional[int] = Field(default=5)
```

#### Endpoint `POST /api/bundles/export` (nuevo, en `src/api/routes/bundles.py`)

```python
@router.post(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export agents as a bundle ZIP",
)
async def export_bundle(
    request: ExportRequest,
    org_id: str = Depends(require_org_id),
) -> Response:
    ...
```

### Patrones existentes a seguir

1. **Patrón de endpoint** → `src/api/routes/bundles.py:47-109` — `import_bundle()` usa `Depends(require_org_id)`, `HTTPException` para errores, `ImportService(org_id)` como orquestador, try/except con errores específicos.
2. **Patrón de schemas** → `src/services/bundle_schemas.py` — Pydantic BaseModel con `Field(...)`, valores default.
3. **Patrón de service** → `src/services/import_service.py:26-32` — Constructor con `org_id`, usa `get_tenant_client(org_id)`, usa `BundleManager(org_id)`.
4. **Patrón de ZIP creation** → `src/services/bundle_manager.py:197-245` — `create_bundle()` recibe manifest + agents + flows + skills, retorna `bytes`. Genera JSON + hashes automáticamente.

### Modularidad

- `ExportService` en archivo propio → cohesión alta
- `ExportRequest` / `AgentExportItem` en `bundle_schemas.py` → reutiliza modelos existentes
- Endpoint en `bundles.py` existente → no crea archivo nuevo de routes
- `BundleManager.create_bundle()` → ya existe, se reutiliza

### Imports exactos

```python
# src/api/routes/bundles.py (añadir)
from fastapi import Response  # ANADIR a imports existentes
from src.services.bundle_schemas import ExportRequest, ExportResponse  # NUEVO
from src.services.export_service import ExportService  # NUEVO

# src/services/export_service.py (nuevo)
from src.db.session import get_tenant_client
from src.services.bundle_manager import BundleManager, BundleError
from src.services.bundle_schemas import BundleManifest, BundleInfo, AgentExportItem, ExportRequest
from src.config import get_settings
```

### Calidad

- `create_bundle()` en BundleManager ya maneja hashing SHA256 de cada archivo → no duplicar
- `create_bundle()` ya genera ZIP con `manifest.json` al final → consistente
- La validación de `goal` y `backstory` debe alinearse con `bundle-schema-v2.md` que dice "Mínimo 10 caracteres"
- Complejidad ciclomática baja: endpoint delega a service, service delega a BundleManager

---

## 3️⃣ Análisis de Backend (ETAPA 2)

### Endpoints

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| POST | `/api/bundles/export` | Genera ZIP bundle con agents + skills | `require_org_id` |

### Payload del request

```json
{
  "name": "my-bundle",
  "description": "Bundle exportado desde builder",
  "version": "1.0.0",
  "author": "user",
  "agents": [
    {
      "role": "analyst",
      "soul_json": {
        "role": "Analyst",
        "goal": "Analyze data and provide insights.",
        "backstory": "You are a data analyst expert."
      },
      "allowed_tools": ["fetch_url"],
      "max_iter": 3
    }
  ],
  "skills": ["excel_reader"]
}
```

**Campos obligatorios por agente según validación:**
- `role` — siempre requerido (1-100 chars)
- Si NO se provee `soul_json`:
  - `goal` — requerido (min 10 chars)
  - `backstory` — requerido (min 10 chars)
- Si se provee `soul_json`:
  - `soul_json.role` — requerido
  - `soul_json.goal` — requerido (min 10 chars)
  - `soul_json.backstory` — requerido (min 10 chars)

### Response

**Happy path (200):**
```python
Response(
    content=zip_bytes,
    media_type="application/zip",
    headers={"Content-Disposition": f'attachment; filename="{bundle_name}.zip"'}
)
```

**Error paths:**
- **422** — Valicación Pydantic falla (missing role, goal, backstory)
- **400** — `BundleError` (agentes no encontrados en DB, skills no encontrados)
- **413** — Bundle excede `max_bundle_size_mb`
- **500** — Error inesperado

### Middleware aplicable

- `require_org_id` — Obligatorio en todo endpoint de bundles. Extrae `X-Org-ID` header.

### Flujos de datos

```
Request payload → ExportService.export_bundle()
  ├── 1. Validación: cada agente tiene role + (goal + backstory) o soul_json con esos campos
  ├── 2. Para cada agente:
  │     ├── Si tiene soul_json: usar directamente
  │     └── Si no: leer de agent_catalog donde org_id + role match → completar
  ├── 3. Para skills (si se especificaron nombres):
  │     └── Leer de skill_catalog donde org_id + name match
  ├── 4. Construir manifest: BundleManifest(version="2.0", bundle_info=BundleInfo(...), hashes={})
  ├── 5. Llamar BundleManager.create_bundle(manifest, agents, flows=[], skills)
  │     └── Genera ZIP en memoria con manifest + agents/*.json + skills/*.py
  │     └── Calcula hashes SHA256 de cada archivo
  │     └── Retorna bytes
  └── 6. Retornar Response con ZIP bytes + headers
```

### Contratos

**Request→Service contract:**
- `ExportService(org_id: str)` → constructor con org_id del middleware
- `export_service.export_bundle(request: ExportRequest) -> bytes` → retorna ZIP bytes

**Service→BundleManager contract:**
- `BundleManager(org_id: str).create_bundle(manifest, agents, flows, skills) -> bytes` — Ya existe y funciona

### Error handling

```python
try:
    service = ExportService(org_id=org_id)
    zip_bytes = service.export_bundle(request)
    return Response(content=zip_bytes, media_type="application/zip", ...)
except BundleValidationError as e:
    raise HTTPException(status_code=422, detail=str(e))
except BundleError as e:
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.exception("Unexpected error exporting bundle for org %s", org_id)
    raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
```

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo: Builder → Export → Download

```
[Builder UI] → Selecciona agentes + skills
      │
      ▼
POST /api/bundles/export
  Headers: X-Org-ID: <org_uuid>
  Body: ExportRequest JSON
      │
      ▼
[ExportService] → Valida payload → Lee agentes/skills de DB → Genera ZIP
      │
      ▼
Browser recibe ZIP → Download automático
      │
      ▼
[Opcional] POST /api/bundles/import ← Re-importar el ZIP
```

### Coherencia end-to-end

- **Data:** `agent_catalog` es fuente de verdad. El export lee de ahí si no se provee `soul_json` completo.
- **Code:** `BundleManager.create_bundle()` ya genera ZIP válido compatible con `import_bundle` → round-trip garantizado.
- **Backend:** El endpoint `/export` es reverso simétrico de `/import` → usan mismos schemas `BundleManifest`, `BundleInfo`.
- **Fullstack:** El builder visual (Paso 04) enviará el payload `ExportRequest` → recibe ZIP → usuario lo descarga.

### Gaps y fricciones

1. **El export actual NO registra en `bundle_imports`** — El import sí crea un registro en `bundle_imports`. Para simetría, el export debería crear un registro de tipo "export" o similar. Pero el schema actual solo tiene `status IN ('pending', 'validating', 'importing', 'committed', 'failed')` — no hay "exported". **Decisión:** No registrar en `bundle_imports` ya que es una tabla de auditoría de importaciones. El export es stateless.

2. **Skills en payload — El plan dice `skills?: [{name, code}]` pero el formato real del bundle es `skills: Dict[str, str]` (filename → source).** El export request debería simplement pedir nombres de skills, y el servicio lee `code_source` de la DB. **Decisión:** `skills` en `ExportRequest` es `Optional[List[str]]` (nombres), no objetos con código. El servicio lee el código de la DB.

3. **Flows en export — El plan NO menciona flows en el payload.** Sin embargo, `BundleManager.create_bundle` acepta `flows`. Para MVP, el export solo exporta agents + skills. Flows se pueden agregar en paso futuro. **Decisión:** `flows` no se incluye en `ExportRequest` por ahora. El builder aún no maneja flows (viene en Paso 07).

4. **Validación de agent existence — ¿Qué pasa si el usuario pide exportar un agent que no existe en `agent_catalog`?** Ket error debe ser claro: listar los roles no encontrados. **Decisión:** Retornar 400 con detalle de roles faltantes.

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: fap export
- **Qué automatiza:** Exportar bundle desde CLI sin necesidad del builder visual. Hoy solo existe `fap export-agents` que exporta a directorio (no ZIP) y `fap package` que empaqueta desde directorio. El flujo actual es: `fap export-agents` → revisar → `fap package`. Esto es manual y fragmentado.
- **Tipo:** CLI command
- **Cómo se usa:** `fap export --org-id <uuid> --agents analyst,reviewer --skills excel_reader -o bundle.zip`
- **Impacto para el usuario final:** Un solo comando reemplaza 2 pasos manuales (export + package). Permite CI/CD y testing automático del flujo de export.
- **Prioridad:** Tarea 0 — implementar antes que el endpoint para poder testear el endpoint sin curl manual.
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Endpoint lee agentes de agent_catalog respetando RLS (org_id)
✅ [DATA] Endpoint lee skills de skill_catalog respetando RLS (org_id)
✅ [DATA] No se requieren migraciones nuevas (tablas existentes son suficientes)
✅ [DATA] Índices existentes cubren queries de lectura por org_id + role
✅ [CODE] ExportService en src/services/export_service.py con firma definida
✅ [CODE] ExportRequest y AgentExportItem modelos Pydantic en bundle_schemas.py
✅ [CODE] Endpoint POST /api/bundles/export en bundles.py con Depends(require_org_id)
✅ [CODE] Validación: cada agente tiene role + (goal + backstory | soul_json completo)
✅ [CODE] Reutiliza BundleManager.create_bundle() para generar ZIP
✅ [CODE] Manejo de errores: 422 validación, 400 datos no encontrados, 500 inesperado
✅ [BACKEND] POST con payload válido → ZIP descargable con Content-Disposition header
✅ [BACKEND] ZIP contiene manifest.json con version 2.0, bundle_info, hashes
✅ [BACKEND] POST con agente sin role → 422 con error específico
✅ [BACKEND] POST con agente sin goal/backstory → 422 con error específico
✅ [BACKEND] POST con agente que no existe en DB → 400 con roles faltantes
✅ [BACKEND] ZIP se puede re-importar con POST /api/bundles/import sin errores
✅ [FULLSTACK] Flujo completo: builder → POST /export → ZIP → re-import funciona
✅ [FULLSTACK] Skills se leen de DB por nombre, código incluido en ZIP
✅ [DX] Comando CLI `fap export` ejecuta sin errores y genera ZIP válido
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| ZIP excede límite de memoria | Media | BundleManager.create_bundle() carga todo en memoria. `max_bundle_size_mb=10` mitigado pero bundles grandes podrían crecer | Configurar límite en settings + response header con tamaño |
| Agent con `soul_json` malformado | Media | `soul_json` en DB puede tener campos faltantes (goal vacío, backstory corta) | Validar longitud mínima (10 chars) en export, no solo existencia |
| Race condition entre export y concurrente edit | Baja | Agente modificado entre lectura de DB y generación de ZIP | Leer datos una vez al inicio, no re-leer. ZIP es snapshot atómico |
| Skills con código Python peligroso | Alta | Incluir `code_source` de skills puede exponer info sensible si bundle se comparte | SecurityGuard ya valida skills en import; en export solo se copia código fuente existente |
| `StreamingResponse` vs `Response` | Baja | Plan dice StreamingResponse pero no se usa en proyecto | Usar `Response` con `content=bytes` (D1). ZIP en-memoria es suficientemente rápido |
| Flows excluidos del MVP de export | Baja | El builder visual (Paso 07) incluye flows pero el export MVP no | Documentar explícitamente que flows se agregarán en Paso 07/08 |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|-----------------|-----------------|-------|-------------|-------------|--------------|-------------|
| 0 | **DX & Tooling**: `fap export` CLI command | `src/cli/commands/export.py` (modificar existente) | `def export_bundle(org_id: str, agents: str, skills: optional, output: Path, name: optional)` | `src/cli/commands/tools_list.py:29-64` — Typer sub-app con opciones | DX | Media | 1h | Ninguna | → verificar: `fap export --help` ejecuta sin errores |
| 1 | Añadir modelos Pydantic `ExportRequest` + `AgentExportItem` + `ExportResponse` | `src/services/bundle_schemas.py` (modificar existente) | `class ExportRequest(BaseModel): name: str = Field(..., min_length=3, max_length=100); description: Optional[str] = None; version: str = Field(default="1.0.0"); author: Optional[str] = Field(default="user"); agents: List[AgentExportItem]; skills: Optional[List[str]] = None` / `class AgentExportItem(BaseModel): role: str = Field(..., min_length=1, max_length=100); soul_json: Optional[Dict[str, Any]] = None; goal: Optional[str] = None; backstory: Optional[str] = None; allowed_tools: Optional[List[str]] = Field(default_factory=list); max_iter: Optional[int] = Field(default=5)` | `bundle_schemas.py:13-19` — BundleInfo pattern | DATA | Baja | 0.5h | Ninguna | → verificar: `from src.services.bundle_schemas import ExportRequest, AgentExportItem` sin error |
| 2 | Crear `ExportService` | `src/services/export_service.py` (nuevo) | `class ExportService: def __init__(self, org_id: str); def export_bundle(self, request: ExportRequest) -> bytes; def _validate_agents(self, agents: List[AgentExportItem]) -> None; def _read_agents_from_db(self, roles: List[str]) -> List[Dict]; def _read_skills_from_db(self, skill_names: Optional[List[str]]) -> Dict[str, str]` | `src/services/import_service.py:26-32` — Constructor con org_id, usa get_tenant_client | CODE | Media | 2h | Tarea 1 | → verificar: `from src.services.export_service import ExportService` sin error |
| 3 | Añadir endpoint `POST /api/bundles/export` | `src/api/routes/bundles.py` (modificar existente) | `async def export_bundle(request: ExportRequest, org_id: str = Depends(require_org_id)) -> Response` — Status 200, retorna `Response(content=zip_bytes, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{name}.zip"'})` | `src/api/routes/bundles.py:47-109` — import_bundle pattern con Depends(require_org_id), try/except | BACKEND | Media | 1.5h | Tarea 2 | → verificar: `uv run python -c "from src.api.routes.bundles import router"` sin error |
| 4 | Test unitario: ExportService.validación | `tests/unit/test_export_service.py` (nuevo) | `test_validate_agents_with_goal_backstory`, `test_validate_agents_with_soul_json`, `test_validate_agents_missing_role`, `test_validate_agents_short_goal`, `test_export_bundle_reads_from_db`, `test_export_bundle_generates_valid_zip` | `tests/unit/` pattern existente | FULLSTACK | Media | 1.5h | Tareas 1-3 | → verificar: `uv run pytest tests/unit/test_export_service.py -v` pasa |
| 5 | Test integración: endpoint endpoint-to-end | `tests/integration/test_bundles_export.py` (nuevo) | `test_export_valid_payload_returns_zip`, `test_export_missing_role_returns_422`, `test_export_agent_not_found_returns_400`, `test_export_roundtrip_with_import` | `tests/integration/` pattern existente | FULLSTACK | Media | 1.5h | Tareas 1-4 | → verificar: `uv run pytest tests/integration/test_bundles_export.py -v` pasa |
| 6 | Actualizar CLI `fap export` para usar ExportService vía API | `src/cli/commands/export.py` (modificar existente) | `def export_bundle(org_id: str, agents: str, skills: optional, output: Path, name: optional)` — Usa `httpx.post` contra `/api/bundles/export` con payload | `src/cli/commands/tools_list.py` — patron de CLI con httpx | DX | Media | 1h | Tarea 3 | → verificar: `fap export --org-id test --agents analyst -o bundle.zip` genera ZIP válido |

**Tiempo total estimado:** 8 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Export con flows incluidos:** Cuando el builder visual (Paso 07) soporte canvas con tasks/flows, añadir `flows` al `ExportRequest` y al `ExportService`.
- **Export incremental/diff:** Solo exportar agentes que cambiaron desde última export (comparar hashes).
- **Cache de export:** Para bundles grandes, cachear ZIP generado por org_id + hash de payload.
- **Streaming export:** Para bundles >50MB, migrar a `StreamingResponse` con generation yield.
- **Registro de exportaciones:** Añadir tabla `bundle_exports` para auditoría (who exported what, when).
- **Validación pre-export:** Endpoint `POST /api/bundles/export/validate` para dry-run sin generar ZIP.

---

## 🚫 Reglas de Oro

- ✅ **Análisis basado en código real**, no supuestos — 24 elementos verificados contra código
- ✅ **6 discrepancias detectadas** — D1 StreamingResponse, D2 soul_json validation, D3 skills format, D4 ExportService nuevo, D5 lectura DB con RLS, D6 no hay endpoint GET skills
- ✅ **Todo verificado contra código**, planes de implementación referencian archivos concretos
- ✅ **Si el plan contradice el código** → el código gana (D1: Response vs StreamingResponse, D3: Dict skills vs Array)
- ✅ **Nivel CTO exigente** en rigor
- ✅ **Coherente con phase-state.md** — patrón de org_id + RLS + BundleManager existente
- ✅ **TODO el paso cubierto** — endpoint + service + validación + error handling + CLI DX
- ✅ **Etapas secuenciales** — data → code → backend → fullstack+DX
- ✅ **1 herramienta DX propuesta** — `fap export` CLI
- ✅ **Tareas atómicas** — 1 archivo/función por tarea, interfaz completa, patrón explícito, verificación inline