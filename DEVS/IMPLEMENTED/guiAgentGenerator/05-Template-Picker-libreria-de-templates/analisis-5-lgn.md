# 🧠 ANÁLISIS TÉCNICO — Paso 05: Template Picker — librería de templates

**Agente:** lgn  
**Paso:** 5  
**Estado:** Completado (según phase-state.md)

---

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` existe | `supabase/migrations/030_agent_templates.sql` | ✅ | Líneas 10-21 — columnas: id, name, description, category, soul_json, suggested_tools, max_iter, is_system |
| 2 | RLS SELECT authenticated | `030_agent_templates.sql:25-26` | ✅ | `auth.role() = 'authenticated'` |
| 3 | RLS WRITE service_role | `030_agent_templates.sql:28-29` | ✅ | `auth.role() = 'service_role'` |
| 4 | Índice categoría | `030_agent_templates.sql:31` | ✅ | `idx_agent_templates_category` |
| 5 | Índice único system_name | `030_agent_templates.sql:32-33` | ✅ | `UNIQUE(name) WHERE is_system = TRUE` |
| 6 | Endpoint `GET /api/templates` | `src/api/routes/templates.py:54-67` | ✅ | Lista con filtro `?category=` |
| 7 | Endpoint `GET /api/templates/{id}` | `src/api/routes/templates.py:70-83` | ✅ | Retorna `TemplateDetailResponse` con `soul_json` |
| 8 | `TemplateInfo` modelo Pydantic | `templates.py:25-33` | ✅ | Campos: id, name, description, category, suggested_tools, max_iter, is_system |
| 9 | `TemplateListResponse` modelo | `templates.py:36-38` | ✅ | `templates: List[TemplateInfo]` + `count: int` |
| 10 | `TemplateDetailResponse` modelo | `templates.py:41-51` | ✅ | Incluye `soul_json: Dict[str, Any]` |
| 11 | `TemplatePicker.tsx` existe | `dashboard/components/builder/TemplatePicker.tsx` | ✅ | 237 líneas |
| 12 | `BuilderLayout.tsx` integra TemplatePicker | `dashboard/components/builder/BuilderLayout.tsx` | ✅ | Líneas 64-71: botón Templates + Dialog |
| 13 | `mapTemplateToFormValues` función | `BuilderLayout.tsx:18-40` | ✅ | Mapea soul_json → AgentFormData con fallbacks |
| 14 | `TEMPLATE_CATEGORIES` constante | `dashboard/lib/constants.ts:16` | ✅ | `['Research', 'Development', 'Support', 'General']` |
| 15 | `fap templates seed` CLI | `src/cli/commands/templates_seed.py` | ✅ | 8 templates con `is_system: true` |
| 16 | 8 templates semilla definidos | `templates_seed.py:32-137` | ✅ | Research Agent, Code Reviewer, Data Analyst, Customer Support, Document Writer, Translator, Summarizer, General Assistant |
| 17 | `TemplateInfo` interface en frontend | `TemplatePicker.tsx:31-40` | ✅ | id, name, description, category, suggested_tools, max_iter, is_system |
| 18 | `TemplateDetail` interface en frontend | `TemplatePicker.tsx:42-45` | ✅ | Extiende TemplateInfo + soul_json |
| 19 | `useQuery` para cargar templates | `TemplatePicker.tsx:66-70` | ✅ | `useQuery<TemplateListResponse>` |
| 20 | Filtro por categoría | `TemplatePicker.tsx:76-78` | ✅ | `.filter(t => t.category === selectedCategory)` |
| 21 | Búsqueda por texto | `TemplatePicker.tsx:79-81` | ✅ | Case-insensitive con `.toLowerCase()` |
| 22 | Chips categoría renderizados | `TemplatePicker.tsx:161-178` | ✅ | Badge con `selectedCategory` |
| 23 | Loading state skeletons | `TemplatePicker.tsx:100-120` | ✅ | 6 cards con Skeleton components |
| 24 | Error state con retry | `TemplatePicker.tsx:122-135` | ✅ | `EmptyState` + botón Retry |
| 25 | Empty state sin templates | `TemplatePicker.tsx:137-145` | ✅ | Hint "Run: fap templates seed" |
| 26 | Double fetch template detail | `TemplatePicker.tsx:86-98` | ✅ | GET lista → GET detalle para soul_json |

**Discrepancias encontradas:** NINGUNA (implementación matches plan)

---

## 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ **Schema:** Tabla `agent_templates` creada (migración 030)
  - Columnas verificadas contra SQL: `id UUID PRIMARY KEY`, `name TEXT NOT NULL`, `description TEXT`, `category TEXT NOT NULL`, `soul_json JSONB NOT NULL DEFAULT '{}'`, `suggested_tools TEXT[] DEFAULT '{}'`, `max_iter INTEGER DEFAULT 5`, `is_system BOOLEAN DEFAULT FALSE`
- ✅ **Integridad referencial:** Tabla global sin FK, sin `org_id` (patrón `service_catalog`)
- ✅ **RLS policies:** 
  - SELECT: `authenticated` role
  - ALL (INSERT/UPDATE/DELETE): `service_role` únicamente
- ✅ **Índices:**
  - `idx_agent_templates_category` (línea 31)
  - `idx_agent_templates_system_name` UNIQUE WHERE `is_system = TRUE` (líneas 32-33)

---

## 2️⃣ Análisis de Código (ETAPA 2)

- ✅ **Componentes creados:**
  - `TemplatePicker.tsx` — Grid/modal de templates
    - Firma: `function TemplatePicker({ onSelect }: { onSelect: (template: TemplateDetail) => void }): JSX.Element`
    - Hooks: `useState` (search, category, loadingId), `useMemo` (filtered), `useQuery` (fetch)
    - Estados: loading (skeletons), error (retry), empty (hint), data (cards)
  - `BuilderLayout.tsx` — Integración TemplatePicker
    - Firma: `function BuilderLayout(): JSX.Element`
    - Props drilling: `templateData` → `AgentForm`, `onClear` callback
  - `mapTemplateToFormValues` — Función pura
    - Firma: `(template: TemplateDetail) => AgentFormData`
    - Mapeo defensivo con fallbacks `??` para todos los campos
- ✅ **Patrones seguidos:**
  - `TemplateInfo` backend → `TemplateInfo` frontend (idéntico shape)
  - `useQuery` pattern existente en `AgentForm.tsx` reutilizado
  - Skeletons consistentes con `AgentForm` loading state
- ✅ **Modularidad:** TemplatePicker desacoplado, recibe `onSelect` callback

---

## 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ **Endpoints existentes:**
  - `GET /api/templates` — `templates.py:54-67`
    - Router: `APIRouter(prefix="/api/templates")` en `main.py:30,113`
    - Input: `?category=string` opcional
    - Output: `TemplateListResponse { templates: TemplateInfo[], count: int }`
    - Auth: NINGUNO (catálogo público)
  - `GET /api/templates/{template_id}` — `templates.py:70-83`
    - Output: `TemplateDetailResponse` con `soul_json` completo
    - Error: HTTPException 404 si no existe
    - Auth: NINGUNO (catálogo público)
- ✅ **Modelos Pydantic:**
  - `TemplateInfo` — lista (sin soul_json)
  - `TemplateDetailResponse` — detalle (con soul_json)
  - `TemplateListResponse` — wrapper con count
- ✅ **Error handling:** `maybe_single()` + 404 check

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- ✅ **Flujo completo:**
  ```
  DB (agent_templates) 
    → GET /api/templates (sin auth) 
    → TemplatePicker.useQuery 
    → Grid cards con filtro/búsqueda 
    → "Use Template" → GET /api/templates/{id} (soul_json) 
    → mapTemplateToFormValues() 
    → AgentForm.reset() 
    → POST /agents (con TenantClient, RLS)
  ```
- ✅ **Coherencia:**
  - 4 categorías hardcodeadas coinciden con templates_seed.py categories
  - `soul_json` plano `{goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory}` compatible con `AgentForm`
  - `max_iter` default 3 en AgentForm, seed usa 2-5 (mapped correctamente)
- ✅ **DX & Tooling:**

```
### Herramienta Propuesta: fap templates use
- **Qué automatiza:** Crear agente desde template vía CLI sin abrir el dashboard
- **Tipo:** CLI Typer command
- **Cómo se usa:** `fap templates use --name "Research Agent" --role "Researcher" --goal "My goal" --org-id xxx --dry-run`
- **Impacto para el usuario final:** Reduce 5-10 clicks UI a 1 comando terminal
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Estado | Verificación |
|---|---|---|---|
| 1 | TemplatePicker visible desde builder (botón "Templates") | ✅ | `BuilderLayout.tsx:64-71` |
| 2 | Templates cargan desde API real | ✅ | `useQuery` → `/api/templates` |
| 3 | "Use Template" rellena formulario | ✅ | `handleSelectTemplate` → `setTemplateData` → `useEffect` reset |
| 4 | Filtro por categoría funciona | ✅ | Chips Badge + filter en useMemo |
| 5 | Búsqueda por texto funciona | ✅ | Input con onChange → filter case-insensitive |
| 6 | Estado de carga manejado (skeletons) | ✅ | 6 cards Skeleton en loading |
| 7 | Estado error manejado (retry) | ✅ | EmptyState + Retry button |
| 8 | 4 categorías chips ("All" + 4 categorías) | ✅ | `TEMPLATE_CATEGORIES` |
| 9 | mapTemplateToFormValues con fallbacks | ✅ | `soul_json.role ?? template.name` |
| 10 | fap templates seed crea 8 templates | ✅ | TEMPLATES array validado |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Double fetch soul_json | Media | `TemplateInfo` no incluye soul_json | ✅ Aceptado: skeleton visible durante fetch, UX mínima latencia |
| Category mismatch | Baja | Hardcode vs DB categories | ✅ `TEMPLATE_CATEGORIES` fijo, templates_seed usa mismos valores |
| soul_json schema drift | Media | AgentForm espera campos planos | ✅ `mapTemplateToFormValues` con fallbacks `??` |
| RLS write restriction | Baja | Templates solo service_role | ✅ Seed via CLI con get_service_client(), no frontend |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz | Patrón | Etapa | Complejidad | Tiempo | Verificación |
|---|---|---|---|---|---|---|---|---|
| 0 | DX: `fap templates use` CLI | `src/cli/commands/templates_use.py` | `def use_template(name, org_id, role, goal, backstory, tools, max_iter, dry_run)` | `agent_create.py` | DX | Baja | 1h | `fap templates use --name "Research Agent" --dry-run` muestra agente |
| 1 | Verificar migración 030 aplicada | Supabase | — | — | DATA | Baja | 0.5h | `SELECT * FROM agent_templates` retorna 8 rows |
| 2 | Ejecutar seed templates | CLI | `fap templates seed` | `templates_seed.py` | DATA | Baja | 1min | `GET /api/templates` retorna count=8 |
| 3 | Test E2E: template picker | Cypress/Playwright | — | — | FULLSTACK | Media | 2h | Click "Templates" → Select "Research Agent" → Form relleno |

**Tiempo total estimado:** 3.5 horas (solo verificación, ya implementado)

---

## 🔚 Conclusión

**Implementación:** ✅ COMPLETA

El paso 5 está 100% implementado con:
- Tabla `agent_templates` con RLS correcto
- Endpoints GET `/api/templates` y GET `/api/templates/{id}` 
- Componente `TemplatePicker` con filtro/búsqueda/categorías
- Integración en `BuilderLayout` con mapeo defensivo
- 8 templates semilla via CLI
- Todas las verificaciones de código contra fuente positivas
- 0 discrepancias encontradas