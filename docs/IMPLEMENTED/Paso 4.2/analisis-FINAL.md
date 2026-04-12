# 🏛️ ANÁLISIS TÉCNICO UNIFICADO: PASO 4.2 - FlowHierarchyView.tsx

## 1. Resumen Ejecutivo
El `FlowHierarchyView` es el componente táctico central de la Fase 4, diseñado para ofrecer una **Supervisión de Inteligencia Estructural**. Su propósito es transformar la lista plana de procesos en una vista jerárquica y diagnóstica que permita a los operadores entender las dependencias críticas ("Upstream") y el impacto de propagación ("Downstream") de cada flujo de negocio.

Este componente no solo servirá para visualización, sino que actuará como un **Dashboard de Salud del Grafo**, resaltando proactivamente ciclos lógicos o dependencias rotas detectadas por el backend en el Paso 4.1. Se integrará directamente en la vista de `/workflows` para mantener el contexto operativo.

## 2. Diseño Funcional Consolidado

### Happy Path:
1. El usuario accede a la sección de **Workflows**.
2. Debajo del grid de plantillas, aparece la sección "**Jerarquía y Salud de Procesos**".
3. Los flows se presentan agrupados por **Categorías de Negocio** (ej. Ventas, Operaciones, Sistema) en secciones colapsables.
4. Cada nodo de flow muestra:
    - **Identidad:** Nombre formateado y ID técnico.
    - **Relaciones Upstream:** Qué otros flows deben existir/funcionar para que este sea válido (`depends_on`).
    - **Relaciones Downstream:** Qué flows se verían afectados si este flow falla o cambia.
5. El usuario puede expandir/colapsar categorías para gestionar la densidad visual.

### Edge Cases (MVP):
- **Ciclos Detectados:** Si el backend reporta un ciclo (A -> B -> A), el componente debe marcar los nodos involucrados con un estado de error crítico (borde rojo, animación sutil, icono de alerta).
- **Dependencias Huérfanas:** Si un flow depende de un tipo inexistente, se listará como "Roto" en rojo.
- **Sin Categoría:** Agrupamiento automático en un nodo "Sin categorizar" para asegurar que ningún flow quede oculto.

### Manejo de Errores:
- **Fallo de API:** Se muestra un `Alert` amigable con el error técnico y un botón de reintento.
- **Sin Datos:** Estado vacío con ilustración de `FolderTree` indicando que no hay flows registrados.

---

## 3. Diseño Técnico Definitivo

### Integración de Arquitectura
El componente se integrará en `dashboard/app/(dashboard)/workflows/page.tsx` como un módulo independiente.

### Contrato de Datos Actualizado
Es obligatorio actualizar las interfaces en `dashboard/lib/types.ts` para capturar la metadata de validación del backend:

```typescript
export interface FlowHierarchyResponse {
  hierarchy: Record<string, FlowHierarchyNode>
  categories: Record<string, string[]>
  validation: {
    invalid_dependencies: Record<string, string[]> // flow_type -> [inv_flow_types]
    cycles: string[][] // Lista de vectores de ciclos
  }
}
```

### Lógica de Visualización (Enriquecimiento)
Se refactorizará el componente existente para incluir:
- **Componente `HealthHeader`:** Indicador global de salud (ej. "Todo Verde" 🟢 o "3 Errores de Grafo" 🔴).
- **Lógica de Predicado `isInvalid`:** Una función que determine si un nodo está en un ciclo o tiene dependencias rotas basándose en el objeto `validation`.
- **Tooltip de Error:** Explicación técnica de por qué un nodo está en rojo (ej. "Forma parte del ciclo: A -> B -> A").

---

## 4. Decisiones Tecnológicas

1. **Uso de CSS Puro para Conectores:** Mantener la implementación actual de líneas con CSS absoluto (border-left/top) para simular el árbol. Es ligero y suficiente para la escala actual (< 50 flows).
2. **Integración en `/workflows`:** Decisión pragmática para evitar redundancia de navegación. Facilita la transición de "Crear" a "Supervisar".
3. **TanStack Query (Caché):** Mantener `staleTime: 60s`. Los cambios en la jerarquía son estructurales (requieren reinicio o registro de código), por lo que no requieren tiempo real.
4. **Framer Motion:** Introducir `AnimatePresence` y `motion.div` para las expansiones de categorías y la aparición de advertencias, elevando la estética a "Premium".

---

## 5. Criterios de Aceptación MVP ✅

### Funcionales:
- [ ] Los flows aparecen agrupados por su `category` definida en el backend.
- [ ] Las categorías son colapsables/expandibles y persisten su estado durante la sesión del componente.
- [ ] Se visualizan tanto los `depends_on` (Input) como los `required_by` (Output) de forma legible.

### Técnicos:
- [ ] El componente consume el endpoint `/api/flows/hierarchy` usando TanStack Query.
- [ ] El `npm run build` en el dashboard no arroja errores de tipos (requiere actualizar `types.ts`).
- [ ] El componente es totalmente responsive y no rompe el layout de la página de workflows.

### Robustez (Diagnóstico):
- [ ] **Visualización de Ciclos:** Si el API envía ciclos, los flows afectados se resaltan visualmente.
- [ ] **Visualización de Huérfanos:** Si el API envía dependencias inválidas, el nodo muestra un aviso de error.
- [ ] **Empty/Error States:** Se muestran skeletons durante la carga y una card de error estructurada si el fetch falla.

---

## 6. Plan de Implementación

1. **Fase 1: Tipado Reforzado [Baja]:** Actualizar `dashboard/lib/types.ts` con el objeto `validation` completo.
2. **Fase 2: Lógica de Diagnóstico [Media]:** Modificar `FlowHierarchyView.tsx` para extraer y computar los estados de error (ciclos/huérfanos) desde el payload.
3. **Fase 3: Refinamiento de UI [Media]:** 
    - Implementar el Header de Salud Global.
    - Añadir estilos de error (rojo/pulse) a los `FlowNode` afectados.
    - Integrar micro-animaciones con Framer Motion.
4. **Fase 4: Integración en Página [Baja]:** Importar y renderizar en `dashboard/app/(dashboard)/workflows/page.tsx`.

---

## 7. Riesgos y Mitigaciones
- **Riesgo:** Grafo muy denso dificulta lectura. 
- **Mitigación:** Las categorías están cerradas por defecto en flows con baja actividad y el scroll es manejado por el contenedor padre.
- **Riesgo:** Confusión entre "Categoría del Flow" y "Estado del Flow".
- **Mitigación:** Usar Badges distintivos para categorías y colores de borde/iconos para estados de error.

---

## 8. Testing Mínimo Viable
1. **Test de Integridad:** Verificar que un flow con `category="ventas"` aparezca en el grupo de Ventas.
2. **Test de Dependencias:** Verificar que si Flow A depende de Flow B, Flow B aparezca en "Requerido por" de Flow A.
3. **Test de Error:** Mockear una respuesta con un ciclo `A->B->A` y verificar que ambos nodos se pongan en rojo.

---

## 9. 🔮 Roadmap (NO implementar ahora)
- **Editor de Jerarquía:** Drag-and-drop para mover flows entre categorías (actualizando DB).
- **React Flow Integration:** Vista de grafo no lineal para grafos extremadamente complejos.
- **Filtros por Estado de Salud:** Mostrar solo los flows que tienen errores de configuración.
