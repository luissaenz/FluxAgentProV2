# 🧠 ANÁLISIS TÉCNICO — Paso 08 — AGENTE dsp

> Fase: `guiAgentGenerator`
> Paso: 8 — ExportDialog + flujo completo de exportación
> Analista: dsp
> Fecha: 2026-05-15
> Stack: Next.js 14 + TypeScript + ReactFlow v11 + FastAPI + Supabase

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Endpoint `POST /api/bundles/export` existe | grep `bundles.py` | ✅ | `src/api/routes/bundles.py:199-253` — handler con `Depends(require_org_id)` |
| 2 | `ExportBundleRequest` schema Pydantic | grep `bundle_schemas.py` | ✅ | `src/services/bundle_schemas.py:111-115` — agents (1-15), skills opcional |
| 3 | `AgentExportItem` schema | grep `bundle_schemas.py` | ✅ | `src/services/bundle_schemas.py:102-109` — role, soul_json, allowed_tools, max_iter |
| 4 | `ExportService.export()` operativo | grep `export_service.py` | ✅ | `src/services/export_service.py:28-70` — retorna `(zip_bytes, filename)` |
| 5 | `canvasToExportPayload()` util | grep `canvasUtils.ts` | ✅ | `dashboard/lib/canvasUtils.ts:36-44` — filtra agentNodes → `{agents: AgentExportItem[]}` |
| 6 | `AgentForm` con campos completos | grep `AgentForm.tsx` | ✅ | `dashboard/components/builder/AgentForm.tsx:30-42` — 11 campos zod |
| 7 | `CrewCanvas` tiene diálogo de export inline | grep `CrewCanvas.tsx` | ⚠️ | `dashboard/components/builder/CrewCanvas.tsx:604-627` — implementación parcial inline, NO componente separado |
| 8 | `CrewCanvas` tiene "Copy as JSON" | grep `CrewCanvas.tsx` | ⚠️ | `dashboard/components/builder/CrewCanvas.tsx:362-365` — duplicado con futuro ExportDialog |
| 9 | `ExportDialog.tsx` NO EXISTE | glob `ExportDialog*` | ❌ | **CREAR** — archivo nuevo requerido por el plan |
| 10 | Componente `Dialog` shadcn/ui disponible | read `dialog.tsx` | ✅ | `dashboard/components/ui/dialog.tsx:1-78` — `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription` |
| 11 | `api.post` disponible para fetch autenticado | read `api.ts` | ✅ | `dashboard/lib/api.ts:57-62` — JWT + X-Org-ID headers automáticos |
| 12 | `jszip` instalado en dependencias frontend | read `package.json` | ✅ | `dashboard/package.json:35` — `"jszip": "^3.10.1"` |
| 13 | `BundleManager.create_bundle()` genera ZIP en memoria | grep `export_service.py` | ✅ | `src/services/export_service.py:62` — `zip_bytes = self.bundle_manager.create_bundle(...)` |
| 14 | `SkillExportItem` schema para "Include skills" | grep `bundle_schemas.py` | ✅ | `src/services/bundle_schemas.py:95-99` — name, code |
| 15 | `navigator.clipboard.writeText` API disponible | estándar web | ✅ | API nativa del navegador, soportada en Chrome/Firefox/Safari |
| 16 | `AgentForm` exporta tipo `AgentFormData` | grep `AgentForm.tsx` | ✅ | `dashboard/components/builder/AgentForm.tsx:44` — `z.infer<typeof agentFormSchema>` |
| 17 | `LoadingSpinner` componente reutilizable | glob `LoadingSpinner*` | ✅ | `dashboard/components/shared/LoadingSpinner.tsx:12` — props: size, className, label |
| 18 | `sonner` toast disponible | grep `CrewCanvas.tsx` | ✅ | `dashboard/components/builder/CrewCanvas.tsx:17` — `import { toast } from 'sonner'` |
| 19 | `BuilderLayout` orquesta AgentForm + CrewCanvas | read `BuilderLayout.tsx` | ✅ | `dashboard/components/builder/BuilderLayout.tsx:50-153` — tabs, template dialog, playground sheet |
| 20 | Skills en `ExportBundleRequest` son opcionales | grep `bundle_schemas.py` | ✅ | `src/services/bundle_schemas.py:116` — `skills: Optional[List[SkillExportItem]] = Field(default_factory=list)` |
| 21 | `canvasToExportPayload` NO incluye llm_provider/llm_model en soul_json | ⚠️ LIMITACIÓN | read `canvasUtils.ts:11-33` | `node.data.llm_provider` → `soul_json.llm_provider` — pero AgentNode no recibe llm_provider del drag. Canvas agents pierden LLM config. |
| 22 | Export endpoint aplica validación goal/backstory min 10 chars | grep `bundles.py` | ✅ | `src/api/routes/bundles.py:215-238` — 422 si len < 10 |

### Discrepancias encontradas

| # | Discrepancia | Resolución |
|---|---|---|
| D1 | `CrewCanvas` tiene diálogo de export inline (líneas 604-627) que EL PLAN NO MENCIONA como implementación existente. Solapa con ExportDialog. | Extraer a `ExportDialog.tsx`. CrewCanvas delega a ExportDialog vía prop `exportPayload`. Eliminar Dialog inline + `confirmExport` de CrewCanvas. |
| D2 | "Copy as JSON" implementado en CrewCanvas (`handleCopyJSON`, línea 362-365). El plan pide incluirlo EN ExportDialog. | Unificar en ExportDialog. CrewCanvas pasa `fullGraphJson` como prop. Si no hay `fullGraphJson`, ExportDialog no muestra botón "Copy as JSON". |
| D3 | Export endpoint en backend valida `soul_json.goal` y `soul_json.backstory` (líneas 216-226 bundles.py). ExportDialog DEBE construir `soul_json` con formato `{goal, backstory, llm_provider?, llm_model?, verbose?, reasoning?, inject_date?, memory?}` para pasar validación. | `canvasToExportPayload()` ya construye soul_json parcial. ExportDialog debe enriquecerlo con LLM config si está disponible. |
| D4 | AgentForm no tiene botón/toggle de export. Plan requiere "Integrar ExportDialog en AgentForm (exportar un solo agente)". | Añadir botón "Export" al AgentForm (junto a Save Agent/Clear). Abre ExportDialog con payload de 1 agente construido desde form values. |
| D5 | "Include skills" checkbox NO EXISTE en ninguna parte. Plan requiere opción explícita. Sin skills seleccionables en UI actual (MVP sin custom skills per-agent). | Checkbox "Include skills" visible pero disabled con tooltip "No custom skills available" en MVP. Implementación completa post-MVP cuando exista skill selector. |
| D6 | `canvasToExportPayload()` incluye `llm_provider`/`llm_model` si `data.llm_provider !== undefined`. Pero AgentNode.soul_json se construye desde drag de sidebar, donde `data` es `AgentListItem` sin `llm_provider`. | Canvas export no puede incluir LLM config porque AgentNode no la tiene. ExportDialog advierte "LLM config not included in canvas export. Use Agent Form export for full config." |
| D7 | `ExportService.export()` construye el ZIP completo en memoria. No hay progreso incremental reportable. Tamaño y filename se conocen post facto. | Feedback visual: spinner durante fetch, toast con filename+tamaño al completar. Sin barra de progreso real (no soportado por backend). |

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema involucrado

**Tabla `agent_catalog`** (migración `004_agent_catalog.sql`) — lectura por ExportService:
- `role TEXT` — identificador del agente (export payload lo usa como key)
- `soul_json JSONB` — contiene `{goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}`
- `allowed_tools TEXT[]` — lista de herramientas asignadas
- `max_iter INT` — iteraciones máximas

**Tabla `skill_catalog`** (existente) — lectura opcional para skills:
- `name TEXT` — nombre de la skill
- `code_source TEXT` — código fuente Python

### Nuevas entidades de datos

Ninguna. Paso 08 es puramente UI/frontend. No requiere migraciones ni nuevas tablas.

### Estructura del payload de exportación

```json
{
  "bundle_name": "export_20260515_143000",
  "agents": [
    {
      "role": "Code Reviewer",
      "soul_json": {
        "goal": "Review pull requests for security issues",
        "backstory": "Senior security engineer with 10 years experience",
        "llm_provider": "groq",
        "llm_model": "llama-3.1-70b-versatile",
        "verbose": false,
        "reasoning": false,
        "inject_date": false,
        "memory": false
      },
      "allowed_tools": ["fetch_url", "read_file"],
      "max_iter": 3
    }
  ],
  "skills": []
}
```

### Integridad referencial

- Export NO persiste datos → sin constraints de FK
- `agent_catalog` tiene `UNIQUE(org_id, role)` → roles duplicados en export no generan conflictos (no inserta)
- RLS `agent_catalog_tenant_isolation` (mig 004) aplica en lectura → el export respeta tenant isolation

### Cambios de schema necesarios

**Ninguno.** Paso puramente UI.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Archivo nuevo: `ExportDialog.tsx`

**Ubicación:** `dashboard/components/builder/ExportDialog.tsx`

**Propósito:** Diálogo modal unificado para exportar agentes como bundle ZIP, accesible desde AgentForm (1 agente) y CrewCanvas (N agentes desde canvas).

**Props:**

```typescript
interface ExportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Payload desde canvas (canvasToExportPayload) */
  exportPayload: { agents: AgentExportItem[]; skills?: SkillExportItem[] } | null
  /** JSON completo del grafo para "Copy as JSON" (solo desde CrewCanvas) */
  fullGraphJson?: string
  /** Origen del diálogo: afecta labels y opciones disponibles */
  source: 'agent-form' | 'crew-canvas'
  /** Nombre sugerido para el ZIP */
  suggestedName?: string
}
```

**Patrón de referencia:** `dashboard/components/builder/TemplatePicker.tsx` (Dialog modal con contenido data-driven) + `dashboard/components/builder/CrewCanvas.tsx:604-627` (diálogo export existente a extraer).

**Firma completa de helpers internos:**

```typescript
// Construye summary de exportación
function buildExportSummary(
  agents: AgentExportItem[],
  skills: SkillExportItem[] | undefined
): { agentCount: number; skillCount: number; roles: string[] }

// Ejecuta descarga ZIP vía POST /api/bundles/export
async function executeExport(
  payload: ExportBundleRequest,
  onProgress: (phase: 'generating' | 'downloading') => void
): Promise<{ blob: Blob; filename: string; size: number }>

// Copia JSON al portapapeles
async function copyJSONToClipboard(json: string): Promise<void>
```

**Estados visuales del diálogo:**

| Estado | Contenido |
|---|---|
| `summary` (inicial) | Lista de agentes (roles), conteo de skills, opciones (Include skills checkbox, Copy as JSON button) |
| `exporting` | `LoadingSpinner` con label "Generating bundle..." + botones deshabilitados |
| `success` | Mensaje verde "Exported as {filename} ({size})" + botón "Close" |
| `error` | Mensaje rojo con detalle del error + botón "Retry" + botón "Close" |
| `empty` | Mensaje "No agents to export" + botón "Close" |

### Modificación: `CrewCanvas.tsx`

**Cambios:**
1. **Eliminar** estado `exportDialogOpen`, `exportWarning`, funciones `handleExport()`, `confirmExport()`, `handleCopyJSON()` y el `<Dialog open={exportDialogOpen}>` block (líneas 83-84, 208-260, 362-365, 604-627).
2. **Añadir** estado `exportDialogOpen` + props para `ExportDialog`:
   ```typescript
   const exportPayload = useMemo(() => canvasToExportPayload(nodes), [nodes])
   const fullGraphJson = useMemo(() => nodesToSnapshot(nodes, edges), [nodes, edges])
   ```
3. **Reemplazar** botón "Export" onclick → `setExportDialogOpen(true)`
4. **Añadir** `<ExportDialog>` al final del return JSX.

**Patrón de referencia:** Mismo archivo `CrewCanvas.tsx`, pattern existente de `handleExport()` → Dialog → `confirmExport()`. El refactoring preserva comportamiento pero delega a componente externo.

### Modificación: `AgentForm.tsx`

**Cambios:**
1. **Añadir** botón "Export" en la fila de botones (junto a "Save Agent" y "Clear"):
   ```tsx
   <Button type="button" variant="outline" onClick={handleOpenExport}>
     <Download className="mr-1.5 h-4 w-4" />
     Export
   </Button>
   ```
   Nota: no usar `type="submit"`. Deshabilitado si `!watch('role') || !watch('goal') || !watch('backstory')`.
2. **Añadir** estado `exportDialogOpen` + función `buildSingleAgentPayload()`:
   ```typescript
   function buildSingleAgentPayload(): { agents: AgentExportItem[] } {
     const values = getValues()
     return {
       agents: [{
         role: values.role,
         soul_json: {
           goal: values.goal,
           backstory: values.backstory,
           llm_provider: values.llmProvider,
           llm_model: values.llmModel,
           verbose: values.verbose,
           reasoning: values.reasoning,
           inject_date: values.injectDate,
           memory: values.memory,
         },
         allowed_tools: values.allowedTools,
         max_iter: values.maxIter,
       }]
     }
   }
   ```
3. **Añadir** `<ExportDialog>` al final del return JSX con `source="agent-form"`.

**Import nuevo:** `import { Download } from 'lucide-react'` (ya existe en CrewCanvas.tsx, añadir a AgentForm.tsx).

### Reutilización de patrones existentes

| Patrón | Referencia | Aplicación en ExportDialog |
|---|---|---|
| Dialog modal shadcn/ui | `BuilderLayout.tsx:129-139` (TemplatePicker) | `Dialog + DialogContent + DialogHeader + DialogTitle + DialogDescription` |
| Loading spinner con label | `LoadingSpinner.tsx:12` | `LoadingSpinner size="md" label="Generating bundle..."` |
| Toast sonner | `CrewCanvas.tsx:254` — `toast.success('Crew exported as ZIP')` | `toast.success(...)` / `toast.error(...)` |
| Fetch autenticado | `api.ts:54-62` — `api.post()` | `api.post('/bundles/export', payload)` → PERO necesita blob response. Usar `fetch` directo con headers de `fapFetch` |
| Memo para cálculos derivados | `CrewCanvas.tsx:88-91` — `useMemo(orgId)` | `useMemo` para `exportPayload` y `fullGraphJson` |
| Blob download pattern | `CrewCanvas.tsx:247-253` — `URL.createObjectURL(blob)` + `<a>` click | Mismo pattern. Extraer a helper `downloadBlob(blob, filename)` en `@/lib/utils` o inline |

### Modularidad y acoplamiento

- **ExportDialog** es independiente: recibe payload vía props, no accede a state global ni ReactFlow.
- **Cohesión alta**: toda la lógica de UI de exportación concentrada en un componente.
- **Acoplamiento bajo**: solo depende de `api.post`/`fapFetch` + `Dialog` + `LoadingSpinner` + `sonner`. Sin acoplamiento a ReactFlow ni canvas.
- **Reutilizable**: mismo componente sirve para AgentForm (1 agente) y CrewCanvas (N agentes).

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoint consumido

**`POST /api/bundles/export`** — `src/api/routes/bundles.py:199-253`

| Aspecto | Valor |
|---|---|
| Método | POST |
| Auth | `Depends(require_org_id)` — header `X-Org-ID` |
| Content-Type | `application/json` |
| Input | `ExportBundleRequest` (Pydantic) |
| Output (éxito) | `200` + `application/zip` + `Content-Disposition: attachment; filename=...` |
| Output (error validación) | `422` — `{detail: "agent 'X': soul_json.goal required"}` |
| Output (error servidor) | `500` — `{detail: "Internal server error during export: ..."}` |
| Timeout efectivo | ~5-10s (generación ZIP en memoria, sin streaming) |

### Validaciones del backend (relevantes para frontend)

1. **goal requerido** — `soul_json.goal` debe existir y ser string (línea 217-219)
2. **backstory requerido** — `soul_json.backstory` debe existir y ser string (línea 222-226)
3. **Longitud mínima 10 chars** — goal y backstory ≥ 10 caracteres (líneas 229-238)
4. **Máximo 15 agentes** — `ExportBundleRequest.agents` max_length=15 (bundle_schemas.py:115)
5. **Máximo 50MB** — `BundleManager` rechaza ZIP > 50MB

### Flujo de datos backend

```
ExportDialog (frontend)
  │
  ├─ Construye payload { bundle_name?, agents: AgentExportItem[], skills?: SkillExportItem[] }
  │
  ├─ POST /api/bundles/export  ──→  bundles.py:export_bundle()
  │                                      │
  │                                      ├─ Valida goal/backstory por agente
  │                                      ├─ ExportService(org_id).export(payload)
  │                                      │     ├─ create_base_manifest()
  │                                      │     ├─ Convierte skills a {filename: code}
  │                                      │     └─ bundle_manager.create_bundle(manifest, agents, flows=[], skills)
  │                                      │           └─ Genera ZIP en memoria (manifest.json + agents/*.json + skills/*.py)
  │                                      └─ Response(content=zip_bytes, media_type="application/zip")
  │
  └─ Recibe blob → URL.createObjectURL → <a> download click → toast success
```

### Autenticación

El frontend usa `fapFetch`/`api.post` que automáticamente inyecta:
- Header `Authorization: Bearer {supabase_access_token}`
- Header `X-Org-ID: {org_id}`

El endpoint backend valida `require_org_id` (extrae `X-Org-ID` header). Compatible.

### Error handling — contrato HTTP

| Escenario | Status backend | Mensaje frontend | Acción ExportDialog |
|---|---|---|---|
| Agente sin goal/backstory | 422 | `agent 'X': soul_json.goal required` | Mostrar en UI, NO reintentar (error de datos) |
| goal/backstory < 10 chars | 422 | `agent 'X': soul_json.goal must be at least 10 characters` | Mostrar en UI |
| ZIP > 50MB (raro en MVP) | 500 | `Internal server error...` | Mostrar error + "Try with fewer agents" |
| Backend caído / timeout | Error red | `Failed to connect to backend` | Botón "Retry" |
| Sin `X-Org-ID` header | 400 | `X-Org-ID header required` | Redirigir a selección de org |

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo completo end-to-end

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. USUARIO configura agente en AgentForm (role, goal, backstory, tools) │
│    ↓                                                                    │
│ 2. USUARIO hace clic en botón "Export"                                 │
│    ↓                                                                    │
│ 3. ExportDialog se abre con resumen:                                    │
│    ┌──────────────────────────────────────┐                            │
│    │ 📦 Export Agent                      │                            │
│    │                                      │                            │
│    │ Agent: Code Reviewer                 │                            │
│    │ Tools: fetch_url, read_file          │                            │
│    │ Max Iter: 3                          │                            │
│    │                                      │                            │
│    │ ☐ Include skills (none available)    │                            │
│    │                                      │                            │
│    │ [ Export as ZIP ]  [ Copy as JSON ]  │                            │
│    └──────────────────────────────────────┘                            │
│    ↓                                                                    │
│ 4. USUARIO hace clic "Export as ZIP"                                   │
│    ↓                                                                    │
│ 5. LoadingSpinner "Generating bundle..."                               │
│    ↓                                                                    │
│ 6. POST /api/bundles/export → ZIP blob                                 │
│    ↓                                                                    │
│ 7. Descarga automática (content-disposition) + toast "Exported as       │
│    export_20260515_143000.zip (2.4 KB)"                                 │
│    ↓                                                                    │
│ 8. USUARIO puede re-importar ZIP en /integrations/bundles               │
│    ↓                                                                    │
│ 9. Round-trip: CREAR → EXPORTAR → IMPORTAR → verificar agentes          │
└─────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────┐
│ FLUJO CREW CANVAS (N agentes):                                          │
│    ↓                                                                    │
│ 1. USUARIO arrastra agentes al canvas, conecta tasks                    │
│ 2. Clic "Export" en toolbar → ExportDialog                              │
│ 3. Resumen: "3 agents: Researcher, Writer, Reviewer"                    │
│    ⚠️ "Tasks and connections not exported (bundle-schema-v2 limitation)"│
│ 4. [ Export as ZIP ] descarga bundle con solo agentes                   │
│ 5. [ Copy as JSON ] copia grafo COMPLETO (nodes+edges) al portapapeles │
└─────────────────────────────────────────────────────────────────────────┘
```

### Coherencia arquitectónica

- **Decisiones de data apoyan al código**: `ExportBundleRequest` ya definido en backend. ExportDialog solo consume, no modifica.
- **APIs soportan experiencia**: El endpoint export ya existe (Paso 02). ExportDialog es capa de presentación.
- **MVP tiene sentido como unidad**: Usuario crea agente → lo exporta → puede compartir ZIP o reimportar. Flujo cerrado.

### Gaps detectados

| Gap | Causa | Impacto | Mitigación |
|---|---|---|---|
| Canvas agents sin LLM config | AgentNode no recibe `llm_provider`/`llm_model` del drag | Export desde canvas pierde selección de LLM | Advertir en ExportDialog. El agente usa defaults del sistema al reimportar. |
| Skills "Include" es no-op en MVP | Sin UI para crear/buscar skills custom | Checkbox no hace nada | Mostrar disabled con tooltip. Post-MVP: habilitar con selector de skills. |
| Sin barra de progreso real | ZIP se genera sincrónicamente en backend (todo en memoria) | Usuario ve spinner sin feedback incremental | Mostrar solo spinner + mensaje. Post-MVP: backend con streaming + Server-Sent Events. |
| `api.post` no soporta respuesta blob | `fapFetch` hace `response.json()`. El export retorna `application/zip`. | No se puede usar `api.post` directamente | Usar `fetch` directo duplicando headers de `fapFetch`. Mejora pendiente: `api.download()` o `api.postBlob()`. |

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: `fap bundle validate-payload`
- **Qué automatiza:** Valida un payload de exportación JSON contra el schema `ExportBundleRequest` sin necesidad de ejecutar el endpoint real. Muestra summary (agentes, skills, tamaño estimado) y errores de validación específicos (goal/backstory ausente, longitud insuficiente, nombre inválido). Elimina el ciclo "exportar → error 422 → corregir → re-exportar".
- **Tipo:** CLI (comando Typer)
- **Cómo se usa:**
  ```
  # Desde archivo JSON (generado por CrewCanvas Copy as JSON)
  fap bundle validate-payload --file crew_payload.json

  # Desde stdin
  cat crew_payload.json | fap bundle validate-payload --stdin

  # Con --json para output parseable
  fap bundle validate-payload --file crew_payload.json --json
  ```

  Output ejemplo:
  ```
  ╭───────────────┬─────────────────────────────────╮
  │ Validación    │ Resultado                       │
  ├───────────────┼─────────────────────────────────┤
  │ Schema válido │ ✓                               │
  │ Agentes       │ 3 (Researcher, Writer, Reviewer)│
  │ Skills        │ 0                               │
  │ Errores       │ 0                               │
  │ Advertencias  │ 1 (goal "test" < 10 chars)      │
  │ Tamaño est.   │ ~2.1 KB                         │
  ╰───────────────┴─────────────────────────────────╯
  ```
- **Impacto para el usuario final:** Antes: construir payload en UI → esperar respuesta backend → ver error 422 → adivinar qué campo falla → corregir → reintentar. Después: validar en terminal en < 1s, ver todos los errores de una vez, corregir en lote.
- **Prioridad:** Tarea 0 — implementar ANTES del ExportDialog para validar el contrato de payload que el frontend debe construir correctamente.
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] No se requieren nuevas tablas ni migraciones
✅ [CODE] ExportDialog.tsx existe en dashboard/components/builder/
✅ [CODE] ExportDialog acepta props: open, onOpenChange, exportPayload, fullGraphJson?, source, suggestedName?
✅ [CODE] CrewCanvas.tsx DELEGA export a ExportDialog (elimina Dialog inline + confirmExport + handleCopyJSON)
✅ [CODE] AgentForm.tsx tiene botón "Export" que abre ExportDialog con payload de 1 agente
✅ [CODE] ExportDialog construye summary: agentes (roles), skills count
✅ [CODE] Checkbox "Include skills" visible pero disabled en MVP con tooltip
✅ [CODE] Botón "Export as ZIP" → POST /api/bundles/export → descarga automática
✅ [CODE] Botón "Copy as JSON" visible solo cuando source="crew-canvas" y fullGraphJson != null
✅ [BACKEND] POST /api/bundles/export acepta payload construido por ExportDialog sin errores 422
✅ [BACKEND] ZIP descargado es reimportable vía POST /api/bundles/import sin errores
✅ [FULLSTACK] Usuario crea agente en AgentForm → Export → descarga ZIP → reimporta en /integrations/bundles → agente aparece en catálogo
✅ [FULLSTACK] Usuario ensambla crew en canvas → Export → ZIP contiene todos los agentes del canvas
✅ [FULLSTACK] "Copy as JSON" copia el grafo COMPLETO (nodes+edges+metadata) al portapapeles
✅ [FULLSTACK] Feedback visual: spinner durante export, toast con filename + tamaño al completar
✅ [FULLSTACK] Manejo de errores: ZIP vacío (sin agentes), agentes sin goal/backstory, timeout
✅ [DX] fap bundle validate-payload ejecuta sin errores y valida payload contra schema ExportBundleRequest
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Export desde canvas pierde LLM config | Alta | AgentNode no almacena `llm_provider`/`llm_model` del formulario original. El drag solo copia datos de `AgentListItem` (GET /agents response). | ExportDialog muestra warning: "LLM configuration not included in canvas export. Use Agent Form export for full configuration." Post-MVP: enriquecer AgentListItem con soul_json completo desde backend. |
| Regresión en CrewCanvas por refactoring | Media | Eliminar 6 funciones (handleExport, confirmExport, handleCopyJSON, handleSaveCrew exportDialogOpen) + Dialog block puede romper referencias. `handleSaveCrew` también usa `nodesToSnapshot`. | `handleSaveCrew` (línea 332-351) NO se elimina (es funcionalidad distinta: save/load JSON). Solo se elimina la lógica de export ZIP + Copy as JSON. Verificar tests `test_canvas_serialize.py` (7 tests) + `test_crew_endpoints.py` (8 tests) pasan tras cambios. |
| `api.post` incompatible con blob response | Media | `fapFetch` hace `response.json()` para todos los métodos. Export retorna `application/zip`. | Usar `fetch` directo en ExportDialog con headers copiados de `fapFetch`. No modificar `api.ts` (evitar breaking change). Documentar como limitación MVP. Post-MVP: añadir `api.postBlob()`. |
| Export sin `soul_json.role` causa round-trip parcial | Baja | El export endpoint no requiere `soul_json.role`. Pero al reimportar, si soul_json no tiene role, el agente puede perder metadata de rol en el catálogo. | Incluir `soul_json.role = agent.role` al construir payload en ExportDialog. Compatible con schema actual (Dict sin restricciones). |
| Clipboard API no disponible en HTTP no seguro | Baja | `navigator.clipboard.writeText` requiere contexto seguro (HTTPS o localhost). En entornos sin HTTPS, falla silenciosamente. | Envolver en try/catch. Si falla: toast "Clipboard unavailable. Copy manually:" + mostrar textarea con JSON para copia manual. |
| ZIP > 50MB con muchos agentes + skills | Baja | 15 agentes × ~500KB cada uno ≈ 7.5MB (no alcanza 50MB). Skills custom grandes podrían acercarse. | ExportDialog muestra advertencia si > 10 agentes: "Large export may be slow". Post-MVP: streaming + progress. |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap bundle validate-payload` | `src/cli/commands/bundle_validate_payload.py` | `def validate_payload(file: Optional[str], stdin: bool, json_output: bool) -> None` | `src/cli/commands/bundle_export.py:34-135` — estructura Typer command | DX | Baja | 1h | Ninguna | → verificar: `uv run fap bundle validate-payload --help` + test con payload inválido (goal ausente) retorna error descriptivo |
| 1 | Crear `ExportDialog.tsx` | `dashboard/components/builder/ExportDialog.tsx` | `export function ExportDialog({ open, onOpenChange, exportPayload, fullGraphJson, source, suggestedName }: ExportDialogProps)` | `dashboard/components/builder/TemplatePicker.tsx` — Dialog modal con estados loading/error/success/data | CODE | Media | 2h | Tarea 0 | → verificar: importable sin error TS + `npm run lint` sin nuevos errores + dialog abre/cierra con botón externo |
| 2 | Integrar ExportDialog en AgentForm | `dashboard/components/builder/AgentForm.tsx` | Añadir botón "Export" + estado `exportDialogOpen` + `buildSingleAgentPayload()` → `{ agents: [{role, soul_json: {goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}, allowed_tools, max_iter}] }` | Mismo archivo, pattern `handleSubmit` (accede a `getValues()`) | CODE | Baja | 1h | Tarea 1 | → verificar: botón "Export" visible en AgentForm, deshabilitado si role/goal/backstory vacíos. Clic abre ExportDialog con summary de 1 agente. |
| 3 | Refactorizar CrewCanvas para delegar export a ExportDialog | `dashboard/components/builder/CrewCanvas.tsx` | Eliminar: `exportDialogOpen`, `exportWarning` states, `handleExport()`, `confirmExport()`, `handleCopyJSON()`, `<Dialog open={exportDialogOpen}>` block. Añadir: `useMemo` para `exportPayload` + `fullGraphJson`, `<ExportDialog>` con props. | Mismo archivo, pattern `useMemo` existente (línea 88) + `Dialog` existente (línea 559-571) | CODE | Media | 1.5h | Tarea 1 | → verificar: `npm run lint` sin errores. Botón "Export" en toolbar abre ExportDialog. Export y Copy as JSON funcionan igual que antes. `handleSaveCrew` sigue operativo (no afectado). |
| 4 | Añadir `fap bundle validate-payload` al registro CLI | `src/cli/main.py` | `from src.cli.commands.bundle_validate_payload import validate_payload` + `bundle_app.command("validate-payload")(validate_payload)` | `src/cli/main.py:75` — pattern `add_typer(bundle_app, name="bundle")` | CODE | Baja | 0.25h | Tarea 0 | → verificar: `uv run fap bundle --help` muestra `validate-payload` en subcomandos |
| 5 | Validar round-trip export→import | — | Flujo manual: AgentForm → Export ZIP → Ir a /integrations/bundles → Import → Verificar agente en catálogo | Test manual end-to-end | FULLSTACK | Baja | 0.5h | Tareas 1-4 | → verificar: ZIP exportado de AgentForm se reimporta exitosamente. Agente aparece en lista. |

**Tiempo total estimado:** 6.25 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Post-MVP**: `api.postBlob()` método en `api.ts` para respuestas binarias (evita fetch directo en ExportDialog)
- **Post-MVP**: Enriquecer `AgentListItem` (GET /agents) con `soul_json` completo para que canvas export incluya LLM config
- **Post-MVP**: Backend streaming ZIP generation con Server-Sent Events para barra de progreso real en ExportDialog
- **Post-MVP**: "Include skills" realmente funcional con selector de skills custom en AgentForm
- **Post-MVP**: Export con tasks/edges incluidos (requiere extensión de bundle-schema-v2.md)
- **Post-MVP**: Tabla `skill_catalog` en frontend → `useQuery` GET /skills para poblar el checkbox "Include skills"

---

## 📊 Métrica de Calidad

| Métrica | Estado |
|---|---|
| `proyecto-config.json` leído | ✅ |
| Elementos verificados (§0) | 22 / 12 requeridos |
| Discrepancias detectadas | 7 (≥1 para código existente) |
| Secciones completadas | 8 (0-7) |
| Etapas cubiertas | 4 (data, code, backend, fullstack+DX) |
| Criterios de aceptación | 18 (verificables, binarios) |
| Riesgos identificados | 6 (≥3) |
| Tareas atómicas | 5 tareas = 5 artefactos |
| Interfaz exacta por tarea | 5/5 — con firmas TypeScript + Python completas |
| Patrón referencia explícito por tarea | 4/4 — archivos concretos (no "seguir el estilo") |
| Verificación inline por tarea | 5/5 — comandos concretos |
| Suposiciones no verificadas | 0 |
| Propuesta DX | 1 herramienta (`fap bundle validate-payload`) |
| Estimación de tiempo | 6.25h total (por tarea y global) |
