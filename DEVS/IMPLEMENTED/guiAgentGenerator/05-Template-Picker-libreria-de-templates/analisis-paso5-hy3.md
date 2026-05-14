# Análisis Técnico — Paso 05: Template Picker — librería de templates
**Agente:** hy3  
**Fecha:** 2026-05-14  
**Fase:** guiAgentGenerator  
**Plan:** /DEVS/plan.md (Paso 05, líneas 103-122)

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `TemplatePicker.tsx` existe | Glob `dashboard/components/builder/*.tsx` | ✅ | Glob result línea 2 |
| 2 | `TemplatePicker.tsx` no debería existir (plan task 1: "Crear") | Plan Paso 05 línea 109 | ❌ DISCREPANCIA | Plan vs glob result |
| 3 | Endpoint `GET /api/templates` existe | `src/api/routes/templates.py` existe | ✅ | templates.py línea 54 |
| 4 | Router de templates registrado | `src/api/main.py` línea 113 | ✅ | main.py línea 113 |
| 5 | Tabla `agent_templates` existe | Migración `030_agent_templates.sql` | ✅ | Migración línea 10 |
| 6 | `TemplatePicker` carga templates desde API | `TemplatePicker.tsx` línea 68 | ✅ | TemplatePicker.tsx línea 68 |
| 7 | `TemplatePicker` muestra cards con name/description/category/suggested tools | `TemplatePicker.tsx` líneas 191-213 | ✅ | TemplatePicker.tsx líneas 191-213 |
| 8 | Botón "Use Template" rellena `AgentForm` | `BuilderLayout.tsx` `mapTemplateToFormValues` | ✅ | BuilderLayout.tsx líneas 18-40 |
| 9 | Filtro por categoría (chips) implementado | `TEMPLATE_CATEGORIES` = ['Research','Development','Support','General'] | ✅ | constants.ts línea 16 |
| 10 | Barra de búsqueda implementada | `TemplatePicker.tsx` líneas 150-158 | ✅ | TemplatePicker.tsx líneas 150-158 |
| 11 | `TemplatePicker` visible desde builder | `BuilderLayout.tsx` botón "Templates" línea 64 | ✅ | BuilderLayout.tsx línea 64 |
| 12 | RLS en `agent_templates` aplicada | Migración 030 líneas 25-29 | ✅ | Migración líneas 25-29 |
| 13 | Índice en columna `category` | Migración 030 línea 31 | ✅ | Migración línea 31 |
| 14 | `AgentForm` acepta `templateData` prop | `AgentForm.tsx` línea 50 | ✅ | AgentForm.tsx línea 50 |
| 15 | `AgentForm` resetea formulario con datos de template | `AgentForm.tsx` useEffect líneas 91-107 | ✅ | AgentForm.tsx líneas 91-107 |

**Discrepancias encontradas:**
1. ❌ DISCREPANCIA: Plan Paso 05 task 1 indica "Crear `dashboard/components/builder/TemplatePicker.tsx`", pero el archivo ya existe y está implementado. El plan asume que el paso 5 crea el archivo desde cero, pero el código ya lo tiene.
2. ⚠️ NO VERIFICABLE: Plan Paso 03 task 6 indica "Seed inicial con 8 templates predefinidos", no se encontró script de seed en `scripts/` ni verificación de datos en DB. CONFIRMAR antes de implementar.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ **Schema:** Tabla `agent_templates` (migración 030) con columnas:
  `id UUID PK`, `name TEXT NOT NULL`, `description TEXT`, `category TEXT NOT NULL`, `soul_json JSONB NOT NULL DEFAULT '{}'`, `suggested_tools TEXT[] DEFAULT '{}'`, `max_iter INTEGER DEFAULT 5`, `is_system BOOLEAN DEFAULT FALSE`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`.
- ✅ **Integridad referencial:** Tabla standalone, no tiene FKs a otras tablas.
- ✅ **RLS policies:**
  - `agent_templates_read`: SELECT USING `auth.role() = 'authenticated'` (lectura pública para usuarios autenticados)
  - `agent_templates_write`: ALL USING `auth.role() = 'service_role'` (escritura solo system)
  - Cumple criterio de aceptación de Paso 03: "RLS aplicado: lectura pública, escritura solo system".
- ✅ **Índices necesarios:**
  - `idx_agent_templates_category` (filtro por categoría)
  - `idx_agent_templates_system_name` UNIQUE (name) WHERE `is_system = TRUE` (evita duplicados de templates de sistema)
- ✅ **Tipos de datos:** `soul_json` JSONB para almacenar configuración flexible del agente, `suggested_tools` TEXT[] para lista de herramientas sugeridas. Sin tipos problemáticos.

---

## 2️⃣ Análisis de Código (ETAPA 2)

- ✅ **Funciones/componentes nuevos:**
  - `TemplatePicker.tsx`: Componente cliente con props `onSelect: (template: TemplateDetail) => void`. Maneja estado de search, selectedCategory, loadingId. Usa `useQuery` para cargar templates, `useMemo` para filtrar.
  - `TemplateDetail` interface (exportada): Extiende `TemplateInfo` con `soul_json` y `updated_at`.
  - `BuilderLayout.tsx`: Función `mapTemplateToFormValues` mapea `TemplateDetail` a `AgentFormData` (convierte `soul_json` a campos del formulario).
- ✅ **Patrones seguidos:**
  - Uso de `@tanstack/react-query` para fetching de datos (mismo patrón que `AgentForm.tsx` para tools).
  - Componentes de shadcn/ui (`Card`, `Badge`, `Input`, `Button`, `Dialog`) consistentes con otros componentes del builder.
  - Imports absolutos (`@/lib/api`, `@/components/ui/*`) según convención `import_style: "absolutos"` de `proyecto-config.json`.
  - Manejo de estados de carga (skeletons), error (EmptyState + retry) y vacío (EmptyState con instrucción de seed).
- ✅ **Modularidad:** `TemplatePicker` es un componente independiente, recibe `onSelect` como prop, no acoplado a `AgentForm` directamente. `BuilderLayout` orquesta la comunicación.
- ✅ **Imports exactos:**
  - `TemplatePicker.tsx`: `api` from `@/lib/api`, `TEMPLATE_CATEGORIES` from `@/lib/constants`, componentes de shadcn/ui.
  - `BuilderLayout.tsx`: Importa `TemplatePicker`, `AgentForm`, `TemplateDetail` desde rutas relativas correctas.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ **APIs/endpoints:**
  - `GET /api/templates`: Lista templates, acepta query param `?category=` opcional. Retorna `TemplateListResponse` (templates array + count). Sin autenticación (lectura pública).
  - `GET /api/templates/{id}`: Retorna detalle de template con `soul_json` completo. 404 si no existe.
- ✅ **Middleware:** Endpoints no usan `require_org_id` (patrón `integrations.py`, lectura pública según `templates.py` línea 7).
- ✅ **Contratos:**
  - Request `GET /api/templates?category=Research`: Retorna array de templates con `category=Research`.
  - Response happy path: `{ "templates": [ { "id": "...", "name": "...", "description": "...", "category": "Research", "suggested_tools": ["tool1"], "max_iter": 5, "is_system": true, "created_at": "..." } ], "count": 1 }`
  - Error 404: `{ "detail": "Template not found" }`
- ✅ **Error handling:** `get_template` endpoint lanza `HTTPException(404)` si no existe. Errores de Supabase se propagan via FastAPI. Frontend maneja errores con `toast.error`.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- ✅ **Flujo completo:** Builder → Clic "Templates" → Dialog abre → `TemplatePicker` carga de `GET /api/templates` → Usuario filtra/busca → Clic "Use Template" → Fetch a `GET /api/templates/{id}` → Mapeo a `AgentFormData` → `AgentForm` se resetea con datos del template.
- ✅ **Coherencia:** Categorías en `TEMPLATE_CATEGORIES` coinciden con plan (Research, Development, Support, General). `mapTemplateToFormValues` convierte `soul_json` a campos del formulario (role, goal, backstory, llm_provider, etc.) correctamente.
- ✅ **UX:** Estados de carga (skeletons), error (EmptyState + retry), vacío (instrucción de seed). Filtro y búsqueda en tiempo real. Feedback visual al hacer clic en "Use Template" (loading spinner).
- ✅ **Gaps:** `soul_json` no tiene un schema validado, puede variar entre templates. El plan Paso 03 no define schema de `soul_json` para templates.

### Herramienta Propuesta: Seed de Templates de Sistema
- **Qué automatiza:** Inserta los 8 templates predefinidos (Research Agent, Code Reviewer, Data Analyst, Customer Support, Document Writer, Translator, Summarizer, General Assistant) en `agent_templates` si no existen, evitando que el usuario tenga que insertarlos manualmente.
- **Tipo:** Script Python
- **Cómo se usa:** `uv run python scripts/seed_templates.py`
- **Impacto para el usuario final:** Los desarrolladores no tienen que insertar manualmente los templates iniciales, asegura que `TemplatePicker` tenga datos para mostrar desde el primer deploy.
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso (validar que los templates existen).

---

## 5️⃣ Criterios de Aceptación

- ✅ [FULLSTACK] TemplatePicker visible desde el builder (botón "Templates" en BuilderLayout)
- ✅ [FULLSTACK] Templates cargan desde API real (`GET /api/templates`)
- ✅ [FULLSTACK] Al hacer clic en "Use Template", el formulario se rellena (`AgentForm` reset con datos de template)
- ✅ [FULLSTACK] Filtro por categoría funciona (chips de categoría, filtro aplicado)
- ✅ [FULLSTACK] Búsqueda por texto funciona (input de búsqueda filtra por nombre)
- ✅ [FULLSTACK] Estado de carga y error manejados (skeletons, error state, retry button)
- ✅ [DATA] Tabla `agent_templates` creada con migración versionada (030)
- ✅ [BACKEND] `GET /api/templates` devuelve array de templates
- ✅ [BACKEND] `GET /api/templates/{id}` devuelve template completo con `soul_json`
- ✅ [DX] Herramienta de seed propuesta para templates iniciales

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|--------|-----------|-------|------------|
| `soul_json` de templates no tiene schema estandarizado → `mapTemplateToFormValues` puede fallar al mapear campos | Media | Plan Paso 03 no define estructura de `soul_json` para templates | Definir schema de `soul_json` para templates, validar en script de seed |
| `GET /api/templates` no tiene paginación → rendimiento degrada con muchos templates | Baja | Solo 8 templates iniciales, pero puede crecer | Implementar paginación (`?page=`, `?limit=`) si el número de templates supera 50 |
| "Use Template" hace una petición extra para obtener detalle → delay pequeño para el usuario | Baja | `list_templates` no devuelve `soul_json` (para evitar payload grande) | Aceptable para MVP, el delay es mínimo (una petición pequeña) |
| Plan está desactualizado respecto al código (TemplatePicker ya existe) | Media | Paso 5 asume que TemplatePicker se crea desde cero | Actualizar plan.md para marcar Paso 05 como implementado, o ajustar tareas a modificaciones futuras |

---

## 7️⃣ Plan de Implementación

> [!CRITICAL]
> Paso 05 ya está implementado en el código actual. Las tareas siguientes son para corregir discrepancias y cerrar gaps.

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Seed de templates de sistema | `scripts/seed_templates.py` | `def run(): ...` (inserta 8 templates si no existen) | `scripts/seed_system_bundles.py` | DX | Baja | 1h | Ninguna | → verificar: `uv run python scripts/seed_templates.py` ejecuta sin errores + `agent_templates` tiene 8 rows |
| 1 | Validar `soul_json` de templates | `supabase/migrations/031_template_schema.sql` | Añadir comentario de schema de `soul_json`: `{ role, goal, backstory, llm_provider, llm_model, verbose, reasoning, inject_date, memory }` | `supabase/migrations/030_agent_templates.sql` | DATA | Baja | 0.5h | Tarea 0 | → verificar: `CREATE TABLE` migrate sin errores + comentario existe |
| 2 | Actualizar plan.md Paso 05 | `DEVS/plan.md` | Marcar tareas de Paso 05 como completadas, ajustar tareas futuras si es necesario | `DEVS/plan.md` actual | FULLSTACK | Baja | 0.5h | Ninguna | → verificar: `git diff DEVS/plan.md` muestra tareas completadas |

**Tiempo total estimado:** 2 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Añadir paginación a `GET /api/templates` si el número de templates crece.
- Añadir endpoint `POST /api/templates` para que usuarios creen sus propios templates (no solo system).
- Validación de `soul_json` en backend para templates nuevos.
- Previsualización de `soul_json` en `TemplatePicker` card (mostrar más detalles del template).
