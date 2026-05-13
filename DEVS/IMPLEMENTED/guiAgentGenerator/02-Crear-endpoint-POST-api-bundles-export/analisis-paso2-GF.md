# 🧠 ANÁLISIS TÉCNICO - PASO 02 - GF

## 0️⃣ Verificación Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `BundleManager` | `src/services/bundle_manager.py` | ✅ | Clase (L51) |
| 2 | `create_bundle` | `src/services/bundle_manager.py` | ✅ | Método (L197) |
| 3 | `BundleManifest` | `src/services/bundle_schemas.py` | ✅ | Schema (L22) |
| 4 | `routes/bundles.py` | `src/api/routes/bundles.py` | ✅ | Archivo existe |
| 5 | `StreamingResponse` | `from fastapi.responses` | ✅ | Nativo FastAPI |
| 6 | `zipfile` usage | `src/services/bundle_manager.py` | ✅ | L12, L216 |
| 7 | `import_bundle` | `src/api/routes/bundles.py` | ✅ | Patrón @router.post (L47) |
| 8 | `require_org_id` | `src/api/middleware.py` | ✅ | Usado en L56 de bundles.py |

**Discrepancias:**
- `create_bundle` ya existe (L197). El plan sugiere "crearlo", pero mejor reutilizarlo y extenderlo.
- Payload del plan no incluye `flows`. -> *Soportar lista vacía por defecto.*
- `manifest.json` requiere hashes. -> *`create_bundle` ya lo hace automáticamente.*

---

## 1️⃣ Análisis de Datos
- **Tablas:** Ninguna (Export es generativo, no persiste).
- **Schema:** Sin cambios.
- **RLS:** No aplica (Endpoint transitorio).

---

## 2️⃣ Análisis de Código
- **Modificar:** `src/api/routes/bundles.py`.
- **Nuevo Schema:**
```python
class ExportAgentRequest(BaseModel):
    role: str
    soul_json: Dict[str, Any]
    allowed_tools: List[str]
    max_iter: int = 3

class BundleExportRequest(BaseModel):
    agents: List[ExportAgentRequest]
    skills: Optional[List[Dict[str, str]]] = []
    flows: Optional[List[Dict[str, Any]]] = []
```
- **Logic:**
  1. Validar requeridos (`role`, `goal`, `backstory` dentro de `soul_json`).
  2. Instanciar `BundleManager`.
  3. Llamar `create_bundle` con `agents`, `flows`, `skills`.
  4. Retornar bytes vía `StreamingResponse`.

---

## 3️⃣ Análisis de Backend
- **Endpoint:** `POST /api/bundles/export`.
- **Payload:** JSON (agentes + skills).
- **Response:** `application/zip` (Streaming).
- **Header:** `Content-Disposition: attachment; filename="bundle.zip"`.

---

## 4️⃣ Análisis de Fullstack + DX
- **Flujo:** Builder Frontend -> POST JSON -> Backend ZIP -> Descarga.
- **DX Tooling:**
  ### Herramienta: `curl-export-test`
  - **Qué:** Script para disparar el export y guardar el ZIP en disco local.
  - **Tipo:** Bash/Python script.
  - **Uso:** `./scripts/test_export.sh`.
  - **Prioridad:** Tarea 0.

---

## 5️⃣ Criterios de Aceptación
- ✅ `POST /api/bundles/export` devuelve ZIP binario.
- ✅ ZIP contiene `manifest.json` con hashes válidos.
- ✅ ZIP contiene `agents/` y `skills/` (si aplica).
- ✅ Payload inválido (sin role) devuelve 422.
- ✅ ZIP resultante es importable vía `POST /api/bundles/import`.

---

## 6️⃣ Riesgos
| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Memoria | Media | Bundles gigantes | Límite 50MB (configurado en `BundleManager`). |
| Corrupción ZIP | Baja | Stream interrumpido | `zipfile.ZIP_DEFLATED` + validación final. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón | Etapa | T |
|---|---|---|---|---|---|---|
| 0 | **DX**: Test Export Script | `scripts/test_export.py` | `POST /api/bundles/export` -> `open('test.zip', 'wb')` | — | DX | 0.5h |
| 1 | Definir Request Models | `src/api/routes/bundles.py` | `BundleExportRequest` | `src/services/bundle_schemas.py` | CODE | 0.5h |
| 2 | Implementar Export Endpoint | `src/api/routes/bundles.py` | `@router.post("/export")` | `import_bundle` (reverso) | BACKEND | 1.5h |
| 3 | Validar E2E (Export -> Import) | — | — | — | FULLSTACK | 1h |

**Total:** 3.5h
