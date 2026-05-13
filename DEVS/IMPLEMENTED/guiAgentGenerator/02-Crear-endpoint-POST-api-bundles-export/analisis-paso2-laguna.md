# Análisis Paso 2 - laguna

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `BundleManager.create_bundle()` existe | grep en `src/services/bundle_manager.py` | ✅ | src/services/bundle_manager.py:197-245 |
| 2 | `BundleManifest` schema con `hashes` dict | grep en `src/services/bundle_schemas.py` | ✅ | src/services/bundle_schemas.py:22-43 |
| 3 | `BundleContent` schema con agents/flows/skills | grep en `src/services/bundle_schemas.py` | ✅ | src/services/bundle_schemas.py:45-58 |
| 4 | `agent_catalog` tabla existe | grep en `supabase/migrations/004_agent_catalog.sql` | ✅ | Columnas: id, org_id, role, soul_json, allowed_tools, max_iter |
| 5 | `skill_catalog` tabla existe | grep en `supabase/migrations/0026_bundle_system.sql` | ✅ | src/services/import_service.py:250-277 |
| 6 | `bundle_imports` tabla existe | grep en `supabase/migrations/0026_bundle_system.sql` | ✅ | Schema con id, org_id, bundle_name, bundle_hash |
| 7 | `BundleRPCResult` schema | grep en `src/services/bundle_schemas.py` | ✅ | status, bundle_id, agents_count, flows_count, skills_count, error |
| 8 | `BundleRPCPayload` schema | grep en `src/services/bundle_schemas.py` | ✅ | bundle_name, bundle_hash, version, agents, flows, skills |
| 9 | `ImportService` existe | ls check | ✅ | src/services/import_service.py |
| 10 | `StreamingResponse` disponible en FastAPI | import check | ✅ | fastapi.responses.StreamingResponse |
| 11 | Archivo `src/api/routes/bundles.py` existe | ls check | ✅ | Existe con endpoint import validado |
| 12 | `require_org_id` middleware existe | grep en `src/api/middleware.py` | ✅ | src/api/middleware.py:66-81 |
| 13 | `security_guard` en `BundleManager` | src/services/bundle_manager.py:54-57 | ✅ | SecurityGuard valida skills |
| 14 | Endpoint `POST /api/bundles/import` existe | grep en bundles.py | ✅ | src/api/routes/bundles.py:47-109 |

### Discrepancias encontradas:

1. **❌ Endpoint `POST /api/bundles/export` no existe**: Debe crearse. El archivo `bundles.py` solo tiene `import` pero no `export`.

2. **❌ Falta validación de campos requeridos**: El plan menciona validar `role`, `goal`, `backstory` antes de empaquetar, pero el `BundleManager.create_bundle()` no tiene esta validación — asume datos válidos.

3. **⚠️ `StreamingResponse` no usado en bundles.py**: El archivo existing usa `UploadFile` para import, pero no hay patrón de descarga con `StreamingResponse` en el módulo.

4. **❌ Payload del plan falta `flows` y `skills` definición**: El plan dice `{ agents: [...], skills?: [...] }` pero el schema v2 incluye también `flows`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema impactado
- **Ninguna tabla nueva** - El paso exporta datos existentes a ZIP
- Tablas referenciadas: `agent_catalog`, `skill_catalog`, `bundle_imports`

### Relaciones entre tablas
- `agent_catalog` → `bundle_imports` (via `bundle_id`)
- `skill_catalog` → `bundle_imports` (via `bundle_id`)

### RLS aplicable
- Solo lectura de tablas propias del tenant
- `require_org_id` middleware ya aplica tenant isolation

### Índices necesarios
- Ninguno adicional - usa queries existentes

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivos a crear/modificar
1. **`src/api/routes/bundles.py`** (modificar - agregar endpoint export)

### Firma del endpoint a crear
```python
# src/api/routes/bundles.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AgentExport(BaseModel):
    role: str
    soul_json: Dict[str, Any] = Field(..., description="Must include role, goal, backstory")
    allowed_tools: List[str] = []
    max_iter: int = 3

class ExportRequest(BaseModel):
    agents: List[AgentExport]
    skills: Optional[List[Dict[str, str]]] = None  # {name, code}

@router.post("/export")
async def export_bundle(
    request: ExportRequest,
    org_id: str = Depends(require_org_id),
) -> StreamingResponse:
    """Export agents as ZIP bundle (bundle-schema-v2)."""
```

### Patrón a seguir
- **Referencia**: `src/api/routes/bundles.py :: import_bundle`
- **Patrón de request**: `src/api/routes/agents.py :: RunAgentRequest`
- **StreamingResponse**: No hay ejemplo en el proyecto, usar FastAPI estándar

### Validaciones requeridas
```python
# Validar soul_json requerido
for agent in request.agents:
    if "goal" not in agent.soul_json or "backstory" not in agent.soul_json:
        raise HTTPException(422, f"Agent {agent.role} missing goal or backstory")
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoint a crear
- **Ruta**: `POST /api/bundles/export`
- **Method**: POST
- **Auth**: `require_org_id` middleware
- **Request**: `ExportRequest` con `agents` y `skills?`
- **Response**: `StreamingResponse` con ZIP (media_type: `application/zip`)
- **Error**: 422 con detalle si validación falla

### Flujo de datos
```
POST /api/bundles/export
  → require_org_id() extrae org_id
  → Validar soul_json.goal y soul_json.backstory en cada agente
  → BundleManager.create_bundle() genera ZIP en memoria
  → StreamingResponse con archivo ZIP
```

### Payload de ejemplo (happy path)
```json
{
  "agents": [
    {
      "role": "researcher",
      "soul_json": {"role": "Researcher", "goal": "Research topics", "backstory": "Expert researcher"},
      "allowed_tools": ["excel_reader"],
      "max_iter": 3
    }
  ],
  "skills": [
    {"name": "custom_tool.py", "code": "from crewai_tools import BaseTool..."}
  ]
}
```

### Error handling
- 422: `soul_json` sin `goal` o `backstory`
- 500: Error generando ZIP (loggear stack trace)

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end
```
Builder visual → POST /api/bundles/export → Descarga ZIP → POST /api/bundles/import
```

### Herramienta Propuesta: DX & Tooling

**Herramienta Propuesta: bundle-validator**

- **Qué automatiza:** Validar un bundle ZIP antes de enviarlo al endpoint export, detectando errores de schema sin consumir el endpoint.
- **Tipo:** Script CLI
- **Cómo se usa:**
  ```bash
  uv run python scripts/bundle_validator.py ./my-bundle.zip
  ```
- **Impacto para el usuario final:** Reduce iteración — detecta errores de manifest/agentes antes de exportar desde el builder.
- **Prioridad:** Tarea 0

### Inconsistencias detectadas
- El plan solo menciona `skills` como opcional, pero `BundleManager.create_bundle()` también soporta `flows`
- El plan no especifica el nombre del archivo ZIP — se propone `bundle-{timestamp}.zip`

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Verificable |
|---|---|---|
| 1 | [DATA] POST con datos válidos → ZIP descargable | ✅ `curl -X POST -H "X-Org-ID: test" -d '{"agents":[...]}' http://localhost:8000/api/bundles/export -o bundle.zip` |
| 2 | [DATA] ZIP contiene `manifest.json` válido | ✅ `unzip -l bundle.zip` verifica estructura |
| 3 | [DATA] `manifest.json` incluye `bundle_info` + `hashes` | ✅ Extraer y validar JSON |
| 4 | [BACKEND] POST sin `goal`/`backstory` → 422 | ✅ `curl -X POST -d '{"agents":[{"role":"x","soul_json":{}}]}'` devuelve 422 |
| 5 | [FULLSTACK] ZIP se puede re-importar sin errores | ✅ `curl -X POST -F "file=@bundle.zip" /api/bundles/import` importa OK |
| 6 | [CODE] Endpoint usa `StreamingResponse` | ✅ Código muestra `return StreamingResponse(iter([zip_bytes]), ...)` |
| 7 | [DX] bundle-validator implementado | ✅ `python scripts/bundle_validator.py --help` funciona |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| ZIP corrupto por memoria | Media | `create_bundle()` devuelve bytes, no escribe a disco | Validar con `zipfile.is_zipfile()` antes de return |
| Validación de skills insuficiente | Media | SecurityGuard no se ejecuta en export | Documentar que skills pasan validación en import |
| Filename ZIP sin timestamp | Baja | Problemas si múltiples exports simultáneos | Incluir UUID en filename |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | DX: bundle-validator | `scripts/bundle_validator.py` | `def validate_bundle(path: Path) -> ValidationResult` | Nuevo | DX | Baja | 0.5h | Ninguna | → `python scripts/bundle_validator.py docs/bundle-schema-v2.md` retorna OK |
| 1 | Crear endpoint export | `src/api/routes/bundles.py` | `@router.post("/export") async def export_bundle(request: ExportRequest, org_id: str = Depends(require_org_id)) -> StreamingResponse` | `bundles.py :: import_bundle` | BACKEND | Media | 1h | Tarea 0 | → `curl -X POST localhost:8000/api/bundles/export` devuelve 200 + ZIP |
| 2 | Validar integración | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 0-1 | → Export → Import flujo completo funciona |

**Tiempo total estimado:** 2.0 horas