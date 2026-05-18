# Análisis Técnico — Paso 14: Optimización de UX y Rendimiento Frontend

**Agente:** mm
**Paso:** 14
**Fecha:** 2026-05-18

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `useClickOutside` hook en ToolMultiSelect | grep en `ToolMultiSelect.tsx` | ✅ | Línea 32-40: handleClickOutside con mousedown event |
| 2 | useEffect en AgentForm | grep en `AgentForm.tsx` | ✅ | Líneas 98-114, 120-122, 224-229 |
| 3 | ReactFlow import dinámico | grep en `CrewCanvas.tsx` | ❌ | Línea 48: import directo, NO hay dynamic import |
| 4 | useMemo en cálculos de payload | grep en `CrewCanvas.tsx` | ✅ | Líneas 207-218: useMemo para exportPayload |
| 5 | cmdk instalado | grep en `package.json` | ❌ | NO existe en dependencies |
| 6 | debounce en búsqueda | grep en `TemplatePicker.tsx`, `ToolMultiSelect.tsx` | ❌ | Sin debounce, onChange directo |
| 7 | lib/template-mapper.ts existe | glob en `lib/` | ❌ | NO existe, función en BuilderLayout.tsx líneas 28-50 |
| 8 | Fallback portapapeles | grep en `ExportDialog.tsx` | ✅ | Líneas 92-98: fallback con toast |
| 9 | Query params para navegación | grep en `BuilderTabContext.tsx` | ❌ | Solo useState, NO sincroniza con URL |
| 10 | Métodos HTTP centralizados | grep en `api.ts` | ✅ | Líneas 96-118: get, post, put, patch, delete |
| 11 | Constantes métodos HTTP | grep en `constants.ts` | ❌ | NO hay constantes para métodos HTTP |
| 12 | Dynamic import ReactFlow en page | grep en `builder/page.tsx` | ❌ | Import directo de componentes |

**Discrepancias encontradas:**

1. **D1 - ReactFlow no usa carga diferida:** El CSS de ReactFlow (`reactflow/dist/style.css`) se importa directamente en `CrewCanvas.tsx:48`, no hay `next/dynamic` en la página. Esto incrementa el bundle inicial. **Resolución:** Implementar dynamic import con ssr: false en `builder/page.tsx`.

2. **D2 - Sin debounce en campos de búsqueda:** `TemplatePicker.tsx:155` y `ToolMultiSelect.tsx:113` usan `onChange` directo sin debounce, causando re-renders excesivos en cada keystroke. **Resolución:** Crear hook `useDebounce` o instalar `use-debounce`.

3. **D3 - Query params no sincronizados:** `BuilderTabContext.tsx` usa solo `useState` interno. No hay sincronización con `useSearchParams`, impidiendo deep linking a pestañas específicas. **Resolución:** Integrar `useSearchParams` de Next.js.

4. **D4 - Mapeo template no extraído:** La función `mapTemplateToFormValues` está hardcodeada en `BuilderLayout.tsx:28-50`. Debería estar en `lib/template-mapper.ts` para reutilización. **Resolución:** Extraer a módulo dedicado.

5. **D5 - cmdk no instalado:** El package.json no incluye `cmdk` (command palette). La tarea ID-021 menciona evaluar migración a cmdk pero no se ha instalado. **Resolución:** Evaluar necesidad real vs usar componentes actuales.

6. **D6 - Constantes HTTP faltantes:** No hay constantes para métodos HTTP en `constants.ts`. Los strings 'GET', 'POST', etc. están hardcodeados en `api.ts`. **Resolución:** Agregar enum HTTP_METHODS a constants.ts.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**No aplica** — Este paso no modifica schema de DB ni estructuras de datos. Es puramente optimización de frontend.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes nuevos/modificados

| Componente | Estado | Cambios necesarios |
|---|---|---|
| `hooks/useClickOutside.ts` | 🔴 No existe | Crear hook reutilizable |
| `hooks/useDebounce.ts` | 🔴 No existe | Crear hook para búsqueda |
| `lib/template-mapper.ts` | 🔴 No existe | Extraer de BuilderLayout |
| `lib/constants.ts` | 🟡 Parcial | Agregar HTTP_METHODS |
| `BuilderTabContext.tsx` | 🔴 No implementado | Integrar useSearchParams |
| `builder/page.tsx` | 🔴 No implementado | Dynamic import ReactFlow |

### Firmas requeridas

```typescript
// hooks/useClickOutside.ts
export function useClickOutside(
  ref: RefObject<HTMLElement>,
  handler: (event: MouseEvent | TouchEvent) => void
): void

// hooks/useDebounce.ts
export function useDebounce<T>(value: T, delay: number): T

// lib/template-mapper.ts
export function mapTemplateToFormValues(template: TemplateDetail): AgentFormData
export type TemplateDetail = { ... }

// lib/constants.ts
export const HTTP_METHODS = {
  GET: 'GET',
  POST: 'POST',
  PUT: 'PUT',
  PATCH: 'PATCH',
  DELETE: 'DELETE',
} as const
```

### Patrones a seguir

- **Hook pattern:** Ver `hooks/useCurrentOrg.ts` para estructura de hooks con contexto
- **Dynamic import:** Ver cómo otros componentes en dashboard usan `next/dynamic`
- **Template mapping:** Ver `BuilderLayout.tsx:28-50` para lógica actual a extraer

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**No aplica** — Este paso no modifica APIs ni backend. Es puramente optimización de frontend.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo actual

```
Page /builder
  → BuilderTabProvider (useState interno)
    → BuilderLayout
      → AgentForm / CrewCanvas / TemplatePicker
```

### Problemas identificados

1. **Sin deep linking:** Cambiar de pestaña no actualiza URL, no se puede compartir enlace directo
2. **Performance:** Bundle de ReactFlow carga inmediatamente aunque usuario no use canvas
3. **UX búsqueda:** Cada keystroke dispara re-render en TemplatePicker y ToolMultiSelect
4. **Modularidad:** Lógica de mapeo duplicada si se necesita en otros lugares

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: useDebounce hook + useClickOutside hook
- **Qué automatiza:** Re-renders innecesarios en componentes de búsqueda y cierre de dropdowns
- **Tipo:** hooks reutilizables
- **Cómo se usa:** 
  ```tsx
  const debouncedSearch = useDebounce(search, 300)
  useClickOutside(ref, () => setOpen(false))
  ```
- **Impacto para el usuario final:** UI más responsiva, especialmente en dispositivos lentos
- **Prioridad:** Tarea 0 — implementar antes que el resto del paso
```

### Propuesta alternativa: CLI de diagnóstico

```
### Herramienta Propuesta: Builder Performance Diagnostic
- **Qué automatiza:** Detecta problemas de render en componentes del builder
- **Tipo:** script de análisis estático
- **Cómo se usa:** npm run diagnose:builder
- **Impacto para el desarrollador:** Identificar componentes sin memoización, hooks con dependencias faltantes
- **Prioridad:** Baja — no bloqueante
```

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] Hook useClickOutside exportado desde hooks/useClickOutside.ts
✅ [CODE] Hook useDebounce exportado desde hooks/useDebounce.ts
✅ [CODE] función mapTemplateToFormValues exportada desde lib/template-mapper.ts
✅ [CODE] Constante HTTP_METHODS agregada a lib/constants.ts
✅ [FULLSTACK] Query params sincronizados: ?tab=agent-form actualiza pestaña
✅ [FULLSTACK] Deep linking funcional: compartir URLtab=crew-canvas abre pestaña correcta
✅ [CODE] ReactFlow carga con dynamic import ssr:false
✅ [CODE] useMemo aplicado en búsqueda de TemplatePicker con debounce
✅ [DX] Hooks useClickOutside y useDebounce usados en ToolMultiSelect
✅ [DX] useEffect en AgentForm tiene dependencias correctas (sin warnings de eslint)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Romper navegación al agregar query params | Alta | Cambios en BuilderTabContext pueden afectar routing existente | Testear con navegación manual + verificar no hay conflictos con otros params |
| Dynamic import rompe SSR de otros componentes | Media | ReactFlow tiene dependencias que fallan en servidor | Usar ssr: false y verificar loading states |
| Hooks nuevos causan regresiones en otros componentes | Media | Si se cambian signatures de otros hooks | Crear como funciones nuevas, no modificar existentes |
| Debounce afecta UX de búsqueda instantánea | Baja | 300ms delay puede sentirse lento | Permitir configuración de delay, default 300ms |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Crear hooks useClickOutside y useDebounce | `dashboard/hooks/useClickOutside.ts`, `dashboard/hooks/useDebounce.ts` | `useClickOutside(ref, handler)`, `useDebounce(value, delay)` | `hooks/useCurrentOrg.ts` | DX | Baja | 0.5h | Ninguna | → verificar: `tsc --noEmit` sin errores |
| 1 | Extraer mapping a lib/template-mapper.ts | `dashboard/lib/template-mapper.ts` | `mapTemplateToFormValues(template: TemplateDetail): AgentFormData` | `BuilderLayout.tsx:28-50` | CODE | Baja | 0.5h | Tarea 0 | → verificar: importable desde `lib/template-mapper.ts` |
| 2 | Agregar HTTP_METHODS a constants.ts | `dashboard/lib/constants.ts` | `HTTP_METHODS = { GET, POST, PUT, PATCH, DELETE }` | `constants.ts` existentes | CODE | Baja | 0.25h | Ninguna | → verificar: usar constante en api.ts sin errores |
| 3 | Implementar Query Params en BuilderTabContext | `dashboard/components/builder/BuilderTabContext.tsx` | `useSearchParams()` + `useRouter()` | Navigation existente del dashboard | FULLSTACK | Media | 1h | Ninguna | → verificar: navegar a ?tab=crew-canvas cambia pestaña |
| 4 | Dynamic import de ReactFlow | `dashboard/app/(app)/builder/page.tsx` | `dynamic(() => import(...), { ssr: false })` | pattern de otros dynamic imports en dashboard | CODE | Media | 0.5h | Tarea 1 | → verificar: `npm run build` succeeds |
| 5 | Aplicar debounce en búsquedas | `TemplatePicker.tsx`, `ToolMultiSelect.tsx` | `useDebounce(search, 300)` | TemplatePicker actual | CODE | Baja | 0.5h | Tarea 0 | → verificar: eslint warnings reducidos |
| 6 | Corregir dependencias de useEffect en AgentForm | `AgentForm.tsx` | useEffect con array de dependencias correcto | ESLint exhaustive-deps | CODE | Baja | 0.25h | Ninguna | → verificar: `npm run lint` sin warnings |
| 7 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-6 | → verificar: criterios §5 pasan |

**Tiempo total estimado:** 4 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Integrar `cmdk` si se decide migración de herramientas (evaluar necesidad real primero)
- Agregar诊断 CLI para detectar problemas de render en builder
- Considerar React.memo para nodos de AgentNode/TaskNode en canvas
- Evaluar Zustand o similar para estado global del builder si cresce

---

## 🚫 Reglas de Oro

- ✅ **Análisis accionable y específico**, no genérico
- ✅ **TODO verificado contra código**, no supuestos
- ✅ **Si algo no está definido** → señalarlo como ambigüedad + resolución concreta
- ✅ **Si el plan contradice el código** → el código gana + documentar discrepancia
- ✅ **Nivel CTO exigente** en rigor y profundidad
- ✅ **Coherente con phase-state.md** — no perder decisiones ya tomadas
- ✅ **TODO el paso**, incluyendo sub-pasos
- ✅ **Etapas secuenciales** — data → code → backend → fullstack+DX, sin saltar
- ✅ **≥ 1 herramienta DX propuesta** — siempre, sin excepción
- ✅ **Tareas atómicas**: una tarea = un artefacto = interfaz completa = patrón explícito = verificación inline
- ✅ **El implementador no decide nada**: si debe inferir cualquier detalle de diseño → la tarea está incompleta