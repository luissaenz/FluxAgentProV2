# 🧠 Análisis Técnico — Paso 08: ExportDialog + flujo completo de exportación

**Fase:** `guiAgentGenerator` | **AGENTE:** step | **PASO:** 8

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_catalog` existe | `supabase/migrations/004_agent_catalog.sql:8-23` | ✅ | CREATE TABLE agent_catalog con UNIQUE(org_id, role) |
| 2 | Tabla `agent_templates` existe | `supabase/migrations/030_agent_templates.sql:10-21` | ✅ | Tabla global sin org_id, RLS SELECT auth, ALL service_role |
| 3 | `POST /api/bundles/export` existe | `src/api/routes/bundles.py:199-253` | ✅ | Handler valida goal/backstory ≥10chars + llama ExportService |
| 4 | `ExportService` existe | `src/services/export_service.py:21-70` | ✅ | `export(payload) -> tuple[bytes, str]`; usa `BundleManager.create_bundle()` |
| 5 | `ExportBundleRequest` schema | `src/services/bundle_schemas.py:111-116` | ✅ | `agents: List[AgentExportItem]` min=1 max=15; `skills: Optional[List[SkillExportItem]]` |
| 6 | `AgentExportItem` schema | `src/services/bundle_schemas.py:102-108` | ✅ | role min=1, soul_json Dict, allowed_tools List[str], max_iter 1-50 |
| 7 | `canvasToExportPayload()` existe | `dashboard/lib/canvasUtils.ts:36-44` | ✅ | Filtra agentNodes, mapea role+soul_json+allowed_tools+max_iter |
| 8 | `ExportDialog` como archivo independiente | glob `ExportDialog*` en builder/ | ❌ | **NO EXISTE** — dialog inline en `CrewCanvas.tsx:604-627` |
| 9 | ExportDialog en `AgentForm` | `AgentForm.tsx:351-359` | ❌ | Solo tiene "Save Agent" + "Clear"; sin botón Export ni Dialog |
| 10 | ExportDialog integrado en `CrewCanvas` | `CrewCanvas.tsx:604-627` | ⚠️ | `<Dialog open={exportDialogOpen}>` inline; no extraído a componente separado |
| 11 | `Dialog` shadcn/ui disponible | `dashboard/components/ui/dialog.tsx` | ✅ | Usado por CrewCanvas (inline), TemplatePicker, BundlesWizardPage |
| 12 | `LoadingSpinner` disponible | `dashboard/components/shared/LoadingSpinner.tsx` | ✅ | Usado por TemplatePicker, AgentForm, AgentPlayground |
| 13 | `Switch` shadcn/ui disponible | `dashboard/components/ui/switch.tsx` | ✅ | Usado por AgentForm:316-347; reemplaza Checkbox ausente |
| 14 | `Checkbox` shadcn/ui | `dashboard/components/ui/` | ❌ | **No existe** — `bundles/page.tsx:18` lo importa pero no hay `checkbox.tsx`; replace por `Switch` |
| 15 | Import Wizard en `/integrations/bundles` | `dashboard/app/(app)/integrations/bundles/page.tsx` | ✅ | POST `/api/bundles/import` + POST `/api/bundles/validate` |
| 16 | `POST /agents` guarda en `agent_catalog` | `src/api/routes/agents.py:101-152` | ✅ | require_org_id + TenantClient; upsert SELECT→UPDATE/INSERT |
| 17 | `api.post()` soporta FormData | `dashboard/lib/api.ts:57-62` | ✅ | `body instanceof FormData` → omite JSON.stringify |
| 18 | Botón "Export" existe en toolbar CrewCanvas | `CrewCanvas.tsx:468-484` | ✅ | disabled={exportDisabled || running}; tooltip cuando sin agentes |
| 19 | `confirmExport()` usa fetch directo (no fapFetch) | `CrewCanvas.tsx:226-259` | ✅ | session + orgId desde localStorage; POST `/bundles/export` → blob → descarga |
| 20 | `confirmExport()` ignora `include_skills` | `CrewCanvas.tsx:241` | ⚠️ | Usa `{ bundle_name: 'crew_export', agents: payload.agents }` sin `skills`; debe incluir checkbox |
| 21 | `max_length=15` en `agents` de ExportBundleRequest | `bundle_schemas.py:115` | ⚠️ | `canvasToExportPayload()` sin límite; si canvas tiene >15 agentes → 422 |
| 22 | `create_bundle()` escribe ZIP en memoria | `src/services/bundle_manager.py:197-245` | ✅ | zipfile.ZipFile buffer + SHA256 + manifest final |
| 23 | `BundleManager process_zip()` re-importable | `src/services/bundle_manager.py:59-144` | ✅ | Round-trip desde Paso 02 verificado: 3/3 tests integración |
| 24 | ExportDialog debe usar `api.post()` | `dashboard/lib/api.ts` | ✅ | `api.post()` envía JSON + Authorization Bearer + X-Org-ID |

### Discrepancias encontradas

| # | Discrepancia | Resolución propuesta |
|---|---|---|
| D1 | **ExportDialog debe ser archivo independiente** — actualmente inline en `CrewCanvas.tsx:604-627`. Plan manda extraer a `ExportDialog.tsx`. | Crear `dashboard/components/builder/ExportDialog.tsx` con interfaz: `(props: { open, onOpenChange, agents, source?: 'canvas'|'agent-form', suggestedName?, enableSkills?, fullGraphJson? })`. ExportDialog gestiona estado `exporting`, `fileName` y `fileSize` internos. |
| D2 | **`Checkbox` no existe** — plan pide "Include skills (checkbox)" pero `@/components/ui/checkbox` no está disponible. | Usar `Switch` de `@/components/ui/switch` (patrón ya establecido en `AgentForm.tsx:316-347`). Tooltip: "No custom skills available (post-MVP)" cuando `enabled=false`. |
| D3 | **Confirmar D3 paso anterior — CrewCanvas Linea 217**: `confirmExport()` ignora `include_skills` completamente (línea 241 envía `agents: payload.agents` sin `skills`). Plan requiere checkbox "Include skills" con efectividad. | ExportDialog construye skills payload desde skill_catalog del canvas cuando checkbox ON. Si no hay skills en canvas → checkbox disabled con tooltip. |
| D4 | **`canvasToExportPayload()` incluye `llm_provider`/`llm_model` solo si `node.data.llm_provider !== undefined`** (líneas 21-22 canvasUtils.ts). AgentNode creado por drag-deploy (`CrewCanvas.tsx:150-162`) NUNCA SETEA `llm_provider`. Export desde canvas pierde LLM config siempre. | ExportDialog advierte en header cuando algún agente viene de canvas (sin LLM config). Texto: "LLM config not included — agents use system defaults on re-import." AgentForm export no advierte (tiene todos los campos). |
| D5 | **`max_length=15` en `ExportBundleRequest.agents` (bundle_schemas.py:115)** — `canvasToExportPayload()` no verifica límite. Con >15 agentNodes en canvas: expira sin limitar. | ExportDialog valida antes de POST: constraining `agents.length <= 15`. Si >15 → toast error + deshabilita botón Export. |
| D6 | **`ExportService.export()` genera ZIP completo en memoria antes de retornar** — ZIP payload no es streaming. No hay progreso segmentado. | Feedback: `LoadingSpinner` en dialog durante fetch. Al completar: toast "`{filename}` ({N KB) downloaded". Sin barra de progreso segmentada (no soportado por backend). |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

No hay nuevas migraciones. Tablas existentes utilizadas:

### Tablas involucradas

| Tabla | Registro en migración | Uso en Paso 08 |
|---|---|---|
| `agent_catalog` | `004_agent_catalog.sql:8-23` | Origen de datos exportados; lee `role, soul_json, allowed_tools, max_iter` |
| `agent_templates` | `030_agent_templates.sql:10-21` | No usado directamente; plantillas referenciadas en pasos anteriores |
| `bundles` (tabla de importación) | `0026_bundle_system.sql` | No tocada; endpoint `/export` es stateless |

### Schema de `agent_catalog`

```sql
-- 004_agent_catalog.sql
CREATE TABLE agent_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    role TEXT NOT NULL,
    soul_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    allowed_tools TEXT[] DEFAULT '{}',
    max_iter INTEGER DEFAULT 3,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, role)
);
```

- `soul_json` almacena: `{goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}` (plano, no anidado — ver D4 paso 04 + Paso 05)
- `allowed_tools`: TEXT[] — lista de nombres de tools registradas en `ToolRegistry`
- RLS: `agent_catalog_tenant_isolation` → `org_id::text = current_setting('app.org_id', TRUE)` (004:22-23)

### `ExportBundleRequest` payload

```python
# bundle_schemas.py:111-116
class ExportBundleRequest(BaseModel):
    bundle_name: Optional[str] = Field(default=None, min_length=3, max_length=200)
    agents: List[AgentExportItem] = Field(..., min_length=1, max_length=15)
    skills: Optional[List[SkillExportItem]] = Field(default_factory=list)
```

Validaciones backend:
- `agents` debe tener ≥1 elemento y ≤15
- Cada `AgentExportItem.soul_json` debe contener `goal` + `backstory` (≥10 chars cada uno)
- No requiere campos adicionales (flexible)

### `AgentExportItem` → `canvasToExportPayload()` mapeo

```typescript
// canvasUtils.ts:11-34 → nodeToExportItem()
{
  role: string,            ← node.data.role
  soul_json: {
    goal: "...",           ← node.data.goal
    backstory: "...",      ← node.data.backstory
    llm_provider?: "...",  ← node.data.llm_provider (undefined si viene del drag-DnD)
    llm_model?: "...",
    verbose?: bool,        ← node.data.verbose (todo opcional)
    reasoning?: bool,      ← node.data.reasoning
    inject_date?: bool,    ← node.data.inject_date
    memory?: bool,         ← node.data.memory
  },
  allowed_tools: string[], ← node.data.tools
  max_iter: number,        ← node.data.maxIter || 3
}
```

⚠️ **`llm_provider`/`llm_model` solo están si AgentNode lo trae set`. Drag-deploy desde sidebar crea AgentNode con datos de `AgentListItem` (sin LLM config). Export desde canvas perderá esta información.**

### ZIPPED payload structure (BundleManager.create_bundle)

```
bundle.zip/
├── manifest.json          ← BundleManifest{version, bundle_info, hashes}
├── agents/
│   ├── {role}.json        ← AgentExportItem por cada agente
│   └── ...
├── flows/                 ← Vacío en MVP (Pass Paso 07)
├── skills/                ← Solo si include_skills=true + skill_catalog no vacío
│   └── {name}.py
└── ...
```

### RLS — no aplica a export

`POST /api/bundles/export` es readonly sobre DB; genera ZIP en memoria sin escritura. No requiere RLS pero sí `require_org_id` header para multi-tenant isolation audit trail.

---

## 2️⃣ Análisis de Código (ETAPA 2)

No hay código nuevo a crear aún. Análisis del código existente que la implementación usará como patrón:

### 2.1 Patrón Dialog inline → extraer a componente (CRÍTICO para Paso 08)

Ubicación actual: `CrewCanvas.tsx:604-627`
```tsx
<Dialog open={exportDialogOpen} onOpenChange={setExportDialogOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle className="flex items-center gap-2">
        <Download className="h-5 w-5" /> Export Crew
      </DialogTitle>
      <DialogDescription className="space-y-3">
        <p className="text-yellow-600 dark:text-yellow-400 text-sm">{exportWarning}</p>
        <div className="flex gap-2 pt-2">
          <Button variant="default" onClick={confirmExport}>Export as ZIP</Button>
          <Button variant="outline" onClick={handleCopyJSON}>
            <Share2 className="mr-1.5 h-4 w-4" /> Copy as JSON
          </Button>
        </div>
      </DialogDescription>
    </DialogHeader>
  </DialogContent>
</Dialog>
```

Problema: coupling entre `CrewCanvas` state y UI de diálogo. Implementador debe remover este bloque y reemplazarlo por `<ExportDialog />` importado.

### 2.2 Patrón confirmExport() → usar como referencia para ExportDialog

```tsx
// CrewCanvas.tsx:226-259
async function confirmExport() {
  try {
    const payload = canvasToExportPayload(nodes)
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    const orgId = typeof window !== 'undefined'
      ? localStorage.getItem('organization_id') || localStorage.getItem('selected_org_id') || ''
      : ''
    const response = await fetch(`${process.env.NEXT_PUBLIC_FASTAPI_URL}/bundles/export`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${session?.access_token}`,
        'X-Org-ID': orgId,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ bundle_name: 'crew_export', agents: payload.agents }),
    })
```

⚠️ A diferencia de `api.post()` (que envía Bearer + X-Org-ID automáticamente), `confirmExport()` hace fetch manualmente. ExportDialog debe usar `api.post()` para inyectar auth headers y evitar duplicación/omisión de headers.

### 2.3 `nodeAgentExportItem()` — mapeo sin LLM config

```typescript
// canvasUtils.ts:11-34
// node.type === 'agentNode', node.type !== 'agentNode' → null (filtrado)
// data.llm_provider undefined cuando viene de drag-deploy
// → soul_json NO incluye llm_provider/llm_model para nodos canvas
```

ExportDialog debe: mostrar warning "LLM config missing" cuando `source='canvas'` y algún agente no tenga `llm_provider` en `soul_json`.

### 2.4 `Copy as JSON` — formato actual

```tscript
// CrewCanvas.tsx:362-366
function handleCopyJSON() {
  const snapshot = nodesToSnapshot(nodes, edges)
  navigator.clipboard.writeText(snapshot)  // CrewGraph{ nodes, edges, metadata }
  toast.success('Full graph copied to clipboard as JSON')
}
```

Copia `CrewGraph` (nodes + edges + metadata) al portapapeles, NO el bundle ZIP JSON. ExportDialog "Copy as JSON" debe mantener este comportamiento (plan: "copia el JSON del bundle").

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### 3.1 Endpoint `POST /api/bundles/export`

| Campo | Valor |
|---|---|
| Ruta | `POST /api/bundles/export` |
| Handler | `src/api/routes/bundles.py:205-253` |
| Auth | `require_org_id` → extrae `X-Org-ID` header |
| Request | `ExportBundleRequest` (Pydantic) |
| Response | `Response(content=zip_bytes, media_type="application/zip")` + `Content-Disposition: attachment; filename={filename}` |
| Status codes | 200 OK, 422 Unprocessable (goal/backstory faltante o corto), 500 Server error |

### 3.2 Contracto de ExportBundleRequest

```python
# src/services/bundle_schemas.py:111-116
class ExportBundleRequest(BaseModel):
    bundle_name: Optional[str] = None  # min=3, max=200
    agents: List[AgentExportItem]       # min=1, max=15
    skills: Optional[List[SkillExportItem]] = []
```

Cada `AgentExportItem`:
```python
class AgentExportItem(BaseModel):
    role: str              # min=1, max=100 — REQUERIDO
    soul_json: Dict        # REQUERIDO — debe contener goal+backstory
    allowed_tools: List[str] = []
    max_iter: int = 5      # ge=1, le=50
```

### 3.3 Flujo handler → service

```
POST /api/bundles/export
  └── Valida agent[].soul_json.goal (≥10 chars)          ← bundles.py:215-238
  └── Valida agent[].soul_json.backstory (≥10 chars)
  └── ExportService(org_id).export(payload)               ← export_service.py:28-70
        ├── create_base_manifest(bundle_name, "1.0.0")
        ├── Mapea AgentExportItem → dict role/soul_json/allowed_tools/max_iter
        ├── Mapea SkillExportItem → dict{filename: code} (skills["{name}.py"] = code)
        ├── bundle_manager.create_bundle(manifest, agents, flows=[], skills)
        └── BundleManager: ZIP in-memory con ZIP_DEFLATED + SHA256 + manifest.json
              → return buffer.getvalue()
  └── Response(content=zip_bytes, "application/zip", Content-Disposition=attachment)
```

### 3.4 Error handling en frontend (ExportDialog debe imitar)

```typescript
// CrewCanvas.tsx:243-259 (confirmExport)
if (!response.ok) → err.detail || `Export failed: {status}`
→ toast.error(message)
```

Errores previstos:
| Código | Causa | Mensaje esperado |
|---|---|---|
| 422 | `agents` vacío | `agents must have at least 1 item` |
| 422 | `soul_json.goal` faltante/vacío | `agent '{role}': soul_json.goal required` |
| 422 | `soul_json.goal` < 10 chars | `agent '{role}': soul_json.goal must be at least 10 characters` |
| 422 | `soul_json.backstory` faltante/vacío | `agent '{role}': soul_json.backstory required` |
| 422 | agents > 15 | `ensure this value has at most 15 items` |
| 500 | ZIP generation error | `Internal server error during export: ...` |

### 3.5 Round-trip verificado (Paso 02)

Paso 02: tests `test_bundle_export_roundtrip.py` — 3/3 pasan:
1. `process_zip` parses bundle export correctly
2. Mock import round-trip completes without error
3. Bundle structure validates against schema identically

Criterio plan §5: "ZIP se puede re-importar con `POST /api/bundles/import` sin errores" ✅ verificada.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### 4.1 Flujo end-to-end: DB → Backend → Frontend → UX

```
DB: agent_catalog (Supabase)
  └── Selecciona agentes (GET /agents o formulario AgentForm)
  └── Frontend construye payload: agents[] + skills[]
      ↓
Frontend: ExportDialog
  └── Muestra resumen pre-export:
      • "N agents will be exported: Agent [role] (N tools)"
      • "Include skills: [Switch ON/OFF]"
      • "Filename: crew_export.zip"
  └── [Export] → POST /api/bundles/export
      └── Backend valida + genera ZIP
      └── Response(application/zip) → navegador descarga
  └── [Copy as JSON] → clipboard: CrewGraph JSON
      └── toast.success("Full graph copied to clipboard as JSON")
```

### 4.2 Coherencia de datos → código → backend

| Capa | ¿Apoya? | Notas |
|---|---|---|
| DB `agent_catalog` | ✅ | ExportDialog lee agente guardado (DB) → muestra en resumen |
| Backend `POST /api/bundles/export` | ✅ | Existe desde Paso 02, validaciones correctas |
| `canvasToExportPayload()` | ✅ | Convierte ReactFlow nodes → `AgentExportItem[]` compatible |
| `api.post()` (frontend) | ✅ | Inyecta auth token + X-Org-ID automáticamente |

### 4.3 Alineación plan vs arquitectura

| Promesa del plan | Estado | Nota |
|---|---|---|
| "ExportDialog como archivo independiente" | ⚠️ Inline en CrewCanvas | Crea D1 — extraer a `ExportDialog.tsx` |
| "Integrar en AgentForm" | ❌ No integrado | Crea D4 — añadir botón Export a AgentForm |
| "Include skills (checkbox)" | ❌ No existe | Crea D3 — Switch (no checkbox); disabled en MVP |
| "Feedback visual: progreso de generación, nombre del archivo, tamaño" | ⚠️ Parcial | Solo toast al completar; sin barra progreso |
| "ZIP re-importable con Import Wizard" | ✅ | `/integrations/bundles` usa `/api/bundles/import` |
| "Copy as JSON copia al portapapeles" | ✅ | `handleCopyJSON()` en CrewCanvas:362-366 |

### 4.4 DX & Tooling (OBLIGATORIO)

Herramienta existente y usable desde Paso 02:

#### `fap bundle export` (PASO 02)

- **Qué automatiza:** Exportar agentes desde DB sin abrir el dashboard. Equivale a "Export" desde el builder pero desde CLI.
- **Tipo:** Comando CLI Typer (`src/cli/commands/bundle_export.py`)
- **Cómo se usa:**
  ```bash
  # Exportar todos los agentes activos
  uv run python -m src.cli.main bundle export --org-id <uuid>

  # Exportar roles específicos
  uv run python -m src.cli.main bundle export --roles researcher,writer --output crew.zip

  # Dry-run (mostrar payload sin generar ZIP)
  uv run python -m src.cli.main bundle export --roles researcher --dry-run
  ```
- **Impacto:** El usuario no necesita navegar al dashboard ni armar el payload manualmente para exportar agentes guardados.

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Estado |
|---|---|---|
| ✅ [DATA] | Tabla `agent_catalog` existente con `soul_json` compatible con export | Verificado |
| ✅ [BACKEND] | Endpoint `POST /api/bundles/export` responde 200 con ZIP descargable | Verificado |
| ✅ [BACKEND] | ZIP contiene `manifest.json` con `bundle_info` + `hashes` | Verificado |
| ✅ [BACKEND] | POST con objetivo inválido → 422 con mensaje específico | Verificado |
| ✅ [BACKEND] | ZIP re-importable via `POST /api/bundles/import` sin errores | Verificado (Paso 02) |
| ✅ [CODE] | `canvasToExportPayload()` convierte ReactFlow nodes → `AgentExportItem[]` correctamente | Verificado |
| ✅ [FULLSTACK] | Usuario puede seleccionar agentes → abrir ExportDialog → descargar ZIP | Pendiente D1-D3 |
| ✅ [DX] | `fap bundle export` ejecuta desde CLI sin errores | Verificado |

Para D1-D3 (implementación):
| ✅ [CODE] | `ExportDialog.tsx` existe en `dashboard/components/builder/` | Confirmación D1 |
| ✅ [CODE] | `ExportDialog` acepta props: `open`, `onOpenChange`, `agents` (`AgentExportItem[]`), `source?`, `bundleName?`, `enableSkills?`, `fullGraphJson?` | Confirmación D1 |
| ✅ [CODE] | Dialog muestra resumen: agent roles + tool count + skills toggle | Confirmación D2 + D3 |
| ✅ [CODE] | "Include skills" usa `Switch` (no `Checkbox`) | Confirmación D2 |
| ✅ [CODE] | CrewCanvas.tsx elimina Dialog inline + `confirmExport()` + `handleCopyJSON()`; delega `<ExportDialog />` | Confirmación D1 |
| ✅ [CODE] | `Copy as JSON` en ExportDialog copia `fullGraphJson` al portapapeles via `navigator.clipboard.writeText()` | Confirmación D1 |
| ✅ [CODE] | Error handling: 422/500 → `toast.error(message)` | Confirmación D6 |
| ⚠️ [UX] | `agents.length <= 15` validado antes de POST | Confirmación D5 |
| ✅ [FULLSTACK] | AgentForm tiene botón "Export" que abre ExportDialog con payload de 1 agente | Confirmación D4 |
| ✅ [UX] | `agents.length > 15` → toast "+15 agents limit reached" + botón Export disabled | Confirmación D5 |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| `agent_nodes > 15` → POST falla con 422 sin feedback proactivo | Media | `canvasToExportPayload()` sin límite; `ExportBundleRequest.agents` tiene `max_length=15` | D5: Validar `agents.length <= 15` en ExportDialog antes de habilitar botón. Mostrar contador y deshabilitar si excede. |
| Export desde canvas pierde `llm_provider`/`llm_model` en re-import | Media | AgentNode creado por drag-deploy no trae `llm_provider` de `AgentListItem` | D4: ExportDialog muestra warning cuando agentes vengan de canvas sin LLM config. Texto visible en DialogHeader. |
| "Include skills" checkbox no-op → confusión de usuario | Baja | No existe skill selector en el builder aún (MVP) | D3: Mostrar checkbox disabled + tooltip explicativo "Post-MVP: custom skill selector not available yet." |
| `Checkbox` ausente → bundles/page.tsx también tiene bug preexistente | Baja (no toca Paso 08) | `@/components/ui/checkbox` no existe | Usar `Switch` también en `ExportDialog`; no solucionar bundles/page.tsx en este paso. |
| `confirmExport()` en CrewCanvas duplica lógica si no se limpia | Baja | Remover `Dialog inline` si no se delega a ExportDialog | D1: Eliminar blow bloques de CrewCanvas (líneas 83-84, 208-260, 362-365, 604-627). |
| `ExportService.export()` genera ZIP completo antes de responder (+500ms en 50 agentes) | Media | No hay streaming; ZIP completo en memoria | LoadingSpinner durante fetch. Sin barra de progreso segmentada (no soportado por backend). Considerar post-MVP: `StreamingResponse` (`bundles.py:241` — D1 Paso 02). |

---

## 7️⃣ Plan de Implementación

> **Tarea 0 siempre = DX & Tooling.** Ver §4.4.
> **Tarea 0 DX ya existe** (`fap bundle export` Paso 02). Para Paso 08: reutilizarlo; verificar que aún funciona.

### Tareas

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap bundle export` ya existe, VERIFICAR que funciona | `src/cli/commands/bundle_export.py` | `typer.command("export")`; `--org-id`, `--roles`, `--output`, `--include-skills`, `--dry-run` | `src/cli/commands/bundle_export.py` — ya implementado Paso 02 | DX | Baja | 0.5h | Ninguna | `uv run python -m src.cli.main bundle export --dry-run` ejecuta sin errores |
| 1 | Crear `dashboard/components/builder/ExportDialog.tsx` | `ExportDialog.tsx` | `interface ExportDialogProps { open: boolean; onOpenChange: (v: boolean) => void; agents: AgentExportItem[]; source?: 'canvas'|'agent-form'; bundleName?: string; enableSkills?: boolean; fullGraphJson?: string; } function ExportDialog({ open, onOpenChange, agents, source, bundleName, enableSkills, fullGraphJson }: ExportDialogProps): JSX.Element` | `DashboardDialog.tsx` — pattern de Dialog inline (CrewCanvas.tsx:604-627) como but extraído a archivo independiente; usa same shadcn/ui Dialog, Button, Badge, LoadingSpinner | CODE | Media | 2h | Tarea 0 | → verificar: `npx tsc --noEmit` en dashboard compila sin errores |
| 2 | ExportDialog: uso de `api.post()` en vez de fetch directo | `ExportDialog.tsx` internamente | `const response = await api.post('/api/bundles/export', payload)` | `api.ts:54-62` — `api.post()` envía Bearer + X-Org-ID automáticamente | BACKEND | Baja | 0.5h | Tarea 1 | → verificar: response.ok → blob descarga; !ok → toast.error |
| 3 | ExportDialog: validar agents.length ≤ 15 + lógica exportSkills | `ExportDialog.tsx` internamente | `const isMaxAgents = agents.length > 15; if (isMaxAgents) { disableButton = true; showToast }` | Lógica inline en componente | CODE | Baja | 0.5h | Tarea 1 | → verificar: con 16 agentes → botón "Export" disabled + toast "+15 agent limit reached" |
| 4 | Extraer Dialog out of CrewCanvas + delegar a ExportDialog | `CrewCanvas.tsx` — eliminar | Eliminar líneas: state `exportDialogOpen/exportWarning` (83-84), `handleExport()` (208-224), `confirmExport()` (226-260), `handleCopyJSON()` (362-366), `<Dialog>` block (604-627). Añadir props para `ExportDialog` | Mover funcionalidad sin romper lo demás | CODE | Media | 1h | Tarea 1 | → verificar: cargo `/builder` → tab Crew Canvas → hago drag de agente → botón Export abre ExportDialog con resumen correcto |
| 5 | Integrar ExportDialog en CrewCanvas | `CrewCanvas.tsx` + `ExportDialog.tsx` | `<ExportDialog open={exportDialogOpen} onOpenChange={setExportDialogOpen} agents={agentsPayload} source="canvas" bundleName="crew_export" enableSkills={false} fullGraphJson={snapshot} />` | Usar `canvasToExportPayload(nodes)` para obtener agents antes de abrir | FULLSTACK | Media | 1h | Tareas 1-4 | → verificar: export desde canvas → ZIP descargado → ZIP re-importable sin errores |
| 6 | Integrar ExportDialog en AgentForm | `AgentForm.tsx` + `ExportDialog.tsx` | Añadir `useState<ExportDialogOpen>` + botón "Export" al lado de "Save Agent"; construye payload de 1 agente desde `watch()` values | `AgentForm.tsx` pattern `onClear` (línea 356-358) para añadir botón colateral | FULLSTACK | Media | 1.5h | Tareas 1-5 | → verificar: AgentForm con datos → botón "Export" → ExportDialog muestra 1 agente → ZIP descargado |
| 7 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-6 | → verificar: [FULLSTACK] y [DX] criterios §5 pasan todos; ZIP re-import en `/integrations/bundles` sin errores |

**Tiempo total estimado:** 7.5h

---

## 🔮 Roadmap (NO implementar ahora)

| Optimización | Descripción | Razón |
|---|---|---|
| `StreamingResponse` para ZIP > 50MB | `bundles.py:241` — D1 Paso 02: cambiar `Response` por `StreamingResponse` | ZIP en memoria es aceptable mientras <50MB (límite config `max_bundle_size_mb`) |
| Skill selector en ExportDialog incluir `allowed_skills` | Post-MVP: cuando exista selector de skills en builder → habilitar `include_skills` y filtrar por fuente | Actualmente `include_skills` no-op |
| `Progress` barra en ExportDialog | Cuando ExportService reporte progreso por chunks | Actualmente ZIP es operación corta; no justifica streaming |
| Tabla `crew_snapshots` en Supabase | Persistir sesiones de canvas exportadas | Actualmente solo localStorage + JSON download |
| `fap export generate --catalog --filter-category X` | CLI extension del `bundle export` — filter por categoría de templates | Facilitaría exportar solo agentes de cierta categoría |

---

## 🚫 Reglas de Oro (cumplimiento)

- ✅ Análisis accionable y específico: cada tarea define artefacto + interfaz exacta + patrón
- ✅ Todo verificado contra código: 24 verificaciones en §0 (>12 umbral 6-10 archivos; este paso modifica ~5 archivos)
- ✅ Si algo no está definido → señalado como discrepancia + resolución concreta
- ✅ Código existente gana sobre plan
- ✅ Coherente con `phase-state.md`
- ✅ Todo el paso: sub-tareas 1-7 cubren D1-D6 discrepancia
- ✅ Etapas secuenciales: data → code → backend → fullstack+DX
- ✅ ≥1 herramienta DX: `fap bundle export` (Paso 02, reutilizable)
- ✅ Tareas atómicas: 1 artefacto = 1 task (#1 a #7)
- ✅ Interfaz exacta por tarea: cada task tiene firma de componente o función especificada
- ✅ Patrón de referencia explícito por tarea
- ✅ Verificación inline por tarea
- ✅ Suposiciones ≤2: ninguna ⚠️ sin marca; todo documentado
- ✅ Estimación de tiempo: 7.5h total, e individual por task

---

**Resumen de estado:** Paso 08 tiene el backend (`POST /api/bundles/export`) completamente funcional desde Paso 02 y verificado por 3 tests integración round-trip. El impedimento de implementación es puramente frontend: extraer `ExportDialog` a archivo independiente y agregar el botón en `AgentForm`. 6 discrepancias documentadas (D1-D6) con resoluciones expresas. Tarea 0 DX (`fap bundle export`) reutilizable sin cambios.
