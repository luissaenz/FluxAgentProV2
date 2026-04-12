# Diseño Funcional

## Happy Path Detallado
El usuario accede al dashboard de analítica o supervisión. La vista `FlowHierarchyView` se carga automáticamente, realizando una consulta al endpoint `/flows/hierarchy` para obtener la jerarquía completa de flows. Se renderiza una estructura visual organizada por categorías (ej. "ventas", "operaciones", "system"), donde cada categoría es una sección expandible por defecto. Dentro de cada categoría, los flows se muestran como nodos en un árbol visual con líneas conectores, indicando claramente las dependencias: "Depende de" (upstream) y "Requerido por" (downstream). Los flows sin dependencias se marcan como "independientes". El usuario puede colapsar/expandir categorías para navegar la jerarquía.

## Edge Cases Relevantes para MVP
- **Sin flows registrados**: Se muestra un estado vacío con icono de árbol y mensaje explicativo ("No hay flows registrados o no tienen metadata de jerarquía").
- **Flows sin categoría**: Agrupados bajo "Sin categoría" con formato consistente.
- **Flows sin dependencias**: Indicados explícitamente como "Flow independiente (sin dependencias)" para claridad.
- **Error de carga inicial**: No afecta otros componentes del dashboard; se muestra un card de error con icono y mensaje retry implícito.

## Manejo de Errores
- **API falla**: Componente muestra card con borde rojo, icono de alerta, título "Error al cargar la jerarquía" y mensaje técnico. No bloquea el resto del dashboard.
- **Datos inconsistentes**: La validación en backend previene dependencias huérfanas o ciclos, pero si ocurren, se muestran warnings en logs (no en UI para MVP).
- **Timeout de query**: TanStack Query maneja con configuración de staleTime 60s, evitando sobrecarga.

# Diseño Técnico

## Componentes Nuevos o Modificaciones
- **Nuevo componente principal**: `FlowHierarchyView.tsx` en `dashboard/components/flows/`.
- **Subcomponentes internos**: `CategoryTree` (maneja agrupación por categoría) y `FlowNode` (renderiza nodo individual con dependencias).
- **Interfaces**: Sin nuevas; reutiliza `FlowHierarchyNode` y `FlowHierarchyResponse` de `lib/types.ts`.

## Inputs/Outputs de Cada Componente
- **FlowHierarchyView**: Input: ninguno (fetch interno). Output: JSX con jerarquía completa o estados alternos (loading/error/empty).
- **CategoryTree**: Input: `category` (string), `flowTypes` (string[]), `hierarchy` (Record). Output: Sección expandible con lista de nodos.
- **FlowNode**: Input: `node` (FlowHierarchyNode), `hierarchy` (Record). Output: Card con header, dependencias upstream/downstream.

## Modelos de Datos Nuevos o Extensiones
Ninguna extensión requerida. Utiliza estructura existente de jerarquía con `category`, `depends_on` y `flow_type`.

## Integraciones
- **API**: Endpoint `/flows/hierarchy` (operativo desde paso 4.1), retorna `{ hierarchy: Record, categories: Record, validation: Dict }`.
- **Librerías**: TanStack React Query para fetching con caching. Shadcn/ui (Card, Badge, Button, Skeleton) para UI consistente. Lucide React para iconos.

Coherente con contratos vigentes: `category` string, `depends_on` array de strings. No contradice `estado-fase.md`.

# Decisiones

- **Visualización como árbol expandible**: Optado por estructura jerárquica simple en lugar de grafo completo (ej. con React Flow), para mantener complejidad baja en MVP y bundle pequeño. Las líneas conectores usan CSS absoluto para simular árbol visual sin librerías externas.
- **Bidireccionalidad de dependencias**: Mostrar tanto upstream ("Depende de") como downstream ("Requerido por") en cada nodo, proporcionando contexto completo sin requerir navegación adicional o tooltips.
- **Categorización por defecto**: Flows sin `category` agrupados en "Sin categoría" con formato consistente, evitando UI fragmentada.
- **Estados de UI**: Implementar loading skeleton, error card y empty state explícitos, siguiendo patrones de dashboard existente para UX coherente.
- **No lazy loading inicial**: Cargar toda jerarquía en una query para simplicidad; optimizable en roadmap si >50 flows.

Cada decisión justificada por priorización MVP: simplicidad técnica sobre features avanzadas, manteniendo extensibilidad futura.

# Criterios de Aceptación
- El componente `FlowHierarchyView` compila y renderiza sin errores de TypeScript o runtime.
- La jerarquía se agrupa correctamente por categorías con conteo visible en badges.
- Cada nodo de flow muestra nombre formateado (usando `formatFlowType`) y dependencias como badges legibles.
- Estados de loading (skeleton), error (card roja) y vacío (iconos explicativos) se manejan correctamente.
- La UI es responsive (funciona en mobile/desktop) y accesible (usando componentes shadcn con ARIA implícito).
- Las dependencias se calculan dinámicamente (upstream/downstream) sin asumir datos estáticos.
- El fetching usa staleTime de 60s para evitar sobrecarga en navegación frecuente.

# Riesgos
- **Rendimiento con escala**: Si hay >50 flows, el render podría ser lento en dispositivos bajos; **mitigación**: Implementar virtualización (react-window) en roadmap, no en MVP.
- **Complejidad visual en árboles profundos**: Dependencias anidadas podrían hacer la UI confusa; **mitigación**: Limitar profundidad inicial a 3 niveles, agregar indicador de "ver más" si necesario.
- **Dependencias circulares o inválidas**: Aunque validadas en backend, si pasan a frontend, causarían loops infinitos; **estrategia**: Agregar validación cliente-side básica y reportar errores a equipo dev vía logging.
- **Cambio en API contract**: Si `estado-fase.md` evoluciona, podría requerir refactor; **mitigación**: Tests unitarios para componente.
- **Bundle size**: Adición de iconos lucide podría crecer bundle; **mitigación**: Tree-shaking ya configurado en Next.js.

# Plan
1. **Crear estructura base de FlowHierarchyView.tsx** (Baja complejidad): Importar tipos, configurar useQuery, render básico con Card wrapper.
2. **Implementar CategoryTree subcomponente** (Media complejidad): Lógica de expansión/colapso, mapeo de flowTypes a nodos, cálculo de categorías display.
3. **Desarrollar FlowNode con dependencias** (Media complejidad): Render de card con header, badges para upstream/downstream, líneas conectores CSS.
4. **Agregar estados alternos (loading/error/empty)** (Baja complejidad): Skeleton para loading, AlertCircle para error, FolderTree para vacío.
5. **Testing manual y ajustes UX** (Baja complejidad): Verificar en browser, ajustar spacing/iconos para legibilidad.

**Orden recomendado**: 1→2→3→4→5, secuencial ya que cada paso depende del anterior.
**Dependencias**: Requiere endpoint `/flows/hierarchy` operativo (completado en paso 4.1). No bloquea otros pasos.

# 🔮 Roadmap (NO implementar ahora)
- **Optimizaciones de rendimiento**: Virtualización para listas >100 items, lazy loading por categoría.
- **Mejoras UX**: Soporte para zoom/pan en árbol, drag-and-drop reordenamiento de categorías, filtros por búsqueda.
- **Features avanzadas**: Exportar jerarquía como imagen/SVG, integración con herramientas de diagrama (ej. D3.js) si jerarquía crece.
- **Arquitectura futura**: Preparar para separación en micro-componentes si se agrega interactividad compleja (ej. edición inline de dependencias).
- **Decisiones tomadas pensando en futuro**: Estructura modular (subcomponentes) facilita extensiones sin refactor masivo; uso de CSS en lugar de librerías permite migración a React Flow si necesario.