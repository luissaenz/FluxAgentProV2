# Análisis Técnico — Paso 4.2: FlowHierarchyView.tsx

**Agente:** oc (Analista)  
**Fecha:** 2026-04-12  
**Estado:** ✅ YA IMPLEMENTADO

---

## 1. Diseño Funcional

### 1.1 Propósito
Componente de visualización en árbol de la jerarquía de flows de negocio, agrupados por categoría, mostrando dependencias upstream y downstream.

### 1.2 Happy Path
1. El componente realiza query a `GET /flows/hierarchy`
2. Renderiza cada categoría como un tree node colapsable
3. Dentro de cada categoría renderiza cada flow como un nodo independiente
4. Cada nodo muestra:
   - Nombre formateado del flow
   - Badge de categoría (si aplica)
   - Lista de dependencies (`depends_on`)
   - Lista de flows que dependen de este (`required by`)
5. Permite expandir/colapsar cada categoría

### 1.3 Edge Cases
- **Sin datos:** Muestra estado vacío con icono FolderTree
- **Error de API:** Muestra Card de error con AlertCircle
- **Loading:** Muestra Skeletons mientras carga
- **Flow sin categoría:** Agrupa bajo "sin_categoria"
- **Flow sin dependencias:** Muestra "Flow independiente"

### 1.4 Manejo de Errores
- Error HTTP: Muestra mensaje estructurado con título y descripción
- Sin red: Error capturado por TanStack Query, muestra estado de error

---

## 2. Diseño Técnico

### 2.1 Componentes Involved

| Componente | Archivo | Rol |
|------------|---------|-----|
| `FlowHierarchyView` | `dashboard/components/flows/FlowHierarchyView.tsx` | Componente principal |
| `CategoryTree` | Mismo archivo (interno) | Renderiza categoría colapsable |
| `FlowNode` | Mismo archivo (interno) | Renderiza nodo individual de flow |
| API Endpoint | `src/api/routes/flows.py:158-184` | Serve `/flows/hierarchy` |

### 2.2 Interfaces

```typescript
interface FlowHierarchyNode {
  flow_type: string;
  name: string;
  category?: string;
  depends_on: string[];
}

interface FlowHierarchyResponse {
  hierarchy: Record<string, FlowHierarchyNode>;
  categories: Record<string, string[]>;
  validation: {
    invalid_dependencies: Record<string, string[]>;
    cycles: string[][];
  };
}
```

### 2.3 Dependencias de Runtime
- `@tanstack/react-query` para data fetching
- `lucide-react` para iconos (ChevronRight, ChevronDown, GitBranch, ArrowDown, FolderTree, AlertCircle)
- Componentes UI de shadcn/ui: Card, CardContent, CardHeader, CardTitle, Badge, Skeleton, Button
- Tipos en `dashboard/lib/types.ts:221-229`

### 2.4 Data Flow
1. TanStack Query realiza GET a `/flows/hierarchy`
2. Response se cachea por 60 segundos (`staleTime: 60_000`)
3. Se renderiza `Object.entries(data.categories)` para cada categoría
4. Cada categoría renderiza sus flow types lookup en `hierarchy`

---

## 3. Decisiones

### Decisión 1: Uso de Componentes Internos
**Justificación:** `CategoryTree` y `FlowNode` son componentes de presentación puros que solo reciben props. No requieren estado ni lógica independiente, por lo que mantenerlos en el mismo archivo es apropiado para este nivel de complejidad.

### Decisión 2: Cache de 60 segundos
**Justificación:** La jerarquía de flows cambia muy infrequently (solo cuando se registra un nuevo flow en startup). Un staleTime de 60s evita refetching excesivo mientras mantiene coherencia razonable.

### Decisión 3: Validación No Mostrada en UI
**Justificación:** El endpoint retorna `validation` con ciclos y dependencias inválidas, pero el componente actual no lo renderiza. Esto es un gap: el usuario no ve warnings de integridad del grafo.

---

## 4. Criterios de Aceptación

| # | Criterio | Cumple |
|---|----------|--------|
| 1 | El componente se renderiza sin errores en la página | ✅ |
| 2 | La query a `/flows/hierarchy` se ejecuta correctamente | ✅ |
| 3 | Las categorías se agrupan y muestran colapsables | ✅ |
| 4 | Las dependencias `depends_on` se visualizan | ✅ |
| 5 | Los flows que dependen de un nodo se muestran como "required by" | ✅ |
| 6 | Estados de loading/error/empty funcionan | ✅ |
| 7 | **La validación del grafo se muestra al usuario** | ❌ FALTA |

---

## 5. Riesgos

### Riesgo 1: Validación No Visible
**Descripción:** Los resultados de validación (ciclos, dependencias inválidas) se reciben en la API pero no se renderizan en la UI.
**Mitigación:** Añadir sección de warnings en el componente para mostrar el estado de validación.

### Riesgo 2: Nodos Huérfanos No Identificados
**Descripción:** Si un flow tiene categoría `null`, se agrupa en "sin_categoria" pero no hay indicación visual de que requiere categorización.
**Mitigación:** Badge de "sin categorizar" con color distintivo.

---

## 6. Plan

### Tareas de Completado (ya realizadas)

| # | Tarea | Complejidad | Estado |
|---|-------|-------------|--------|
| 1 | Crear endpoint `/flows/hierarchy` en backend | Media | ✅ |
| 2 | Definir tipos TypeScript `FlowHierarchyNode`, `FlowHierarchyResponse` | Baja | ✅ |
| 3 | Implementar `FlowHierarchyView` con CategoryTree y FlowNode | Media | ✅ |
| 4 | Integrar con TanStack Query | Baja | ✅ |
| 5 | Añadir estados de loading/error/empty | Baja | ✅ |

### Tarea Pendiente (no bloqueante)

| # | Tarea | Complejidad | Dependencia |
|---|-------|-------------|-------------|
| 6 | Renderizar validation result (ciclos/dependencias inválidas) | Baja | #1-5 |

---

## 7. Roadmap (Post-MVP)

- **Visualización interactiva:** Click en nodo para ver detalle del flow y ejecuta directamente
- **Zoom/Pan:** Si la jerarquía crece mucho, permitir navegación visual tipo graph
- **Filtros:** Buscar flows por nombre o filtrar por categoría
- **Export:** Descargar diagrama como PNG/SVG