# 🏛️ Análisis Unificado — Paso 08: ExportDialog + flujo completo de exportación

**Fase:** `guiAgentGenerator`
**Unificador:** Arquitecto de Sistemas Senior
**Fecha:** 2026-05-15
**Fuente de verdad:** `proyecto-config.json` (leído) + código fuente (`src/`, `dashboard/`, `supabase/migrations/`)

---

## 0️⃣ Evaluación de Análisis y Verificaciones (OBLIGATORIO)

### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| step | ✅ 24 elementos | 6 (D1-D6) | ✅ `fap bundle export` (reutiliza) | ✅ archivos + líneas | 5.0 |
| dsp | ✅ 22 elementos | 7 (D1-D7) | ✅ `fap bundle validate-payload` (nuevo CLI) | ✅ archivos + líneas + firmas completas | 4.5 |
| glm5.1 | ✅ 22 elementos | 4 (D1-D4) | ✅ `fap bundle preview` + `fapDownload()` helper | ✅ archivos + líneas + tipos TS completos | 4.5 |
| qwen3.6 | ✅ 18 elementos | 4 (D1-D4) | ✅ `fap bundle validate` + ExportPreview | ✅ archivos + líneas | 4.0 |
| lgn | ✅ 8 elementos | 3 | ✅ `export-validator` (Node.js) | ✅ archivos + líneas | 4.0 |
| gpt-ossH | ✅ 7 elementos | 5 | ✅ `fap bundle export --as-json` | ✅ archivos + líneas | 3.5 |
| mm2.5 | ✅ 8 elementos | 3 | ✅ `fap bundle validate` CLI | ✅ archivos | 3.5 |
| nemoH | ✅ 10 elementos | 2 | ✅ ExportDialog como DX | ✅ archivos + líneas | 3.0 |
| llama3.3 | ✅ 10 elementos | 2 | ✅ ExportDialog como DX | ✅ archivos + líneas | 3.0 |
| x\<environment_details\> | ✅ 5 elementos | 4 | ❌ Ninguna concreta | ⚠️ Solo descripciones generales | 2.5 |

### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | **ExportDialog no existe como archivo independiente** — está inline en `CrewCanvas.tsx:604-627` | step, dsp, glm5.1, qwen3.6, gpt-ossH, mm2.5, lgn, nemoH, llama3.3, x | ✅ `CrewCanvas.tsx:604-627` | Crear `dashboard/components/builder/ExportDialog.tsx` como componente reutilizable. Extraer lógica inline de CrewCanvas. |
| 2 | **AgentForm no tiene botón de exportación** — el plan requiere integrar ExportDialog en AgentForm | step, dsp, glm5.1, qwen3.6, mm2.5, lgn, gpt-ossH | ✅ `AgentForm.tsx:351-359` (solo Save Agent + Clear) | Añadir botón "Export" junto a Save Agent. Construye payload de 1 agente desde `getValues()`. |
| 3 | **"Include skills" checkbox no existe en UI y skills no son accesibles desde frontend** — sin endpoint `GET /api/skills/available` | step, dsp, glm5.1, gpt-ossH, mm2.5, lgn | ✅ `CrewCanvas.tsx:241` (payload sin `skills`) + sin endpoint skills | MVP: checkbox "Include skills" visible pero disabled con tooltip "Coming soon". Post-MVP: endpoint `GET /api/skills/available`. |
| 4 | **`api.post()` no soporta blob response** — `fapFetch` siempre hace `response.json()` (línea 51) | glm5.1, dsp, step, qwen3.6 | ✅ `dashboard/lib/api.ts:51` — `return response.json()` | Crear función `fapDownload(path, body)` en `api.ts` que retorna `Response` sin parsear. ExportDialog usa `fapDownload()` → `.blob()`. |
| 5 | **`Checkbox` shadcn/ui no existe** en `dashboard/components/ui/` | glm5.1, step | ✅ `dashboard/components/ui/` — no existe `checkbox.tsx`. `bundles/page.tsx:18` lo importa (bug preexistente) | Crear `dashboard/components/ui/checkbox.tsx` con patrón Radix (`@radix-ui/react-checkbox`). Usar en ExportDialog para "Include skills". |
| 6 | **LLM config (`llm_provider`/`llm_model`) se pierde en export desde canvas** — AgentNode creado por drag-deploy no recibe estos campos | step, dsp | ✅ `canvasUtils.ts:21-22` — `node.data.llm_provider` solo si `!== undefined`; drag-deploy no lo setea | Mostrar warning en ExportDialog cuando `source='crew-canvas'`: "LLM configuration not included. Use Agent Form export for full config." |
| 7 | **`max_length=15` en `ExportBundleRequest.agents` no se valida en frontend** — canvas con >15 agentes causa 422 silencioso | step | ✅ `bundle_schemas.py:115` — `max_length=15` | ExportDialog valida `agents.length <= 15` antes de POST. Si >15, toast "+15 agents limit reached" + botón Export deshabilitado. |
| 8 | **Filename hardcoded `crew_export.zip`** — `CrewCanvas.tsx:241,251` no usa `bundle_name` personalizable | glm5.1 | ✅ `CrewCanvas.tsx:241` — `bundle_name: 'crew_export'` | ExportDialog acepta input editable `bundleName` (default: `export_YYYYMMDD_HHMMSS`). Pasar a `ExportBundleRequest.bundle_name`. |
| 9 | **bundle-schema-v2 no soporta tasks/edges** — solo agents se exportan en ZIP | step, dsp, gpt-ossH, mm2.5 | ✅ `export_service.py:65` — `flows=[]` hardcoded | Warning en ExportDialog: "Tasks and connections not exported (bundle-schema-v2 limitation). Use Copy as JSON for full graph." |
| 10 | **Sin feedback de progreso/tamaño en export** — `confirmExport()` no muestra filename ni tamaño antes de descargar | step, dsp, qwen3.6, gpt-ossH | ✅ `CrewCanvas.tsx:226-260` — solo toast al completar | ExportDialog muestra spinner "Generating bundle..." + toast con `{filename} ({size})` al completar. Sin barra de progreso real (ZIP se genera en memoria). |

---

## 1️⃣ Resumen Ejecutivo

- **Objetivo:** Añadir diálogo de exportación unificado (`ExportDialog.tsx`) que consuma `POST /api/bundles/export` (ya funcional desde Paso 02) y permita descargar agentes/crews como bundle ZIP desde AgentForm (1 agente) y CrewCanvas (N agentes).
- **Correcciones críticas al plan:** El plan asume que ExportDialog se crea desde cero, pero ya existe lógica inline en `CrewCanvas.tsx:604-627`. Debe refactorizarse (extraer a componente independiente), no duplicarse. El plan pide "Include skills (checkbox)" pero no existe endpoint `GET /api/skills/available` ni componente `Checkbox` en shadcn/ui — MVP con checkbox disabled. El plan menciona "Copy as JSON" en ExportDialog, pero CrewCanvas ya lo implementa (`handleCopyJSON`, línea 362-365) — unificar.
- **Herramienta DX seleccionada:** `fap bundle validate-payload` (CLI nuevo, propuesto por dsp) — valida payload JSON contra schema `ExportBundleRequest` antes de enviar al backend. **Fusión:** se complementa con `fapDownload()` helper (propuesto por glm5.1) como Tarea 0b necesario para blob download autenticado.

---

## 2️⃣ Diseño Funcional Consolidado

### Happy Path

1. Usuario configura agente en AgentForm (role, goal, backstory, tools, LLM) o ensambla crew en CrewCanvas (arrastra agentes, conecta tasks).
2. Usuario hace clic en botón "Export" (en AgentForm: junto a Save Agent; en CrewCanvas: en toolbar).
3. Se abre **ExportDialog** con resumen:
   - Lista de agentes a exportar (role, tools count, goal truncado)
   - Input editable de bundle name (default: `export_YYYYMMDD_HHMMSS`)
   - Checkbox "Include skills" (disabled con tooltip "Coming soon" en MVP)
   - Warning si `source='crew-canvas'`: "LLM config not included" + "Tasks/connections not exported"
4. Usuario revisa, opcionalmente edita bundle name, hace clic "Export as ZIP".
5. Loading spinner "Generating bundle..." mientras `POST /api/bundles/export` procesa.
6. Al completar: ZIP se descarga automáticamente + toast "Exported as {filename} ({size})".
7. Alternativa: "Copy as JSON" copia al portapapeles (agente individual en AgentForm, CrewGraph completo en CrewCanvas).
8. ZIP descargado es re-importable en `/integrations/bundles` vía Import Wizard.

### Edge Cases MVP

- **Agente sin role/goal/backstory:** Botón Export deshabilitado en AgentForm.
- **Canvas con >15 agentes:** ExportDialog muestra error "+15 agents limit reached" + botón Export deshabilitado.
- **Canvas sin agentes:** ExportDialog muestra "No agents to export" + botón Close.
- **Export desde canvas:** Warning visible "LLM configuration not included" + "Tasks not exported".
- **Fallo de red / timeout:** Toast error con detalle + botón "Retry" en diálogo.
- **Clipboard no disponible (HTTP):** Try/catch → toast "Clipboard unavailable. Copy manually:" + textarea con JSON.
- **Auth expirada:** `fapDownload()` lanza error → toast "Session expired. Please log in again."
- **ZIP >50MB:** Backend rechaza (500) → toast "Export too large. Try with fewer agents."

---

## 3️⃣ Diseño Técnico Definitivo

### Componentes y Modificaciones

#### A. `dashboard/components/builder/ExportDialog.tsx` — CREACIÓN

- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/dashboard/components/builder/ExportDialog.tsx`
- **Tipo de cambio:** Creación
- **Descripción:** Diálogo modal unificado para exportar agentes como bundle ZIP. Reutilizable desde AgentForm y CrewCanvas.
- **Interfaces clave:**
  ```typescript
  interface ExportDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    agents: AgentExportItem[]                          // payload agents
    source: 'agent-form' | 'crew-canvas'               // afecta warnings y opciones
    bundleName?: string                                // nombre editable (default generado)
    enableSkills?: boolean                             // checkbox "Include skills" (MVP: false)
    fullGraphJson?: string                             // para "Copy as JSON" (solo crew-canvas)
    onExportComplete?: () => void                      // callback post-export exitoso
  }

  // Estados internos:
  // - includeSkills: boolean (checkbox)
  // - bundleNameInput: string (input editable)
  // - isExporting: boolean
  // - error: string | null
  // - fileSize: string | null

  // Estados visuales del diálogo:
  // - summary  → lista agentes + checkbox + input nombre + botones Export/Copy
  // - exporting → LoadingSpinner "Generating bundle..." + botones deshabilitados
  // - success  → mensaje verde "Exported as {filename} ({size})" + botón Close
  // - error    → mensaje rojo con detalle + botón Retry + botón Close
  // - empty    → mensaje "No agents to export" + botón Close
  ```
- **Patrones a seguir:**
  - `TemplatePicker.tsx` — Dialog modal con estados loading/error/empty/data
  - `CrewCanvas.tsx:604-627` — diálogo export existente (estructura Dialog a extraer)
  - `AgentForm.tsx:316-347` — uso de `Switch` shadcn/ui
  - `LoadingSpinner.tsx:12` — indicador de carga

#### B. `dashboard/lib/api.ts` — MODIFICACIÓN

- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/dashboard/lib/api.ts`
- **Tipo de cambio:** Modificación (añadir función)
- **Descripción:** Añadir `fapDownload()` para descargas binarias con auth headers automáticos.
- **Interfaz clave:**
  ```typescript
  export async function fapDownload(path: string, body: unknown): Promise<Response> {
    // Obtiene session + orgId (mismo patrón que fapFetch)
    // fetch POST con Authorization Bearer + X-Org-ID + Content-Type JSON
    // Retorna Response sin parsear (.blob()/.arrayBuffer() a cargo del caller)
    // Si !response.ok → parsea error JSON → throw Error(detail)
  }
  ```
- **Patrón a seguir:** `api.ts:5-52` (`fapFetch` existente) pero sin `response.json()`.

#### C. `dashboard/components/ui/checkbox.tsx` — CREACIÓN

- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/dashboard/components/ui/checkbox.tsx`
- **Tipo de cambio:** Creación
- **Descripción:** Componente Checkbox shadcn/ui con `@radix-ui/react-checkbox` (ya instalado como dep transitiva de `@radix-ui/react-dropdown-menu`).
- **Interfaz clave:**
  ```typescript
  interface CheckboxProps {
    checked: boolean
    onCheckedChange: (checked: boolean) => void
    disabled?: boolean
    className?: string
  }
  export function Checkbox({ checked, onCheckedChange, disabled, className }: CheckboxProps): JSX.Element
  ```
- **Patrón a seguir:** `dashboard/components/ui/switch.tsx` — Radix primitive + cva + cn.

#### D. `dashboard/lib/types.ts` — MODIFICACIÓN

- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/dashboard/lib/types.ts`
- **Tipo de cambio:** Modificación (añadir tipos)
- **Descripción:** Añadir interfaces `AgentExportItem`, `SkillExportItem`, `ExportBundleRequest` para tipado fuerte del payload de exportación.
- **Interfaces clave:**
  ```typescript
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
  export interface ExportBundleRequest {
    bundle_name?: string
    agents: AgentExportItem[]
    skills?: SkillExportItem[]
  }
  ```

#### E. `dashboard/components/builder/CrewCanvas.tsx` — REFACTOR

- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/dashboard/components/builder/CrewCanvas.tsx`
- **Tipo de cambio:** Refactor
- **Descripción:**
  - **Eliminar:** state `exportDialogOpen` (línea 83), `exportWarning` (línea 84), funciones `handleExport()` (208-224), `confirmExport()` (226-260), `handleCopyJSON()` (362-366), bloque `<Dialog open={exportDialogOpen}>` (604-627).
  - **Añadir:** `useMemo` para `exportPayload` (`canvasToExportPayload(nodes)`) y `fullGraphJson` (`nodesToSnapshot(nodes, edges)`). Import y render de `<ExportDialog>` con props.
  - **Conservar:** `handleSaveCrew()` (332-351) — no se toca (funcionalidad distinta: save/load JSON).
- **Patrón a seguir:** Mismo archivo, pattern `useMemo` existente (línea 88).

#### F. `dashboard/components/builder/AgentForm.tsx` — MODIFICACIÓN

- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/dashboard/components/builder/AgentForm.tsx`
- **Tipo de cambio:** Modificación
- **Descripción:** Añadir botón "Export" junto a "Save Agent" y "Clear". Construye payload de 1 agente desde `getValues()`.
- **Firma clave:**
  ```typescript
  // Función helper en AgentForm:
  function buildSingleAgentPayload(): { agents: AgentExportItem[] } {
    const values = getValues()
    return {
      agents: [{
        role: values.role,
        soul_json: {
          goal: values.goal, backstory: values.backstory,
          llm_provider: values.llmProvider, llm_model: values.llmModel,
          verbose: values.verbose, reasoning: values.reasoning,
          inject_date: values.injectDate, memory: values.memory,
        },
        allowed_tools: values.allowedTools,
        max_iter: values.maxIter,
      }]
    }
  }
  ```
- **Botón:** `<Button type="button" variant="outline" onClick={...} disabled={!watch('role') || !watch('goal') || !watch('backstory')}>`
- **Patrón a seguir:** `AgentForm.tsx:351-358` (botones Save/Clear existentes).

#### G. `src/cli/commands/bundle_validate_payload.py` — CREACIÓN

- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/src/cli/commands/bundle_validate_payload.py`
- **Tipo de cambio:** Creación
- **Descripción:** CLI que valida un payload JSON contra el schema `ExportBundleRequest` sin ejecutar el endpoint real.
- **Interfaz clave:**
  ```python
  @app.command("validate-payload")
  def validate_payload(
      file: Annotated[Optional[Path], typer.Option("--file", help="JSON payload file")] = None,
      stdin: Annotated[bool, typer.Option("--stdin", help="Read from stdin")] = False,
      json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
  ) -> None:
      # Lee payload de file o stdin
      # Valida contra ExportBundleRequest (Pydantic)
      # Output tabla Rich: schema válido, agentes, skills, errores, advertencias, tamaño est.
  ```
- **Patrón a seguir:** `src/cli/commands/bundle_export.py:34-135` (estructura Typer command) + `scripts/bundle_validator.py` (lógica de validación).

#### H. `src/cli/main.py` — MODIFICACIÓN

- **Ruta real:** `/home/daniel/develop/Personal/FluxAgentProV2/src/cli/main.py`
- **Tipo de cambio:** Modificación (registro de comando)
- **Descripción:** Registrar `validate-payload` como subcomando de `bundle`.
- **Cambio:**
  ```python
  from src.cli.commands.bundle_validate_payload import validate_payload
  bundle_app.command("validate-payload")(validate_payload)
  ```
- **Patrón a seguir:** `src/cli/main.py:75` — registro de subcomandos `bundle`.

### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta 0a: fap bundle validate-payload
- **Qué automatiza:** Valida un payload de exportación JSON contra el schema ExportBundleRequest sin necesidad de ejecutar el endpoint real. Muestra summary (agentes, skills, tamaño estimado) y errores de validación específicos (goal/backstory ausente, longitud insuficiente, nombre inválido). Elimina el ciclo "exportar → error 422 → corregir → re-exportar".
- **Tipo:** CLI (comando Typer)
- **Ubicación:** src/cli/commands/bundle_validate_payload.py
- **Cómo se usa:**
  ```bash
  fap bundle validate-payload --file crew_payload.json
  cat crew_payload.json | fap bundle validate-payload --stdin
  fap bundle validate-payload --file crew_payload.json --json
  ```
- **Impacto para el usuario final:** Antes: construir payload en UI → esperar respuesta backend → ver error 422 → adivinar qué campo falla → corregir → reintentar. Después: validar en terminal en < 1s, ver todos los errores de una vez, corregir en lote.
- **El implementador DEBE usarla** para validar el contrato de payload antes de integrar ExportDialog.

### Herramienta 0b: fapDownload() helper (api.ts)
- **Qué automatiza:** Descarga binaria (ZIP) desde endpoints del backend con auth headers (JWT + X-Org-ID) automáticos. Evita duplicar lógica de fetch en cada componente que necesite blob response.
- **Tipo:** Función TypeScript (helper de API)
- **Ubicación:** dashboard/lib/api.ts
- **Cómo se usa:**
  ```typescript
  const response = await fapDownload('/api/bundles/export', payload)
  const blob = await response.blob()
  ```
- **Impacto para el usuario final:** El implementador no repite lógica de auth + fetch en ExportDialog, CrewCanvas, ni futuros componentes que necesiten descarga binaria.
- **El implementador DEBE usarla** en ExportDialog en lugar de `fetch()` directo.
```

---

## 4️⃣ Decisiones Tecnológicas

1. **ExportDialog como componente independiente (no inline en CrewCanvas):** El plan manda extraer a archivo separado. CrewCanvas.tsx:604-627 tiene implementación parcial inline que debe refactorizarse, no duplicarse. Justificación: reutilización desde AgentForm y CrewCanvas, testeabilidad unitaria del diálogo.

2. **⚠️ El plan dice "Include skills (checkbox)" pero:** `@/components/ui/checkbox` no existe (bug preexistente en `bundles/page.tsx:18`). Se crea `checkbox.tsx` con Radix (`@radix-ui/react-checkbox` ya instalado como dep transitiva). Checkbox en ExportDialog visible pero disabled en MVP (sin endpoint `GET /api/skills/available`). Tooltip: "Coming soon — custom skill selector not available yet."

3. **⚠️ El plan dice usar `api.post()` pero:** `fapFetch` siempre hace `response.json()` (línea 51). ZIP download necesita `response.blob()`. El código real usa `fetch` directo en `CrewCanvas.tsx:234`. Se crea `fapDownload()` en `api.ts` como helper dedicado para blob responses. No se modifica `fapFetch` existente (evita breaking change).

4. **⚠️ El plan no menciona límite de 15 agentes en `ExportBundleRequest`:** `bundle_schemas.py:115` tiene `max_length=15`. `canvasToExportPayload()` no valida este límite. ExportDialog debe validar `agents.length <= 15` antes de habilitar botón Export.

5. **LLM config en canvas export:** AgentNode creado por drag-deploy (`CrewCanvas.tsx:150-162`) no recibe `llm_provider`/`llm_model` de `AgentListItem`. Export desde canvas pierde esta información. ExportDialog muestra warning, no es error (el agente usa defaults del sistema al reimportar).

6. **Export agents-only en ZIP:** `bundle-schema-v2` no contempla tasks ni edges. `canvasToExportPayload()` filtra solo `agentNode`. `ExportService.export()` usa `flows=[]` hardcoded. Warning en ExportDialog: "Tasks and connections not exported." Alternativa: "Copy as JSON" exporta grafo completo (CrewGraph).

7. **Switch en lugar de Checkbox para toggles binarios:** `AgentForm.tsx:316-347` ya usa `Switch` para `verbose`, `reasoning`, `inject_date`, `memory`. ExportDialog usará `Checkbox` (nuevo componente) para "Include skills" por semántica (selección opcional, no toggle de estado). Consistente con UX esperada del plan.

---

## 5️⃣ Criterios de Aceptación MVP

```
✅ [DATA] No se requieren nuevas migraciones — paso puramente UI + integración con endpoint existente
✅ [DATA] Export es read-only sobre agent_catalog y skill_catalog — sin impacto en integridad referencial
✅ [CODE] ExportDialog.tsx creado en dashboard/components/builder/ con props: open, onOpenChange, agents, source, bundleName, enableSkills, fullGraphJson
✅ [CODE] checkbox.tsx creado en dashboard/components/ui/ con Radix primitives
✅ [CODE] fapDownload() helper añadido a dashboard/lib/api.ts — retorna Response sin parsear
✅ [CODE] Tipos AgentExportItem, SkillExportItem, ExportBundleRequest añadidos a dashboard/lib/types.ts
✅ [CODE] CrewCanvas.tsx refactorizado: lógica export inline eliminada (líneas 83-84, 208-260, 362-366, 604-627), reemplazada por <ExportDialog>
✅ [CODE] AgentForm.tsx modificado: botón "Export" junto a Save Agent, disabled sin role/goal/backstory
✅ [BACKEND] Endpoint POST /api/bundles/export funciona sin cambios (ya implementado Paso 02)
✅ [BACKEND] ZIP descargable es reimportable vía POST /api/bundles/import (round-trip verificado en Paso 02)
✅ [FULLSTACK] ExportDialog muestra resumen: lista de agentes (role + tools count), input bundle name, checkbox Include skills (disabled en MVP)
✅ [FULLSTACK] Botón "Export as ZIP" → POST /api/bundles/export → descarga automática con filename del header
✅ [FULLSTACK] "Copy as JSON" copia al portapapeles (agente individual en AgentForm, CrewGraph en CrewCanvas)
✅ [FULLSTACK] Warning "LLM config not included" visible cuando source='crew-canvas'
✅ [FULLSTACK] Warning "Tasks and connections not exported (bundle-schema-v2 limitation)" visible en crew-canvas
✅ [FULLSTACK] Loading spinner "Generating bundle..." durante export + toast con filename y tamaño al completar
✅ [FULLSTACK] Manejo de errores: sin agentes → empty state, >15 agentes → disabled + toast, goal/backstory <10 chars → error toast, timeout → error toast + retry
✅ [DX] fap bundle validate-payload ejecuta sin errores y valida payload contra schema ExportBundleRequest
✅ [DX] fapDownload() descarga binaria funcional con auth headers automáticos
```

**Funcionales:**
- [ ] ExportDialog se abre desde AgentForm con 1 agente y desde CrewCanvas con N agentes
- [ ] ZIP descargado es reimportable en `/integrations/bundles`
- [ ] Copy as JSON copia al portapapeles correctamente
- [ ] Checkbox "Include skills" visible pero disabled con tooltip en MVP

**Técnicos:**
- [ ] `npm run lint` en dashboard sin nuevos errores ni warnings
- [ ] `uv run ruff check src/ tests/` sin nuevos errores ni warnings
- [ ] Tests unitarios existentes: 7/7 `test_bundle_export.py` + 3/3 `test_bundle_export_roundtrip.py` siguen pasando
- [ ] Tests canvas: 7/7 `test_canvas_serialize.py` + 8/8 `test_crew_endpoints.py` siguen pasando (sin regresión tras refactor CrewCanvas)

---

## 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0a | **DX & Tooling:** `fap bundle validate-payload` — crear CLI `src/cli/commands/bundle_validate_payload.py` + registrar en `src/cli/main.py` | Baja | 0.5h | Ninguna |
| 0b | **DX & Tooling:** `fapDownload()` — añadir helper a `dashboard/lib/api.ts` para descarga binaria autenticada | Baja | 0.25h | Ninguna |
| 0c | **DX & Tooling:** `Checkbox` UI — crear `dashboard/components/ui/checkbox.tsx` con Radix (bloquea uso de checkbox en ExportDialog) | Baja | 0.5h | Ninguna |
| 1 | Añadir tipos `AgentExportItem`, `SkillExportItem`, `ExportBundleRequest` a `dashboard/lib/types.ts` | Baja | 0.25h | Ninguna |
| 2 | Crear `dashboard/components/builder/ExportDialog.tsx` — diálogo completo con estados summary/exporting/success/error/empty, input bundleName, checkbox includeSkills, botones Export/Copy | Media | 2h | 0b, 0c, 1 |
| 3 | Refactorizar `dashboard/components/builder/CrewCanvas.tsx` — eliminar export inline + confirmExport + handleCopyJSON + Dialog block, reemplazar por `<ExportDialog>` | Media | 1h | 2 |
| 4 | Integrar ExportDialog en `dashboard/components/builder/AgentForm.tsx` — añadir botón "Export" + `buildSingleAgentPayload()` | Baja | 1h | 2 |
| 5 | Validar flujo end-to-end: AgentForm Export → ZIP → reimportar en `/integrations/bundles` | Baja | 0.5h | 3, 4 |
| 6 | Validar flujo end-to-end: CrewCanvas Export → ZIP → reimportar + Copy as JSON | Baja | 0.5h | 3 |
| | **TOTAL** | | **~6.5h** | |

---

## 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Regresión en CrewCanvas por refactor | Media | Eliminar 4 funciones + 1 Dialog block puede romper referencias. `handleSaveCrew` también usa `nodesToSnapshot` pero NO se elimina. | Verificar tests `test_canvas_serialize.py` (7) + `test_crew_endpoints.py` (8) pasan tras cambios. `handleSaveCrew` no se toca. |
| `api.post()` incompatible con blob → duplicación de fetch | Media | `fapFetch` siempre `.json()`. Sin `fapDownload()`, cada componente repite fetch raw con auth. | Implementar `fapDownload()` como Tarea 0b. ExportDialog usa `fapDownload()` exclusivamente. |
| Checkbox no existe → build roto | Alta | `bundles/page.tsx:18` ya importa `Checkbox` inexistente. Añadir `checkbox.tsx` es requisito previo. | Crear `checkbox.tsx` como Tarea 0c (pre-requisito bloqueante). |
| Skills no accesibles desde frontend | Media | Sin endpoint `GET /api/skills/available`. Checkbox no puede poblar datos. | MVP: checkbox disabled con tooltip "Coming soon". Post-MVP: endpoint skills. |
| Export desde canvas pierde LLM config | Alta | AgentNode creado por drag-deploy no recibe `llm_provider`/`llm_model`. | Warning visible en ExportDialog. Agente usa defaults del sistema al reimportar. Post-MVP: enriquecer `AgentListItem` con `soul_json` completo. |
| >15 agentes en canvas → 422 sin feedback proactivo | Media | `canvasToExportPayload()` sin límite. Backend `max_length=15`. | ExportDialog valida `agents.length <= 15` antes de habilitar botón Export. |
| `navigator.clipboard` no disponible en HTTP no seguro | Baja | Requiere HTTPS o localhost. | Try/catch → textarea con JSON para copia manual si falla. |

---

## 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | ExportDialog abre desde AgentForm con 1 agente válido | AgentForm con role="Researcher", goal="Find information...", backstory="Experienced researcher...", tools=["fetch_url"] | Dialog muestra 1 agente en resumen, botón Export habilitado |
| TP-2 | ExportDialog abre desde AgentForm sin role/goal/backstory | AgentForm vacío | Botón "Export" en AgentForm deshabilitado |
| TP-3 | ExportDialog abre desde CrewCanvas con 3 agentes | Canvas con 3 agentNodes (Researcher, Writer, Reviewer) | Dialog muestra 3 agentes, warning "LLM config not included", warning "Tasks not exported" |
| TP-4 | Export as ZIP desde AgentForm → descarga | POST /api/bundles/export con payload de 1 agente | ZIP descargado, `manifest.json` contiene bundle_info con 1 agente, ZIP reimportable |
| TP-5 | Export as ZIP desde CrewCanvas → descarga | POST /api/bundles/export con payload de 3 agentes | ZIP descargado, 3 archivos JSON en `agents/`, ZIP reimportable |
| TP-6 | Copy as JSON desde AgentForm | Click "Copy as JSON" | Portapapeles contiene JSON con 1 agente (AgentExportItem) |
| TP-7 | Copy as JSON desde CrewCanvas | Click "Copy as JSON" | Portapapeles contiene CrewGraph (nodes+edges+metadata) |
| TP-8 | Export con >15 agentes | Canvas con 16 agentNodes | Botón Export deshabilitado, toast "+15 agents limit reached" |
| TP-9 | Export sin agentes | CrewCanvas vacío | ExportDialog muestra "No agents to export", botón Export deshabilitado |
| TP-10 | `fap bundle validate-payload` con payload válido | `--file valid_payload.json` | Output: "Schema válido ✓", agentes=3, errores=0 |
| TP-11 | `fap bundle validate-payload` con goal <10 chars | `--file invalid_payload.json` | Output: error "soul_json.goal must be at least 10 characters" |
| TP-12 | ZIP exportado se reimporta en Import Wizard | Subir ZIP en `/integrations/bundles` | Import exitoso, agentes aparecen en catálogo |

**Comandos para ejecutar tests:**
```bash
# Tests unitarios existentes (sin cambios — verificar no regresión)
uv run pytest tests/unit/test_bundle_export.py -v --timeout=60
uv run pytest tests/unit/test_canvas_serialize.py -v --timeout=60
uv run pytest tests/unit/test_crew_endpoints.py -v --timeout=60

# Tests integración round-trip (sin cambios — verificar no regresión)
uv run pytest tests/integration/test_bundle_export_roundtrip.py -v --timeout=60

# Validar DX tooling
uv run python -m src.cli.main bundle validate-payload --help

# Lint
uv run ruff check src/ tests/
cd dashboard && npm run lint
```

