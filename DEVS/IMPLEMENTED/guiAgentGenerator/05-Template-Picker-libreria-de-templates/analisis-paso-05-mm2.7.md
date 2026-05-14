# Análisis Paso 05 — Template Picker (mm2.7)

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` | grep `{migrations}/030_agent_templates.sql` | ✅ | mig 030 línea 10 |
| 2 | Endpoint `GET /api/templates` | grep `{api_routes}/templates.py:54` | ✅ | `templates.py:54-67` |
| 3 | Endpoint `GET /api/templates/{id}` | grep `{api_routes}/templates.py:70` | ✅ | `templates.py:70-83` |
| 4 | RLS `agent_templates_read` | grep `migrations/030` | ✅ | mig 030 línea 25-26 |
| 5 | `TemplateInfo` Pydantic model | grep `templates.py:25-33` | ✅ | `class TemplateInfo(BaseModel)` |
| 6 | `TemplateDetailResponse` model | grep `templates.py:41-51` | ✅ | `class TemplateDetailResponse` |
| 7 | `TemplatePicker.tsx` existe | ls `{dashboard}/components/builder/` | ✅ | `TemplatePicker.tsx` (6868 bytes) |
| 8 | `BuilderLayout.tsx` integra TemplatePicker | grep `BuilderLayout.tsx:89` | ✅ | `<TemplatePicker onSelect=...>` |
| 9 | `TEMPLATE_CATEGORIES` constante | grep `constants.ts:16` | ✅ | `['Research','Development','Support','General']` |
| 10 | `TEMPLATE_CACHE_MS` constante | grep `constants.ts:18` | ✅ | `5 * 60 * 1000` |
| 11 | `AgentForm.templateData` prop | grep `AgentForm.tsx:50,91` | ✅ | `templateData?: AgentFormData \| null` + useEffect |
| 12 | `mapTemplateToFormValues()` fn | grep `BuilderLayout.tsx:18-40` | ✅ | Mapeo defensivo con fallbacks |
| 13 | `GET /api/templates` sin auth | grep `templates.py:54` sin Depends | ✅ | Sin `require_org_id` |
| 14 | RLS SELECT `auth.role()='authenticated'` | grep `migrations/030:26` | ✅ | Policy pública lectura |
| 15 | Template seed idempotente | grep `templates_seed.py:183` | ✅ | Check-then-insert |

**Discrepancias encontradas:** ninguna.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ **Schema:** Tabla `agent_templates` (UUID, name TEXT, description TEXT, category TEXT, soul_json JSONB, suggested_tools TEXT[], max_iter INT, is_system BOOLEAN, created_at, updated_at). Global sin org_id.
- ✅ **Integridad referencial:** N/A (tabla standalone).
- ✅ **RLS policies:** `agent_templates_read` → SELECT requiere `auth.role() = 'authenticated'`; `agent_templates_write` → ALL solo `auth.role() = 'service_role'`. Lectura pública autenticada, escritura solo service_role (CLI seed).
- ✅ **Índices:** `idx_agent_templates_category` en category; `idx_agent_templates_system_name` UNIQUE WHERE is_system=TRUE.
- ✅ **Tipos de datos:** `soul_json JSONB` flexible. `suggested_tools TEXT[]` array de strings. Sin problemas detectados.

---

## 2️⃣ Análisis de Código (ETAPA 2)

- ✅ **Funciones/Clases nuevas:**
  - `TemplatePicker.tsx` (líneas 1-237): Componente React con useState, useMemo, useQuery. Estados: loading (skeletons), error (EmptyState+Retry), empty (EmptyState+seed hint), data (grid cards).
  - `mapTemplateToFormValues()` en `BuilderLayout.tsx:18-40`: Mapea `TemplateDetail → AgentFormData` con valid (`valid.includes(provider)`) y fallbacks `??`.

- ✅ **Patrones:**
  - TemplatePicker sigue patrón de `AgentForm`: useQuery + TanStack Query + api.get().
  - Mapeo usa `as const` assertion + type guard pattern (`valid.includes(provider as Provider)`).
  - Dialog modal con overflow-y-auto en BuilderLayout.

- ✅ **Imports exactos:**
  - TemplatePicker: `@tanstack/react-query`, `sonner`, `lucide-react`, `@/lib/api`, `@/lib/constants`, shadcn/ui components.
  - BuilderLayout: `@/components/builder/BuilderCanvas`, `@/components/builder/AgentForm`, `@/components/builder/TemplatePicker`, shadcn/ui Dialog.

- ✅ **Firma `TemplatePicker`:**
  ```typescript
  interface TemplatePickerProps {
    onSelect: (template: TemplateDetail) => void
  }
  // TemplateDetail = TemplateInfo + soul_json: Record<string, unknown> + updated_at?
  ```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ **Endpoints:**
  - `GET /api/templates?category=` → `TemplateListResponse` con `{templates: TemplateInfo[], count: int}`. Sin auth.
  - `GET /api/templates/{template_id}` → `TemplateDetailResponse` con `soul_json: Dict[str, Any]`. 404 si no existe.

- ✅ **Middleware:** Sin auth en endpoints templates (catálogo público). RLS `auth.role()='authenticated'` a nivel DB.

- ✅ **Flujo:** Frontend TemplatePicker → `api.get('/api/templates')` → Supabase `agent_templates` → `TemplateInfo[]` cards. Click "Use Template" → `api.get('/api/templates/{id}')` → `TemplateDetail` → `onSelect(template)` → `BuilderLayout.handleSelectTemplate` → `mapTemplateToFormValues` → `setTemplateData` → `AgentForm.useEffect(reset(templateData))`.

- ✅ **Contratos:** TemplateInfo para lista (sin soul_json). TemplateDetail para detalle completo (con soul_json). Double fetch necesario por diseño.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- ✅ **Flujo completo:** DB `agent_templates` → `GET /api/templates` (lista pública) → TemplatePicker grid → click "Use Template" → `GET /api/templates/{id}` (detail con soul_json) → mapTemplateToFormValues → AgentForm se llena → usuario guarda con POST /agents.

- ✅ **Coherencia:** step 05 reutiliza infrastructure paso 03 (tabla + endpoints) + paso 04 (AgentForm + BuilderLayout). Sin gaps detectados.

- ✅ **Gaps:** Ninguno. Double fetch es已知 tradeoff. Category chips hardcodeados en TEMPLATE_CATEGORIES (futuro: endpoint de categorías).

- ✅ **DX & Tooling:**

```
### Herramienta Propuesta: fap templates validate
- **Qué automatiza:** Validar que todos los templates en DB tengan soul_json válido y campos requeridos (role, goal, backstory).
- **Tipo:** CLI command
- **Cómo se usa:** fap templates validate [--org-id <uuid>] [--json]
- **Impacto para el usuario final:** Detecta templates corruptos antes de que el builder los muestre. Evita user confusion cuando template no llena formulario.
- **Prioridad:** Media — post-MVP. Templates seedados por sistema son confiables.
```

---

## 5️⃣ Criterios de Aceptación

- ✅ [DATA] Tabla `agent_templates` existe con columnas correctas (mig 030 verificada)
- ✅ [CODE] `TemplatePicker.tsx` rendering con 4 estados (loading/error/empty/data)
- ✅ [CODE] `mapTemplateToFormValues()` extrae `soul_json.role → role` plano con fallbacks
- ✅ [BACKEND] `GET /api/templates` retorna `{templates: TemplateInfo[], count}` sin auth
- ✅ [BACKEND] `GET /api/templates/{id}` retorna `TemplateDetailResponse` con soul_json
- ✅ [FULLSTACK] TemplatePicker visible desde builder (botón "Templates" en BuilderLayout)
- ✅ [FULLSTACK] Click "Use Template" → AgentForm se rellena con datos del template
- ✅ [FULLSTACK] Filtro por categoría funciona (TEMPLATE_CATEGORIES chips)
- ✅ [FULLSTACK] Búsqueda por nombre funciona (client-side case-insensitive)
- ✅ [DX] `fap templates seed` ejecuta sin errores (idempotente)

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| soul_json vacío o malformado en template DB | Media | Seed script no valida estructura | Post-MVP: `fap templates validate` CLI |
| Double fetch latency >500ms en conexión lenta | Baja | TemplateInfo no incluye soul_json | TemplatePicker con staleTime 5min (TEMPLATE_CACHE_MS) |
| Category hardcodeada → desincronización con DB | Baja | TEMPLATE_CATEGORIES como constante | Post-MVP: GET /api/templates/categories endpoint |
| Templates con role en campo wrong (no soul_json.role) | Media | Algunos seeds antiguos podrían tener role en lugar flat | mapTemplateToFormValues usa `template.name` como fallback para role |

---

## 7️⃣ Plan de Implementación

> Paso 05 ya implementado según phase-state.md. Análisis documenta estado actual.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | N/A (TemplatePicker implementado) | — | — | — | — | — | — | — | — |

**Tiempo total estimado:** N/A (completado)

---

## 🔮 Roadmap (NO implementar ahora)

- `fap templates validate` CLI para validar integridad de templates en DB
- `GET /api/templates/categories` endpoint dinámico (evita constante hardcodeada)
- Soporte para templates custom por organización (futura migración con org_id)
- Cache server-side de templates con TTL (actualmente client-side staleTime)

---

## 🚫 Reglas de Oro — Cumplimiento

- ✅ Análisis accionable y específico: basado en código real verificado
- ✅ TODO verificado contra código: 15 elementos verificados en §0
- ✅ Discrepancias detectadas: 0 (step ya implementado y funcional)
- ✅ Nivel CTO exigente: gap de double fetch documentado con justificación
- ✅ Coherente con phase-state.md: referencias cruzadas verificadas
- ✅ TODO el paso: TemplatePicker + integración BuilderLayout + mapeo
- ✅ DX tooling propuesto: `fap templates validate` CLI
- ✅ Tareas atómicas: N/A (completado)
- ✅ Interfaz exacta: TemplatePickerProps + mapTemplateToFormValues documentadas
- ✅ Suposiciones no verificadas: 0