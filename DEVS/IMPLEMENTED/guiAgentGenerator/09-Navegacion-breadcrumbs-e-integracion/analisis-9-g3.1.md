# Análisis Técnico: Paso 09 - Integración del Builder y Navegación

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Enlace "Builder" en sidebar existente | Visualizar `nav-main.tsx` | ✅ | `components/nav-main.tsx`, línea 50 |
| 2 | Componente `app-sidebar.tsx` | Verifica inclusión de la navegación | ✅ | `components/app-sidebar.tsx`, línea 64 usa `<NavMain />` |
| 3 | Componente UI Breadcrumb existe | Revisar `components/ui` | ✅ | `components/ui/breadcrumb.tsx` implementado |
| 4 | Componente `BuilderLayout` centraliza UI | Revisar `components/builder/BuilderLayout.tsx` | ✅ | `BuilderLayout.tsx` contiene los tabs y modales |
| 5 | Carga de ReactFlow sin SSR | Revisar `BuilderCanvas.tsx` | ✅ | `components/builder/BuilderCanvas.tsx`, línea 6 usa `dynamic(..., { ssr: false })` |
| 6 | Skeletons de carga | Revisar `CrewCanvas.tsx` y dynamic | ✅ | `components/builder/BuilderCanvas.tsx`, línea 8 y `CrewCanvas.tsx` línea 369 |
| 7 | Error Boundary del framework | Buscar `error.tsx` en builder | ❌ | No existe `app/(app)/builder/error.tsx` |

**Discrepancias encontradas:**
- **Error Boundary no implementado**: Aunque ReactFlow se carga con `dynamic`, si ocurre un fallo en runtime dentro del canvas, la aplicación entera podría crashear. Se debe agregar el archivo `error.tsx` estándar de Next.js en el directorio del builder.
- **Navegación Sidebar Ya Existente**: El enlace ya fue agregado en pasos anteriores. No es necesario re-crearlo, solo confirmar su funcionamiento con la estructura de Breadcrumbs.

---

### 1️⃣ Análisis de Datos (ETAPA 1)

- ✅ **Schema**: No aplica. Este paso es puramente de frontend y experiencia de usuario (UI/UX).
- ✅ **Integridad referencial**: No aplica.
- ✅ **RLS policies**: No aplica.
- ✅ **Índices necesarios**: No aplica.
- ✅ **Tipos de datos**: No aplica.

---

### 2️⃣ Análisis de Código (ETAPA 2)

- ✅ **Funciones/clases nuevas**: 
  - `error.tsx`: Componente `export default function BuilderError({ error, reset }: { error: Error; reset: () => void })` requerido por Next.js para capturar errores de cliente/servidor en la subruta.
- ✅ **Patrones**: Se emplean los componentes de `@/components/ui/breadcrumb.tsx` para generar la ruta visual.
- ✅ **Modularidad**: En lugar de afectar `page.tsx` con lógicas de estado visual, los Breadcrumbs deben implementarse dentro de `BuilderLayout.tsx` o conectarse a los tabs locales para reflejar la pestaña actual (`Agent Form` vs `Crew Canvas`).
- ✅ **Imports exactos**:
  - `from "@/components/ui/breadcrumb" import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator }`

---

### 3️⃣ Análisis de Backend (ETAPA 3)

- ✅ **APIs/endpoints**: No aplica.
- ✅ **Middleware**: No aplica.
- ✅ **Flujos**: No aplica.
- ✅ **Contratos**: No aplica.
- ✅ **Error handling**: El manejo de errores será del lado del cliente utilizando el Error Boundary de React/Next.js.

---

### 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

- ✅ **Flujo completo**: El usuario navega desde el Sidebar al Builder. El sistema debe mantener consistencia indicando en qué sub-herramienta del Builder está (a través de Breadcrumbs) y proteger la experiencia si el canvas falla.
- ✅ **Coherencia**: Utiliza el stack y theme de Shadcn garantizando integración visual sin saltos.
- ✅ **Alineación**: Ya contamos con las herramientas base (`dynamic` de Next.js, Shadcn components). 
- ✅ **Gaps**: "Templates" es un modal (Dialog), no una subruta ni un tab, por lo que integrarlo al breadcrumb podría ser anti-intuitivo. El breadcrumb debería mostrar principalmente la tab activa: `[New Agent | Crew Canvas]`.
- ✅ **DX & Tooling (OBLIGATORIO):**

### Herramienta Propuesta: `verify_ssr_components.py`
- **Qué automatiza:** Escanea el proyecto buscando importaciones directas de librerías propensas a romper el SSR (como `reactflow`) para asegurar que estén envueltas en `next/dynamic` con `ssr: false`.
- **Tipo:** script / validador
- **Cómo se usa:** `uv run python scripts/verify_ssr_components.py`
- **Impacto para el usuario final:** Previene fallos catastróficos en producción debidos a errores de hidratación o "Window is not defined" que arruinan la experiencia del usuario.
- **Prioridad:** Tarea 0 — ejecutar y validar antes de codificar la UI.

---

### 5️⃣ Criterios de Aceptación

✅ [FULLSTACK] El enlace "Builder" es visible y funcional en el Sidebar principal.
✅ [FULLSTACK] Los Breadcrumbs se renderizan en el `BuilderLayout` y reflejan la pestaña actual (Agent Form / Crew Canvas).
✅ [FULLSTACK] Existe un `error.tsx` en la ruta `/builder` que captura errores del canvas sin romper el dashboard general.
✅ [CODE] El canvas de ReactFlow utiliza `dynamic import` asegurando el criterio de SSR.
✅ [DX] La herramienta `verify_ssr_components.py` audita las importaciones de componentes de cliente y finaliza sin errores.

---

### 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Fallo del canvas ReactFlow | Media | Manipulación incorrecta de nodos o carga asíncrona | Implementar un Error Boundary global para la ruta `/builder` (`error.tsx`). |
| Inconsistencia de Breadcrumbs | Baja | El Builder no tiene sub-rutas físicas, usa un Layout basado en Tabs | Vincular el estado `activeTab` del Layout directamente al contenido del Breadcrumb. |

---

### 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX & Tooling**: validador SSR | `{paths.scripts}/verify_ssr_components.py` | `def run(): ...` | — | DX | Media | 0.5h | Ninguna | → verificar: `python scripts/verify_ssr_components.py` ejecuta sin errores |
| 1 | Modificar `BuilderLayout.tsx` para incluir Breadcrumbs dinámicos | `{paths.frontend}/components/builder/BuilderLayout.tsx` | `export function BuilderLayout()` (agregar el subcomponente Breadcrumb en el header) | `@/components/ui/breadcrumb.tsx` | CODE | Media | 1h | Tarea 0 | → verificar: Al cambiar entre tabs, el texto del Breadcrumb cambia. |
| 2 | Crear Error Boundary para el Builder | `{paths.frontend}/app/(app)/builder/error.tsx` | `export default function BuilderError({ error, reset }: { error: Error; reset: () => void })` | Patrón estándar de Next.js Error Boundaries | FULLSTACK | Baja | 0.5h | Tarea 1 | → verificar: Forzar un error en el canvas muestra la UI de recuperación sin romper la app. |

**Tiempo total estimado:** 2.0 horas
