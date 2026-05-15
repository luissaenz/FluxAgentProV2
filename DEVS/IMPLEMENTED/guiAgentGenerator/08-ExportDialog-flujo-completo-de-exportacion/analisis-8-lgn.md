# Análisis Técnico — Paso 8: ExportDialog + flujo completo de exportación

**Agente:** lgn  
**Paso:** 8  
**Objetivo:** Diálogo de exportación que consume `POST /api/bundles/export` y permite descargar el crew ensamblado como bundle ZIP

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `ExportDialog.tsx` debe crearse | Glob search | ❌ NO EXISTE | File no encontrado en `dashboard/components/builder/` |
| 2 | `POST /api/bundles/export` existe | `src/api/routes/bundles.py:199-253` | ✅ VERIFICADO | Handler con `require_org_id` + validación goal/backstory |
| 3 | `ExportService` existe | `src/services/export_service.py:21-70` | ✅ VERIFICADO | Orquestador que usa `BundleManager.create_bundle()` |
| 4 | `canvasToExportPayload()` existe | `dashboard/lib/canvasUtils.ts:36-44` | ✅ VERIFICADO | Filtra solo agentNodes → `AgentExportItem[]` |
| 5 | CrewCanvas export actual | `dashboard/components/builder/CrewCanvas.tsx:208-260` | ✅ VERIFICADO | Export directo sin ExportDialog component |
| 6 | `BundleManager.create_bundle()` existe | Verificado en corrections D1 | ✅ VERIFICADO | Genera ZIP en memoria |
| 7 | `AgentExportItem` schema | `src/services/bundle_schemas.py:102-109` | ✅ VERIFICADO | role, soul_json, allowed_tools, max_iter |
| 8 | Integration en AgentForm | `AgentForm.tsx` | ❌ NO ENCONTRADO | No hay botón export en AgentForm actual |

**Discrepancias encontradas:**
- ❌ `ExportDialog.tsx` NO existe - debe crearse desde cero
- ❌ El plan indica integración en AgentForm, pero AgentForm actual NO tiene botón export
- ⚠️ CrewCanvas tiene export inline (líneas 208-260) - NO usa ExportDialog separado
- ⚠️ El plan menciona "Include skills checkbox" - el export actual NO soporta skills

---

## 1️⃣ Análisis de Datos (ETAPA 1)

- **Tablas involucradas:** Ninguna nueva migración requerida
- **Schema existente:** `agent_catalog` (existente), `skill_catalog` (existente)
- **Export es read-only:** Lee de `agent_catalog` vía Supabase sin modificar schema
- **Skills opcional:** El payload puede incluir `skills: [{name, code}]` pero NO persiste en DB
- **RLS:** El `POST /api/bundles/export` usa `require_org_id` - solo exporta agentes del org

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes a crear/modificar:

**Nuevo archivo: `ExportDialog.tsx`**
- Propósito: Diálogo modal con resumen pre-export y opciones de export
- Props requeridas:
  - `open: boolean` - control de visibilidad
  - `onOpenChange: (open: boolean) => void` - callback de cierre
  - `nodes: Node[]` - nodos del canvas para generar payload
  - `orgId: string` - organización actual para autenticación
- Firmas:
  ```typescript
  interface ExportDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    nodes: Node[]
    orgId: string
  }
  ```

**Modificaciones en `AgentForm.tsx`:**
- Añadir botón "Export Agent" que abre ExportDialog con un solo agente
- El export payload para agente individual: `{ agents: [agentData] }`

**Patrón de referencia:** `CrewCanvas.tsx:208-260`
- Usar `canvasToExportPayload()` para generar payload
- Fetch con `Authorization` + `X-Org-ID` headers
- Descarga blob con `URL.createObjectURL()`

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoint existente: `POST /api/bundles/export`
- **Ruta:** `src/api/routes/bundles.py:199-253`
- **Auth:** `require_org_id` (header `X-Org-ID`)
- **Payload:** `ExportBundleRequest` (Pydantic)
  ```python
  class ExportBundleRequest(BaseModel):
      bundle_name: Optional[str]  # max 200 chars
      agents: List[AgentExportItem]  # 1-15 items, cada uno con role, soul_json, allowed_tools, max_iter
      skills: Optional[List[SkillExportItem]]  # name + code
  ```
- **Response:** `Response(content=zip_bytes, media_type="application/zip")`
- **Validaciones:** goal/backstory requeridos + mínimo 10 caracteres cada uno

### ExportService:
- `export(payload) -> tuple[bytes, str]` - genera ZIP en memoria
- Usa `BundleManager.create_bundle(manifest, agents, flows=[], skills)`
- **NOTA:** `flows=[]` hardcoded (limitación bundle-schema-v2)

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo end-to-end:
1. Usuario hace clic en "Export" (AgentForm o CrewCanvas)
2. ExportDialog muestra: agentes incluidos, skills sugeridas, advertencias
3. Usuario confirma → `POST /bundles/export` con payload
4. ZIP se descarga automáticamente
5. "Copy as JSON" copia el bundle manifest sin descargar

### DX & Tooling propuesto:
```
### Herramienta Propuesta: export-validator
- **Qué automatiza:** Valida que un bundle exportado cumpla con bundle-schema-v2 antes de descargar
- **Tipo:** Script CLI (Node.js)
- **Cómo se usa:** `npx @fap/export-validator crew_export.zip`
- **Impacto:** Previene errores de import eliminando bundles malformados
- **Prioridad:** Tarea 0 — implementar antes que ExportDialog
```

### Discrepancias plan vs código:
- ⚠️ **Tasks/edges NO exportables** - bundle-schema-v2 solo soporta agents + skills
- ⚠️ El plan menciona "skills personalizadas" pero NO hay UI para crear/editar skills
- ⚠️ Copy as JSON copia el grafo completo (nodes+edges) NO el bundle manifest

---

## 5️⃣ Criterios de Aceptación

```
✅ [DATA] No requiere migraciones nuevas
✅ [CODE] ExportDialog.tsx creado con props typed
✅ [CODE] AgentForm modificado con botón Export
✅ [BACKEND] POST /api/bundles/export funciona con agents array
✅ [BACKEND] POST /api/bundles/export acepta skills opcional
✅ [FULLSTACK] Diálogo muestra resumen de agentes a exportar
✅ [FULLSTACK] Botón Export descarga ZIP válido
✅ [FULLSTACK] "Copy as JSON" copia al portapapeles
✅ [FULLSTACK] ZIP re-importable con POST /api/bundles/import
✅ [DX] Herramienta export-validator creada
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| ZIP vacío/error | Media | Agent sin role/goal/backstory | Validar antes de enviar, mostrar errores específicos |
| Skills no soportadas | Baja | No hay `SkillExportItem` en UI | Documentar como "Post-MVP" |
| Timeout en export | Baja | Bundle muy grande (>50MB) | Limitar a 15 agentes max, validar tamaño |
| Roles duplicados | Media | Canvas permite duplicados | Deshabilitar Export hasta resolver (ya implementado en CrewCanvas) |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo | Verificación |
|---|---|---|---|---|---|---|---|---|
| 0 | DX: export-validator | `scripts/export-validator.ts` | `validateBundle(path: string): ValidationResult` | `scripts/bundle-validator.py` | DX | Baja | 0.5h | `node scripts/export-validator.ts --help` sin errores |
| 1 | Crear ExportDialog | `dashboard/components/builder/ExportDialog.tsx` | `export function ExportDialog({open,onOpenChange,nodes,orgId}:ExportDialogProps)` | Patrón Dialog en `CrewCanvas.tsx:604-627` | CODE | Media | 2h | Dialog muestra resumen, export funciona |
| 2 | Integrar en AgentForm | `dashboard/components/builder/AgentForm.tsx` | Botón "Export" → abre ExportDialog con `nodes=[formAgent]` | Patrón Sheet en `BuilderLayout.tsx:141-151` | CODE | Baja | 0.5h | Export agente individual funciona |
| 3 | Probar flujo completo | — | — | — | FULLSTACK | Baja | 0.5h | Criterios §5 todos pasan |

**Tiempo total estimado:** 3.5 horas

---

## 8️⃣ Roadmap (NO implementar ahora)

- Tasks/edges export en bundle-schema-v3
- Skills editor UI para crear skills personalizados
- Export con múltiples crews preseleccionados
- Plantillas de export con configuración predefinida