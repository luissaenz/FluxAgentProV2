# Análisis Técnico — Paso 08: ExportDialog + flujo completo de exportación

> **Agente:** glm5.1  
> **Fecha:** 2026-05-15  
> **Paso:** 08 — ExportDialog + flujo completo de exportación

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|----------|-------------|--------|-----------|
| 1 | `ExportBundleRequest` existe | `bundle_schemas.py:111-116` | ✅ VERIFICADO | Campos: `bundle_name`, `agents: List[AgentExportItem]`, `skills: Optional[List[SkillExportItem]]` |
| 2 | `AgentExportItem` existe | `bundle_schemas.py:102-108` | ✅ VERIFICADO | Campos: `role`, `soul_json: Dict`, `allowed_tools: List[str]`, `max_iter: int` |
| 3 | `SkillExportItem` existe | `bundle_schemas.py:95-99` | ✅ VERIFICADO | Campos: `name`, `code: str` |
| 4 | `POST /api/bundles/export` existe | `bundles.py:199-253` | ✅ VERIFICADO | Retorna `Response` con ZIP, valida goal/backstory ≥10 chars |
| 5 | `ExportService.export()` existe | `export_service.py:28-70` | ✅ VERIFICADO | Retorna `tuple[bytes, str]`, usa `BundleManager.create_bundle()` |
| 6 | `BundleManager.create_bundle()` existe | `bundle_manager.py:197-245` | ✅ VERIFICADO | Recibe manifest, agents, flows, skills → genera ZIP en memoria |
| 7 | Export logic ya en `CrewCanvas.tsx` | `CrewCanvas.tsx:208-260` | ❌ DISCREPANCIA | Plan dice "crear ExportDialog.tsx" pero ya existe lógica inline en CrewCanvas. Refactorizar, no crear desde cero. |
| 8 | `api.ts` no soporta descarga binaria | `api.ts:51` | ⚠️ NO VERIFICABLE para ZIP | `fapFetch` siempre llama `response.json()`. Export ZIP requiere `response.blob()`. CrewCanvas ya usa `fetch()` raw (linea 234). |
| 9 | Componente `Checkbox` UI no existe | `dashboard/components/ui/` | ❌ DISCREPANCIA | `bundles/page.tsx:18` importa `@/components/ui/checkbox` pero el archivo NO existe. Construcción rota preexistente. |
| 10 | `canvasToExportPayload()` filtra solo agents | `canvasUtils.ts:36-44` | ✅ VERIFICADO | `node.type === 'agentNode'` — tasks/edges excluidos (limitación bundle-schema-v2) |
| 11 | `navigator.clipboard.writeText()` usado | `CrewCanvas.tsx:364` | ✅ VERIFICADO | Ya implementado para "Copy as JSON". Patrón reusable. |
| 12 | `skill_catalog` tabla existe en DB | CLI `fap bundle export --include-skills` | ✅ VERIFICADO | Consulta `svc.table("skill_catalog")` con `org_id` + `is_active`. No hay endpoint frontend para listar skills. |
| 13 | Import Wizard existe en `/integrations/bundles` | `bundles/page.tsx` | ✅ VERIFICADO | `api.post('/api/bundles/import', formData)` + `api.post('/api/bundles/validate', formData)` |
| 14 | `JSZip` disponible como dependencia | `package.json` | ✅ VERIFICADO | `"jszip": "^3.10.1"` instalado |
| 15 | Dialog component existe | `dashboard/components/ui/dialog.tsx` | ✅ VERIFICADO | Radix Dialog ya usado en CrewCanvas y TemplatePicker |
| 16 | ` Sheet` component existe | `dashboard/components/ui/sheet.tsx` | ✅ VERIFICADO | Usado en AgentPlayground |
| 17 | `AgentForm.onSave` prop | `AgentForm.tsx:47` | ✅ VERIFICADO | `onSave?: (data: AgentFormData) => Promise<void>` — permite customización desde padre |
| 18 | `useCurrentOrg` hook | `hooks/useCurrentOrg.ts` | ✅ VERIFICADO | Retorna `{ orgId }` — patrón para obtener org_id sin localStorage directo |
| 19 | `Auth` en bundles endpoint | `bundles.py:207` | ✅ VERIFICADO | `Depends(require_org_id)` — requiere header `X-Org-ID` |
| 20 | Supabase auth para token JWT | `api.ts:9-10` | ✅ VERIFICADO | `supabase.auth.getSession()` → `session.access_token` en header `Authorization` |
| 21 | `flows` excluido de export MVP | `export_service.py:65` | ✅ VERIFICADO | `flows=[]` hardcoded. Skills sí soportados. |
| 22 | `crew_export.zip` hardcoded en CrewCanvas | `CrewCanvas.tsx:241,251` | ❌ DISCREPANCIA | Filename hardcoded sin nombre custom. `ExportService` soporta `bundle_name` personalizable. |

**Discrepancias encontradas:**

1. **D1 — Export ya implementado inline en CrewCanvas**: `CrewCanvas.tsx:208-260` contiene `handleExport()`, `confirmExport()`, `handleCopyJSON()`, y un `<Dialog>` de export rudimentario (líneas 604-627). El plan dice "crear `ExportDialog.tsx`" — debe refactorizar esta lógica, no duplicarla. Resolución: extraer lógica de export a componente `ExportDialog.tsx` dedicado, consumir desde CrewCanvas y AgentForm.

2. **D2 — `api.ts` no soporta blob/binary**: `fapFetch()` siempre parsea `response.json()` (línea 51). ZIP download necesita `response.blob()`. CrewCanvas ya usa `fetch()` raw (línea 234). Resolución: crear función `api.download(path, body)` en `api.ts` que retorna `Response` sin parsear, o función helper `downloadBundle()` dedicada. No romper `fapFetch` existente.

3. **D3 — `Checkbox` UI component no existe**: `bundles/page.tsx:18` importa `Checkbox` desde `@/components/ui/checkbox` pero el archivo NO existe en `dashboard/components/ui/`. Build roto preexistente. Resolución: crear `dashboard/components/ui/checkbox.tsx` con shadcn/ui pattern (`@radix-ui/react-checkbox` instalado vía existing deps) antes de usar Checkbox en ExportDialog. Prioridad: Tarea 0 o pre-requisito bloqueante.

4. **D4 — Filename hardcoded `crew_export.zip`**: CrewCanvas línea 251 usa `crew_export.zip` sin personalización. `ExportBundleRequest.bundle_name` soporta nombres custom. Resolución: ExportDialog debe aceptar `bundleName` prop, pasar al payload, y usar `Content-Disposition` filename del response header.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Tablas tocadas

**Ninguna tabla nueva.** Este paso no crea migraciones. Operaciones sobre tablas existentes:

| Tabla | Operación | Detalle |
|-------|-----------|---------|
| `agent_catalog` | SELECT | Consulta agentes para generar payload de export. Ya existe `GET /agents` |
| `skill_catalog` | SELECT (opcional) | Si "Include skills" checkbox activado, consultar skills de la org |

### Schema de datos — Payload de export

```json
{
  "bundle_name": "my_crew_20260515",
  "agents": [
    {
      "role": "Code Reviewer",
      "soul_json": { "goal": "...", "backstory": "...", "llm_provider": "groq", ... },
      "allowed_tools": ["fetch_url"],
      "max_iter": 3
    }
  ],
  "skills": [
    { "name": "custom_tool", "code": "def run(args): ..." }
  ]
}
```

### RLS

- `agent_catalog`: RLS `tenant_isolation` via `X-Org-ID` + `require_org_id`. Frontend pasa org_id en header.
- `skill_catalog`: Misma RLS tenant_isolation. Consulta vía `TenantClient`.

### Índices

Sin cambios. Índices existentes bastan.

### Tipos de datos problemáticos

- `soul_json` es JSONB → se envía como `Dict` en payload, sin validación de estructura en frontend. Backend valida `goal` y `backstory` ≥10 chars.
- `skills` es `Optional[List[SkillExportItem]]` — default `None`, no `[]`. Si se envía `skills: []`, `ExportService` no incluye skills (correcto). Si se envía `skills: None`, tampoco los incluye.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes nuevos

#### `ExportDialog.tsx`
- **Función principal:** Diálogo modal que muestra resumen pre-export, opción "Include skills", botón "Export" (descarga ZIP), botón "Copy as JSON"
- **Props:**
  ```typescript
  interface ExportDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    agents: AgentExportItem[]        // lista de agentes a exportar
    defaultBundleName?: string       // nombre sugerido para el bundle
    mode: 'single' | 'crew'          // 'single' = AgentForm, 'crew' = CrewCanvas
  }
  ```
- **Estado local:**
  - `includeSkills: boolean` (checkbox)
  - `isExporting: boolean` (loading state)
  - `error: string | null`
  - `fileName: string` (editable bundle name)

### Componentes modificados

#### `CrewCanvas.tsx`
- **Eliminar:** lógica inline de export (`handleExport`, `confirmExport`, `handleCopyJSON`, `<Dialog>` export)  
- **Reemplazar con:** `<ExportDialog>` componente, pasando `agents` desde `canvasToExportPayload(nodes)` y `mode="crew"`
- **Eliminar:** `setExportDialogOpen`, `setExportWarning`, `exportWarning` state

#### `BuilderLayout.tsx` / `AgentForm.tsx`
- **Añadir:** Botón "Export" en AgentForm (junto a "Save Agent" y "Clear")
- **Integrar:** `<ExportDialog mode="single">` con datos del formulario actual

### Patrón de referencia — Dialog existente

`CrewCanvas.tsx:559-627` (export dialog actual) — reutilizar estructura `<Dialog>`, `<DialogContent>`, `<DialogHeader>`.

### Patrón de referencia — fetch para binary download

`CrewCanvas.tsx:226-260` (confirmExport actual) — usar `fetch()` raw con `response.blob()` + `URL.createObjectURL()`. NO usar `api.post()` (falla con JSON parse).

### Patrón de referencia — "Copy as JSON"

`CrewCanvas.tsx:362-365` (handleCopyJSON) — `navigator.clipboard.writeText(json)` + `toast.success()`.

### Patrón de referencia — checkbox

No existe componente `Checkbox` UI. `bundles/page.tsx:18` importa uno que no existe. **Bloqueante.** Crear con pattern shadcn/ui: `@radix-ui/react-checkbox` (ya instalado como dep de `@radix-ui/react-dropdown-menu`).

### Imports exactos requeridos

```typescript
// ExportDialog.tsx
import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { Download, Copy, FileArchive } from 'lucide-react'
import { toast } from 'sonner'
import type { AgentExportItem } from '@/lib/types'  // nuevo tipo
```

```typescript
// checkbox.tsx (shadcn/ui pattern)
import * as React from 'react'
import * as CheckboxPrimitive from '@radix-ui/react-checkbox'
import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
```

### Función auxiliar — `api.download()`

Necesaria para no repetir fetch raw en cada lugar que necesite binary download:

```typescript
// api.ts — añadir
export async function fapDownload(path: string, body: unknown): Promise<Response> {
  const { data: { session } } = await supabase.auth.getSession()
  const orgId = typeof window !== 'undefined'
    ? localStorage.getItem('organization_id') || localStorage.getItem('selected_org_id') || ''
    : ''

  if (!session?.access_token) throw new Error('Not authenticated')

  const response = await fetch(`${process.env.NEXT_PUBLIC_FASTAPI_URL}${path}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${session.access_token}`,
      'X-Org-ID': orgId,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `Export failed: ${response.status}`)
  }

  return response  // sin .json() — caller hace .blob() o .arrayBuffer()
}
```

### Tipos nuevos

```typescript
// types.ts — añadir
export interface ExportBundleRequest {
  bundle_name?: string
  agents: AgentExportItem[]
  skills?: SkillExportItem[]
}

export interface AgentExportItem {
  role: string
  soul_json: Record<string, unknown>
  allowed_tools: string[]
  max_iter: number
}

export interface SkillExportItem {
  name: string
  code: string
}
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoint existente — `POST /api/bundles/export`

| Propiedad | Valor |
|-----------|-------|
| Ruta | `/api/bundles/export` |
| Método | POST |
| Auth | `Depends(require_org_id)` |
| Content-Type | `application/json` |
| Response | `Response(content=zip_bytes, media_type="application/zip", headers={"Content-Disposition": "attachment; filename={name}.zip"})` |

**Payload request:**
```json
{
  "bundle_name": "my_export",       // Optional, min 3, max 200 chars
  "agents": [                        // Required, min 1, max 15
    {
      "role": "string",              // Required, min 1, max 100
      "soul_json": {                 // Required
        "goal": "...",               // Required, min 10 chars (validado en handler)
        "backstory": "..."           // Required, min 10 chars (validado en handler)
      },
      "allowed_tools": [],           // Default []
      "max_iter": 5                  // Default 5, ge 1, le 50
    }
  ],
  "skills": [                        // Optional
    { "name": "tool_name", "code": "..." }
  ]
}
```

**Response headers (éxito):**
```
Content-Type: application/zip
Content-Disposition: attachment; filename=my_export.zip
```

**Response body:** ZIP bytes

**Error responses:**
- `422`: Agente sin `soul_json.goal` o `soul_json.backstory`, o goal/backstory < 10 chars
- `422`: Payload vacío o malformed (Pydantic validation)
- `500`: Error interno en `ExportService`

### Middleware aplicable

- `require_org_id`: Extrae `X-Org-ID` del header. Obligatorio.

### Flujo de datos — Export

```
Frontend (ExportDialog.tsx)
  → Construye payload ExportBundleRequest
  → POST /api/bundles/export (con auth headers)
  → Recibe Response con ZIP bytes
  → Crea Blob, URL.createObjectURL, descarga automática
```

### Flujo de datos — Copy as JSON

```
Frontend (ExportDialog.tsx)
  → Construye objeto CrewGraph (agents + edges)
  → navigator.clipboard.writeText(JSON.stringify(...))
  → Toast "Copied to clipboard"
```

### Flujo de datos — Include Skills

```
Frontend (ExportDialog.tsx)
  → Si includeSkills=true, consulta skill_catalog via GET /api/skills (NO EXISTE)
  → o consulta directamente desde Supabase client (front-end directo)
  → Añade skills al payload
```

⚠️ **Discrepancia**: No existe endpoint `GET /api/skills` para listar skills de una org. El CLI usa `get_service_client()` (service_role) para consultar `skill_catalog`. El frontend no tiene acceso directo a esta tabla vía API.  
**Resolución MVP:** Opción A — crear endpoint `GET /api/skills/available` (consistente con `GET /api/tools/available`). Opción B — consultar skills vía Supabase client directo desde frontend (no requiere nuevo endpoint, usa RLS). Opción C — omitir "Include skills" en MVP, solo exportar agents (el endpoint acepta `skills: null`).  
**Recomendación:** Opción C para MVP. Checkbox "Include skills" visible pero deshabilitado con tooltip "Coming soon" hasta que Paso futuro cree el endpoint.

### Error handling — casos

| Error | Código | Causa | UX |
|-------|--------|-------|----|
| ZIP vacío / sin agentes | 422 | Payload sin agentes (`agents: []`) | Toast: "At least one agent required" |
| Agente sin role | 422 | `soul_json` sin goal/backstory | Toast: detalle del error del backend |
| Timeout del servidor | - | ExportService tarda >30s | Catch network error, toast genérico |
| ZIP generación fallida | 500 | Error en BundleManager | Toast: "Export failed. Try again." |
| Auth expirada | 401 | Token JWT expirado | Toast: "Session expired. Please log in again." |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo — Export ZIP

```
AgentForm/CrewCanvas
  → Usuario hace clic "Export"
  → ExportDialog abre con:
    - Resumen: N agentes, paneles con role + tools
    - Input editable: Bundle name (default: "crew_export_20260515")
    - Checkbox "Include skills" (disabled en MVP)
    - Botón "Export as ZIP" (primary)
    - Botón "Copy as JSON" (outline)
  → Usuario hace clic "Export as ZIP"
  → Loading state: "Generating ZIP..." + spinner
  → POST /api/bundles/export con payload
  → Response OK (200)
  → Crear Blob → URL.createObjectURL → trigger download
  → Toast: "Bundle exported successfully"
  → Cerrar diálogo

Si error:
  → Toast con detalle del error
  → Permanecer en diálogo para reintentar
```

### Flujo completo — Copy as JSON

```
ExportDialog
  → Usuario hace clic "Copy as JSON"
  → Construye CrewGraph JSON (agents + edges + metadata)
  → navigator.clipboard.writeText(JSON.stringify(graph))
  → Toast: "Bundle JSON copied to clipboard"
  → Botón cambia temporalmente a "Copied ✓"
```

### Flujo — Single Agent Export (desde AgentForm)

```
AgentForm
  → Usuario completa formulario
  → Clic "Export" (nuevo botón junto a Save Agent / Clear)
  → ExportDialog abre con mode="single"
  → Resumen muestra 1 agente con sus datos del formulario
  → Export ZIP con ese agente individual
```

### Flujo — Crew Export (desde CrewCanvas)

```
CrewCanvas
  → Usuario tiene agents en canvas
  → Clic "Export" (ya existe en toolbar)
  → ExportDialog abre con mode="crew"
  → Resumen muestra todos los agents del canvas
  → Warning: "Tasks and connections not included in ZIP (bundle-schema-v2 limitation)"
  → Export ZIP con agents del canvas
```

### Coherencia

- **Data → Código**: Los datos que `canvasToExportPayload()` genera coinciden con `AgentExportItem` del backend. ✅
- **Código → Backend**: El payload JSON coincide con `ExportBundleRequest` de Pydantic. ✅
- **Backend → UX**: El ZIP es descargable por el navegador vía `Content-Disposition`. ✅
- **Re-importación**: El ZIP generado es compatible con `POST /api/bundles/import` (BundleWizard en `/integrations/bundles`). ✅

### Gaps

1. **No hay endpoint para listar skills del frontend**: Checkbox "Include skills" no puede poblar datos sin `GET /api/skills/available`. MVP: disable con tooltip "Coming soon".
2. **`api.ts` no soporta download binario**: Cada lugar que hace export usa `fetch()` raw en vez de `api.post()`. Añadir `fapDownload()` a `api.ts`.
3. **`Checkbox` UI component faltante**: `@/components/ui/checkbox` no existe. Necesita crearse (shadcn/ui pattern).
4. **Resumen pre-export necesita datos enriquecidos**: AgentForm necesita exponer `AgentFormData` como `AgentExportItem`. Conversión necesaria.

### Herramienta DX Propuesta

```
### Herramienta Propuesta: fap bundle preview
- **Qué automatiza:** Previsualización del contenido del bundle exportado desde CLI sin generar ZIP
- **Tipo:** CLI command
- **Cómo se usa:** `fap bundle preview --org-id=UUID --roles=Code_Reviewer,Data_Analyst`
- **Impacto para el usuario final:** Valida qué agentes se incluirán antes de generar el ZIP. Evita export-and-reimport cycles.
- **Prioridad:** Media — útil pero no bloqueante para el paso
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] No se crean nuevas tablas/migraciones — solo lectura de agent_catalog y skill_catalog
✅ [CODE] ExportDialog.tsx creado con props open/onOpenChange/agents/mode/defaultBundleName
✅ [CODE] Checkbox UI component creado en @/components/ui/checkbox.tsx
✅ [CODE] fapDownload() helper añadido a api.ts para descarga binaria
✅ [CODE] AgentExportItem y SkillExportItem tipos añadidos a types.ts
✅ [CODE] ExportBundleRequest tipo añadido a types.ts
✅ [CODE] CrewCanvas refactorizado: lógica export inline eliminada, reemplazada por ExportDialog
✅ [CODE] AgentForm integrado con botón "Export" → ExportDialog mode="single"
✅ [BACKEND] POST /api/bundles/export funciona sin cambios (ya implementado en Paso 02)
✅ [BACKEND] Response headers incluyen Content-Disposition con filename correcto
✅ [FULLSTACK] Diálogo muestra resumen de agentes a exportar (role, tools count, model)
✅ [FULLSTACK] Botón "Export as ZIP" descarga ZIP válido con Content-Disposition filename
✅ [FULLSTACK] ZIP se puede re-importar con Import Wizard en /integrations/bundles
✅ [FULLSTACK] "Copy as JSON" copia JSON al portapapeles con toast de confirmación
✅ [FULLSTACK] Checkbox "Include skills" visible pero deshabilitado en MVP
✅ [FULLSTACK] Input editable para bundle name con default "export_YYYYMMDD_HHMMSS"
✅ [FULLSTACK] Loading state "Generating ZIP..." durante export
✅ [FULLSTACK] Error handling: agente sin goal/backstory, timeout, ZIP vacío
✅ [FULLSTACK] Warning en mode="crew": "Tasks and connections not included (bundle-schema-v2 limitation)"
✅ [DX] Herramienta fap bundle preview propuesta para validación previa (post-MVP)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| Checkbox UI no existe → build roto | Alta | `bundles/page.tsx` importa `Checkbox` inexistente | Crear `checkbox.tsx` con shadcn/ui pattern como Tarea 1 |
| api.ts no soporta binary → usar fetch raw | Media | `fapFetch` siempre `.json()` | Crear `fapDownload()` helper dedicado. No modificar `fapFetch` |
| Skills no accesibles desde frontend | Media | Sin `GET /api/skills/available` | MVP: disable checkbox con tooltip. Post-MVP: crear endpoint |
| ExportDialog duplica lógica existente | Media | CrewCanvas ya tiene export inline | Refactorizar: extraer a ExportDialog, CrewCanvas consume |
| AgentForm no expone datos como AgentExportItem | Media | AgentFormData ≠ AgentExportItem | Función conversora local en ExportDialog |
| Content-Disposition filename override | Baja | Backend genera filename, frontend puede querer otro | Usar header `Content-Disposition` del response. Parsear filename del header |
| navigator.clipboard falla en contexts insecure | Baja | Requiere HTTPS o localhost | Fallback: `document.execCommand('copy')`. Toast de error si falla |
| Export ZIP grande >50MB | Baja | `fapFetch` no tiene timeout custom | Backend ya limita `max_bundle_size_mb`. MVP: sin progreso de descarga |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|-------|-----------|-----------------|-----------------|-------|-------------|-------------|--------------|--------------|
| 0 | **DX & Tooling**: crear Checkbox UI component | `dashboard/components/ui/checkbox.tsx` | `export function Checkbox({ checked, onCheckedChange, disabled, className }: CheckboxProps)` | `dashboard/components/ui/switch.tsx` — Radix primitive + cva | CODE | Baja | 0.5h | Ninguna | → verificar: `import { Checkbox } from '@/components/ui/checkbox'` sin error TS |
| 1 | Añadir tipos `AgentExportItem`, `SkillExportItem`, `ExportBundleRequest` a `types.ts` | `dashboard/lib/types.ts` | Ver sección 2 — interfaces exactas | `dashboard/lib/types.ts:254-289` (CanvasAgentNode pattern) | DATA | Baja | 0.25h | Ninguna | → verificar: `npx tsc --noEmit` sin errores en types |
| 2 | Añadir `fapDownload()` a `api.ts` | `dashboard/lib/api.ts` | `export async function fapDownload(path: string, body: unknown): Promise<Response>` | `dashboard/lib/api.ts:5-52` (fapFetch pattern, retorna Response sin .json()) | BACKEND | Baja | 0.25h | Ninguna | → verificar: `fapDownload('/bundles/export', payload)` retorna Response con `.blob()` disponible |
| 3 | Crear componente `ExportDialog.tsx` | `dashboard/components/builder/ExportDialog.tsx` | `function ExportDialog({ open, onOpenChange, agents, defaultBundleName, mode }: ExportDialogProps)` | `dashboard/components/builder/TemplatePicker.tsx` — Dialog modal + loading + error states | CODE | Alta | 2h | Tareas 0-2 | → verificar: diálogo renderiza resumen de agents, botones Export/Copy, checkbox Include skills |
| 4 | ExportDialog: funcionalidad "Export as ZIP" | `dashboard/components/builder/ExportDialog.tsx` (añadir a Tarea 3) | `async function handleExport(): Promise<void>` — llama `fapDownload('/api/bundles/export', payload)` → `.blob()` → download | `CrewCanvas.tsx:226-260` (confirmExport pattern con fetch raw) | FULLSTACK | Media | 1h | Tareas 2-3 | → verificar: clic "Export as ZIP" descarga ZIP con Content-Disposition filename |
| 5 | ExportDialog: funcionalidad "Copy as JSON" | `dashboard/components/builder/ExportDialog.tsx` (añadir a Tarea 3) | `async function handleCopyJSON(): Promise<void>` — `navigator.clipboard.writeText(JSON.stringify(data))` | `CrewCanvas.tsx:362-365` (handleCopyJSON pattern) | FULLSTACK | Baja | 0.5h | Tarea 3 | → verificar: clic "Copy as JSON" pone JSON en portapapeles, toast "Copied" |
| 6 | ExportDialog: resumen pre-export y checkbox "Include skills" | `dashboard/components/builder/ExportDialog.tsx` (añadir a Tarea 3) | Mostrar lista de agents con role+tools, input editable bundle_name, checkbox disabled | `bundles/page.tsx:138-250` (resumen sidebar pattern) | FULLSTACK | Media | 0.75h | Tarea 0, 3 | → verificar: resumen muestra agents correctos, checkbox disabled con tooltip "Coming soon" |
| 7 | Refactorizar CrewCanvas: eliminar export inline, usar ExportDialog | `dashboard/components/builder/CrewCanvas.tsx` | Eliminar `handleExport`, `confirmExport`, `handleCopyJSON`, `<Dialog export>`. Añadir `<ExportDialog agents={canvasToExportPayload(nodes).agents} mode="crew" />` | N/A (refactor) | CODE | Media | 1h | Tarea 3 | → verificar: clic "Export" en CrewCanvas abre ExportDialog, export funciona igual |
| 8 | Integrar ExportDialog en AgentForm con modo "single" | `dashboard/components/builder/AgentForm.tsx` + `dashboard/components/builder/BuilderLayout.tsx` | Añadir botón "Export" junto a "Save Agent"/"Clear". On click → mapear `AgentFormData` a `AgentExportItem` → abrir ExportDialog | `AgentForm.tsx:351-358` (botones Save/Clear pattern) | FULLSTACK | Media | 1h | Tareas 3, 1 | → verificar: desde AgentForm con datos completados → clic "Export" → ExportDialog muestra 1 agente → ZIP descarga |
| 9 | Validar flujo end-to-end completo | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 3-8 | → verificar: criterios §5 [FULLSTACK] todos pasan |

**Tiempo total estimado:** 7.25 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Endpoint `GET /api/skills/available`**: Habilitar "Include skills" en ExportDialog. Mismo pattern que `GET /api/tools/available`.
- **Progreso de descarga**: Usar `ReadableStream` + `Content-Length` header para barra de progreso en ZIP grandes (>10MB).
- **Exportación de flows en bundle**: Actualmente `flows=[]` hardcoded. Cuando se implemente edición de flows en canvas, incluirlos en export.
- **`fap bundle preview` CLI**: Previsualizar contenido sin generar ZIP. Dogfooding de `ExportService.export()` con dry-run.
- **Validación pre-export en frontend**: Zod schema para `ExportBundleRequest` que valide goal/backstory ≥10 chars antes de enviar al backend (fail-fast UX).
- **Auto-naming por fecha**: Default bundle_name = `export_YYYYMMDD_HHMMSS` generado dinámicamente.
- **Extensiones de archivo consistentes**: Verificar que `SkillExportItem.name` no incluya `.py` en el frontend (backend lo añade).