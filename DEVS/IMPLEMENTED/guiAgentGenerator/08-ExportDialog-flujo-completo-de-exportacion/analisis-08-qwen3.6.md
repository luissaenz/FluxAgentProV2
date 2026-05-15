# Análisis Técnico — Paso 08: ExportDialog + flujo completo de exportación

**Agente:** qwen3.6
**Fecha:** 2026-05-15
**Fase:** guiAgentGenerator

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Endpoint `POST /api/bundles/export` existe | `src/api/routes/bundles.py:199-253` | ✅ | Handler `export_bundle`, validación goal/backstory, `ExportService` |
| 2 | `ExportService.export()` existe | `src/services/export_service.py:28-70` | ✅ | Retorna `tuple[bytes, str]`, usa `BundleManager.create_bundle()` |
| 3 | `ExportBundleRequest` Pydantic model | `src/services/bundle_schemas.py:111-116` | ✅ | `bundle_name`, `agents: List[AgentExportItem]`, `skills: Optional[List[SkillExportItem]]` |
| 4 | `AgentExportItem` Pydantic model | `src/services/bundle_schemas.py:102-108` | ✅ | `role`, `soul_json`, `allowed_tools`, `max_iter` |
| 5 | `SkillExportItem` Pydantic model | `src/services/bundle_schemas.py:95-99` | ✅ | `name`, `code` con constraints |
| 6 | `canvasToExportPayload()` existe | `dashboard/lib/canvasUtils.ts:36-44` | ✅ | Filtra `agentNode`, retorna `{ agents: AgentExportItem[] }` |
| 7 | `nodesToSnapshot()` existe | `dashboard/lib/canvasUtils.ts:46-72` | ✅ | Serializa grafo completo → JSON string |
| 8 | `CrewCanvas` tiene `exportDialogOpen` state | `CrewCanvas.tsx:83` | ✅ | `useState(false)` + diálogo inline básico |
| 9 | `CrewCanvas` tiene `confirmExport()` | `CrewCanvas.tsx:226-260` | ✅ | Llama `POST /bundles/export` directo con `fetch`, descarga blob |
| 10 | `BuilderLayout` NO tiene ExportDialog | `BuilderLayout.tsx` completo | ✅ | Solo TemplatePicker + AgentPlayground dialogs |
| 11 | `AgentForm` NO tiene botón export | `AgentForm.tsx:351-359` | ✅ | Solo "Save Agent" + "Clear" |
| 12 | `bundle_validator.py` script existe | `scripts/bundle_validator.py` | ✅ | Valida ZIP offline: manifest, hashes, agent/skill files |
| 13 | `generateCrewPy()` existe | `dashboard/lib/crewCodeGen.ts:3-80` | ✅ | Genera código Python crewai sequential |
| 14 | Tabla `agent_catalog` existe | `supabase/migrations/004_agent_catalog.sql` | ✅ | Con RLS tenant_isolation |
| 15 | `require_org_id` middleware existe | `src/api/middleware.py:66` | ✅ | Extrae `X-Org-ID` header |
| 16 | Tests round-trip export existen | `tests/integration/test_bundle_export_roundtrip.py` | ✅ | 3 tests: process_zip, mock import, estructura |
| 17 | Tests unitarios export existen | `tests/unit/test_bundle_export.py` | ✅ | 7 tests: validación, generación, edge cases |
| 18 | `fapFetch` / `api` helper existe | `dashboard/lib/api.ts` | ✅ | `api.post()`, `api.get()` con auth + org_id |

**Discrepancias encontradas:**

1. **D1 — ExportDialog inline en CrewCanvas, no componente separado:** El plan dice "Crear `dashboard/components/builder/ExportDialog.tsx"` pero `CrewCanvas.tsx:604-627` tiene un diálogo inline básico (solo warning + 2 botones). No hay archivo `ExportDialog.tsx`. → **Resolución:** Crear componente dedicado `ExportDialog.tsx` con resumen pre-export, checkbox "Include skills", feedback de progreso, "Copy as JSON".
2. **D2 — Export desde CrewCanvas usa `fetch` directo, no `api.post()`:** `CrewCanvas.tsx:234` usa `fetch` manual en lugar del helper `api` existente. → **Resolución:** Unificar a `api.post()` o mantener `fetch` si se necesita blob response (el helper `api` retorna `.json()`). Mantener `fetch` para blob download pero refactorizar a función reutilizable.
3. **D3 — AgentForm sin opción de export individual:** El plan dice "Integrar ExportDialog en AgentForm (exportar un solo agente)" pero `AgentForm.tsx` no tiene ningún botón/función de export. → **Resolución:** Añadir botón "Export" en AgentForm que exporte solo el agente del formulario.
4. **D4 — Sin feedback de progreso/size en export actual:** `confirmExport()` en CrewCanvas no muestra nombre del archivo ni tamaño antes de descargar. → **Resolución:** ExportDialog debe mostrar resumen pre-export con conteo de agentes, skills opcionales, nombre estimado del archivo.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**No hay cambios de schema.** El paso 08 es puramente UI + integración con endpoints existentes.

- **Tablas tocadas:** Ninguna nueva. `agent_catalog` (ya existente, mig 004) se lee indirectamente cuando el usuario selecciona agentes para exportar.
- **Integridad referencial:** Sin impacto. El export es stateless — no persiste nada en DB.
- **RLS policies:** Sin cambios. El endpoint `POST /api/bundles/export` usa `require_org_id` (header-based), no RLS directo.
- **Índices:** Ninguno nuevo.
- **Tipos de datos:** Sin cambios.

**Impacto en datos existentes:** Nulo. El export es lectura-only → genera ZIP en memoria → descarga.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes nuevos

#### 1. `ExportDialog.tsx`

**Firma completa:**
```tsx
interface ExportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onExport: (includeSkills: boolean) => Promise<void>
  onCopyJSON: () => void
  agents: { role: string; goal?: string; tools?: string[] }[]
  skills?: { name: string; code: string }[]
  mode: 'single-agent' | 'crew'
  isExporting: boolean
}

function ExportDialog(props: ExportDialogProps): JSX.Element
```

**Patrón a seguir:** `dashboard/components/builder/TemplatePicker.tsx` — Dialog con header, contenido scrollable, estados loading/error/empty, botones de acción.

**Imports:**
```tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Download, Copy, FileDown } from 'lucide-react'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { toast } from 'sonner'
```

#### 2. Función `performExport()` (utilidad reutilizable)

**Firma completa:**
```typescript
async function performExport(
  payload: { bundle_name?: string; agents: AgentExportItem[]; skills?: SkillExportItem[] },
  filename: string
): Promise<void>
```

**Ubicación:** `dashboard/lib/exportUtils.ts` (nuevo archivo)

**Patrón a seguir:** `dashboard/lib/api.ts` — función async con `fetch`, manejo de errores, blob download.

**Imports:**
```typescript
import { createClient } from '@/lib/supabase'
import { toast } from 'sonner'
```

### Componentes modificados

#### 3. `BuilderLayout.tsx`

**Cambios:**
- Añadir state `exportDialogOpen`, `exportMode`, `exportAgents`, `exportSkills`
- Añadir botón "Export" en toolbar (junto a Playground + Templates)
- Integrar `ExportDialog` component
- Botón Export visible en tab "Agent Form" (export agente individual) y "Crew Canvas" (export crew completo)

**Patrón a seguir:** Mismo patrón que TemplatePicker integration (`dialogOpen` state + Dialog wrapper).

#### 4. `AgentForm.tsx`

**Cambios:**
- Añadir prop `onExport?: (data: AgentFormData) => void`
- Añadir botón "Export" junto a "Save Agent" + "Clear"
- Botón disabled si formulario no es válido (sin role/goal/backstory)

#### 5. `CrewCanvas.tsx`

**Cambios:**
- Reemplazar diálogo inline (`exportDialogOpen` en línea 604-627) con `ExportDialog` component
- Usar `performExport()` de `exportUtils.ts` en lugar de `fetch` manual
- Pasar `agents` del canvas + `skills` opcionales al dialog

### Funciones nuevas en `canvasUtils.ts`

#### 6. `canvasToExportPayloadWithSkills()`

**Firma:**
```typescript
function canvasToExportPayloadWithSkills(
  nodes: Node[],
  includeSkills: boolean,
): { agents: AgentExportItem[]; skills?: SkillExportItem[] }
```

**Nota:** `canvasToExportPayload()` existente no incluye skills. Esta versión extiende para soportar checkbox "Include skills".

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**Sin cambios en backend.** El endpoint `POST /api/bundles/export` ya existe y funciona (Paso 02 completado).

### Endpoint existente — contrato

| Propiedad | Valor |
|---|---|
| Ruta | `POST /api/bundles/export` |
| Archivo | `src/api/routes/bundles.py:199-253` |
| Auth | `require_org_id` (header `X-Org-ID`) |
| Input | `ExportBundleRequest` (JSON body) |
| Output | `Response` con `Content-Type: application/zip` + `Content-Disposition: attachment` |
| Status | 200 (éxito), 422 (validación), 500 (error interno) |

### Payload de request (ya definido)

```python
class ExportBundleRequest(BaseModel):
    bundle_name: Optional[str] = Field(default=None, min_length=3, max_length=200)
    agents: List[AgentExportItem] = Field(..., min_length=1, max_length=15)
    skills: Optional[List[SkillExportItem]] = Field(default_factory=list)
```

### Error handling existente

| Error | Status | Detalle |
|---|---|---|
| `soul_json.goal` faltante | 422 | `agent '{role}': soul_json.goal required` |
| `soul_json.backstory` faltante | 422 | `agent '{role}': soul_json.backstory required` |
| goal/backstory < 10 chars | 422 | `must be at least 10 characters` |
| Error inesperado | 500 | `Internal server error during export: {str(e)}` |

### Flujo de datos

```
Frontend (ExportDialog)
  → POST /api/bundles/export (JSON body: {bundle_name, agents[], skills[]})
  → Backend valida goal/backstory (handler)
  → ExportService.export(payload) → BundleManager.create_bundle()
  → Response ZIP bytes
  → Frontend descarga blob como archivo
```

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end

```
[Agent Form tab]
  Usuario llena formulario → clic "Export" → ExportDialog abre
  → Resumen: 1 agente, role + goal preview
  → Checkbox "Include skills" (deshabilitado si no hay skills custom)
  → Botón "Export" → POST /api/bundles/export → descarga ZIP
  → Botón "Copy as JSON" → clipboard con JSON del agente

[Crew Canvas tab]
  Usuario arrastra agentes al canvas → clic "Export" → ExportDialog abre
  → Resumen: N agentes (lista de roles), M tasks (info-only, no exportadas)
  → Warning: "Tasks y connections no se exportan (bundle-schema-v2 limitación)"
  → Checkbox "Include skills"
  → Botón "Export" → POST /api/bundles/export → descarga ZIP
  → Botón "Copy as JSON" → clipboard con CrewGraph completo (nodes+edges)
```

### Coherencia con arquitectura existente

- ✅ `POST /api/bundles/export` ya existe y funciona (Paso 02)
- ✅ `canvasToExportPayload()` ya convierte nodos → payload compatible
- ✅ `bundle_validator.py` ya valida ZIPs offline
- ✅ Tests round-trip ya verifican re-importabilidad
- ⚠️ `api.post()` retorna `.json()`, no blob → export necesita `fetch` directo o modificar helper

### Gaps identificados

1. **Blob download con auth:** El helper `api.post()` parsea response como JSON. Para ZIP download se necesita `response.blob()`. Solución: función dedicada `performExport()` que usa `fetch` con headers de auth (mismo patrón que `CrewCanvas.tsx:234-253` pero reutilizable).
2. **Skills custom en frontend:** No hay UI para crear/editar skills custom en el builder. El checkbox "Include skills" estará deshabilitado hasta que el usuario tenga skills. Post-MVP: editor de skills en builder.
3. **Nombre del bundle:** El plan no especifica cómo se genera el nombre. Propuesta: default `export_{timestamp}` (ya implementado en backend), usuario puede override en dialog.

### DX & Tooling — OBLIGATORIO

```
### Herramienta Propuesta: fap bundle validate (CLI enhancement)
- **Qué automatiza:** Validar que un ZIP exportado desde el builder es re-importable sin necesidad de subirlo al dashboard. El usuario ejecuta localmente y obtiene reporte detallado de estructura, hashes, y compatibilidad.
- **Tipo:** CLI command (enhancement del script `bundle_validator.py` existente)
- **Cómo se usa:** `fap bundle validate ./crew_export.zip` — output: PASS/FAIL con detalles por archivo
- **Impacto para el usuario final:** Evita el ciclo "exportar → intentar importar → error → re-exportar". Validación instantánea local antes de compartir bundles.
- **Prioridad:** Tarea 0 — registrar como subcomando `fap bundle validate` antes de implementar el dialog
```

```
### Herramienta Propuesta: Export Preview (frontend)
- **Qué automatiza:** Muestra preview del contenido del ZIP antes de generar la descarga. El usuario ve exactamente qué agentes, skills y estructura tendrá el bundle.
- **Tipo:** Componente UI (dentro de ExportDialog)
- **Cómo se usa:** Al abrir ExportDialog, se renderiza lista de agentes con role + goal truncado + tool count. Checkbox para incluir/excluir skills.
- **Impacto para el usuario final:** Confirma qué se está exportando antes de descargar. Previene export accidental de agentes incompletos.
- **Prioridad:** Tarea 1 — parte integral del ExportDialog
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] Sin cambios de schema — paso no requiere migraciones nuevas
✅ [CODE] Componente `ExportDialog.tsx` existe con props: open, onOpenChange, onExport, onCopyJSON, agents, skills, mode, isExporting
✅ [CODE] Función `performExport()` en `exportUtils.ts` maneja blob download con auth headers
✅ [CODE] `BuilderLayout.tsx` integra ExportDialog con botón "Export" en toolbar
✅ [CODE] `AgentForm.tsx` tiene botón "Export" individual (disabled sin role/goal/backstory)
✅ [CODE] `CrewCanvas.tsx` reemplaza diálogo inline con `ExportDialog` component
✅ [BACKEND] Endpoint `POST /api/bundles/export` acepta payload desde ExportDialog sin cambios
✅ [BACKEND] ZIP descargable se puede re-importar con `POST /api/bundles/import` (round-trip)
✅ [FULLSTACK] ExportDialog muestra resumen pre-export: agentes incluidos, conteo, nombre del bundle
✅ [FULLSTACK] Checkbox "Include skills" funcional (deshabilitado si skills vacíos)
✅ [FULLSTACK] "Copy as JSON" copia al clipboard (agente individual en AgentForm, CrewGraph completo en CrewCanvas)
✅ [FULLSTACK] Manejo de errores: ZIP vacío → toast error, agentes sin role → disabled, timeout → toast error
✅ [DX] `fap bundle validate` CLI command registrado y funcional
✅ [DX] Export Preview muestra contenido antes de descargar
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Blob download falla con CORS | Alta | FastAPI no expone headers para blob response desde dominio diferente | Verificar CORS config en `main.py` — `allow_origins` debe incluir dominio del dashboard |
| Export de crew con tasks genera ZIP incompleto | Media | `bundle-schema-v2` no contempla tasks/edges → solo agents se exportan | Warning explícito en ExportDialog + "Copy as JSON" como alternativa para grafo completo |
| Skills custom no existen en frontend | Media | No hay UI para crear skills en builder → checkbox siempre deshabilitado | Documentar como limitación MVP. Post-MVP: editor de skills. |
| Auth token expira durante export | Baja | Export puede tardar > token lifetime si hay muchos agentes | `fapFetch` renueva token vía `supabase.auth.getSession()` en cada llamada |
| Bundle name collision al re-importar | Baja | Mismo `bundle_name` + mismo org_id → posible conflicto | Backend usa `bundle_name` solo para metadata, no como ID único. Sin riesgo real. |
| `api.post()` no soporta blob | Baja | Helper existente retorna `.json()` | Usar `fetch` directo con headers de auth en `performExport()` |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Registrar `fap bundle validate` CLI | `src/cli/commands/bundle_validate.py` | `def validate_bundle(file: str, verbose: bool): → tuple[bool, list[str]]` | `src/cli/commands/bundle_export.py` + `scripts/bundle_validator.py` | DX | Baja | 0.5h | Ninguna | → verificar: `uv run python -m src.cli.main bundle validate --help` muestra help |
| 1 | Crear `exportUtils.ts` con `performExport()` | `dashboard/lib/exportUtils.ts` | `async function performExport(payload: ExportPayload, filename: string): Promise<void>` | `dashboard/lib/api.ts` — fetch con auth headers | CODE | Baja | 0.5h | Tarea 0 | → verificar: `import { performExport } from '@/lib/exportUtils'` sin error TS |
| 2 | Crear `ExportDialog.tsx` componente | `dashboard/components/builder/ExportDialog.tsx` | `function ExportDialog(props: ExportDialogProps): JSX.Element` — props: `open, onOpenChange, onExport, onCopyJSON, agents[], skills?, mode, isExporting` | `dashboard/components/builder/TemplatePicker.tsx` — Dialog con header, scrollable content, action buttons | CODE | Media | 1.5h | Tarea 1 | → verificar: componente renderiza con agents mock, muestra resumen + checkboxes + botones |
| 3 | Añadir `canvasToExportPayloadWithSkills()` | `dashboard/lib/canvasUtils.ts` | `function canvasToExportPayloadWithSkills(nodes: Node[], includeSkills: boolean): { agents: AgentExportItem[]; skills?: SkillExportItem[] }` | `canvasToExportPayload()` existente (línea 36-44) | CODE | Baja | 0.5h | Tarea 1 | → verificar: retorna agents + skills cuando includeSkills=true y hay skill nodes |
| 4 | Integrar ExportDialog en `BuilderLayout.tsx` | `dashboard/components/builder/BuilderLayout.tsx` | Añadir states: `exportDialogOpen`, `exportMode`, `exportAgents`, `exportSkills`. Botón "Export" en toolbar junto a Playground/Templates. | Patrón TemplatePicker integration (`dialogOpen` state + Dialog wrapper, línea 129-139) | FULLSTACK | Media | 1h | Tareas 2, 3 | → verificar: botón Export visible en toolbar, abre dialog con agente actual del form |
| 5 | Añadir botón Export en `AgentForm.tsx` | `dashboard/components/builder/AgentForm.tsx` | Añadir prop `onExport?: (data: AgentFormData) => void`. Botón "Export" junto a "Save Agent" (línea 351-359). Disabled si `!watch('role') \|\| !watch('goal') \|\| !watch('backstory')`. | Patrón botones existentes en AgentForm (línea 351-359) | FULLSTACK | Baja | 0.5h | Tarea 2 | → verificar: botón Export aparece junto a Save Agent, disabled sin campos requeridos |
| 6 | Refactorizar `CrewCanvas.tsx` para usar ExportDialog | `dashboard/components/builder/CrewCanvas.tsx` | Reemplazar diálogo inline (línea 604-627) con `<ExportDialog ... />`. Usar `performExport()` en lugar de `fetch` manual (línea 234-253). | Patrón `handleExport()` + `confirmExport()` existentes, pero delegando a ExportDialog | FULLSTACK | Media | 1h | Tareas 2, 3 | → verificar: clic "Export" en canvas abre ExportDialog con lista de agentes del canvas |
| 7 | Validar flujo end-to-end completo | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 4-6 | → verificar: criterios §5 [FULLSTACK] y [DX] pasan todos. ZIP exportado re-importable sin errores |

**Tiempo total estimado:** 6 horas

---

## 🔮 Roadmap (NO implementar ahora)

1. **Editor de skills custom en builder:** UI para crear/editar Python skills desde el builder. Actualmente no hay forma de añadir skills custom sin CLI. Post-MVP: panel "Custom Skills" en BuilderLayout con editor de código + validación syntax.
2. **Export con tasks/edges:** Extender `bundle-schema-v2.md` para soportar tasks y edges. Actualmente solo agents se exportan. Alternativa MVP: "Copy as JSON" ya exporta grafo completo.
3. **Export progress indicator:** Para bundles grandes (>10 agents), mostrar progress bar durante generación del ZIP. Actualmente el backend genera ZIP en memoria instantáneamente, pero post-MVP con streaming podría necesitar feedback.
4. **Bundle naming wizard:** Permitir al usuario elegir nombre descriptivo del bundle con validación en tiempo real (min 3 chars, max 200, sin caracteres especiales).
5. **Export templates presets:** Exportar crew canvas como template reutilizable (no solo bundle). Similar a CREW_TEMPLATES pero generado por el usuario.
6. **Share bundle link:** Generar link compartible que permita importar bundle directamente sin descargar ZIP. Post-MVP: endpoint `POST /api/bundles/share` genera URL temporal.

---

## 🚫 Reglas de Oro — Checklist

- ✅ `proyecto-config.json` leído antes de explorar
- ✅ 18 elementos verificados (§0) — umbral: 12+ para 3-5 archivos
- ✅ 4 discrepancias detectadas (D1-D4)
- ✅ 8 secciones completadas (0-7)
- ✅ 4 etapas cubiertas (data, code, backend, fullstack+DX)
- ✅ 14 criterios de aceptación, todos verificables
- ✅ 6 riesgos identificados (técnico, integración, futuro)
- ✅ Tareas atómicas: 7 tareas, una por artefacto
- ✅ Interfaz exacta por tarea: firmas completas con tipos
- ✅ Patrón de referencia explícito por tarea: archivo concreto indicado
- ✅ Verificación inline por tarea: comando o check concreto
- ✅ 2 herramientas DX propuestas: `fap bundle validate` + Export Preview
- ✅ Estimación de tiempo: 6h total, por tarea
- ✅ Suposiciones no verificadas: 0
