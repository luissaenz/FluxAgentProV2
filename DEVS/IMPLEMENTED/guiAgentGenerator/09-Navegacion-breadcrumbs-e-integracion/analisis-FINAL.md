# 🏛️ Análisis Técnico Unificado — Paso 9: Navegación, breadcrumbs e integración

> **Paso:** 9  
> **Fecha:** 2026-05-16  
> **Fase:** `guiAgentGenerator`
> **Estado:** 🏁 FINAL (Unificado)

---

### 0️⃣ Evaluación de Análisis y Verificaciones (OBLIGATORIO)

#### Tabla de Evaluación de Agentes

| Agente | Verificó código | Discrepancias detectadas | Propuesta DX | Evidencia sólida | Score (1-5) |
|:---|:---|:---|:---|:---|:---|
| step | ✅ | 4 | ✅ Boundary Validator | ✅ 25 elementos | 4.8 |
| g3.1 | ✅ | 2 | ✅ SSR Verifier | ✅ 7 elementos | 4.0 |
| lgn | ✅ | 3 | ✅ Boundary Validator | ✅ 9 elementos | 4.2 |
| op3.1 | ✅ | 4 | ✅ Builder Check | ✅ 22 elementos | 4.9 |

#### Discrepancias Críticas Consolidadas

| # | Discrepancia | Detectó | Verificada contra código | Resolución |
|---|---|---|---|---|
| 1 | `app-sidebar.tsx` tiene array `navMain` dead code | step, op3.1, lgn | ✅ `app-sidebar.tsx:28-38` | Eliminar array local y pasar `items={defaultNavItems}` a `<NavMain />` |
| 2 | Breadcrumbs UI existen pero no se usan | step, op3.1, lgn | ✅ `grep` 0 resultados en `dashboard/app/` | Implementar en `/builder/page.tsx` reflejando tabs activas. |
| 3 | Sin `loading.tsx` ni `error.tsx` en rutas | step, lgn, g3.1 | ✅ `find` 0 resultados en `dashboard/` | Crear archivos de convención Next.js en `/builder/`. |
| 4 | Sin ErrorBoundary específico para ReactFlow | op3.1, g3.1 | ✅ `grep` 0 resultados | Crear `BuilderErrorBoundary` (class component) para encapsular el canvas. |

---

### 1️⃣ Resumen Ejecutivo

Este paso integra estructuralmente el **Agent Builder** en el ecosistema del Dashboard. Se resuelve la desincronización de la navegación en el sidebar (eliminando código muerto), se implementa la navegación espacial mediante **Breadcrumbs** contextuales y se robustece la ruta mediante archivos de convención de Next.js (`loading.tsx`, `error.tsx`) y un **Error Boundary** dedicado para el canvas de ReactFlow.

**Correcciones críticas:**
- El plan sugería sub-rutas para breadcrumbs, pero el Builder usa **Tabs**. Los breadcrumbs se sincronizarán con el estado de las tabs sin cambiar la ruta física.
- Se detectó que el sidebar funciona "por accidente" al usar un fallback en `NavMain`. Se forzará el uso de `defaultNavItems` como única fuente de verdad.

**Decisión DX:** Se crea `scripts/validate_builder_nav.py`, una herramienta fusionada que valida la presencia de breadcrumbs, error boundaries, carga sin SSR y limpieza de dead code.

---

### 2️⃣ Diseño Funcional Consolidado

#### Happy Path
1. Usuario accede al Dashboard → Sidebar muestra "Builder" (ícono Wand2).
2. Click en "Builder" → Navega a `/builder`.
3. Se muestra `loading.tsx` con skeletons que replican el layout del Builder.
4. Página carga: Breadcrumb muestra `Dashboard > Builder > Agent Form`.
5. Cambio a tab "Crew Canvas" → Breadcrumb actualiza a `Dashboard > Builder > Crew Canvas`.
6. Si ReactFlow falla, el resto de la página (sidebar, breadcrumbs, tabs) permanece funcional gracias al Error Boundary local.

#### Edge Cases MVP
- **Fallo de hidratación:** El canvas DEBE cargarse con `ssr: false` para evitar discrepancias servidor/cliente.
- **Deep Linking:** El acceso directo vía `/builder?tab=crew-canvas` debe mostrar la tab y el breadcrumb correcto.
- **Resiliencia:** El botón "Retry" en el error boundary debe permitir re-intentar la carga del canvas sin refrescar toda la aplicación.

---

### 3️⃣ Diseño Técnico Definitivo

#### Componentes y Modificaciones

**1. `dashboard/components/app-sidebar.tsx` (Modificación)**
- **Tipo:** Limpieza y Refactor.
- **Acción:** Eliminar `const navMain = [...]` (dead code). Pasar `items={defaultNavItems}` a `<NavMain />`.
- **Justificación:** SSOT (Single Source of Truth) para la navegación.

**2. `dashboard/app/(app)/builder/loading.tsx` (Nuevo)**
- **Tipo:** UI / UX.
- **Descripción:** Skeleton que simula el layout 60/40 del builder.
- **Patrón:** Usar `<Skeleton>` de `@/components/ui/skeleton`.

**3. `dashboard/app/(app)/builder/error.tsx` (Nuevo)**
- **Tipo:** Robustez.
- **Descripción:** Error boundary de ruta Next.js. Muestra mensaje descriptivo y botón de reintento.

**4. `dashboard/components/builder/BuilderErrorBoundary.tsx` (Nuevo)**
- **Tipo:** Componente Core.
- **Interfaz:** `class BuilderErrorBoundary extends React.Component<Props, State>`
- **Justificación:** Capturar errores específicos de ReactFlow que `error.tsx` de ruta podría no aislar suficientemente.

**5. `dashboard/components/builder/BuilderBreadcrumb.tsx` (Nuevo)**
- **Tipo:** Navegación.
- **Interfaz:** `export function BuilderBreadcrumb({ activeTab }: { activeTab: string })`
- **Patrón:** Usar primitivas de `@/components/ui/breadcrumb.tsx`.

#### DX & Tooling — Tarea 0 (OBLIGATORIO)

```
### Herramienta: Builder Integrity Check
- **Qué automatiza:** Valida: 1) Sidebar SSOT, 2) Presencia de loading/error boundaries, 3) Configuración SSR en canvas, 4) Integración de Breadcrumbs.
- **Tipo:** script / validador
- **Ubicación:** scripts/validate_builder_nav.py
- **Cómo se usa:** uv run python scripts/validate_builder_nav.py
- **Impacto para el usuario final:** Previene regresiones visuales y crashes de hidratación que rompen la experiencia del usuario.
- **El implementador DEBE usarla** para verificar cada cambio realizado en las tareas 1-6.
```

---

### 4️⃣ Decisiones Tecnológicas

1. **Breadcrumbs basados en Estado:** Se decide NO crear sub-rutas físicas (`/builder/canvas`) para mantener la velocidad de cambio de pestañas de `BuilderLayout`. El breadcrumb consumirá una prop `activeTab`.
2. **Error Boundary de Clase:** Se usa un Class Component para `BuilderErrorBoundary` ya que es el único patrón soportado por React para capturar errores de renderizado de hijos de manera granular.
3. **SSOT Navigation:** Se elimina la duplicación en `app-sidebar.tsx` para evitar que futuras actualizaciones del catálogo de herramientas queden desincronizadas en el sidebar.

---

### 5️⃣ Criterios de Aceptación MVP

```
✅ [CODE] app-sidebar.tsx sin dead code (líneas 28-38 eliminadas).
✅ [CODE] BuilderBreadcrumb implementado y visible en /builder.
✅ [CODE] error.tsx y loading.tsx presentes en app/(app)/builder/.
✅ [CODE] BuilderCanvas envuelto en BuilderErrorBoundary dentro de BuilderLayout.
✅ [FULLSTACK] Sidebar muestra "Builder" correctamente.
✅ [FULLSTACK] Breadcrumb cambia entre "Agent Form" y "Crew Canvas" al alternar pestañas.
✅ [DX] scripts/validate_builder_nav.py valida exitosamente la estructura del Builder.
```

---

### 6️⃣ Plan de Implementación

| # | Tarea | Complejidad | Tiempo Est. | Dependencias |
|---|---|---|---|---|
| 0 | **DX & Tooling:** Crear `scripts/validate_builder_nav.py` | Media | 0.5h | Ninguna |
| 1 | Limpiar dead code y unificar nav en `app-sidebar.tsx` | Baja | 0.3h | Tarea 0 |
| 2 | Crear `loading.tsx` y `error.tsx` en `/builder` | Baja | 0.5h | Tarea 0 |
| 3 | Crear `BuilderErrorBoundary.tsx` e integrar en `BuilderLayout` | Media | 0.7h | Tarea 2 |
| 4 | Crear `BuilderBreadcrumb.tsx` e integrar en `page.tsx` | Media | 0.5h | Tarea 3 |
| 5 | Añadir sub-items de Builder en `nav-main.tsx` | Baja | 0.3h | Tarea 1 |
| 6 | Validación final con script DX y build de producción | Baja | 0.2h | Todas |
| **TOTAL** | | | **3.0h** | |

---

### 7️⃣ Riesgos y Mitigaciones

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Crash de hidratación | Alta | Importación de ReactFlow en SSR | Uso estricto de `dynamic(ssr: false)` validado por script DX. |
| Inconsistencia visual | Baja | Breadcrumbs solo en una página | Usar componentes de Shadcn para asegurar coherencia con el diseño atómico. |
| URL Desincronizada | Media | El breadcrumb no refleja la URL | Sincronizar tabs con query params `?tab=` en Tarea 5. |

---

### 8️⃣ Testing Mínimo Viable

| ID | Caso | Input | Output Esperado |
|---|---|---|---|
| TP-1 | Navegación Sidebar | Click en "Builder" | Carga `/builder` y resalta ítem en sidebar. |
| TP-2 | Breadcrumb dinámico | Click en Tab "Crew Canvas" | Texto cambia a `... > Builder > Crew Canvas`. |
| TP-3 | Error Boundary | Forzar crash en `CrewCanvas` | Se muestra fallback local, sidebar sigue usable. |

Comando para validar estructura: `uv run python scripts/validate_builder_nav.py`
