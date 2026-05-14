# ANÁLISIS — Paso 05: Template Picker (Agente: mm)

## 0️⃣ Verificación contra Código Fuente

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_templates` existe | grep `supabase/migrations/030_agent_templates.sql` | ✅ | línea 10 |
| 2 | Columnas: id, name, description, category, soul_json, suggested_tools, max_iter, is_system | migración 030 | ✅ | líneas 10-21 |
| 3 | RLS: SELECT authenticated, ALL service_role | migración 030 | ✅ | líneas 25-29 |
| 4 | Índice category | migración 030 | ✅ | línea 31 |
| 5 | Índice parcial UNIQUE(name) WHERE is_system | migración 030 | ✅ | líneas 32-33 |
| 6 | Endpoint GET /api/templates existe | src/api/routes/templates.py:54-67 | ✅ | línea 54 |
| 7 | Endpoint GET /api/templates/{id} existe | src/api/routes/templates.py:70-83 | ✅ | línea 70 |
| 8 | Filtro ?category= funciona | templates.py:61-62 | ✅ | query.eq() |
| 9 | Response incluye count | templates.py:38,66 | ✅ | TemplateListResponse |
| 10 | Endpoint sin require_org_id (público) | templates.py:54,70 | ✅ | Sin Depends |
| 11 | CLI `fap templates seed` existe | src/cli/commands/templates_seed.py | ✅ | línea 1 |
| 12 | CLI registrado en main.py | src/cli/main.py:34,58 | ✅ | add_typer |
| 13 | Component AgentForm.tsx existe | dashboard/components/builder/AgentForm.tsx | ✅ | línea 1 |
| 14 | AgentForm usa react-hook-form + zod | AgentForm.tsx:72-73 | ✅ | zodResolver |
| 15 | AgentForm tiene initialValues prop | AgentForm.tsx:49,61,74-86 | ✅ | Partial<AgentFormData> |
| 16 | Component ToolMultiSelect.tsx existe | dashboard/components/builder/ToolMultiSelect.tsx | ✅ | línea 1 |
| 17 | Patrón búsqueda + filtrado en ToolMultiSelect | ToolMultiSelect.tsx:42-50 | ✅ | useMemo filtered |
| 18 | Component BuilderLayout.tsx existe | dashboard/components/builder/BuilderLayout.tsx | ✅ | línea 1 |
| 19 | UI dialog existe | dashboard/components/ui/dialog.tsx | ✅ | shadcn |
| 20 | UI card existe | dashboard/components/ui/card.tsx | ✅ | shadcn |
| 21 | UI badge existe | dashboard/components/ui/badge.tsx | ✅ | shadcn |
| 22 | API client api.get() | dashboard/lib/api.ts:55-56 | ✅ | fapFetch wrapper |

**Discrepancias encontradas:**
- Ninguna directa. Seed de templates (8 predefinidos) existe en CLI pero no verificado si ejecutado en Supabase. **Acción:** el implementador debe ejecutar `fap templates seed` antes de probar el TemplatePicker.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema
- **Tabla:** `agent_templates` (global, sin org_id)
- **Columnas:**
  - `id UUID` — PK, gen_random_uuid()
  - `name TEXT NOT NULL` — nombre del template
  - `description TEXT` — descripción breve
  - `category TEXT NOT NULL` — Research/Development/Support/General
  - `soul_json JSONB NOT NULL DEFAULT '{}'` — config del agente
  - `suggested_tools TEXT[] DEFAULT '{}'` — tools recomendadas
  - `max_iter INTEGER DEFAULT 5` — iteraciones máximas
  - `is_system BOOLEAN DEFAULT FALSE` — template del sistema
  - `created_at TIMESTAMPTZ DEFAULT now()`
  - `updated_at TIMESTAMPTZ DEFAULT now()`

### Integridad Referencial
- No hay FK. Tabla global independiente.
- Índice parcial `UNIQUE(name) WHERE is_system = TRUE` previene duplicados de system templates.

### RLS Policies
- SELECT: `auth.role() = 'authenticated'` — cualquier usuario logueado puede leer
- ALL (INSERT/UPDATE/DELETE): `auth.role() = 'service_role'` — solo seed CLI escribe

### Datos Existentes
- CLI `fap templates seed` debe ejecutarse previamente para populates la tabla con 8 templates predefinidos.
- Si no hay datos, TemplatePicker mostrará array vacío.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes a Crear

#### TemplatePicker.tsx
**Ubicación:** `dashboard/components/builder/TemplatePicker.tsx`

**Interfaz:**
```typescript
interface TemplatePickerProps {
  onSelect: (template: TemplateData) => void
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface TemplateData {
  id: string
  name: string
  description: string
  category: string
  soul_json: {
    goal: string
    backstory: string
    llm_provider: string
    llm_model: string
    verbose: boolean
    reasoning: boolean
    inject_date: boolean
    memory: boolean
  }
  suggested_tools: string[]
  max_iter: number
}
```

**Patrón a seguir:** ToolMultiSelect.tsx (líneas 42-59) — búsqueda con useMemo + filtrado por texto.

**Imports requeridos:**
```typescript
'use client'
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, X } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
```

**Funcionalidad:**
1. Fetch templates desde `GET /api/templates` (useQuery)
2. Grid de cards con nombre, descripción, categoría, tools sugeridas
3. Chips de filtro por categoría (Research, Development, Support, General)
4. Barra de búsqueda por nombre
5. Botón "Use Template" que llama `onSelect(template)` + cierra modal

---

### Integración con AgentForm

**Prop a agregar en AgentForm.tsx:**
```typescript
interface AgentFormProps {
  onSave?: (data: AgentFormData) => Promise<void>
  onClear?: () => void
  initialValues?: Partial<AgentFormData>
  // Nueva prop:
  externalValues?: Partial<AgentFormData>  // para when TemplatePicker selecciona
}
```

**Uso de setValue para auto-rellenar:**
```typescript
// En AgentForm, useEffect para aplicar externalValues
useEffect(() => {
  if (externalValues) {
    setValue('role', externalValues.role ?? '')
    setValue('goal', externalValues.goal ?? '')
    setValue('backstory', externalValues.backstory ?? '')
    setValue('llmProvider', externalValues.llmProvider ?? 'groq')
    setValue('llmModel', externalValues.llmModel ?? 'llama-3.1-70b-versatile')
    setValue('allowedTools', externalValues.allowedTools ?? [])
    setValue('maxIter', externalValues.maxIter ?? 3)
    setValue('verbose', externalValues.verbose ?? false)
    setValue('reasoning', externalValues.reasoning ?? false)
    setValue('injectDate', externalValues.injectDate ?? false)
    setValue('memory', externalValues.memory ?? false)
  }
}, [externalValues])
```

**Falta en AgentForm actual:** No hay prop `externalValues`. El plan dice "Use Template → rellena el formulario". La implementación más limpia es pasar `initialValues` actualizado cuando el usuario selecciona un template, O agregar un nuevo prop. **Recomendación:** usar `initialValues` ya existente, actualizándolo cuando el usuario selecciona template.

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints Involucrados

| Endpoint | Método | Input | Output | Auth |
|---|---|---|---|---|
| `/api/templates` | GET | `?category=` opcional | `{templates: TemplateInfo[], count: number}` | None |
| `/api/templates/{id}` | GET | template_id (path) | TemplateDetailResponse | None |

### Estructura de Respuesta

**GET /api/templates (listado):**
```typescript
// TemplateInfo (templates.py:25-33)
{
  id: string
  name: string
  description: string | null
  category: string
  suggested_tools: string[]  // tools del template
  max_iter: number
  is_system: boolean
  created_at: string | null
}
```

**GET /api/templates/{id} (detalle):**
```typescript
// TemplateDetailResponse (templates.py:41-51)
{
  id: string
  name: string
  description: string | null
  category: string
  soul_json: {
    goal: string
    backstory: string
    llm_provider: string
    llm_model: string
    verbose: boolean
    reasoning: boolean
    inject_date: boolean
    memory: boolean
  }
  suggested_tools: string[]
  max_iter: number
  is_system: boolean
  created_at: string | null
  updated_at: string | null
}
```

### Mapeo soul_json → AgentFormData

| Campo TemplateDetailResponse.soul_json | Campo AgentFormData |
|---|---|
| goal | goal |
| backstory | backstory |
| llm_provider | llmProvider |
| llm_model | llmModel |
| verbose | verbose |
| reasoning | reasoning |
| inject_date | injectDate |
| memory | memory |

| Campo TemplateDetailResponse | Campo AgentFormData |
|---|---|
| - | role (NO existe en template - usuario debe ingresar) |
| suggested_tools | allowedTools |
| max_iter | maxIter |

**Nota importante:** El template NO incluye `role`. El usuario debe ingresarlo manualmente después de seleccionar template. Esto es correcto porque role es el identificador único del agente en la org, mientras que el template define la configuración base.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo End-to-End

```
Usuario → /builder → Click "Templates" → Modal TemplatePicker abre
    → GET /api/templates → retorna templates
    → Usuario filtra por categoría / busca por nombre
    → Usuario click "Use Template"
    → Modal cierra
    → AgentForm se rellena con soul_json del template
    → Usuario ingresa/ajusta role (obligatorio)
    → Usuario click "Save Agent" → POST /agents
```

### Puntos Críticos

1. **Seed no ejecutado:** Si `fap templates seed` no se ejecutó, el endpoint retorna array vacío. TemplatePicker mostraría "No templates found".
2. **Role obligatorio:** El template no tiene role. AgentForm valida role requerido. Usuario debe ingresarlo.
3. **Categoría del template:** Se muestra como Badge en la card.
4. **Tools sugeridas:** Se muestran como badges, pero NO se auto-seleccionan (usuario debe confirmarlas).

### Gaps/Ambigüedades

| Gap | Resolución Propuesta |
|---|---|
| Botón "Templates" no existe en UI actual | Crear botón en BuilderLayout header, cerca del título "Agent Configuration" |
| No hay estado para controlar modal | TemplatePicker maneja su propio `open` state, o recibe `open`/`onOpenChange` como props |
| TemplatePicker acceso a AgentForm | Pasando función `onSelect` que actualiza estado en BuilderLayout, el cual pasa `initialValues` a AgentForm |

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: `fap templates validate`
- **Qué automatiza:** Verificar que los templates en DB son válidos y tienen todos los campos requeridos para el builder
- **Tipo:** CLI command
- **Cómo se usa:** `fap templates validate [--verbose]` — checkea soul_json tiene campos requeridos, suggested_tools es array, category válida
- **Impacto para el usuario final:** Antes de abrir el builder, el admin puede validar que el seed fue correcto y los templates son usables
- **Prioridad:** Tarea 2 — después de crear TemplatePicker, antes de integrar en UI
```

**Justificación:** TemplatePicker depende de datos válidos en DB. Si seed ejecutó con datos malformados, el builder fallará silenciosamente (cards vacías o errores). Esta herramienta permite diagnóstico rápido.

---

## 5️⃣ Criterios de Aceptación

| # | Criterio | Tipo | Verificable |
|---|---|---|---|
| ✅ | TemplatePicker.tsx existe en dashboard/components/builder/ | CODE | ✅ |
| ✅ | GET /api/templates devuelve array de templates | BACKEND | ✅ |
| ✅ | Cards muestran: nombre, descripción, categoría, tools sugeridas | FULLSTACK | ✅ |
| ✅ | Click "Use Template" → AgentForm se rellena con soul_json | FULLSTACK | ✅ |
| ✅ | Filtro por categoría funciona (chips: Research/Development/Support/General) | FULLSTACK | ✅ |
| ✅ | Barra de búsqueda filtra por nombre | FULLSTACK | ✅ |
| ✅ | Loading state mientras carga templates | FULLSTACK | ✅ |
| ✅ | Error state si endpoint falla | FULLSTACK | ✅ |
| ✅ | Botón "Templates" visible en builder UI | FULLSTACK | ✅ |
| ✅ | Modal abre/cierra correctamente | FULLSTACK | ✅ |
| ✅ | [DX] fap templates validate ejecuta sin errores | DX | ✅ |

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Seed de templates no ejecutado → UI vacía | Alta | Admin no ejecutó `fap templates seed` | Documentar en setup del builder, agregar check en UI |
| Template sin role → usuario confundido | Media | Diseño: template no incluye role (es único por org) | Agregar placeholder "Enter role name..." al auto-rellenar |
| soul_json malformado en DB → crash UI | Media | Seed con datos incompletos | Validar en `fap templates validate` (herramienta propuesta) |
| Categorías mismatch con chips hardcodeados | Baja | Filter chips no coinciden categories en DB | Obtener categorías dinámicas desde endpoint, no hardcodear |
| Large número de templates → perf degradada | Baja | Sin paginación en endpoint | Agregar limit/offset si >50 templates |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: `fap templates validate` | `src/cli/commands/templates_validate.py` | `def validate_templates(org_id: str, verbose: bool) -> int` | `templates_seed.py` | DX | Media | 1h | Ninguna | → verificar: `uv run python -m src.cli.main templates validate` ejecuta |
| 1 | Crear componente TemplatePicker | `dashboard/components/builder/TemplatePicker.tsx` | `export function TemplatePicker({ onSelect, open, onOpenChange }: TemplatePickerProps)` | `ToolMultiSelect.tsx` (búsqueda/filtro) | CODE | Media | 2h | Tarea 0 (opcional) | → verificar: importable desde `dashboard/components/builder/` sin error |
| 2 | Integrar TemplatePicker en BuilderLayout | `dashboard/components/builder/BuilderLayout.tsx` | Agregar estado `selectedTemplate` + botón "Templates" + pasar `initialValues` a AgentForm | `BuilderLayout.tsx` | FULLSTACK | Baja | 1h | Tarea 1 | → verificar: click "Templates" abre modal |
| 3 | Modificar AgentForm para recibir initialValues actualizados | `dashboard/components/builder/AgentForm.tsx` | Agregar `useEffect` que aplique `initialValues` cuando cambian (sin reset completo) | `AgentForm.tsx:171-176` (useEffect existente) | FULLSTACK | Baja | 0.5h | Ninguna | → verificar: selecting template rellena formulario |
| 4 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-3 | → verificar: criteria §5 todos pasan |

**Tiempo total estimado:** 5 horas

---

## 🔮 Roadmap (NO implementar ahora)

- **Paginación de templates:** Si >20 templates, agregar limit/offset en endpoint + load more en UI
- **Categorías dinámicas:** Obtener categorías únicas de DB en lugar de hardcode: `SELECT DISTINCT category FROM agent_templates`
- **Preview de template:** Modal detallado con toda la config del template antes de seleccionar
- **Custom templates:** Post-MVP, permitir a usuarios crear sus propios templates (requiere agregar org_id a tabla)

---

## 🚫 Reglas de Oro — Verificación post-análisis

- ✅ Análisis accionable y específico — sí
- ✅ TODO verificado contra código — 22 elementos verificados
- ✅ Discrepancias detectadas — 1 (seed no verificado live)
- ✅ Secciones completadas — 8 secciones (0-7)
- ✅ Etapas cubiertas — 4 etapas (data, code, backend, fullstack+DX)
- ✅ Criterios de aceptación — 11 verificables
- ✅ Riesgos identificados — 5 (2 altas, 2 medias, 1 baja)
- ✅ Tareas atómicas — 4 artefactos (TemplatePicker, BuilderLayout update, AgentForm update, CLI validate)
- ✅ Interfaz exacta por tarea — sí
- ✅ Patrón de referencia explícito — ToolMultiSelect.tsx, templates_seed.py, BuilderLayout.tsx
- ✅ Verificación inline por tarea — sí
- ✅ Suposiciones no verificadas — 1 (seed ejecutado en Supabase) ⚠️
- ✅ Propuesta DX / Tooling — `fap templates validate`
- ✅ Estimación de tiempo — 5h total

---

**IDIOMA:** Español 🇪🇸

**AGENTE:** mm

**PASO:** 05

**FECHA:** 2026-05-14