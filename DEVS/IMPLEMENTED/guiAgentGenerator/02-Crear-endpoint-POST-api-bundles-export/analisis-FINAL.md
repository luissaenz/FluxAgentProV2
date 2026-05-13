# 🏛️ ANÁLISIS UNIFICADO FINAL — Paso 02: `POST /api/bundles/export`

> **Proyecto:** FluxAgentPro-v2
> **Fase:** guiAgentGenerator
> **Paso:** 02 — Crear endpoint `POST /api/bundles/export`
> **Unificador:** Arquitecto de Sistemas Senior
> **Fecha:** 2026-05-13
> **Fuente de verdad:** Código real en `src/` y `supabase/migrations/` — plan.md es secundario

---

### 0️⃣ Evaluación de Análisis y Verificaciones (OBLIGATORIO)

#### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| RING | ✅ 12 elementos | 4 | ✅ `fap export-bundle` | ✅ Líneas exactas | 4.2 |
| DSP | ✅ 21 elementos | 6 | ✅ `fap bundle export` | ✅ Líneas exactas | 5.0 |
| LAGUNA | ✅ 14 elementos | 4 | ✅ `bundle-validator` | ⚠️ Sin líneas exactas | 3.0 |
| GLM | ✅ 24 elementos | 6 | ✅ `fap export` | ✅ Líneas exactas | 4.8 |
| GF | ✅ 8 elementos | 3 | ✅ `curl-export-test` | ❌ Solo nombres de archivo | 2.0 |

#### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|-------------|---------|--------------------------|------------|
| 1 | **Skills format**: Plan dice `skills?: [{name, code}]` (array objects). `create_bundle()` espera `Dict[str, str]` (filename→code) | DSP, GLM | ✅ `bundle_manager.py:197` | Handler convierte `[{name, code}]` → `{name: code}`. Coincide con interfaz de usuario amigable. |
| 2 | **StreamingResponse vs Response**: Plan dice StreamingResponse. ZIP se genera entero en memoria por `create_bundle()`, no hay streaming real. | GLM (D1) | ✅ `bundle_manager.py:197-245` retorna `bytes` | Usar `Response(content=zip_bytes, media_type="application/zip")`. Migrar a `StreamingResponse` si bundles >50MB en futuro. |
| 3 | **Payload omite `model` e `is_active` del schema v2 real**: Plan solo incluye 4 campos, el schema real tiene 7. | DSP (D1) | ✅ `004_agent_catalog.sql:6-17` | MVP exporta lo que envía el builder (Paso 04). `model` e `is_active` se agregan cuando el builder los provea. No bloq. |
| 4 | **Payload omite `flows`**: Plan no menciona flows. `create_bundle()` acepta `flows: List[Dict]`. | DSP (D4), GLM (gap 3) | ✅ `bundle_manager.py:197` | `flows` excluido de MVP. Canvas (Paso 07) agregará flows al export. Pasar `flows=[]` a `create_bundle()`. |
| 5 | **`max_iter` rango inconsistente**: RING dice 1-50, DSP dice 1-5, GLM dice default 5. | RING, DSP, GLM | ✅ `004_agent_catalog.sql:16` (DEFAULT 5) | Rango 1-50 para flexibilidad (DSP muy restrictivo). Default 5. Coincide con `agent_catalog` schema. |
| 6 | **soul_json ambiguity**: Dos formatos posibles en DB (full JSON importado vs nested soul). En request payload no aplica — datos vienen del form. | DSP (D3) | ✅ Request payload ≠ DB lookup | MVP: datos vienen del builder en body. Sin ambigüedad. Si se agrega lectura de DB post-MVP, resolver con detección defensiva. |
| 7 | **Validación `role`+`goal`+`backstory`**: Plan lo pide, `create_bundle()` no lo valida. | TODOS | ✅ `bundle_manager.py:197` | Validar en el handler ANTES de llamar a `create_bundle()`. Responsabilidad del endpoint, no del bundle manager. |
| 8 | **`ExportService` nuevo vs inline**: RING/GLM proponen nuevo archivo, DSP/LAGUNA/GF proponen inline en handler. | Todos | ✅ Patrón `ImportService` en `import_service.py:26-32` | Crear `ExportService` en `src/services/export_service.py`. Cohesión, testabilidad, consistente con `ImportService`. |
| 9 | **Falta endpoint GET skills para listar**: No hay endpoint para obtener skills de una org. ExportService necesita leer de DB. | GLM (D6) | ✅ No existe endpoint de skills | ExportService usa `get_tenant_client(org_id)` y consulta `skill_catalog` directo. No requiere endpoint separado. |

---

### 1️⃣ Resumen Ejecutivo

- **Objetivo:** Crear endpoint `POST /api/bundles/export` que genera ZIP descargable en formato bundle-schema-v2 a partir de agentes + skills enviados por el builder visual. Complemento simétrico de `POST /api/bundles/import`.
- **Correcciones críticas al plan:**
  1. Plan dice `StreamingResponse` → código usa `Response` (ZIP en memoria, no streaming real)
  2. Plan dice `skills?: [{name, code}]` → `create_bundle()` espera `Dict[str, str]`, handler debe convertir
  3. Plan no menciona `ExportService` → se crea como orquestador (patrón ImportService)
- **Herramienta DX seleccionada:** `fap bundle export` (propuesta DSP — naming consistente con `fap tools list`). Fusiona lo mejor de todas: naming DSP, features RING+GLM, testing-helper LAGUNA como utilidad separada.

---

### 2️⃣ Diseño Funcional Consolidado

#### Happy Path

1. Dashboard (Builder) envía `POST /api/bundles/export` con payload JSON
2. FastAPI valida `ExportBundleRequest` automáticamente (Pydantic) → 422 si inválido
3. `require_org_id` extrae `X-Org-ID` header → 400 si ausente
4. Handler valida cada agente: `soul_json.goal` y `soul_json.backstory` requeridos → 422 si faltan
5. Handler convierte skills array → dict: `{s.name: s.code for s in skills}`
6. `ExportService(org_id)` construye `BundleManifest` vía `create_base_manifest()`
7. `ExportService` llama `BundleManager.create_bundle(manifest, agents, flows=[], skills)`
8. `create_bundle()` genera ZIP en memoria con `manifest.json` + `agents/*.json` + `skills/*.py` + hashes SHA256
9. Handler retorna `Response(content=zip_bytes, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=..."})`
10. Navegador descarga ZIP

#### Edge Cases MVP

- Payload con `agents` vacío → 422 (`min_length=1`)
- Payload con `agents` > 15 → 422 (`max_length=15`)
- Agent sin `soul_json.goal` → 422 específico: `"agent '{role}': soul_json.goal required"`
- Agent sin `soul_json.backstory` → 422 específico
- `max_iter` fuera de rango (1-50) → 422 (Pydantic `ge=1, le=50`)
- `soul_json` no es dict válido → 422 (Pydantic type validation)
- Error interno en `create_bundle()` → 500 con logging
- ZIP generado debe ser re-importable por `POST /api/bundles/import`

---

### 3️⃣ Diseño Técnico Definitivo

#### Componentes y Modificaciones

| Ruta real | Tipo | Descripción | Interfaces clave |
|-----------|------|-------------|-----------------|
| `src/services/bundle_schemas.py` | Modificación | Añadir modelos `AgentExportItem`, `SkillExportItem`, `ExportBundleRequest` | `AgentExportItem(BaseModel)`, `ExportBundleRequest(BaseModel)` |
| `src/services/export_service.py` | Creación | Servicio orquestador: valida payload, construye manifest, llama `create_bundle()` | `ExportService(org_id).export(req) -> tuple[bytes, str]` |
| `src/api/routes/bundles.py` | Modificación | Añadir endpoint `POST /api/bundles/export` + imports | `async def export_bundle(req, org_id=Depends(require_org_id)) -> Response` |
| `src/cli/commands/bundle_export.py` | Creación | CLI `fap bundle export` — exporta de DB directo (Tarea 0) | `def bundle_export(org_id, output, include_skills, roles, version) -> Path` |
| `tests/unit/test_bundle_export.py` | Creación | Tests unitarios de validación y export | `test_export_*` (5 tests mínimos) |
| `tests/integration/test_bundle_export_roundtrip.py` | Creación | Test de integración round-trip export→import | `test_export_import_roundtrip` |
| `scripts/bundle_validator.py` | Creación | Script helper para validar ZIPs exportados (opcional, no bloqueante) | `validate_bundle(path) -> ValidationResult` |

#### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: `fap bundle export`
- **Qué automatiza:** Exportar agentes de DB a ZIP bundle desde CLI. Reemplaza flujo manual: consultar DB → construir JSON → curl → obtener ZIP.
- **Tipo:** CLI (Typer command)
- **Ubicación:** `src/cli/commands/bundle_export.py`
- **Cómo se usa:**
  ```bash
  fap bundle export --org-id <UUID> --output backup.zip
  fap bundle export --org-id <UUID> --include-skills --output full-backup.zip
  fap bundle export --org-id <UUID> --roles recepcionista,analyst --output partial.zip
  ```
- **Impacto para el usuario final:** Elimina apertura de dashboard, copia de payloads manuales, curl/Postman. Un comando → ZIP listo.
- **El implementador DEBE usarla** para validar que export endpoint y CLI comparten lógica (dogfooding obligatorio).

### Helper complementario: `scripts/bundle_validator.py`
- **Qué automatiza:** Validar estructura de ZIP exportado sin consumir el endpoint.
- **Tipo:** Script CLI
- **Uso:** `uv run python scripts/bundle_validator.py ./bundle.zip`
- **Nota:** No bloqueante, implementar después del endpoint si hay tiempo.
```

---

### 4️⃣ Decisiones Tecnológicas

1. **Response vs StreamingResponse:** Se usa `fastapi.responses.Response(content=bytes)` porque `BundleManager.create_bundle()` genera el ZIP completo en memoria. No hay beneficio real de streaming. Si bundles >50MB en futuro, migrar a `StreamingResponse` con generator chunked. Fuente: `bundle_manager.py:197-245` retorna `bytes`.

2. **ExportService en archivo separado:** Consistente con `ImportService` en `import_service.py`. Separa concerns: handler maneja HTTP, service maneja lógica de negocio. Permite test unitario sin FastAPI.

3. **Skills como `List[SkillExportItem]` en payload, no `Dict[str,str]`:** El usuario envía `skills: [{name, code}]` (amigable para frontend), el handler convierte a `Dict[str,str]` para `create_bundle()`. La conversión es simple: `{s.name: s.code for s in payload.skills}`.

4. **Validación de agentes en handler, no en service:** Regla: validación de input (Pydantic + reglas de negocio simples) en handler, lógica compleja en service. `goal`/`backstory` check en handler porque depende del contrato HTTP.

5. **`bundle_name` opcional con default:** Si no se provee, generar `export_YYYYmmdd_HHMMSS`. Coincide con timestamp naming de `create_bundle()`.

6. **Sin registro en `bundle_imports`:** El export es stateless. No se persiste registro de exportación. Tabla `bundle_imports` es solo para auditoría de imports.

7. **Correcciones al plan:**
   - ⚠️ El plan dice "Devolver StreamingResponse" pero el código real genera ZIP en memoria. Usar `Response(content=bytes)`.
   - ⚠️ El plan dice `skills?: [{name, code}]` pero `create_bundle()` espera `Dict[str,str]`. Handler convierte.
   - ⚠️ El plan no menciona `ExportService` como componente separado. Se crea por cohesión y testabilidad.
   - ⚠️ El plan omite `flows` del payload. Soportados por `create_bundle()` pero excluidos de MVP.

---

### 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA]   Modelo ExportBundleRequest con agents (min 1, max 15) y skills (optional List[{name, code}])
✅ [DATA]   Modelo AgentExportItem valida: role (1-100), soul_json (dict), allowed_tools (list), max_iter (1-50 default 5)
✅ [DATA]   Validador soul_json.goal y soul_json.backstory requeridos → 422 con mensaje específico
✅ [CODE]   ExportService en src/services/export_service.py con export(payload) -> tuple[bytes, str]
✅ [CODE]   ExportService reutiliza BundleManager.create_bundle() — sin duplicación de lógica ZIP
✅ [CODE]   Endpoint POST /api/bundles/export con firma correcta y Depends(require_org_id)
✅ [BACKEND] POST con payload válido → 200 + ZIP descargable (Content-Type: application/zip)
✅ [BACKEND] ZIP contiene manifest.json válido bundle-schema-v2 con bundle_info + hashes
✅ [BACKEND] POST sin goal/backstory → 422: "agent 'X': soul_json.goal required"
✅ [BACKEND] POST con agents vacío → 422 (Pydantic min_length=1)
✅ [FULLSTACK] ZIP exportado se re-importa con POST /api/bundles/import sin errores (round-trip)
✅ [FULLSTACK] Content-Disposition header incluye filename correcto
✅ [FULLSTACK] Skills incluidos en ZIP aparecen en skills/ dentro del bundle
✅ [DX]       Comando fap bundle export --org-id <UUID> genera ZIP válido sin errores
✅ [DX]       Comando fap bundle export --help muestra ayuda completa
```

**Funcionales:**
- [ ] POST con payload válido → ZIP descargable con estructura correcta
- [ ] POST con datos inválidos → 422 con mensaje descriptivo
- [ ] ZIP re-importable con POST /api/bundles/import

**Técnicos:**
- [ ] ExportService pasa tests unitarios (validación + generación ZIP)
- [ ] Round-trip export→import pasa test de integración
- [ ] CLI `fap bundle export` ejecuta sin errores
- [ ] Sin nuevas migraciones de DB requeridas

---

### 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|-------|------------|-------------|--------------|
| 0 | **DX & Tooling:** `fap bundle export` CLI en `src/cli/commands/bundle_export.py` | Media | 1.5h | Ninguna |
| 1 | Modelos Pydantic `AgentExportItem`, `SkillExportItem`, `ExportBundleRequest` en `src/services/bundle_schemas.py` | Baja | 0.5h | Tarea 0 |
| 2 | `ExportService` en `src/services/export_service.py` — orquesta validación + manifest + create_bundle | Media | 1.5h | Tarea 1 |
| 3 | Endpoint `POST /api/bundles/export` en `src/api/routes/bundles.py` — handler + imports + validación | Media | 1.5h | Tarea 2 |
| 4 | Tests unitarios: `tests/unit/test_bundle_export.py` (5 tests: validación x3, generación, error) | Media | 1h | Tarea 3 |
| 5 | Test integración round-trip: `tests/integration/test_bundle_export_roundtrip.py` | Media | 1h | Tarea 4 |
| 6 | Validación E2E: CLI + endpoint + round-trip — todos los criterios §5 pasan | Baja | 0.5h | Tareas 1-5 |
| **TOTAL** | | | **7.5h** | |

> **Tarea 0 siempre = DX & Tooling.** Implementador DEBE ejecutarla primero y usar la herramienta resultante para dogfooding.

#### Detalle Tarea 2 — ExportService.export()

```python
def export(self, payload: ExportBundleRequest) -> tuple[bytes, str]:
    bundle_name = payload.bundle_name or f"export_{datetime.utcnow():%Y%m%d_%H%M%S}"
    manifest = create_base_manifest(bundle_name)

    agents = [
        {
            "role": a.role,
            "soul_json": a.soul_json,
            "allowed_tools": a.allowed_tools,
            "max_iter": a.max_iter,
        }
        for a in payload.agents
    ]

    skills = {}
    if payload.skills:
        for s in payload.skills:
            skills[s.name] = s.code

    zip_bytes = self.bundle_manager.create_bundle(
        manifest=manifest,
        agents=agents,
        flows=[],
        skills=skills,
    )

    return zip_bytes, f"{bundle_name}.zip"
```

#### Detalle Tarea 3 — Endpoint

```python
@router.post(
    "/export",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Export agents as FAP-Bundle v2 ZIP",
)
async def export_bundle(
    payload: ExportBundleRequest,
    org_id: str = Depends(require_org_id),
) -> Response:
    service = ExportService(org_id=org_id)
    zip_bytes, filename = service.export(payload)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
```

**Imports a añadir en `bundles.py`:**
```python
from io import BytesIO
from fastapi.responses import Response
from src.services.export_service import ExportService
from src.services.bundle_schemas import ExportBundleRequest
```

---

### 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| ZIP exportado no re-importable por `POST /api/bundles/import` | Alta | Mapeo de datos entre ExportRequest y create_bundle() tiene discrepancias de formato | Test E2E round-trip (Tarea 5). Export → Import en mismo test. |
| ZIP excede límite de memoria | Media | 15 agents + skills grandes → ZIP >50MB en memoria | Límite `max_bundle_size_mb=10` en config. Sin streaming, responsabilidad del config. |
| soul_json.goal/backstory con validación débil | Media | Se aceptan strings vacíos o muy cortos | Validar longitud mínima 10 chars en handler, consistente con `bundle-schema-v2.md` |
| Divergencia CLI ↔ endpoint | Baja | `fap bundle export` y endpoint usan lógica de reconstrucción distinta | Ambos usan `ExportService` y `BundleManager.create_bundle()` — misma lógica compartida |
| Timeout HTTP en bundles grandes | Baja | `create_bundle()` síncrono, >30s puede timeout | 10 MB límite mitiga. Post-MVP: BackgroundTasks + polling |

---

### 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|----|------|-------|-----------------|
| TP-1 | Export válido con 1 agent + 1 skill | `{agents: [{role, soul_json{goal,backstory}, tools}], skills: [{name, code}]}` | 200 + ZIP con manifest.json, agents/, skills/ |
| TP-2 | Export sin goal en soul_json | `{agents: [{role, soul_json: {role, backstory}}]}` | 422: "soul_json.goal required" |
| TP-3 | Export con agents vacío | `{agents: []}` | 422: Pydantic min_length=1 |
| TP-4 | Export con max_iter > 50 | `{agents: [{..., max_iter: 100}]}` | 422: Pydantic ge=1, le=50 |
| TP-5 | Round-trip: export → import | ZIP generado por TP-1 → POST /api/bundles/import | 200 + BundleRPCResult con status=committed |
| TP-6 | CLI `fap bundle export --help` | --help flag | Output no-errors con opciones documentadas |

**Comando para ejecutar tests:**
```bash
uv run pytest tests/unit/test_bundle_export.py -v
uv run pytest tests/integration/test_bundle_export_roundtrip.py -v
```
