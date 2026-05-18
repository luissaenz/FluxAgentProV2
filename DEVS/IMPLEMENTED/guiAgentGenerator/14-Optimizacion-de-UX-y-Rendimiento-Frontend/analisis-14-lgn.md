# Análisis Técnico — Paso 14: Optimización de UX y Rendimiento Frontend

**Agente:** lgn  
**Paso:** 14  
**Fecha:** 2026-05-18

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | ReactFlow dynamic import en BuilderCanvas | grep en `BuilderCanvas.tsx` | ✅ | Líneas 3-8: `dynamic(() => import('@/components/builder/CrewCanvas'), { ssr: false })` |
| 2 | ReactFlow CSS lazy loading | grep en `CrewCanvas.tsx` | ⚠️ | Línea 48: import estático `'reactflow/dist/style.css'` dentro del componente cliente |
| 3 | useEffect con dependencias en AgentForm | grep en `AgentForm.tsx` | ✅ | Líneas 98-114, 120-122, 224-229 - todos tienen arrays de dependencias correctos |
| 4 | useMemo en cálculos de payload | grep en `CrewCanvas.tsx` | ✅ | Líneas 207-218, 209: `useMemo` para `exportPayload`, `fullGraphJson` |
| 5 | cmdk instalado | grep en `package.json` | ❌ | NO existe en dependencies del frontend |
| 6 | debounce en búsqueda | grep en `TemplatePicker.tsx`, `ToolMultiSelect.tsx` | ❌ | onChange directo sin debounce en ambos archivos |
| 7 | lib/template-mapper.ts existe | glob en `lib/` | ❌ | NO existe - función `mapTemplateToFormValues` hardcodeada en `BuilderLayout.tsx:28-50` |
| 8 | Fallback portapapeles | grep en `ExportDialog.tsx` | ✅ | Líneas 92-98: fallback con toast y duration 10000ms |
| 9 | Query params para navegación | grep en `BuilderTabContext.tsx` | ❌ | Solo `useState`, NO sincroniza con `useSearchParams` |
| 10 | Métodos HTTP centralizados en constants | grep en `constants.ts` | ❌ | NO hay `HTTP_METHODS` - solo constants de UI existentes |
| 11 | Hook useClickOutside existe | glob en `hooks/` | ❌ | NO existe - implementación inline en `ToolMultiSelect.tsx:32-40` |
| 12 | Hook useDebounce existe | glob en `hooks/` | ❌ | NO existe |

**Discrepancias encontradas:**

1. **D1 - CSS de ReactFlow no lazy:** El CSS `'reactflow/dist/style.css'` se importa estáticamente en `CrewCanvas.tsx:48` dentro del bloque de imports. Aunque CrewCanvas ya es cargado dinámicamente vía `BuilderCanvas`, el CSS se incluye en el bundle del componente padre. **Resolución:** Mover el import CSS dentro de un `useEffect` o usar dynamic import del CSS.

2. **D2 - Sin debounce en búsqueda:** `TemplatePicker.tsx:155` (`setSearch(e.target.value)`) y `ToolMultiSelect.tsx:113` (`setSearch(e.target.value)`) usan onChange directo sin debounce, causando re-renders en cada keystroke. **Resolución:** Crear hook `useDebounce` o instalar librería `use-debounce`.

3. **D3 - Query params no sincronizados:** `BuilderTabContext.tsx` usa solo `useState` interno. No hay sincronización con `useSearchParams` de Next.js, impidiendo deep linking a pestañas específicas. **Resolución:** Integrar `useSearchParams` y `useRouter` para sincronizar `?tab=agent-form|crew-canvas`.

4. **D4 - Mapeo template no extraído:** La función `mapTemplateToFormValues` está hardcodeada en `BuilderLayout.tsx:28-50`. Debería estar en `lib/template-mapper.ts` para reutilización. **Resolución:** Extraer a módulo dedicado.

5. **D5 - cmdk no instalado:** El package.json del frontend no incluye `cmdk`. La tarea ID-021 menciona evaluar migración pero no se ha instalado. **Resolución:** Evaluar necesidad real - los componentes actuales funcionan sin cmdk.

6. **D6 - Constantes HTTP faltantes:** No hay constantes para métodos HTTP en `constants.ts`. Los strings 'GET', 'POST', etc. están hardcodeados en `api.ts`. **Resolución:** Agregar `HTTP_METHODS` a constants.ts.

7. **D7 - Hook useClickOutside no reutilizable:** La lógica está inline en `ToolMultiSelect.tsx:32-40` con `useEffect` + `handleClickOutside`. Debería ser un hook reutilizable. **Resolución:** Crear `hooks/useClickOutside.ts`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

**No aplica** — Este paso no modifica schema de DB ni estructuras de datos. Es puramente optimización de frontend.

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Componentes nuevos requeridos

| Componente | Estado | Acción necesaria |
|---|---|---|
| `hooks/useClickOutside.ts` | 🔴 No existe | Crear hook reutilizable extraído de ToolMultiSelect |
| `hooks/useDebounce.ts` | 🔴 No existe | Crear hook para búsqueda |
| `lib/template-mapper.ts` | 🔴 No existe | Extraer `mapTemplateToFormValues` de BuilderLayout |
| `lib/constants.ts` | 🟡 Parcial | Agregar `HTTP_METHODS` |
| `BuilderTabContext.tsx` | 🔴 No implementado | Integrar useSearchParams para sync URL |

### Firmas requeridas

```typescript
// hooks/useClickOutside.ts
export function useClickOutside<T extends HTMLElement>(
  ref: RefObject<T>,
  handler: (event: MouseEvent | TouchEvent) => void
): void

// hooks/useDebounce.ts
export function useDebounce<T>(value: T, delay: number): T

// lib/template-mapper.ts
export function mapTemplateToFormValues(template: TemplateDetail): AgentFormData
export type TemplateDetail = { ... } from '@components/builder/TemplatePicker'

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
- **Template mapping:** Ver `BuilderLayout.tsx:28-50` para lógica actual a extraer

---

## 3️⃣ Análisis de Backend (ETAPA 3)

**No aplica** — Este paso no modifica APIs ni backend.

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Flujo actual

```
Page /builder (page.tsx)
  → BuilderTabProvider
    → BuilderLayout (Tabs con useState interno)
      → AgentForm / CrewCanvas / TemplatePicker
```

### Problemas identificados

1. **Sin deep linking:** Cambiar de pestaña no actualiza URL (?tab=agent-form), no se puede compartir enlace directo
2. **Performance:** CSS de ReactFlow se carga con el bundle del componente, no diferido
3. **UX búsqueda:** Cada keystroke dispara re-render en TemplatePicker y ToolMultiSelect
4. **Modularidad:** Lógica de mapeo duplicada si se necesita en otros lugares

### DX & Tooling (OBLIGATORIO)

```
### Herramienta Propuesta: useDebounce + useClickOutside hooks
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

---

## 5️⃣ Criterios de Aceptación

```
✅ [CODE] Hook useClickOutside exportado desde hooks/useClickOutside.ts
✅ [CODE] Hook useDebounce exportado desde hooks/useDebounce.ts
✅ [CODE] función mapTemplateToFormValues exportada desde lib/template-mapper.ts
✅ [CODE] Constante HTTP_METHODS agregada a lib/constants.ts
✅ [FULLSTACK] Query params sincronizados: ?tab=agent-form actualiza pestaña
✅ [FULLSTACK] Deep linking funcional: compartir URL?tab=crew-canvas abre pestaña correcta
✅ [CODE] ReactFlow CSS cargado de forma diferida (dinámico o en useEffect)
✅ [CODE] useMemo aplicado en búsqueda de TemplatePicker con debounce
✅ [DX] Hooks useClickOutside y useDebounce usados en ToolMultiSelect
✅ [DX] useEffect en AgentForm tiene dependencias correctas (sin warnings de eslint)
```

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Romper navegación al agregar query params | Alta | Cambios en BuilderTabContext pueden afectar routing existente | Testear con navegación manual + verificar no hay conflictos con otros params |
| Dynamic import de CSS rompe styles | Media | ReactFlow tiene dependencias CSS específicas | Usar CSS Modules o cargar condicionalmente con verificación |
| Hooks nuevos causan regresiones | Media | Si se cambian signatures de otros hooks | Crear como funciones nuevas, no modificar existentes |
| Debounce afecta UX de búsqueda instantánea | Baja | 300ms delay puede sentirse lento | Permitir configuración de delay, default 300ms |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a segvir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: Crear hooks useClickOutside y useDebounce | `dashboard/hooks/useClickOutside.ts`, `dashboard/hooks/useDebounce.ts` | `useClickOutside<T>(ref, handler)`, `useDebounce<T>(value, delay)` | `hooks/useCurrentOrg.ts` | DX | Baja | 0.5h | Ninguna | → verificar: `tsc --noEmit` sin errores |
| 1 | Extraer mapping a lib/template-mapper.ts | `dashboard/lib/template-mapper.ts` | `mapTemplateToFormValues(template: TemplateDetail): AgentFormData` | `BuilderLayout.tsx:28-50` | CODE | Baja | 0.5h | Tarea 0 | → verificar: importable desde `lib/template-mapper.ts` |
| 2 | Agregar HTTP_METHODS a constants.ts | `dashboard/lib/constants.ts` | `HTTP_METHODS = { GET, POST, PUT, PATCH, DELETE }` | `constants.ts` existentes | CODE | Baja | 0.25h | Ninguna | → verificar: usar constante en api.ts sin errores |
| 3 | Implementar Query Params en BuilderTabContext | `dashboard/components/builder/BuilderTabContext.tsx` | `useSearchParams()` + `useRouter()` integrado | Context API existente + Next.js routing | FULLSTACK | Media | 1h | Ninguna | → verificar: navegar a ?tab=crew-canvas cambia pestaña |
| 4 | Dynamic import de CSS ReactFlow | `dashboard/components/builder/CrewCanvas.tsx` | CSS import condicional con verificación cliente | pattern de dynamic CSS loading | CODE | Media | 0.5h | Tarea 1 | → verificar: `npm run build` succeeds |
| 5 | Aplicar debounce en búsquedas | `TemplatePicker.tsx`, `ToolMultiSelect.tsx` | `useDebounce(search, 300)` | TemplatePicker actual | CODE | Baja | 0.5h | Tarea 0 | → verificar: eslint warnings reducidos |
| 6 | Validar flujo end-to-end | — | — | — | FULLSTACK | Baja | 0.5h | Tareas 1-5 | → verificar: criterios §5 pasan |

**Tiempo total estimado:** 3.75 horas

---

## 🔮 Roadmap (NO implementar ahora)

- Integrar `cmdk` si se decide migración de herramientas (evaluar necesidad real)
- Agregar diagnóstico CLI para detectar problemas de render en builder
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