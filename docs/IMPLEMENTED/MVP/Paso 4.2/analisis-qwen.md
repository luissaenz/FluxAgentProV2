# Análisis Técnico — Paso 4.2: Implementar `FlowHierarchyView.tsx`

## 1. Diseño Funcional

### Happy Path
1. El usuario navega a la página de Workflows (`/workflows`).
2. El componente `FlowHierarchyView` carga automáticamente la jerarquía de flows desde `GET /flows/hierarchy`.
3. Se visualiza un árbol colapsable agrupado por categorías (`ventas`, `operaciones`, `system`, `sin_categoria`).
4. Cada nodo de flow muestra:
   - Nombre formateado del flow (vía `formatFlowType`).
   - Badge de categoría si aplica.
   - Dependencias upstream ("Depende de: ...") con badges clickeables.
   - Dependencias downstream ("Requerido por: ...") calculadas dinámicamente.
   - Indicador visual si es un flow independiente (sin dependencias).
5. El usuario puede colapsar/expandir categorías individualmente.
6. Los badges de dependencia son visuales (no navegación — MVP).

### Edge Cases
- **Sin flows registrados:** El componente muestra un empty state con ícono `FolderTree` y mensaje "Sin jerarquía de flows".
- **Error de red/API:** Muestra un card con borde rojo (`border-destructive/50`), ícono `AlertCircle` y el mensaje de error.
- **Loading skeleton:** Mientras carga, muestra 3 skeletons de altura fija para evitar layout shift.
- **Dependencias huérfanas:** Si un flow depende de un flow que no existe en el registry, el badge de dependencia se muestra igual pero el endpoint ya reporta esto en `validation.invalid_dependencies` (Paso 4.1). **MVP:** No se visualiza la advertencia de validación en UI — se deja para roadmap.
- **Ciclos detectados:** Similar al anterior, el backend ya los detecta pero la UI no los renderiza explícitamente en MVP.

### Manejo de Errores (lo que ve el usuario)
| Escenario | Comportamiento Visual |
|-----------|----------------------|
| Timeout de API (>30s) | Skeleton persistente → error card con mensaje genérico de timeout |
| 401/403 | El middleware de auth redirige a login — no maneja el componente |
| 500 del backend | Error card con "Error al cargar la jerarquía" + mensaje técnico |
| Respuesta vacía `{}` | Empty state con ícono y texto informativo |

---

## 2. Diseño Técnico

### Estado Actual
El componente `FlowHierarchyView.tsx` **ya existe** y está completamente implementado en:
```
dashboard/components/flows/FlowHierarchyView.tsx
```

Contiene 3 componentes internos:
- **`FlowHierarchyView`** — Componente principal con React Query.
- **`CategoryTree`** — Sección colapsable por categoría.
- **`FlowNode`** — Nodo individual con dependencias upstream/downstream.

### Lo que falta: Integración
El componente **no está importado ni renderizado en ninguna página**. El paso 4.2 se considera completo cuando:

1. **Se integra en la página de Workflows** (`/workflows/page.tsx`) como una sección adicional debajo del grid de workflows, O
2. **Se crea una página dedicada** (`/workflows/hierarchy`) accesible desde un tab o botón.

**Decisión para MVP:** Integrarlo en la página principal de `/workflows` como una sección inferior. Es el enfoque más simple y no requiere nuevas rutas.

### Componentes y Dependencias

| Elemento | Origen | Estado |
|----------|--------|--------|
| `FlowHierarchyView.tsx` | `dashboard/components/flows/` | ✅ Implementado |
| `FlowHierarchyNode` type | `dashboard/lib/types.ts` | ✅ Definido |
| `FlowHierarchyResponse` type | `dashboard/lib/types.ts` | ✅ Definido |
| `GET /flows/hierarchy` | `src/api/routes/flows.py` | ✅ Operativo |
| `formatFlowType` | `dashboard/lib/presentation/fallback.ts` | ✅ Disponible |
| `useQuery` (React Query) | `@tanstack/react-query` | ✅ Instalado |
| shadcn/ui (Card, Badge, etc.) | `dashboard/components/ui/` | ✅ Instalados |
| lucide-react icons | `lucide-react` | ✅ Instalados |

**No se requieren nuevas dependencias.**

### Interfaz de Datos

**Input:** Ninguno (el componente hace fetch autónomo con `queryKey: ['flows-hierarchy']`).

**Output:** Renderizado visual de árbol jerárquico.

**Contrato con backend (ya vigente):**
```ts
interface FlowHierarchyResponse {
  hierarchy: Record<string, FlowHierarchyNode>
  categories: Record<string, string[]>
  validation: { invalid_dependencies: Dict, cycles: List }
}
```

El componente actual **no usa el campo `validation`** — solo renderiza `hierarchy` y `categories`. Esto es correcto para MVP.

---

## 3. Decisiones

### D1: Integración en `/workflows` vs página dedicada
**Decisión:** Integrar `FlowHierarchyView` como sección inferior en la página existente de `/workflows`, debajo del grid de templates.

**Justificación:**
- No requiere crear nueva ruta ni actualizar sidebar/navegación.
- El contexto natural de la jerarquía es junto a los workflows — el usuario que gestiona workflows quiere ver cómo se relacionan.
- Menor superficie de cambio, menor riesgo.
- Si en el futuro se necesita una vista dedicada (ej. con zoom, pan, interactividad avanzada), se puede extraer sin romper nada.

### D2: No mostrar advertencias de validación en MVP
**Decisión:** Los campos `validation.invalid_dependencies` y `validation.cycles` del endpoint NO se visualizan en esta iteración.

**Justificación:**
- El endpoint ya los calcula (Paso 4.1) y los reporta en logs del servidor.
- Para MVP, que el árbol se renderice correctamente es suficiente.
- Mostrar warnings visuales de ciclos/huérfanos añade complejidad de UI que no bloquea el valor central: ver la jerarquía.

### D3: No hacer los badges de dependencia clickeables (sin navegación)
**Decisión:** Los badges de "Depende de" y "Requerido por" son puramente visuales, no navegan al nodo dependiente.

**Justificación:**
- Conectar badges a scroll/navegación entre nodos requiere estado global o hash-based routing.
- Para MVP, la visibilidad de la relación es suficiente.
- Se puede añadir highlight-on-hover o scroll-to-node en roadmap sin cambiar el componente base.

### D4: Stale time de 60 segundos
**Decisión:** Mantener `staleTime: 60_000` ya configurado en el hook.

**Justificación:** La jerarquía de flows cambia muy raramente (solo al registrar nuevos flows o modificar dependencias en código). 60s es conservador y apropiado. No necesita refetch automático agresivo.

---

## 4. Criterios de Aceptación

| # | Criterio | Verificable |
|---|----------|-------------|
| 1 | `FlowHierarchyView` se renderiza en la página `/workflows` | ✅ Visualmente visible al navegar a `/workflows` |
| 2 | Los datos se cargan desde `GET /flows/hierarchy` | ✅ Network tab muestra la llamada con status 200 |
| 3 | Las categorías se muestran colapsables con badge de cantidad | ✅ Click en categoría expande/colapsa |
| 4 | Cada nodo muestra nombre, dependencias upstream y downstream | ✅ Texto legible para cada flow |
| 5 | Loading skeleton se muestra durante la carga | ✅ Se ve skeleton antes de que llegue la respuesta |
| 6 | Error state se muestra si la API falla | ✅ Simular error (ej. backend down) → card roja |
| 7 | Empty state se muestra si no hay flows | ✅ Con registry vacío → mensaje "Sin jerarquía" |
| 8 | No introduce errores de TypeScript | ✅ `npm run build` sin errores en dashboard |
| 9 | No rompe la funcionalidad existente de `/workflows` | ✅ El grid de workflows y filtros siguen operativos |
| 10 | El componente respeta el tema dark/light | ✅ Colores coherentes con CSS variables |

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| El grid de workflows + el árbol hacen la página demasiado larga (scroll excesivo) | Media | Bajo | El árbol usa categorías colapsables — el usuario controla la visibilidad. Se puede añadir un "Ver más / Ver menos" toggle si es necesario. |
| La API `/flows/hierarchy` es lenta con muchos flows | Baja | Medio | `staleTime: 60s` reduce refetches. Si hay >50 flows, considerar paginación o virtualización en roadmap. |
| Conflicto visual entre el filtro de status y el árbol | Baja | Bajo | Separación clara con spacing (`space-y-6`). El filtro afecta solo al grid de workflows, no al árbol. |
| El componente no se actualiza al registrar un nuevo flow en runtime | Media | Bajo | React Query refetch en focus + staleTime de 60s cubre la mayoría de casos. Para actualización instantánea se necesitaría invalidación manual (roadmap). |

---

## 6. Plan

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1 | Importar `FlowHierarchyView` en `/workflows/page.tsx` | Baja | — |
| 2 | Renderizar el componente debajo del grid de workflows, envuelto en condición de que existan workflows | Baja | Tarea 1 |
| 3 | Verificar que no haya conflictos de estilos o layout | Baja | Tarea 2 |
| 4 | Probar manualmente: carga, loading, error, empty state | Baja | Tarea 3 |
| 5 | Ejecutar `npm run build` en dashboard para confirmar 0 errores TypeScript | Baja | Tarea 4 |

**Orden recomendado:** 1 → 2 → 3 → 4 → 5 (lineal, sin paralelismo necesario).

**Estimación total:** Baja. El componente ya existe y funciona; solo requiere integración en la página existente.

---

## 🔮 Roadmap (NO implementar ahora)

### Mejoras de visualización
- **Grafo visual interactivo** con `@xyflow/react` o `reactflow`: nodos arrastrables, zoom, pan, minimap. Reemplazaría o complementaría la vista de árbol actual.
- **Highlight de dependencias al hover**: al pasar sobre un nodo, resaltar sus conexiones upstream/downstream y atenuar el resto.
- **Scroll-to-node**: click en badge de dependencia hace scroll al nodo dependiente.

### Validación visual
- **Indicadores de integridad**: mostrar warnings inline si `validation.invalid_dependencies` o `validation.cycles` contienen entradas relevantes para los flows visibles.
- **Badge de estado**: flows con dependencias rotas marcados con ícono de alerta amarillo.

### Interactividad
- **Click en nodo → detalle**: navegar a `/workflows/{flow_type}` o abrir un drawer con metadata del flow.
- **Filtrado por categoría**: en lugar de solo colapsar, permitir seleccionar qué categorías mostrar.
- **Búsqueda de flows**: input de texto para filtrar por nombre.

### Performance
- **Virtualización del árbol** si hay >50 flows registrados.
- **Refetch optimista** tras ejecutar `RunFlowDialog` (invalidar `['flows-hierarchy']` cuando se crea un nuevo flow dinámico).

### Decisiones de diseño tomadas para no bloquear futuro
- El componente está aislado en su propio archivo — fácilmente extraíble a página dedicada.
- El contrato de datos (`FlowHierarchyResponse`) ya incluye `validation` — solo falta consumirlo en UI.
- No se acopló la navegación a los badges — se pueden hacer clickeables sin refactor mayor.
- Se usó CSS puro para conectores (no librería de grafos) — migrar a `@xyflow/react` no requiere deshacer trabajo, solo añadir una capa adicional.
