# 🧠 ANÁLISIS TÉCNICO: PASO 4.2 - FlowHierarchyView.tsx

## 1. Diseño Funcional

El `FlowHierarchyView` es el componente central para la supervisión de la arquitectura de procesos de negocio en LUMIS. No es solo una lista, sino una representación de la **inteligencia estructural** del sistema.

### Happy Path:
1. El usuario navega a la sección de "Workflows" (o una nueva pestaña de "Jerarquía").
2. El sistema carga los datos desde `GET /flows/hierarchy`.
3. Se presentan los procesos agrupados por **Categorías de Negocio** (ej. Ventas, Operaciones, Sistema).
4. Dentro de cada flow, se visualizan de forma clara sus dependencias:
    - **Upstream (Bloqueantes):** De qué otros procesos depende para iniciarse o completarse.
    - **Downstream (Impacto):** Qué otros procesos dependen de este.
5. El usuario puede expandir/colapsar categorías para gestionar la densidad de información.

### Edge Cases (MVP):
- **Grafos con Ciclos:** Si el backend detecta un ciclo (ej. A -> B -> A), el frontend debe resaltar los nodos involucrados con un estado de error/warning severo para evitar bucles infinitos en ejecución.
- **Dependencias Huérfanas:** Si un flow indica que depende de un ID de flow que no existe en el registro, el sistema debe marcarlo como "Inválido" o "Desconectado".
- **Sin Categoría:** Los flows sin metadata deben agruparse en una sección "Otros" o "Sin Categoría" para no perder visibilidad.

### Manejo de Errores:
- **Error de Red/API:** Mostrar un `Alert` amigable con opción de reintento.
- **Datos Inconsistentes:** Si el payload `hierarchy` no coincide con `categories`, priorizar la visualización de la lista plana para no bloquear al usuario.

---

## 2. Diseño Técnico

### Componente: `FlowHierarchyView.tsx`
Se basará en la estructura actual pero con un enfoque en **Diagnóstico y Calidad Visual**.

#### Modificaciones a la Interfaz de Tipos (`dashboard/lib/types.ts`):
Es CRÍTICO sincronizar el frontend con los nuevos campos de validación del backend:
```typescript
export interface FlowHierarchyResponse {
  hierarchy: Record<string, FlowHierarchyNode>
  categories: Record<string, string[]>
  validation: {
    invalid_dependencies: Record<string, string[]> // flow_type -> [deps_invalidas]
    cycles: string[][] // Listas de ciclos detectados
  }
}
```

#### Estructura de UI:
- **Header Informativo:** Resumen de salud del grafo ("X Procesos, Y Categorías, Z Errores detectados").
- **Grid de Categorías:** Layout responsivo de tarjetas o secciones colapsables.
- **Nodos de Flow Enriquecidos:**
    - Indicador de estado (Verde: OK, Rojo: Error/Ciclo, Ambar: Dependencia Huérfana).
    - Botón de acción rápida: "Ejecutar este flow" (reusing `RunFlowDialog`).

### Integración de Datos:
- **Hook:** Seguir usando `useQuery` de TanStack Query para caching y estados de loading.
- **Endpoint:** `api.get('/flows/hierarchy')`.

---

## 3. Decisiones

1. **Estado de Validación como Filtro Visual:** En lugar de solo listar, se usará el objeto `validation` para inyectar clases de CSS (ej. `border-destructive`, `animate-pulse`) a los nodos que comprometan la integridad del sistema.
2. **Uso de Lucid-React para Semántica:**
    - `Workflow`: Nodo estándar.
    - `AlertTriangle`: Ciclo detectado.
    - `Link2Off`: Dependencia rota.
3. **Mantenimiento del Componente Interno `FlowNode`:** Separar la lógica de cálculo de dependencias inversas ($isDependencyOf$) para mantener el renderizado eficiente.

---

## 4. Criterios de Aceptación

- [ ] **Visualización por Categoría:** Los flows se muestran agrupados según el campo `category` del backend.
- [ ] **Trazabilidad Upstream:** Se listan los `depends_on` de cada flow con nombres formateados.
- [ ] **Trazabilidad Downstream:** Se identifican y listan los flows que dependen del nodo actual.
- [ ] **Detección Visual de Ciclos:** Si un flow está en un ciclo (según `data.validation.cycles`), debe mostrar un borde rojo y un icono de advertencia.
- [ ] **Detección de Dependencias Rotas:** Si un flow tiene dependencias inválidas (según `data.validation.invalid_dependencies`), se listan explícitamente como errores en el nodo.
- [ ] **Interactividad Pro:Expandir/Colapsar:** Las categorías recuerdan su estado o al menos permiten navegación limpia.

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **Complejidad de Grafo:** Demasiados flows pueden saturar la pantalla. | Media | Implementar búsqueda local o filtros por categoría dentro de la vista. |
| **Desincronización de Tipos:** El backend envía `validation` pero el frontend no lo espera. | Alta | Actualizar `types.ts` ANTES de tocar el componente (Tarea 1 del plan). |
| **Performance:** El cálculo de dependencias inversas en el cliente con +100 flows. | Baja | El número de flows actual es < 20. Si crece, mover el cálculo de `isDependencyOf` al backend. |

---

## 6. Plan

1. **Tarea 1 [Typing]:** Actualizar `dashboard/lib/types.ts` para incluir el objeto `validation` completo (Complejidad: Baja).
2. **Tarea 2 [Logic]:** Refactorizar `FlowHierarchyView.tsx` para extraer los datos de validación del payload (Complejidad: Baja).
3. **Tarea 3 [UI Node]:** Mejorar el componente `FlowNode` para soportar estados de error (Ciclos/Rotos) y visualización de dependencias inversas mejorada (Complejidad: Media).
4. **Tarea 4 [UI Layout]:** Implementar el Header de Salud del Grafo con indicadores globales (Complejidad: Baja).
5. **Tarea 5 [Polish]:** Añadir animaciones de entrada (`Framer Motion`) y estados de hover premium (Complejidad: Media).

---

## 🔮 Roadmap (No implementar ahora)

- **Edición Drag-and-Drop:** Permitir cambiar dependencias visualmente y persistir en DB (vía `DynamicWorkflow`).
- **Vista de Grafo Real:** Integrar `React Flow` para representar el árbol de forma no lineal, con zoom y pan.
- **Métricas Vivas:** Superponer sobre cada nodo el % de éxito o tiempo promedio de ejecución actual (proveniente de `FlowTypeMetrics`).
